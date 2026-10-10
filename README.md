# Arquimedes — Math Problem Database

A structured problem–answer database of competition mathematics.
All content has been verified beforehand.

- **10,645 problems** with full statements and written solutions
- **10,631 solutions** (14 problems have statements but no written solution yet)
- **27,175 answer choices** across 6,492 multiple-choice problems
- **7,266 problems** with a verified answer (letter for MC, value for AIME-style)
- **1,064 geometry/diagram images** as standalone SVGs
- **18 source competitions, 1950–2026**: AHSME (1,810), HMMT February (2,606),
  HMMT November (1,072), AMC 8/10/12 (3,600), AIME I/II (810+255),
  USAMO (153), IMO (156), USA TST/TSTST (93), …

## Documentation

- [`docs/schema.md`](docs/schema.md) — full data dictionary: problem JSON
  fields, SQLite schema, LaTeX convention, image format
- [`docs/usage.md`](docs/usage.md) — Python/SQL query examples, KaTeX rendering

## Layout

```
problems/<category>/<problem-id>.json   one JSON file per problem
images/<sha256>.svg                     standalone diagram SVGs
data/problems.sqlite                    queryable SQLite database
data/index.json                         category → problem summary index
tools/build_database.py                 rebuilds problems/, images/, data/ from raw/
raw/                                    raw content archives (git-ignored)
```

### Categories

| category | problems |
|---|---|
| geometry | 3,685 |
| algebra | 3,304 |
| number-theory | 1,212 |
| combinatorics | 936 |
| uncategorized | 522 |
| arithmetic | 483 |
| probability | 382 |
| logic-foundations | 66 |
| problem-solving-techniques | 55 |

Category = the problem's primary subject. Multi-subject problems keep the full
list in `subjects`. The 522 "uncategorized" problems have no primary subject
(their concept tags are still in `concepts`).

## Problem JSON schema

```jsonc
{
  "id": "prob.ahsme-1952-p24",
  "title": "1952 AHSME Problem 24",
  "category": "geometry",
  "subjects": ["geometry"],
  "concepts": [{"id": "geo.area", "label": "Area", "roles": ["given"]}],
  "source": {"collection": "AHSME", "year": 1952, "number": 24},
  "difficulty": {"course": 30.0, "source": 1760, "mohs": null},
  "estimatedMinutes": 2,
  "statement": "In the figure, ... \\(AC=12.\\) ...",
  "answerChoices": [{"label": "A", "text": "\\(75\\)"}],   // [] for non-MC
  "answer": {"letter": "b", "value": "117/2"},            // nulls for proof problems
  "solutions": [{
    "id": "sol.ahsme-1952-p24.live",
    "kind": "proof-sketch",
    "text": "Since \\(AB=20,\\) ...",
    "hints": ["..."],
    "images": ["<sha256>"]
  }],
  "images": {"statement": ["<sha256>"], "solutions": ["<sha256>"]}
}
```

## Math typesetting

All math is stored as **raw LaTeX** with these delimiters:

- inline math: `\(...\)`
- display math: `\[...\]`

To render, feed the text to KaTeX/MathJax with those delimiters enabled
(see [`docs/usage.md`](docs/usage.md)). The JSON is UTF-8; LaTeX backslashes
are JSON-escaped (`\\(`), so `json.load` gives you the exact LaTeX source
string. No rendering, conversion, or normalization has been applied.

## Images

- Referenced from problem JSON via `images.statement` / `images.solutions`
  (arrays of SHA-256 hashes) → file at `images/<hash>.svg`.
- SVGs are **standalone and self-contained** — all glyph definitions are
  inlined in each file's `<defs>`; no external references.
- Plain SVG files, largest is tens of KB — no Git LFS needed.

## SQLite

`data/problems.sqlite` tables:

- `problems` — one row per problem (id, title, category, subjects/concepts JSON,
  source collection/year/number, difficulty scores, statement, answer
  letter/value, has_choices, images JSON, extra metadata JSON)
- `answer_choices(problem_id, label, text)`
- `solutions(id, problem_id, kind, text, hints JSON)`
- `images(hash, path)` and `problem_images(problem_id, image_hash, role)`

Example: all AIME problems with answers —

```sql
SELECT id, statement, answer_value FROM problems
WHERE source_collection LIKE 'AIME%' AND answer_value IS NOT NULL;
```

## Notes on data quality

- Statements and solutions are clean content only — no UI boilerplate,
  banners, or review notices.
- 19 empty placeholder entries (no statement content) are excluded.
- Proof problems (USAMO/IMO/HMMT etc.) legitimately have no `answer` — the
  solution text is the deliverable.
