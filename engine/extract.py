"""Document reading (demo).

There is no API key for the hackathon, so reading is mock only: after a short pause we return the
prepared result from data/families/<family>/expected.json. The result is checked the same way a
real AI answer would be. The AI never decides tax rules; it only reads documents.
"""

import json
import time
from pathlib import Path

FAMILIES_DIR = Path(__file__).resolve().parent.parent / "data" / "families"
FAMILIES = ("a", "b", "c")
READING_PAUSE_SECONDS = 1.2

# The fields we ask for, per document type (from CLAUDE.md).
FIELDS = {
    "death_certificate": ["full_name", "date_of_death"],
    "p45_p60": ["employer", "pay_to_date", "tax_to_date", "tax_year"],
    "payslip": ["employer", "pay_to_date", "tax_to_date", "tax_year"],
    "pension_statement": ["provider", "annual_amount", "tax_deducted"],
    "interest_letter": ["bank", "interest_amount", "tax_year"],
    "dividend_statement": ["company", "dividend_amount", "payment_date"],
    "rental_summary": ["rent_received", "expenses", "period"],
    "sale_statement": ["asset", "sale_date", "sale_price"],
    "grant_of_probate": ["executor_name", "date_granted"],
}
CONFIDENCE = ("low", "medium", "high")


def family_from_file_name(file_name, default):
    """Sample files are named like b_pension_statement.pdf. Otherwise use the family picked in the sidebar."""
    first = Path(file_name).name[:2].lower()
    if len(first) == 2 and first[1] == "_" and first[0] in FAMILIES:
        return first[0]
    return default


def validate(entry, doc_type):
    """Check a reading result has the right shape. Raises ValueError if it does not."""
    if not isinstance(entry, dict) or entry.get("document_type") != doc_type:
        raise ValueError("wrong document type")
    if entry.get("confidence") not in CONFIDENCE:
        raise ValueError("bad confidence")
    fields = entry.get("fields")
    if not isinstance(fields, dict):
        raise ValueError("fields missing")
    missing = [f for f in FIELDS[doc_type] if fields.get(f) in (None, "")]
    return {
        "document_type": doc_type,
        "fields": {f: fields.get(f) for f in FIELDS[doc_type]},
        "missing_fields": sorted(set(missing) | set(entry.get("missing_fields") or [])),
        "confidence": entry["confidence"],
        "read_ok": True,
    }


def could_not_read(doc_type):
    return {
        "document_type": doc_type,
        "fields": {},
        "missing_fields": list(FIELDS.get(doc_type, [])),
        "confidence": "low",
        "read_ok": False,
    }


def read_document(doc_type, file_name, default_family="b"):
    """Read one uploaded document. Returns the fields found, missing_fields and confidence."""
    time.sleep(READING_PAUSE_SECONDS)
    family = family_from_file_name(file_name, default_family)
    try:
        with open(FAMILIES_DIR / family / "expected.json", encoding="utf-8") as f:
            entry = json.load(f)["documents"][doc_type]
        return validate(entry, doc_type)
    except (OSError, KeyError, ValueError):
        return could_not_read(doc_type)


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
