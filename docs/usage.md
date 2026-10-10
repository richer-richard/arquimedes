# Usage

Two access paths: the **JSON file tree** (browse, diff, script against) and
the **SQLite database** (query). Both carry identical content.

## Python + JSON files

```python
import json, glob, random

# random geometry problem with a diagram
paths = glob.glob("problems/geometry/*.json")
prob = json.load(open(random.choice(paths)))
print(prob["statement"])            # raw LaTeX with \( \) delimiters
for img in prob["images"]["statement"]:
    print(f"diagram: images/{img}.svg")
print(prob["answer"], prob["solutions"][0]["text"][:200])
```

## Python + SQLite

```python
import sqlite3, json
db = sqlite3.connect("data/problems.sqlite")
db.row_factory = sqlite3.Row

# all 2015+ AIME problems, with answers
rows = db.execute("""
    SELECT id, title, statement, answer_value
    FROM problems
    WHERE source_collection LIKE 'AIME%' AND source_year >= 2015
    ORDER BY source_year, source_number
""").fetchall()
```

## SQL examples

Problems by concept tag (concepts are JSON text):

```sql
SELECT id, title FROM problems
WHERE concepts LIKE '%"geo.circle-geometry"%';
```

Multiple-choice practice set with images:

```sql
SELECT p.id, p.statement, pi.image_hash
FROM problems p JOIN problem_images pi ON pi.problem_id = p.id
WHERE p.has_choices = 1 AND pi.role = 'statement';
```

Difficulty-ordered number theory:

```sql
SELECT id, difficulty_course FROM problems
WHERE category = 'number-theory' AND difficulty_course IS NOT NULL
ORDER BY difficulty_course;
```

## Rendering math

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

## Rebuilding from raw

```bash
python3 tools/build_database.py   # raw/ -> problems/, images/, data/
```

The builder is idempotent: it deletes and recreates `data/problems.sqlite`
and rewrites the JSON tree in place.
