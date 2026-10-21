#!/usr/bin/env python
"""Build a Hugging Face copy that keeps every problem and stamps its copyright.

The git shards are not modified. Each published record gains a ``rights``
object from data/rights.json. The dataset card uses license ``other`` because
the corpus is mixed.

    uv run python tools/export_hf.py --check
    uv run python tools/export_hf.py --out /tmp/arquimedes-hf
    hf upload richard01172000/arquimedes /tmp/arquimedes-hf . --repo-type dataset

``--check`` only counts parts. It writes nothing.
"""

import argparse
import gzip
import io
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.lib.rights import CATALOG_PATH, load_catalog, stamp
from tools.lib.shards import read_shards

ROOT = Path(__file__).resolve().parents[1]
PROBLEMS = ROOT / "problems"
IMAGES = ROOT / "images"
DATASETS = (
    "core", "aops", "cemc", "olympiadbench", "omnimath",
    "math", "deepmath", "numina", "bigmath",
)


def iter_records():
    for dataset in DATASETS:
        yield from read_shards(PROBLEMS / dataset)


def check(catalog):
    counts = Counter()
    uses = Counter()
    total = 0
    for rec in iter_records():
        rights = stamp(rec, catalog)["rights"]
        counts[rights["part"]] += 1
        uses[rights["use"]] += 1
        total += 1
    print(f"{total} problems")
    for use, n in uses.most_common():
        print(f"  {use}: {n}")
    print("parts:")
    for part, n in counts.most_common():
        entry = catalog["parts"][part]
        dist = entry["distribution"] or "notice only"
        print(f"  {n:8}  {part}  {dist}  {entry['holder']}")
    missing = set(catalog["parts"]) - set(counts)
    if missing:
        raise SystemExit(f"catalog parts with no records: {sorted(missing)}")
    return total


def dataset_card(catalog):
    lines = [
        "---",
        "license: other",
        "language:",
        "- en",
        "pretty_name: Arquimedes",
        "size_categories:",
        "- 1M<n<10M",
        "tags:",
        "- math",
        "- mathematics",
        "task_categories:",
        "- question-answering",
        "configs:",
        "- config_name: default",
        "  data_files:",
        "  - split: train",
        "    path: problems/*/*.jsonl.gz",
        "---",
        "",
        "# Arquimedes",
        "",
        "1,038,963 competition and benchmark math problems in one schema.",
        "Every record keeps its text. `rights` names the holder and the license",
        "the distributor attached. `distribution` is null when no open license",
        "was found. This stamp does not create a new grant.",
        "",
        "Code for the tools that built the corpus is MIT. The Mohs value is a",
        "calibration produced for this project, not a measurement from the source.",
        "Project page: https://github.com/richer-richard/arquimedes",
        "",
        "Rows with `rights.use` of `notice-only` are the contest problems this",
        "project collected itself (`core` and `aops`). Rows with `noncommercial`",
        "are CEMC, CC BY-NC 4.0. Every other row is passed through from a dataset",
        "already published under Apache 2.0 or MIT, and the underlying holder is",
        "named on the row.",
        "",
        "Drop `notice-only` and `noncommercial` to leave those 11,748 rows out.",
        "Nothing is dropped in this copy.",
        "",
        "| part | problems are described as | distribution | use |",
        "|---|---|---|---|",
    ]
    for part, entry in catalog["parts"].items():
        dist = entry["distribution"] or "none"
        notice = entry["notice"].replace("|", "\\|")
        lines.append(f"| `{part}` | {notice} | {dist} | {entry['use']} |")
    lines.append("")
    lines.append("Full wording also lives in `rights.json`.")
    lines.append("")
    return "\n".join(lines)


def write_shard(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as raw:
        gz = gzip.GzipFile(filename=path.name, mode="wb", fileobj=raw, mtime=0)
        with io.TextIOWrapper(gz, encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")))
                fh.write("\n")


def export(out, catalog):
    out = Path(out)
    if out.exists():
        raise SystemExit(f"{out} already exists")
    out.mkdir(parents=True)
    (out / "README.md").write_text(dataset_card(catalog), encoding="utf-8")
    shutil.copyfile(CATALOG_PATH, out / "rights.json")
    if IMAGES.is_dir():
        shutil.copytree(IMAGES, out / "images")
    total = 0
    for dataset in DATASETS:
        src = PROBLEMS / dataset
        for path in sorted(src.glob("shard-*.jsonl.gz")):
            records = [stamp(rec, catalog) for rec in read_shards(path)]
            write_shard(out / "problems" / dataset / path.name, records)
            total += len(records)
            print(f"{dataset}/{path.name}: {len(records)}", flush=True)
    print(f"wrote {total} problems to {out}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Stamp rights and build a Hugging Face dataset tree.")
    parser.add_argument("--check", action="store_true", help="count parts, write nothing")
    parser.add_argument("--out", help="directory to write; must not already exist")
    parser.add_argument("--upload", action="store_true", help="hf upload --out after writing it")
    parser.add_argument("--repo", default="richard01172000/arquimedes")
    args = parser.parse_args(argv)
    catalog = load_catalog()
    if args.check:
        check(catalog)
        return 0
    if not args.out:
        parser.error("pass --check or --out")
    export(args.out, catalog)
    if args.upload:
        subprocess.run(
            ["hf", "upload", args.repo, args.out, ".", "--repo-type", "dataset"],
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
