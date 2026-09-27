"""Data facts the rules rely on (architecture Part B) and the contract's own worked
example (Appendix B, p36), carried over from the Step 2 prototype's named checks."""
import datetime as dt
import os
import re
import unittest
from collections import Counter
from decimal import ROUND_FLOOR

from _support import D, TRANSCRIPTION, accepted, inputs, line, make_app, make_line

from civilwork_audit import contract as C
from civilwork_audit.config import PricingOptions
from civilwork_audit.pricing import price_lines


class ContractWorkedExample(unittest.TestCase):
    """Appendix B prices three lines. Two reproduce; C.31.010 at 91.37 = 86.20 x 1.06
    omits the Clause 29A index (reportable guideline/contract difference A6.5)."""

    def test_appendix_b(self):
        app = make_app(site="S-03 Access Road", site_zone="Z2 North Spur", period_from=dt.date(2025, 5, 6),
                       period_to=dt.date(2025, 5, 13), application_date=dt.date(2025, 5, 22))
        common = dict(site="S-03 Access Road", site_zone="Z2 North Spur")
        lines = [
            make_line(line_ref="T-00001-01", line_no=1, item_code="A.12.020", unit="m3", ground_class="G4 Weathered Rock",
                      work_date=dt.date(2025, 5, 6), quantity=180, **common),
            make_line(line_ref="T-00001-02", line_no=2, item_code="A.14.020", unit="m3", ground_class="G2 Firm Sabkha",
                      work_date=dt.date(2025, 5, 7), quantity=96, **common),
            make_line(line_ref="T-00001-03", line_no=3, item_code="C.31.010", unit="lm", ground_class="G2 Firm Sabkha",
                      work_date=dt.date(2025, 5, 13), quantity=48, **common)]
        p = price_lines(lines, {"T-00001": app}, PricingOptions())
        self.assertEqual(p["T-00001-01"].parts[0].rate, D("50.72"))
        self.assertEqual(p["T-00001-02"].parts[0].rate, D("23.74"))
        self.assertEqual(p["T-00001-03"].base, D("88.44"))          # 86.20 x 102.60 / 100, half-even
        self.assertEqual(p["T-00001-03"].parts[0].rate, D("93.75"))  # not the 91.37 printed
        self.assertEqual((D("15794.40") * D("0.05")).quantize(D("0.01"), ROUND_FLOOR), D("789.72"))


class DataFacts(unittest.TestCase):
    def test_line_descriptions_are_schedule_1_wording(self):
        sched = {}
        for n in (17, 18, 19):
            with open(os.path.join(TRANSCRIPTION, f"page_{n:03d}.md"), encoding="utf-8") as f:
                for m in re.finditer(r"^\| ([A-E]\.\d\d\.\d{3}) \| ([^|]+?) \|", f.read(), re.M):
                    sched[m.group(1)] = m.group(2)
        for ln in inputs().lines:
            self.assertEqual(ln.description, sched[ln.item_code], ln.line_ref)

    def test_application_level_fields(self):
        apps = inputs().applications.values()
        self.assertTrue(all(a.adjustment == 0 and a.retention_released == 0 for a in apps))
        self.assertTrue(all(a.retention == (a.application_total * C.RETENTION_RATE).quantize(D("0.01"), ROUND_FLOOR) for a in apps))
        self.assertTrue(all(a.net_payable == a.application_total - a.retention for a in apps))
        self.assertEqual(sorted(a.application_no for a in apps if a.contract_ref != C.CONTRACT_REF), ["PA-00560", "PA-00711"])

    def test_issue_day_applications_priced_at_new_rate(self):
        for ref in ("PA-00006-14", "PA-00380-02"):
            r = accepted().lines[ref]
            self.assertEqual((r.price.base, r.price.amount), (D("56.80"), r.line.amount), ref)

    def test_31A_population_billed_total(self):
        refs = accepted().plan.a31_lines
        self.assertEqual(sum(line(r).amount for r in refs), D("902512.37"))
        self.assertEqual(sorted(r for r in refs if accepted().lines[r].price.amount != line(r).amount), ["PA-00350-02"])

    def test_shared_dewatering_records_never_share_a_date(self):
        by_rec = {}
        for ln in inputs().lines:
            if ln.record_ref.startswith("DW"):
                by_rec.setdefault(ln.record_ref, []).append(ln.work_date)
        shared = {r: d for r, d in by_rec.items() if len(d) > 1}
        self.assertEqual(len(shared), 19)
        self.assertTrue(all(len(set(d)) == len(d) for d in shared.values()))
        same_app = sorted(r for r in shared if len({ln.application_no for ln in inputs().lines if ln.record_ref == r}) == 1)
        self.assertEqual(same_app, ["DW-00045", "DW-00097"])

    def test_work_after_completion_only_on_two_lines(self):
        late = sorted(ln.line_ref for ln in inputs().lines if ln.work_date > C.COMPLETION)
        self.assertEqual(late, ["PA-00375-07", "PA-00678-10"])
        self.assertEqual(Counter(ln.application_no for ln in inputs().lines if ln.work_date < C.COMMENCEMENT), Counter())


if __name__ == "__main__":
    unittest.main()
