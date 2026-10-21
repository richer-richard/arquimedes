"""Where a checkout and an installed copy keep the corpus."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def user_data_dir() -> Path:
    """Per-user corpus directory, outside the Python environment uvx throws away."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "arquimedes"


def looks_like_root(path: Path) -> bool:
    return (path / "data" / "index.json").is_file() or (path / "problems").is_dir()
