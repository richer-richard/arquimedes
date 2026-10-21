# Usage

Two access paths: the **JSONL shards** under `problems/` (everything,
including the reasoning traces) and the **SQLite database**
`data/problems.sqlite` (fast queries, excludes model-reasoning traces).

## Reading shards

Each shard is a gzip-compressed JSON Lines file with one problem record per
line. The Python standard library is enough:

```python
import gzip, json

with gzip.open("problems/core/shard-00000.jsonl.gz", "rt", encoding="utf-8") as fh:
    for line in fh:
        prob = json.loads(line)
        print(prob["id"], prob["title"])
        print(prob["statement"])           # raw LaTeX with \( \) delimiters
        for img in prob["images"]["statement"]:
            print(f"diagram: images/{img}.svg")
        break
```

The helper `tools/lib/shards.py` iterates a whole dataset directory, a glob
pattern, or a single file:

```python
from tools.lib.shards import read_shards

for prob in read_shards("problems/cemc"):
    print(prob["id"], prob["answer"]["letter"])
```

## Streaming large datasets

The large datasets (`numina` has 840,924 records) do not fit comfortably in
memory as parsed objects. Stream shard files one line at a time and keep
only what you need:

```python
import glob, gzip, json

count = 0
for path in sorted(glob.glob("problems/numina/shard-*.jsonl.gz")):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            prob = json.loads(line)
            if prob["answer"]["value"] is not None:
                count += 1
print(count)
```

Memory use stays flat regardless of dataset size.

## Building the SQLite database

`data/problems.sqlite` is not committed to git. Build it from the shards:

```bash
.venv/bin/python tools/build_database.py
```

The build takes under a minute and writes about 1.7 GB. It also regenerates
the summary index `data/index.json`. Solutions of kind `model-reasoning`
are excluded from the database and stay available in the JSONL shards.

To save disk space, add `--lean` (or run `uv run arquimedes build --lean`).
The lean build is about 0.8 GB and leaves the `solutions` table empty. Search,
sampling, and filters cover all problems, and the CLI and MCP server read each
problem's solutions from its shard. SQL queries against the `solutions` table
need the full build.

## Querying SQLite

Problems per dataset:

```sql
SELECT dataset, COUNT(*) AS n
FROM problems
GROUP BY dataset
ORDER BY n DESC;
```

Problems per competition:

```sql
SELECT source_collection, COUNT(*) AS n
FROM problems
WHERE source_collection IS NOT NULL
GROUP BY source_collection
ORDER BY n DESC;
```

Fetch one problem with its solutions:

```python
import sqlite3, json

db = sqlite3.connect("data/problems.sqlite")
db.row_factory = sqlite3.Row

prob = db.execute(
    "SELECT * FROM problems WHERE id = ?", ("prob.ahsme-1950-p10",)
).fetchone()
print(prob["title"])
print(prob["statement"])

sols = db.execute(
    "SELECT kind, text, hints FROM solutions WHERE problem_id = ?", (prob["id"],)
).fetchall()
for sol in sols:
    print(sol["kind"], sol["text"][:200])
    print("hints:", json.loads(sol["hints"]))
```

Find problems with diagram images, resolved to file paths:

```sql
SELECT p.id, i.path
FROM problems p
JOIN problem_images pi ON pi.problem_id = p.id
JOIN images i ON i.hash = pi.image_hash
WHERE pi.role = 'statement'
LIMIT 10;
```

JSON-typed columns (`subjects`, `concepts`, `hints`, `images`, `metadata`)
are stored as JSON text. `metadata` carries extra record fields such as
`sourceUrl`, `sourceTags`, and `difficultyNote` when present:

```sql
SELECT id, json_extract(metadata, '$.difficultyNote') AS level
FROM problems
WHERE dataset = 'math'
LIMIT 10;
```

Filter by unified Mohs difficulty (uses `idx_problems_cat_mohs`):

```sql
SELECT id, title, difficulty_mohs, category
FROM problems
WHERE category = 'number-theory'
  AND difficulty_mohs BETWEEN 6.5 AND 8.5
ORDER BY difficulty_mohs DESC
LIMIT 20;
```

Full-text search with FTS5 (`problems_fts`):

```sql
SELECT p.id, p.title, p.difficulty_mohs
FROM problems_fts f
JOIN problems p ON p.rowid = f.rowid
WHERE problems_fts MATCH '"Cauchy-Schwarz" OR "AM-GM"'
LIMIT 10;
```

## CLI: `arquimedes`

After installing project dependencies (`uv sync`), use the `arquimedes` command
for quick inspection of the SQLite database (build it first if needed):

```bash
uv run arquimedes stats
uv run arquimedes search "pigeonhole"
uv run arquimedes sample --category geometry --min-mohs 7 --limit 5
uv run arquimedes show prob.imo-2023-p1
```

- `stats` — dataset and category counts from `data/index.json` / SQLite.
- `search` — full-text search over problem statements and titles.
- `sample` — random sample with optional category and Mohs filters.
- `show` — print one problem record (statement, answer, metadata).

## Install without a checkout

The PyPI package `arquimedes-mcp` contains the program and not the problems.
`arquimedes fetch` downloads the Hugging Face corpus into the user data
directory and builds the lean index:

```bash
uvx arquimedes-mcp fetch
uvx arquimedes-mcp
```

`uvx --from arquimedes-mcp arquimedes` runs the CLI against that same copy.
Pass `--root` to store it somewhere else. The download is about 1.3 GB and
the lean index about 0.8 GB.

## MCP server: `arquimedes-mcp`

The Model Context Protocol server exposes search, stats, and problem lookup
to MCP clients (Cursor, Claude Desktop, etc.):

```bash
uv run arquimedes-mcp
```

Configure your client to launch that command; it reads `data/problems.sqlite`
and the same query paths as the CLI. It speaks JSON-RPC over stdio and offers
four read-only tools:

| tool | arguments | returns |
|---|---|---|
| `arquimedes_get_stats` | none | problem counts by dataset, category, and competition; solution counts by kind |
| `arquimedes_search_problems` | `query` (required), `category`, `dataset`, `competition`, `min_mohs`, `max_mohs`, `limit` (1–50, default 10) | summaries of problems whose statement or title contains all query words |
| `arquimedes_sample_problems` | `category`, `dataset`, `competition`, `year`, `min_mohs`, `max_mohs`, `has_choices`, `has_diagram`, `limit` (1–50, default 5), `seed` | a uniform random draw among matching problems; the same seed repeats it |
| `arquimedes_get_problem` | `problem_id` (required), `include_solutions` (default true), `include_traces` (default false) | the full record, with solutions as `{id, kind, text, hints}` |

Summaries carry `id`, `title`, `dataset`, `category`, `competition`, `year`,
`number`, `mohs`, `difficultyNote`, `answerLetter`, `answerValue`,
`hasChoices`, and `statement`. Bad arguments and unknown ids come back as tool
results with `isError: true`. The tool names before 1.0 (`arquimedes_stats`,
`arquimedes_search`, `arquimedes_sample`) are still accepted in `tools/call`.

The server also offers the resource `arquimedes://index` (the summary index)
and the prompt `math-practice-set` (arguments `category` and `difficulty`).

## Train/eval splits: `tools/export_splits.py`

Export decontaminated JSONL train and eval splits for fine-tuning or
benchmarking without benchmark leakage:

```bash
.venv/bin/python tools/export_splits.py
```

Optional flags: `--out-dir splits` (default), `--stats-only` (print counts
without writing files). The script defines a canonical **eval** set (MATH test,
OlympiadBench, Omni-MATH, AoPS, and recent `core` / `cemc` contests) and a
**train** set of remaining answerable problems that do not match eval under
normalized statement keys or 5-gram shingle overlap.

## Working with model-reasoning traces

The 277,002 `model-reasoning` traces exist only in the JSONL shards (all in
`deepmath`, three per problem). Filter solutions by kind while streaming:

```python
import gzip, json

with gzip.open("problems/deepmath/shard-00000.jsonl.gz", "rt", encoding="utf-8") as fh:
    prob = json.loads(fh.readline())

traces = [s for s in prob["solutions"] if s["kind"] == "model-reasoning"]
print(prob["id"], len(traces))
print(traces[0]["text"][:400])
```

## Rendering math

Statements, choices, solutions, and hints are raw LaTeX. Inline math appears
as `\(...\)` or `$...$`, display math as `\[...\]` or `$$...$$`. The pairs are
equivalent and all four forms are valid. Some statements contain inline
`[asy]...[/asy]` diagram code.

Web (KaTeX auto-render):

```html
<script src="https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16/dist/contrib/auto-render.min.js"></script>
<script>
  renderMathInElement(document.body, {
    delimiters: [
      {left: "\\(", right: "\\)", display: false},
      {left: "\\[", right: "\\]", display: true},
      {left: "$$", right: "$$", display: true},
      {left: "$", right: "$", display: false},
    ],
  });
</script>
```

For matplotlib or markdown, strip or convert the delimiters first.

## Rebuilding from scratch

The pipeline has three stages, each re-runnable:

```bash
# 1. Convert each dataset into validated staging shards (one converter per dataset).
.venv/bin/python tools/import_math.py

# 2. Merge staging/ into the final problems/ shards, deduplicating across datasets.
.venv/bin/python tools/merge_datasets.py

# 3. Build data/problems.sqlite and data/index.json from problems/.
.venv/bin/python tools/build_database.py
```

The merge step deduplicates identical statements globally and reuses the
existing `core` shards when present. A dataset whose staging directory is
absent keeps its existing `problems/` shards, so re-running the merge never
requires every staging input to be present. The build step deletes and
recreates `data/problems.sqlite` on every run.
