# Changelog

Versions follow [semantic versioning](https://semver.org). The interfaces
covered from 1.0.0 on are listed under "Stability (1.x)" in the README.

## 1.0.0 (2026-10-19)

First stable release.

### Breaking changes

- MCP tools are renamed to a consistent verb_noun style:
  `arquimedes_stats` is now `arquimedes_get_stats`, `arquimedes_search` is
  `arquimedes_search_problems`, and `arquimedes_sample` is
  `arquimedes_sample_problems`. `arquimedes_get_problem` is unchanged. The old
  names are still accepted by `tools/call` but are no longer listed.
- `answer.letter` now only holds the lowercase choice letter of a
  multiple-choice problem. 1,830 `core` free-response records carried a copy
  of the answer there (`"60"`, LaTeX, lowercased text); their letter is now
  null and `answer.value` is unchanged. Three `omnimath` answers that are a
  player, a person, or a grid letter rather than a choice moved from
  `answer.letter` to `answer.value`.
- `source.number` is an int whenever it is purely numeric. 202 `aops`
  records change from `"1"` to `1`, and 25 HMMT February Guts 2019 records
  change from `"H_{4}"` to `"H4"`. The engine now returns the same type from
  SQLite (which stores the column as TEXT) as from the shards.
- `get_problem` returns the same shape with a full, lean, or missing database.
  Solutions are always `{id, kind, text, hints}`; `include_solutions` controls
  the written solutions and `include_traces` the deepmath reasoning traces.
  Without SQLite it used to return the raw shard record, traces included.
  With SQLite, an unknown id now returns `None` at once instead of scanning
  the shards.
- `has_diagram` now matches only problems with a statement diagram. With
  SQLite it used to match solution-only diagrams too.

### Fixed

- The MCP server no longer exits on bad input. Bad tool arguments and unknown
  ids return tool results with `isError: true`; invalid JSON gets -32700, a
  non-object message -32600, and an unexpected failure -32603.
- `initialize` negotiates the protocol version: a supported client version is
  echoed, anything else gets `2025-11-25`.
- The `math-practice-set` prompt rejects a non-numeric difficulty with -32602
  instead of crashing, and points at the current tool names.
- Sampling is uniform over every matching problem. It used to draw from the
  first 250 or so matches in database order, or from one contiguous block of
  rows when no filter was given.
- Two `omnimath` records whose only solution was a "this problem needs a
  solution" placeholder, with a non-answer extracted from it, now have no
  solution and a null answer. Written solutions: 797,671.
- 25 HMMT February Guts 2019 titles read "Problem H {4}" after an earlier
  cleanup; they now read "Problem H4".
- `prob.hmmt-feb-geometry-2016-p3` held a lowercased solution sketch in its
  answer fields. The sketch is now a solution, and the answer
  (`\frac{25\sqrt{3}}{12}-\frac{4\pi}{3}`) is derived from it.
- 134 `aops` records had `source.number` values like `"Problem_3"`.
- Six `difficulty.note` values were imputed from placeholder labels
  (`MATH Level ?` became `MATH Level 3`, `deepmath -1` became `deepmath 5`).
  They are null now, and `difficulty.mohs` for those records comes from the
  fallback heuristic. Like every `mohs` value it is a calibration.
- The web explorer catalog loaded solutions from the SQLite `solutions` table,
  which is empty in a lean build. It now reads them from the shards, picks the
  same problems regardless of query plan, and deletes unused diagrams.
- `LICENSE` names `arquimedes/` as MIT, as the README and package metadata
  already did.

### Added

- A test suite in `tests/` that builds a five-problem corpus and checks the
  engine in all three database modes, the MCP server, and the CLI, plus a CI
  workflow running it with Python 3.10 and 3.14.
- `tools/build_database.py --root` builds from another directory.
- A `(dataset, category)` index and `ANALYZE` at build time. Filtered sampling
  on the full corpus takes under 200 ms.
- Stricter record validation: `answer.letter` must be a lowercase letter or
  null, and `source.number` an int, a non-numeric string, or null.
- A stability statement in the README and this changelog.

## 0.3.2 (2026-10-19)

- `arquimedes-mcp` answers `resources/templates/list` with an empty list
  instead of -32601 "Method not found".

## 0.3.0 (2026-10-19)

First tagged release.

- 1,038,963 problems across 9 datasets, with written solutions, deepmath
  reasoning traces, diagrams, and a unified `difficulty.mohs` on every record.
- `arquimedes` CLI (`stats`, `search`, `sample`, `show`, `build`, `splits`)
  and the stdio MCP server `arquimedes-mcp`.
- `arquimedes build --lean` builds a 0.8 GB index that reads solutions from
  the shards.
- Decontaminated train and eval splits, and the web explorer on GitHub Pages.
