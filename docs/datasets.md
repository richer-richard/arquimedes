# Datasets

The database holds **1,038,963 problems** in 9 datasets. Each dataset lives in
`problems/<slug>/` as gzipped JSONL shards and uses the shared v2 record
schema described in [`schema.md`](schema.md).

| dataset | problems | contents |
|---|---|---|
| `numina` | 840,924 | NuminaMath problems |
| `deepmath` | 92,334 | DeepMath problems with reasoning traces |
| `bigmath` | 77,527 | Big-Math-RL-Verified problems with verified answers |
| `math` | 12,401 | MATH benchmark problems |
| `core` | 10,645 | curated competition problems |
| `omnimath` | 2,640 | Omni-MATH olympiad problems |
| `olympiadbench` | 1,389 | OlympiadBench olympiad problems |
| `cemc` | 792 | CEMC multiple-choice contests |
| `aops` | 311 | competition problems with community-written solutions |

Global category totals (all datasets combined):

| category | problems |
|---|---|
| uncategorized | 376,384 |
| algebra | 242,585 |
| geometry | 212,970 |
| number-theory | 99,890 |
| arithmetic | 40,112 |
| probability | 35,650 |
| combinatorics | 25,036 |
| logic-foundations | 5,985 |
| problem-solving-techniques | 351 |

`uncategorized` means no primary subject was assigned to the record.

## core (10,645)

Curated competition problems from the AMC program (AHSME, AMC 8, AMC 10,
AMC 12, AIME, USAMO), the IMO, USA TST/TSTST, and HMMT (February, November,
Invitational).

Field notes:

- The richest records in the database. Every problem has a human-readable
  title, numeric difficulty ratings (`difficulty.course` on a roughly
  0–100 scale, `difficulty.source`), and an estimated solve time. Nearly
  all carry concept tags, which no other dataset has.
- Ids keep the legacy pattern `prob.<collection>-<year>-p<n>` instead of
  `prob.core-NNNNNN`.
- `answer.letter` holds the choice letter for multiple-choice problems and a
  value string for AIME-style problems.
- Many solutions carry progressive hints.
- The database's 22 `strategy` and 18 `answer-only` solutions all live in
  this dataset. Everything else is `proof-sketch`.
- Statement and solution diagrams are SVG images referenced by hash.

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

## aops (311)

Competition problems from the AoPS Wiki with community-written solutions.

Field notes:

- `source.collection` names the competition: IMO Shortlist (102), USAJMO
  (91), Canadian MO (83), APMO (28), and Putnam (7). `source.year` and
  `source.number` carry the contest year and problem code.
- Most records have one or more `proof-sketch` solutions, and a few carry an
  exact answer in `answer.value`.
- Every record has a human-readable title and a `source.url`.
- No numeric difficulty fields.

| category | problems |
|---|---|
| geometry | 100 |
| number-theory | 84 |
| algebra | 58 |
| combinatorics | 34 |
| uncategorized | 33 |
| probability | 2 |

## cemc (792)

CEMC multiple-choice contests: Gauss (Grade 7) with 174 problems, Gauss
(Grade 8) with 166, Pascal (Grade 9) with 134, Cayley (Grade 10) with 150,
and Fermat (Grade 11) with 168.

Field notes:

- Every problem is multiple choice with five options and has exactly one
  written solution.
- Nearly all problems have both `answer.letter` and `answer.value`.
- `source.url` is set on every record, and `source.tags` labels the contest.
- No numeric difficulty fields.

| category | problems |
|---|---|
| uncategorized | 431 |
| number-theory | 149 |
| geometry | 63 |
| probability | 52 |
| algebra | 46 |
| arithmetic | 33 |
| combinatorics | 18 |

## olympiadbench (1,389)

OlympiadBench olympiad problems (`source.collection` = `OlympiadBench`).

Field notes:

- `difficulty.note` is `Competition` on every record.
- Answers are exact values in `answer.value` on many records. There are no
  choice letters.
- Diagram images are JPG files referenced by full filename.
- `source.tags` carries subject and answer-type labels.

| category | problems |
|---|---|
| geometry | 447 |
| algebra | 384 |
| combinatorics | 336 |
| number-theory | 222 |

## omnimath (2,640)

Omni-MATH olympiad-level problems.

Field notes:

- `difficulty.note` carries a rating from `omnimath 1` to `omnimath 9.5`.
- Answers are exact values in `answer.value`.
- `source.tags` names the origin contest, for example
  `china_team_selection_test`.
- Some statements contain inline `[asy]...[/asy]` diagram code.
- Every problem has exactly one written solution.

| category | problems |
|---|---|
| algebra | 1,382 |
| number-theory | 400 |
| combinatorics | 381 |
| geometry | 368 |
| uncategorized | 84 |
| probability | 15 |
| arithmetic | 10 |

## math (12,401)

MATH benchmark problems (`source.collection` = `MATH`).

Field notes:

- `difficulty.note` is `MATH Level 1` (easiest) through `MATH Level 5`
  (hardest).
- Every problem has exactly one written solution, and nearly all have an
  exact answer in `answer.value`.
- `source.tags` carries the MATH subject and split labels.
- Some statements contain inline `[asy]...[/asy]` diagram code.

| category | problems |
|---|---|
| algebra | 6,368 |
| arithmetic | 2,068 |
| number-theory | 1,398 |
| geometry | 1,341 |
| combinatorics | 1,226 |

## deepmath (92,334)

DeepMath problems with reasoning traces instead of written solutions.

Field notes:

- Every problem carries exactly three `model-reasoning` solutions, 277,002
  traces in total across the dataset. The traces are long-form, exploratory
  step-by-step reasoning.
- All problems have an exact answer in `answer.value`.
- `difficulty.note` carries a rating from `deepmath 1` to `deepmath 10` in
  half steps.
- `source.tags` holds a subject path such as
  `Mathematics -> Geometry -> Plane Geometry -> Angles`.
- The traces live only in the JSONL shards and are excluded from the SQLite
  build. See [`usage.md`](usage.md) for how to read them.

| category | problems |
|---|---|
| uncategorized | 37,799 |
| algebra | 28,480 |
| geometry | 10,120 |
| number-theory | 8,010 |
| probability | 5,517 |
| combinatorics | 2,138 |
| arithmetic | 105 |
| logic-foundations | 88 |
| problem-solving-techniques | 77 |

## numina (840,924)

NuminaMath problems, by far the largest dataset.

Field notes:

- Most problems have exactly one written `proof-sketch` solution, and most
  carry an exact answer in `answer.value`. A minority of problems use
  `answer.letter`.
- `source.tags` records the origin bucket of each problem (for example
  `olympiads`, `cn_k12`, `orca_math`, `synthetic`). A problem can carry
  several tags.
- No titles and no numeric difficulty fields.

| category | problems |
|---|---|
| uncategorized | 311,319 |
| algebra | 182,369 |
| geometry | 179,192 |
| number-theory | 81,949 |
| arithmetic | 36,007 |
| probability | 26,264 |
| combinatorics | 17,925 |
| logic-foundations | 5,680 |
| problem-solving-techniques | 219 |

## bigmath (77,527)

Big-Math-RL-Verified problems (SynthLabsAI on Hugging Face) with verified
final answers and no written solutions.

Field notes:

- Nearly every record carries a verified final answer in `answer.value`.
  There are no written solutions.
- `difficulty.note` holds `llama8b_solve_rate <rate>`, the solve rate of a
  Llama 8B model on the problem. Lower rates are harder.
- `source.tags` carries the origin dataset and domain path strings, for
  example `aops_forum` and
  `Mathematics -> Applied Mathematics -> Statistics -> Mathematical Statistics`.
- No titles and no collection or year fields.

| category | problems |
|---|---|
| uncategorized | 26,196 |
| algebra | 20,194 |
| geometry | 17,654 |
| number-theory | 6,466 |
| probability | 3,418 |
| combinatorics | 2,042 |
| arithmetic | 1,406 |
| logic-foundations | 151 |

## Deduplication across datasets

Identical problem statements are stored only once, in the highest-priority
dataset. The comparison ignores case, whitespace, braces, and LaTeX spacing
commands, so purely cosmetic differences do not create duplicates.

Priority order:

1. `core`
2. `aops`
3. `cemc`
4. `olympiadbench`
5. `omnimath`
6. `math`
7. `deepmath`
8. `numina`
9. `bigmath`

`openr1` is not present as a separate dataset because its problems are fully
contained in `numina`. Under the priority rule above, every `openr1` record
matched a `numina` record and was subsumed by it.
