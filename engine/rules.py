"""Turns answers and read documents into results, using rules.yaml and prices.yaml.

Pure Python, no AI. These are DEMO RULES and must be checked by a UK accountant before real use.
Nothing here knows about one case type: the returns, dates, points and prices all come from the YAML.
"""

from datetime import date, timedelta

from engine.extract import show_value
from engine.flow import checklist, field_label, format_date, matches, parse_date


def possessive(answers):
    name = (answers.get("first_name") or "").strip()
    if not name:
        return "their"
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def tax_year_start(day, month, day_of_month):
    """The tax year starts on 6 April. A date before 6 April belongs to the previous tax year."""
    year = day.year if (day.month, day.day) >= (month, day_of_month) else day.year - 1
    return date(year, month, day_of_month)


def outcome_matches(outcome, answers):
    """when_any: any condition is true. when_all: every condition is true. Neither: always matches."""
    if "when_any" in outcome:
        return any(matches(c, answers) for c in outcome["when_any"])
    if "when_all" in outcome:
        return all(matches(c, answers) for c in outcome["when_all"])
    return True


def period(config, answers):
    """The part of a tax year a return covers: from the start of the tax year to a date the person gave."""
    end = answers.get(config["ends_on"])
    if not end:
        return None
    start = tax_year_start(end, config["tax_year_start"]["month"], config["tax_year_start"]["day"])
    tax_year = f"{start.year} to {start.year + 1}"
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "tax_year_end": (start.replace(year=start.year + 1) - timedelta(days=1)).isoformat(),
        "tax_year": tax_year,
        "text": config["text"].format(start=format_date(start), end=format_date(end), tax_year=tax_year),
    }


def evaluate_return(config, answers):
    """One card on the results screen. The first outcome that matches wins."""
    outcome = next(o for o in config["outcomes"] if outcome_matches(o, answers))
    return {
        "id": config["id"],
        "key": outcome["key"],
        "title": config["title"],
        "status": outcome["status"],
        "text": outcome["text"].replace("{person_possessive}", possessive(answers)),
        "period": period(config["period"], answers) if "period" in config else None,
    }


def key_dates(config, answers, returns, extracted):
    """Dates we already know, in date order. They come from an answer, a document we read, or the
    period of a return. They are facts from the case, not deadlines."""
    periods = {r["id"]: r["period"] or {} for r in returns}
    found = []
    for item in config.get("dates", []):
        if "question" in item:
            value = answers.get(item["question"])
        elif "document" in item:
            result = extracted.get(item["document"]) or {}
            value = result["fields"].get(item["field"]) if result.get("read_ok") else None
        else:
            value = periods.get(item["return"], {}).get(item["period"])
        day = parse_date(value) if value else None
        if day:
            found.append({"date": day.isoformat(), "text": format_date(day), "label": item["label"]})
    found.sort(key=lambda d: d["date"])
    return {"title": config["title"], "text": config["text"], "dates": found}


def money(pounds):
    """169 becomes '£169'. A line that costs nothing is shown as 'Included'."""
    return f"£{pounds:,}" if pounds else "Included"


def quote(prices, answers, returns):
    """The price lines that apply, and their total. Prices are whole pounds in prices.yaml."""
    lines = list(prices["always"])
    for r in returns:  # one line per return, if prices.yaml has one for that outcome
        line = prices["returns"].get(r["id"], {}).get(r["key"])
        if line:
            lines.append(line)
    lines += [e for e in prices["extras"] if matches(e["when"], answers)]
    total = sum(line["price"] for line in lines)
    return {"title": prices["title"], "total_label": prices["total_label"], "note": prices["note"],
            "lines": [{"label": line["label"], "price": money(line["price"])} for line in lines],
            "total": f"£{total:,}"}


def date_check(doc, result, answers):
    """Compare a date read from a document with a date the person gave, if documents.yaml asks for it.

    Returns None when there is nothing to compare. Otherwise {"same": True or False, "text": for the
    person, "point": for the accountant}.
    """
    check = doc.get("check_date")
    if not check or not result or not result.get("read_ok"):
        return None
    found = parse_date(result["fields"].get(check["field"]))
    given = answers.get(check["question"])
    if not found or not given:
        return None
    if found == given:
        return {"same": True, "text": check["same"], "point": ""}
    words = {"found": format_date(found), "given": format_date(given)}
    return {"same": False, "text": check["different"].format(**words), "point": check["point"].format(**words)}


def needs_confirming(result):
    """True if we read values from the document and the person has not yet said they are right."""
    return bool(result and result.get("read_ok") and not result.get("confirmed"))


def documents_status(case, answers, extracted):
    """Each checklist item with its status: added, missing, or added but needs a look."""
    rows = []
    for doc in checklist(case, answers):
        result = extracted.get(doc["id"])
        check = date_check(doc, result, answers)
        if not result:
            status = "missing"
        elif (result.get("read_ok") is False or result.get("missing_fields") or needs_confirming(result)
              or (check and not check["same"])):
            status = "check"
        else:
            status = "added"
        rows.append({"id": doc["id"], "label": doc["label"], "status": status, "result": result,
                     "check": check})
    return rows


def points_to_check(rules, answers, docs):
    """Short notes for the accountant: uncertain answers and documents that need a look. No tax rules here."""
    config = rules["accountant_points"]
    points = [p["text"] for p in config["by_answer"] if matches(p["when"], answers)]
    for doc in docs:
        result = doc["result"] or {}
        if doc["check"] and not doc["check"]["same"]:
            points.append(doc["check"]["point"])
        if result.get("read_ok") is False or result.get("missing_fields"):
            points.append(config["document_needs_look"].format(label=doc["label"]))
        elif needs_confirming(result):
            points.append(config["document_not_confirmed"].format(label=doc["label"]))
        for field, change in (result.get("corrections") or {}).items():
            points.append(config["document_corrected"].format(
                label=doc["label"], field=field_label(field).lower(),
                read=show_value(change["read"]), given=change["given"]))
    return points


def evaluate(case, answers, extracted):
    rules, prices = case["rules"], case["prices"]
    returns = [evaluate_return(config, answers) for config in rules["returns"]]
    docs = documents_status(case, answers, extracted)
    return {
        "rules_version": rules["version"],
        "rules_reviewed_by": rules.get("reviewed_by") or "",
        "returns": returns,
        "key_dates": key_dates(rules["key_dates"], answers, returns, extracted),
        "documents": docs,
        "missing_documents": [d["label"] for d in docs if d["status"] == "missing"],
        "points_to_check": points_to_check(rules, answers, docs),
        "quote": quote(prices, answers, returns),
    }
