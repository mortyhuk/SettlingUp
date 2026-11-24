# SettlingUp: One step at a time

Gentle tax help for families and executors after someone dies.

When someone dies, the person sorting out their affairs often has to deal with tax as well: a final
tax return for the person who died, and sometimes a tax return for the estate. Most people have never
done this before, and they are doing it while grieving.

**One step at a time** asks a few kind, plain questions, reads the documents the family already has,
and shows what is likely to be needed and what it will cost. Then it hands everything to an accountant
in one tidy pack.

> **Hackathon demo, 24 to 25 November 2026.** Everything in this repository is made up: the people,
> the documents and the results. The tax rules are demo rules that a UK accountant has not checked yet.
> Nothing is filed with HMRC. Please do not put real documents or personal details into it.

## What it does

1. **Asks a few gentle questions.** Who you are, about the person who died, their income, and what
   has happened since. One small group of questions per screen.
2. **Builds a document checklist** from the answers. For example, a pension means pension statements,
   and a house sale means the completion statement.
3. **Reads each document** and shows what it found in plain words. The person confirms it or corrects
   it. For the demo, reading uses prepared results instead of a live AI service.
4. **Shows what is likely to be needed:** the final tax return and its period, whether the estate may
   need its own return, the key dates we already know, and a fixed-fee quote.
5. **Makes a handover pack** (PDF) and sends it to the accountant inbox.

The accountant inbox shows the packs that have been sent, with a status for each. The accountant can
open the original documents and ask the person for anything that is missing.

People can stop and come back later with a return code (like `KTRM-4729`). They can also delete their
case and documents at any time.

## Two services, one engine

The app is built around **case types**. A case type is just a folder of four YAML files. Python code
never names a case type, a return or a document.

| Case type | Folder | Sample people |
|---|---|---|
| Tax after a death | `engine/case_types/after_a_death/` | Families A, B and C |
| Tax returns for doctors | `engine/case_types/doctors/` | Family D (Dr Alex Sample) |

To add a new service, add a new folder with these four files:

- `questions.yaml`: the screens and questions
- `documents.yaml`: which documents to ask for, based on the answers, and what to read from them
- `rules.yaml`: the rules for the results screen
- `prices.yaml`: the quote

## Run it

You need Python 3.11 or newer. The commands below use [uv](https://docs.astral.sh/uv/) to make the
Python environment. A normal `python -m venv .venv` works too.

```bash
uv venv --python 3.12 --seed .venv
```
```bash
source .venv/bin/activate
```
```bash
pip install -r requirements.txt
```
```bash
streamlit run app.py
```

The app opens at http://localhost:8501. The accountant inbox is at
http://localhost:8501/?view=accountant, or you can open it from the welcome screen.

### Try a sample family

On the documents screen, upload the matching sample PDFs from `data/families/`. The app uses the
letter at the start of the file name (`a_`, `b_`, `c_` or `d_`) to know which family it is.

| Family | Person | What makes it interesting |
|---|---|---|
| A | Joan Example, died 2 April 2026 | Pension only. Died before 6 April, so the final return covers the previous tax year. |
| B | Peter Sample, died 14 August 2026 | Pension, savings interest and dividends. Probate granted. **Use this one for the demo video.** |
| C | Rita Demo, died 10 June 2026 | Self-employed, rental income, and a house sold after death. |
| D | Dr Alex Sample | Doctors service. Employed NHS work and some locum work, a pension savings statement, and professional fees. |

## Check before a demo

```bash
python -m unittest discover tests
```
```bash
python scripts/check_demo.py
```

The second command runs Families A to D through the engine without the screens. It should end with
"All good. Ready to record."

To make the sample PDFs again:

```bash
python scripts/make_documents.py
```

To empty the inbox and all saved cases, delete the `out/` folder.

## How it is put together

```
app.py                     the person's screens and navigation
inbox.py                   the accountant inbox
engine/
  case_types/              one folder of YAML files per service
  flow.py                  loads a case type and works out the next screen
  rules.py                 turns answers into results (plain Python, no AI)
  extract.py               document reading (prepared results for the demo)
  pack.py                  builds the handover pack PDF
  store.py                 saves cases and uploaded files (SQLite in out/)
data/families/a|b|c|d/     made-up sample documents and their prepared results
scripts/                   make the sample PDFs and check the demo
tests/                     automatic tests
out/                       saved cases, uploads and packs (not in git)
```

Built with Python, Streamlit, PyYAML and reportlab.

## Principles

- **Made-up data only.** Every sample document is clearly fictional.
- **AI reads; it does not decide.** Tax rules live in `rules.yaml` and plain Python. AI only reads
  documents and writes friendly text.
- **Gentle, plain UK English** on every screen.
- **An accountant always confirms.** The app never says it files a return.

## Not real yet

- Document reading uses prepared results, not a live AI service.
- The rules have not been reviewed by a UK accountant.
- Prices are examples. Nobody has agreed prices for these services.
- No sign-in, no real email, and no security or data protection review.

## Team

Morty and Sian.
