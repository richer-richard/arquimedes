#!/usr/bin/env python
"""Import Hothan/OlympiadBench (English maths COMP configs) into staging shards.

Re-runnable: downloads into raw/olympiadbench/ if missing, then converts to
staging/olympiadbench/ (images in staging/olympiadbench/images/).
Usage: .venv/bin/python tools/import_olympiadbench.py
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
from tools.lib.images import save_image

SLUG = "olympiadbench"
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "raw" / SLUG
STAGING_DIR = ROOT / "staging" / SLUG
IMAGES_DIR = STAGING_DIR / "images"
CONFIGS = ["OE_TO_maths_en_COMP", "TP_TO_maths_en_COMP",
           "OE_MM_maths_en_COMP", "TP_MM_maths_en_COMP"]
ALL_CONFIGS = [
    "OE_MM_maths_en_COMP", "OE_MM_maths_zh_CEE", "OE_MM_maths_zh_COMP",
    "OE_MM_physics_en_COMP", "OE_MM_physics_zh_CEE",
    "OE_TO_maths_en_COMP", "OE_TO_maths_zh_CEE", "OE_TO_maths_zh_COMP",
    "OE_TO_physics_en_COMP", "OE_TO_physics_zh_CEE",
    "TP_MM_maths_en_COMP", "TP_MM_maths_zh_CEE", "TP_MM_maths_zh_COMP",
    "TP_MM_physics_en_COMP",
    "TP_TO_maths_en_COMP", "TP_TO_maths_zh_CEE", "TP_TO_maths_zh_COMP",
    "TP_TO_physics_en_COMP",
]
BASE = "https://huggingface.co/datasets/Hothan/OlympiadBench/resolve/main/OlympiadBench"

CJK_RE = re.compile(r"[一-鿿]")


def download():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for cfg in CONFIGS:
        dest = RAW_DIR / f"{cfg}.parquet"
        if not dest.exists():
            print(f"downloading {cfg}")
            urllib.request.urlretrieve(f"{BASE}/{cfg}/{cfg}.parquet", dest)


def download_full():
    """Archive all 18 configs into raw/olympiadbench/full/ (conversion scope
    stays the 4 English-maths COMP configs in CONFIGS)."""
    full_dir = RAW_DIR / "full"
    full_dir.mkdir(parents=True, exist_ok=True)
    for cfg in ALL_CONFIGS:
        dest = full_dir / f"{cfg}.parquet"
        if not dest.exists():
            print(f"downloading full/{cfg}")
            urllib.request.urlretrieve(f"{BASE}/{cfg}/{cfg}.parquet", dest)


def clean(text):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    return strip_boilerplate(normalize_latex(text)).strip()


def sniff_ext(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    return None


def convert():
    rows = []
    for cfg in CONFIGS:
        for row in pq.read_table(RAW_DIR / f"{cfg}.parquet").to_pylist():
            row["config"] = cfg
            rows.append(row)
    rows.sort(key=lambda r: (r["config"], r.get("id") or 0))

    stats = {"rows_raw": len(rows), "kept": 0, "dropped_nonenglish": 0,
             "dropped_invalid": 0, "dropped_dup": 0}
    seen = set()
    records = []
    notes = []
    n_images = 0
    n_bad_images = 0

    for row in rows:
        question = clean(row.get("question"))
        context = clean(row.get("context"))
        statement = f"{context}\n\n{question}" if context else question
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

        stmt_images = []
        for i in range(1, 10):
            img = row.get(f"image_{i}")
            if not img or not img.get("bytes"):
                continue
            data = img["bytes"]
            ext = sniff_ext(data)
            if ext is None:
                n_bad_images += 1
                continue
            stmt_images.append(save_image(data, ext, IMAGES_DIR))
            n_images += 1

        finals = [clean(a) for a in (row.get("final_answer") or []) if a and a.strip()]
        if len(finals) > 1:
            answer_value = ", ".join(finals)
        elif finals:
            answer_value = finals[0]
        else:
            answer_value = None
        if answer_value and answer_value.lower() in ("proof", "notfound"):
            answer_value = None

        sol_parts = [clean(s) for s in (row.get("solution") or []) if s and s.strip()]
        sol_text = "\n\n".join(p for p in sol_parts if p)

        n = len(records)
        solutions = []
        if sol_text:
            solutions.append({"id": f"sol.{SLUG}-{n:06d}.0", "kind": "proof-sketch",
                              "text": sol_text, "hints": [], "images": []})

        subfield = row.get("subfield")
        category = map_known_subject(subfield) or classify_category(statement)
        difficulty = row.get("difficulty")
        tags = [t for t in (row["config"], row.get("subject"), row.get("answer_type")) if t]
        rec = {
            "id": make_id(SLUG, n),
            "title": "",
            "category": category,
            "subjects": [] if category == "uncategorized" else [category],
            "concepts": [],
            "source": {"dataset": SLUG, "collection": "OlympiadBench", "year": None,
                       "number": None, "url": None, "tags": tags},
            "difficulty": {"course": None, "source": None, "mohs": None,
                           "note": str(difficulty) if difficulty else None},
            "estimatedMinutes": None,
            "statement": statement,
            "answerChoices": [],
            "answer": {"letter": None, "value": answer_value},
            "solutions": solutions,
            "images": {"statement": stmt_images, "solutions": []},
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
    notes.append(f"images saved: {n_images}, unrecognized image magic skipped: {n_bad_images}")
    shard_paths = write_shards(records, STAGING_DIR)
    report = {"dataset": SLUG, **stats,
              "shard_files": [str(p.relative_to(ROOT)) for p in shard_paths],
              "notes": notes[:20]}
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    (STAGING_DIR / "REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2)[:1200])


if __name__ == "__main__":
    download()
    download_full()
    convert()
