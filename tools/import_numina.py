#!/usr/bin/env python
"""Import AI-MO/NuminaMath-1.5 into staging shards.

Re-runnable: downloads the 3 parquet shards into raw/numina/ if missing,
then converts to staging/numina/. Usage: .venv/bin/python tools/import_numina.py
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
from tools.lib.classify import classify_category, map_known_subject
from tools.lib.shards import write_shards, norm_key

SLUG = "numina"
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "raw" / SLUG
STAGING_DIR = ROOT / "staging" / SLUG
URLS = [f"https://huggingface.co/datasets/AI-MO/NuminaMath-1.5/resolve/main/data/train-0000{i}-of-00003.parquet"
        for i in range(3)]

CJK_RE = re.compile(r"[一-鿿]")
LETTER_RE = re.compile(r"^[A-E]$")
SENTINELS = ("", "proof", "notfound")


def download():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for url in URLS:
        dest = RAW_DIR / url.rsplit("/", 1)[-1]
        if dest.exists():
            try:
                pq.ParquetFile(dest).metadata
                continue
            except Exception:
                print(f"re-downloading corrupt {dest.name}", flush=True)
                dest.unlink()
        print(f"downloading {url}", flush=True)
        urllib.request.urlretrieve(url, dest)


def clean(text):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    return strip_boilerplate(normalize_latex(text)).strip()


def convert_rows(rows, stats, seen, records, notes):
    for row in rows:
        if row.get("problem_is_valid") != "Yes":
            stats["dropped_invalid"] += 1
            continue
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

        question_type = row.get("question_type") or ""
        raw_answer = (row.get("answer") or "").strip()
        answer = {"letter": None, "value": None}
        if question_type != "proof" and raw_answer.lower() not in SENTINELS:
            if question_type == "MCQ":
                answer["value"] = clean(raw_answer)
                if LETTER_RE.match(raw_answer):
                    answer["letter"] = raw_answer.lower()
            elif LETTER_RE.match(raw_answer):
                answer["letter"] = raw_answer.lower()
            else:
                answer["value"] = clean(raw_answer)

        sol_text = clean(row.get("solution"))
        n = len(records)
        solutions = []
        if sol_text and row.get("solution_is_valid") == "Yes":
            solutions.append({"id": f"sol.{SLUG}-{n:06d}.0", "kind": "proof-sketch",
                              "text": sol_text, "hints": [], "images": []})

        src = row.get("source")
        tags = [str(src)] if src else []
        if row.get("synthetic"):
            tags.append("synthetic")

        category = map_known_subject(src) or classify_category(statement)
        rec = {
            "id": make_id(SLUG, n),
            "title": "",
            "category": category,
            "subjects": [] if category == "uncategorized" else [category],
            "concepts": [],
            "source": {"dataset": SLUG, "collection": None, "year": None,
                       "number": None, "url": None, "tags": tags},
            "difficulty": {"course": None, "source": None, "mohs": None, "note": None},
            "estimatedMinutes": None,
            "statement": statement,
            "answerChoices": [],
            "answer": answer,
            "solutions": solutions,
            "images": {"statement": [], "solutions": []},
        }
        try:
            validate_record(rec)
        except ValueError as exc:
            stats["dropped_invalid"] += 1
            notes.append(f"invalid row skipped: {exc}")
            continue
        seen.add(key)
        records.append(rec)


def convert():
    stats = {"rows_raw": 0, "kept": 0, "dropped_nonenglish": 0,
             "dropped_invalid": 0, "dropped_dup": 0}
    seen = set()
    records = []
    notes = []

    for path in sorted(RAW_DIR.glob("train-*.parquet")):
        table = pq.read_table(path)
        stats["rows_raw"] += table.num_rows
        rows = table.to_pylist()
        rows.sort(key=lambda r: r.get("problem") or "")
        print(f"{path.name}: {table.num_rows} rows", flush=True)
        convert_rows(rows, stats, seen, records, notes)

    stats["kept"] = len(records)
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
