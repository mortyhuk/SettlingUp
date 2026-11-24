"""Document reading (demo).

There is no API key for the hackathon, so reading is mock only: after a short pause we return the
prepared result from data/families/<family>/expected.json. The result is checked the same way a
real AI answer would be. The AI never decides tax rules; it only reads documents.

Which fields to look for in each document comes from the case type's documents.yaml (fields).
"""

import json
import time
from pathlib import Path

FAMILIES_DIR = Path(__file__).resolve().parent.parent / "data" / "families"
READING_PAUSE_SECONDS = 1.2
CONFIDENCE = ("low", "medium", "high")


def family_from_file_name(file_name, default):
    """Sample files are named like b_pension_statement.pdf. Otherwise use the family picked in the sidebar."""
    first = Path(file_name).name[:2].lower()
    if len(first) == 2 and first[1] == "_" and first[0].isalpha() and (FAMILIES_DIR / first[0]).is_dir():
        return first[0]
    return default


def validate(entry, doc_type, wanted):
    """Check a reading result has the right shape. Raises ValueError if it does not."""
    if not isinstance(entry, dict) or entry.get("document_type") != doc_type:
        raise ValueError("wrong document type")
    if entry.get("confidence") not in CONFIDENCE:
        raise ValueError("bad confidence")
    fields = entry.get("fields")
    if not isinstance(fields, dict):
        raise ValueError("fields missing")
    missing = [f for f in wanted if fields.get(f) in (None, "")]
    return {
        "document_type": doc_type,
        "fields": {f: fields.get(f) for f in wanted},
        "missing_fields": sorted(set(missing) | set(entry.get("missing_fields") or [])),
        "confidence": entry["confidence"],
        "read_ok": True,
    }


def could_not_read(doc_type, wanted):
    return {
        "document_type": doc_type,
        "fields": {},
        "missing_fields": list(wanted),
        "confidence": "low",
        "read_ok": False,
    }


def read_document(doc, file_name, default_family):
    """Read one uploaded document. doc is its entry in documents.yaml (reads_as and fields).

    Returns the fields found, missing_fields and confidence.
    """
    doc_type, wanted = doc["reads_as"], doc.get("fields", [])
    time.sleep(READING_PAUSE_SECONDS)
    family = family_from_file_name(file_name, default_family)
    try:
        with open(FAMILIES_DIR / family / "expected.json", encoding="utf-8") as f:
            entry = json.load(f)["documents"][doc_type]
        return validate(entry, doc_type, wanted)
    except (OSError, KeyError, ValueError):
        return could_not_read(doc_type, wanted)


def show_value(value):
    """Numbers become 18,000 (or 18,000.50). Everything else is shown as it is."""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def describe(template, fields):
    """Fill a 'found' template from documents.yaml, e.g. '£{annual_amount} a year from {provider}'."""
    return template.format_map({k: show_value(v) for k, v in fields.items()})
