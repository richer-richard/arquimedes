#!/usr/bin/env python3
"""Normalize all problem shards in-place using multiprocessing.

Applies:
  - Upgraded domain tag + statement + solution category classification
  - Unified Mohs difficulty scale (difficulty.mohs in [1.0, 10.0])
  - Subjects array normalization (no 'uncategorized' string in subjects)
  - Title underscore cleanup (e.g. 'Problem_1' -> 'Problem 1'), and source.number 'Problem_1' -> '1'
  - Unknown-level difficulty notes ('MATH Level ?', 'deepmath -1') set to null
  - Answer value cleanup (strip outer inline math delimiters, copy non-MC core letter to value, populate MC value)
  - HTML entity unescaping in statements
  - Full v2 schema validation on every record
"""

import collections
import gzip
import io
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.lib.difficulty import normalize_record_hygiene  # noqa: E402
from tools.lib.schema import validate_record  # noqa: E402

PROBLEMS_DIR = ROOT / "problems"


def _process_shard(shard_path_str: str) -> dict:
    shard_path = Path(shard_path_str)
    dataset = shard_path.parent.name
    tmp_path = shard_path.with_suffix(".jsonl.gz.tmp")

    counts = collections.Counter()
    cat_counts = collections.Counter()

    with gzip.open(shard_path, "rt", encoding="utf-8") as fin:
        gz_out = gzip.GzipFile(filename=str(tmp_path), mode="wb", mtime=0)
        with io.TextIOWrapper(gz_out, encoding="utf-8") as fout:
            for line in fin:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                old_cat = rec.get("category")
                old_mohs = (rec.get("difficulty") or {}).get("mohs")

                normalize_record_hygiene(rec)
                validate_record(rec)

                new_cat = rec.get("category")
                if old_cat == "uncategorized" and new_cat != "uncategorized":
                    counts["rescued_uncategorized"] += 1
                if old_mohs is None and rec["difficulty"]["mohs"] is not None:
                    counts["mohs_populated"] += 1
                counts["total"] += 1
                cat_counts[new_cat] += 1

                fout.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")))
                fout.write("\n")

    os.replace(tmp_path, shard_path)
    return {
        "dataset": dataset,
        "shard": shard_path.name,
        "counts": dict(counts),
        "categories": dict(cat_counts),
    }


def main():
    t0 = time.time()
    shards = sorted(str(p) for p in PROBLEMS_DIR.glob("*/shard-*.jsonl.gz"))
    workers = min(mp.cpu_count() or 4, 12)
    print(f"Normalizing {len(shards)} shards across {workers} workers...", flush=True)

    totals = collections.Counter()
    by_dataset = collections.defaultdict(collections.Counter)
    global_cats = collections.Counter()

    with mp.Pool(processes=workers) as pool:
        for res in pool.imap_unordered(_process_shard, shards, chunksize=4):
            ds = res["dataset"]
            for k, v in res["counts"].items():
                totals[k] += v
            for cat, n in res["categories"].items():
                by_dataset[ds][cat] += n
                global_cats[cat] += n

    elapsed = time.time() - t0
    print(f"Done in {elapsed:.1f}s!", flush=True)
    print("Totals:", json.dumps(dict(totals), indent=2))
    print("Global categories:", json.dumps(dict(sorted(global_cats.items(), key=lambda kv: -kv[1])), indent=2))
    for ds in sorted(by_dataset):
        unc = by_dataset[ds].get("uncategorized", 0)
        tot = sum(by_dataset[ds].values())
        print(f"  {ds:15s}: total={tot:>8,d}  uncategorized={unc:>6,d} ({100.0*unc/tot:.2f}%)")


if __name__ == "__main__":
    main()
