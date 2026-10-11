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

The build takes under a minute and writes about 1.5 GB. It also regenerates
the summary index `data/index.json`. Solutions of kind `model-reasoning`
are excluded from the database and stay available in the JSONL shards.

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

Statements, choices, solutions, and hints are raw LaTeX with `\(...\)`
inline and `\[...\]` display delimiters. Some imported records were
normalized from `$...$` delimiters, and some statements contain inline
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
existing `core` shards when present. The build step deletes and recreates
`data/problems.sqlite` on every run.
