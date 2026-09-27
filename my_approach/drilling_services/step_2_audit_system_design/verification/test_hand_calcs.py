"""Hand calculations on real lines and reports, used to validate the verification code itself.

Run: python -m unittest test_hand_calcs -v
"""
import datetime as dt
import unittest

from common import D, RECORDS_DIR, parse_report, r2
from evidence import EvidenceOptions, supported
from pricing import Reading, build_rate, lih_value, pd210_split

d = dt.date


class HandCalcs(unittest.TestCase):
    def test_section_factor_line_MDS_00001_003(self):
        # DD-110, 26", 01-Jan-2025, Standard: 1,417.75 x 1.315 = 1,864.34125 -> 1,864.34 (billed 1864.34)
        self.assertEqual(r2(D("1417.75") * D("1.315")), D("1864.34"))
        self.assertEqual(build_rate("DD-110", d(2025, 1, 1), '26"', "Operating", "Standard")[0], D("1864.34"))

    def test_half_even_standby_MW_320(self):
        # 779.65 x 0.50 = 389.825 -> half-even 389.82 (half-up would give 389.83)
        self.assertEqual(build_rate("MW-320", d(2025, 2, 2), '8-1/2"', "Standby", "Standard")[0], D("389.82"))

    def test_index_MDS_00214_011(self):
        # MW-310, 8-1/2", 19-Mar-2025: 2,245.85 x 101.50/100 = 2,279.53775 -> 2,279.54; x 0.945 = 2,154.1653 -> 2,154.17
        # billed 2,171.14 = April index 102.30 applied to a March day
        self.assertEqual(build_rate("MW-310", d(2025, 3, 19), '8-1/2"', "Operating", "Standard")[0], D("2154.17"))
        self.assertEqual(r2(r2(D("2245.85") * D("1.023")) * D("0.945")), D("2171.14"))

    def test_discount_step_MDS_01739_041(self):
        # DD-120, 8-1/2", 15-Sep-2026, invoice 21-Sep-2026 (after A3): 416.00 x 0.945 = 393.12; x 0.93 = 365.6016 -> 365.60
        self.assertEqual(build_rate("DD-120", d(2026, 9, 15), '8-1/2"', "Operating", "Standard", d(2026, 9, 21))[0], D("365.60"))

    def test_a3_pre_issue(self):
        # 36A: DD-101 for 10-Feb-2026 invoiced 01-Mar-2026 stays at A1 1,916.50; invoiced 18-Aug-2026 is A3 1,954.00
        self.assertEqual(build_rate("DD-101", d(2026, 2, 10), '8-1/2"', "Operating", "Standard", d(2026, 3, 1))[0], D("1916.50"))
        self.assertEqual(build_rate("DD-101", d(2026, 2, 10), '8-1/2"', "Operating", "Standard", d(2026, 8, 18))[0], D("1954.00"))

    def test_lih_MDS_00639_027(self):
        # LH-713, lost 20-Aug-2025, 189 h on Part E: SAR 1,443,750.00 / 375.00 halalas = 385,000.00;
        # 189 // 25 = 7 % -> 358,050.00. Billed 385,000.00 (no depreciation).
        self.assertEqual(lih_value("LH-713", d(2025, 8, 20), 189)[0], D("358050.00"))

    def test_lih_sar_month_MDS_00307_006(self):
        # LH-712, 21-Apr-2025, 57 h: 4,687,500 x 100 / 374.90 = 1,250,333.4222 -> 1,250,333.42; 2 % -> 1,225,326.7516 -> 1,225,326.75
        self.assertEqual(lih_value("LH-712", d(2025, 4, 21), 57)[0], D("1225326.75"))
        self.assertEqual(lih_value("LH-712", d(2025, 4, 21), 57, Reading(lih_from_sar=False))[0], D("1225000.00"))

    def test_pd210_split(self):
        # Clause 23: 1,450 -> 1,560 m splits at 1,500 (boundary belongs to the shallower band)
        self.assertEqual(pd210_split(1450, 1560), [(1450, 1500, D("42.35")), (1500, 1560, D("58.15"))])
        self.assertEqual(pd210_split(1500, 1560), [(1500, 1560, D("58.15"))])

    def test_invoice_discount_MDS_00072(self):
        # services 1,307,552.40: (1,307,552.40 - 250,000.00) x 4 % = 42,302.096 -> -42,302.10 (billed: none)
        self.assertEqual(-r2((D("1307552.40") - D("250000.00")) * D("0.04")), D("-42302.10"))

    def test_vat_MDS_00001(self):
        # net 99,820.36 x 15 % = 14,973.054 -> 14,973.05; total 114,793.41 (as billed)
        self.assertEqual(r2(D("99820.36") * D("0.15")), D("14973.05"))

    def test_report_parse_and_support(self):
        rep = parse_report(RECORDS_DIR / "DDR_NGP-BD-011_20260225.txt")
        self.assertEqual(rep.crew, {"DD-101": 2, "DD-102": 1, "MW-301": 2})
        self.assertEqual(rep.tool_codes, {"MW-310", "HC-620", "DD-110", "MW-330"})
        self.assertEqual((rep.dstart, rep.dend, rep.circ, rep.metres), (0, 275, 15, 275))
        sup = supported(rep, {"NGP-BD-011": (d(2026, 2, 25), d(2026, 4, 10))}, set(),
                        EvidenceOptions(chargeable_hour_minus_one=True))
        self.assertEqual(sup["DD-130"], 1)          # gyro surveys: 1, Part C present
        self.assertEqual(sup["MB-701"], 1)          # first day on the well
        self.assertNotIn("DD-120", sup)             # no rotary steerable in hole
        self.assertNotIn("PD-210", sup)             # 26" section is not performance-drilled

    def test_chargeable_hour_DDR_BD_011_20260308(self):
        # report circulating hours 16 -> invoice DD-120 15 (Clause 21A); minimum 6 not engaged
        rep = parse_report(RECORDS_DIR / "DDR_NGP-BD-011_20260308.txt")
        self.assertEqual(rep.circ, 16)
        sup = supported(rep, {"NGP-BD-011": (d(2026, 2, 25), d(2026, 4, 10))}, set(),
                        EvidenceOptions(chargeable_hour_minus_one=True))
        self.assertEqual(sup["DD-120"], 15)


if __name__ == "__main__":
    unittest.main()
