#!/usr/bin/env python3
"""Build the Arquimedes SQLite database and summary index from merged shards.

Inputs:
  problems/<slug>/shard-*.jsonl.gz    final per-dataset problem records (v2 schema)
  images/                             diagram files (images/<sha256>.svg, olympiadbench <hash>.jpg)

Outputs:
  data/problems.sqlite                queryable SQLite database
  data/index.json                   summary index (datasets, categories, competitions, solution kinds)

Solutions with kind "model-reasoning" are excluded from the sqlite solutions
table (they remain in the JSONL shards) to keep the database small.
"""
import collections
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.lib.shards import read_shards  # noqa: E402

PROBLEMS_DIR = ROOT / "problems"
IMAGES_DIR = ROOT / "images"
DATA_DIR = ROOT / "data"

BATCH = 20000

# top-level record keys mapped to dedicated columns/tables; anything else
# lands in the metadata JSON column
KNOWN_KEYS = {
    "id", "title", "category", "subjects", "concepts", "source", "difficulty",
    "estimatedMinutes", "statement", "answerChoices", "answer", "solutions", "images",
}

DDL = """
CREATE TABLE problems (
    id TEXT PRIMARY KEY,
    title TEXT,
    category TEXT,
    dataset TEXT,
    subjects TEXT,          -- JSON array
    concepts TEXT,          -- JSON array
    source_collection TEXT,
    source_year INTEGER,
    source_number TEXT,
    difficulty_course REAL,
    difficulty_source REAL,
    difficulty_mohs REAL,
    estimated_minutes REAL,
    statement TEXT NOT NULL,
    answer_letter TEXT,
    answer_value TEXT,
    has_choices INTEGER,
    images TEXT,            -- JSON {statement: [...hash], solutions: [...hash]}
    metadata TEXT           -- JSON: extra record keys + sourceUrl/sourceTags/difficultyNote
);
CREATE TABLE answer_choices (
    problem_id TEXT REFERENCES problems(id),
    label TEXT,
    text TEXT,
    PRIMARY KEY (problem_id, label)
);
CREATE TABLE solutions (
    id TEXT PRIMARY KEY,
    problem_id TEXT REFERENCES problems(id),
    kind TEXT,
    text TEXT,
    hints TEXT              -- JSON array
);
CREATE TABLE images (
    hash TEXT PRIMARY KEY,
    path TEXT NOT NULL
);
CREATE TABLE problem_images (
    problem_id TEXT REFERENCES problems(id),
    image_hash TEXT REFERENCES images(hash),
    role TEXT,              -- 'statement' | 'solution'
    PRIMARY KEY (problem_id, image_hash, role)
);
"""

INDEXES = """
CREATE INDEX idx_problems_category ON problems(category);
CREATE INDEX idx_problems_dataset ON problems(dataset);
CREATE INDEX idx_problems_source ON problems(source_collection, source_year);
CREATE INDEX idx_problems_mohs ON problems(difficulty_mohs);
CREATE INDEX idx_problems_cat_mohs ON problems(category, difficulty_mohs);
CREATE INDEX idx_solutions_problem_id ON solutions(problem_id);
CREATE VIRTUAL TABLE problems_fts USING fts5(
    id UNINDEXED,
    title,
    statement,
    source_collection,
    content='problems',
    content_rowid='rowid'
);
INSERT INTO problems_fts(problems_fts) VALUES('rebuild');
"""


def scan_images():
    """Return {image_key: relative_path} for files in images/.

    SVGs are keyed by bare hash (core convention: records reference the hash,
    file is images/<hash>.svg). Other extensions (olympiadbench .jpg) are
    keyed by full filename, matching how records reference them.
    """
    table = {}
    if not IMAGES_DIR.is_dir():
        return table
    for path in sorted(IMAGES_DIR.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        key = path.stem if path.suffix == ".svg" else path.name
        table[key] = f"images/{path.name}"
    return table


def record_metadata(rec):
    meta = {k: rec[k] for k in rec if k not in KNOWN_KEYS}
    src = rec.get("source") or {}
    diff = rec.get("difficulty") or {}
    if src.get("url"):
        meta["sourceUrl"] = src["url"]
    if src.get("tags"):
        meta["sourceTags"] = src["tags"]
    if diff.get("note") is not None:
        meta["difficultyNote"] = diff["note"]
    return meta


def main():
    t0 = time.time()
    DATA_DIR.mkdir(exist_ok=True)
    db_path = DATA_DIR / "problems.sqlite"
    if db_path.exists():
        os.remove(db_path)
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA journal_mode=OFF")
    db.execute("PRAGMA synchronous=OFF")
    db.executescript(DDL)

    image_table = scan_images()
    db.executemany("INSERT OR IGNORE INTO images VALUES (?,?)",
                   [(h, p) for h, p in image_table.items()])

    stats = collections.Counter()
    datasets = collections.defaultdict(collections.Counter)  # slug -> category -> n
    categories = collections.Counter()
    competitions = collections.Counter()
    solution_kinds = collections.Counter()

    prob_rows, choice_rows, sol_rows, pimg_rows = [], [], [], []

    def flush():
        if prob_rows:
            db.executemany("INSERT INTO problems VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", prob_rows)
            prob_rows.clear()
        if choice_rows:
            db.executemany("INSERT INTO answer_choices VALUES (?,?,?)", choice_rows)
            choice_rows.clear()
        if sol_rows:
            db.executemany("INSERT INTO solutions VALUES (?,?,?,?,?)", sol_rows)
            sol_rows.clear()
        if pimg_rows:
            db.executemany("INSERT OR IGNORE INTO problem_images VALUES (?,?,?)", pimg_rows)
            pimg_rows.clear()

    dataset_dirs = sorted(d for d in PROBLEMS_DIR.iterdir() if d.is_dir())
    for d in dataset_dirs:
        slug = d.name
        for rec in read_shards(d):
            src = rec.get("source") or {}
            diff = rec.get("difficulty") or {}
            answer = rec.get("answer") or {}
            images = rec.get("images") or {}
            choices = rec.get("answerChoices") or []
            pid = rec["id"]

            prob_rows.append((
                pid,
                rec.get("title"),
                rec.get("category"),
                src.get("dataset") or slug,
                json.dumps(rec.get("subjects") or [], ensure_ascii=False),
                json.dumps(rec.get("concepts") or [], ensure_ascii=False),
                src.get("collection"),
                src.get("year") if isinstance(src.get("year"), int) else None,
                str(src["number"]) if src.get("number") is not None else None,
                diff.get("course"),
                diff.get("source"),
                diff.get("mohs"),
                rec.get("estimatedMinutes"),
                rec.get("statement"),
                answer.get("letter"),
                answer.get("value"),
                int(bool(choices)),
                json.dumps(images, ensure_ascii=False),
                json.dumps(record_metadata(rec), ensure_ascii=False),
            ))
            for c in choices:
                choice_rows.append((pid, c.get("label"), c.get("text")))

            for sol in rec.get("solutions") or []:
                kind = sol.get("kind")
                solution_kinds[kind] += 1
                if kind == "model-reasoning":
                    stats["solutions_excluded_model_reasoning"] += 1
                    continue
                sol_rows.append((
                    sol.get("id"), pid, kind, sol.get("text"),
                    json.dumps(sol.get("hints") or [], ensure_ascii=False),
                ))
                stats["solutions_kept"] += 1

            for role, key in (("statement", "statement"), ("solution", "solutions")):
                for h in images.get(key) or []:
                    if h in image_table:
                        pimg_rows.append((pid, h, role))
                    else:
                        stats["dangling_image_refs"] += 1

            stats["problems"] += 1
            datasets[slug][rec.get("category")] += 1
            categories[rec.get("category")] += 1
            if src.get("collection"):
                competitions[src["collection"]] += 1

            if len(prob_rows) >= BATCH:
                flush()
        flush()
        print(f"[{slug}] inserted ({time.time() - t0:.1f}s)", flush=True)

    db.executescript(INDEXES)
    db.commit()

    index = {
        "totalProblems": stats["problems"],
        "datasets": {
            slug: {"count": sum(cats.values()), "categories": dict(sorted(cats.items()))}
            for slug, cats in sorted(datasets.items())
        },
        "categories": dict(sorted(categories.items())),
        "competitions": dict(sorted(competitions.items(), key=lambda kv: (-kv[1], kv[0]))),
        "solutionKinds": dict(sorted(solution_kinds.items())),
    }
    with open(DATA_DIR / "index.json", "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1, ensure_ascii=False)

    db.close()
    stats["images"] = len(image_table)
    print(json.dumps(dict(stats), indent=2, sort_keys=True))
    print(f"build time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
