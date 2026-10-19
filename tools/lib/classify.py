"""Heuristic category classification and known-subject mapping."""

import re

_CATEGORY_RULES = [
    ("probability", re.compile(
        r"\b(probabilit|expected value|expectation|dice|a die\b|fair die|six-sided die|"
        r"coin flip|coin toss|flipping a coin|tossing a coin|fair coin|"
        r"random(?:ly)?\b|at random|chance of|drawn? .*random|selected at random|"
        r"chosen at random|picked at random|independent events?|mutually exclusive|"
        r"conditional probability|bayes|markov|random variable|normal distribution|"
        r"binomial distribution|poisson|hypergeometric|bernoulli|standard deviation|"
        r"variance of)\b|"
        r"P\s*\(\s*[A-Z]\s*(?:\\cap|\\cup|\\mid|\|)", re.I)),
    ("logic-foundations", re.compile(
        r"\b(truth table|truth value|propositions?|negation of|contrapositive|"
        r"converse of|inverse of the statement|logically equivalent|quantifiers?|"
        r"boolean|knights and knaves|liars? and truth|always tells the truth|always lies|"
        r"necessary and sufficient|sufficient but not necessary|necessary but not sufficient|"
        r"sufficient condition|necessary condition|set theory|venn diagram|power set|"
        r"empty set|disjoint sets?|subset of)\b|"
        r"\\(?:varnothing|emptyset)(?![a-zA-Z])|"
        r"[A-Z]\s*(?:\\cap|\\cup|\\subset|\\subseteq|\\setminus)\s*[A-Z]", re.I)),
    ("problem-solving-techniques", re.compile(
        r"\b(pigeonhole|invariant|monovariant|extremal principle|"
        r"without loss of generality|mathematical induction|by induction|"
        r"coloring argument|chessboard coloring|double counting)\b", re.I)),
    ("geometry", re.compile(
        r"\b(triangles?|circles?|angles?|polygons?|perimeter|area of|surface area|"
        r"volume of|tangent to|chord|secant|rectangles?|"
        r"(?<!perfect )squares?\b(?!\s*(?:root|of\b))|"
        r"quadrilaterals?|pentagons?|hexagons?|heptagons?|octagons?|decagons?|dodecagons?|"
        r"regular polygon|cubes?|spheres?|cones?|cylinders?|prisms?|pyramids?|"
        r"tetrahedr(?:on|a)|octahedr(?:on|a)|icosahedr(?:on|a)|dodecahedr(?:on|a)|"
        r"polyhedr(?:on|a)|parallelepipeds?|radius|radii|diameter|circumference|"
        r"circumcircle|incircle|excircle|nine-point circle|orthocenter|centroid|"
        r"circumcenter|incenter|excenter|hypotenuse|isosceles|equilateral|scalene|"
        r"collinear|concyclic|concurrent|parallelograms?|rhomb(?:us|i)|trapezoids?|"
        r"trapezium|vertices of|vertex of|inscribed|circumscribed|side length|"
        r"midpoints?\b|bisectors?\b|perpendicular|parallel to|parallel lines?|"
        r"line segments?\b|coplanar|dihedral angle|cross-section|hemisphere|frustum|"
        r"annulus|sector of|arc length|coordinate plane|cartesian plane|"
        r"distance between|focus of|foci of|directrix|eccentricity|"
        r"ellipses?\b|hyperbolas?\b|conic sections?\b|trigonometr|law of sines|"
        r"law of cosines|heron's formula|ptolemy|menelaus|ceva|radical axis|"
        r"power of a point|homothety|euler line|reflection across|rotated by|rotation of)\b|"
        r"\\(?:triangle|angle|measuredangle|perp|parallel|odot)(?![a-zA-Z])|"
        r"\\(?:overrightarrow|overline)\s*\{[A-Z]{2,}\}|"
        r"\d+\s*\^\s*\{?\s*\\circ\s*\}?", re.I)),
    ("combinatorics", re.compile(
        r"\b(how many ways|in how many|number of ways|committee|arrangements?|"
        r"permutations?|combinations?|choose|selection|seated|sit around|"
        r"arrange|deck of cards|handshakes?|tournament|round-robin|"
        r"number of (?:orderings|subsets|committees|arrangements|ways|paths|strings|"
        r"words|sequences|configurations|colorings|tilings|graphs|trees|bijections|"
        r"triples|pairs|tuples|solutions)|"
        r"distinct (?:arrangements?|orderings?|sequences? of)|"
        r"binomial coefficient|stars and bars|inclusion-exclusion|generating function|"
        r"catalan|fibonacci|stirling|derangements?|recurrence relation|graph theory|"
        r"bipartite|connected graph|planar graph|spanning tree|chromatic|hamiltonian|"
        r"eulerian|chessboard|winning strategy|two-player game|alternately|takes? turns?|"
        r"grid of points)\b|"
        r"\d+\s*(?:\\times|x)\s*\d+\s*(?:grid|board|table|squares|cells)|"
        r"\\(?:binom|dbinom|tbinom)\s*\{|"
        r"\\mathrm\{C\}_\s*\{?\d+", re.I)),
    ("number-theory", re.compile(
        r"\b(primes?\b|primality|composite numbers?|divisible|divisibility|divisors?|"
        r"factors? of|number of factors|prime factor|greatest common divisor|gcd\b|lcm\b|"
        r"least common multiple|remainder|modulo|modular|congruent|congruence|"
        r"diophantine|integer solutions?|positive integers?|non-negative integers?|"
        r"nonnegative integers?|all integers|three integers|two integers|four integers|"
        r"pair of integers|triple of integers|is an integer|are integers|integer values?|"
        r"integers\b|integer\b|natural numbers?|"
        r"digits? (?:of|sum)|sum of (?:the )?digits|units digit|last digit|"
        r"last two digits|hundreds digit|tens digit|base-\d+|in base \d+|in base [a-z]\b|"
        r"binary representation|decimal representation|perfect (?:square|cube|power|number)|"
        r"relatively prime|coprime|totient|euler's phi|fermat's little|wilson's theorem|"
        r"chinese remainder|quadratic residue|legendre symbol|floor function|ceiling function|"
        r"multiple of \d+|multiples of \d+|even integer|odd integer|even number|odd number|"
        r"consecutive integers|consecutive odd|consecutive even|factorial)\b|"
        r"\\(?:pmod|bmod|equiv|lfloor|lceil)(?![a-zA-Z])|"
        r"\d+\s*!\s*(?:\+|\-|=|\\cdot|\\times)", re.I)),
    ("algebra", re.compile(
        r"\b(polynomials?|equations?|functional equation|functions?|domain of|range of|"
        r"inverse function|monotonic|strictly increasing|strictly decreasing|"
        r"even function|odd function|periodic function|sequences?|inequality|inequalities|"
        r"logarithms?|complex numbers?|imaginary part|real part|conjugate|"
        r"roots? of|zeros? of|quadratic|cubic|quartic|monic|solve for|"
        r"f\s*\(\s*[xntabk]\s*\)|g\s*\(\s*[xntabk]\s*\)|P\s*\(\s*x\s*\)|"
        r"arithmetic (?:sequence|progression|series)|"
        r"geometric (?:sequence|progression|series)|common difference|common ratio|"
        r"harmonic|sum of the series|infinite series|converges?|diverges?|limit of|"
        r"differentiable|continuous function|derivative|integral|antiderivative|"
        r"critical points?|inflection|taylor series|maclaurin|power series|"
        r"differential equation|eigenvalues?|eigenvectors?|determinant|matrices|matrix|"
        r"invertible|transpose|trace of|vector space|linear transformation|rank of|"
        r"systems? of .*equations?|slope|y-intercept|x-intercept|parabola|"
        r"exponents?|exponential|radicals?|absolute value|factorize|factoring|"
        r"simplify|expand|real numbers?|positive reals?|non-negative reals?|"
        r"am-gm|cauchy-schwarz|holder's|jensen's|chebyshev|vieta|discriminant|"
        r"completing the square|binomial theorem|binomial expansion|"
        r"minimum value|maximum value|extremum|supremum|infimum|unknown variable)\b|"
        r"\\(?:log|ln|lim|int|iint|oint|sum|prod|det|sin|cos|tan|cot|sec|csc|"
        r"arcsin|arccos|arctan|sinh|cosh|tanh|sqrt|dfrac|tfrac|leq|geq|le|ge|neq)(?![a-zA-Z])|"
        r"\\begin\{(?:pmatrix|bmatrix|vmatrix|matrix|cases|aligned|align\*?)\}|"
        r"\\frac\s*\{[^}]*[a-zA-Z][^}]*\}\s*\{|"
        r"[a-zA-Z]\s*\^\s*\{?[2-9nmkx]\}?", re.I)),
    ("arithmetic", re.compile(
        r"\b(percent|percentage|ratio of|proportion|proportional|fractions?\b|"
        r"numerator|denominator|decimal|discount|simple interest|compound interest|"
        r"annual return|invested|profit|loss of|cost price|selling price|wholesale|retail|"
        r"average|arithmetic mean|mean of|median of|mode of|"
        r"how (?:much|many|long|far|old|fast|tall|heavy|more|less|fewer)|"
        r"dollars?|cents?|yuan|euros?|pounds?|loonie|dime|quarter|nickel|pennies|penny|"
        r"unit price|sales tax|tip of|markup|commission|salary|wage|"
        r"per hour|per minute|per second|per day|per week|per month|per year|"
        r"per kg|per gram|per liter|km/h|mph|m/s|miles per hour|kilometers per hour|"
        r"constant speed|constant rate|average speed|travelling|traveling|halfway|"
        r"number line|clock|years old|twice as old|older than|younger than|recipe|"
        r"cups of|gallons? of|liters? of|kilograms?|grams? of|ounces?|"
        r"value of|evaluate|compute|calculate|simplify)\b|"
        r"\d+\s*\\?%|"
        r"\\\$|\$\s*\d|"
        r"\\frac\s*\{\s*-?\d+\s*\}\s*\{\s*-?\d+\s*\}|"
        r"\d+\s*(?:\\times|\\div|\\cdot|\+|\-)\s*\d+", re.I)),
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
    "number_theory": "number-theory",
    "prealgebra": "arithmetic",
    "precalculus": "algebra",
    # OlympiadBench subfields / Omni-MATH / DeepMath / BigMath domains
    "combinatorics": "combinatorics",
    "calculus": "algebra",
    "integral calculus": "algebra",
    "differential calculus": "algebra",
    "multivariable calculus": "algebra",
    "multi-variable calculus": "algebra",
    "vector calculus": "algebra",
    "limits": "algebra",
    "limit": "algebra",
    "derivatives": "algebra",
    "partial derivatives": "algebra",
    "applications of derivatives": "algebra",
    "applications of integrals": "algebra",
    "techniques of integration": "algebra",
    "series": "algebra",
    "infinite series": "algebra",
    "optimization": "algebra",
    "differential equations": "algebra",
    "ordinary differential equations (odes)": "algebra",
    "partial differential equations (pdes)": "algebra",
    "linear algebra": "algebra",
    "matrices": "algebra",
    "matrix operations": "algebra",
    "determinants": "algebra",
    "linear transformations": "algebra",
    "vectors": "algebra",
    "vector algebra": "algebra",
    "abstract algebra": "algebra",
    "group theory": "algebra",
    "ring theory": "algebra",
    "field theory": "algebra",
    "functional equations": "algebra",
    "analysis": "algebra",
    "real analysis": "algebra",
    "complex analysis": "algebra",
    "convex analysis": "algebra",
    "equations and inequalities": "algebra",
    "algebraic expressions": "algebra",
    "polynomial operations": "algebra",
    "polynomials": "algebra",
    "polynomial equations": "algebra",
    "sequences and series": "algebra",
    "sequence and series": "algebra",
    "arithmetic sequences": "algebra",
    "geometric sequences": "algebra",
    "functions": "algebra",
    "function": "algebra",
    "function theory": "algebra",
    "piecewise functions": "algebra",
    "periodic functions": "algebra",
    "power functions": "algebra",
    "exponential functions": "algebra",
    "logarithmic functions": "algebra",
    "quadratic functions": "algebra",
    "quadratic equations": "algebra",
    "quadratic inequalities": "algebra",
    "linear equations": "algebra",
    "linear functions": "algebra",
    "simple equations": "algebra",
    "systems of equations": "algebra",
    "system of equations": "algebra",
    "systems of linear equations": "algebra",
    "nonlinear equations": "algebra",
    "rational expressions": "algebra",
    "rational functions": "algebra",
    "rational equations": "algebra",
    "exponents and powers": "algebra",
    "exponents and indices": "algebra",
    "exponents": "algebra",
    "exponentiation": "algebra",
    "absolute values": "algebra",
    "complex numbers": "algebra",
    "binomial theorem": "algebra",
    "binomial expansion": "algebra",
    "binomial expansions": "algebra",
    "inequalities": "algebra",
    # Probability & Statistics
    "probability": "probability",
    "geometric probability": "probability",
    "statistics": "probability",
    "mathematical statistics": "probability",
    "variance": "probability",
    "frequency distribution": "probability",
    "sampling methods": "probability",
    # Combinatorics & Discrete Math
    "discrete mathematics": "combinatorics",
    "counting methods": "combinatorics",
    "combinations": "combinatorics",
    "permutations": "combinatorics",
    "combinatorial methods": "combinatorics",
    "combinatorial problems": "combinatorics",
    "combinatorial algebra": "combinatorics",
    "graph theory": "combinatorics",
    "coloring": "combinatorics",
    "colorings": "combinatorics",
    "recurrence relations": "combinatorics",
    "sequences and recurrences": "combinatorics",
    "recursion and sequences": "combinatorics",
    "recursion": "combinatorics",
    "recursive functions": "combinatorics",
    "game theory": "combinatorics",
    "algorithms": "combinatorics",
    # Logic & Set Theory
    "logic": "logic-foundations",
    "propositions": "logic-foundations",
    "set theory": "logic-foundations",
    "sets": "logic-foundations",
    "set operations": "logic-foundations",
    "operations on sets": "logic-foundations",
    "basic set operations": "logic-foundations",
    "basic operations on sets": "logic-foundations",
    "subset relationships": "logic-foundations",
    "complement of sets": "logic-foundations",
    "intersection": "logic-foundations",
    # Geometry & Trigonometry
    "trigonometry": "geometry",
    "trigonometric functions": "geometry",
    "trigonometric equations": "geometry",
    "trigonometric inequalities": "geometry",
    "sine": "geometry",
    "cosine": "geometry",
    "tangent": "geometry",
    "solid geometry": "geometry",
    "plane geometry": "geometry",
    "analytic geometry": "geometry",
    "analytical geometry": "geometry",
    "coordinate geometry": "geometry",
    "differential geometry": "geometry",
    "non-euclidean geometry": "geometry",
    "hyperbolic geometry": "geometry",
    "spherical geometry": "geometry",
    "combinatorial geometry": "geometry",
    "vector geometry": "geometry",
    "polygonal geometry": "geometry",
    "circles": "geometry",
    "triangles": "geometry",
    "similar triangles": "geometry",
    "similarity": "geometry",
    "polygons": "geometry",
    "quadrilaterals": "geometry",
    "rectangles": "geometry",
    "angles": "geometry",
    "angle measures": "geometry",
    "angle conversion": "geometry",
    "dihedral angles": "geometry",
    "3d shapes": "geometry",
    "area": "geometry",
    "areas": "geometry",
    "surface area": "geometry",
    "volume": "geometry",
    "perimeter": "geometry",
    "lines": "geometry",
    "points and lines": "geometry",
    "curves": "geometry",
    "loci": "geometry",
    "conic sections": "geometry",
    "conics": "geometry",
    "parabolas": "geometry",
    "ellipses": "geometry",
    "triangulations": "geometry",
    "triangulation": "geometry",
    "manifolds": "geometry",
    "curvature": "geometry",
    "quadrants": "geometry",
    # Number Theory
    "prime numbers": "number-theory",
    "primality": "number-theory",
    "composite numbers": "number-theory",
    "greatest common divisors (gcd)": "number-theory",
    "least common multiples (lcm)": "number-theory",
    "gcd and lcm": "number-theory",
    "factorization": "number-theory",
    "divisors and factorization": "number-theory",
    "factors and multiples": "number-theory",
    "congruences": "number-theory",
    "modular arithmetic": "number-theory",
    "divisibility": "number-theory",
    "divisors": "number-theory",
    "divisor functions": "number-theory",
    "quadratic residues": "number-theory",
    "diophantine equations": "number-theory",
    "linear diophantine equations": "number-theory",
    "integers": "number-theory",
    "integer theory": "number-theory",
    "factorial": "number-theory",
    # Arithmetic & Word Problems
    "arithmetic": "arithmetic",
    "math word problems": "arithmetic",
    "mathematics word problems": "arithmetic",
    "fractions": "arithmetic",
    "decimals": "arithmetic",
    "ratios": "arithmetic",
    "rational numbers": "arithmetic",
    "gsm8k": "arithmetic",
    # Ambiguous or source-only tags (recognized, but resolved by heuristics)
    "other": None,
    "mathematics": None,
    "applied mathematics": None,
    "single-variable": None,
    "multi-variable": None,
    "amc_aime": None,
    "olympiads": None,
    "olympiads_ref": None,
    "cn_k12": None,
    "cn_contest": None,
    "synthetic": None,
    "synthetic_math": None,
    "orca_math": None,
    "metamath": None,
    "aops_forum": None,
    "math": None,
    "synthetic_amc": None,
    "big_math": None,
    "harp": None,
    "openmath": None,
    # OlympiadBench / Omni-MATH competition names are not categories
    "imo": None,
    "imo shortlist": None,
    "imo_sl": None,
    "cmc": None,
    "apmo": None,
}

_SPLIT_RE = re.compile(r"\s*(?:->|/)\s*")


def map_known_subject(tag) -> str | None:
    """Map a dataset-native subject/domain tag (or '->' path) to a category, or None."""
    if isinstance(tag, (list, tuple)):
        for item in tag:
            res = map_known_subject(item)
            if res:
                return res
        return None
    if not isinstance(tag, str) or not tag.strip():
        return None
    low = tag.strip().lower()
    direct = _SUBJECT_MAP.get(low)
    if direct:
        return direct
    if "->" in low or "/" in low:
        parts = [p.strip() for p in _SPLIT_RE.split(low) if p.strip()]
        # Scan right-to-left (most specific leaf first)
        for part in reversed(parts):
            mapped = _SUBJECT_MAP.get(part)
            if mapped:
                return mapped
    return None


def classify_record(statement: str, tags=None, solutions=None) -> str:
    """Classify a problem record using domain tags, statement, and solution fallback."""
    if tags:
        mapped = map_known_subject(tags)
        if mapped:
            return mapped
    cat = classify_category(statement)
    if cat != "uncategorized":
        return cat
    if solutions:
        for sol in solutions:
            text = sol.get("text") if isinstance(sol, dict) else str(sol)
            if text:
                cat = classify_category(text)
                if cat != "uncategorized":
                    return cat
    if tags:
        tag_set = {str(t).strip().lower() for t in (tags if isinstance(tags, (list, tuple)) else [tags])}
        if tag_set & {"orca_math", "gsm8k", "metamath"}:
            return "arithmetic"
        if tag_set & {"cn_k12", "synthetic_math", "synthetic", "amc_aime", "cn_contest", "olympiads", "aops_forum"}:
            return "algebra"
    return "uncategorized"
