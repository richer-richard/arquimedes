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
  store the exact answer in `answer.value`. `answer.letter` is only ever the
  lowercase choice letter of a multiple-choice problem.

## Licenses and attribution

The statements, solutions, answers, and diagrams are third-party material.
This repository does not hold those copyrights and does not relicense them.
An earlier `LICENSE` placed `problems/`, `images/`, and `data/` under
CC BY 4.0. That sentence was this project's claim. It was not a grant from
the contest organizers or the dataset authors, and it does not apply to that
text.

CC BY 4.0 applies only to annotations this project created: the Mohs
calibration in `difficulty.mohs`, the category labels assigned here, and
[`data/index.json`](../data/index.json). The calibration is a mapping onto a
1–10 scale, not a measurement supplied by the sources. Code in
`arquimedes/`, `tools/`, and `site/` is MIT. See [`LICENSE`](../LICENSE).

The notes below are the terms those sources publish. They are not a legal
opinion. A dataset card that says Apache 2.0 or MIT is the distributor's
claim about its release. It does not, by itself, show that a contest
organizer or a forum licensed the underlying problems.

| dataset | copied from | license the distributor attached | underlying works |
|---|---|---|---|
| `core` | legacy contest records already in this repository; no source URL is stored | none | MAA contests, the IMO, and HMMT |
| `aops` | AoPS Wiki problem pages | none found on the wiki | MAA contests, the IMO Shortlist, the APMO, and the Canadian Mathematical Olympiad |
| `cemc` | CEMC past contests | CC BY-NC 4.0, plus a no-fee condition | University of Waterloo |
| `olympiadbench` | `Hothan/OlympiadBench`, English maths competition configs | Hugging Face card: Apache 2.0. Code repository: MIT | official olympiad papers, OCR'd |
| `omnimath` | `KbsdJames/Omni-MATH` | Hugging Face metadata: Apache 2.0. The GitHub repository has no `LICENSE` file | official contest pages and AoPS |
| `math` | `DigitalLearningGmbH/MATH-lighteval`, a mirror of Hendrycks MATH | MIT, copyright 2021 Dan Hendrycks | competition problems |
| `deepmath` | `zwhe99/DeepMath-103K` | MIT | questions from Apache 2.0 collections; three DeepSeek-R1 traces per problem |
| `numina` | `AI-MO/NuminaMath-1.5` | Apache 2.0 | contests, exams, forums, and synthetic sets |
| `bigmath` | `SynthLabsAI/Big-Math-RL-Verified` | Apache 2.0 on the dataset card. Filtering code: MIT | the source labels listed below |

Diagrams are not licensed separately. JPG diagrams belong to `olympiadbench`
records, and SVG diagrams belong to `core` records.

`open-r1/OpenR1-Math-220k` is Apache 2.0. Every record matched a `numina`
record, so it is not a separate dataset. See the deduplication section.

### core

`core` has no `source.url`. The files were already in this repository, and
the ingestion path behind that legacy copy was not recorded.

The MAA contests in this dataset are AHSME, AMC 8, AMC 10, AMC 10A, AMC 10B,
AMC 12, AMC 12A, AMC 12B, AIME, AIME I, AIME II, USAMO, USA TST, and USA
TSTST. Printed AMC and AIME booklets carry a copyright notice of the
Mathematical Association of America. After the contest period, the notice
commonly grants permission to copy individual problems for educational use
without a fee, provided the copies are not made or distributed for profit or
commercial advantage and the copyright notice is kept. The wording is not the
same on every booklet: some allow paper or electronic copies, including a web
page, and some AMC 8 booklets allow paper copies only. That is not CC BY 4.0.
The current [MAA competition policies](https://maa.org/student-programs/amc/maa-amc-policies/)
restrict discussion and copying during the contest period. They are not an
open license for the archive.

The 156 IMO problems have no open license on the pages checked for this
review. HMMT publishes past problems at
<https://www.hmmt.co/www/archive/problems>. Its
[privacy policy](https://hmmt.co/www/privacy) says rights in publicly available
site information are held by HMMT and its organizers. No open license was
found.

### aops

All 311 records link to an AoPS Wiki problem page, for example
<https://artofproblemsolving.com/wiki/index.php/1989_APMO_Problems/Problem_1>.
The collections are the IMO Shortlist (102), USAJMO (91), the Canadian
Mathematical Olympiad (83), the APMO (28), and the Putnam (7).

[AoPS Wiki:Copyright](https://artofproblemsolving.com/wiki/index.php/AoPS_Wiki:Copyright)
does not name a documentation license, and the wiki's copyright talk page
says none has been chosen. The wiki footer is "Copyright © Art of Problem
Solving". The [AoPS terms of service](https://artofproblemsolving.com/company/tos)
say, in section 18, that materials presented through the service may be used
for information purposes only. Section 7 grants AoPS a license to user posts.
It does not grant the public a license to copy them. The wiki's
[MAA notice](https://artofproblemsolving.com/wiki/index.php/Template:MAA_Notice)
says MAA problems are copyrighted by the Mathematical Association of America.
USAJMO and the Putnam are MAA contests. No open license was found for the IMO
Shortlist, the APMO, or the Canadian Mathematical Olympiad.

### cemc

Every record cites <https://cemc.uwaterloo.ca/resources/past-contests>. The
[CEMC copyright page](https://cemc.uwaterloo.ca/copyright) says materials owned
by the University of Waterloo are licensed under CC BY-NC 4.0, and that
nobody may charge a fee for access to past contests and other CEMC resources.
CC BY-NC 4.0 does not allow commercial use, and it cannot be restated as
CC BY 4.0.

### olympiadbench

Imported from
<https://huggingface.co/datasets/Hothan/OlympiadBench>, and only the English
maths competition configs (`OE_TO_maths_en_COMP`, `TP_TO_maths_en_COMP`,
`OE_MM_maths_en_COMP`, `TP_MM_maths_en_COMP`). The Hugging Face dataset card
is tagged Apache 2.0. The code repository
<https://github.com/OpenBMB/OlympiadBench> is MIT, copyright 2024 OpenBMB, and
its README says the problems were parsed with Mathpix from official PDFs of
international olympiads, Chinese olympiads, and the Gaokao. Those organizers
are not the MIT or Apache licensors.

### omnimath

Imported from
<https://github.com/KbsdJames/Omni-MATH> (`Omni-Math.jsonl`). That repository
has no `LICENSE` file. The Hugging Face dataset
<https://huggingface.co/datasets/KbsdJames/Omni-MATH> is tagged Apache 2.0 in
its metadata. The paper, [arXiv:2410.07985](https://arxiv.org/abs/2410.07985),
says the problems were taken from official contest sites, the AoPS Wiki, and
the AoPS forum. The same AoPS and contest limits as `aops` and `core` apply
to that text.

### math

Imported from
<https://huggingface.co/datasets/DigitalLearningGmbH/MATH-lighteval>, a mirror
of Hendrycks MATH. The mirror points at
<https://github.com/hendrycks/math/blob/master/LICENSE>, which is the MIT
License, copyright 2021 Dan Hendrycks. The problems are competition problems.
The MIT grant is the dataset author's. It is not a grant from the contest
organizers.

### deepmath

Imported from <https://huggingface.co/datasets/zwhe99/DeepMath-103K>. The
dataset card and <https://github.com/zwhe99/DeepMath> are MIT. The paper,
[arXiv:2504.11456](https://arxiv.org/abs/2504.11456), Appendix D, lists the
question sources it used as Apache 2.0: MMIQC, WebInstructSub, and
NuminaMath-CoT. Each problem in this repository carries three
`model-reasoning` traces from that release, generated with DeepSeek-R1.
DeepSeek licenses the R1 code and weights under MIT
(<https://github.com/deepseek-ai/DeepSeek-R1>). The questions inside the
Apache 2.0 sources include contest and web text, so the MIT tag on DeepMath
does not clear those underlying rights.

### numina

Imported from <https://huggingface.co/datasets/AI-MO/NuminaMath-1.5>. The
dataset card says the dataset is available under Apache 2.0. After this
repository's English-language filter and deduplication, the origin tag on the
840,924 kept records is:

| origin tag | problems |
|---|---:|
| `cn_k12` | 261,780 |
| `olympiads` | 172,562 |
| `orca_math` | 143,435 |
| `synthetic_math` | 143,185 |
| `aops_forum` | 65,111 |
| `cn_contest` | 27,171 |
| `metamath` | 9,881 |
| `inequalities` | 6,769 |
| `amc_aime` | 4,532 |
| `number_theory` | 3,469 |
| `olympiads_ref` | 3,029 |

The NuminaMath technical report says the AMC and AIME statements were
collected from the AoPS Wiki, and that the AoPS forum's contest collection
was crawled. Those portions are the same AoPS and MAA material described
above, with an Apache 2.0 tag added by the dataset authors.

### bigmath

Imported from
<https://huggingface.co/datasets/SynthLabsAI/Big-Math-RL-Verified>. The
dataset card is tagged Apache 2.0. Hugging Face requires an access token to
download the parquet. The filtering code at
<https://github.com/SynthLabsAI/big-math> is MIT and is not the dataset. The
paper, [arXiv:2502.17387](https://arxiv.org/abs/2502.17387), describes the
upstream collection. After deduplication, the source label stored on the
77,527 records in this repository is:

| source label | problems |
|---|---:|
| `big_math` | 38,615 |
| `olympiads` | 31,665 |
| `harp` | 2,257 |
| `cn_k12` | 1,395 |
| `aops_forum` | 1,293 |
| `orca_math` | 1,269 |
| `gsm8k` | 618 |
| `openmath` | 359 |
| `omnimath` | 54 |
| `amc_aime` | 2 |

`aops_forum`, `amc_aime`, `olympiads`, and `omnimath` are contest and forum
text. The Apache 2.0 tag does not replace those terms.

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
- `answer.letter` holds the choice letter for multiple-choice problems and is
  null for free-response problems; `answer.value` holds the normalized choice
  text or exact answer (including AIME-style numeric answers).
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
  (91), Canadian MO (83), APMO (28), and Putnam (7). `source.year` carries
  the contest year and `source.number` the problem number (an int such as
  `3`) or code (a string such as `"A1"`).
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
- Every problem but two has exactly one written solution. Those two had only
  a "this problem needs a solution" placeholder, which was removed.

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
  carry an exact answer in `answer.value`. About 59,000 multiple-choice
  problems also carry `answer.letter`; their choices are written inline in the
  statement, so `answerChoices` is empty.
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
