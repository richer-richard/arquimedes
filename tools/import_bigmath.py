#!/usr/bin/env python
"""Import SynthLabsAI/Big-Math-RL-Verified into staging shards.

Re-runnable: downloads the single parquet into raw/bigmath/ if missing (the
dataset is gated, so a Hugging Face access token is read from the HF_TOKEN
environment variable at runtime), then converts to staging/bigmath/. The
dataset has no human solutions, so records carry an empty solutions list.
Usage: HF_TOKEN=... .venv/bin/python tools/import_bigmath.py
"""

import json
import os
import re
import shutil
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pyarrow.parquet as pq

from tools.lib.schema import make_id, validate_record
from tools.lib.latex import normalize_latex, strip_boilerplate
from tools.lib.classify import classify_record
from tools.lib.difficulty import normalize_record_hygiene
from tools.lib.shards import write_shards, norm_key

SLUG = "bigmath"
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "raw" / SLUG
STAGING_DIR = ROOT / "staging" / SLUG
HF_PAGE = "https://huggingface.co/datasets/SynthLabsAI/Big-Math-RL-Verified"
URLS = [f"{HF_PAGE}/resolve/main/data/train-00000-of-00001.parquet"]

CJK_RE = re.compile(r"[一-鿿]")


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
        token = os.environ.get("HF_TOKEN", "").strip()
        if not token:
            sys.exit("HF_TOKEN is not set; the dataset is gated and requires a Hugging Face access token")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req) as resp, open(dest, "wb") as fh:
            shutil.copyfileobj(resp, fh)


def clean(text):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    return strip_boilerplate(normalize_latex(text)).strip()


def convert_rows(rows, stats, seen, records, notes, counters):
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

        raw_answer = (row.get("answer") or "").strip()
        if raw_answer:
            answer_value = clean(raw_answer)
        else:
            answer_value = None
            counters["no_answer"] += 1
        if "[asy]" in statement:
            counters["asy"] += 1

        rate = row.get("llama8b_solve_rate")
        if isinstance(rate, (int, float)):
            note = f"llama8b_solve_rate {rate:.3f}"
        else:
            note = None
            counters["null_solve_rate"] += 1

        src = row.get("source")
        tags = [str(src)] if src else []
        tags.extend(str(d) for d in (row.get("domain") or []))

        category = classify_record(statement, tags=tags)
        n = len(records)
        rec = normalize_record_hygiene({
            "id": make_id(SLUG, n),
            "title": "",
            "category": category,
            "subjects": [] if category == "uncategorized" else [category],
            "concepts": [],
            "source": {"dataset": SLUG, "collection": None, "year": None,
                       "number": None, "url": HF_PAGE, "tags": tags},
            "difficulty": {"course": None, "source": None, "mohs": None, "note": note},
            "estimatedMinutes": None,
            "statement": statement,
            "answerChoices": [],
            "answer": {"letter": None, "value": answer_value},
            "solutions": [],
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


def convert():
    stats = {"rows_raw": 0, "kept": 0, "dropped_nonenglish": 0,
             "dropped_invalid": 0, "dropped_dup": 0}
    seen = set()
    records = []
    notes = []
    counters = {"no_answer": 0, "asy": 0, "null_solve_rate": 0}

    for path in sorted(RAW_DIR.glob("train-*.parquet")):
        table = pq.read_table(path)
        stats["rows_raw"] += table.num_rows
        rows = table.to_pylist()
        rows.sort(key=lambda r: r.get("problem") or "")
        print(f"{path.name}: {table.num_rows} rows", flush=True)
        convert_rows(rows, stats, seen, records, notes, counters)

    stats["kept"] = len(records)
    shard_paths = write_shards(records, STAGING_DIR)
    summary = [
        "dataset has no human solutions; solutions list left empty",
        f"records with empty answer (answer.value=null): {counters['no_answer']}",
        f"statements containing [asy] kept inline: {counters['asy']}",
        f"rows with null llama8b_solve_rate (difficulty.note=null): {counters['null_solve_rate']}",
    ]
    report = {"dataset": SLUG, **stats,
              "shard_files": [str(p.relative_to(ROOT)) for p in shard_paths],
              "notes": (summary + notes)[:20]}
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    (STAGING_DIR / "REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2)[:1200])


if __name__ == "__main__":
    download()
    convert()
