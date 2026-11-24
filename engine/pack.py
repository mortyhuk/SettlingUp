"""Builds the handover pack for an accountant: a JSON file and a 1-2 page PDF, both marked Demo."""

import io
from xml.sax.saxutils import escape
import json
from datetime import date, datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from engine import extract, flow

OUT_DIR = Path(__file__).resolve().parent.parent / "out"
DEMO_NOTE = "DEMO ONLY. Made-up data. Demo rules, not real tax rules. An accountant must confirm everything."
STATUS_WORDS = {"added": "Added", "check": "Added, needs a look", "missing": "Still to send"}

GREEN = colors.HexColor("#134E4A")
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
            summary = extract.describe(doc["found"], result["fields"])
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
        })
    final = results["final_return"]
    return {
        "demo": DEMO_NOTE,
        "case_type": case["questions"]["name"],
        "created": (created or datetime.now()).isoformat(timespec="seconds"),
        "answers": {k: json_safe(v) for k, v in answers.items()},
        "answers_in_words": [{"question": q, "answer": a} for q, a in flow.answer_summary(case, answers)],
        "documents": documents,
        "missing_documents": results["missing_documents"],
        "points_to_check": results["points_to_check"],
        "results": {
            "label": results["label"],
            "final_return": {"status": final["status"], "text": final["text"], "period": final["period"]},
            "estate_return": {"status": results["estate_return"]["status"],
                              "text": results["estate_return"]["text"]},
            "key_dates": results["key_dates"]["text"],
        },
        "quote": results["quote"],
    }


def to_json(pack):
    return json.dumps(pack, indent=2, ensure_ascii=False).encode("utf-8")


def _demo_mark(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.Color(0.06, 0.46, 0.43, alpha=0.08))
    canvas.setFont("Helvetica-Bold", 90)
    canvas.translate(A4[0] / 2, A4[1] / 2)
    canvas.rotate(35)
    canvas.drawCentredString(0, 0, "DEMO")
    canvas.restoreState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.drawString(18 * mm, 10 * mm, DEMO_NOTE)
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
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF3EF")))
    table.setStyle(TableStyle(style))
    return table


def to_pdf(pack):
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9.5, leading=12.5)
    small = ParagraphStyle("small", parent=body, fontSize=8.5, textColor=colors.HexColor("#475467"))
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=GREEN, fontSize=18, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=GREEN, fontSize=12.5, spaceBefore=10,
                        spaceAfter=4)
    banner = ParagraphStyle("banner", parent=body, backColor=colors.HexColor("#FDF1D6"),
                            textColor=colors.HexColor("#7A4B00"), borderPadding=5, spaceAfter=8)

    def p(text, style=body, bold=False):
        text = escape(str(text))
        return Paragraph(f"<b>{text}</b>" if bold else text, style)

    width = A4[0] - 36 * mm
    story = [
        p("Handover pack for an accountant", h1),
        p(f"Case type: tax after a death. Created {pack['created'].replace('T', ' at ')}.", small),
        Spacer(1, 6),
        p(DEMO_NOTE, banner),
        p("About the case", h2),
        _table([[p(r["question"]), p(r['answer'], bold=True)] for r in pack["answers_in_words"]],
               [width * 0.55, width * 0.45], header=False),
        p("Documents", h2),
        _table([[p("Document", bold=True), p("Status", bold=True), p("What was found", bold=True)]] +
               [[p(d["label"]), p(STATUS_WORDS[d["status"]]), p(d["summary"] or "-")] for d in pack["documents"]],
               [width * 0.32, width * 0.2, width * 0.48]),
    ]

    r = pack["results"]
    final = r["final_return"]
    period = f" {final['period']['text']}" if final["period"] else ""
    story += [
        p("Results (demo rules)", h2),
        p(r["label"], small),
        Spacer(1, 3),
        _table([
            [p("Final personal tax return", bold=True), p(final['status'], bold=True), p(final["text"] + period)],
            [p("Estate tax return", bold=True), p(r['estate_return']['status'], bold=True),
             p(r["estate_return"]["text"])],
            [p("Key dates", bold=True), p("-"), p(r["key_dates"])],
        ], [width * 0.27, width * 0.2, width * 0.53], header=False),
    ]

    points = pack["points_to_check"] or ["No extra points were flagged from the answers or documents."]
    story += [p("Points to check", h2)] + [p(f"- {point}") for point in points]

    if pack["missing_documents"]:
        story += [p("Still to send", h2)] + [p(f"- {label}") for label in pack["missing_documents"]]

    q = pack["quote"]
    story += [
        p(q["title"], h2),
        _table([[p(line["label"]), p(line["price"])] for line in q["lines"]] +
               [[p(q['total_label'], bold=True), p(q['total'], bold=True)]],
               [width * 0.75, width * 0.25], header=False),
        p(q["note"], small),
    ]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm, title="Handover pack (demo)")
    doc.build(story, onFirstPage=_demo_mark, onLaterPages=_demo_mark)
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
