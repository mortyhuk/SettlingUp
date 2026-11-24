"""Turns answers and read documents into results, using rules.yaml and prices.yaml.

Pure Python, no AI. These are DEMO RULES and must be checked by a UK accountant before real use.
"""

from datetime import date

from engine.flow import checklist, format_date, matches


def possessive(answers):
    name = (answers.get("first_name") or "").strip()
    if not name:
        return "their"
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def tax_year_start(day_of_death, month, day):
    """The tax year starts on 6 April. A death before 6 April belongs to the previous tax year."""
    year = day_of_death.year if (day_of_death.month, day_of_death.day) >= (month, day) else day_of_death.year - 1
    return date(year, month, day)


def final_return(rules, answers):
    config = rules["final_return"]
    key = "likely" if any(matches(c, answers) for c in config["likely_if_any"]) else "check"
    outcome = config["outcomes"][key]
    result = {
        "key": key,
        "title": config["title"],
        "status": outcome["status"],
        "text": outcome["text"].replace("{person_possessive}", possessive(answers)),
        "period": None,
    }
    died = answers.get("date_of_death")
    if died:
        start = tax_year_start(died, **config["tax_year_start"])
        result["period"] = {
            "start": start.isoformat(),
            "end": died.isoformat(),
            "tax_year": f"{start.year} to {start.year + 1}",
            "text": config["period_text"].format(start=format_date(start), end=format_date(died),
                                                 tax_year=f"{start.year} to {start.year + 1}"),
        }
    return result


def estate_return(rules, answers):
    config = rules["estate_return"]
    if any(matches(c, answers) for c in config["may_be_needed_if_any"]):
        key = "may_be_needed"
    elif all(matches(c, answers) for c in config["simpler_if_all"]):
        key = "simpler"
    else:
        key = "not_sure"
    outcome = config["outcomes"][key]
    return {"key": key, "title": config["title"], "status": outcome["status"], "text": outcome["text"]}


def quote(prices, answers, final_key, estate_key):
    lines = list(prices["always"])
    lines.append(prices["final_return"][final_key])
    lines.append(prices["estate_return"][estate_key])
    lines += [{"label": e["label"], "price": e["price"]} for e in prices["extras"] if matches(e["when"], answers)]
    return {"title": prices["title"], "lines": lines, "total_label": prices["total_label"],
            "total": prices["total"], "note": prices["note"]}


def documents_status(case, answers, extracted):
    """Each checklist item with its status: added, missing, or added but needs a look."""
    rows = []
    for doc in checklist(case, answers):
        result = extracted.get(doc["id"])
        if not result:
            status = "missing"
        elif result.get("read_ok") is False or result.get("missing_fields"):
            status = "check"
        else:
            status = "added"
        rows.append({"id": doc["id"], "label": doc["label"], "status": status, "result": result})
    return rows


def evaluate(case, answers, extracted):
    rules, prices = case["rules"], case["prices"]
    final = final_return(rules, answers)
    estate = estate_return(rules, answers)
    docs = documents_status(case, answers, extracted)
    return {
        "label": rules["label"],
        "final_return": final,
        "estate_return": estate,
        "key_dates": rules["key_dates"],
        "documents": docs,
        "missing_documents": [d["label"] for d in docs if d["status"] == "missing"],
        "quote": quote(prices, answers, final["key"], estate["key"]),
    }
