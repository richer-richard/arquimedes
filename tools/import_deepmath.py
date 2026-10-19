#!/usr/bin/env python
"""Import zwhe99/DeepMath-103K into staging shards, with R1 reasoning traces.

Downloads the 10 full parquets into raw/deepmath/full/ (slim projections in
raw/deepmath/slim-*.parquet are kept for reference), then converts to
staging/deepmath/: same record mapping as the slim import, plus each non-empty
r1_solution_1/2/3 appended as a "model-reasoning" solution.
Usage: .venv/bin/python tools/import_deepmath.py
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
from tools.lib.classify import classify_record
from tools.lib.difficulty import normalize_record_hygiene
from tools.lib.shards import write_shards, norm_key

SLUG = "deepmath"
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "raw" / SLUG / "full"
STAGING_DIR = ROOT / "staging" / SLUG
MAX_RECORDS = 500
URLS = [f"https://huggingface.co/datasets/zwhe99/DeepMath-103K/resolve/main/data/train-0000{i}-of-00010.parquet"
        for i in range(10)]

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
        urllib.request.urlretrieve(url, dest)


def clean(text):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    return strip_boilerplate(normalize_latex(text)).strip()


def iter_sorted_rows(path, sort_col):
    """Yield rows of one parquet file as dicts, sorted by the sort column."""
    table = pq.read_table(path)
    keys = table.column(sort_col).to_pylist()
    order = sorted(range(len(keys)), key=lambda i: keys[i] or "")
    cols = {name: table.column(name) for name in table.column_names}
    for i in order:
        yield {name: col[i].as_py() for name, col in cols.items()}


def convert():
    stats = {"rows_raw": 0, "kept": 0, "dropped_nonenglish": 0,
             "dropped_invalid": 0, "dropped_dup": 0}
    seen = set()
    notes = []
    counters = {"n": 0, "traces": 0}

    def gen_records():
        for path in sorted(RAW_DIR.glob("train-*.parquet")):
            print(f"{path.name}", flush=True)
            for row in iter_sorted_rows(path, "question"):
                stats["rows_raw"] += 1
                statement = clean(row.get("question"))
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

                raw_answer = (row.get("final_answer") or "").strip()
                if raw_answer.lower() in ("", "proof", "notfound"):
                    answer_value = None
                else:
                    answer_value = clean(raw_answer)

                topic = row.get("topic")
                tags = [str(topic)] if topic else []
                difficulty = row.get("difficulty")
                note = f"deepmath {difficulty:g}" if isinstance(difficulty, (int, float)) and difficulty > 0 else "deepmath 5"

                n = counters["n"]
                base = f"{SLUG}-{n:06d}"
                solutions = []
                for j in (1, 2, 3):
                    trace = clean(row.get(f"r1_solution_{j}"))
                    if trace:
                        solutions.append({"id": f"sol.{base}.r1-{j}",
                                          "kind": "model-reasoning",
                                          "text": trace, "hints": [], "images": []})
                        counters["traces"] += 1
                category = classify_record(statement, tags=tags, solutions=solutions)
                rec = normalize_record_hygiene({
                    "id": make_id(SLUG, n),
                    "title": "",
                    "category": category,
                    "subjects": [] if category == "uncategorized" else [category],
                    "concepts": [],
                    "source": {"dataset": SLUG, "collection": None, "year": None,
                               "number": None, "url": None,
                               "tags": tags},
                    "difficulty": {"course": None, "source": None, "mohs": None, "note": note},
                    "estimatedMinutes": None,
                    "statement": statement,
                    "answerChoices": [],
                    "answer": {"letter": None, "value": answer_value},
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
                counters["n"] += 1
                yield rec

    # clear old shards so shard indices line up with the new layout
    for old in STAGING_DIR.glob("shard-*.jsonl.gz"):
        old.unlink()
    shard_paths = write_shards(gen_records(), STAGING_DIR, max_records=MAX_RECORDS)
    stats["kept"] = counters["n"]
    notes.append(f"traces_added={counters['traces']} (r1_solution_1/2/3, kind=model-reasoning)")
    sizes = [p.stat().st_size for p in shard_paths]
    notes.append(f"shard gz bytes: max={max(sizes)} min={min(sizes)}")
    report = {"dataset": SLUG, **stats, "traces_added": counters["traces"],
              "shard_files": [str(p.relative_to(ROOT)) for p in shard_paths],
              "notes": notes[:20]}
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    (STAGING_DIR / "REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "shard_files"}, indent=2))
    print(f"shards: {len(shard_paths)}")


if __name__ == "__main__":
    download()
    convert()
