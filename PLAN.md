# Build plan with Claude Code

Total time: about 7 to 10 hours (4 to 6 if you stay in mock mode).
Work one phase at a time. After each phase: click through the app, then save a checkpoint
(`git add -A && git commit -m "phase N"`). Git works locally, so you don't need GitHub for this.

If a phase takes more than 30 minutes longer than planned, cut scope or use mock mode and move on.
The video matters more than perfect code.

---

## Phase 0: Set up (20-30 min)
1. Install Claude Code. Follow the official guide: https://docs.claude.com/en/docs/claude-code/overview
2. Make a folder, e.g. `one-step-demo`, and put CLAUDE.md and PLAN.md in it.
3. Open Claude Code in that folder and paste:

> Read CLAUDE.md and PLAN.md. Don't write code yet. Tell me in 5 bullet points what you'll build,
> list anything unclear, then set up the project: requirements.txt (streamlit, pyyaml, anthropic,
> reportlab), the folder layout from CLAUDE.md, a .gitignore (ignore .venv and out/) and git init.

**Check:** the folders exist and `pip install -r requirements.txt` works.

---

## Phase 1: Question flow (1-1.5 h)
> Build the question flow for the after_a_death case type. Put every screen and question in
> engine/case_types/after_a_death/questions.yaml, exactly as described in CLAUDE.md. Write
> engine/flow.py to load it and work out next and back. In app.py, show one screen at a time with a
> progress bar ("Step X of 7"), Back and Continue buttons, and Continue disabled until the required
> answers are given. Keep answers in st.session_state. Use the calm green look from CLAUDE.md with
> a small block of custom CSS. Skip documents, results and pack for now: show placeholders.

**Check:** you can click from Welcome to the placeholders and back without errors.

---

## Phase 2: Made-up families and documents (1 h)
> Write scripts/make_documents.py to create sample PDFs with reportlab for three made-up families.
> Every page must show "SAMPLE - NOT A REAL DOCUMENT" across it. Use plain layouts, no official
> designs or crests. Also write data/families/<x>/expected.json with the fields CLAUDE.md lists for
> each document, matching what's printed on the PDFs.
> Family A (simple): pension only, no estate income, nothing sold, probate not needed.
> Family B (medium): pension, savings interest and shares; some estate interest; probate granted.
> Family C (complex): rental property and self-employed work; house sold after death; probate granted.
> Use clearly fictional names and round, made-up amounts.

**Check:** open a few PDFs. They should look believable and clearly say SAMPLE.

---

## Phase 3: AI reading (1.5-2.5 h, or 30 min in mock mode)
First ask Sian or the organisers whether there's an Anthropic API key for the hackathon.
No key? Build mock mode only and move on.

> Build engine/extract.py. For each uploaded document, call the Anthropic API (model
> claude-sonnet-5-5, key from ANTHROPIC_API_KEY) with the PDF and ask for JSON only, using the
> fields in CLAUDE.md for that document type, plus document_type, missing_fields and confidence.
> Validate the JSON. With MOCK_AI=1, or if the call fails, return the matching entry from
> data/families/<x>/expected.json instead. Then add the documents screen in app.py: the checklist
> comes from documents.yaml based on the answers, each item has an upload button, and after upload
> show what was found in plain words, e.g. "Pension statement: £[amount] a year from [provider]".

**Check:** run Family B in mock mode, then once with the API. The fields should match expected.json.

---

## Phase 4: Results and quote (1 h)
> Write engine/rules.py using rules.yaml and prices.yaml. It takes the answers and the extracted
> documents and returns: final return status and period, estate return status, key dates text,
> missing documents and the quote lines. Pure Python, no AI. Then build the results screen with a
> "Demo rules only" label at the top. Keep prices as [PRICE] placeholders from prices.yaml.

**Check:** Family A shows "We'll check" and "Probably a simpler route". Family C shows "Likely
needed" and "May be needed".

---

## Phase 5: Handover pack (1 h)
> Write engine/pack.py. Build a JSON file with the answers, extracted fields, checklist status,
> missing documents and results. Also build a 1-2 page PDF summary for the accountant with
> reportlab, marked "Demo". Add the pack screen: a short summary, two download buttons (JSON, PDF)
> and a "Send to an accountant (demo)" button that goes to the thank-you screen. Save files in out/.

**Check:** both downloads open and the numbers match the documents.

---

## Phase 6: Polish and rehearsal (1 h)
> Read every screen's text and make it gentle, short, plain UK English. Make buttons large and
> spacing generous. Add a "Start again" button on the thank-you screen. Then walk through Families
> A, B and C in mock mode and fix anything that breaks or looks odd.

**Check:** Family B runs in under 90 seconds without errors.

---

## Phase 7: Video (1-1.5 h)
Record a screen video of Family B, in mock mode so nothing can fail live.
- 0:00-0:20 The problem: after a death, families don't know what tax returns are needed, and
  probate firms stop at inheritance tax.
- 0:20-1:40 The demo: questions, upload, AI reading, checklist, results, pack.
- 1:40-2:00 Why Taxfix: we already have the accountants. One engine, more niche services next
  (for example doctors' returns). Add a real number from Snowflake if Sian finds one.

---

## Stretch: second case type, doctors' returns (1-2 h, only if time)
> Add a second case type, doctors, under engine/case_types/doctors with its own questions.yaml,
> documents.yaml, rules.yaml and prices.yaml: NHS payslips and P60, locum invoices, pension savings
> statement, GMC, indemnity and BMA fees. Add a case-type choice on the welcome screen. Don't change
> how the engine works. Make one made-up doctor in data/families/d.

---

## Tips for working with Claude Code
- Ask it to plan first ("tell me your plan before coding"), then say go.
- One phase per conversation keeps it focused. Start each one with "Read CLAUDE.md first".
- If it goes off track, say exactly what's wrong, or go back to your last git commit.
- Keep CLAUDE.md up to date when you decide something new, like the final project name.
- Never paste real customer data, even "just to test".
