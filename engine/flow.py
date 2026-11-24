"""Loads a case type and works out screens, next/back, completeness and the document checklist."""

from datetime import date, datetime
from pathlib import Path

import yaml

CASE_TYPES_DIR = Path(__file__).parent / "case_types"


def load_case_type(name):
    """Read every YAML file in engine/case_types/<name>/ into one dict, keyed by file name."""
    folder = CASE_TYPES_DIR / name
    case = {}
    for path in sorted(folder.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            case[path.stem] = yaml.safe_load(f)
    return case


def case_type_names():
    """Every case type we have: each folder in engine/case_types/ with a questions.yaml."""
    return sorted(p.name for p in CASE_TYPES_DIR.iterdir() if (p / "questions.yaml").exists())


def service_name(name):
    """The name of a case type in plain words, e.g. 'Tax after a death'."""
    with open(CASE_TYPES_DIR / name / "questions.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["service_name"]


def screens(case):
    return case["questions"]["screens"]


def kind_index(case, kind):
    """The first screen of a kind, e.g. the documents screen."""
    return next(i for i, screen in enumerate(screens(case)) if screen["kind"] == kind)


def screen_index(case, screen_id):
    for i, screen in enumerate(screens(case)):
        if screen["id"] == screen_id:
            return i
    raise KeyError(screen_id)


def next_index(case, index):
    return min(index + 1, len(screens(case)) - 1)


def back_index(index):
    return max(index - 1, 0)


def is_answered(question, answers):
    value = answers.get(question["id"])
    if question["type"] == "checkboxes":
        return bool(value)
    if question["type"] == "text":
        return bool(value and str(value).strip())
    return value is not None


def is_complete(screen, answers):
    """True when every required question on the screen has an answer."""
    for question in screen.get("questions", []):
        if question.get("required") and not is_answered(question, answers):
            return False
    return True


def matches(condition, answers):
    """A condition is {question: id, equals: value} or {question: id, includes: value}."""
    value = answers.get(condition["question"])
    if "equals" in condition:
        return value == condition["equals"]
    if "includes" in condition:
        return condition["includes"] in (value or [])
    raise ValueError(f"Unknown condition: {condition}")


def checklist(case, answers):
    """The documents to ask for, in order, based on the answers."""
    docs_config = case["documents"]
    items = list(docs_config["always"])
    for rule in docs_config["by_answer"]:
        if matches(rule["when"], answers):
            items.extend(rule["documents"])
    return items


def person(answers):
    name = (answers.get("first_name") or "").strip()
    return name if name else "they"


def personalise(text, answers):
    return text.replace("{person}", person(answers))


def answer_summary(case, answers):
    """A list of (question label, answer in words) for every answered question."""
    rows = []
    for screen in screens(case):
        for question in screen.get("questions", []):
            if not is_answered(question, answers):
                continue
            value = answers[question["id"]]
            labels = {o["value"]: o["label"] for o in question.get("options", [])}
            if question["type"] == "checkboxes":
                text = ", ".join(labels.get(v, v) for v in value)
            elif question["type"] == "date":
                text = format_date(value)
            else:
                text = labels.get(value, str(value))
            rows.append((personalise(question["label"], answers), text))
    return rows


def format_date(d):
    return f"{d.day} {d:%B %Y}"


def field_label(field):
    """'annual_amount' becomes 'Annual amount'."""
    return field.replace("_", " ").capitalize()


def restore_answers(case, saved):
    """Answers loaded from the database have dates as text. Turn those back into dates."""
    answers = dict(saved)
    for screen in screens(case):
        for question in screen.get("questions", []):
            if question["type"] == "date" and answers.get(question["id"]):
                answers[question["id"]] = parse_date(answers[question["id"]])
    return answers


def parse_date(value):
    """Turn '14 August 2026', '2026-08-14' or '14/08/2026' into a date. None if it is not a date we know."""
    if isinstance(value, date):
        return value
    for pattern in ("%d %B %Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(value).strip(), pattern).date()
        except ValueError:
            pass
    return None
