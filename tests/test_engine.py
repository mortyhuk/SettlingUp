"""Automatic tests for the engine: rules, document checks, the pack and saving cases.

Made-up data only. Run from the project folder:  python -m unittest discover tests
"""

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import check_demo  # noqa: E402
from engine import extract, flow, pack, rules, store  # noqa: E402

extract.READING_PAUSE_SECONDS = 0  # no need to wait in tests


def statuses(results):
    return {r["id"]: r["status"] for r in results["returns"]}


class CaseTypes(unittest.TestCase):
    """Every case type folder must load and have what the screens need."""

    def test_every_case_type_loads(self):
        names = flow.case_type_names()
        self.assertIn("after_a_death", names)
        self.assertIn("doctors", names)
        for name in names:
            case = flow.load_case_type(name)
            self.assertEqual(set(case), {"questions", "documents", "rules", "prices"}, name)
            kinds = [screen["kind"] for screen in flow.screens(case)]
            self.assertEqual(kinds[0], "welcome", name)
            self.assertEqual(kinds[-3:], ["results", "pack", "thanks"], name)
            self.assertTrue(case["rules"]["version"], name)

    def test_every_outcome_that_needs_a_price_has_one(self):
        for name in flow.case_type_names():
            case = flow.load_case_type(name)
            for config in case["rules"]["returns"]:
                self.assertIn(config["id"], case["prices"]["returns"], name)
                self.assertNotIn("when_any", config["outcomes"][-1], "the last outcome must always match")
                self.assertNotIn("when_all", config["outcomes"][-1], "the last outcome must always match")


class SampleFamilies(unittest.TestCase):
    """The made-up families give the results the plan expects."""

    def results_for(self, family):
        case, answers, extracted, problems = check_demo.run_family(family)
        self.assertEqual(problems, [])
        return case, answers, rules.evaluate(case, answers, extracted)

    def test_family_a_simple(self):
        _, _, results = self.results_for("a")
        self.assertEqual(statuses(results), {"final_return": "We'll check",
                                             "estate_return": "Probably a simpler route"})
        self.assertEqual(results["points_to_check"], [])

    def test_family_b_medium(self):
        _, _, results = self.results_for("b")
        self.assertEqual(statuses(results), {"final_return": "Likely needed", "estate_return": "May be needed"})
        self.assertEqual(results["missing_documents"], [])
        self.assertEqual([d["text"] for d in results["key_dates"]["dates"]],
                         ["6 April 2026", "14 August 2026", "20 October 2026", "5 April 2027"])

    def test_family_c_complex(self):
        _, _, results = self.results_for("c")
        self.assertEqual(statuses(results), {"final_return": "Likely needed", "estate_return": "May be needed"})
        prices = [line["price"] for line in results["quote"]["lines"]]
        self.assertEqual(prices, ["Included", "£169", "£169"])  # one fixed fee per tax return

    def test_the_quote_adds_up(self):
        totals = {family: self.results_for(family)[2]["quote"]["total"] for family in "abcd"}
        self.assertEqual(totals, {"a": "£139", "b": "£338", "c": "£338", "d": "£169"})
        prices = [line["price"] for line in self.results_for("a")[2]["quote"]["lines"]]
        self.assertEqual(prices, ["Included", "Included", "£139"])

    def test_family_d_doctor(self):
        _, _, results = self.results_for("d")
        self.assertEqual(statuses(results), {"self_assessment": "Likely needed", "fee_relief": "Worth checking"})

    def test_pack_builds_for_every_family(self):
        for family in "abcd":
            case, answers, results = self.results_for(family)
            data = pack.build(case, answers, results)
            self.assertEqual(json.loads(pack.to_json(data))["results"]["rules_version"], case["rules"]["version"])
            self.assertTrue(pack.to_pdf(data).startswith(b"%PDF"), family)


class TaxYear(unittest.TestCase):
    def test_a_death_before_6_april_belongs_to_the_previous_tax_year(self):
        self.assertEqual(rules.tax_year_start(date(2026, 4, 5), 4, 6), date(2025, 4, 6))
        self.assertEqual(rules.tax_year_start(date(2026, 4, 6), 4, 6), date(2026, 4, 6))
        self.assertEqual(rules.tax_year_start(date(2026, 1, 10), 4, 6), date(2025, 4, 6))

    def test_final_return_period(self):
        case, answers, extracted, _ = check_demo.run_family("a")  # died 2 April 2026
        period = rules.evaluate(case, answers, extracted)["returns"][0]["period"]
        self.assertEqual((period["start"], period["end"], period["tax_year_end"]),
                         ("2025-04-06", "2026-04-02", "2026-04-05"))


class DocumentChecks(unittest.TestCase):
    def setUp(self):
        self.case, self.answers, self.extracted, _ = check_demo.run_family("b")

    def status_of(self, results, doc_id):
        return next(d["status"] for d in results["documents"] if d["id"] == doc_id)

    def test_a_different_date_on_the_certificate_is_flagged(self):
        self.answers["date_of_death"] = date(2026, 8, 12)
        results = rules.evaluate(self.case, self.answers, self.extracted)
        self.assertEqual(self.status_of(results, "death_certificate"), "check")
        self.assertIn("Date of death: the certificate shows 14 August 2026, but the answer given was "
                      "12 August 2026.", results["points_to_check"])

    def test_a_document_the_person_has_not_confirmed_is_flagged(self):
        self.extracted["pension_statement"].pop("confirmed")
        results = rules.evaluate(self.case, self.answers, self.extracted)
        self.assertEqual(self.status_of(results, "pension_statement"), "check")
        self.assertEqual(len(results["points_to_check"]), 1)
        self.assertIn("has not confirmed", results["points_to_check"][0])

    def test_a_correction_keeps_both_values_for_the_accountant(self):
        result = self.extracted["pension_statement"]
        result["fields"]["annual_amount"] = "18,500"
        result["corrections"] = {"annual_amount": {"read": 18000, "given": "18,500"}}
        result["confirmed"] = "corrected"
        results = rules.evaluate(self.case, self.answers, self.extracted)
        self.assertEqual(self.status_of(results, "pension_statement"), "added")
        self.assertEqual(results["points_to_check"],
                         ["Pension statements: the person changed the annual amount from 18,000 to 18,500."])
        summary = pack.build(self.case, self.answers, results)["documents"][1]["summary"]
        self.assertIn("£18,500 a year", summary)
        self.assertIn("Corrected by the person", summary)

    def test_a_missing_document_is_listed(self):
        del self.extracted["grant_of_probate"]
        results = rules.evaluate(self.case, self.answers, self.extracted)
        self.assertEqual(results["missing_documents"], ["Grant of probate or letters of administration"])

    def test_a_document_that_cannot_be_read_goes_to_the_accountant(self):
        doc = next(d for d in flow.checklist(self.case, self.answers) if d["id"] == "pension_statement")
        result = extract.read_document(doc, "c_pension_statement.pdf", "b")  # family C has no pension
        self.assertFalse(result["read_ok"])
        self.extracted["pension_statement"] = result
        results = rules.evaluate(self.case, self.answers, self.extracted)
        self.assertIn("Pension statements: this could not be read fully. Please look at the original.",
                      results["points_to_check"])

    def test_not_sure_answers_become_points_for_the_accountant(self):
        self.answers.update(lived_in_uk="no", usually_filed_sa="not_sure", probate="not_yet")
        points = rules.evaluate(self.case, self.answers, self.extracted)["points_to_check"]
        self.assertIn("The person who died lived outside the UK. A specialist should check this.", points)
        self.assertIn("Not sure whether a Self Assessment return was usually sent.", points)
        self.assertIn("Probate has not been granted yet.", points)


class SavedCases(unittest.TestCase):
    """Saving, coming back, sending to the accountant, being asked for a document, and deleting."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.real_out, store.OUT_DIR = store.OUT_DIR, Path(self.folder.name)
        self.case, self.answers, self.extracted, _ = check_demo.run_family("b")

    def tearDown(self):
        store.OUT_DIR = self.real_out
        self.folder.cleanup()

    def send(self, code):
        results = rules.evaluate(self.case, self.answers, self.extracted)
        store.send(code, pack.build(self.case, self.answers, results))

    def test_codes_are_tidied(self):
        self.assertEqual(store.normalise_code(" ktrm 4729 "), "KTRM-4729")
        self.assertEqual(store.normalise_code("KTRM-4729"), "KTRM-4729")
        self.assertIsNone(store.load("NOPE-0000"))

    def test_save_and_come_back(self):
        code = store.create("after_a_death")
        store.save(code, 4, self.answers, self.extracted, "someone@example.com")
        saved = store.load(code)
        self.assertEqual(saved["screen"], 4)
        self.assertEqual(saved["email"], "someone@example.com")
        self.assertEqual(flow.restore_answers(self.case, saved["answers"]), self.answers)  # dates come back as dates
        self.assertEqual(saved["extracted"], self.extracted)
        self.assertEqual(store.sent_cases(), [])  # not in the inbox until it is sent

    def test_send_ask_for_a_document_and_send_again(self):
        code = store.create("after_a_death")
        del self.extracted["grant_of_probate"]
        self.send(code)
        self.assertEqual([c["status"] for c in store.sent_cases()], ["new"])

        store.ask_for(code, "grant_of_probate", "Grant of probate or letters of administration", "A copy is fine.")
        self.assertEqual(store.load(code)["status"], "waiting")
        self.assertEqual(len(store.open_requests(code)), 1)

        self.send(code)  # sent again without the document: still waiting for it
        self.assertEqual(len(store.open_requests(code)), 1)

        doc = next(d for d in flow.checklist(self.case, self.answers) if d["id"] == "grant_of_probate")
        result = extract.read_document(doc, "b_grant_of_probate.pdf", "b")
        result.update(file_name="b_grant_of_probate.pdf", confirmed="yes", added=store.now())
        self.extracted["grant_of_probate"] = result
        self.send(code)
        self.assertEqual(store.open_requests(code), [])
        self.assertEqual(store.load(code)["status"], "updated")

    def test_files_are_kept_and_deleted_with_the_case(self):
        code = store.create("after_a_death")
        stored = store.save_file(code, "death_certificate", "../my cert?.pdf", b"made-up")
        self.assertEqual(stored, "death_certificate__my_cert_.pdf")  # no folders or odd characters
        self.assertEqual(store.read_file(code, stored), b"made-up")
        store.delete(code)
        self.assertIsNone(store.load(code))
        self.assertIsNone(store.read_file(code, stored))


if __name__ == "__main__":
    unittest.main()
