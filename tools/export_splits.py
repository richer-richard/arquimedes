#!/usr/bin/env python3
"""Export decontaminated train and eval splits from the Arquimedes problem shards.

Canonical Evaluation Split (`eval`):
  - `math` test split (5,000 benchmark problems, including MATH-500)
  - `olympiadbench` (1,389 olympiad benchmark problems)
  - `omnimath` (2,640 olympiad benchmark problems)
  - `aops` (311 IMO Shortlist, USAJMO, Canadian MO, APMO, Putnam problems)
  - Recent competition problems (`source.year >= 2023`) from `core` and `cemc`
    (covers recent AMC 8/10/12, AIME I/II, USAMO, IMO, HMMT, CEMC)

Decontaminated Training Split (`train`):
  - All remaining problems across `numina`, `deepmath`, `bigmath`, `math` (train split),
    and pre-2023 `core` / `cemc` that:
      1. Have a verifiable answer (`answer.value` is non-empty) OR a written/reasoning solution
      2. Do NOT collide with any evaluation problem under exact normalized key (`norm_key`)
      3. Do NOT collide with any evaluation problem under 5-gram token shingle overlap
         (catches reworded or slightly reformatted benchmark leaks)

Usage:
  .venv/bin/python tools/export_splits.py [--out-dir splits] [--stats-only]
"""

import argparse
import collections
import gzip
import hashlib
import io
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.lib.shards import norm_key, read_shards  # noqa: E402

PROBLEMS_DIR = ROOT / "problems"
DEFAULT_OUT = ROOT / "splits"

_WORD_RE = re.compile(r"[a-z0-9]{2,}")
_STOP_TOKENS = {
    "the", "and", "for", "that", "with", "from", "are", "is", "in", "to", "of",
    "let", "find", "what", "value", "number", "positive", "real", "integers",
    "integer", "determine", "show", "prove", "given", "such", "many", "how",
    "frac", "sqrt", "left", "right", "cdot", "text", "begin", "end",
}


def _digest(key: str) -> bytes:
    return hashlib.sha1(key.encode("utf-8")).digest()


def _characteristic_shingle_hashes(statement: str, k: int = 5, max_shingles: int = 6) -> list[int]:
    """Extract deterministic 64-bit hashes of the rarest/longest k-word shingles for near-dup detection."""
    tokens = [w for w in _WORD_RE.findall(statement.lower()) if w not in _STOP_TOKENS]
    if len(tokens) < k:
        return []
    shingles = []
    for i in range(len(tokens) - k + 1):
        s = " ".join(tokens[i:i + k])
        h = int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest(), "little")
        shingles.append(h)
    shingles.sort()
    return shingles[:max_shingles]


def is_eval_record(rec: dict) -> tuple[bool, str | None]:
    """Return (True, benchmark_name) if record belongs to the canonical evaluation set."""
    src = rec.get("source") or {}
    ds = src.get("dataset") or ""
    year = src.get("year")
    tags = set(src.get("tags") or [])

    if ds == "olympiadbench":
        return True, "olympiadbench"
    if ds == "omnimath":
        return True, "omnimath"
    if ds == "aops":
        return True, "aops"
    if ds == "math" and "test" in tags:
        return True, "math_test"
    if ds in ("core", "cemc") and isinstance(year, int) and year >= 2023:
        return True, f"{ds}_2023plus"
    return False, None


def main():
    parser = argparse.ArgumentParser(description="Export decontaminated train/eval splits.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT,
                        help="Output directory for train.jsonl.gz, eval.jsonl.gz, and REPORT.json")
    parser.add_argument("--stats-only", action="store_true",
                        help="Compute decontamination statistics without writing output split files")
    args = parser.parse_args()

    t0 = time.time()
    eval_exact = set()
    eval_shingles = set()
    stats = collections.Counter()
    eval_by_benchmark = collections.Counter()
    train_by_dataset = collections.Counter()
    decontam_by_dataset = collections.Counter()

    out_dir: Path = args.out_dir
    if not args.stats_only:
        out_dir.mkdir(parents=True, exist_ok=True)
        eval_gz = gzip.GzipFile(filename=str(out_dir / "eval.jsonl.gz"), mode="wb", mtime=0)
        eval_fh = io.TextIOWrapper(eval_gz, encoding="utf-8")
        train_gz = gzip.GzipFile(filename=str(out_dir / "train.jsonl.gz"), mode="wb", mtime=0)
        train_fh = io.TextIOWrapper(train_gz, encoding="utf-8")
    else:
        eval_fh = train_fh = None

    try:
        # Pass 1: Collect evaluation benchmark problems and index their exact keys + token shingles
        print("Pass 1: Indexing canonical evaluation splits...", flush=True)
        for ds in ("core", "cemc", "aops", "olympiadbench", "omnimath", "math"):
            dpath = PROBLEMS_DIR / ds
            if not dpath.is_dir():
                continue
            for rec in read_shards(dpath):
                is_eval, bench = is_eval_record(rec)
                if not is_eval:
                    continue
                stmt = rec.get("statement") or ""
                eval_exact.add(_digest(norm_key(stmt)))
                for sh in _characteristic_shingle_hashes(stmt):
                    eval_shingles.add(sh)
                stats["eval_total"] += 1
                eval_by_benchmark[bench] += 1
                if eval_fh is not None:
                    out_rec = dict(rec)
                    out_rec["split"] = "eval"
                    out_rec["benchmark"] = bench
                    eval_fh.write(json.dumps(out_rec, ensure_ascii=False, separators=(",", ":")) + "\n")

        print(f"  Indexed {stats['eval_total']:,} eval problems "
              f"({len(eval_shingles):,} 5-gram shingle fingerprints) in {time.time() - t0:.1f}s.", flush=True)

        # Pass 2: Stream candidate training problems and decontaminate against eval index
        print("Pass 2: Filtering and decontaminating training split...", flush=True)
        for dpath in sorted(d for d in PROBLEMS_DIR.iterdir() if d.is_dir()):
            ds = dpath.name
            for rec in read_shards(dpath):
                is_eval, _ = is_eval_record(rec)
                if is_eval:
                    continue
                stats["train_candidates"] += 1

                ans = rec.get("answer") or {}
                sols = rec.get("solutions") or []
                has_verifiable_answer = bool(ans.get("value") or ans.get("letter"))
                has_solution = bool(sols)
                if not (has_verifiable_answer or has_solution):
                    stats["dropped_unverifiable"] += 1
                    continue

                stmt = rec.get("statement") or ""
                if _digest(norm_key(stmt)) in eval_exact:
                    stats["dropped_exact_collision"] += 1
                    decontam_by_dataset[ds] += 1
                    continue

                shingles = _characteristic_shingle_hashes(stmt)
                if len(shingles) >= 3 and sum(1 for sh in shingles if sh in eval_shingles) >= 3:
                    stats["dropped_near_duplicate_leak"] += 1
                    decontam_by_dataset[ds] += 1
                    continue

                stats["train_kept"] += 1
                train_by_dataset[ds] += 1
                if train_fh is not None:
                    train_fh.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
    finally:
        if eval_fh is not None:
            eval_fh.close()
        if train_fh is not None:
            train_fh.close()

    report = {
        "eval_total": stats["eval_total"],
        "eval_by_benchmark": dict(sorted(eval_by_benchmark.items(), key=lambda kv: -kv[1])),
        "train_candidates": stats["train_candidates"],
        "train_kept": stats["train_kept"],
        "dropped_exact_collision": stats["dropped_exact_collision"],
        "dropped_near_duplicate_leak": stats["dropped_near_duplicate_leak"],
        "dropped_unverifiable": stats["dropped_unverifiable"],
        "decontaminated_by_dataset": dict(sorted(decontam_by_dataset.items(), key=lambda kv: -kv[1])),
        "train_by_dataset": dict(sorted(train_by_dataset.items(), key=lambda kv: -kv[1])),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    if not args.stats_only:
        (out_dir / "REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
