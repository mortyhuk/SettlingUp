# Project: "One step at a time" (hackathon demo)

Gentle tax help for families and executors after someone dies.
Hackathon working name: "Tax after a death" (a softer name is being chosen).
Team: Morty (lead) and Sian. Hackathon: Tue 24 to Wed 25 Nov 2026.

## Goal for the hackathon (level 3: working demo)
A small web app that:
1. asks a few gentle questions,
2. reads made-up documents with AI,
3. shows a document checklist, which returns are likely needed and a fixed-fee quote,
4. produces a handover pack for an accountant (JSON and PDF).

It must look real in a 2-minute video. It does NOT need to be production-ready.

## Out of scope (fake it or leave it out)
- Sign-in, payments, filing to HMRC, the real accountant workflow.
- Real tax rules. All rules here are DEMO RULES and must say so on screen.

## Hard rules
- MADE-UP DATA ONLY. Never use, paste or upload real customer data, names or documents.
- Every sample document shows "SAMPLE - NOT A REAL DOCUMENT". Do not copy official designs or crests.
- Gentle, plain UK English on every screen. No jokes, no emojis.
- Never claim we file the estate return (SA900). Say "an accountant will confirm".
- Keep it simple. Prefer fewer files and plain code over clever code.
- Do not let the AI decide tax rules. AI only reads documents and writes friendly text.
- Ask before adding a new library or changing the folder layout.

## Tech stack
- Python 3.11+, Streamlit for the UI.
- PyYAML for config, reportlab for PDFs.
- Anthropic Python SDK for document reading. Model: claude-sonnet-5-5.
  The key comes from the ANTHROPIC_API_KEY environment variable. Never hard-code it.
- MOCK_AI=1 switches to mock mode: the app reads prepared JSON from data/families/*/expected.json
  instead of calling the API. Mock mode must always work, even with no key and no internet.

## Folder layout
```
app.py                          Streamlit app (screens and navigation only)
engine/
  case_types/after_a_death/
    questions.yaml              screens and questions
    documents.yaml              which documents to ask for, based on answers
    rules.yaml                  demo rules for the results screen
    prices.yaml                 quote prices (placeholders: [PRICE])
  flow.py                       loads a case type and works out the next screen
  rules.py                      turns answers into results (pure Python, no AI)
  extract.py                    AI document reading + mock mode
  pack.py                       builds the handover pack (JSON + PDF)
data/families/a|b|c/            made-up documents + expected.json per family
scripts/make_documents.py       creates the sample PDFs
out/                            generated handover packs (git-ignored)
```
The engine is built around "case types" so a second case type (doctors' returns) can be added later
by adding a new folder under engine/case_types/, without changing app.py.

## Question flow (case type: after_a_death)
1. Welcome: "One step at a time". Short, kind intro. Button: Start.
2. Who are you? Executor or administrator / Helping the executor / Not sure yet.
3. About the person: first name (optional), date of death, lived in the UK? (Yes/No; if No, show a kind note that a specialist will check).
4. Income before they died (multi-select): pay from a job, a pension, self-employed work, rental property, savings interest, shares or dividends, not sure.
   Did they usually send a Self Assessment return? Yes / No / Not sure.
5. Since they died: estate income yet? (No income yet / Some, e.g. rent or interest / Not sure).
   Anything sold, like a house or shares? (Yes / No / Not sure). Probate granted? (Yes / Not yet / Not needed / Not sure).
6. Your documents: checklist built from the answers, with upload per document.
7. Results: final return, estate return, key dates, fixed-fee quote. Label "Demo rules only".
8. Accountant pack: summary + download (JSON and PDF) + "Send to an accountant (demo)".
9. Thank you: what happens next (3 short steps).

## Demo rules (rules.yaml) - must be checked by a UK accountant before real use
- Final personal return: "Likely needed" if they usually filed Self Assessment, or had self-employed,
  rental or share income. Otherwise "We'll check".
- Final return period: 6 April of the tax year of death to the date of death
  (tax year starts 6 April; a death before 6 April belongs to the previous tax year).
- Estate return: "May be needed" if anything was sold or the estate has some income.
  "Probably a simpler route" if no estate income and nothing sold. Otherwise "Not sure yet".
- Key dates: "Your accountant will confirm the deadline for each return."

## Documents (documents.yaml)
Always: death certificate. Then by answer: job -> last payslip and P45 or P60; pension -> pension
statements; self-employed -> income and costs records; rental -> rental income and costs;
savings -> interest letters; shares -> share statements and dividend vouchers; sold = yes ->
sale or completion statement; probate = yes -> grant of probate or letters of administration.

## AI reading (extract.py)
- One call per document. Ask for JSON only, with these fields per type:
  death_certificate: full_name, date_of_death
  p45_p60 / payslip: employer, pay_to_date, tax_to_date, tax_year
  pension_statement: provider, annual_amount, tax_deducted
  interest_letter: bank, interest_amount, tax_year
  dividend_statement: company, dividend_amount, payment_date
  rental_summary: rent_received, expenses, period
  sale_statement: asset, sale_date, sale_price
  grant_of_probate: executor_name, date_granted
- Also return: document_type, missing_fields (list), confidence (low/medium/high).
- Validate the JSON. If the call fails, fall back to mock mode for that document and show a calm message.

## Look and feel
Calm green: background #EAF3EF, cards #FFFFFF, text #1D2939, headings #134E4A, accent #0F766E.
Large text (17-18px body), big buttons, one question group per screen, progress bar "Step X of 7".

## How to run
The Mac's own Python is 3.9, so the venv is made with uv (installed in ~/.local/bin).
```
uv venv --python 3.12 --seed .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/make_documents.py        # (re)creates the sample PDFs and expected.json
streamlit run app.py
```

## Decisions (24 Nov 2026)
- No API key for the hackathon. Document reading is MOCK ONLY: extract.py always returns the prepared
  result from data/families/<x>/expected.json, after a short "reading" pause. The documents screen says
  so ("Demo: prepared sample results"). The anthropic package stays in requirements.txt but is unused.
- Mock mode picks the family from the uploaded file name (a_..., b_..., c_...). If the name does not
  start with a family letter, it uses the "Demo family" picker in the sidebar (default: B).
- "Step X of 7" counts screens 2 to 8. Welcome and Thank you have no step number.
- Lived in the UK = No shows a kind note and the flow carries on.
- Self-employed income and costs records are uploaded but not read; the accountant reads them.
- A death on 1 to 5 April belongs to the previous tax year (final return period starts 6 April of the year before).

## Definition of done
Family B can be run start to finish in under 90 seconds: answers, uploads, AI reading (or mock),
results, and a downloaded handover pack. All screens say "demo" where needed. No real data anywhere.
