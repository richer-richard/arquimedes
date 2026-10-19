"""Unified Mohs difficulty scale (1.0 to 10.0) and record normalization helpers."""

import html
import re
from tools.lib.classify import classify_record

_MATH_LEVEL_MAP = {
    "MATH Level 1": 2.0,
    "MATH Level 2": 2.8,
    "MATH Level 3": 3.6,
    "MATH Level 4": 4.5,
    "MATH Level 5": 5.5,
}

_CEMC_BASE = {
    "CEMC Gauss (Grade 7)": 1.5,
    "CEMC Gauss (Grade 8)": 1.8,
    "CEMC Pascal (Grade 9)": 2.3,
    "CEMC Cayley (Grade 10)": 2.7,
    "CEMC Fermat (Grade 11)": 3.1,
}

_DEEPMATH_RE = re.compile(r"^deepmath\s+(-?[\d.]+)$")
_OMNIMATH_RE = re.compile(r"^omnimath\s+([\d.]+)$")
_LLAMA_RE = re.compile(r"^llama8b_solve_rate\s+([\d.]+)$")
_INT_RE = re.compile(r"(\d+)")
_PROOF_RE = re.compile(r"\b(prove that|show that|determine all|find all functions)\b", re.I)


def _clamp(val: float, lo: float = 1.0, hi: float = 10.0) -> float:
    return round(max(lo, min(hi, val)), 1)


def compute_mohs(rec: dict) -> float:
    """Compute a calibrated 1.0-10.0 Mohs difficulty rating for a v2 problem record."""
    src = rec.get("source") or {}
    diff = rec.get("difficulty") or {}
    ds = src.get("dataset") or ""
    coll = src.get("collection") or ""
    num = src.get("number")
    tags = src.get("tags") or []
    tag_set = {str(t).strip().lower() for t in tags}
    note = (diff.get("note") or "").strip()

    # 1. Core dataset: calibrated from difficulty.course (0..120)
    course = diff.get("course")
    if isinstance(course, (int, float)) and not isinstance(course, bool):
        return _clamp(1.0 + 0.075 * float(course))

    # 2. Explicit dataset notes: omnimath, deepmath, math, bigmath
    if note:
        if note in _MATH_LEVEL_MAP:
            return _MATH_LEVEL_MAP[note]
        m = _OMNIMATH_RE.match(note)
        if m:
            return _clamp(float(m.group(1)))
        m = _DEEPMATH_RE.match(note)
        if m:
            v = float(m.group(1))
            return _clamp(5.0 if v <= 0 else v)
        m = _LLAMA_RE.match(note)
        if m:
            r = max(0.0, min(1.0, float(m.group(1))))
            base = 2.0 + 5.5 * ((1.0 - r) ** 0.75)
            if "olympiads" in tag_set or "omnimath" in tag_set:
                base += 0.7
            elif "gsm8k" in tag_set or "orca_math" in tag_set:
                base -= 0.5
            return _clamp(base, 1.2, 9.5)

    # 3. CEMC contests (Grade 7-11, Problem 1-25)
    if ds == "cemc" or coll in _CEMC_BASE:
        base = _CEMC_BASE.get(coll, 2.3)
        pnum = int(num) if isinstance(num, int) or (isinstance(num, str) and num.isdigit()) else 12
        return _clamp(base + 0.09 * max(0, min(25, pnum) - 1), 1.2, 6.0)

    # 4. AoPS olympiads (IMO Shortlist, USAJMO, Canadian MO, APMO, Putnam)
    if ds == "aops":
        num_str = str(num or "")
        m_int = _INT_RE.search(num_str)
        idx = int(m_int.group(1)) if m_int else 2
        if coll == "IMO Shortlist":
            return _clamp(6.8 + 0.38 * max(0, min(8, idx) - 1), 6.8, 9.6)
        if coll == "Putnam":
            return _clamp(7.4 + 0.35 * max(0, min(6, idx) - 1), 7.4, 9.5)
        if coll == "APMO":
            return _clamp(7.0 + 0.40 * max(0, min(5, idx) - 1), 7.0, 8.8)
        # USAJMO, Canadian MO
        return _clamp(6.5 + 0.32 * max(0, min(6, idx) - 1), 6.5, 8.4)

    # 5. OlympiadBench
    if ds == "olympiadbench" or coll == "OlympiadBench":
        is_tp = any(t.startswith("TP_") for t in tags if isinstance(t, str))
        is_mm = any("_MM_" in t for t in tags if isinstance(t, str))
        base = 8.2 if is_tp else 7.6
        if is_mm:
            base += 0.3
        return _clamp(base, 7.0, 9.0)

    # 6. Numina & fallback tag/complexity calibration
    stmt = rec.get("statement") or ""
    sols = rec.get("solutions") or []
    sol_len = max((len(s.get("text") or "") for s in sols if isinstance(s, dict)), default=0)

    if "orca_math" in tag_set or "metamath" in tag_set or "gsm8k" in tag_set:
        base = 2.0
    elif "cn_k12" in tag_set:
        base = 3.8
    elif "synthetic_math" in tag_set or "synthetic" in tag_set:
        base = 4.5
    elif "amc_aime" in tag_set:
        base = 5.0
    elif "cn_contest" in tag_set or "aops_forum" in tag_set:
        base = 6.2
    elif "olympiads" in tag_set or "olympiads_ref" in tag_set:
        base = 7.4
    else:
        base = 4.5

    # Complexity modulation from solution length and proof nature
    if sol_len > 2200:
        base += 0.6
    elif sol_len > 1100:
        base += 0.3
    elif 0 < sol_len < 240:
        base -= 0.3
    if _PROOF_RE.search(stmt):
        base += 0.4

    return _clamp(base, 1.0, 9.5)


_SINGLE_LETTER_RE = re.compile(r"^[a-e]$", re.I)
_CHOICE_LETTER_RE = re.compile(r"^[a-z]$")
_HTML_ENTITY_RE = re.compile(r"&(?:lt|gt|amp|quot|nbsp|#\d+);")
_UNDERSCORE_PROB_RE = re.compile(r"\bProblem_(\w+)")
_UNDERSCORE_NUM_RE = re.compile(r"^Problem_(\w+)$")
_SUBSCRIPT_RE = re.compile(r"_\{(\w+)\}")
_MANGLED_SUBSCRIPT_RE = re.compile(r"\b([A-Z]) \{(\d+)\}")
_PLACEHOLDER_SOLUTION_RE = re.compile(r"^This problem needs a solution\b")
_PLACEHOLDER_ANSWER_RE = re.compile(r"^The problem provided does not contain a solution\b")


def strip_outer_math_delims(val: str | None) -> str | None:
    """Strip outer \\(...\\) or $...$ if they wrap the entire answer string."""
    if not val or not isinstance(val, str):
        return val
    s = val.strip()
    if s.startswith(r"\(") and s.endswith(r"\)"):
        inner = s[2:-2].strip()
        if r"\(" not in inner and r"\)" not in inner:
            return inner if inner else None
    if len(s) >= 2 and s.startswith("$") and s.endswith("$") and not s.startswith("$$"):
        inner = s[1:-1].strip()
        if "$" not in inner:
            return inner if inner else None
    return s


def normalize_record_hygiene(rec: dict) -> dict:
    """Apply in-place category, difficulty.mohs, subjects, title, and answer hygiene fixes."""
    src = rec.get("source") or {}
    diff = rec.setdefault("difficulty", {"course": None, "source": None, "mohs": None, "note": None})
    ans = rec.setdefault("answer", {"letter": None, "value": None})
    tags = src.get("tags") or []

    # 0. Drop scraped "this problem needs a solution" placeholders and the answer
    #    extracted from them; they are not solutions
    if rec.get("solutions"):
        rec["solutions"] = [s for s in rec["solutions"]
                            if not _PLACEHOLDER_SOLUTION_RE.match((s.get("text") or "").strip())]
    if isinstance(ans.get("value"), str) and _PLACEHOLDER_ANSWER_RE.match(ans["value"]):
        ans["value"] = None
    sols = rec.get("solutions") or []

    # 1. Unescape stray HTML entities in statement
    stmt = rec.get("statement") or ""
    if _HTML_ENTITY_RE.search(stmt):
        stmt = html.unescape(stmt).replace("\u00a0", " ")
        rec["statement"] = stmt

    # 2. Fix title underscores (e.g. 'APMO 1989 Problem_1' -> 'APMO 1989 Problem 1',
    #    'Problem H_{4}' -> 'Problem H4') and normalize source.number: an int when
    #    purely numeric, otherwise a plain string ('Problem_1' -> 1, 'H_{4}' -> 'H4')
    title = rec.get("title") or ""
    fixed = _MANGLED_SUBSCRIPT_RE.sub(r"\1\2", _SUBSCRIPT_RE.sub(r"\1", title))
    if "_" in fixed:
        fixed = _UNDERSCORE_PROB_RE.sub(r"Problem \1", fixed).replace("_", " ")
    if fixed != title:
        rec["title"] = fixed
    num = src.get("number")
    if isinstance(num, str):
        m = _UNDERSCORE_NUM_RE.match(num)
        num = _SUBSCRIPT_RE.sub(r"\1", m.group(1) if m else num).strip()
        src["number"] = int(num) if num.isdigit() else (num or None)

    # 3. Reclassify uncategorized records using upgraded classify_record
    cat = rec.get("category") or "uncategorized"
    if cat == "uncategorized":
        cat = classify_record(stmt, tags=tags, solutions=sols)
        rec["category"] = cat

    # 4. Normalize subjects array: never include "uncategorized", always include concrete category
    subs = [s for s in (rec.get("subjects") or []) if s and s != "uncategorized"]
    if cat != "uncategorized" and cat not in subs:
        subs.insert(0, cat)
    rec["subjects"] = subs

    # 5. Unknown-level placeholders from the source datasets mean "no label", not a level
    if diff.get("note") in ("MATH Level ?", "deepmath -1"):
        diff["note"] = None

    # 6. Populate unified difficulty.mohs (1.0 - 10.0)
    diff["mohs"] = compute_mohs(rec)

    # 7. Normalize answers
    letter = ans.get("letter")
    val = ans.get("value")
    choices = rec.get("answerChoices") or []

    # answer.letter only holds a multiple-choice label. Older core records put the
    # answer value there (AIME numerics, LaTeX, lowercased text); keep it in value.
    if letter and not _CHOICE_LETTER_RE.match(str(letter)):
        if val is None:
            val = str(letter).strip()
            ans["value"] = val
        ans["letter"] = letter = None

    # If MC problem has letter and answerChoices but value is None, populate from matching choice
    if choices and letter and _SINGLE_LETTER_RE.match(str(letter)) and val is None:
        target = str(letter).upper()
        for ch in choices:
            if isinstance(ch, dict) and ch.get("label") == target:
                val = ch.get("text")
                ans["value"] = val
                break

    if ans.get("value") is not None:
        ans["value"] = strip_outer_math_delims(ans["value"])

    return rec
