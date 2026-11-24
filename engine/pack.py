"""Builds the handover pack for an accountant: a JSON file and a 1-2 page PDF."""

import io
from xml.sax.saxutils import escape
import json
from datetime import date, datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from engine import extract, flow

OUT_DIR = Path(__file__).resolve().parent.parent / "out"
STATUS_WORDS = {"added": "Added", "check": "Added, needs a look", "missing": "Still to send"}
# Whether the person has checked the values we read: "yes", "corrected" or not yet (None).
CONFIRMED_WORDS = {"yes": "Confirmed by the person.", "corrected": "Corrected by the person.",
                   None: "Not confirmed by the person yet."}

GREEN = colors.HexColor("#154618")
LINE = colors.HexColor("#D0D5DD")


def json_safe(value):
    if isinstance(value, date):
        return value.isoformat()
    return value


def build(case, answers, results, created=None):
    """Everything the accountant needs, as one dict."""
    found_templates = {d["id"]: d for d in flow.checklist(case, answers)}
    documents = []
    for row in results["documents"]:
        result = row["result"] or {}
        doc = found_templates[row["id"]]
        summary = ""
        if result.get("read_ok"):
            summary = extract.describe(doc["found"], result["fields"]) + ". " + CONFIRMED_WORDS[result.get("confirmed")]
        elif result.get("read_ok") is False:
            summary = "Could not be read automatically."
        elif result:
            summary = "Not read automatically. Please review."
        documents.append({
            "id": row["id"],
            "label": row["label"],
            "status": row["status"],
            "file_name": result.get("file_name"),
            "summary": summary,
            "fields": result.get("fields", {}),
            "missing_fields": result.get("missing_fields", []),
            "confidence": result.get("confidence"),
            "confirmed": result.get("confirmed"),
            "corrections": result.get("corrections", {}),
            "stored_file": result.get("stored_file"),
            "added": result.get("added", ""),
        })
    return {
        "case_type": case["questions"]["name"],
        "service": case["questions"]["service_name"],
        "created": (created or datetime.now()).isoformat(timespec="seconds"),
        "answers": {k: json_safe(v) for k, v in answers.items()},
        "answers_in_words": [{"question": q, "answer": a} for q, a in flow.answer_summary(case, answers)],
        "documents": documents,
        "missing_documents": results["missing_documents"],
        "points_to_check": results["points_to_check"],
        "results": {
            "rules_version": results["rules_version"],
            "rules_reviewed_by": results["rules_reviewed_by"],
            "returns": [{"id": r["id"], "title": r["title"], "status": r["status"], "text": r["text"],
                         "period": r["period"]} for r in results["returns"]],
            "key_dates": {"text": results["key_dates"]["text"], "dates": results["key_dates"]["dates"]},
        },
        "quote": results["quote"],
    }


def to_json(pack):
    return json.dumps(pack, indent=2, ensure_ascii=False).encode("utf-8")


def _footer(canvas, doc):
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.drawString(18 * mm, 10 * mm, "Handover pack. An accountant confirms everything in it.")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")


def _table(rows, widths, header=True):
    table = Table(rows, colWidths=widths)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF3EB")))
    table.setStyle(TableStyle(style))
    return table


def to_pdf(pack):
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9.5, leading=12.5)
    small = ParagraphStyle("small", parent=body, fontSize=8.5, textColor=colors.HexColor("#475467"))
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=GREEN, fontSize=18, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=GREEN, fontSize=12.5, spaceBefore=10,
                        spaceAfter=4)

    def p(text, style=body, bold=False):
        text = escape(str(text))
        return Paragraph(f"<b>{text}</b>" if bold else text, style)

    width = A4[0] - 36 * mm
    story = [
        p("Handover pack for an accountant", h1),
        p(f"Service: {pack['service']}. Created {pack['created'].replace('T', ' at ')}.", small),
        p("About the case", h2),
        _table([[p(r["question"]), p(r['answer'], bold=True)] for r in pack["answers_in_words"]],
               [width * 0.55, width * 0.45], header=False),
        p("Documents", h2),
        _table([[p("Document", bold=True), p("Status", bold=True), p("What was found", bold=True)]] +
               [[p(d["label"]), p(STATUS_WORDS[d["status"]]), p(d["summary"] or "-")] for d in pack["documents"]],
               [width * 0.32, width * 0.2, width * 0.48]),
    ]

    r = pack["results"]
    story += [
        p("Results", h2),
        p(f"Rules version {r['rules_version']}." + (f" Reviewed by {r['rules_reviewed_by']}."
          if r["rules_reviewed_by"] else ""), small),
        Spacer(1, 3),
        _table([[p(item["title"], bold=True), p(item["status"], bold=True),
                 p(item["text"] + (f" {item['period']['text']}" if item["period"] else ""))]
                for item in r["returns"]],
               [width * 0.27, width * 0.2, width * 0.53], header=False),
    ]
    dates = [p("Key dates", h2)]
    if r["key_dates"]["dates"]:
        dates.append(_table([[p(d["text"], bold=True), p(d["label"])] for d in r["key_dates"]["dates"]],
                            [width * 0.27, width * 0.73], header=False))
        dates.append(Spacer(1, 3))
    dates.append(p(r["key_dates"]["text"], small))
    story.append(KeepTogether(dates))  # do not split a short section across two pages

    points = pack["points_to_check"] or ["No extra points were flagged from the answers or documents."]
    story += [p("Points to check", h2)] + [p(f"- {point}") for point in points]

    if pack["missing_documents"]:
        story += [p("Still to send", h2)] + [p(f"- {label}") for label in pack["missing_documents"]]

    q = pack["quote"]
    story.append(KeepTogether([
        p(q["title"], h2),
        _table([[p(line["label"]), p(line["price"])] for line in q["lines"]] +
               [[p(q['total_label'], bold=True), p(q['total'], bold=True)]],
               [width * 0.75, width * 0.25], header=False),
        p(q["note"], small),
    ]))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm, title="Handover pack")
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def save(pack, json_bytes, pdf_bytes):
    """Write both files to out/ and return their paths."""
    OUT_DIR.mkdir(exist_ok=True)
    stamp = pack["created"].replace(":", "").replace("-", "")
    json_path = OUT_DIR / f"handover_{stamp}.json"
    pdf_path = OUT_DIR / f"handover_{stamp}.pdf"
    json_path.write_bytes(json_bytes)
    pdf_path.write_bytes(pdf_bytes)
    return json_path, pdf_path
