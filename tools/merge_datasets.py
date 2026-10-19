#!/usr/bin/env python3
"""Merge legacy core problems and staged datasets into final problems/<slug>/ shards.

Inputs:
  problems/<category>/*.json          legacy v1 core records (consumed, then deleted)
  staging/<slug>/shard-*.jsonl.gz     v2-validated staged records
  staging/official/cemc-mc/           CEMC staging (dataset slug is "cemc")
  staging/olympiadbench/images/*      diagram images to copy into images/

Outputs:
  problems/<slug>/shard-*.jsonl.gz    final merged shards per dataset
  images/                             olympiadbench images copied in (dedup by name)

Dedupe is global on shards.norm_key(statement), in priority order:
core first (core wins), then aops, cemc, olympiadbench, omnimath, math,
deepmath, numina, bigmath, openr1. Non-core records get dense new ids make_id(slug, n) and their
solution ids are regenerated as sol.<id suffix>.<old trailing token>.

Re-runnable: existing problems/<slug>/ shard dirs are rewritten from staging;
if the legacy category tree is already gone, core shards are reused as-is.
A dataset whose staging dir is absent keeps its existing problems/<slug>/
shards, which are re-registered in the seen set so dedupe stays exact.
"""

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.lib.schema import CATEGORY_LIST, make_id  # noqa: E402
from tools.lib.difficulty import normalize_record_hygiene  # noqa: E402
from tools.lib.shards import norm_key, read_shards, write_shards  # noqa: E402

PROBLEMS = ROOT / "problems"
IMAGES = ROOT / "images"
STAGING = ROOT / "staging"

CORE_SHARD_SIZE = 10000
# priority order: (slug, staging dir, shard size) — shard sizes preserve staging limits
DATASETS = [
    ("aops", STAGING / "aops", 10000),
    ("cemc", STAGING / "official" / "cemc-mc", 10000),
    ("olympiadbench", STAGING / "olympiadbench", 10000),
    ("omnimath", STAGING / "omnimath", 10000),
    ("math", STAGING / "math", 10000),
    ("deepmath", STAGING / "deepmath", 500),
    ("numina", STAGING / "numina", 10000),
    ("bigmath", STAGING / "bigmath", 10000),
    ("openr1", STAGING / "openr1", 250),
]


def _digest(statement: str) -> bytes:
    return hashlib.sha1(norm_key(statement).encode("utf-8")).digest()


def _legacy_core_records():
    for path in sorted(PROBLEMS.glob("*/*.json")):
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
        src = rec.setdefault("source", {})
        src.setdefault("dataset", "core")
        src.setdefault("url", None)
        src.setdefault("tags", [])
        rec.setdefault("difficulty", {}).setdefault("note", None)
        yield rec


def _register_seen(records, seen):
    for rec in records:
        seen.add(_digest(rec["statement"]))
        yield rec


def merge_core(seen):
    """Build problems/core/ from the legacy category tree, then delete the tree.

    On re-run (legacy tree already gone) just re-register existing core shards
    in the seen set.
    """
    core_dir = PROBLEMS / "core"
    legacy_files = sorted(PROBLEMS.glob("*/*.json"))
    if not legacy_files:
        if not core_dir.is_dir():
            raise SystemExit("no legacy problems/<category>/*.json and no problems/core/ shards")
        n_in = 0
        for rec in read_shards(core_dir):
            seen.add(_digest(rec["statement"]))
            n_in += 1
        return {"dataset": "core", "input": n_in, "dupes_dropped": 0, "final": n_in,
                "note": "reused existing core shards"}

    n_in = len(legacy_files)
    write_shards(_register_seen(_legacy_core_records(), seen), core_dir, max_records=CORE_SHARD_SIZE)
    for cat in CATEGORY_LIST:
        cat_dir = PROBLEMS / cat
        if cat_dir.is_dir() and any(cat_dir.glob("*.json")):
            shutil.rmtree(cat_dir)
    return {"dataset": "core", "input": n_in, "dupes_dropped": 0, "final": n_in}


def _new_solution_id(old_sid, old_suffix, new_suffix, j, used, stats):
    token = None
    prefix = f"sol.{old_suffix}."
    if isinstance(old_sid, str) and old_sid.startswith(prefix):
        token = old_sid.rsplit(".", 1)[-1] or None
    if token is None:
        token = f"s{j}"
        stats["sol_id_fallback"] += 1
    new_id = f"sol.{new_suffix}.{token}"
    if new_id in used:
        new_id = f"sol.{new_suffix}.s{j}"
        stats["sol_id_collision"] += 1
    used.add(new_id)
    return new_id


def merge_dataset(slug, staging_dir, shard_size, seen):
    out_dir = PROBLEMS / slug
    if out_dir.is_dir():
        shutil.rmtree(out_dir)

    stats = {"dataset": slug, "input": 0, "dupes_dropped": 0, "final": 0,
             "sol_id_fallback": 0, "sol_id_collision": 0}

    def gen():
        for rec in read_shards(staging_dir):
            stats["input"] += 1
            dig = _digest(rec["statement"])
            if dig in seen:
                stats["dupes_dropped"] += 1
                continue
            seen.add(dig)
            old_suffix = rec["id"][len("prob."):]
            new_id = make_id(slug, stats["final"])
            stats["final"] += 1
            rec["id"] = new_id
            rec["source"]["dataset"] = slug
            new_suffix = new_id[len("prob."):]
            used = set()
            for j, sol in enumerate(rec.get("solutions") or []):
                sol["id"] = _new_solution_id(sol.get("id"), old_suffix, new_suffix, j, used, stats)
            yield normalize_record_hygiene(rec)

    write_shards(gen(), out_dir, max_records=shard_size)
    if stats["final"] == 0:
        shutil.rmtree(out_dir)  # fully deduped away (e.g. openr1 ⊂ numina)
    return stats


def copy_olympiadbench_images():
    src_dir = STAGING / "olympiadbench" / "images"
    copied = skipped = 0
    if not src_dir.is_dir():
        return {"copied": 0, "skipped_existing": 0}
    IMAGES.mkdir(exist_ok=True)
    for src in sorted(src_dir.iterdir()):
        if not src.is_file():
            continue
        dest = IMAGES / src.name
        if dest.exists():
            skipped += 1
            continue
        shutil.copy2(src, dest)
        copied += 1
    return {"copied": copied, "skipped_existing": skipped}


def main():
    t0 = time.time()
    seen = set()
    report = []

    report.append(merge_core(seen))
    print(f"[core] done ({time.time() - t0:.1f}s)", flush=True)

    for slug, staging_dir, shard_size in DATASETS:
        t = time.time()
        if not staging_dir.is_dir():
            out_dir = PROBLEMS / slug
            n_in = 0
            if out_dir.is_dir():
                for rec in read_shards(out_dir):
                    seen.add(_digest(rec["statement"]))
                    n_in += 1
                note = "staging absent, reused existing shards"
            else:
                note = "staging absent, no existing shards"
            report.append({"dataset": slug, "input": n_in, "dupes_dropped": 0,
                           "final": n_in, "note": note})
            print(f"[{slug}] reused ({time.time() - t:.1f}s)", flush=True)
            continue
        report.append(merge_dataset(slug, staging_dir, shard_size, seen))
        print(f"[{slug}] done ({time.time() - t:.1f}s)", flush=True)

    img_stats = copy_olympiadbench_images()

    total_in = sum(r["input"] for r in report)
    total_dup = sum(r["dupes_dropped"] for r in report)
    total_out = sum(r["final"] for r in report)

    print("\nper-dataset merge report:")
    print(f"{'dataset':<15} {'input':>9} {'dupes':>9} {'final':>9}")
    for r in report:
        print(f"{r['dataset']:<15} {r['input']:>9} {r['dupes_dropped']:>9} {r['final']:>9}")
        if r.get("note"):
            print(f"  note: {r['note']}")
        for k in ("sol_id_fallback", "sol_id_collision"):
            if r.get(k):
                print(f"  {k}: {r[k]}")
    print(f"{'TOTAL':<15} {total_in:>9} {total_dup:>9} {total_out:>9}")
    print(f"\nolympiadbench images: {img_stats}")
    print(f"elapsed: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
