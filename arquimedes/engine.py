"""Fast SQLite + FTS5 query engine with automatic JSONL shard fallback."""

from __future__ import annotations

import collections
import gzip
import json
import os
import random
import sqlite3
from pathlib import Path
from typing import Any


def find_repo_root() -> Path:
    env_root = os.environ.get("ARQUIMEDES_ROOT")
    if env_root:
        p = Path(env_root).expanduser().resolve()
        if (p / "data" / "index.json").exists() or (p / "problems").is_dir():
            return p
    # Check relative to this package file
    pkg_root = Path(__file__).resolve().parent.parent
    if (pkg_root / "data" / "index.json").exists() or (pkg_root / "problems").is_dir():
        return pkg_root
    cwd = Path.cwd().resolve()
    if (cwd / "data" / "index.json").exists() or (cwd / "problems").is_dir():
        return cwd
    return pkg_root


class ArquimedesEngine:
    """High-speed read-only query interface over SQLite (with shard fallback)."""

    def __init__(self, root: Path | None = None):
        self.root = root or find_repo_root()
        self.db_path = self.root / "data" / "problems.sqlite"
        self.index_path = self.root / "data" / "index.json"
        self.problems_dir = self.root / "problems"
        self._conn: sqlite3.Connection | None = None
        self._fallback_stats: dict[str, Any] | None = None
        self._db_mode: str | None = None

    @property
    def has_sqlite(self) -> bool:
        return self.db_path.is_file() and self.db_path.stat().st_size > 0

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            uri = f"file:{self.db_path}?mode=ro"
            self._conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA query_only = ON")
            self._conn.execute("PRAGMA temp_store = MEMORY")
            self._conn.execute("PRAGMA mmap_size = 268435456")
        return self._conn

    @property
    def db_mode(self) -> str:
        """'lean' when the solutions table was left empty at build time, else 'full'."""
        if self._db_mode is None:
            try:
                row = self._get_conn().execute("SELECT value FROM build_info WHERE key = 'mode'").fetchone()
                self._db_mode = row[0] if row else "full"
            except sqlite3.OperationalError:
                self._db_mode = "full"
        return self._db_mode

    def _shard_record_for(self, row: sqlite3.Row) -> dict[str, Any] | None:
        """Load the full JSONL record behind a SQLite row."""
        if "shard_index" in row.keys() and row["shard_index"] is not None:
            path = self.problems_dir / row["dataset"] / f"shard-{row['shard_index']:05d}.jsonl.gz"
            if path.is_file():
                with gzip.open(path, "rt", encoding="utf-8") as fh:
                    line_no = 0
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        if line_no == row["shard_line"]:
                            rec = json.loads(line)
                            if rec.get("id") == row["id"]:
                                return rec
                            break
                        line_no += 1
        return self._find_in_shards(row["id"], dataset=row["dataset"])

    def get_stats(self) -> dict[str, Any]:
        index: dict[str, Any] = {}
        if self.index_path.is_file():
            index = json.loads(self.index_path.read_text(encoding="utf-8"))
        if self.has_sqlite:
            stats = index
        else:
            # data/index.json describes the full corpus; without SQLite only the
            # records _iter_shard_fallback reaches can be searched or sampled.
            stats = self._shard_fallback_stats()
            stats["note"] = (
                "data/problems.sqlite is not present, so search and sample only scan the "
                "JSONL shards counted here. Run `arquimedes build` to index the full corpus."
            )
            if index.get("totalProblems"):
                stats["fullCorpusProblems"] = index["totalProblems"]
        stats["sqliteReady"] = self.has_sqlite
        stats["repoRoot"] = str(self.root)
        return stats

    def fallback_datasets(self) -> list[str]:
        """Dataset slugs that have at least one JSONL shard on disk."""
        if not self.problems_dir.is_dir():
            return []
        return sorted(
            d.name for d in self.problems_dir.iterdir()
            if d.is_dir() and any(d.glob("shard-*.jsonl.gz"))
        )

    def _shard_fallback_stats(self) -> dict[str, Any]:
        if self._fallback_stats is None:
            datasets: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
            categories: collections.Counter = collections.Counter()
            competitions: collections.Counter = collections.Counter()
            kinds: collections.Counter = collections.Counter()
            for rec in self._iter_shard_fallback():
                src = rec.get("source") or {}
                cat = rec.get("category") or "uncategorized"
                datasets[src.get("dataset") or "unknown"][cat] += 1
                categories[cat] += 1
                if src.get("collection"):
                    competitions[src["collection"]] += 1
                for sol in rec.get("solutions") or []:
                    kinds[sol.get("kind") or "unknown"] += 1
            self._fallback_stats = {
                "totalProblems": sum(categories.values()),
                "datasets": {
                    slug: {"count": sum(cats.values()), "categories": dict(sorted(cats.items()))}
                    for slug, cats in sorted(datasets.items())
                },
                "categories": dict(sorted(categories.items())),
                "competitions": dict(sorted(competitions.items(), key=lambda kv: (-kv[1], kv[0]))),
                "solutionKinds": dict(sorted(kinds.items())),
            }
        return dict(self._fallback_stats)

    @staticmethod
    def _number(value: str | None) -> int | str | None:
        """source_number is stored as TEXT; records keep purely numeric numbers as ints."""
        return int(value) if value is not None and value.isdigit() else value

    @staticmethod
    def _record_view(rec: dict[str, Any], include_solutions: bool, include_traces: bool) -> dict[str, Any]:
        """The get_problem result shape, identical with a full, lean, or missing database."""
        src = rec.get("source") or {}
        diff = rec.get("difficulty") or {}
        ans = rec.get("answer") or {}
        solutions = []
        for s in rec.get("solutions") or []:
            wanted = include_traces if s.get("kind") == "model-reasoning" else include_solutions
            if wanted:
                solutions.append({
                    "id": s.get("id"),
                    "kind": s.get("kind"),
                    "text": s.get("text"),
                    "hints": s.get("hints") or [],
                })
        return {
            "id": rec.get("id"),
            "title": rec.get("title") or "",
            "category": rec.get("category"),
            "subjects": rec.get("subjects") or [],
            "concepts": rec.get("concepts") or [],
            "source": {
                "dataset": src.get("dataset"),
                "collection": src.get("collection"),
                "year": src.get("year"),
                "number": src.get("number"),
                "url": src.get("url"),
                "tags": src.get("tags") or [],
            },
            "difficulty": {
                "course": diff.get("course"),
                "source": diff.get("source"),
                "mohs": diff.get("mohs"),
                "note": diff.get("note"),
            },
            "estimatedMinutes": rec.get("estimatedMinutes"),
            "statement": rec.get("statement"),
            "answerChoices": [{"label": c.get("label"), "text": c.get("text")} for c in rec.get("answerChoices") or []],
            "answer": {"letter": ans.get("letter"), "value": ans.get("value")},
            "solutions": solutions,
            "images": rec.get("images") or {"statement": [], "solutions": []},
        }

    def _row_to_summary(self, row: sqlite3.Row) -> dict[str, Any]:
        meta = json.loads(row["metadata"]) if row["metadata"] else {}
        stmt = row["statement"] or ""
        return {
            "id": row["id"],
            "title": row["title"] or "",
            "dataset": row["dataset"],
            "category": row["category"],
            "competition": row["source_collection"],
            "year": row["source_year"],
            "number": self._number(row["source_number"]),
            "mohs": row["difficulty_mohs"],
            "difficultyNote": meta.get("difficultyNote"),
            "answerLetter": row["answer_letter"],
            "answerValue": row["answer_value"],
            "hasChoices": bool(row["has_choices"]),
            "statement": stmt,
        }

    def get_problem(self, problem_id: str, include_solutions: bool = True, include_traces: bool = False) -> dict[str, Any] | None:
        """Full problem record; include_solutions adds written solutions, include_traces adds
        deepmath model-reasoning traces. Returns None for unknown ids."""
        if not self.has_sqlite:
            rec = self._find_in_shards(problem_id)
            return self._record_view(rec, include_solutions, include_traces) if rec else None

        conn = self._get_conn()
        row = conn.execute("SELECT * FROM problems WHERE id = ?", (problem_id,)).fetchone()
        if row is None:
            return None
        meta = json.loads(row["metadata"]) if row["metadata"] else {}
        solutions: list[dict[str, Any]] = []
        if (include_solutions and self.db_mode == "lean") or (include_traces and row["dataset"] == "deepmath"):
            solutions = (self._shard_record_for(row) or {}).get("solutions") or []
        elif include_solutions:
            solutions = [
                {"id": s["id"], "kind": s["kind"], "text": s["text"],
                 "hints": json.loads(s["hints"]) if s["hints"] else []}
                for s in conn.execute(
                    "SELECT id, kind, text, hints FROM solutions WHERE problem_id = ? ORDER BY rowid",
                    (problem_id,),
                )
            ]
        rec = {
            "id": row["id"],
            "title": row["title"],
            "category": row["category"],
            "subjects": json.loads(row["subjects"]) if row["subjects"] else [],
            "concepts": json.loads(row["concepts"]) if row["concepts"] else [],
            "source": {
                "dataset": row["dataset"],
                "collection": row["source_collection"],
                "year": row["source_year"],
                "number": self._number(row["source_number"]),
                "url": meta.get("sourceUrl"),
                "tags": meta.get("sourceTags") or [],
            },
            "difficulty": {
                "course": row["difficulty_course"],
                "source": row["difficulty_source"],
                "mohs": row["difficulty_mohs"],
                "note": meta.get("difficultyNote"),
            },
            "estimatedMinutes": row["estimated_minutes"],
            "statement": row["statement"],
            "answerChoices": [
                {"label": c["label"], "text": c["text"]}
                for c in conn.execute(
                    "SELECT label, text FROM answer_choices WHERE problem_id = ? ORDER BY label",
                    (problem_id,),
                )
            ],
            "answer": {"letter": row["answer_letter"], "value": row["answer_value"]},
            "solutions": solutions,
            "images": json.loads(row["images"]) if row["images"] else None,
        }
        return self._record_view(rec, include_solutions, include_traces)

    def _find_in_shards(self, problem_id: str, dataset: str | None = None) -> dict[str, Any] | None:
        if not dataset and problem_id.startswith("prob."):
            slug = problem_id[len("prob."):].split("-", 1)[0]
            if (self.problems_dir / slug).is_dir():
                dataset = slug
            else:
                dataset = "core"
        dirs = [self.problems_dir / dataset] if dataset else sorted(self.problems_dir.iterdir())
        for d in dirs:
            if not d.is_dir():
                continue
            for shard in sorted(d.glob("shard-*.jsonl.gz")):
                with gzip.open(shard, "rt", encoding="utf-8") as fh:
                    for line in fh:
                        if problem_id in line:
                            rec = json.loads(line)
                            if rec.get("id") == problem_id:
                                return rec
        return None

    def search(
        self,
        query: str,
        *,
        category: str | None = None,
        dataset: str | None = None,
        competition: str | None = None,
        min_mohs: float | None = None,
        max_mohs: float | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(100, int(limit)))
        if self.has_sqlite:
            conn = self._get_conn()
            where = []
            params: list[Any] = []
            if category:
                where.append("p.category = ?")
                params.append(category)
            if dataset:
                where.append("p.dataset = ?")
                params.append(dataset)
            if competition:
                where.append("p.source_collection = ?")
                params.append(competition)
            if min_mohs is not None:
                where.append("p.difficulty_mohs >= ?")
                params.append(float(min_mohs))
            if max_mohs is not None:
                where.append("p.difficulty_mohs <= ?")
                params.append(float(max_mohs))

            # Clean query for FTS5 MATCH; fallback to LIKE if syntax has special chars
            fts_tokens = [t for t in query.replace('"', " ").split() if t]
            fts_query = " AND ".join(f'"{t}"' for t in fts_tokens)
            filter_sql = (" AND " + " AND ".join(where)) if where else ""

            try:
                sql = f"""
                    SELECT p.*
                    FROM problems_fts f
                    JOIN problems p ON p.rowid = f.rowid
                    WHERE problems_fts MATCH ? {filter_sql}
                    LIMIT ?
                """
                rows = conn.execute(sql, [fts_query, *params, limit]).fetchall()
                return [self._row_to_summary(r) for r in rows]
            except sqlite3.OperationalError:
                sql = f"""
                    SELECT p.*
                    FROM problems p
                    WHERE (p.statement LIKE ? OR p.title LIKE ?) {filter_sql}
                    LIMIT ?
                """
                like_q = f"%{query}%"
                rows = conn.execute(sql, [like_q, like_q, *params, limit]).fetchall()
                return [self._row_to_summary(r) for r in rows]

        # Shard fallback
        q_low = query.lower()
        results = []
        for rec in self._iter_shard_fallback(dataset=dataset):
            if category and rec.get("category") != category:
                continue
            src = rec.get("source") or {}
            if competition and src.get("collection") != competition:
                continue
            mohs = (rec.get("difficulty") or {}).get("mohs")
            if min_mohs is not None and (mohs is None or mohs < min_mohs):
                continue
            if max_mohs is not None and (mohs is None or mohs > max_mohs):
                continue
            if q_low in (rec.get("statement") or "").lower() or q_low in (rec.get("title") or "").lower():
                results.append(self._rec_to_summary(rec))
                if len(results) >= limit:
                    break
        return results

    def sample(
        self,
        *,
        category: str | None = None,
        dataset: str | None = None,
        competition: str | None = None,
        year: int | None = None,
        min_mohs: float | None = None,
        max_mohs: float | None = None,
        has_choices: bool | None = None,
        has_diagram: bool | None = None,
        limit: int = 5,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(100, int(limit)))
        if self.has_sqlite:
            conn = self._get_conn()
            where = []
            params: list[Any] = []
            if category:
                where.append("p.category = ?")
                params.append(category)
            if dataset:
                where.append("p.dataset = ?")
                params.append(dataset)
            if competition:
                where.append("p.source_collection = ?")
                params.append(competition)
            if year is not None:
                where.append("p.source_year = ?")
                params.append(int(year))
            if min_mohs is not None:
                where.append("p.difficulty_mohs >= ?")
                params.append(float(min_mohs))
            if max_mohs is not None:
                where.append("p.difficulty_mohs <= ?")
                params.append(float(max_mohs))
            if has_choices is not None:
                where.append("p.has_choices = ?")
                params.append(1 if has_choices else 0)
            if has_diagram:
                where.append("p.id IN (SELECT problem_id FROM problem_images WHERE role = 'statement')")

            # Uniform over every matching row: pick rowids, then load only those rows
            rng = random.Random(seed)
            if where:
                where_sql = "WHERE " + " AND ".join(where)
                rowids: Any = [r[0] for r in conn.execute(f"SELECT p.rowid FROM problems p {where_sql}", params)]
            else:
                rowids = range(1, (conn.execute("SELECT MAX(rowid) FROM problems").fetchone()[0] or 0) + 1)
            picked = rng.sample(rowids, min(limit, len(rowids)))
            if not picked:
                return []
            marks = ",".join("?" * len(picked))
            rows = {r["rowid"]: r for r in conn.execute(
                f"SELECT rowid, * FROM problems WHERE rowid IN ({marks})", picked)}
            return [self._row_to_summary(rows[i]) for i in picked if i in rows]

        # Shard fallback: reservoir sample over every matching record
        rng = random.Random(seed)
        pool: list[dict[str, Any]] = []
        seen = 0
        for rec in self._iter_shard_fallback(dataset=dataset):
            if category and rec.get("category") != category:
                continue
            src = rec.get("source") or {}
            if competition and src.get("collection") != competition:
                continue
            if year is not None and src.get("year") != year:
                continue
            mohs = (rec.get("difficulty") or {}).get("mohs")
            if min_mohs is not None and (mohs is None or mohs < min_mohs):
                continue
            if max_mohs is not None and (mohs is None or mohs > max_mohs):
                continue
            if has_choices is not None and bool(rec.get("answerChoices")) != has_choices:
                continue
            if has_diagram and not ((rec.get("images") or {}).get("statement")):
                continue
            seen += 1
            if len(pool) < limit:
                pool.append(self._rec_to_summary(rec))
            else:
                j = rng.randrange(seen)
                if j < limit:
                    pool[j] = self._rec_to_summary(rec)
        return pool

    def _iter_shard_fallback(self, dataset: str | None = None):
        if not self.problems_dir.is_dir():
            return
        dirs = [self.problems_dir / dataset] if dataset else sorted(self.problems_dir.iterdir())
        for d in dirs:
            if not d.is_dir():
                continue
            for shard in sorted(d.glob("shard-*.jsonl.gz"))[:2]:
                with gzip.open(shard, "rt", encoding="utf-8") as fh:
                    for line in fh:
                        if line.strip():
                            yield json.loads(line)

    @staticmethod
    def _rec_to_summary(rec: dict[str, Any]) -> dict[str, Any]:
        src = rec.get("source") or {}
        diff = rec.get("difficulty") or {}
        ans = rec.get("answer") or {}
        return {
            "id": rec.get("id"),
            "title": rec.get("title") or "",
            "dataset": src.get("dataset"),
            "category": rec.get("category"),
            "competition": src.get("collection"),
            "year": src.get("year"),
            "number": src.get("number"),
            "mohs": diff.get("mohs"),
            "difficultyNote": diff.get("note"),
            "answerLetter": ans.get("letter"),
            "answerValue": ans.get("value"),
            "hasChoices": bool(rec.get("answerChoices")),
            "statement": rec.get("statement") or "",
        }
