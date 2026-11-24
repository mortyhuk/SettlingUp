"""Quick check before recording: runs Families A, B and C through the engine without the screens.

It fills in each family's demo answers, "uploads" its sample documents, works out the results and
builds the handover pack in memory. Nothing is saved. Made-up data only.

Run from the project folder:  python scripts/check_demo.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine import extract, flow, pack, rules  # noqa: E402

CASE_TYPE = "after_a_death"

# What each family should show on the results screen (from PLAN.md and the demo rules).
EXPECTED = {
    "a": ("We'll check", "Probably a simpler route"),
    "b": ("Likely needed", "May be needed"),
    "c": ("Likely needed", "May be needed"),
}


def answers_from_labels(case, demo_answers):
    """expected.json stores answers as the words on screen. Turn them back into stored values."""
    questions = {q["id"]: q for screen in flow.screens(case) for q in screen.get("questions", [])}
    answers = {}
    for qid, shown in demo_answers.items():
        question = questions[qid]
        values = {o["label"]: o["value"] for o in question.get("options", [])}
        if question["type"] == "checkboxes":
            answers[qid] = [values[label] for label in shown]
        elif question["type"] == "radio":
            answers[qid] = values[shown]
        elif question["type"] == "date":
            answers[qid] = flow.parse_date(shown)
        else:
            answers[qid] = shown
    return answers


def check_family(case, family):
    problems = []
    with open(ROOT / "data" / "families" / family / "expected.json", encoding="utf-8") as f:
        expected = json.load(f)
    answers = answers_from_labels(case, expected["demo_answers"])

    extracted = {}
    for doc in flow.checklist(case, answers):
        file_name = f"{family}_{doc['id']}.pdf"
        if not (ROOT / "data" / "families" / family / file_name).exists():
            problems.append(f"no sample file {file_name}")
            continue
        result = extract.read_document(doc["reads_as"], file_name, family) if doc.get("reads_as") else {"read_ok": None}
        result["file_name"] = file_name
        if result["read_ok"] is False:
            problems.append(f"{file_name} could not be read")
        extracted[doc["id"]] = result

    results = rules.evaluate(case, answers, extracted)
    shown = (results["final_return"]["status"], results["estate_return"]["status"])
    if shown != EXPECTED[family]:
        problems.append(f"results show {shown}, expected {EXPECTED[family]}")
    if results["missing_documents"]:
        problems.append(f"still to send: {results['missing_documents']}")
    if results["points_to_check"]:
        problems.append(f"unexpected points to check: {results['points_to_check']}")

    data = pack.build(case, answers, results)
    if not pack.to_json(data) or not pack.to_pdf(data).startswith(b"%PDF"):
        problems.append("the pack could not be built")
    return shown, len(extracted), problems


def main():
    extract.READING_PAUSE_SECONDS = 0  # no need to wait here
    case = flow.load_case_type(CASE_TYPE)
    all_ok = True
    for family in EXPECTED:
        shown, documents, problems = check_family(case, family)
        print(f"Family {family.upper()}: {'OK' if not problems else 'PROBLEM'}  "
              f"({documents} documents, final return: {shown[0]}, estate return: {shown[1]})")
        for problem in problems:
            print(f"  - {problem}")
        all_ok = all_ok and not problems
    print("All good. Ready to record." if all_ok else "Please fix the problems above before recording.")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
