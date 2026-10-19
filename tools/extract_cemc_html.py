"""Extract multiple-choice problem records from CEMC contest HTML files.

CEMC publishes Pandoc-generated HTML versions of recent contests with raw
LaTeX preserved in \\(...\\) spans. For the multiple-choice families
(Gauss 7/8, Pascal, Cayley, Fermat) the structure is regular in spirit but
malformed in detail across years (split <li>s, <ol><body><ol> nestings), so
parsing goes through a small tolerant DOM and groups each problem list's
children into runs that start at an <li> and continue through non-<li>
siblings.

  contest:  <h2>Part A: ...</h2> then <ol> with one item per problem;
            answer choices live in <ol class="horizontal"> (5 x <li>)
  solution: <ol> with one <li> per problem ending in "Answer: (B)"

Problems containing <img> or <table> are skipped (not representable as
text). Every emitted record passes tools.lib.schema.validate_record.

Usage:
    .venv/bin/python tools/extract_cemc_html.py
"""

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.schema import validate_record  # noqa: E402
from lib.shards import write_shards  # noqa: E402
from lib.classify import classify_record  # noqa: E402
from lib.difficulty import normalize_record_hygiene  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CEMC_DIR = ROOT / "raw" / "official" / "cemc"
OUT_DIR = ROOT / "staging" / "official" / "cemc-mc"
DATASET = "cemc-mc"

CONTESTS = {
    "Gauss7": ("Gauss", "Grade 7"),
    "Gauss8": ("Gauss", "Grade 8"),
    "Pascal": ("Pascal", "Grade 9"),
    "Cayley": ("Cayley", "Grade 10"),
    "Fermat": ("Fermat", "Grade 11"),
}
LETTERS = "ABCDE"
VOID_TAGS = {"img", "br", "hr", "meta", "link", "input", "col", "base",
             "area", "embed", "source", "track", "wbr"}


# ------------------------------------------------------------- mini DOM

class Node:
    __slots__ = ("tag", "attrs", "children")

    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.children = []  # str | Node

    def text_content(self, exclude=None):
        out = []

        def walk(n):
            for c in n.children:
                if isinstance(c, str):
                    out.append(c)
                else:
                    if exclude and exclude(c):
                        continue
                    if c.tag == "br":
                        out.append("\n")
                    elif c.tag == "p":
                        out.append("\n\n")
                        walk(c)
                    else:
                        walk(c)
        walk(self)
        text = "".join(out)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)  # single newline -> space
        return text.strip()

    def find_all(self, tag):
        for c in self.children:
            if isinstance(c, Node):
                if c.tag == tag:
                    yield c
                yield from c.find_all(tag)

    def contains(self, tags):
        return any(True for _ in self.find_all_any(tags))

    def find_all_any(self, tags):
        for c in self.children:
            if isinstance(c, Node):
                if c.tag in tags:
                    yield c
                yield from c.find_all_any(tags)


class DOMBuilder(HTMLParser):
    # emulate browser auto-closing: a new <li> closes an open <li> in the
    # same list; block starts close an open <p>
    P_CLOSERS = {"p", "li", "div", "ol", "ul", "h1", "h2", "h3", "h4",
                 "table", "hr", "blockquote", "pre", "section"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            # close an open <li> belonging to the current list
            for i in range(len(self.stack) - 1, 0, -1):
                t = self.stack[i].tag
                if t in ("ol", "ul"):
                    break
                if t == "li":
                    del self.stack[i:]
                    break
        if tag in self.P_CLOSERS and self.stack[-1].tag == "p":
            self.stack.pop()
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, dict(attrs)))

    def handle_endtag(self, tag):
        # pop to the nearest matching open tag (tolerates misnesting)
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_dom(html):
    b = DOMBuilder()
    b.feed(html)
    return b.root


def ol_class(node):
    return node.attrs.get("class", "")


def iter_problem_ols(root):
    """Yield problem-list <ol> nodes in document order. A list qualifies when
    an <h2> containing 'Part' was seen and the <ol> has <li> children; nested
    part lists (2021-style, where later Parts nest inside Part A's <ol>) are
    found by recursing into yielded lists."""
    pending_part = False

    def walk(node):
        nonlocal pending_part
        for c in node.children:
            if isinstance(c, str):
                continue
            if c.tag == "h2":
                if "part" in c.text_content().lower():
                    pending_part = True
            elif c.tag == "ol":
                cls = ol_class(c)
                if "horizontal" in cls:
                    continue  # choices list, not a problem list
                has_li = any(isinstance(x, Node) and x.tag == "li"
                             for x in c.children)
                if pending_part and has_li and "nostyle" not in cls:
                    yield c
                    pending_part = False
                yield from walk(c)  # later Parts may nest inside this list
            else:
                yield from walk(c)
    yield from walk(root)


_BOUNDARY_TAGS = {"h1", "h2", "h3", "h4", "hr", "ul", "table"}


def item_runs(ol):
    """Group an <ol>'s children into items: each <li> starts an item, and
    following orphan content (<p>, text, choices <ol class=horizontal>)
    continues it; structural nodes (headings, rules, nested lists) are
    boundaries that belong to no item."""
    items = []
    for c in ol.children:
        if isinstance(c, Node) and c.tag == "li":
            items.append([c])
        elif isinstance(c, Node) and (
                c.tag in _BOUNDARY_TAGS
                or (c.tag == "ol" and "horizontal" not in ol_class(c))):
            continue
        elif items:
            items[-1].append(c)
    return items


def parse_problems(html):
    """Return [(number, statement, choices, usable)] with original numbering
    so solutions (which list every problem) stay aligned."""
    root = parse_dom(html)
    problems = []
    for ol in iter_problem_ols(root):
        for run in item_runs(ol):
            stmt_parts, choices, skip = [], [], False
            for node in run:
                if isinstance(node, str):
                    if node.strip():
                        stmt_parts.append(node.strip())
                    continue
                if node.contains({"img", "table"}):
                    skip = True
                for sub in node.find_all("ol"):
                    if "horizontal" in ol_class(sub):
                        choices = [li.text_content()
                                   for li in sub.children
                                   if isinstance(li, Node) and li.tag == "li"]
                stmt_parts.append(node.text_content(
                    exclude=lambda n: n.tag == "ol"
                    and "horizontal" in ol_class(n)))
            stmt = "\n\n".join(p for p in stmt_parts if p).strip()
            usable = bool(stmt) and not skip and len(choices) == 5
            problems.append((len(problems) + 1, stmt, choices, usable))
    return problems


def _run_text(run):
    return "\n\n".join(
        (n if isinstance(n, str) else n.text_content()) for n in run).strip()


ANS_RE = re.compile(r"Answer:\s*\(?([A-E])\)?", re.I)


def parse_solutions(html, heading=None):
    """Return [(solution_text, letter)]; heading e.g. 'Grade 7' selects the
    section of a combined Gauss solution file."""
    root = parse_dom(html)
    best = None
    for ol in root.find_all("ol"):
        cls = ol_class(ol)
        if "horizontal" in cls or "nostyle" in cls:
            continue
        items = item_runs(ol)
        texts = [_run_text(run) for run in items]
        n_ans = sum(1 for t in texts if ANS_RE.search(t))
        if n_ans >= 10:  # a solution list has ~25 items each ending Answer: (X)
            if best is None or n_ans > best[0]:
                best = (n_ans, texts)
    if best is None:
        return []
    out = []
    for text in best[1]:
        m = ANS_RE.search(text)
        letter = m.group(1).upper() if m else None
        if m:
            text = text[:m.start()].strip()
        if text:
            out.append((text, letter))
    return out


def split_gauss_grades(html):
    """Split a combined Gauss solution file into {grade: html-fragment} is
    not trivial on text; instead parse per-grade by locating the grade
    heading nodes and their following solution <ol>."""
    root = parse_dom(html)
    sections = {}

    def walk(node):
        for c in node.children:
            if isinstance(c, str):
                continue
            if c.tag == "h2":
                t = c.text_content().strip().lower()
                if t in ("grade 7", "grade 8"):
                    sections[t] = []
                    # the solution <ol> is a later sibling; mark and continue
                    walk.current = t
            elif c.tag == "ol" and getattr(walk, "current", None):
                cls = ol_class(c)
                if "horizontal" not in cls and "nostyle" not in cls:
                    sections[walk.current].append(c)
                    walk.current = None
            else:
                walk(c)
    walk.current = None
    walk(root)
    return sections


def grade_id_for(slug):
    return {"Gauss7": "grade 7", "Gauss8": "grade 8"}.get(slug)


def build_records():
    records = []
    stats = {"pairs": 0, "problems": 0, "skipped_unusable": 0,
             "skipped_invalid": 0, "no_solution_match": 0}
    for slug, (cname, grade) in CONTESTS.items():
        fam_dir = CEMC_DIR / cname
        if not fam_dir.exists():
            continue
        for cpath in sorted(fam_dir.glob(f"*{slug}Contest.html")):
            year = int(re.match(r"(\d{4})", cpath.name).group(1))
            sol_path = fam_dir / (f"{year}GaussSolution.html"
                                  if slug.startswith("Gauss")
                                  else f"{year}{cname}Solution.html")
            problems = parse_problems(cpath.read_text(encoding="utf-8"))
            solutions = []
            if sol_path.exists():
                sol_html = sol_path.read_text(encoding="utf-8")
                if slug.startswith("Gauss"):
                    sections = split_gauss_grades(sol_html)
                    ols = sections.get(grade_id_for(slug), [])
                    solutions = []
                    for ol in ols:
                        for run in item_runs(ol):
                            text = _run_text(run)
                            m = ANS_RE.search(text)
                            letter = m.group(1).upper() if m else None
                            if m:
                                text = text[:m.start()].strip()
                            if text:
                                solutions.append((text, letter))
                else:
                    solutions = parse_solutions(sol_html)
            stats["pairs"] += 1
            usable_n = sum(1 for p in problems if p[3])
            stats["problems"] += usable_n
            stats["skipped_unusable"] += len(problems) - usable_n
            if len(problems) != 25:
                print(f"  WARN {cpath.name}: {len(problems)} problem blocks "
                      f"(expected 25)", file=sys.stderr)
            if solutions and len(solutions) != 25:
                print(f"  WARN {sol_path.name}: {len(solutions)} solutions "
                      f"(expected 25)", file=sys.stderr)
            for n, stmt, choices, usable in problems:
                if not usable:
                    continue
                i = n  # original problem number keeps solutions aligned
                sol_text, letter = None, None
                if i <= len(solutions):
                    sol_text, letter = solutions[i - 1]
                else:
                    stats["no_solution_match"] += 1
                sol_objs = ([{
                    "id": f"sol.{DATASET}-{len(records) + 1:06d}.official",
                    "kind": "proof-sketch",
                    "text": sol_text,
                    "hints": [],
                    "images": [],
                }] if sol_text else [])
                category = classify_record(stmt, solutions=sol_objs)
                rec = normalize_record_hygiene({
                    "id": f"prob.{DATASET}-{len(records) + 1:06d}",
                    "title": f"{year} {cname} ({grade}) Problem {i}",
                    "category": category,
                    "subjects": [category] if category != "uncategorized"
                                else [],
                    "concepts": [],
                    "source": {
                        "dataset": DATASET,
                        "collection": f"CEMC {cname} ({grade})",
                        "year": year,
                        "number": i,
                        "url": "https://cemc.uwaterloo.ca/resources/past-contests",
                        "tags": ["cemc", cname.lower(), "multiple-choice"],
                    },
                    "difficulty": {"course": None, "source": None,
                                   "mohs": None, "note": None},
                    "estimatedMinutes": None,
                    "statement": stmt,
                    "answerChoices": [
                        {"label": LETTERS[j], "text": ch}
                        for j, ch in enumerate(choices)
                    ],
                    "answer": {
                        "letter": letter.lower() if letter else None,
                        "value": (choices[LETTERS.index(letter)]
                                  if letter else None),
                    },
                    "solutions": sol_objs,
                    "images": {"statement": [], "solutions": []},
                })
                try:
                    validate_record(rec)
                except ValueError as e:
                    stats["skipped_invalid"] += 1
                    print(f"  INVALID {year} {slug} P{i}: {e}", file=sys.stderr)
                    continue
                records.append(rec)
    return records, stats


def main():
    records, stats = build_records()
    print(f"contest files parsed: {stats['pairs']}")
    print(f"problems usable (image/table-free, 5 choices): {stats['problems']}")
    print(f"problems skipped (images/tables/no-choices): "
          f"{stats['skipped_unusable']}")
    print(f"records emitted: {len(records)}")
    print(f"invalid dropped: {stats['skipped_invalid']}")
    print(f"problems beyond solution list: {stats['no_solution_match']}")
    if records:
        paths = write_shards(records, OUT_DIR)
        for p in paths:
            print(f"wrote {p}")


if __name__ == "__main__":
    main()
