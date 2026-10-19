#!/usr/bin/env python
"""Import MATH (DigitalLearningGmbH/MATH-lighteval mirror) into staging shards.

Re-runnable: downloads into raw/math/ if missing, then converts to
staging/math/. Usage: .venv/bin/python tools/import_math.py
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pyarrow.parquet as pq

from tools.lib.schema import make_id, validate_record
from tools.lib.latex import normalize_latex, strip_boilerplate
from tools.lib.classify import classify_record, map_known_subject
from tools.lib.difficulty import normalize_record_hygiene
from tools.lib.shards import write_shards, norm_key

SLUG = "math"
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "raw" / SLUG
STAGING_DIR = ROOT / "staging" / SLUG
BASE = "https://huggingface.co/datasets/DigitalLearningGmbH/MATH-lighteval/resolve/main/data"
SPLITS = {"train": "train-00000-of-00001.parquet", "test": "test-00000-of-00001.parquet"}

CJK_RE = re.compile(r"[一-鿿]")


def download():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for fname in SPLITS.values():
        dest = RAW_DIR / fname
        if not dest.exists():
            print(f"downloading {fname}")
            urllib.request.urlretrieve(f"{BASE}/{fname}", dest)


def clean(text):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    return strip_boilerplate(normalize_latex(text)).strip()


def extract_boxed(solution):
    """Return the content of the single top-level \\boxed{...} in solution, else None."""
    hits = []
    for m in re.finditer(r"\\boxed\s*\{", solution):
        depth, i = 1, m.end()
        while i < len(solution) and depth:
            if solution[i] == "{":
                depth += 1
            elif solution[i] == "}":
                depth -= 1
            i += 1
        if depth == 0:
            hits.append(solution[m.end():i - 1])
    return hits[0] if len(hits) == 1 else None


def convert():
    rows = []
    for split, fname in SPLITS.items():
        for row in pq.read_table(RAW_DIR / fname).to_pylist():
            row["split"] = split
            rows.append(row)
    rows.sort(key=lambda r: r.get("problem") or "")

    stats = {"rows_raw": len(rows), "kept": 0, "dropped_nonenglish": 0,
             "dropped_invalid": 0, "dropped_dup": 0}
    seen = set()
    records = []
    notes = []

    for row in rows:
        statement = clean(row.get("problem"))
        if not statement:
            stats["dropped_invalid"] += 1
            continue
        if CJK_RE.search(statement):
            stats["dropped_nonenglish"] += 1
            continue
        key = norm_key(statement)
        if key in seen:
            stats["dropped_dup"] += 1
            continue

        sol_text = clean(row.get("solution"))
        boxed = extract_boxed(sol_text) if sol_text else None
        answer = {"letter": None, "value": clean(boxed) if boxed else None}

        n = len(records)
        solutions = []
        if sol_text:
            solutions.append({"id": f"sol.{SLUG}-{n:06d}.0", "kind": "proof-sketch",
                              "text": sol_text, "hints": [], "images": []})

        subject = row.get("type") or ""
        tags = [t for t in (subject, row["split"]) if t]
        category = map_known_subject(subject) or classify_record(statement, tags=tags, solutions=solutions)
        level = row.get("level")
        rec = normalize_record_hygiene({
            "id": make_id(SLUG, n),
            "title": "",
            "category": category,
            "subjects": [] if category == "uncategorized" else [category],
            "concepts": [],
            "source": {"dataset": SLUG, "collection": "MATH", "year": None,
                       "number": None, "url": None,
                       "tags": tags},
            "difficulty": {"course": None, "source": None, "mohs": None,
                           "note": f"MATH {level}" if level else None},
            "estimatedMinutes": None,
            "statement": statement,
            "answerChoices": [],
            "answer": answer,
            "solutions": solutions,
            "images": {"statement": [], "solutions": []},
        })
        try:
            validate_record(rec)
        except ValueError as exc:
            stats["dropped_invalid"] += 1
            notes.append(f"invalid row skipped: {exc}")
            continue
        seen.add(key)
        records.append(rec)

    stats["kept"] = len(records)
    n_ans = sum(1 for r in records if r["answer"]["value"] is not None)
    notes.append(f"answer.value extracted from \\boxed in {n_ans}/{len(records)} records")
    shard_paths = write_shards(records, STAGING_DIR)
    report = {"dataset": SLUG, **stats,
              "shard_files": [str(p.relative_to(ROOT)) for p in shard_paths],
              "notes": notes[:20]}
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    (STAGING_DIR / "REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2)[:1200])


if __name__ == "__main__":
    download()
    convert()
