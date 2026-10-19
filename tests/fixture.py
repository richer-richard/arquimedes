"""A five-problem corpus built three ways: full database, lean database, and shards only."""

from __future__ import annotations

import atexit
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.lib.schema import validate_record
from tools.lib.shards import write_shards

REPO = Path(__file__).resolve().parent.parent


def _record(pid, dataset, category, statement, *, title="", collection=None, year=None, number=None,
            mohs=5.0, note=None, choices=(), letter=None, value=None, solutions=(), statement_images=()):
    return {
        "id": pid,
        "title": title,
        "category": category,
        "subjects": [category],
        "concepts": [],
        "source": {"dataset": dataset, "collection": collection, "year": year, "number": number,
                   "url": None, "tags": []},
        "difficulty": {"course": None, "source": None, "mohs": mohs, "note": note},
        "estimatedMinutes": None,
        "statement": statement,
        "answerChoices": [{"label": label, "text": text} for label, text in choices],
        "answer": {"letter": letter, "value": value},
        "solutions": list(solutions),
        "images": {"statement": list(statement_images), "solutions": []},
    }


def _solution(sid, text, kind="proof-sketch", hints=()):
    return {"id": sid, "kind": kind, "text": text, "hints": list(hints), "images": []}


RECORDS = {
    "core": [
        _record("prob.aime-i-2020-p1", "core", "number-theory",
                r"Find the number of positive divisors of \(2020\).",
                title="2020 AIME I Problem 1", collection="AIME I", year=2020, number=1, mohs=5.0, value="12",
                solutions=[_solution("sol.aime-i-2020-p1.live", "Since \\(2020 = 2^2 \\cdot 5 \\cdot 101\\), there are \\(3 \\cdot 2 \\cdot 2 = 12\\).",
                                     hints=["Factor 2020.", "Count exponent choices."])]),
        _record("prob.amc-12a-2020-p2", "core", "geometry",
                "A square has side length 3. What is the area of the square?",
                title="2020 AMC 12A Problem 2", collection="AMC 12A", year=2020, number=2, mohs=2.0,
                choices=[("A", "6"), ("B", "8"), ("C", "9"), ("D", "12"), ("E", "16")], letter="c", value="9",
                solutions=[_solution("sol.amc-12a-2020-p2.live", "The area is \\(3^2 = 9\\).")],
                statement_images=["deadbeef"]),
        _record("prob.hmmt-feb-guts-2019-ph-4", "core", "combinatorics",
                "How many ways are there to choose 2 of 5 people?",
                title="2019 HMMT February Guts Problem H4", collection="HMMT February", year=2019, number="H4",
                mohs=4.0, value="10"),
    ],
    "aops": [
        _record("prob.aops-000000", "aops", "algebra",
                "Prove that the pigeonhole principle holds for 3 pigeons and 2 holes.",
                title="IMO Shortlist 2005 A1", collection="IMO Shortlist", year=2005, number="A1", mohs=7.0,
                solutions=[_solution("sol.aops-000000.0", "Two pigeons must share a hole.")]),
    ],
    "deepmath": [
        _record("prob.deepmath-000000", "deepmath", "algebra",
                r"Evaluate \(\lim_{x \to 0} \frac{\sin x}{x}\).", mohs=6.0, note="deepmath 6", value="1",
                solutions=[_solution(f"sol.deepmath-000000.r1-{i}", f"Trace {i}: the limit is 1.", kind="model-reasoning")
                           for i in (1, 2, 3)]),
    ],
}
ALL_IDS = [r["id"] for recs in RECORDS.values() for r in recs]

_ROOTS: dict[str, Path] = {}


def roots() -> dict[str, Path]:
    """{'full': root, 'lean': root, 'none': root}; built once per test run."""
    if _ROOTS:
        return _ROOTS
    tmp = Path(tempfile.mkdtemp(prefix="arquimedes-test-"))
    atexit.register(shutil.rmtree, tmp, ignore_errors=True)
    base = tmp / "full"
    for dataset, recs in RECORDS.items():
        for rec in recs:
            validate_record(rec)
        write_shards(iter(recs), base / "problems" / dataset)
    (base / "images").mkdir(parents=True)
    (base / "images" / "deadbeef.svg").write_text("<svg/>", encoding="utf-8")
    for name in ("lean", "none"):
        shutil.copytree(base, tmp / name)
    build = [sys.executable, str(REPO / "tools" / "build_database.py")]
    subprocess.run(build + ["--root", str(base)], check=True, capture_output=True)
    subprocess.run(build + ["--lean", "--root", str(tmp / "lean")], check=True, capture_output=True)
    # A checkout without a database still has the tracked data/index.json
    (tmp / "none" / "data").mkdir()
    shutil.copy(base / "data" / "index.json", tmp / "none" / "data" / "index.json")
    _ROOTS.update(full=base, lean=tmp / "lean", none=tmp / "none")
    return _ROOTS
