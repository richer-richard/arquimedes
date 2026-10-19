"""Command-line interface for the Arquimedes math problem database."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from typing import Any

from arquimedes.engine import ArquimedesEngine


def _truncate(text: str, width: int = 160) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= width:
        return clean
    return clean[: width - 1] + "…"


def _print_problem_card(p: dict[str, Any], full: bool = False) -> None:
    pid = p.get("id", "")
    title = p.get("title") or ""
    ds = p.get("dataset") or (p.get("source") or {}).get("dataset") or ""
    cat = p.get("category") or ""
    comp = p.get("competition") or (p.get("source") or {}).get("collection") or ""
    mohs = p.get("mohs") if "mohs" in p else (p.get("difficulty") or {}).get("mohs")
    ans_val = p.get("answerValue") if "answerValue" in p else (p.get("answer") or {}).get("value")
    ans_let = p.get("answerLetter") if "answerLetter" in p else (p.get("answer") or {}).get("letter")

    header_parts = [f"\033[1;36m{pid}\033[0m"]
    if title:
        header_parts.append(f"\033[1m{title}\033[0m")
    meta = [f"dataset={ds}", f"category={cat}"]
    if comp:
        meta.append(f"competition={comp}")
    if mohs is not None:
        meta.append(f"mohs={mohs:.1f}/10")
    header_parts.append(f"\033[90m({' · '.join(meta)})\033[0m")
    print("  ".join(header_parts))

    stmt = p.get("statement") or ""
    if full:
        print("\n" + stmt.strip() + "\n")
        choices = p.get("answerChoices") or []
        if choices:
            print("\033[1mChoices:\033[0m")
            for ch in choices:
                print(f"  ({ch.get('label')}) {ch.get('text')}")
            print()
        if ans_val is not None or ans_let is not None:
            ans_str = f"{ans_val}" if ans_val is not None else f"({ans_let})"
            if ans_let and ans_val and ans_let.lower() != str(ans_val).lower():
                ans_str = f"({ans_let.upper()}) {ans_val}"
            print(f"\033[1;33mAnswer:\033[0m {ans_str}")
        imgs = (p.get("images") or {}).get("statement") or []
        if imgs:
            img_paths = [f"images/{h}.svg" if "." not in h else f"images/{h}" for h in imgs]
            print(f"\033[1;32mDiagrams:\033[0m {', '.join(img_paths)}")
        sols = p.get("solutions") or []
        for idx, sol in enumerate(sols, 1):
            kind = sol.get("kind", "solution")
            hints = sol.get("hints") or []
            if hints:
                print(f"\n\033[1;35mHints ({len(hints)}):\033[0m")
                for h_i, h in enumerate(hints, 1):
                    print(f"  {h_i}. {h}")
            print(f"\n\033[1;34mSolution {idx} [{kind}]:\033[0m\n{sol.get('text', '').strip()}")
    else:
        print(f"  {_truncate(stmt, 140)}")
        if ans_val is not None or ans_let is not None:
            ans_disp = ans_val if ans_val is not None else ans_let
            print(f"  \033[33mAnswer:\033[0m {_truncate(str(ans_disp), 80)}")


def cmd_stats(engine: ArquimedesEngine, args: argparse.Namespace) -> int:
    stats = engine.get_stats()
    if args.json:
        print(json.dumps(stats, indent=2))
        return 0
    total = stats.get("totalProblems", 0)
    sqlite_ok = "ready" if stats.get("sqliteReady") else "not built (run `arquimedes build`)"
    print(f"\033[1mArquimedes Math Problem Database\033[0m — \033[1;36m{total:,}\033[0m problems")
    print(f"SQLite + FTS5 engine: {sqlite_ok}\n")

    print("\033[1mDatasets:\033[0m")
    for slug, info in sorted((stats.get("datasets") or {}).items(), key=lambda kv: -kv[1]["count"]):
        print(f"  {slug:15s} {info['count']:>10,d}")

    print("\n\033[1mCategories:\033[0m")
    for cat, cnt in sorted((stats.get("categories") or {}).items(), key=lambda kv: -kv[1]):
        pct = (100.0 * cnt / total) if total else 0.0
        print(f"  {cat:28s} {cnt:>10,d}  ({pct:5.2f}%)")

    print("\n\033[1mSolution Kinds:\033[0m")
    for kind, cnt in sorted((stats.get("solutionKinds") or {}).items(), key=lambda kv: -kv[1]):
        print(f"  {kind:20s} {cnt:>10,d}")
    return 0


def cmd_search(engine: ArquimedesEngine, args: argparse.Namespace) -> int:
    t0 = time.perf_counter()
    results = engine.search(
        args.query,
        category=args.category,
        dataset=args.dataset,
        competition=args.competition,
        min_mohs=args.min_mohs,
        max_mohs=args.max_mohs,
        limit=args.limit,
    )
    dt_ms = (time.perf_counter() - t0) * 1000.0
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0
    print(f"\033[90mFound {len(results)} result(s) in {dt_ms:.1f} ms\033[0m\n")
    for p in results:
        _print_problem_card(p, full=False)
        print()
    return 0


def cmd_sample(engine: ArquimedesEngine, args: argparse.Namespace) -> int:
    t0 = time.perf_counter()
    results = engine.sample(
        category=args.category,
        dataset=args.dataset,
        competition=args.competition,
        year=args.year,
        min_mohs=args.min_mohs,
        max_mohs=args.max_mohs,
        has_choices=True if args.multiple_choice else None,
        has_diagram=True if args.has_diagram else None,
        limit=args.limit,
        seed=args.seed,
    )
    dt_ms = (time.perf_counter() - t0) * 1000.0
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0
    print(f"\033[90mSampled {len(results)} problem(s) in {dt_ms:.1f} ms\033[0m\n")
    for p in results:
        _print_problem_card(p, full=False)
        print()
    return 0


def cmd_show(engine: ArquimedesEngine, args: argparse.Namespace) -> int:
    prob = engine.get_problem(args.problem_id, include_solutions=not args.no_solutions, include_traces=args.traces)
    if prob is None:
        print(f"Problem not found: {args.problem_id}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(prob, indent=2, ensure_ascii=False))
        return 0
    _print_problem_card(prob, full=True)
    return 0


def cmd_build(engine: ArquimedesEngine, _args: argparse.Namespace) -> int:
    script = engine.root / "tools" / "build_database.py"
    return subprocess.call([sys.executable, str(script)])


def cmd_splits(engine: ArquimedesEngine, args: argparse.Namespace) -> int:
    script = engine.root / "tools" / "export_splits.py"
    cmd = [sys.executable, str(script), "--out-dir", str(args.out_dir)]
    if args.stats_only:
        cmd.append("--stats-only")
    return subprocess.call(cmd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arquimedes",
        description="Fast CLI for the Arquimedes 1.04M competition & benchmark math problem database.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_stats = sub.add_parser("stats", help="Show corpus counts by dataset, category, and competition")
    p_stats.add_argument("--json", action="store_true", help="Emit JSON output")
    p_stats.set_defaults(func=cmd_stats)

    p_search = sub.add_parser("search", help="Full-text search across 1.04M math problems (FTS5)")
    p_search.add_argument("query", help="Search keywords, theorem name, or LaTeX snippet")
    p_search.add_argument("-c", "--category", help="Filter by category (e.g. geometry, number-theory, algebra)")
    p_search.add_argument("-d", "--dataset", help="Filter by dataset slug (e.g. core, omnimath, math, numina)")
    p_search.add_argument("--competition", help="Filter by competition (e.g. IMO, USAMO, AIME I, Putnam)")
    p_search.add_argument("--min-mohs", type=float, help="Minimum Mohs difficulty (1.0 to 10.0)")
    p_search.add_argument("--max-mohs", type=float, help="Maximum Mohs difficulty (1.0 to 10.0)")
    p_search.add_argument("-n", "--limit", type=int, default=10, help="Max results (default: 10)")
    p_search.add_argument("--json", action="store_true", help="Emit JSON output")
    p_search.set_defaults(func=cmd_search)

    p_sample = sub.add_parser("sample", help="Sample random math problems with filters")
    p_sample.add_argument("-c", "--category", help="Filter by category")
    p_sample.add_argument("-d", "--dataset", help="Filter by dataset slug")
    p_sample.add_argument("--competition", help="Filter by competition")
    p_sample.add_argument("--year", type=int, help="Filter by contest year")
    p_sample.add_argument("--min-mohs", type=float, help="Minimum Mohs difficulty (1.0 to 10.0)")
    p_sample.add_argument("--max-mohs", type=float, help="Maximum Mohs difficulty (1.0 to 10.0)")
    p_sample.add_argument("--multiple-choice", action="store_true", help="Only multiple-choice problems")
    p_sample.add_argument("--has-diagram", action="store_true", help="Only problems with SVG/JPG diagrams")
    p_sample.add_argument("-n", "--limit", type=int, default=5, help="Number of problems to sample (default: 5)")
    p_sample.add_argument("--seed", type=int, help="Random seed for reproducible sampling")
    p_sample.add_argument("--json", action="store_true", help="Emit JSON output")
    p_sample.set_defaults(func=cmd_sample)

    p_show = sub.add_parser("show", help="Display a single problem with statement, answer, hints, and solutions")
    p_show.add_argument("problem_id", help="Problem ID (e.g. prob.ahsme-1950-p10 or prob.aops-000000)")
    p_show.add_argument("--no-solutions", action="store_true", help="Omit solutions from output")
    p_show.add_argument("--traces", action="store_true", help="Include model-reasoning traces from deepmath shards")
    p_show.add_argument("--json", action="store_true", help="Emit full v2 JSON record")
    p_show.set_defaults(func=cmd_show)

    p_build = sub.add_parser("build", help="Build data/problems.sqlite (with FTS5) and data/index.json from shards")
    p_build.set_defaults(func=cmd_build)

    p_splits = sub.add_parser("splits", help="Export decontaminated train/eval splits")
    p_splits.add_argument("--out-dir", default="splits", help="Output directory (default: splits)")
    p_splits.add_argument("--stats-only", action="store_true", help="Compute stats without writing files")
    p_splits.set_defaults(func=cmd_splits)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    engine = ArquimedesEngine()
    return args.func(engine, args)


if __name__ == "__main__":
    sys.exit(main())
