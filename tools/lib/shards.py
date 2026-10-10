"""Sharded gzipped JSON Lines storage for problem records."""

import glob as globlib
import gzip
import json
import re
from pathlib import Path

_SHARD_GLOB = "shard-*.jsonl.gz"
_NORM_TOKEN_RE = re.compile(r"\\left|\\right|\\[,;!]|\\[{}]")
_WS_RE = re.compile(r"\s+")


def write_shards(records, out_dir, max_records=10000):
    """Write records to shard-NNNNN.jsonl.gz files; returns list of paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    fh = None
    count = 0
    try:
        for rec in records:
            if fh is None or count >= max_records:
                if fh is not None:
                    fh.close()
                path = out_dir / f"shard-{len(paths):05d}.jsonl.gz"
                fh = gzip.open(path, "wt", encoding="utf-8")
                paths.append(path)
                count = 0
            fh.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")
            count += 1
    finally:
        if fh is not None:
            fh.close()
    return paths


def _resolve_files(path_or_dir):
    p = Path(path_or_dir) if isinstance(path_or_dir, (str, Path)) else None
    if isinstance(path_or_dir, str) and any(c in path_or_dir for c in "*?["):
        return [Path(f) for f in sorted(globlib.glob(path_or_dir))]
    if p is not None and p.is_dir():
        return sorted(p.glob(_SHARD_GLOB))
    return [p]


def read_shards(path_or_dir):
    """Yield record dicts from a shard dir, glob pattern, or single file."""
    for path in _resolve_files(path_or_dir):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)


def norm_key(statement: str) -> str:
    """Normalization key for dedupe: case/whitespace/spacing-token insensitive."""
    s = statement.lower()
    s = _NORM_TOKEN_RE.sub("", s)
    s = s.replace("$", "").replace("{", "").replace("}", "")
    s = _WS_RE.sub("", s)
    return s
