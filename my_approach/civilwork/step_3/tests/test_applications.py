"""Application decisions: totals, procedural breaches, 31A and 45A, and the documented
baseline (architecture Appendix A, parsed from the document rather than copied)."""
import csv
import datetime as dt
import os
import re
import unittest
from decimal import ROUND_FLOOR

from _support import D, REPO, accepted, inputs

ARCH = os.path.join(REPO, "my_approach", "civilwork", "step_2_audit_system_design", "civilwork_audit_architecture_final.md")
DATA = os.path.join(REPO, "invoice-auditing-level-2", "civilwork", "invoices")


def appendix_a() -> dict[str, tuple[str, D, D, float]]:
    with open(ARCH, encoding="utf-8") as f:
        text = f.read()
    table = text[text.index("## Appendix A"):text.index("## Appendix B")]
    out = {}
    for m in re.finditer(r"^\| (PA-\d{5}) \| (\w+)[^|]*\| ([\d,.]+) \| ([\d,.]+) \| [^|]+\| ([\d.]+) \|$", table, re.M):
        out[m.group(1)] = (m.group(2), D(m.group(3).replace(",", "")), D(m.group(4).replace(",", "")), float(m.group(5)))
    return out


def app(no):
    return accepted().applications[no]


class DocumentedBaseline(unittest.TestCase):
    def test_flagged_set_category_totals_and_confidence_match_appendix_a(self):
        doc = appendix_a()
        self.assertEqual(len(doc), 59)
        flagged = {k for k, d in accepted().applications.items() if d.flagged}
        self.assertEqual(flagged, set(doc))
        for no, (cat, billed, expected, conf) in doc.items():
            d = app(no)
            self.assertEqual((d.error_category, d.billed_total, d.expected_total, d.confidence),
                             (cat, billed, expected, conf), no)

    def test_flag_rate_inside_readme_band(self):
        n = sum(d.flagged for d in accepted().applications.values())
        self.assertTrue(0.05 * 900 <= n <= 0.08 * 900, n)       # README: 5-8 % are wrong


class ApplicationRules(unittest.TestCase):
    def test_pa00043_total_arithmetic_corrected_not_zeroed(self):   # Q3
        d = app("PA-00043")
        self.assertEqual(d.billed_total - d.line_sum, D("32.18"))
        self.assertEqual(d.expected_total, D("231425.26"))
        self.assertEqual(d.error_category, "total_arithmetic")

    def test_pa00125_all_work_after_submission_is_zero(self):        # Q3
        a = inputs().applications["PA-00125"]
        self.assertEqual((a.application_date, a.period_to), (dt.date(2025, 4, 15), dt.date(2025, 4, 29)))
        self.assertEqual(app("PA-00125").expected_total, 0)
        self.assertIn("submitted_before_period_end", app("PA-00125").causes)

    def test_procedural_breaches_flag_but_keep_supported_total(self):  # Q3
        for no, cat in (("PA-00560", "wrong_contract_ref"), ("PA-00711", "wrong_contract_ref"),
                        ("PA-00699", "submitted_late"), ("PA-00708", "submitted_late")):
            d = app(no)
            self.assertTrue(d.flagged, no)
            self.assertEqual(d.error_category, cat, no)
            self.assertEqual(d.expected_total, d.billed_total, no)
        self.assertIn("submitted_late", app("PA-00613").causes)       # 26 days

    def test_late_is_more_than_21_days(self):
        lags = {no: (a.application_date - a.period_to).days for no, a in inputs().applications.items()}
        self.assertEqual(sorted(no for no, lag in lags.items() if lag > 21), ["PA-00613", "PA-00699", "PA-00708"])
        self.assertTrue(all("submitted_late" not in app(no).causes for no, lag in lags.items() if lag == 21))

    def test_q1_pa00443_carries_31A_with_total_unchanged(self):
        d = app("PA-00443")
        self.assertEqual((d.flagged, d.error_category, d.adjustment_due), (True, "adjustment_31A_omitted", D("60508.18")))
        self.assertEqual(d.expected_total, d.billed_total)
        for no in ("PA-00006", "PA-00023", "PA-00380"):              # submitted on the issue date
            self.assertEqual(inputs().applications[no].application_date, dt.date(2026, 5, 12))
            self.assertFalse(app(no).flagged, no)
        self.assertEqual(accepted().plan.a31_carriers, ["PA-00443"])

    def test_45A_release_from_raw_csv(self):
        with open(os.path.join(DATA, "applications.csv"), encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        after = sorted((r["application_date"], r["application_no"]) for r in rows if r["application_date"] > "2026-09-30")
        carrier_date, carrier = after[0]
        held = sum(D(r["retention"]) for r in rows if r["application_date"] < carrier_date)
        release = (held / 2).quantize(D("0.01"), ROUND_FLOOR)
        self.assertEqual((carrier, held, release), ("PA-00678", D("8069143.47"), D("4034571.73")))
        self.assertEqual(app("PA-00678").release_due, release)
        self.assertIn("retention_release_45A_omitted", app("PA-00678").causes)

    def test_under_billed_applications_get_a_higher_expected_total(self):
        for no in ("PA-00248", "PA-00297", "PA-00610", "PA-00659", "PA-00803", "PA-00889"):
            self.assertGreater(app(no).expected_total, app(no).billed_total, no)
        self.assertEqual(app("PA-00297").expected_total - app("PA-00297").billed_total, D("151483.86"))

    def test_pa00243_two_line_reductions(self):
        self.assertEqual(app("PA-00243").expected_total, D("92485.16"))
        self.assertEqual(app("PA-00243").billed_total - app("PA-00243").expected_total, D("246.00") + 2 * D("684.00"))

    def test_unflagged_applications_reconcile_exactly(self):
        for no, d in accepted().applications.items():
            if not d.flagged:
                self.assertEqual((d.expected_total, d.line_sum, d.causes), (d.billed_total, d.billed_total, {}), no)
                self.assertEqual(d.confidence, 0.90)

    def test_every_flag_has_a_clause_backed_cause(self):
        for no, d in accepted().applications.items():
            if d.flagged:
                self.assertTrue(d.causes, no)
                self.assertIn(d.error_category, d.causes, no)


if __name__ == "__main__":
    unittest.main()
