"""Copyright stamp for each dataset slice.

The git shards stay as they are. The Hugging Face export copies a record and
adds ``rights``, taken from data/rights.json. A stamp records the holder and
the license the distributor actually attached. It does not create a new grant.
``distribution`` is null when no open license was found.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "data" / "rights.json"

_AOPS = {
    "IMO Shortlist": "imo-shortlist",
    "APMO": "apmo",
    "Canadian MO": "cmo",
}


def load_catalog(path=None):
    path = Path(path) if path else CATALOG_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def part_id(rec):
    """Return the rights part id for one v2 record."""
    source = rec.get("source") or {}
    dataset = source.get("dataset")
    collection = source.get("collection") or ""
    if dataset == "cemc":
        return "cemc"
    if dataset == "core":
        if collection.startswith("HMMT"):
            return "hmmt"
        if collection == "IMO":
            return "imo"
        return "maa"
    if dataset == "aops":
        return _AOPS.get(collection, "maa")
    if dataset in ("math", "deepmath", "olympiadbench", "omnimath"):
        return dataset
    if dataset in ("numina", "bigmath"):
        origin = next((tag for tag in (source.get("tags") or []) if "->" not in tag), None)
        if not origin:
            raise KeyError(f"{dataset} record {rec.get('id')} has no origin tag")
        return f"{dataset}/{origin}"
    raise KeyError(f"no rights rule for dataset {dataset!r} on {rec.get('id')}")


def rights_for(rec, catalog=None):
    """Return the rights object to store on a published record.

    Does not modify ``rec``.
    """
    catalog = catalog if catalog is not None else load_catalog()
    part = part_id(rec)
    try:
        entry = catalog["parts"][part]
    except KeyError:
        raise KeyError(f"rights catalog has no part {part!r} for {rec.get('id')}") from None
    return {
        "part": part,
        "holder": entry["holder"],
        "distribution": entry["distribution"],
        "use": entry["use"],
        "notice": entry["notice"],
    }


def stamp(rec, catalog=None):
    """Copy ``rec`` and set ``rights``. The input record is left unchanged."""
    stamped = dict(rec)
    stamped["rights"] = rights_for(rec, catalog)
    return stamped
