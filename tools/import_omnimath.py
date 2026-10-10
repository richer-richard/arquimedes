#!/usr/bin/env python
"""Import KbsdJames/Omni-MATH (Omni-Math.jsonl) into staging shards.

Re-runnable: downloads into raw/omnimath/ if missing, then converts to
staging/omnimath/. Usage: .venv/bin/python tools/import_omnimath.py
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.lib.schema import make_id, validate_record
from tools.lib.latex import normalize_latex, strip_boilerplate
from tools.lib.classify import classify_category, map_known_subject
from tools.lib.shards import write_shards, norm_key

SLUG = "omnimath"
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "raw" / SLUG
RAW_FILE = RAW_DIR / "Omni-Math.jsonl"
STAGING_DIR = ROOT / "staging" / SLUG
URL = "https://raw.githubusercontent.com/KbsdJames/Omni-MATH/main/Omni-Math.jsonl"

CJK_RE = re.compile(r"[一-鿿]")
LETTER_RE = re.compile(r"^[A-E]$")


def download():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not RAW_FILE.exists():
        print(f"downloading {URL}")
        urllib.request.urlretrieve(URL, RAW_FILE)


def clean(text):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    return strip_boilerplate(normalize_latex(text)).strip()


def category_from_domain(domain, statement):
    if isinstance(domain, list):
        for entry in domain:
            for part in str(entry).split("->"):
                cat = map_known_subject(part)
                if cat:
                    return cat
    return classify_category(statement)


def convert():
    rows = [json.loads(line) for line in RAW_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
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

        raw_answer = (row.get("answer") or "").strip()
        if raw_answer.lower() in ("", "proof", "notfound"):
            answer = {"letter": None, "value": None}
        elif LETTER_RE.match(raw_answer):
            answer = {"letter": raw_answer.lower(), "value": None}
        else:
            answer = {"letter": None, "value": clean(raw_answer)}

        sol_text = clean(row.get("solution"))
        n = len(records)
        solutions = []
        if sol_text:
            solutions.append({"id": f"sol.{SLUG}-{n:06d}.0", "kind": "proof-sketch",
                              "text": sol_text, "hints": [], "images": []})

        difficulty = row.get("difficulty")
        note = f"omnimath {difficulty:g}" if isinstance(difficulty, (int, float)) else None

        src = row.get("source")
        tags = [str(src)] if src else []

        category = category_from_domain(row.get("domain"), statement)
        rec = {
            "id": make_id(SLUG, n),
            "title": "",
            "category": category,
            "subjects": [] if category == "uncategorized" else [category],
            "concepts": [],
            "source": {"dataset": SLUG, "collection": None, "year": None,
                       "number": None, "url": None, "tags": tags},
            "difficulty": {"course": None, "source": None, "mohs": None, "note": note},
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
