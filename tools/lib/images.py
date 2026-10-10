"""Content-addressed image storage."""

import hashlib
from pathlib import Path

_EXT_ALIASES = {
    ".svg": ".svg",
    ".png": ".png",
    ".jpg": ".jpg",
    ".jpeg": ".jpg",
    ".gif": ".gif",
}


def save_image(data_bytes: bytes, ext: str, images_dir) -> str:
    """Store image bytes under images_dir keyed by sha256; returns filename."""
    ext = ext.lower()
    if not ext.startswith("."):
        ext = "." + ext
    if ext not in _EXT_ALIASES:
        raise ValueError(f"unsupported image extension: {ext!r}")
    ext = _EXT_ALIASES[ext]
    digest = hashlib.sha256(data_bytes).hexdigest()
    filename = digest + ext
    path = Path(images_dir) / filename
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data_bytes)
    return filename
