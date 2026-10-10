#!/usr/bin/env python3
"""Build the Arquimedes problem database from the raw records in raw/.

Inputs:
  raw/meta/catalog.json             problem catalog entries (metadata)
  raw/chunks/c*.json                problem content records (statement/solutions)
  raw/meta/manifest.json            media asset manifest (hash -> [url, [shared-def indexes]])
  raw/media/assets/<hash>.svg       media skeleton SVGs
  raw/media/shared-definitions.json shared SVG <path> definitions

Outputs:
  problems/<category>/<id>.json     one cleaned JSON file per problem
  images/<hash>.svg                 standalone SVGs (shared defs inlined)
  data/problems.sqlite              queryable SQLite database
  data/index.json                   category -> problem summary index
"""
import json
import glob
import os
import re
import sqlite3
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")
PROBLEMS_DIR = os.path.join(ROOT, "problems")
IMAGES_DIR = os.path.join(ROOT, "images")
DATA_DIR = os.path.join(ROOT, "data")

BOILERPLATE_PATTERNS = [
    re.compile(r"Imported content\s*·\s*review pending[^\n]*", re.IGNORECASE),
    re.compile(r"This record has not yet been independently checked[^\n]*", re.IGNORECASE),
    re.compile(r"Check your AIME answer\.?", re.IGNORECASE),
    re.compile(r"Check your answer\.?", re.IGNORECASE),
]


def clean_text(text):
    if not isinstance(text, str):
        return text
    out = text
    for pat in BOILERPLATE_PATTERNS:
        out = pat.sub("", out)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def load_inputs():
    with open(os.path.join(RAW, "meta", "catalog.json")) as f:
        catalog = json.load(f)
    with open(os.path.join(RAW, "meta", "manifest.json")) as f:
        manifest = json.load(f)
    with open(os.path.join(RAW, "media", "shared-definitions.json")) as f:
        shared_defs = json.load(f)
    records = {}
    for path in sorted(glob.glob(os.path.join(RAW, "chunks", "c*.json"))):
        with open(path) as f:
            records.update(json.load(f))
    return catalog, manifest, shared_defs, records


def build_standalone_svg(hash_, skeleton, references, shared_defs):
    """Replicate the app's decodeSvg(): inject shared defs as d0..dN local ids."""
    if references:
        parts = []
        for local_index, def_index in enumerate(references):
            definition = shared_defs[def_index]
            parts.append(definition.replace("<path", f"<path id='d{local_index}'", 1))
        if "<defs/>" in skeleton:
            skeleton = skeleton.replace("<defs/>", f"<defs>{''.join(parts)}</defs>", 1)
        elif "<defs>" not in skeleton:
            # no slot; insert right after the opening <svg ...> tag
            skeleton = re.sub(r"(<svg[^>]*>)", r"\1<defs>" + "".join(parts) + "</defs>", skeleton, count=1)
    return skeleton


def main():
    catalog, manifest, shared_defs, records = load_inputs()
    cat_by_id = {e["id"]: e for e in catalog}
    media_refs = {h: (u[0], u[1]) for h, u in manifest["media"]}

    os.makedirs(PROBLEMS_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    stats = collections.Counter()
    used_images = {}  # hash -> skeleton svg text
    index = collections.defaultdict(list)

    db_path = os.path.join(DATA_DIR, "problems.sqlite")
    if os.path.exists(db_path):
        os.remove(db_path)
    db = sqlite3.connect(db_path)
    db.executescript(
        """
        CREATE TABLE problems (
            id TEXT PRIMARY KEY,
            title TEXT,
            category TEXT,
            subjects TEXT,          -- JSON array
            concepts TEXT,          -- JSON array of {id,label,roles}
            source_collection TEXT,
            source_year INTEGER,
            source_number TEXT,
            difficulty_course REAL,
            difficulty_source REAL,
            difficulty_mohs REAL,
            estimated_minutes REAL,
            statement TEXT NOT NULL,
            answer_letter TEXT,
            answer_value TEXT,
            has_choices INTEGER,
            images TEXT,            -- JSON {statement: [...hash], solutions: [...hash]}
            metadata TEXT           -- JSON of remaining catalog fields
        );
        CREATE TABLE answer_choices (
            problem_id TEXT REFERENCES problems(id),
            label TEXT,
            text TEXT,
            PRIMARY KEY (problem_id, label)
        );
        CREATE TABLE solutions (
            id TEXT PRIMARY KEY,
            problem_id TEXT REFERENCES problems(id),
            kind TEXT,
            text TEXT,
            hints TEXT              -- JSON array
        );
        CREATE TABLE images (
            hash TEXT PRIMARY KEY,
            path TEXT NOT NULL
        );
        CREATE TABLE problem_images (
            problem_id TEXT REFERENCES problems(id),
            image_hash TEXT REFERENCES images(hash),
            role TEXT,              -- 'statement' | 'solution'
            PRIMARY KEY (problem_id, image_hash, role)
        );
        CREATE INDEX idx_problems_category ON problems(category);
        CREATE INDEX idx_problems_source ON problems(source_collection, source_year);
        """
    )

    for pid, rec in sorted(records.items()):
        prob = rec.get("problem") or {}
        statement = clean_text(prob.get("statement") or "")
        if not statement:
            stats["skipped_empty_statement"] += 1
            continue

        cat_entry = cat_by_id.get(pid) or {}
        classification = cat_entry.get("classification") or {}
        category = classification.get("primarySubject") or "uncategorized"
        subjects = classification.get("subjects") or ([category] if category != "uncategorized" else [])
        elements = classification.get("elements") or []
        concepts = [
            {"id": e.get("id"), "label": e.get("label"), "roles": e.get("roles") or []}
            for e in elements
            if isinstance(e, dict)
        ]

        source = cat_entry.get("source") or {}
        course_diff = (cat_entry.get("courseDifficulty") or {}).get("score")
        source_diff = (cat_entry.get("sourceDifficulty") or {}).get("rating")
        mohs = (cat_entry.get("mohsDifficulty") or {})
        mohs_val = mohs.get("rating") if isinstance(mohs, dict) else None

        choices = [
            {"label": c.get("label"), "text": clean_text(c.get("text") or "")}
            for c in (prob.get("answerChoices") or [])
        ]

        sol_objs = []
        answer_letter = None
        answer_value = None
        solution_images = []
        for sid, s in sorted((rec.get("solutions") or {}).items()):
            text = clean_text(s.get("solutionText") or "")
            hints = [clean_text(h) for h in (s.get("hints") or [])]
            sol_imgs = [h for h in (s.get("solutionDiagramIds") or []) if h in media_refs]
            solution_images.extend(sol_imgs)
            if not text and not sol_imgs:
                continue
            if answer_letter is None and s.get("answer"):
                answer_letter = str(s["answer"]).strip().lower() or None
            if answer_value is None and s.get("answerValue"):
                answer_value = str(s["answerValue"]).strip() or None
            sol_objs.append(
                {
                    "id": sid,
                    "kind": s.get("solutionKind"),
                    "text": text,
                    "hints": hints,
                    "images": sol_imgs,
                }
            )
        # fall back to catalog-level answer if solutions carry none
        if answer_letter is None and cat_entry.get("answer"):
            answer_letter = str(cat_entry["answer"]).strip().lower() or None

        stmt_images = [h for h in (prob.get("statementDiagramIds") or []) if h in media_refs]
        for h in stmt_images + solution_images:
            used_images.setdefault(h, None)

        slim = {
            "id": pid,
            "title": cat_entry.get("title") or pid,
            "category": category,
            "subjects": subjects,
            "concepts": concepts,
            "source": {
                "collection": source.get("collection"),
                "year": source.get("year"),
                "number": source.get("number"),
            },
            "difficulty": {
                "course": course_diff,
                "source": source_diff,
                "mohs": mohs_val,
            },
            "estimatedMinutes": cat_entry.get("estimatedMinutes"),
            "statement": statement,
            "answerChoices": choices,
            "answer": {"letter": answer_letter, "value": answer_value},
            "solutions": sol_objs,
            "images": {
                "statement": stmt_images,
                "solutions": sorted(set(solution_images)),
            },
        }

        cat_dir = os.path.join(PROBLEMS_DIR, category)
        os.makedirs(cat_dir, exist_ok=True)
        with open(os.path.join(cat_dir, f"{pid}.json"), "w") as f:
            json.dump(slim, f, indent=2, ensure_ascii=False)

        index[category].append(
            {
                "id": pid,
                "title": slim["title"],
                "source": slim["source"],
                "answer": answer_value or answer_letter,
                "hasChoices": bool(choices),
                "images": len(stmt_images) + len(set(solution_images)),
                "difficulty": slim["difficulty"],
            }
        )

        extra_meta = {
            k: cat_entry.get(k)
            for k in ("tags", "reviewState", "importOrigin", "liveMatchStatus", "references", "dataIssues")
            if cat_entry.get(k) not in (None, "", [], {})
        }
        db.execute(
            "INSERT INTO problems VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                pid,
                slim["title"],
                category,
                json.dumps(subjects, ensure_ascii=False),
                json.dumps(concepts, ensure_ascii=False),
                source.get("collection"),
                source.get("year") if isinstance(source.get("year"), int) else None,
                str(source.get("number")) if source.get("number") is not None else None,
                course_diff,
                source_diff,
                mohs_val,
                cat_entry.get("estimatedMinutes"),
                statement,
                answer_letter,
                answer_value,
                int(bool(choices)),
                json.dumps(slim["images"]),
                json.dumps(extra_meta, ensure_ascii=False),
            ),
        )
        for c in choices:
            db.execute("INSERT INTO answer_choices VALUES (?,?,?)", (pid, c["label"], c["text"]))
        for s in sol_objs:
            db.execute(
                "INSERT INTO solutions VALUES (?,?,?,?,?)",
                (s["id"], pid, s["kind"], s["text"], json.dumps(s["hints"], ensure_ascii=False)),
            )
        stats[f"category.{category}"] += 1
        stats["total"] += 1

    # write standalone SVGs for every referenced image
    for h in sorted(used_images):
        skel_path = os.path.join(RAW, "media", "assets", f"{h}.svg")
        if not os.path.exists(skel_path):
            stats["missing_image_skeleton"] += 1
            continue
        with open(skel_path) as f:
            skeleton = f.read()
        _, references = media_refs[h]
        svg = build_standalone_svg(h, skeleton, references, shared_defs)
        rel = f"images/{h}.svg"
        with open(os.path.join(ROOT, rel), "w") as f:
            f.write(svg)
        db.execute("INSERT INTO images VALUES (?,?)", (h, rel))
        stats["images_written"] += 1

    # link table
    for pid, rec in records.items():
        prob = rec.get("problem") or {}
        for h in prob.get("statementDiagramIds") or []:
            if h in media_refs:
                db.execute("INSERT OR IGNORE INTO problem_images VALUES (?,?,?)", (pid, h, "statement"))
        for s in (rec.get("solutions") or {}).values():
            for h in s.get("solutionDiagramIds") or []:
                if h in media_refs:
                    db.execute("INSERT OR IGNORE INTO problem_images VALUES (?,?,?)", (pid, h, "solution"))

    db.commit()

    for cat, items in index.items():
        items.sort(key=lambda e: (e["source"].get("collection") or "", e["source"].get("year") or 0, e["id"]))
    with open(os.path.join(DATA_DIR, "index.json"), "w") as f:
        json.dump(
            {
                "totalProblems": stats["total"],
                "categories": {cat: len(items) for cat, items in sorted(index.items())},
                "problems": {cat: items for cat, items in sorted(index.items())},
            },
            f,
            indent=1,
            ensure_ascii=False,
        )

    db.close()
    print(json.dumps(dict(stats), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
