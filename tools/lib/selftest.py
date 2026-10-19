"""Sanity self-test for tools/lib: run with .venv/bin/python tools/lib/selftest.py"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.lib.schema import make_id, validate_record
from tools.lib.latex import normalize_latex, strip_boilerplate
from tools.lib.classify import classify_category, classify_record, map_known_subject
from tools.lib.difficulty import normalize_record_hygiene
from tools.lib.shards import write_shards, read_shards, norm_key
from tools.lib.images import save_image

failures = []


def check(name, fn):
    try:
        fn()
        print(f"PASS {name}")
    except Exception as exc:
        failures.append(name)
        print(f"FAIL {name}: {exc}")


def test_latex():
    got = normalize_latex("Let $x^2$ and $$y=1$$ cost \\$5")
    want = "Let \\(x^2\\) and \\[y=1\\] cost \\$5"
    assert got == want, f"{got!r} != {want!r}"
    assert normalize_latex("already \\(x\\) and \\[y\\]") == "already \\(x\\) and \\[y\\]"
    assert normalize_latex("a b") == "a b"
    assert normalize_latex("a\n\n\n\nb") == "a\n\nb"
    dirty = ("What is $1+1$?\n\nCheck your AIME answer.\n"
             "Imported content · review pending. This record has not yet been "
             "independently checked in the course library.")
    assert strip_boilerplate(dirty) == "What is \\(1+1\\)?" or \
        strip_boilerplate(dirty) == "What is $1+1$?"
    assert strip_boilerplate("symbols αβγ ∑ ∫ π survive") == "symbols αβγ ∑ ∫ π survive"


def test_classify():
    cases = [
        ("In triangle ABC, the bisector of angle A meets BC at D. The perimeter of the triangle is 20.", "geometry"),
        ("Two dice are rolled. What is the probability that the sum of the faces is 7?", "probability"),
        ("Find the number of positive integers n less than 1000 such that n is divisible by 6 and leaves a remainder of 1 when divided by 7.", "number-theory"),
        ("Let f(x) = x^2 - 3x + 2. Find the sum of the roots of the polynomial f(x).", "algebra"),
        ("In how many ways can a committee of 3 be chosen from 10 people?", "combinatorics"),
    ]
    for statement, want in cases:
        got = classify_category(statement)
        assert got == want, f"{statement[:40]!r}: {got} != {want}"
    assert map_known_subject("Counting & Probability") == "combinatorics"
    assert map_known_subject("Prealgebra") == "arithmetic"
    assert map_known_subject("Calculus") == "algebra"
    assert map_known_subject("Mathematics -> Geometry -> Plane Geometry -> Angles") == "geometry"
    assert map_known_subject("Mathematics -> Applied Mathematics -> Statistics -> Probability -> Other") == "probability"
    assert map_known_subject("Mathematics -> Applied Mathematics -> Math Word Problems") == "arithmetic"
    assert map_known_subject("olympiads") is None
    assert map_known_subject("nonsense") is None
    assert classify_category(r"Compute \(\log_2 8 + \sin \theta\).") == "algebra"
    assert classify_category(r"In \(\triangle ABC\), \(\angle A = 90^\circ\).") == "geometry"
    assert classify_record("Find x.", tags=["orca_math"]) == "arithmetic"


def test_norm_key():
    assert norm_key("Let  $x$ be") == norm_key("let x be")
    assert norm_key("\\left\\{a\\,b\\right\\}") == norm_key("{a b}")


def test_schema():
    rec = {
        "id": make_id("numina", 42),
        "title": "",
        "category": "geometry",
        "subjects": ["geometry"],
        "concepts": [],
        "source": {"dataset": "numina", "collection": None, "year": None,
                   "number": None, "url": None, "tags": ["olympiads"]},
        "difficulty": {"course": None, "source": None, "mohs": None,
                       "note": "MATH Level 5"},
        "estimatedMinutes": None,
        "statement": "In triangle \\(ABC\\), \\(AB = AC\\).",
        "answerChoices": [{"label": "A", "text": "\\(1\\)"}],
        "answer": {"letter": "a", "value": None},
        "solutions": [{"id": "sol.numina-000042.0", "kind": "answer-only",
                       "text": "\\(1\\)", "hints": [], "images": []}],
        "images": {"statement": [], "solutions": []},
    }
    assert rec["id"] == "prob.numina-000042"
    validate_record(rec)
    bad = dict(rec, category="geo")
    try:
        validate_record(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("bad category accepted")


def test_hygiene():
    rec = {
        "title": "APMO 1989 Problem_1",
        "category": "algebra",
        "source": {"dataset": "aops", "collection": "APMO", "number": "Problem_1", "tags": []},
        "difficulty": {"course": None, "source": None, "mohs": None, "note": None},
        "statement": "Find x.",
        "answer": {"letter": None, "value": None},
    }
    normalize_record_hygiene(rec)
    assert rec["title"] == "APMO 1989 Problem 1", rec["title"]
    assert rec["source"]["number"] == "1", rec["source"]["number"]
    for note in ("MATH Level ?", "deepmath -1"):
        rec = {"category": "algebra", "statement": "Find x.", "source": {"dataset": "math"},
               "difficulty": {"note": note}}
        normalize_record_hygiene(rec)
        assert rec["difficulty"]["note"] is None, rec["difficulty"]
        assert 1.0 <= rec["difficulty"]["mohs"] <= 10.0


def test_shards_and_images():
    with tempfile.TemporaryDirectory() as tmp:
        recs = [{"id": f"prob.t-{i:06d}", "statement": f"s{i}"} for i in range(25)]
        out = Path(tmp) / "t"
        paths = write_shards(iter(recs), out, max_records=10)
        assert [p.name for p in paths] == [
            "shard-00000.jsonl.gz", "shard-00001.jsonl.gz", "shard-00002.jsonl.gz"]
        back = list(read_shards(out))
        assert back == recs, "shard roundtrip mismatch"
        assert len(list(read_shards(paths[0]))) == 10
        assert len(list(read_shards(str(out / "shard-*.jsonl.gz")))) == 25

        img_dir = Path(tmp) / "images"
        name1 = save_image(b"<svg></svg>", ".svg", img_dir)
        name2 = save_image(b"<svg></svg>", "svg", img_dir)
        assert name1 == name2 and name1.endswith(".svg")
        assert len(list(img_dir.iterdir())) == 1
        assert save_image(b"x", ".JPEG", img_dir).endswith(".jpg")


check("latex", test_latex)
check("classify", test_classify)
check("norm_key", test_norm_key)
check("schema", test_schema)
check("hygiene", test_hygiene)
check("shards_and_images", test_shards_and_images)

print("ALL PASS" if not failures else f"{len(failures)} FAILURES: {failures}")
sys.exit(1 if failures else 0)
