"""LaTeX text normalization for imported problem records."""

import re

_DISPLAY_RE = re.compile(r"(?<!\\)\$\$(.+?)(?<!\\)\$\$", re.DOTALL)
_INLINE_RE = re.compile(r"(?<!\\)\$(?!\s)([^$]+?)(?<![\s\\])\$", re.DOTALL)
_BLANK_RUN_RE = re.compile(r"\n{3,}")

_BOILERPLATE_PATTERNS = [
    re.compile(r"^imported content\b.*\breview pending\b", re.IGNORECASE),
    re.compile(r"^check your\b.*\banswer\b\.?\s*$", re.IGNORECASE),
]


def normalize_latex(text: str) -> str:
    """Convert $...$/$$...$$ delimiters to \\(...\\)/\\[...\\].

    Escaped dollars (\\$) and existing \\(...\\) / \\[...\\] are left alone.
    Also replaces non-breaking spaces and collapses 3+ newlines to 2.
    """
    if not text:
        return text
    text = text.replace("\u00a0", " ")
    text = _DISPLAY_RE.sub(lambda m: "\\[" + m.group(1) + "\\]", text)
    text = _INLINE_RE.sub(lambda m: "\\(" + m.group(1) + "\\)", text)
    text = _BLANK_RUN_RE.sub("\n\n", text)
    return text


def strip_boilerplate(text: str) -> str:
    """Remove trailing junk lines (import notices, 'Check your answer' lines)."""
    if not text:
        return text
    lines = text.split("\n")
    while lines:
        stripped = lines[-1].strip()
        if not stripped:
            lines.pop()
            continue
        if any(p.search(stripped) for p in _BOILERPLATE_PATTERNS):
            lines.pop()
            continue
        break
    return "\n".join(lines)
