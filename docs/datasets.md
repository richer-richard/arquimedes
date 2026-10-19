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
| algebra | 386,699 |
| geometry | 243,231 |
| arithmetic | 183,930 |
| number-theory | 129,482 |
| probability | 38,809 |
| combinatorics | 35,493 |
| logic-foundations | 19,935 |
| problem-solving-techniques | 1,225 |
| uncategorized | 159 |

`uncategorized` means no primary subject was assigned to the record.

Normalization notes (all 9 datasets):

- `difficulty.mohs` is populated on every record on a unified `1.0` (easiest) to
  `10.0` (hardest IMO/Putnam olympiad) scale, calibrated across datasets.
- `answer.value` is normalized: outer `\(...\)` delimiters are stripped. In
  `core`, multiple-choice problems store the choice text and non-MC problems
  store the exact answer in `answer.value` (alongside `answer.letter` where
  applicable).

## core (10,645)

Curated competition problems from the AMC program (AHSME, AMC 8, AMC 10,
AMC 12, AIME, USAMO), the IMO, USA TST/TSTST, and HMMT (February, November,
Invitational).

Field notes:

- The richest records in the database. Every problem has a human-readable
  title, numeric difficulty ratings (`difficulty.course` on a roughly
  0–100 scale, `difficulty.source`, and unified `difficulty.mohs`), and an
  estimated solve time. Nearly all carry concept tags, which no other dataset
  has.
- Ids keep the legacy pattern `prob.<collection>-<year>-p<n>` instead of
  `prob.core-NNNNNN`.
- `answer.letter` holds the choice letter for multiple-choice problems;
  `answer.value` holds the normalized choice text or exact answer (including
  AIME-style numeric answers).
- Many solutions carry progressive hints.
- The database's 22 `strategy` and 18 `answer-only` solutions all live in
  this dataset. Everything else is `proof-sketch`.
- Statement and solution diagrams are SVG images referenced by hash.

| category | problems |
|---|---|
| geometry | 3,790 |
| algebra | 3,483 |
| number-theory | 1,311 |
| combinatorics | 961 |
| arithmetic | 568 |
| probability | 387 |
| logic-foundations | 76 |
| problem-solving-techniques | 55 |
| uncategorized | 14 |

## aops (311)

Competition problems from the AoPS Wiki with community-written solutions.

Field notes:

- `source.collection` names the competition: IMO Shortlist (102), USAJMO
  (91), Canadian MO (83), APMO (28), and Putnam (7). `source.year` and
  `source.number` carry the contest year and problem code.
- Most records have one or more `proof-sketch` solutions, and a few carry an
  exact answer in `answer.value`.
- Every record has a human-readable title and a `source.url`.
- `difficulty.mohs` carries the unified cross-dataset rating.

| category | problems |
|---|---|
| geometry | 102 |
| number-theory | 93 |
| algebra | 76 |
| combinatorics | 35 |
| probability | 2 |
| arithmetic | 1 |
| problem-solving-techniques | 1 |
| uncategorized | 1 |

## cemc (792)

CEMC multiple-choice contests: Gauss (Grade 7) with 174 problems, Gauss
(Grade 8) with 166, Pascal (Grade 9) with 134, Cayley (Grade 10) with 150,
and Fermat (Grade 11) with 168.

Field notes:

- Every problem is multiple choice with five options and has exactly one
  written solution.
- Nearly all problems have both `answer.letter` and `answer.value`.
- `source.url` is set on every record, and `source.tags` labels the contest.
- `difficulty.mohs` carries the unified cross-dataset rating.

| category | problems |
|---|---|
| arithmetic | 300 |
| number-theory | 207 |
| algebra | 109 |
| geometry | 76 |
| probability | 54 |
| combinatorics | 24 |
| uncategorized | 22 |

## olympiadbench (1,389)

OlympiadBench olympiad problems (`source.collection` = `OlympiadBench`).

Field notes:

- `difficulty.note` is `Competition` on every record; `difficulty.mohs`
  carries the unified cross-dataset rating.
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

- `difficulty.note` carries a rating from `omnimath 1` to `omnimath 9.5`;
  `difficulty.mohs` maps that onto the unified `1.0`–`10.0` scale.
- Answers are exact values in `answer.value`.
- `source.tags` names the origin contest, for example
  `china_team_selection_test`.
- Some statements contain inline `[asy]...[/asy]` diagram code.
- Every problem has exactly one written solution.

| category | problems |
|---|---|
| algebra | 1,382 |
| number-theory | 404 |
| combinatorics | 382 |
| geometry | 371 |
| arithmetic | 79 |
| probability | 15 |
| uncategorized | 7 |

## math (12,401)

MATH benchmark problems (`source.collection` = `MATH`).

Field notes:

- `difficulty.note` is `MATH Level 1` (easiest) through `MATH Level 5`
  (hardest); `difficulty.mohs` maps that onto the unified scale.
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
  half steps; `difficulty.mohs` maps that onto the unified scale.
- `source.tags` holds a subject path such as
  `Mathematics -> Geometry -> Plane Geometry -> Angles`.
- The traces live only in the JSONL shards and are excluded from the SQLite
  build. See [`usage.md`](usage.md) for how to read them.

| category | problems |
|---|---|
| algebra | 58,480 |
| geometry | 12,327 |
| number-theory | 9,059 |
| probability | 6,224 |
| combinatorics | 4,505 |
| logic-foundations | 1,364 |
| arithmetic | 280 |
| problem-solving-techniques | 93 |
| uncategorized | 2 |

## numina (840,924)

NuminaMath problems, by far the largest dataset.

Field notes:

- Most problems have exactly one written `proof-sketch` solution, and most
  carry an exact answer in `answer.value`. A minority of problems use
  `answer.letter`.
- `source.tags` records the origin bucket of each problem (for example
  `olympiads`, `cn_k12`, `orca_math`, `synthetic`). A problem can carry
  several tags.
- No titles; `difficulty.mohs` carries the unified cross-dataset rating.

| category | problems |
|---|---|
| algebra | 287,286 |
| geometry | 204,206 |
| arithmetic | 170,552 |
| number-theory | 109,109 |
| probability | 27,733 |
| combinatorics | 23,543 |
| logic-foundations | 17,413 |
| problem-solving-techniques | 1,076 |
| uncategorized | 6 |

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
- No titles and no collection or year fields; `difficulty.mohs` is derived from
  `difficulty.note` (`llama8b_solve_rate`).

| category | problems |
|---|---|
| algebra | 29,131 |
| geometry | 20,571 |
| arithmetic | 10,082 |
| number-theory | 7,679 |
| combinatorics | 4,481 |
| probability | 4,394 |
| logic-foundations | 1,082 |
| uncategorized | 107 |

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
