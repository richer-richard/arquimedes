"""Fast SQLite + FTS5 query engine with automatic JSONL shard fallback."""

from __future__ import annotations

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

    def get_stats(self) -> dict[str, Any]:
        stats: dict[str, Any] = {}
        if self.index_path.is_file():
            stats = json.loads(self.index_path.read_text(encoding="utf-8"))
        stats["sqliteReady"] = self.has_sqlite
        stats["repoRoot"] = str(self.root)
        return stats

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
            "number": row["source_number"],
            "mohs": row["difficulty_mohs"],
            "difficultyNote": meta.get("difficultyNote"),
            "answerLetter": row["answer_letter"],
            "answerValue": row["answer_value"],
            "hasChoices": bool(row["has_choices"]),
            "statement": stmt,
        }

    def get_problem(self, problem_id: str, include_solutions: bool = True, include_traces: bool = False) -> dict[str, Any] | None:
        if self.has_sqlite:
            conn = self._get_conn()
            row = conn.execute("SELECT * FROM problems WHERE id = ?", (problem_id,)).fetchone()
            if row is not None:
                meta = json.loads(row["metadata"]) if row["metadata"] else {}
                images = json.loads(row["images"]) if row["images"] else {"statement": [], "solutions": []}
                choices = [
                    {"label": c["label"], "text": c["text"]}
                    for c in conn.execute(
                        "SELECT label, text FROM answer_choices WHERE problem_id = ? ORDER BY label",
                        (problem_id,),
                    ).fetchall()
                ]
                solutions = []
                if include_solutions:
                    for s in conn.execute(
                        "SELECT id, kind, text, hints FROM solutions WHERE problem_id = ?",
                        (problem_id,),
                    ).fetchall():
                        solutions.append({
                            "id": s["id"],
                            "kind": s["kind"],
                            "text": s["text"],
                            "hints": json.loads(s["hints"]) if s["hints"] else [],
                        })
                result = {
                    "id": row["id"],
                    "title": row["title"] or "",
                    "category": row["category"],
                    "subjects": json.loads(row["subjects"]) if row["subjects"] else [],
                    "concepts": json.loads(row["concepts"]) if row["concepts"] else [],
                    "source": {
                        "dataset": row["dataset"],
                        "collection": row["source_collection"],
                        "year": row["source_year"],
                        "number": row["source_number"],
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
                    "answerChoices": choices,
                    "answer": {
                        "letter": row["answer_letter"],
                        "value": row["answer_value"],
                    },
                    "solutions": solutions,
                    "images": images,
                }
                if include_traces and row["dataset"] == "deepmath":
                    shard_rec = self._find_in_shards(problem_id, dataset="deepmath")
                    if shard_rec:
                        result["solutions"] = shard_rec.get("solutions") or solutions
                return result

        return self._find_in_shards(problem_id)

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
                where.append("EXISTS (SELECT 1 FROM problem_images pi WHERE pi.problem_id = p.id)")

            where_sql = ("WHERE " + " AND ".join(where)) if where else ""
            # Fast bounded candidate pool sample so we don't ORDER BY RANDOM() over 1M rows
            pool_size = max(limit * 25, 250)
            if not where:
                max_rowid = conn.execute("SELECT MAX(rowid) FROM problems").fetchone()[0] or 1
                rng = random.Random(seed)
                start_id = rng.randint(1, max(1, max_rowid - pool_size))
                sql = "SELECT * FROM problems p WHERE p.rowid >= ? LIMIT ?"
                rows = conn.execute(sql, [start_id, pool_size]).fetchall()
            else:
                sql = f"SELECT * FROM problems p {where_sql} LIMIT ?"
                rows = conn.execute(sql, [*params, pool_size]).fetchall()
            rng = random.Random(seed)
            if len(rows) > limit:
                rows = rng.sample(list(rows), limit)
            return [self._row_to_summary(r) for r in rows]

        # Shard fallback
        pool = []
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
            pool.append(self._rec_to_summary(rec))
            if len(pool) >= max(limit * 10, 100):
                break
        rng = random.Random(seed)
        if len(pool) > limit:
            pool = rng.sample(pool, limit)
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
