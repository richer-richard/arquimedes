"""Heuristic category classification and known-subject mapping."""

import re

_CATEGORY_RULES = [
    ("probability", re.compile(
        r"\b(probabilit|expected value|expectation|dice|a die\b|coin flip|coin toss|"
        r"flipping a coin|tossing a coin|random(?:ly)?\b|at random|chance of|"
        r"drawn? .*random|selected at random)", re.I)),
    ("number-theory", re.compile(
        r"\b(primes?\b|divisible|divisor|gcd|greatest common divisor|lcm\b|"
        r"least common multiple|remainder|modulo|modular|congruent|"
        r"integer solutions?|positive integers?|digits? (of|sum)|perfect (square|cube)|"
        r"prime factor|relatively prime|coprime|number of factors)", re.I)),
    ("geometry", re.compile(
        r"\b(triangles?|circles?|angles?|polygons?|perimeter|area of|tangent to|"
        r"chord|rectangles?|squares?\b|quadrilateral|pentagon|hexagon|"
        r"cube|sphere|cone|cylinder|radius|diameter|circumcircle|incircle|"
        r"orthocenter|centroid|circumcenter|hypotenuse|isosceles|equilateral|"
        r"collinear|concyclic|parallelogram|trapezoid|pyramid|vertices of|"
        r"inscribed|circumscribed|volume of|side length)", re.I)),
    ("combinatorics", re.compile(
        r"\b(how many ways|in how many|committee|arrangements?|permutations?|"
        r"combinations?|choose|selection|seated|arrange|deck of cards|"
        r"handshakes?|tournament|number of (orderings|subsets|committees|"
        r"arrangements|ways)|distinct (arrangements?|orderings?|sequences? of))", re.I)),
    ("algebra", re.compile(
        r"\b(polynomials?|equations?|functions?|sequences?|inequality|inequalities|"
        r"logarithm|\\log|complex numbers?|quadratic|roots? of|solve for|"
        r"f\(x\)|g\(x\)|arithmetic (sequence|progression)|geometric (sequence|progression)|"
        r"sum of the series|infinite series|systems? of equations?|slope|parabola|"
        r"exponents?|radicals?|absolute value)", re.I)),
    ("arithmetic", re.compile(
        r"\b(percent|percentage|ratio of|proportion|fraction of|discount|"
        r"simple interest|average of|how (much|many) (money|dollars|cents)|"
        r"unit price|sales tax|tip of|markup)", re.I)),
    ("logic-foundations", re.compile(
        r"\b(truth table|truth value|propositions?|negation of|contrapositive|"
        r"converse of|logically equivalent|quantifiers?|boolean|"
        r"knights and knaves|liars? and truth)", re.I)),
    ("problem-solving-techniques", re.compile(
        r"\b(pigeonhole|invariant|monovariant|extremal principle|"
        r"without loss of generality|mathematical induction|"
        r"coloring argument|double counting)", re.I)),
]


def classify_category(statement: str) -> str:
    """Classify a problem statement into one of the 9 categories."""
    if not statement:
        return "uncategorized"
    for category, rule in _CATEGORY_RULES:
        if rule.search(statement):
            return category
    return "uncategorized"


_SUBJECT_MAP = {
    # MATH dataset subjects
    "algebra": "algebra",
    "counting & probability": "combinatorics",
    "counting and probability": "combinatorics",
    "geometry": "geometry",
    "intermediate algebra": "algebra",
    "number theory": "number-theory",
    "prealgebra": "arithmetic",
    "precalculus": "algebra",
    # OlympiadBench subfields / Omni-MATH domains
    "combinatorics": "combinatorics",
    "calculus": "algebra",
    "statistics": "algebra",
    "probability": "probability",
    "discrete mathematics": "combinatorics",
    "logic": "logic-foundations",
    "inequalities": "algebra",
    "trigonometry": "geometry",
    "solid geometry": "geometry",
    "plane geometry": "geometry",
    "analytic geometry": "geometry",
    # NuminaMath source tags (recognized, but no fixed category)
    "amc_aime": None,
    "olympiads": None,
    "cn_k12": None,
    "synthetic_math": None,
    "orca_math": None,
    "aops_forum": None,
    "gsm8k": "arithmetic",
    "math": None,
    "synthetic_amc": None,
    # OlympiadBench competition names are not categories
    "imo": None,
    "imo shortlist": None,
    "imo_sl": None,
    "cmc": None,
    "apmo": None,
}


def map_known_subject(tag) -> str | None:
    """Map a dataset-native subject/domain tag to a category, or None."""
    if not isinstance(tag, str) or not tag.strip():
        return None
    return _SUBJECT_MAP.get(tag.strip().lower())
