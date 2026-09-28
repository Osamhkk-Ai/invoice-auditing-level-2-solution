"""Invoice-level outcomes: named examples, negative controls, the documented readings and their
alternatives, and consistency between the submission row and its audit trail."""
import datetime as dt
import unittest
from decimal import Decimal as D

from _support import audit, inputs
from drilling_audit import categories as K
from drilling_audit.config import PRODUCTION


def cents(x):
    return int(x * 100)


class NamedExamples(unittest.TestCase):
    def inv(self, n, cfg=PRODUCTION):
        return audit(cfg).invoices[n]

    def test_discount_missing_MDS_00072(self):
        i = self.inv("MDS-00072")
        self.assertEqual((i.flagged, i.error_category, i.discount), (True, "invoice_discount_omitted", D("-42302.10")))
        self.assertEqual(i.billed_total - i.expected_total, D("48647.42"))       # 42,302.10 + 15 % VAT

    def test_total_arithmetic_MDS_00551(self):
        i = self.inv("MDS-00551")
        self.assertEqual(i.error_category, "total_arithmetic")
        self.assertEqual(i.expected_total, i.net + i.vat)

    def test_procedural_only_rows_keep_amount(self):
        for n, cat in (("MDS-00038", "submitted_late"), ("MDS-00645", "submitted_before_period_end"),
                       ("MDS-01799", "wrong_contract_ref"), ("MDS-00672", "wrong_contract_ref")):
            i = self.inv(n)
            self.assertEqual((i.flagged, i.error_category, i.expected_total, i.confidence),
                             (True, cat, i.billed_total, 0.8), n)

    def test_line_examples(self):
        L = audit().lines
        cases = {  # line: (reasons, expected amount) - hand figures in test_pricing
            "MDS-00214-011": (["rate_differs"], D("2154.17")),
            "MDS-00062-021": (["qty_above_report"], D("1421.25")),         # 125 m x 11.37
            "MDS-00121-043": (["rate_differs"], D("3293.10")),         # 2 x 1,646.55 (no discount in 2025)
            "MDS-00307-006": (["rate_differs"], D("1225326.75")),
            "MDS-00639-027": (["rate_differs"], D("358050.00")),
            "MDS-01739-041": (["rate_differs"], None),
            "MDS-00320-016": (["not_supported_by_report"], D(0)),          # MB-701 on a later day
            "MDS-00954-021": (["part_C_absent"], D(0)),
        }
        for ref, (reasons, amount) in cases.items():
            self.assertEqual(L[ref].reasons, reasons, ref)
            if amount is not None:
                self.assertEqual(L[ref].expected_amount, amount, ref)
        self.assertEqual(L["MDS-01739-041"].rate.rate, D("365.60"))

    def test_rate_labels_follow_the_mechanism(self):
        L = audit().lines
        cases = {"MDS-00214-011": "index_or_fx_month_wrong", "MDS-00307-006": "index_or_fx_month_wrong",
                 "MDS-00121-043": "discount_early", "MDS-00639-027": "lost_in_hole_value_wrong",
                 "MDS-00840-023": "rate_superseded", "MDS-00042-058": "standby_rate_wrong",
                 "MDS-00586-039": "depth_band_wrong", "MDS-00215-020": "class_factor_wrong",
                 "MDS-01342-017": "discount_omitted", "MDS-00856-039": "chargeable_hour_not_deducted",
                 "MDS-00954-021": "record_missing", "MDS-00320-016": "charge_not_in_record"}
        for ref, cat in cases.items():
            self.assertEqual(L[ref].categories, [cat], ref)

    def test_duplicates_and_out_of_term(self):
        L = audit().lines
        self.assertEqual(sorted(k for k, r in L.items() if "already_billed" in r.reasons),
                         ["MDS-00476-051", "MDS-00580-046", "MDS-01654-078"])
        self.assertEqual(sorted(r.line.invoice_no for r in L.values() if "outside_term" in r.reasons),
                         ["MDS-01619", "MDS-01798", "MDS-01860"])


class Adjustment36A(unittest.TestCase):
    def test_production_reading(self):
        i = audit().invoices["MDS-01625"]
        self.assertEqual(i.invoice.invoice_date, dt.date(2026, 8, 17))
        self.assertEqual((i.flagged, i.error_category, i.adjustment), (True, "adjustment_36A_omitted", D("309965.52")))
        self.assertEqual((i.billed_total, i.expected_total), (D("226300.58"), D("536266.10")))
        self.assertEqual(i.expected_total, i.net + i.vat + i.adjustment)          # no VAT on the adjustment
        self.assertEqual(i.confidence, 0.7)

    def test_only_one_invoice_carries_it(self):
        self.assertEqual([n for n, i in audit().invoices.items() if i.adjustment], ["MDS-01625"])

    def test_separate_entry_reading(self):
        i = audit(PRODUCTION.with_(adjustment_treatment="separate")).invoices["MDS-01625"]
        self.assertEqual((i.flagged, i.error_category, i.expected_total), (True, "adjustment_36A_omitted", D("226300.58")))

    def test_vat_on_adjustment_reading(self):
        i = audit(PRODUCTION.with_(vat_on_adjustment=True)).invoices["MDS-01625"]
        self.assertEqual(i.expected_total, D("582760.92"))                         # (196,783.11 + 309,965.52) x 1.15

    def test_strict_after_reading(self):
        res = audit(PRODUCTION.with_(a3_carrier="strictly_after_first_number"))
        self.assertEqual(res.plan.candidates_strictly_after, ["MDS-01585", "MDS-01631", "MDS-01645"])
        self.assertEqual(res.plan.carrier, "MDS-01585")
        self.assertFalse(res.invoices["MDS-01625"].flagged)
        i = res.invoices["MDS-01585"]
        self.assertEqual((i.flagged, i.expected_total - i.billed_total), (True, D("309965.52")))

    def test_tied_candidates_carry_lower_confidence(self):
        for n in ("MDS-01585", "MDS-01631", "MDS-01645"):
            i = audit().invoices[n]
            self.assertEqual((i.flagged, i.confidence), (False, 0.75), n)


class UnsignedReports(unittest.TestCase):
    AFFECTED = ["MDS-00340", "MDS-00842", "MDS-00901"]

    def test_production_zeroes_the_day(self):
        res = audit()
        for n in self.AFFECTED:
            self.assertEqual(res.invoices[n].error_category, "record_not_signed", n)
        lines = [r for r in res.lines.values() if "report_unsigned" in r.reasons]
        self.assertEqual(len(lines), 33)
        self.assertTrue(all(r.expected_amount == 0 for r in lines))
        self.assertEqual(res.invoices["MDS-00901"].billed_total - res.invoices["MDS-00901"].expected_total, D("47191.22"))

    def test_alternatives(self):
        base = audit()
        s5 = audit(PRODUCTION.with_(unsigned_policy="zero_schedule5"))
        keep = audit(PRODUCTION.with_(unsigned_policy="flag_only"))
        for n in self.AFFECTED:
            b, m, k = (x.invoices[n] for x in (base, s5, keep))
            self.assertTrue(b.flagged and m.flagged and k.flagged, n)
            self.assertLess(b.expected_total, m.expected_total, n)
            self.assertLessEqual(m.expected_total, k.expected_total, n)
            self.assertEqual(k.expected_total, k.billed_total, n)      # amounts kept: only the flag remains
        s5_codes = {r.line.code for r in s5.lines.values() if "report_unsigned" in r.reasons and r.expected_amount == 0}
        self.assertEqual(s5_codes, {"RM-510"})                        # the only Clause 37 code billed on those days


class NegativeControls(unittest.TestCase):
    """Unusual lines the contract allows must stay clean unless they carry a separate identified defect."""

    def group(self, pred):
        res = audit()
        g = [r for r in res.lines.values() if pred(r.line)]
        return g, [r.line.line_ref for r in g if r.reasons or r.delta]

    def test_standby_run_charges(self):
        for code in ("DD-111", "LW-420"):
            g, bad = self.group(lambda l, c=code: l.code == c and l.status == "Standby")
            self.assertEqual((len(g), bad), (9, []), code)

    def test_pd210_band_split_lines(self):
        g, bad = self.group(lambda l: l.code == "PD-210" and (l.depth_from in (1500, 3000, 4500) or l.depth_to in (1500, 3000, 4500)))
        self.assertEqual((len(g), bad), (375, []))

    def test_pre_issue_A3_lines_at_old_rate(self):
        inv = inputs().invoices
        g, bad = self.group(lambda l: l.code in ("DD-101", "DD-120") and l.service_date >= dt.date(2026, 2, 1)
                            and inv[l.invoice_no].invoice_date < dt.date(2026, 8, 17))
        self.assertEqual(len(g), 3309)
        self.assertEqual(len(bad), 0)

    def test_hc601_carried_forward(self):
        g, bad = self.group(lambda l: l.code == "HC-601" and l.service_date.year == 2026)
        self.assertEqual((len(g), bad), (769, []))
        self.assertTrue(all(r.line.rate in (D("736.40"), D("368.20")) for r in g))

    def test_misquoted_report_numbers_unflagged(self):
        res = audit()
        for n, ref in (("MDS-00128", "MDS-00128-026"), ("MDS-01352", "MDS-01352-007")):
            self.assertEqual(res.lines[ref].reasons, [])
            self.assertTrue(res.lines[ref].warnings)
            self.assertEqual((res.invoices[n].flagged, res.invoices[n].confidence), (False, 0.75))


class Consistency(unittest.TestCase):
    def test_headline_counts(self):
        res = audit()
        L = res.lines
        self.assertEqual(len(L), 91181)
        self.assertEqual(sum(1 for r in L.values() if not r.reasons and not r.delta), 91047)
        flagged = [i for i in res.invoices.values() if i.flagged]
        self.assertEqual(len(flagged), 120)
        self.assertEqual(sum(1 for i in res.invoices.values() if i.expected_total != i.billed_total), 111)

    def test_flags_categories_and_totals_agree(self):
        for n, i in audit().invoices.items():
            if i.expected_total != i.billed_total:
                self.assertTrue(i.flagged, n)
            self.assertEqual(i.flagged, bool(i.causes), n)
            if i.flagged:
                self.assertIn(i.error_category, i.causes, n)
                self.assertEqual(i.error_category, max(i.causes, key=lambda c: (i.causes[c], -K.ORDER[c])), n)
                lih_only = i.causes.keys() == {"index_or_fx_month_wrong"} and all(
                    r.line.code.startswith("LH-") for r in i.lines if "rate_differs" in r.reasons)
                self.assertEqual(i.confidence, 0.85 if lih_only else min(K.CONFIDENCE[c] for c in i.causes), n)
            else:
                self.assertIn(i.confidence, (0.9, 0.75), n)
            # the rebuilt total is exactly the audit trail's sum: services + discount + VAT + adjustment
            self.assertEqual(i.services, sum((r.expected_amount for r in i.lines), D(0)), n)
            self.assertEqual(i.expected_total, i.services + i.discount + i.vat + i.adjustment, n)
            self.assertNotIn("rebuilt_total_differs", i.reasons, n)

    def test_every_exception_line_has_a_clause(self):
        for ref, r in audit().lines.items():
            for reason in r.reasons:
                self.assertTrue(K.clause(reason), ref)
            if r.delta:
                self.assertTrue(r.reasons, ref)

    def test_category_vocabulary(self):
        cats = {i.error_category for i in audit().invoices.values() if i.flagged}
        self.assertTrue(cats <= set(K.CATEGORY_ORDER))
        self.assertEqual(len(cats), 24)
        self.assertNotIn("rate_wrong", cats)                          # every wrong rate has a named mechanism


if __name__ == "__main__":
    unittest.main()
