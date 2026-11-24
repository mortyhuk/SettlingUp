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
- Real tax rules. The rules here are demo rules. No accountant has reviewed them yet
  (rules.yaml has a version and a reviewed_by line for when one has).

## Hard rules
- MADE-UP DATA ONLY. Never use, paste or upload real customer data, names or documents.
- Every sample document must be clearly made up: a "(fictional)" issuer line, a SAMPLE- reference
  and names like Sample, Example and Demo. Do not copy official designs or crests.
- Gentle, plain UK English on every screen. No jokes, no emojis.
- Never claim we file the estate return (SA900). Say "an accountant will confirm".
- Keep it simple. Prefer fewer files and plain code over clever code.
- Do not let the AI decide tax rules. AI only reads documents and writes friendly text.
- Ask before adding a new library or changing the folder layout.

## Tech stack
- Python 3.11+, Streamlit for the UI.
- PyYAML for config, reportlab for PDFs. Versions are pinned in requirements.txt.
- sqlite3 (comes with Python) for saved cases. unittest (comes with Python) for tests.
- Anthropic Python SDK for document reading. Model: claude-sonnet-5-5.
  The key comes from the ANTHROPIC_API_KEY environment variable. Never hard-code it.
- MOCK_AI=1 switches to mock mode: the app reads prepared JSON from data/families/*/expected.json
  instead of calling the API. Mock mode must always work, even with no key and no internet.

## Folder layout
```
app.py                          Streamlit app (the person's screens and navigation only)
inbox.py                        the accountant's inbox screens
engine/
  case_types/after_a_death/
    questions.yaml              screens and questions
    documents.yaml              which documents to ask for, based on answers
    rules.yaml                  demo rules for the results screen
    prices.yaml                 quote prices in pounds (example fees for the demo)
  case_types/doctors/           second case type: the same four files, for doctors' returns
  flow.py                       loads a case type and works out the next screen
  rules.py                      turns answers into results (pure Python, no AI)
  extract.py                    AI document reading + mock mode
  pack.py                       builds the handover pack (JSON + PDF)
  store.py                      saves cases and uploaded files (SQLite), return codes, the inbox
data/families/a|b|c/            made-up documents + expected.json per family (after a death)
data/families/d/                one made-up doctor (doctors)
scripts/make_documents.py       creates the sample PDFs
scripts/check_demo.py           quick check of Families A, B and C before recording
tests/test_engine.py            automatic tests for rules, document checks, the pack and saving
out/                            generated packs, cases.db and uploads/ (git-ignored, safe to delete)
```
The engine is built around "case types". A case type is only a folder of four YAML files under
engine/case_types/. Nothing in app.py or engine/*.py names a case type, a return or a document.
The second case type (doctors' returns) was added this way.

## Question flow (case type: after_a_death)
1. Welcome: "One step at a time". Short, kind intro. Button: Start.
2. Who are you? Executor or administrator / Helping the executor / Not sure yet.
3. About the person: first name (optional), date of death, lived in the UK? (Yes/No; if No, show a kind note that a specialist will check).
4. Income before they died (multi-select): pay from a job, a pension, self-employed work, rental property, savings interest, shares or dividends, not sure.
   Did they usually send a Self Assessment return? Yes / No / Not sure.
5. Since they died: estate income yet? (No income yet / Some, e.g. rent or interest / Not sure).
   Anything sold, like a house or shares? (Yes / No / Not sure). Probate granted? (Yes / Not yet / Not needed / Not sure).
6. Your documents: checklist built from the answers, with upload per document.
7. Results: final return, estate return, key dates, fixed-fee quote.
8. Accountant pack: summary + download (JSON and PDF) + "Send to an accountant" (goes to the inbox).
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
Calm green: background #EAF3EB, cards #FFFFFF, text #1D2939, headings #154618, accent #154618.
Large text (17-18px body), big buttons, one question group per screen, progress bar "Step X of 7".

## How to run
The Mac's own Python is 3.9, so the venv is made with uv (installed in ~/.local/bin).
```
uv venv --python 3.12 --seed .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/make_documents.py        # (re)creates the sample PDFs and expected.json
python -m unittest discover tests       # automatic tests
python scripts/check_demo.py            # quick check of Families A to D before recording
streamlit run app.py
```
To empty the inbox and all saved cases, delete the out/ folder.

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
- The date read from the death certificate is compared with the date the person gave (check_date in
  documents.yaml). If they differ, the screen shows a kind note and the document is marked "needs a look".
- The pack has a "Points to check" section for the accountant: "not sure" answers, lived outside the UK,
  probate not granted yet, and documents that need a look. The wording is in rules.yaml
  (accountant_points). These only repeat answers and document facts. They are not tax rules.
- The first name is escaped before it is shown inside HTML labels.
- Family B's interest letter is for tax year 2026 to 2027, to match the final return period.
- `python scripts/check_demo.py` runs Families A, B, C and D through the engine without the screens.
  Run it before recording. It should end with "All good. Ready to record."
- Key dates: the results screen and the pack now list dates we already know, in date order (for
  example the date of death, the tax year of the final return, the date probate was granted). They
  come from answers and documents and are set up in rules.yaml (key_dates.dates). They are facts
  from the case, NOT deadlines. The line "Your accountant will confirm the deadline" stays.
- rules.yaml now has a "returns" list. Each return is one card on the results screen, with outcomes
  tried in order (when_any / when_all, first match wins). prices.yaml has one line per outcome.
  The demo rules for "after a death" are the same as before, only written in this shape.
- The fields to read from each document are in documents.yaml (fields), not in extract.py.
- questions.yaml names the service (service_name) and its sample families (sample_families,
  default_family).
- Second case type: doctors (engine/case_types/doctors). Questions: kind of work, usual Self
  Assessment, pension savings statement, fees paid. Results: "Self Assessment tax return" and "Tax
  relief on professional fees". DEMO RULES, to be checked by a UK accountant like the others.
  Made-up Family D is Dr Alex Sample (5 documents).
- The welcome screen has a small "Other services in this demo" link to switch case type. The first
  service shown is still "Tax after a death", so the Family B run is unchanged.
- Handover pack JSON: results.returns is now a list, and results.key_dates has text and dates.

## Decisions (24 Nov 2026, later the same day)
- "Demo" labels are removed from the screens, the PDF pack and the pack JSON. The sample documents no
  longer have the red banner, the diagonal watermark or the footer line. Everyone at the showcase is
  told the data is made up. MADE-UP DATA ONLY still applies, and the sample documents stay clearly
  fictional (see Hard rules).
- Save and come back: every case gets a return code (like KTRM-4729) when the person starts. It is in
  the page address (?case=CODE), so a refresh loses nothing. The welcome screen has "Already started?".
  Each step has "Come back later" with the code, a link by email and "Delete my case and documents".
  No email is really sent: the screen shows the link. A code is not real sign-in. Real use needs
  sign-in by email link.
- Confirm what was read: after each document is read the person presses "Yes, that is right" or
  "Change something". A changed value keeps both what the document said and what the person typed.
  Documents that are not confirmed, and every correction, go into "Points to check".
- Accountant inbox (inbox.py, open it from the sidebar or with ?view=accountant): sent packs, a status,
  the original documents, and "Ask for a document". The person sees the request when they come back
  and the request closes when they add that document and send again. There is no sign-in on the
  inbox yet.
- Statuses: New, In review, Waiting for documents, New documents received, Done (store.STATUSES).
- "Start a new case" only clears the browser. The saved case stays until it is deleted.
- Expanders are not used for sections with inputs, because they close each time the person types.
- Prices: the quote uses the public Taxfix UK prices (checked on taxfix.com/en-uk, 24 Nov 2026) and
  adds up the total. One fixed fee per tax return: £169, the full price of the "Prepared & Filed
  Accurately" plan (£99 for new customers). The tax advice call is £139. There are no extras by
  income type, because Taxfix charges one price per return. Taxfix has no public price for an estate
  return, so it is priced as one more tax return. Nobody has agreed prices for these new services.
- Still not real: AI reading (prepared results), accountant review of the rules, agreed prices,
  email, sign-in, and any security or data protection review. Do not put real documents in.

## Definition of done
Family B can be run start to finish in under 90 seconds: answers, uploads, AI reading (or mock),
results, and a downloaded handover pack. No real data anywhere.
