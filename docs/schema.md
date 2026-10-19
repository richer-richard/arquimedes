# Data Schema

Complete reference for every artifact in this repository: the problem shards,
the SQLite database, the LaTeX convention, the image store, and the summary
index.

## 1. Shard files: `problems/<dataset>/shard-*.jsonl.gz`

Problems are stored per dataset in gzipped JSON Lines shards:

- one directory per dataset: `problems/core/`, `problems/aops/`,
  `problems/cemc/`, `problems/olympiadbench/`, `problems/omnimath/`,
  `problems/math/`, `problems/deepmath/`, `problems/numina/`,
  `problems/bigmath/`
- shards are named `shard-00000.jsonl.gz`, `shard-00001.jsonl.gz`, and so on
- each shard is gzip-compressed JSON Lines: one v2 problem record per line,
  UTF-8, at most 10,000 records per shard
- read with the standard library (`gzip` + `json`) or with
  `tools/lib/shards.py` (`read_shards`)

| dataset | records | contents |
|---|---|---|
| `core` | 10,645 | curated competition problems with written solutions |
| `aops` | 311 | competition problems with community-written solutions |
| `cemc` | 792 | CEMC multiple-choice contests |
| `olympiadbench` | 1,389 | OlympiadBench olympiad problems |
| `omnimath` | 2,640 | Omni-MATH olympiad problems |
| `math` | 12,401 | MATH benchmark problems |
| `deepmath` | 92,334 | DeepMath problems with reasoning traces |
| `numina` | 840,924 | NuminaMath problems |
| `bigmath` | 77,527 | Big-Math-RL-Verified problems with verified answers |

Total: 1,038,963 problems. Details per dataset: [`datasets.md`](datasets.md).

## 2. Problem record (v2)

One JSON object per line. v2 adds four fields to the v1 record:
`source.dataset`, `source.url`, `source.tags`, and `difficulty.note`. All
other fields are unchanged.

| field | type | notes |
|---|---|---|
| `id` | string | `prob.<dataset>-<nnnnnn>` with six digits, e.g. `prob.numina-000369`. Exception: `core` keeps legacy ids of the form `prob.<collection>-<year>-p<n>`, e.g. `prob.ahsme-1950-p10`. |
| `title` | string | Human-readable title ("1950 AHSME Problem 10"). Empty in `math`, `deepmath`, `numina`, `olympiadbench`, `omnimath`, and `bigmath`. |
| `category` | string | Primary subject. One of: `algebra`, `arithmetic`, `combinatorics`, `geometry`, `logic-foundations`, `number-theory`, `probability`, `problem-solving-techniques`, `uncategorized`. |
| `subjects` | string[] | All subjects assigned to the problem (superset of `category`). |
| `concepts` | object[] | Fine-grained concept tags `{id, label, roles[]}`, where `roles` contains `given` and/or `derived`. Populated in `core` only. |
| `source.dataset` | string | **New in v2.** Dataset slug (`core`, `aops`, `cemc`, `olympiadbench`, `omnimath`, `math`, `deepmath`, `numina`, `bigmath`). |
| `source.collection` | string \| null | Competition or benchmark label: `AHSME`, `AMC 8`, `AMC 10A/B`, `AMC 12A/B`, `AIME I/II`, `USAMO`, `IMO`, `HMMT February`, `HMMT November`, `HMMT Invitational`, `USA TST`, `USA TSTST`, the CEMC contest names, `OlympiadBench`, `MATH`, `IMO Shortlist`, `USAJMO`, `Canadian MO`, `APMO`, `Putnam`. |
| `source.year` | int \| null | Contest year where applicable. |
| `source.number` | int \| string \| null | Problem number within its contest. |
| `source.url` | string \| null | **New in v2.** Reference URL. Present on `cemc`, `aops`, and `bigmath` records. |
| `source.tags` | string[] | **New in v2.** Origin labels: subject paths, contest tags, or origin buckets depending on the dataset. Empty in `core` and `aops`. |
| `difficulty.course` | float \| null | Course-calibrated difficulty, roughly 0–100. `core` only. |
| `difficulty.source` | float \| null | Source difficulty rating. `core` only. |
| `difficulty.mohs` | float \| null | Unified difficulty rating from `1.0` (easiest) to `10.0` (hardest IMO/Putnam olympiad), calibrated across all 9 datasets. |
| `difficulty.note` | string \| null | **New in v2.** Dataset difficulty label: `MATH Level 1` to `MATH Level 5`, `deepmath 1` to `deepmath 10`, `omnimath 1` to `omnimath 9.5`, `Competition` (olympiadbench), or `llama8b_solve_rate <rate>` (bigmath). |
| `estimatedMinutes` | number \| null | Estimated solve time. `core` only. |
| `statement` | string | Problem statement. Raw LaTeX, see §4. Never empty. |
| `answerChoices` | object[] | `[{label, text}]` with uppercase letter labels. Empty for non-multiple-choice problems. |
| `answer.letter` | string \| null | Lowercase choice letter (`"b"`). In `core` it may instead hold a value string for AIME-style problems (`"60"`). |
| `answer.value` | string \| null | Exact answer value as a string (`"117/2"`, `"60"`). |
| `solutions` | object[] | Zero or more solutions (see below). |
| `images.statement` | string[] | Image references for statement diagrams, see §5. |
| `images.solutions` | string[] | Image references for solution diagrams. |

### Solution objects

| field | type | notes |
|---|---|---|
| `id` | string | e.g. `sol.ahsme-1950-p10.live`, `sol.deepmath-000000.r1-1`. |
| `kind` | string | `proof-sketch` (797,632), `strategy` (22), `answer-only` (18), or `model-reasoning` (277,002). |
| `text` | string | Solution text, raw LaTeX. |
| `hints` | string[] | Progressive hints. Common in `core`. |
| `images` | string[] | Diagram references used by this solution. |

Notes on solutions:

- `model-reasoning` records are long-form, exploratory step-by-step
  reasoning traces. All of them belong to `deepmath` (three per problem).
  They exist only in the JSONL shards and are excluded from the SQLite build.
- Proof problems (USAMO, IMO, most HMMT February) legitimately have
  `answer.letter` and `answer.value` set to null. The solution text is the
  deliverable.
- A small number of `core` problems and part of `numina` have a statement
  but no written solution.

## 3. SQLite: `data/problems.sqlite`

The SQLite database is a derived artifact and is not committed to git. Build
it with:

```bash
.venv/bin/python tools/build_database.py
```

The build takes under a minute and produces about 1.7 GB. Tables:

```sql
problems(id, title, category, dataset, subjects, concepts,
         source_collection, source_year, source_number,
         difficulty_course, difficulty_source, difficulty_mohs,
         estimated_minutes, statement, answer_letter, answer_value,
         has_choices, images, metadata)          PK (id)
answer_choices(problem_id, label, text)          PK (problem_id, label)
solutions(id, problem_id, kind, text, hints)     PK (id)
images(hash, path)                               PK (hash)
problem_images(problem_id, image_hash, role)     PK (problem_id, image_hash, role)
                                                  role in {statement, solution}
```

- `problems.dataset` holds the dataset slug. Indexes exist on `category`,
  `dataset`, `(source_collection, source_year)`, `difficulty_mohs`
  (`idx_problems_mohs`), and `(category, difficulty_mohs)`
  (`idx_problems_cat_mohs`).
- Full-text search uses the FTS5 virtual table `problems_fts(id, title,
  statement, source_collection)`, backed by `problems` via `content_rowid`.
  Queries use the `MATCH` operator for sub-millisecond search over titles,
  statements, and collection names.
- JSON-typed columns (`subjects`, `concepts`, `hints`, `images`, `metadata`)
  are stored as JSON text. Parse with `json.loads`.
- `metadata` preserves record fields without a dedicated column, plus
  `sourceUrl`, `sourceTags`, and `difficultyNote` when present.
- `solutions` excludes `kind = "model-reasoning"`. The 277,002 reasoning
  traces stay available in the JSONL shards.
- `solutions` therefore holds the 797,672 written solutions: proof-sketch
  (797,632), strategy (22), and answer-only (18).

## 4. LaTeX typesetting convention

Statements, choices, solutions, and hints contain **raw LaTeX source**. Math
is delimited in one of these four forms:

- inline math: `\(...\)` or `$...$`
- display math: `\[...\]` or `$$...$$`

The pairs are equivalent: `\(...\)` and `$...$` both mean inline math, and
`\[...\]` and `$$...$$` both mean display math. Most records use `\(...\)` and
`\[...\]` because the import pipeline normalizes dollar delimiters to that
form, but a small number of records keep the dollar forms. All four are valid
and consumers should accept all of them.

In JSON, backslashes are escaped (`\\(`), so after `json.loads` you hold the
exact LaTeX source string. A literal currency dollar sign is escaped as `\$`.

- Some statements contain inline `[asy]...[/asy]` diagram code blocks,
  notably in the `math` and `omnimath` datasets.

To render on the web, use KaTeX or MathJax configured for all four delimiters
(see [`usage.md`](usage.md)).

## 5. Images: `images/<hash>`

- 1,219 content-addressed files: SVG diagrams, plus JPG diagrams for
  `olympiadbench`.
- A record references an SVG by its bare hash `h` (file `images/<h>.svg`)
  and a JPG by its full filename (file `images/<h>.jpg`, reference includes
  the extension).
- Filenames are content hashes, so images are immutable and deduplicated.
  The same image may back several problems.
- SVGs are standalone and self-contained: every glyph definition is inlined
  in the file's own `<defs>`, with no external references.

## 6. Summary index: `data/index.json`

`data/index.json` is a counts-only summary index, regenerated by
`tools/build_database.py`. It has no per-problem listings.

```jsonc
{
  "totalProblems": 1038963,
  "datasets": {
    "<slug>": {"count": 10645, "categories": {"<category>": 3304}}
  },
  "categories": {"<category>": 386699},
  "competitions": {"<collection>": 1810},
  "solutionKinds": {"<kind>": 797632}
}
```

- `datasets`: per-dataset record count and category breakdown.
- `categories`: global category totals.
- `competitions`: count per `source.collection` label.
- `solutionKinds`: count per solution kind across all shards, including
  `model-reasoning`.
