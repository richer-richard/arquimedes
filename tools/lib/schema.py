"""Canonical problem record v2 schema and validation."""

import re

CATEGORY_LIST = [
    "algebra",
    "arithmetic",
    "combinatorics",
    "geometry",
    "logic-foundations",
    "number-theory",
    "probability",
    "problem-solving-techniques",
    "uncategorized",
]

DATASET_LIST = [
    "core",
    "cemc",
    "numina",
    "deepmath",
    "bigmath",
    "openr1",
    "math",
    "omnimath",
    "olympiadbench",
    "aops",
]

SOLUTION_KINDS = {"proof-sketch", "strategy", "answer-only", "model-reasoning"}

_ID_RE = re.compile(r"^prob\.[a-z0-9][a-z0-9\-]*$")
_ID_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*$")


def make_id(dataset_slug: str, n: int) -> str:
    if not _ID_SLUG_RE.match(dataset_slug):
        raise ValueError(f"bad dataset slug: {dataset_slug!r}")
    return f"prob.{dataset_slug}-{n:06d}"


def _is_str(x):
    return isinstance(x, str)


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _err(msg):
    raise ValueError(msg)


def _check_str_list(value, field):
    if not isinstance(value, list) or not all(_is_str(v) for v in value):
        _err(f"{field}: must be a list of strings")


def validate_record(rec: dict) -> None:
    """Raise ValueError if rec violates the v2 problem record schema."""
    if not isinstance(rec, dict):
        _err("record must be a dict")

    rid = rec.get("id")
    if not _is_str(rid) or not _ID_RE.match(rid):
        _err(f"id: must match ^prob\\.[a-z0-9][a-z0-9\\-]*$, got {rid!r}")

    if not _is_str(rec.get("title")):
        _err("title: must be a string")

    category = rec.get("category")
    if category not in CATEGORY_LIST:
        _err(f"category: must be one of {CATEGORY_LIST}, got {category!r}")

    subjects = rec.get("subjects")
    _check_str_list(subjects, "subjects")
    if category != "uncategorized" and category not in subjects:
        _err(f"subjects: must contain category {category!r}")

    if not isinstance(rec.get("concepts"), list):
        _err("concepts: must be a list")

    source = rec.get("source")
    if not isinstance(source, dict):
        _err("source: must be an object")
    ds = source.get("dataset")
    if not _is_str(ds) or not _ID_SLUG_RE.match(ds):
        _err(f"source.dataset: must be a slug string, got {ds!r}")
    if not (source.get("collection") is None or _is_str(source.get("collection"))):
        _err("source.collection: must be a string or null")
    year = source.get("year")
    if not (year is None or (isinstance(year, int) and not isinstance(year, bool))):
        _err("source.year: must be an int or null")
    number = source.get("number")
    if not (number is None or (_is_str(number) and number and not number.isdigit())
            or (isinstance(number, int) and not isinstance(number, bool))):
        _err(f"source.number: must be an int, a non-numeric string, or null, got {number!r}")
    if not (source.get("url") is None or _is_str(source.get("url"))):
        _err("source.url: must be a string or null")
    _check_str_list(source.get("tags"), "source.tags")

    difficulty = rec.get("difficulty")
    if not isinstance(difficulty, dict):
        _err("difficulty: must be an object")
    for key in ("course", "source", "mohs"):
        v = difficulty.get(key)
        if not (v is None or _is_number(v)):
            _err(f"difficulty.{key}: must be a number or null")
    if not (difficulty.get("note") is None or _is_str(difficulty.get("note"))):
        _err("difficulty.note: must be a string or null")

    em = rec.get("estimatedMinutes")
    if not (em is None or _is_number(em)):
        _err("estimatedMinutes: must be a number or null")

    statement = rec.get("statement")
    if not _is_str(statement) or not statement.strip():
        _err("statement: must be a non-empty string")

    choices = rec.get("answerChoices")
    if not isinstance(choices, list):
        _err("answerChoices: must be a list")
    for ch in choices:
        if not isinstance(ch, dict):
            _err("answerChoices: entries must be objects")
        label = ch.get("label")
        if not (_is_str(label) and len(label) == 1 and label.isupper() and label.isalpha()):
            _err(f"answerChoices.label: must be an uppercase letter, got {label!r}")
        if not _is_str(ch.get("text")):
            _err("answerChoices.text: must be a string")

    answer = rec.get("answer")
    if not isinstance(answer, dict):
        _err("answer: must be an object")
    letter = answer.get("letter")
    if not (letter is None or (_is_str(letter) and len(letter) == 1 and "a" <= letter <= "z")):
        _err(f"answer.letter: must be a lowercase choice letter or null, got {letter!r}")
    if not (answer.get("value") is None or _is_str(answer.get("value"))):
        _err("answer.value: must be a string or null")

    solutions = rec.get("solutions")
    if not isinstance(solutions, list):
        _err("solutions: must be a list")
    for sol in solutions:
        if not isinstance(sol, dict):
            _err("solutions: entries must be objects")
        if not _is_str(sol.get("id")):
            _err("solutions.id: must be a string")
        if sol.get("kind") not in SOLUTION_KINDS:
            _err(f"solutions.kind: must be one of {sorted(SOLUTION_KINDS)}, got {sol.get('kind')!r}")
        if not _is_str(sol.get("text")):
            _err("solutions.text: must be a string")
        _check_str_list(sol.get("hints"), "solutions.hints")
        _check_str_list(sol.get("images"), "solutions.images")

    images = rec.get("images")
    if not isinstance(images, dict):
        _err("images: must be an object")
    _check_str_list(images.get("statement"), "images.statement")
    _check_str_list(images.get("solutions"), "images.solutions")
