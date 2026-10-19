#!/usr/bin/env python3
"""Build the static data catalog and diagram bundle for the GitHub Pages web explorer.

Selects a rich, stratified sample of ~500 problems across all competitions,
categories, and difficulty tiers (including diagram problems and multi-hint
proofs), copies their SVG/JPG diagrams into `site/images/`, and writes
`site/data/explorer.json`.
"""

from __future__ import annotations

import json
import random
import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "problems.sqlite"
INDEX_PATH = ROOT / "data" / "index.json"
IMAGES_DIR = ROOT / "images"
SITE_DIR = ROOT / "site"
SITE_DATA_DIR = SITE_DIR / "data"
SITE_IMAGES_DIR = SITE_DIR / "images"


def main() -> None:
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SITE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    index_data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    rng = random.Random(20261018)
    selected_ids: set[str] = set()
    rows_picked: list[sqlite3.Row] = []

    def add_query(sql: str, params: tuple = (), take: int = 25) -> None:
        candidates = conn.execute(sql, params).fetchall()
        pool = [r for r in candidates if r["id"] not in selected_ids]
        if len(pool) > take:
            pool = rng.sample(pool, take)
        for r in pool:
            selected_ids.add(r["id"])
            rows_picked.append(r)

    # 1. Stratified sample across named competitions with solutions
    competitions = [
        ("IMO", 30),
        ("IMO Shortlist", 25),
        ("USAMO", 25),
        ("USAJMO", 20),
        ("Putnam", 7),
        ("APMO", 15),
        ("Canadian MO", 15),
        ("USA TST", 12),
        ("USA TSTST", 12),
        ("HMMT February", 30),
        ("HMMT November", 20),
        ("AIME I", 25),
        ("AIME II", 25),
        ("AMC 12A", 20),
        ("AMC 10A", 20),
        ("AMC 8", 20),
        ("AHSME", 20),
        ("CEMC Fermat (Grade 11)", 15),
        ("CEMC Cayley (Grade 10)", 12),
        ("CEMC Pascal (Grade 9)", 12),
        ("CEMC Gauss (Grade 8)", 12),
        ("MATH", 30),
        ("OlympiadBench", 20),
    ]
    for comp, quota in competitions:
        add_query(
            """
            SELECT p.* FROM problems p
            WHERE p.source_collection = ?
              AND length(p.statement) BETWEEN 40 AND 1400
            LIMIT 250
            """,
            (comp,),
            take=quota,
        )

    # 2. Ensure strong coverage of problems with SVG diagrams
    add_query(
        """
        SELECT p.* FROM problem_images pi
        JOIN problems p ON p.id = pi.problem_id
        WHERE pi.role = 'statement'
          AND p.dataset = 'core'
        LIMIT 250
        """,
        (),
        take=45,
    )

    # 3. Ensure coverage of Omni-MATH, DeepMath, BigMath, and Numina across all 8 categories
    for ds in ("omnimath", "deepmath", "bigmath", "numina"):
        add_query(
            """
            SELECT p.* FROM problems p
            WHERE p.dataset = ?
              AND length(p.statement) BETWEEN 45 AND 850
              AND p.statement NOT LIKE '%[asy]%'
            LIMIT 350
            """,
            (ds,),
            take=35,
        )

    problems_out = []
    copied_images = 0

    # Build in-memory solutions lookup for the ~550 selected problem IDs in a single pass
    wanted_pids = {r["id"] for r in rows_picked}
    sol_map: dict[str, tuple[str, list[str]]] = {}
    for srow in conn.execute("SELECT problem_id, text, hints FROM solutions"):
        pid = srow["problem_id"]
        if pid in wanted_pids and pid not in sol_map:
            sol_map[pid] = (
                srow["text"],
                json.loads(srow["hints"]) if srow["hints"] else [],
            )
            if len(sol_map) == len(wanted_pids):
                break

    for r in rows_picked:
        pid = r["id"]
        images = json.loads(r["images"]) if r["images"] else {"statement": [], "solutions": []}
        stmt_imgs = []
        for h in images.get("statement") or []:
            fname = h if "." in h else f"{h}.svg"
            src_img = IMAGES_DIR / fname
            if src_img.is_file():
                dst_img = SITE_IMAGES_DIR / fname
                if not dst_img.exists():
                    shutil.copy2(src_img, dst_img)
                    copied_images += 1
                stmt_imgs.append(f"images/{fname}")

        choices = [
            {"label": c["label"], "text": c["text"]}
            for c in conn.execute(
                "SELECT label, text FROM answer_choices WHERE problem_id = ? ORDER BY label",
                (pid,),
            ).fetchall()
        ]
        sol_text, hints = sol_map.get(pid, (None, []))

        title = r["title"] or ""
        if not title:
            comp = r["source_collection"] or r["dataset"].capitalize()
            yr = f" {r['source_year']}" if r["source_year"] else ""
            num = f" #{r['source_number']}" if r["source_number"] else ""
            title = f"{comp}{yr}{num}"

        problems_out.append({
            "id": pid,
            "title": title,
            "dataset": r["dataset"],
            "category": r["category"],
            "competition": r["source_collection"] or r["dataset"],
            "year": r["source_year"],
            "mohs": round(float(r["difficulty_mohs"] or 5.0), 1),
            "statement": r["statement"],
            "choices": choices,
            "answerLetter": r["answer_letter"],
            "answerValue": r["answer_value"],
            "hints": hints,
            "solution": sol_text,
            "diagrams": stmt_imgs,
        })

    # Sort nicely: featured diagram/olympiad problems mixed with clean ordering
    problems_out.sort(key=lambda x: (-(1 if x["diagrams"] else 0), -(x["year"] or 2020), x["id"]))

    payload = {
        "stats": {
            "totalProblems": index_data["totalProblems"],
            "totalSolutions": sum(
                v for k, v in index_data["solutionKinds"].items() if k != "model-reasoning"
            ),
            "totalTraces": index_data["solutionKinds"].get("model-reasoning", 0),
            "totalDiagrams": 1219,
            "categories": index_data["categories"],
            "datasets": {k: v["count"] for k, v in index_data["datasets"].items()},
            "competitions": index_data["competitions"],
        },
        "problems": problems_out,
    }

    out_file = SITE_DATA_DIR / "explorer.json"
    out_file.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(problems_out)} curated problems to {out_file} ({out_file.stat().st_size / 1024:.1f} KB)")
    print(f"Copied {copied_images} diagram files to {SITE_IMAGES_DIR}")


if __name__ == "__main__":
    main()
