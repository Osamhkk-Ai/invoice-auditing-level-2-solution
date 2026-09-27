"""Record parsing, line evidence and cross-application limits (checks 4, 5, 6, 9, 10)."""
import datetime as dt
import unittest
from collections import Counter

from _support import D, accepted, make_app, make_line, records

from civilwork_audit import contract as C
from civilwork_audit.config import ACCEPTED
from civilwork_audit.cross_checks import apply_cross_checks
from civilwork_audit.evidence import assess_line
from civilwork_audit.records import BODY_PATTERNS, parse_record_text

RECORD = """CONCRETE POUR RECORD
Ticket: PR-99999
Job: Northern Access Road, Package 4
Area: S-01 Platform North
Date: 07/03/2025

{body}

Signed (foreman): K. Doyle
Countersigned (Engineer's representative): {counter}
"""


def res(ref):
    return accepted().lines[ref]


class RecordParsing(unittest.TestCase):
    def test_every_record_matches_one_known_pattern(self):
        recs = records()
        self.assertEqual(len(recs), 2169)
        self.assertEqual([r.ref for r in recs.values() if not r.pattern_id], [])
        self.assertEqual([r.ref for r in recs.values() if r.problems], [])
        self.assertEqual(len({r.pattern_id for r in recs.values()}), len(BODY_PATTERNS))
        self.assertEqual(Counter(r.series for r in recs.values()),
                         Counter(CT=381, CV=120, DW=114, DX=266, JS=368, MO=142, PR=365, PS=143, PT=270))

    def test_signatures(self):
        recs = records()
        self.assertEqual([r.ref for r in recs.values() if not r.countersigned], ["DX-00089"])
        self.assertEqual([r.ref for r in recs.values() if not r.signed], [])

    def test_quantity_is_the_quantity_not_the_depth(self):
        rec = parse_record_text("DX-99999", "DAILY EXCAVATION RECORD\nTicket: DX-99999\nArea: S-01 Platform North\n"
                                            "Date: 01/03/2025\n\ntrench dig 210 cube, 3 m deep section\n")
        self.assertEqual((rec.item, rec.quantity), ("A.12.030", 210))

    def test_depth_on_a_band_edge_is_unresolved(self):              # guideline check 6
        rec = parse_record_text("DX-99999", "DAILY EXCAVATION RECORD\nTicket: DX-99999\n\ntrench dig 210 cube, 4 m deep section\n")
        self.assertIsNone(rec.item)
        self.assertEqual(rec.quantity, 210)

    def test_unknown_wording_and_other_mix_are_not_guessed(self):
        self.assertEqual(parse_record_text("PR-99999", RECORD.format(body="poured 40 m3 of something", counter="X")).pattern_id, "")
        self.assertEqual(parse_record_text("PR-99999", RECORD.format(body="wall pour 40 m3, 25/30 mix", counter="X")).pattern_id, "")

    def test_underscore_countersignature_is_missing(self):
        rec = parse_record_text("PR-99999", RECORD.format(body="wall pour 40 m3, 32/40 mix", counter="____________"))
        self.assertEqual((rec.item, rec.quantity, rec.signed, rec.countersigned), ("B.21.040", 40, True, False))

    def test_imported_stone_is_granular_fill_at_record_quantity(self):
        stone = [r for r in accepted().lines.values()
                 if r.line.record_ref in records() and "imported stone" in records()[r.line.record_ref].body]
        self.assertEqual(len(stone), 51)
        for r in stone:
            self.assertEqual((r.line.item_code, r.assessment.evidence_status), ("A.14.010", "ok"), r.line.line_ref)
            self.assertEqual(r.assessment.record_qty, r.line.quantity)

    def test_dewatering_week_across_year_end(self):
        rec = parse_record_text("DW-99999", "DEWATERING LOG\nTicket: DW-99999\nWeek beginning: 29/12/2025\n"
                                            "Days on: Mon 29/12, Tue 30/12, Wed 31/12, Thu 01/01, Fri 02/01\n\n"
                                            "pumps kept going 1 week this period\n")
        self.assertEqual(rec.week_days[-1], dt.date(2026, 1, 2))
        self.assertEqual(len(rec.week_days), 5)


class LineEvidence(unittest.TestCase):
    def test_record_usable_on_2188_lines_and_word_mismatch_nowhere(self):
        statuses = Counter(r.assessment.evidence_status for r in accepted().lines.values())
        self.assertEqual(statuses["ok"], 2188)
        self.assertFalse(any("record_mismatch" in r.categories for r in accepted().lines.values()))

    def test_missing_wrong_series_and_unsigned_records_zero_the_line(self):
        cases = {"PA-00111-12": "record_missing", "PA-00111-13": "record_missing",
                 "PA-00631-10": "record_missing", "PA-00766-12": "record_missing",
                 "PA-00170-04": "record_wrong_series", "PA-00613-01": "record_not_countersigned"}
        for ref, cat in cases.items():
            self.assertIn(cat, res(ref).categories, ref)
            self.assertEqual(res(ref).expected_amount, 0, ref)
        missing_files = sorted(r.line.record_ref for r in accepted().lines.values() if r.assessment.evidence_status == "file_missing")
        self.assertEqual(missing_files, ["CT-00126", "MO-00089", "PS-00039"])

    def test_chargeable_hour(self):                                      # 6A
        hourly_ok = [r for r in accepted().lines.values()
                     if r.line.item_code in C.HOURLY_ITEMS and r.assessment.evidence_status == "ok"]
        self.assertEqual(sum(r.line.quantity == r.assessment.record_qty - 1 for r in hourly_ok), 284)
        r = res("PA-00243-03")
        self.assertEqual((r.line.quantity, r.assessment.record_qty, r.assessment.supported_qty), (10, 10, 9))
        self.assertEqual(r.delta, -D("246.00"))                           # one hour of E.51.010 at base

    def test_survey_tolerance(self):                                     # 33A
        within = [r for r in accepted().lines.values()
                  if r.line.item_code in C.SURVEYED_ITEMS and r.assessment.evidence_status == "ok"
                  and r.line.quantity > r.assessment.record_qty]
        paid_as_billed = [r for r in within if r.assessment.supported_qty == r.line.quantity]
        self.assertEqual(len(paid_as_billed), 25)
        for r in paid_as_billed:
            self.assertLessEqual(D(r.line.quantity), D(r.assessment.record_qty) * D("1.02"))
        r = res("PA-00312-04")
        self.assertEqual((r.line.quantity, r.assessment.record_qty, r.assessment.supported_qty), (4, 3, 3))
        self.assertIn("qty_above_survey_tolerance", r.categories)

    def test_wrong_unit_rejected_in_full(self):                           # Cl 26
        for ref in ("PA-00052-02", "PA-00406-03", "PA-00833-07", "PA-00892-06"):
            self.assertEqual((res(ref).assessment.supported_qty, res(ref).expected_amount), (0, 0), ref)
            self.assertIn("unit_not_per_schedule", res(ref).categories)

    def test_term_period_and_submission_date(self):
        for ref in ("PA-00375-07", "PA-00678-10"):
            self.assertIn("work_after_term", res(ref).categories, ref)
        for ref in ("PA-00154-03", "PA-00700-01"):
            self.assertIn("line_outside_period", res(ref).categories, ref)
            self.assertIn("work_after_submission", res(ref).categories, ref)
        pa125 = [r for r in accepted().lines.values() if r.line.application_no == "PA-00125"]
        self.assertEqual(len(pa125), 6)
        self.assertTrue(all(r.expected_amount == 0 and "work_after_submission" in r.categories for r in pa125))

    def test_weekly_record_needs_five_days(self):                        # 47A
        recs = {"DW-99999": parse_record_text("DW-99999", "DEWATERING LOG\nTicket: DW-99999\nArea: S-01 Platform North\n"
                                               "Week beginning: 02/06/2025\nDays on: Mon 02/06, Tue 03/06, Wed 04/06, Thu 05/06\n\n"
                                               "pumps kept going 1 week this period\nSigned (foreman): A\n"
                                               "Countersigned (Engineer's representative): B\n")}
        ln = make_line(item_code="A.16.010", unit="week", work_date=dt.date(2025, 6, 4), record_ref="DW-99999")
        la = assess_line(ln, make_app(), recs, ACCEPTED)
        self.assertEqual((la.supported_qty, la.categories), (0, ["week_under_five_days"]))


class CrossApplication(unittest.TestCase):
    def test_clause_44_duplicate(self):
        self.assertIn("duplicate_measurement", res("PA-00111-12").categories)
        self.assertNotIn("duplicate_measurement", res("PA-00111-03").categories)

    def test_daily_limits(self):
        self.assertEqual((res("PA-00845-03").line.quantity, res("PA-00845-03").assessment.supported_qty), (3440, 3200))
        self.assertEqual((res("PA-00243-10").line.quantity, res("PA-00243-10").assessment.supported_qty), (3, 1))
        self.assertEqual(res("PA-00243-10").delta, -2 * D("684.00"))

    def test_same_item_area_date_in_two_applications_later_disallowed_in_full(self):
        # Cl 44 runs before Cl 31: a second measurement of the same item, work area and
        # date is disallowed in full, not cut to the remaining daily room.
        a = make_line(line_ref="T-00001-01", application_no="T-00001", item_code="C.32.020", unit="no.", quantity=2)
        b = make_line(line_ref="T-00002-01", application_no="T-00002", item_code="C.32.020", unit="no.", quantity=2)
        las = {x.line_ref: assess_line(x, make_app(application_no=x.application_no), {}, ACCEPTED) for x in (a, b)}
        apply_cross_checks(las, ACCEPTED)
        self.assertEqual((las["T-00001-01"].supported_qty, las["T-00002-01"].supported_qty), (2, 0))
        self.assertEqual(las["T-00002-01"].categories, ["duplicate_measurement"])

    def test_daily_limit_cuts_excess_without_carry_forward(self):
        ln = make_line(item_code="E.53.010", unit="day", quantity=5)
        nxt = make_line(line_ref="T-00001-02", line_no=2, item_code="E.53.010", unit="day", quantity=1,
                        work_date=ln.work_date + dt.timedelta(days=1))
        las = {x.line_ref: assess_line(x, make_app(), {}, ACCEPTED) for x in (ln, nxt)}
        apply_cross_checks(las, ACCEPTED)
        self.assertEqual((las[ln.line_ref].supported_qty, las[nxt.line_ref].supported_qty), (2, 1))

    def test_p19_window(self):
        self.assertIn("mutually_exclusive_item", res("PA-00801-05").categories)      # day 0
        for ref in ("PA-00017-04", "PA-00199-02", "PA-00235-13", "PA-00248-06", "PA-00302-04",
                    "PA-00348-03", "PA-00389-02", "PA-00485-04", "PA-00554-02"):     # day 3: allowed
            self.assertGreater(res(ref).assessment.supported_qty, 0, ref)
            self.assertNotIn("mutually_exclusive_item", res(ref).categories, ref)

    def test_p21_traffic_management_on_surfacing_day(self):
        tm = make_line(line_ref="T-00001-02", line_no=2, item_code="E.51.020", unit="day")
        surf = make_line(line_ref="T-00001-01", item_code="D.43.010", unit="lm", quantity=50)
        las = {x.line_ref: assess_line(x, make_app(), {}, ACCEPTED) for x in (tm, surf)}
        apply_cross_checks(las, ACCEPTED)
        self.assertEqual(las["T-00001-02"].categories, ["traffic_management_during_surfacing"])
        self.assertEqual(las["T-00001-01"].supported_qty, 50)

    def test_q2_shared_dewatering_record_is_not_a_duplicate(self):
        dw = Counter(r.line.record_ref for r in accepted().lines.values() if r.line.record_ref.startswith("DW"))
        shared = [ref for ref, n in dw.items() if n > 1]
        self.assertEqual(len(shared), 19)
        for r in accepted().lines.values():
            if r.line.record_ref in shared:
                self.assertEqual(r.categories, [], r.line.line_ref)


if __name__ == "__main__":
    unittest.main()
