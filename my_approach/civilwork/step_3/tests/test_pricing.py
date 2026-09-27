"""Clause 27 build-up: hand-worked arithmetic on real lines and synthetic boundaries.

Each expected figure is written out from the contract text in the test itself; the
engine is only asked to agree with it.
"""
import datetime as dt
import unittest
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP

from _support import D, accepted, inputs, line, make_app, make_line

from civilwork_audit import contract as C
from civilwork_audit.config import PricingOptions
from civilwork_audit.pricing import price_lines, split_into_bands

CENT = D("0.01")


def half_up(x):
    return x.quantize(CENT, ROUND_HALF_UP)


def price_one(ln, app=None, **opts):
    app = app or make_app(application_no=ln.application_no)
    return price_lines([ln], {ln.application_no: app}, PricingOptions(**opts))[ln.line_ref]


class WorkedExamples(unittest.TestCase):
    """Architecture Appendix C and the boundary lines found in the data."""

    def engine(self, ref):
        return accepted().lines[ref].price

    def test_pa00001_01_night_uplift_in_z2(self):
        ln = line("PA-00001-01")
        self.assertEqual((ln.item_code, ln.zone, ln.night_work, ln.quantity), ("D.43.010", "Z2", True, 299))
        rate = half_up(D("14.80") * D("1.06") * D("1.25"))
        self.assertEqual(rate, D("19.61"))
        self.assertEqual(self.engine(ln.line_ref).amount, rate * 299)
        self.assertEqual(rate * 299, ln.amount)                     # billed correctly: 5,863.39

    def test_pa00576_09_band_split_at_8000(self):
        ln = line("PA-00576-09")
        self.assertEqual((ln.item_code, ln.zone, ln.night_work, ln.quantity), ("A.14.010", "Z1", False, 131))
        p = self.engine(ln.line_ref)
        self.assertEqual(p.band_position, 7935)
        expected = 65 * half_up(D("53.20") * D("0.95")) + 66 * half_up(D("53.20") * D("0.91"))
        self.assertEqual(expected, D("6480.16"))
        self.assertEqual(p.amount, expected)
        self.assertEqual(ln.amount, expected)

    def test_pa00003_06_pre_issue_application_keeps_old_rate(self):
        ln = line("PA-00003-06")
        self.assertLess(inputs().applications["PA-00003"].application_date, C.A3.issued)
        self.assertGreaterEqual(ln.work_date, dt.date(2025, 12, 1))          # 5 % discount, frozen G2
        old = half_up(D("1860.00") * D("1.06") * D("0.95"))
        new = half_up(D("1984.00") * D("1.06") * D("0.95"))
        self.assertEqual((old * 5, new * 5), (D("9365.10"), D("9989.45")))
        self.assertEqual(self.engine(ln.line_ref).amount, old * 5)
        self.assertEqual(ln.amount, old * 5)

    def test_pa00115_05_rounded_once_not_per_step(self):
        ln = line("PA-00115-05")
        once = half_up(D("69.20") * D("1.28") * D("1.375"))
        stepwise = half_up(half_up(D("69.20") * D("1.28")) * D("1.375"))
        self.assertEqual((once, stepwise, ln.rate_applied), (D("121.79"), D("121.80"), D("121.80")))
        r = accepted().lines[ln.line_ref]
        self.assertEqual(r.expected_amount - ln.amount, (once - stepwise) * ln.quantity)
        self.assertEqual(r.categories, ["intermediate_rounding"])

    def test_pa00233_04_half_halala_rounds_up_on_rest_day(self):
        ln = line("PA-00233-04")
        self.assertEqual(ln.work_date.weekday(), 5)                               # Saturday
        unrounded = D("415.00") * D("1.06") * D("1.35")
        self.assertEqual(unrounded, D("593.865"))
        self.assertEqual(half_up(unrounded), D("593.87"))
        self.assertEqual(unrounded.quantize(CENT, ROUND_HALF_EVEN), D("593.86"))
        self.assertEqual(self.engine(ln.line_ref).amount, D("593.87") * 140)
        self.assertEqual(ln.amount, D("83141.80"))

    def test_pa00397_12_usd_conversion_rounds_half_even(self):
        ln = line("PA-00397-12")
        self.assertEqual((ln.item_code, ln.zone, ln.work_date.strftime("%Y-%m")), ("C.32.040", "Z1", "2025-12"))
        converted = D("423.00") * D("375.50") / 100
        self.assertEqual(converted, D("1588.365"))
        self.assertEqual(converted.quantize(CENT, ROUND_HALF_EVEN), D("1588.36"))
        self.assertEqual(self.engine(ln.line_ref).amount, D("1588.36") * 5)
        self.assertEqual(ln.amount, D("7941.80"))

    def test_pa00500_10_band_counter_resets_in_contract_year_2(self):
        ln = line("PA-00500-10")
        self.assertEqual(ln.work_date, dt.date(2026, 1, 5))
        self.assertEqual(self.engine(ln.line_ref).band_position, 0)

    def test_ground_freeze_boundary_lines(self):
        for ref, day, ground in (("PA-00036-07", 27, "G1"), ("PA-00684-06", 27, "G1"), ("PA-00105-04", 28, "G2")):
            ln = line(ref)
            self.assertEqual(ln.work_date, dt.date(2025, 9, day), ref)
            self.assertEqual(self.engine(ref).ground_used, ground, ref)
            self.assertEqual(self.engine(ref).amount, ln.amount, ref)


class BuildUpRules(unittest.TestCase):
    def test_rest_day_alone_when_night_on_rest_day(self):             # Cl 8, P11
        ln = make_line(item_code="B.21.030", unit="m3", work_date=dt.date(2025, 3, 7), night_work=True)
        self.assertEqual(ln.work_date.weekday(), 4)
        p = price_one(ln)
        self.assertEqual((p.uplift_kind, p.uplift_percent), ("rest-day", 35))
        self.assertEqual(p.parts[0].rate, half_up(D("389.00") * D("1.35")))

    def test_night_uplift_capped_above_zone_factor_1_1(self):           # 27A
        for zone, pct in (("Z1 Compound", 25), ("Z2 North Spur", 25), ("Z3 Wadi Crossing", 0), ("Z4 Escarpment", 0)):
            p = price_one(make_line(item_code="D.43.010", unit="lm", site_zone=zone, night_work=True))
            self.assertEqual(p.uplift_percent, pct, zone)

    def test_rest_day_uplift_only_friday_saturday(self):
        for day, pct in ((dt.date(2025, 3, 6), 0), (dt.date(2025, 3, 7), 35), (dt.date(2025, 3, 8), 35), (dt.date(2025, 3, 9), 0)):
            p = price_one(make_line(item_code="D.41.030", work_date=day))
            self.assertEqual(p.uplift_percent, pct, day)

    def test_series_e_has_no_zone_factor_and_unlisted_item_no_ground(self):
        self.assertEqual(price_one(make_line(item_code="E.51.020", unit="day", site_zone="Z4 Escarpment")).zone_factor, 1)
        self.assertEqual(price_one(make_line(item_code="C.32.020", unit="no.", site_zone="Z4 Escarpment")).zone_factor, D("1.28"))
        p = price_one(make_line(item_code="A.11.010", ground_class="G5 Sound Rock"))
        self.assertEqual((p.ground_used, p.ground_factor), ("", 1))

    def test_ground_freeze_synthetic(self):
        before = price_one(make_line(item_code="A.12.030", unit="m3", ground_class="G5 Sound Rock", work_date=dt.date(2025, 9, 27)))
        after = price_one(make_line(item_code="A.12.030", unit="m3", ground_class="G5 Sound Rock", work_date=dt.date(2025, 9, 28)))
        self.assertEqual((before.ground_factor, after.ground_factor), (D("1.63"), 1))

    def test_discount_dates(self):
        cases = [(dt.date(2025, 11, 30), 0), (dt.date(2025, 12, 1), D("0.05")), (dt.date(2026, 3, 31), D("0.05")),
                 (dt.date(2026, 4, 1), D("0.08"))]
        for day, pct in cases:
            self.assertEqual(C.discount_rate("C.32.030", day)[0], pct, day)
        self.assertEqual(C.discount_rate("C.32.020", dt.date(2026, 5, 1))[0], 0)

    def test_discount_is_final_factor_after_band(self):                # S2 s2.2: after the rebate, before rounding
        app = make_app(application_date=dt.date(2026, 6, 30))
        ln = make_line(item_code="B.23.010", unit="tonne", work_date=dt.date(2026, 6, 2), quantity=70)
        p = price_one(ln, app)
        rate = D("4450.00")
        self.assertEqual([(x.quantity, x.percent, x.rate) for x in p.parts],
                         [(60, 100, half_up(rate * D("0.92"))), (10, 97, half_up(rate * D("0.97") * D("0.92")))])


class InstrumentLookup(unittest.TestCase):
    def rate(self, item, day, app_day=dt.date(2026, 12, 31)):
        return C.instrument_rate(item, day, app_day).rate

    def test_b23010_sequence(self):
        self.assertEqual(self.rate("B.23.010", dt.date(2025, 4, 30)), D("4120.00"))
        self.assertEqual(self.rate("B.23.010", dt.date(2025, 5, 1)), D("4385.00"))
        self.assertEqual(self.rate("B.23.010", dt.date(2025, 9, 30)), D("4385.00"))
        self.assertEqual(self.rate("B.23.010", dt.date(2025, 10, 1)), D("4450.00"))

    def test_monthly_rates_and_last_published(self):
        self.assertEqual(self.rate("D.41.020", dt.date(2025, 4, 30)), D("63.50"))
        self.assertEqual(self.rate("D.41.020", dt.date(2025, 7, 15)), D("226.40"))
        self.assertEqual(self.rate("D.41.020", dt.date(2025, 11, 30)), D("220.50"))   # last published
        self.assertEqual(self.rate("D.41.020", dt.date(2025, 12, 1)), D("228.00"))
        self.assertEqual(self.rate("E.54.010", dt.date(2025, 9, 30)), D("876.00"))
        self.assertEqual(self.rate("E.54.010", dt.date(2025, 10, 1)), D("948.00"))
        self.assertEqual(self.rate("E.54.010", dt.date(2026, 4, 1)), D("976.00"))
        self.assertEqual(self.rate("E.54.010", dt.date(2026, 10, 5)), D("1052.00"))   # last published

    def test_clause_31A_boundary(self):
        day = dt.date(2025, 12, 10)
        self.assertEqual(self.rate("A.14.010", day, dt.date(2026, 5, 11)), D("53.20"))
        self.assertEqual(self.rate("A.14.010", day, dt.date(2026, 5, 12)), D("56.80"))
        self.assertEqual(self.rate("A.14.010", dt.date(2025, 10, 31), dt.date(2026, 6, 1)), D("53.20"))
        self.assertEqual(self.rate("C.32.010", day, dt.date(2026, 5, 14)), D("1984.00"))

    def test_contract_years(self):
        self.assertEqual(C.contract_year(dt.date(2025, 1, 5)), 1)
        self.assertEqual(C.contract_year(dt.date(2026, 1, 4)), 1)
        self.assertEqual(C.contract_year(dt.date(2026, 1, 5)), 2)
        self.assertEqual(C.contract_year(dt.date(2026, 9, 30)), 2)
        self.assertIsNone(C.contract_year(dt.date(2026, 10, 1)))


class Bands(unittest.TestCase):
    def test_split_at_edges(self):
        self.assertEqual(split_into_bands("A.14.010", 0, 2000), [(2000, 100)])
        self.assertEqual(split_into_bands("A.14.010", 1990, 20), [(10, 100), (10, 95)])
        self.assertEqual(split_into_bands("A.14.010", 2000, 20), [(20, 95)])
        self.assertEqual(split_into_bands("A.14.010", 7990, 20), [(10, 95), (10, 91)])
        self.assertEqual(split_into_bands("A.14.010", 1990, 6020), [(10, 100), (6000, 95), (10, 91)])
        self.assertEqual(split_into_bands("A.14.010", 9000, 5), [(5, 91)])

    def test_reduced_quantity_keeps_band_position(self):
        lines = [make_line(line_ref="T-00001-01", item_code="A.14.010", unit="m3", quantity=1990),
                 make_line(line_ref="T-00001-02", line_no=2, item_code="A.14.010", unit="m3", quantity=30)]
        prices = price_lines(lines, {"T-00001": make_app()}, PricingOptions())
        p = prices["T-00001-02"]
        self.assertEqual([(x.quantity, x.percent) for x in p.parts], [(10, 100), (20, 95)])
        self.assertEqual(p.amount_for(15), 10 * D("53.20") + 5 * D("50.54"))
        self.assertEqual(p.amount_for(0), 0)


if __name__ == "__main__":
    unittest.main()
