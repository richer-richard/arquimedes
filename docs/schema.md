# Data Schema

Complete reference for every artifact in this repository.

## 1. Problem JSON files — `problems/<category>/<id>.json`

One file per problem, grouped by primary subject. Example:
`problems/geometry/prob.ahsme-1952-p24.json`.

| field | type | notes |
|---|---|---|
| `id` | string | Stable id, e.g. `prob.ahsme-1952-p24`. Pattern: `prob.<collection>-<year>-p<n>`. |
| `title` | string | Human-readable title ("1952 AHSME Problem 24"). |
| `category` | string | Primary subject folder name. One of: `algebra`, `arithmetic`, `combinatorics`, `geometry`, `logic-foundations`, `number-theory`, `probability`, `problem-solving-techniques`, `uncategorized`. |
| `subjects` | string[] | All subjects assigned to the problem (superset of `category`). |
| `concepts` | object[] | Fine-grained concept tags: `{id, label, roles[]}`. 873 distinct concept ids exist; `roles` is `given` and/or `derived`. Example id: `geo.angle-chasing`. |
| `source.collection` | string | Competition: `AHSME`, `AMC 8`, `AMC 10A/B`, `AMC 12A/B`, `AIME I/II`, `USAMO`, `IMO`, `HMMT February`, `HMMT November`, `HMMT Invitational`, `USA TST`, `USA TSTST`, … |
| `source.year` | int \\| null | 1950–2026. |
| `source.number` | int \\| string \\| null | Problem number within its contest. |
| `difficulty.course` | float \\| null | Course-calibrated difficulty score (roughly 0–100). |
| `difficulty.source` | float \\| null | Source rating (AoPS-style scale, e.g. 840–3000+). |
| `difficulty.mohs` | float \\| null | Mohs-scale hardness where present. |
| `estimatedMinutes` | number \\| null | Estimated solve time. |
| `statement` | string | Problem statement. Raw LaTeX, see §3. |
| `answerChoices` | object[] | `[{label: "A", text: "..."}]`. Empty for non-multiple-choice problems. Labels are uppercase letters. |
| `answer.letter` | string \\| null | Lowercase choice letter (`"b"`). For answer-only contests (AIME) this holds the numeric value string instead. |
| `answer.value` | string \\| null | Exact answer value as a string (`"117/2"`, `"60"`). |
| `solutions` | object[] | 0 or 1 solutions per problem (see below). |
| `images.statement` | string[] | SHA-256 hashes of statement diagrams → `images/<hash>.svg`. |
| `images.solutions` | string[] | Same, for solution diagrams. |

### Solution objects

| field | type | notes |
|---|---|---|
| `id` | string | e.g. `sol.ahsme-1952-p24.live`. |
| `kind` | string | `proof-sketch` (10,591), `strategy` (22), or `answer-only` (18). |
| `text` | string | Full written solution, raw LaTeX. |
| `hints` | string[] | Progressive hints (present on 6,500 problems). |
| `images` | string[] | Diagram hashes used by this solution. |

14 problems have a statement but no solution record.
Proof contests (USAMO, IMO, most HMMT February) legitimately have
`answer.letter/value = null` — the solution text *is* the deliverable.

## 2. SQLite — `data/problems.sqlite`

```
problems(id, title, category, subjects, concepts,
         source_collection, source_year, source_number,
         difficulty_course, difficulty_source, difficulty_mohs,
         estimated_minutes, statement, answer_letter, answer_value,
         has_choices, images, metadata)
answer_choices(problem_id, label, text)          PK (problem_id, label)
solutions(id, problem_id, kind, text, hints)     PK (id)
images(hash, path)                               PK (hash)
problem_images(problem_id, image_hash, role)     PK (problem_id, image_hash, role)
                                                  role ∈ {statement, solution}
```

- JSON-typed columns (`subjects`, `concepts`, `hints`, `images`, `metadata`)
  are stored as JSON text — parse with `json.loads`.
- `metadata` preserves remaining catalog fields (`tags`, `reviewState`,
  `importOrigin`, …) when non-empty.
- Indexes: `problems(category)`, `problems(source_collection, source_year)`.

## 3. LaTeX typesetting convention

Statements, choices, solutions, and hints contain **unmodified LaTeX source**
with these delimiters:

- inline: `\(...\)`
- display: `\[...\]`

Nothing has been normalized or re-rendered; strings are the exact LaTeX
source. In JSON files backslashes are escaped (`\\(`);
after `json.load` you hold the literal LaTeX string.

To render (web): KaTeX auto-render with
`delimiters: [{left: "\\(", right: "\\)", display: false}, {left: "\\[", right: "\\]", display: true}]`.

To render (matplotlib/markdown): strip or convert the delimiters first.

## 4. Images — `images/<sha256>.svg`

- Plain SVG 1.1, self-contained. No external references: every glyph path the
  diagram uses is inlined into the file's own `<defs>` (ids `d0…dN`).
- Filenames are content hashes — immutable and deduplicated. A problem
  references an image by hash; the same image may back several problems.
- Sizes: median ~8 KB, max ~219 KB. Git LFS deliberately not used.

## 5. Index — `data/index.json`

```jsonc
{
  "totalProblems": 10645,
  "categories": {"algebra": 3304, ...},
  "problems": {
    "<category>": [
      {"id", "title", "source": {...}, "answer", "hasChoices",
       "images": <count>, "difficulty": {...}}
    ]  // sorted by collection, year, id
  }
}
```

## 6. Coverage summary

| what | count |
|---|---|
| problems with statements | 10,645 |
| problems with written solutions | 10,631 |
| multiple-choice problems | 6,492 |
| answer letters present | 7,266 |
| answer values present | 5,650 |
| problems with hints | 6,500 |
| problems referencing ≥1 image | 1,065 |
| distinct images | 1,064 |
| source collections | 18 (1950–2026) |

Excluded: 19 catalog entries that are empty placeholders (no statement
content).
