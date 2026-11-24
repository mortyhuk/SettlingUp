"""Create the made-up sample documents (PDFs) and expected.json for families A, B and C.

Everything here is invented. Every page says "SAMPLE - NOT A REAL DOCUMENT".
The same data feeds the PDFs and expected.json, so the two always match.

Run from the project folder:  python scripts/make_documents.py
"""

import json
from pathlib import Path

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
FAMILIES_DIR = ROOT / "data" / "families"

# How each document type looks on paper: its title and the label printed next to each field.
LAYOUTS = {
    "death_certificate": {
        "title": "Death certificate",
        "labels": {"full_name": "Full name", "date_of_death": "Date of death"},
    },
    "pension_statement": {
        "title": "Annual pension statement",
        "labels": {"provider": "Pension provider", "annual_amount": "Pension paid in the year",
                   "tax_deducted": "Tax deducted"},
    },
    "interest_letter": {
        "title": "Statement of interest paid",
        "labels": {"bank": "Bank or building society", "interest_amount": "Interest paid",
                   "tax_year": "Tax year"},
    },
    "dividend_statement": {
        "title": "Dividend statement",
        "labels": {"company": "Company", "dividend_amount": "Dividend paid", "payment_date": "Payment date"},
    },
    "rental_summary": {
        "title": "Rental income and costs summary",
        "labels": {"rent_received": "Rent received", "expenses": "Costs paid", "period": "Period"},
    },
    "sale_statement": {
        "title": "Completion statement",
        "labels": {"asset": "Property or asset sold", "sale_date": "Completion date", "sale_price": "Sale price"},
    },
    "grant_of_probate": {
        "title": "Grant of probate",
        "labels": {"executor_name": "Executor", "date_granted": "Date granted"},
    },
    "self_employed_records": {
        "title": "Self-employed income and costs",
        "labels": {"business": "Business", "income": "Income", "costs": "Costs", "period": "Period"},
    },
}

MONEY_FIELDS = {"annual_amount", "tax_deducted", "interest_amount", "dividend_amount", "rent_received",
                "expenses", "sale_price", "pay_to_date", "tax_to_date", "income", "costs"}

# Documents that the app does not read (the accountant reads them). Not added to expected.json.
NOT_READ = {"self_employed_records"}

FAMILIES = {
    "a": {
        "person": "Joan Example",
        "story": "Simple: a pension only. No estate income, nothing sold, probate not needed.",
        "demo_answers": {
            "role": "I am the executor or administrator", "first_name": "Joan", "date_of_death": "2 April 2026",
            "lived_in_uk": "Yes", "income_types": ["A pension"], "usually_filed_sa": "No",
            "estate_income": "No income yet", "anything_sold": "No", "probate": "Not needed",
        },
        "documents": [
            ("death_certificate", "Sampletown Register Office (fictional)",
             {"full_name": "Joan Example", "date_of_death": "2 April 2026"}),
            ("pension_statement", "Example Pensions Ltd",
             {"provider": "Example Pensions Ltd", "annual_amount": 9000, "tax_deducted": 0}),
        ],
    },
    "b": {
        "person": "Peter Sample",
        "story": "Medium: pension, savings interest and shares. Some estate interest. Probate granted.",
        "demo_answers": {
            "role": "I am the executor or administrator", "first_name": "Peter", "date_of_death": "14 August 2026",
            "lived_in_uk": "Yes", "income_types": ["A pension", "Savings interest", "Shares or dividends"],
            "usually_filed_sa": "No", "estate_income": "Some, for example rent or interest",
            "anything_sold": "No", "probate": "Yes",
        },
        "documents": [
            ("death_certificate", "Sampletown Register Office (fictional)",
             {"full_name": "Peter Sample", "date_of_death": "14 August 2026"}),
            ("pension_statement", "Example Pensions Ltd",
             {"provider": "Example Pensions Ltd", "annual_amount": 18000, "tax_deducted": 1100}),
            ("interest_letter", "Sampletown Building Society",
             {"bank": "Sampletown Building Society", "interest_amount": 600, "tax_year": "2025 to 2026"}),
            ("dividend_statement", "Demo Holdings plc",
             {"company": "Demo Holdings plc", "dividend_amount": 400, "payment_date": "1 June 2026"}),
            ("grant_of_probate", "Sampletown Probate Registry (fictional)",
             {"executor_name": "Anna Sample", "date_granted": "20 October 2026"}),
        ],
    },
    "c": {
        "person": "Rita Demo",
        "story": "Complex: rental property and self-employed work. House sold after death. Probate granted.",
        "demo_answers": {
            "role": "I am helping the executor", "first_name": "Rita", "date_of_death": "10 June 2026",
            "lived_in_uk": "Yes", "income_types": ["Self-employed work", "Rental property"],
            "usually_filed_sa": "Yes", "estate_income": "Some, for example rent or interest",
            "anything_sold": "Yes", "probate": "Yes",
        },
        "documents": [
            ("death_certificate", "Sampletown Register Office (fictional)",
             {"full_name": "Rita Demo", "date_of_death": "10 June 2026"}),
            ("self_employed_records", "Rita Demo Garden Design (fictional)",
             {"business": "Rita Demo Garden Design", "income": 4000, "costs": 1000,
              "period": "6 April 2026 to 10 June 2026"}),
            ("rental_summary", "Example Lettings Ltd",
             {"rent_received": 2000, "expenses": 500, "period": "6 April 2026 to 10 June 2026"}),
            ("sale_statement", "Sample & Co Solicitors (fictional)",
             {"asset": "House at 1 Example Road, Sampletown", "sale_date": "30 October 2026",
              "sale_price": 250000}),
            ("grant_of_probate", "Sampletown Probate Registry (fictional)",
             {"executor_name": "Sam Demo", "date_granted": "1 September 2026"}),
        ],
    },
}


def show(field, value):
    if field in MONEY_FIELDS:
        return f"£{value:,.2f}"
    return str(value)


def watermark(c, width, height):
    c.saveState()
    c.setFillColor(Color(0.75, 0.1, 0.1, alpha=0.13))
    c.setFont("Helvetica-Bold", 38)
    c.translate(width / 2, height / 2)
    c.rotate(35)
    for offset in (-220, 0, 220):
        c.drawCentredString(0, offset, "SAMPLE - NOT A REAL DOCUMENT")
    c.restoreState()


def make_pdf(path, family, number, doc_type, issuer, fields):
    layout = LAYOUTS[doc_type]
    width, height = A4
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle(f"SAMPLE - {layout['title']}")

    # Red banner at the top
    c.setFillColor(HexColor("#B42318"))
    c.rect(0, height - 32, width, 32, stroke=0, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, height - 21, "SAMPLE - NOT A REAL DOCUMENT - MADE-UP DATA FOR A DEMO")

    # Issuer and title
    c.setFillColor(HexColor("#1D2939"))
    c.setFont("Helvetica-Bold", 15)
    c.drawString(60, height - 80, issuer)
    c.setFont("Helvetica", 10)
    c.drawString(60, height - 96, "1 Sample Street, Sampletown, SA1 0AA (fictional address)")
    c.setFont("Helvetica-Bold", 22)
    c.drawString(60, height - 150, layout["title"])
    c.setFont("Helvetica", 10)
    c.drawString(60, height - 168, f"Reference: SAMPLE-{family.upper()}-{number:03d}")

    # Field table
    y = height - 215
    c.setStrokeColor(HexColor("#D0D5DD"))
    for field, label in layout["labels"].items():
        c.setFont("Helvetica", 11)
        c.setFillColor(HexColor("#475467"))
        c.drawString(60, y, label)
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(HexColor("#1D2939"))
        c.drawString(250, y, show(field, fields[field]))
        c.line(60, y - 10, width - 60, y - 10)
        y -= 36

    # Footer
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(HexColor("#667085"))
    c.drawString(60, 50, "This is a made-up sample created for a hackathon demo. It is not a real document "
                         "and does not relate to a real person.")

    watermark(c, width, height)
    c.showPage()
    c.save()


def main():
    for family, info in FAMILIES.items():
        folder = FAMILIES_DIR / family
        folder.mkdir(parents=True, exist_ok=True)
        expected = {
            "family": family,
            "person": info["person"],
            "story": info["story"],
            "demo_answers": info["demo_answers"],
            "documents": {},
        }
        for number, (doc_type, issuer, fields) in enumerate(info["documents"], start=1):
            file_name = f"{family}_{doc_type}.pdf"
            make_pdf(folder / file_name, family, number, doc_type, issuer, fields)
            if doc_type not in NOT_READ:
                expected["documents"][doc_type] = {
                    "file": file_name,
                    "document_type": doc_type,
                    "fields": fields,
                    "missing_fields": [],
                    "confidence": "high",
                }
            print("made", folder / file_name)
        with open(folder / "expected.json", "w", encoding="utf-8") as f:
            json.dump(expected, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("made", folder / "expected.json")


if __name__ == "__main__":
    main()
