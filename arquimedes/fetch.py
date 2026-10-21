"""Download the published corpus and build a lean SQLite index.

The git checkout already has the shards. An installed copy does not: PyPI
ships the program, and the corpus stays on Hugging Face. ``arquimedes fetch``
copies that corpus into the user data directory and indexes it.

``uvx`` uses a fresh environment on every run, so the corpus cannot live
inside the package install.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from arquimedes.paths import user_data_dir

HF_REPO = "richard01172000/arquimedes"
API_URL = f"https://huggingface.co/api/datasets/{HF_REPO}"
RESOLVE_URL = f"https://huggingface.co/datasets/{HF_REPO}/resolve/main/"
MARKER = Path("data") / "fetch.json"
# Lean SQLite is about 0.8 GB. Leave room for the build.
SQLITE_HEADROOM = 2 * 1024 ** 3
USER_AGENT = "arquimedes-fetch"


def wanted(name: str) -> bool:
    """Files the installed corpus needs. The dataset card is not one of them."""
    if name in {"README.md", ".gitattributes"} or name.endswith("/"):
        return False
    return name == "rights.json" or name.startswith(("problems/", "images/"))


def select_files(siblings: list[dict]) -> list[dict]:
    files = []
    for item in siblings:
        name = item.get("rfilename") or ""
        if wanted(name):
            files.append({"rfilename": name, "size": item.get("size")})
    if not any(item["rfilename"].startswith("problems/") and item["rfilename"].endswith(".jsonl.gz") for item in files):
        raise SystemExit("Hugging Face dataset listed no problem shards")
    return files


def list_remote_files(url: str = API_URL) -> list[dict]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    return select_files(payload.get("siblings") or [])


def _download(url: str, dest: Path, expected: int | None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_name(dest.name + ".partial")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, open(temporary, "wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    except urllib.error.URLError as exc:
        temporary.unlink(missing_ok=True)
        raise SystemExit(f"download failed for {dest.name}: {exc}") from exc
    size = temporary.stat().st_size
    if expected is not None and size != expected:
        temporary.unlink(missing_ok=True)
        raise SystemExit(f"{dest.name} is {size} bytes, expected {expected}")
    temporary.replace(dest)


def _free_bytes(root: Path) -> int:
    probe = root if root.exists() else root.parent
    probe.mkdir(parents=True, exist_ok=True)
    return shutil.disk_usage(probe).free


def _marker(root: Path) -> Path:
    return root / MARKER


def _ready(root: Path) -> bool:
    database = root / "data" / "problems.sqlite"
    return _marker(root).is_file() and database.is_file() and database.stat().st_size > 0


def fetch(root: Path, *, force: bool = False, files: list[dict] | None = None, base_url: str | None = None) -> int:
    """Download into ``root`` and build a lean index. Return a process status."""
    root = Path(root).expanduser().resolve()
    if _ready(root) and not force:
        print(f"Corpus already installed at {root}")
        return 0

    files = list_remote_files() if files is None else select_files(files)
    base = base_url or RESOLVE_URL
    if not base.endswith("/"):
        base += "/"

    remaining = 0
    for item in files:
        dest = root / item["rfilename"]
        size = item.get("size") or 0
        already = dest.is_file() and (item.get("size") is None or dest.stat().st_size == item["size"])
        if already and not force:
            continue
        remaining += size
    corpus_bytes = sum((item.get("size") or 0) for item in files)
    index_room = SQLITE_HEADROOM if corpus_bytes > 100 * 1024 ** 2 else 64 * 1024 ** 2
    need = remaining + index_room
    free = _free_bytes(root)
    if free < need:
        raise SystemExit(
            f"Need about {need / 1024 ** 3:.1f} GB free for the corpus and its index. "
            f"{free / 1024 ** 3:.1f} GB is free."
        )

    for index, item in enumerate(files, 1):
        name = item["rfilename"]
        dest = root / name
        size = item.get("size")
        if not force and dest.is_file() and (size is None or dest.stat().st_size == size):
            continue
        print(f"[{index}/{len(files)}] {name}", flush=True)
        _download(base + urllib.parse.quote(name), dest, size)

    script = Path(__file__).resolve().parent.parent / "tools" / "build_database.py"
    print("Building the lean index. Search reads this file; solutions stay in the shards.", flush=True)
    completed = subprocess.run(
        [sys.executable, str(script), "--lean", "--root", str(root)],
        check=False,
    )
    if completed.returncode != 0:
        return completed.returncode

    _marker(root).write_text(
        json.dumps(
            {
                "source": f"https://huggingface.co/datasets/{HF_REPO}",
                "files": len(files),
                "index": "lean",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Corpus ready at {root}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="arquimedes fetch",
        description="Download the Arquimedes corpus and build a lean SQLite index.",
    )
    parser.add_argument("--root", type=Path, help="storage directory (default: the user data directory)")
    parser.add_argument("--force", action="store_true", help="download and build again")
    args = parser.parse_args(argv)
    return fetch(args.root or user_data_dir(), force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
