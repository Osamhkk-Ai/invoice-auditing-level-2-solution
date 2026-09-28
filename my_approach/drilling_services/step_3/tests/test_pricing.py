"""Rate build-up: hand arithmetic on real lines, every effective-date boundary, and synthetic cases for
rules the data never exercises. Expected figures are written out by hand, not taken from the engine."""
import datetime as dt
import unittest
from decimal import Decimal as D

import _support  # noqa: F401
from drilling_audit.config import PricingOptions
from drilling_audit.money import r2, to_cents
from drilling_audit.pricing import (base_rate, build_rate, invoice_discount, lih_value, pd210_amount,
                                    pd210_segments, pd210_volume_parts, vat)

d = dt.date
PRE, POST = d(2026, 8, 16), d(2026, 8, 17)


def rate(code, day, sec, st, cls, idate=None, **opt):
    return build_rate(code, day, sec, st, cls, idate, PricingOptions(**opt)).rate


# (code, day, section, status, class, invoice date, expected, why) - Step 2 check_02, hand-derived
BOUNDARIES = [
    ("DD-120", d(2025, 6, 30), '12-1/4"', "Operating", "Standard", None, "384.15", "Sch1 before S1"),
    ("DD-120", d(2025, 7, 1), '12-1/4"', "Operating", "Standard", None, "398.50", "S1 1.1"),
    ("DD-121", d(2025, 6, 30), '8-1/2"', "Standby", "Standard", None, "2893.65", "Sch1 before S1"),
    ("DD-121", d(2025, 7, 1), '8-1/2"', "Standby", "Standard", None, "2984.00", "S1 1.1"),
    ("HC-601", d(2025, 6, 30), '17-1/2"', "Operating", "Standard", None, "689.35", "Sch1 before S1 1.2"),
    ("HC-601", d(2025, 7, 1), '17-1/2"', "Operating", "Standard", None, "701.50", "S1 1.2 July"),
    ("HC-601", d(2026, 3, 15), '17-1/2"', "Operating", "Standard", None, "736.40", "last published carries"),
    ("DD-101", d(2025, 12, 31), '8-1/2"', "Operating", "Standard", None, "1847.35", "Sch1"),
    ("DD-101", d(2026, 1, 1), '8-1/2"', "Operating", "Standard", None, "1916.50", "A1"),
    ("DD-101", d(2026, 1, 31), '8-1/2"', "Operating", "Standard", POST, "1916.50", "A3 not yet effective"),
    ("DD-101", d(2026, 2, 1), '8-1/2"', "Operating", "Standard", PRE, "1916.50", "36A pre-issue"),
    ("DD-101", d(2026, 2, 1), '8-1/2"', "Operating", "Standard", POST, "1954.00", "A3 from issue"),
    ("DD-101", d(2026, 3, 31), '8-1/2"', "Operating", "Standard", POST, "1954.00", "no discount yet"),
    ("DD-101", d(2026, 4, 1), '8-1/2"', "Operating", "Standard", PRE, "1839.84", "1916.50 x 0.96"),
    ("DD-101", d(2026, 4, 1), '8-1/2"', "Operating", "Standard", POST, "1875.84", "1954.00 x 0.96"),
    ("DD-101", d(2026, 6, 30), '8-1/2"', "Operating", "Standard", POST, "1875.84", "x 0.96"),
    ("DD-101", d(2026, 7, 1), '8-1/2"', "Operating", "Standard", POST, "1817.22", "1954.00 x 0.93"),
    ("DD-101", d(2026, 7, 1), '8-1/2"', "Standby", "Standard", POST, "1453.78", "x0.80=1563.20; x0.93=1453.776"),
    ("DD-120", d(2026, 1, 31), '12-1/4"', "Operating", "Standard", POST, "398.50", "S1"),
    ("DD-120", d(2026, 2, 1), '12-1/4"', "Operating", "Standard", PRE, "398.50", "36A pre-issue"),
    ("DD-120", d(2026, 2, 1), '12-1/4"', "Operating", "Standard", POST, "416.00", "A3"),
    ("DD-120", d(2026, 4, 1), '12-1/4"', "Operating", "Standard", PRE, "389.76", "S2 406.00 x 0.96"),
    ("DD-120", d(2026, 4, 1), '12-1/4"', "Operating", "Standard", POST, "399.36", "A3 416.00 x 0.96"),
    ("DD-120", d(2026, 7, 1), '8-1/2"', "Operating", "HPHT", POST, "484.42", "393.12 -> 520.88 -> 484.4184"),
    ("MW-301", d(2026, 6, 30), '8-1/2"', "Operating", "Standard", None, "1639.68", "1708.00 x 0.96"),
    ("MW-301", d(2026, 7, 1), '8-1/2"', "Operating", "Standard", None, "1639.59", "1763.00 x 0.93"),
    ("LW-401", d(2026, 3, 31), '8-1/2"', "Operating", "Standard", None, "1969.00", "A1"),
    ("LW-401", d(2026, 4, 1), '8-1/2"', "Operating", "Standard", None, "1890.24", "1969.00 x 0.96"),
    ("MB-701", d(2026, 3, 31), '26"', "Operating", "Standard", None, "18497.50", "Sch1"),
    ("MB-701", d(2026, 4, 1), '26"', "Operating", "Standard", None, "17757.60", "x 0.96"),
    ("MB-701", d(2026, 7, 1), '26"', "Operating", "Standard", None, "17890.41", "19237.00 x 0.93"),
    ("MW-310", d(2025, 1, 31), '12-1/4"', "Operating", "Standard", None, "2245.85", "index 100.00"),
    ("MW-310", d(2025, 2, 1), '12-1/4"', "Operating", "Standard", None, "2261.57", "index 100.70"),
    ("MW-310", d(2026, 12, 31), '26"', "Operating", "HPHT", None, "4543.12", "2607.43 -> 3428.77 -> 4543.12"),
    ("MW-310", d(2025, 6, 4), '12-1/4"', "Standby", "HPHT", None, "1541.44", "2326.70 -> 3082.88 -> 1541.44"),
    ("HC-620", d(2025, 5, 31), '8-1/2"', "Operating", "Standard", None, "556.38", "index 103.10"),
    ("DD-110", d(2025, 5, 1), '17-1/2"', "Standby", "Standard", None, "708.88", "no section on Standby; 708.875"),
    ("MW-320", d(2025, 5, 1), '8-1/2"', "Standby", "Standard", None, "389.82", "389.825 half-even"),
    ("DD-121", d(2025, 8, 1), '12-1/4"', "Operating", "Standard", None, None, "DD-121 only on Standby"),
    ("HC-640", d(2025, 8, 1), '12-1/4"', "Standby", "Standard", None, None, "not chargeable on Standby"),
    ("DD-111", d(2025, 8, 1), '17-1/2"', "Standby", "Standard", None, "3589.45", "100 % on Standby"),
    ("MW-330", d(2024, 12, 31), '26"', "Operating", "Standard", None, None, "before Commencement"),
    ("MW-330", d(2027, 1, 1), '26"', "Operating", "Standard", None, None, "after extended Expiry"),
]


class Boundaries(unittest.TestCase):
    def test_all_boundaries(self):
        self.assertEqual(len(BOUNDARIES), 43)
        for code, day, sec, st, cls, idate, exp, why in BOUNDARIES:
            with self.subTest(code=code, day=day, why=why):
                got = rate(code, day, sec, st, cls, idate)
                self.assertEqual(got, None if exp is None else D(exp))

    def test_index_month_is_service_month(self):
        # Clause 17A: the month in which the service was performed; 31 Mar vs 1 Apr 2025
        self.assertEqual(rate("HC-620", d(2025, 3, 31), '8-1/2"', "Operating", "Standard"), r2(D("539.65") * D("1.015")))
        self.assertEqual(rate("HC-620", d(2025, 4, 1), '8-1/2"', "Operating", "Standard"), D("552.06"))  # 552.06195

    def test_superseded_monthly_rate_lookup(self):
        # S1 1.2: HC-601 in Jan 2027 would still be 736.40 (outside the Term, so not chargeable at all)
        self.assertEqual(base_rate("HC-601", d(2026, 12, 31), None, PricingOptions())[0], D("736.40"))


class RealLines(unittest.TestCase):
    def test_MDS_00001_003_section_factor(self):
        # 1,417.75 x 1.315 = 1,864.34125 -> 1,864.34 (billed 1,864.34)
        self.assertEqual(rate("DD-110", d(2025, 1, 1), '26"', "Operating", "Standard"), D("1864.34"))

    def test_MDS_00214_011_index(self):
        # MW-310 19-Mar-2025 8-1/2": 2,245.85 x 1.015 = 2,279.53775 -> 2,279.54 x 0.945 = 2,154.1653 -> 2,154.17
        self.assertEqual(rate("MW-310", d(2025, 3, 19), '8-1/2"', "Operating", "Standard"), D("2154.17"))
        self.assertEqual(r2(r2(D("2245.85") * D("1.023")) * D("0.945")), D("2171.14"))   # billed: April index

    def test_MDS_01739_041_discount_step(self):
        # 416.00 x 0.945 = 393.12; x 0.93 = 365.6016 -> 365.60 (billed 376.58 = S1 398.50 x 0.945)
        self.assertEqual(rate("DD-120", d(2026, 9, 15), '8-1/2"', "Operating", "Standard", d(2026, 9, 21)), D("365.60"))

    def test_MDS_01519_058_half_even(self):
        # 1,916.50 x 0.93 = 1,782.345 -> 1,782.34 half-even (half-up 1,782.35)
        self.assertEqual(r2(D("1916.50") * D("0.93")), D("1782.34"))
        self.assertEqual(r2(D("1916.50") * D("0.93"), half_up=True), D("1782.35"))

    def test_MDS_00121_043_discount_not_before_start(self):
        # MW-301 in 2025: no rate discount; billed 1,531.29 = 1,646.55 x 0.93
        self.assertEqual(rate("MW-301", d(2025, 3, 3), '12-1/4"', "Operating", "Standard"), D("1646.55"))
        self.assertEqual(r2(D("1646.55") * D("0.93")), D("1531.29"))

    def test_lost_in_hole_MDS_00639_027(self):
        # LH-713 lost 20-Aug-2025, 189 h: 1,443,750 / 3.7500 = 385,000.00; 7 % -> 358,050.00
        self.assertEqual(lih_value("LH-713", d(2025, 8, 20), 189).rate, D("358050.00"))

    def test_lost_in_hole_exchange_month_MDS_00307_006(self):
        # LH-712 21-Apr-2025, 57 h: 4,687,500 x 100 / 374.90 = 1,250,333.4222 -> .42; 2 % -> 1,225,326.7516 -> .75
        self.assertEqual(lih_value("LH-712", d(2025, 4, 21), 57).rate, D("1225326.75"))
        # billed 1,225,653.68 = the September 2025 rate 374.80
        self.assertEqual(r2(r2(D("4687500") * 100 / D("374.80")) * D("0.98")), D("1225653.68"))

    def test_appendix_f_and_depreciation_cap(self):
        self.assertEqual(lih_value("LH-713", d(2025, 8, 22), 412, PricingOptions(lih_from_sar=False)).rate,
                         D("323400.00"))                                   # 412 h -> 16 %
        self.assertEqual(lih_value("LH-713", d(2025, 8, 22), 412).rate, D("323400.00"))   # 375.00 halalas
        self.assertEqual(lih_value("LH-712", d(2025, 8, 22), 1300).rate, D("625000.00"))  # capped at 50 %
        self.assertEqual(lih_value("LH-712", d(2025, 8, 22), 24).rate, D("1250000.00"))   # 24 h: no complete 25


class InvoiceArithmetic(unittest.TestCase):
    def test_appendix_b_totals_and_discount(self):
        net = D("2955.76") + D("2975.75") + D("9162.00") + D("4070.50") + D("6498.25")
        self.assertEqual((net, vat(net), net + vat(net)), (D("25662.26"), D("3849.34"), D("29511.60")))
        self.assertEqual(invoice_discount(D("312400.00")), D("-2496.00"))

    def test_discount_threshold_edges(self):
        self.assertEqual(invoice_discount(D("250000.00")), D(0))              # "exceeds"
        self.assertEqual(invoice_discount(D("250000.01")), D("0.00"))        # 0.0004 -> 0.00
        self.assertEqual(invoice_discount(D("250000.13")), D("-0.01"))       # 0.0052 -> 0.01
        self.assertEqual(invoice_discount(D("1307552.40")), D("-42302.10"))  # MDS-00072: 42,302.096

    def test_vat_half_even(self):
        self.assertEqual(vat(D("99820.36")), D("14973.05"))     # MDS-00001
        self.assertEqual(vat(D("0.10")), D("0.02"))             # 0.015 -> 0.02 (even)
        self.assertEqual(vat(D("0.30")), D("0.04"))             # 0.045 -> 0.04 (even)

    def test_cents_are_integers(self):
        self.assertEqual(to_cents(D("265123.89")), 26512389)
        with self.assertRaises(ValueError):
            to_cents(D("1.005"))


class PerformanceFootage(unittest.TestCase):
    def test_band_split_and_boundary(self):
        self.assertEqual(pd210_segments(1450, 1560), [(1450, 1500, D("42.35")), (1500, 1560, D("58.15"))])
        self.assertEqual(pd210_segments(1500, 1560), [(1500, 1560, D("58.15"))])
        self.assertEqual(pd210_segments(2930, 3085), [(2930, 3000, D("58.15")), (3000, 3085, D("76.45"))])  # App. B
        self.assertEqual(pd210_segments(4400, 4700), [(4400, 4500, D("76.45")), (4500, 4700, D("98.70"))])

    def test_no_class_factor_on_pd210(self):
        amt, r, _ = pd210_amount(D("58.15"), 70, 0, PricingOptions(), "HPHT")
        self.assertEqual((amt, r), (D("4070.50"), D("58.15")))       # Appendix B, HPHT well
        amt, r, _ = pd210_amount(D("58.15"), 70, 0, PricingOptions(no_class_factor_on_pd210=False), "HPHT")
        self.assertEqual(r, D("77.05"))                              # 77.04875 -> 77.05 (the rejected reading)

    def test_volume_bands_synthetic(self):
        # Schedule 2 Part 2 never engages in the data (max 3,355 m per well-year); synthetic crossing at 40,000
        self.assertEqual(pd210_volume_parts(0, 100), [(100, D("1.00"))])
        self.assertEqual(pd210_volume_parts(39950, 100), [(50, D("1.00")), (50, D("0.96"))])
        self.assertEqual(pd210_volume_parts(119990, 30), [(10, D("0.96")), (20, D("0.92"))])
        amt, _, _ = pd210_amount(D("76.45"), 100, 39950, PricingOptions(), "Standard")
        self.assertEqual(amt, D("3822.50") + r2(D("50") * r2(D("76.45") * D("0.96"))))   # 73.392 -> 73.39


class SyntheticReadings(unittest.TestCase):
    def test_discount_fold_on_standby_is_moot(self):
        # S2 2.2 / A2 2.3 put the discount "as the last factor ... before the rounding". Folding it into the
        # standby step could only matter if base x standby % left a fraction of a cent. For every discounted
        # code with a standby percentage and every base in force from 2026-04-01 the product is exact, so the
        # two readings give identical rates for any Standby day in this contract.
        from drilling_audit import contract as C
        bases = {"DD-101": ["1916.50", "1954.00"], "MW-301": ["1708.00", "1763.00"], "LW-401": ["1969.00"]}
        for code, rs in bases.items():
            for b in rs:
                p = D(b) * C.STANDBY_PCT[code]
                self.assertEqual(p, r2(p), (code, b))
        for day in (d(2026, 4, 1), d(2026, 7, 1)):
            for code in bases:
                self.assertEqual(rate(code, day, '8-1/2"', "Standby", "Standard", POST),
                                 rate(code, day, '8-1/2"', "Standby", "Standard", POST, discount_fold="standby"))

    def test_discount_fold_into_operating_step_differs(self):
        # DD-120 8-1/2" Extended Reach, 2026-07-01, after issue:
        # separate: 416.00 x 0.945 = 393.12; x 1.175 = 461.916 -> 461.92; x 0.93 = 429.5856 -> 429.59
        # folded:   393.12 x 1.175 x 0.93 = 429.58188 -> 429.58
        self.assertEqual(rate("DD-120", d(2026, 7, 1), '8-1/2"', "Operating", "Extended Reach", POST), D("429.59"))
        self.assertEqual(rate("DD-120", d(2026, 7, 1), '8-1/2"', "Operating", "Extended Reach", POST,
                              discount_fold="any"), D("429.58"))

    def test_36A_generic_before_issue(self):
        # Any invoice dated before 17 Aug 2026 is priced without A3, whatever the service month
        self.assertEqual(base_rate("DD-120", d(2026, 9, 1), d(2026, 8, 16), PricingOptions())[0], D("434.00"))
        self.assertEqual(base_rate("DD-120", d(2026, 9, 1), d(2026, 8, 17), PricingOptions())[0], D("416.00"))
        self.assertEqual(base_rate("DD-120", d(2026, 9, 1), d(2026, 8, 16),
                                   PricingOptions(retro_only_from_issue=False))[0], D("416.00"))
        self.assertEqual(base_rate("DD-120", d(2026, 9, 1), d(2026, 8, 17),
                                   PricingOptions(later_issued_governs=False))[0], D("434.00"))


if __name__ == "__main__":
    unittest.main()
