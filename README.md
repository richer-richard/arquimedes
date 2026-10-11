# Arquimedes: Math Problem Database

A structured database of competition and benchmark mathematics: **1,038,963
problems** across 9 datasets, each with a full statement, answer metadata, and
solutions in a uniform JSON schema (v2).

- **1,038,963 problems** with full statements
- **797,672 written solutions**: proof-sketch (797,632), strategy (22), answer-only (18)
- **277,002 model-reasoning traces** (deepmath dataset, JSONL shards only)
- **1,219 diagram images** (SVG and JPG), content-addressed by hash
- **Competition coverage**: AHSME, AMC 8/10/12, AIME, USAMO, IMO, IMO
  Shortlist, USAJMO, Canadian MO, APMO, Putnam, USA TST/TSTST, HMMT, CEMC
  contests, OlympiadBench, and MATH

## Datasets

| dataset | contents | problems | notable fields |
|---|---|---|---|
| `core` | curated competition problems (AMC program, IMO, HMMT, and more) | 10,645 | concept tags, numeric difficulty ratings, hints, estimated solve time |
| `aops` | competition problems with community-written solutions | 311 | collection, year, and problem code per record |
| `cemc` | CEMC multiple-choice contests (Gauss, Pascal, Cayley, Fermat) | 792 | five answer choices per problem, reference URLs |
| `olympiadbench` | OlympiadBench olympiad problems | 1,389 | diagram images (JPG) |
| `omnimath` | Omni-MATH olympiad problems | 2,640 | difficulty rating from 1 to 9.5 |
| `math` | MATH benchmark problems | 12,401 | difficulty levels 1 to 5 |
| `deepmath` | DeepMath problems with reasoning traces | 92,334 | three model-reasoning traces per problem, difficulty rating 1 to 10 |
| `numina` | NuminaMath problems, the largest dataset | 840,924 | origin tags per problem |
| `bigmath` | Big-Math-RL-Verified problems with verified answers | 77,527 | model solve-rate difficulty note, origin tags per problem |

Per-dataset category breakdowns and field notes: [`docs/datasets.md`](docs/datasets.md).

## Competition coverage

The `source.collection` field labels records that come from a named
competition or benchmark. Counts per label:

- AMC program (`core`): AHSME 1,810, AMC 8 1,025, AMC 10A 625, AMC 10B 625,
  AMC 10 50, AMC 12A 625, AMC 12B 625, AMC 12 50, AIME I 405, AIME II 405,
  AIME 255, USAMO 153, USA TST 45, USA TSTST 48
- IMO (`core`): 156
- HMMT (`core`): February 2,606, November 1,072, Invitational 65
- CEMC (`cemc`): Gauss (Grade 7) 174, Gauss (Grade 8) 166, Pascal (Grade 9)
  134, Cayley (Grade 10) 150, Fermat (Grade 11) 168
- AoPS (`aops`): IMO Shortlist 102, USAJMO 91, Canadian MO 83, APMO 28,
  Putnam 7
- OlympiadBench (`olympiadbench`): 1,389
- MATH (`math`): 12,401

Records in `omnimath`, `deepmath`, `numina`, and `bigmath` carry origin
labels in `source.tags` instead of collection and year fields.

## Layout

```
problems/<dataset>/shard-*.jsonl.gz   gzipped JSON Lines, one problem record per line
images/<hash>.svg, images/<hash>.jpg  1,219 content-addressed diagram files
data/index.json                       summary index (counts by dataset, category, competition)
data/problems.sqlite                  queryable SQLite database (not committed, build it locally)
tools/                                per-dataset converters, merge script, database builder
docs/                                 schema, usage, and dataset documentation
```

## Quickstart

Read a problem from a shard with the Python standard library:

```python
import gzip, json

with gzip.open("problems/core/shard-00000.jsonl.gz", "rt", encoding="utf-8") as fh:
    prob = json.loads(fh.readline())

print(prob["title"])
print(prob["statement"])               # raw LaTeX with \( \) delimiters
print(prob["answer"])
print(prob["solutions"][0]["text"][:200])
```

Build the SQLite database (takes under a minute, writes about 1.5 GB):

```bash
.venv/bin/python tools/build_database.py
```

Query it:

```sql
SELECT dataset, COUNT(*) AS n
FROM problems
GROUP BY dataset
ORDER BY n DESC;
```

## Tools

- `tools/import_<slug>.py`: converts one dataset into validated staging
  shards (one converter per dataset).
- `tools/merge_datasets.py`: merges staging into the final `problems/`
  shards, deduplicating identical statements across datasets.
- `tools/build_database.py`: builds `data/problems.sqlite` and
  `data/index.json` from the shards.
- `tools/lib/`: shared helpers (v2 schema validation, shard I/O, category
  classification, LaTeX normalization, content-addressed image storage).

## Documentation

- [`docs/schema.md`](docs/schema.md): full v2 record reference, shard format,
  SQLite schema, LaTeX convention, image store, index format
- [`docs/usage.md`](docs/usage.md): reading and streaming shards, SQL query
  examples, reasoning traces, rebuilding from scratch
- [`docs/datasets.md`](docs/datasets.md): per-dataset contents, field notes,
  category distributions, deduplication rules
