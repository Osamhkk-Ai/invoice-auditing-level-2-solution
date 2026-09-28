"""Every contract constant in ``contract.py`` re-read from the validated Step 1 transcription.

The transcription was checked page by page against the scan (Step 1 validation report). These tests
parse its tables independently of the code and compare, so a mistyped constant fails here.
"""
import datetime as dt
import re
import unittest
from decimal import Decimal

from _support import TRANSCRIPTION
from drilling_audit import contract as C

with open(TRANSCRIPTION, encoding="utf-8") as f:
    TEXT = f.read()


def section(title: str, end: str = "\n# ") -> str:
    i = TEXT.index(title)
    j = TEXT.find(end, i + len(title))
    return TEXT[i:j if j > 0 else None]


def rows(block: str) -> list[list[str]]:
    out = []
    for line in block.splitlines():
        if line.startswith("|") and not re.match(r"^\|[-| ]+\|$", line):
            out.append([c.strip() for c in line.strip().strip("|").split("|")])
    return out


def num(s: str) -> Decimal:
    return Decimal(s.replace(",", "").replace("%", ""))


class Schedules(unittest.TestCase):
    def test_schedule_1(self):
        got = {}
        for r in rows(section("# SCHEDULE 1")):
            if re.fullmatch(r"[A-Z]{2}-\d{3}", r[0]):
                got[r[0]] = (r[1], r[2], None if r[3] in ("Schedule 2", "Clause 31") else num(r[3]))
        self.assertEqual(got, C.SCHEDULE_1)

    def test_schedule_2_bands(self):
        rates = [num(r[2]) for r in rows(section("# SCHEDULE 2 —", "**Part 2")) if re.fullmatch(r"Band \d", r[0])]
        self.assertEqual(rates, [b[2] for b in C.PD210_BANDS])
        self.assertEqual([b[1] for b in C.PD210_BANDS], [1500, 3000, 4500, None])
        pct = [num(r[2]) / 100 for r in rows(section("**Part 2 — Metres drilled")) if re.fullmatch(r"Band \d", r[0])]
        self.assertEqual(pct, [b[2] for b in C.PD210_VOLUME_BANDS])
        self.assertIn("1 m to 40,000 m", TEXT)
        self.assertIn("40,001 m to 120,000 m", TEXT)

    def test_schedule_2c_index(self):
        got = {}
        for r in rows(section("# SCHEDULE 2C")):
            if re.fullmatch(r"\d{4}-\d{2}", r[0]):
                got[r[0]], got[r[2]] = num(r[1]), num(r[3])
        self.assertEqual(got, C.RIG_SERVICES_INDEX)
        codes = {r[0] for r in rows(section("# SCHEDULE 2C")) if r[0].startswith(("MW", "HC"))}
        self.assertEqual(codes, set(C.INDEXED))

    def test_schedule_2d_and_6(self):
        block = section("# SCHEDULE 2D")
        sar = {r[0]: num(r[2]) for r in rows(block) if r[0].startswith("LH-")}
        self.assertEqual(sar, C.LIH_SAR)
        hal = {}
        for r in rows(block):
            if re.fullmatch(r"\d{4}-\d{2}", r[0]):
                hal[r[0]], hal[r[2]] = num(r[1]), num(r[3])
        self.assertEqual(hal, C.HALALAS_PER_USD)
        usd = {r[0]: num(r[2]) for r in rows(section("# SCHEDULE 6")) if r[0].startswith("LH-")}
        self.assertEqual(usd, C.LIH_USD_SCHEDULE_6)

    def test_schedule_3(self):
        s3 = section("# SCHEDULE 3", "# SCHEDULE 4")
        sec = {r[0]: num(r[1]) for r in rows(s3.split("**Part 2")[0]) if r[0] != "Hole section"}
        self.assertEqual(sec, C.SECTION_FACTOR)
        cls = {r[0]: num(r[1]) for r in rows(s3.split("**Part 2")[1].split("**Part 3")[0]) if r[0] != "Well class"}
        self.assertEqual(cls, C.CLASS_FACTOR)
        rated = re.search(r"Section-rated services: ([^.]+)\.", s3).group(1)
        self.assertEqual({x.strip() for x in rated.split(",")}, set(C.SECTION_RATED))
        rated = re.search(r"Class-rated services: ([^.]+)\.", s3).group(1)
        self.assertEqual({x.strip() for x in rated.split(",")}, set(C.CLASS_RATED))
        pt3 = s3.split("**Part 3")[1].split("**Part 4")[0]
        standby = {r[0]: None if r[2] == "Not chargeable" else num(r[2]) / 100 for r in rows(pt3) if r[0] != "Code"}
        self.assertEqual(standby, C.STANDBY_PCT)
        pt5 = s3.split("**Part 5")[1].split("**Part 6")[0]
        self.assertEqual({r[0]: int(r[2]) for r in rows(pt5) if r[0] != "Code"}, C.DAILY_LIMIT)
        self.assertIn("DD-140, LW-430, MB-701, MB-702 (Clause 27)", s3)
        self.assertIn("DD-120: not less than 6 hours", s3)
        self.assertEqual(C.DD120_MINIMUM_HOURS, 6)

    def test_schedule_5_parts(self):
        s5 = section("# SCHEDULE 5")
        req = {r[0]: r[2][-1] for r in rows(s5) if re.fullmatch(r"[A-Z]{2}-\d{3}", r[0])}
        self.assertEqual(req, C.PART_REQUIRED)

    def test_appendix_g(self):
        g = {r[0]: r[2] for r in rows(section("# APPENDIX G")) if r[0] != "Code"}
        words = {**{w: c for w, c in C.TOOL_WORDS.items()}, **C.CREW_WORDS}
        for word, code in words.items():
            self.assertEqual(g[code], word, code)
        for word, code in C.LOST_WORDS.items():
            self.assertEqual(g[code], word, code)
        self.assertEqual(len(g), len(C.TOOL_WORDS) + len(C.CREW_WORDS) + len(C.LOST_WORDS))


class Instruments(unittest.TestCase):
    def test_schedule_of_variations(self):
        sov = {r[0]: r for r in rows(section("# SCHEDULE OF VARIATIONS")) if r[0] != "Instrument"}
        names = {"Supplement No. 1": "S1", "Amendment No. 1": "A1", "Supplement No. 2": "S2",
                 "Amendment No. 2": "A2", "Amendment No. 3": "A3"}
        for full, short in names.items():
            ins = C.INSTRUMENT[short]
            self.assertEqual(sov[full][1], ins.issued.isoformat(), short)
            self.assertEqual(sov[full][2], ins.effective.isoformat(), short)
        self.assertEqual([i.name for i in C.INSTRUMENTS], ["S1", "A1", "S2", "A2", "A3"])   # order issued
        self.assertEqual([i.name for i in C.INSTRUMENTS if i.retroactive], ["A3"])

    def test_substituted_rates(self):
        for short, title in (("S1", "# SUPPLEMENT NO. 1"), ("A1", "# AMENDMENT NO. 1"), ("A2", "# AMENDMENT NO. 2"),
                             ("A3", "# AMENDMENT NO. 3")):
            block = section(title, "Save as stated above")
            got = {r[0]: (num(r[4]), dt.date.fromisoformat(r[5])) for r in rows(block) if len(r) == 6 and re.fullmatch(r"[A-Z]{2}-\d{3}", r[0])}
            ins = C.INSTRUMENT[short]
            self.assertEqual({k: v[0] for k, v in got.items()}, ins.rates, short)
            self.assertTrue(all(v[1] == ins.effective for v in got.values()), short)

    def test_monthly_republications(self):
        months = {"July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
                  "April": 4, "May": 5, "June": 6}
        for short, title, code in (("S1", "**1.2 Monthly", "HC-601"), ("S2", "**2.1 Monthly", "DD-120")):
            block = section(title, "\n**2.2" if short == "S2" else "Save as stated")
            got = {}
            for r in rows(block):
                m = re.fullmatch(r"(\w+) (\d{4})", r[0])
                if m:
                    got[f"{m.group(2)}-{months[m.group(1)]:02d}"] = num(r[1])
            self.assertEqual(got, C.INSTRUMENT[short].monthly[code], short)

    def test_discounts_and_term(self):
        s2, a2 = section("# SUPPLEMENT NO. 2"), section("# AMENDMENT NO. 2")
        self.assertIn("A discount of 4 per cent", s2)
        self.assertIn("A discount of 7 per cent", a2)
        for block, short in ((s2, "S2"), (a2, "A2")):
            codes = {r[0] for r in rows(block.split("Discount on principal services")[1]) if r[0] != "Code"}
            self.assertEqual(codes, set(C.INSTRUMENT[short].discount_codes))
            self.assertIn("as the last factor in the build-up", block)
        self.assertIn("extended to 30 June 2026", section("# AMENDMENT NO. 1"))
        self.assertIn("extended to 31 December 2026", a2)
        self.assertEqual(C.TERM_END, dt.date(2026, 12, 31))


class ControllingWords(unittest.TestCase):
    """The clause wording each disputed reading depends on (decision log)."""

    def test_36A_on_or_after_and_A3_after(self):
        self.assertIn("single adjustment on the first invoice submitted on or after the date of issue, and on no other",
                      TEXT)
        self.assertIn("single adjustment on the first invoice submitted after the date of issue (Clause 36A)", TEXT)

    def test_invoice_total_and_vat(self):
        self.assertIn("The total of an invoice is its net amount plus Value Added Tax.", TEXT)
        self.assertIn("Value Added Tax is charged at 15 per cent of the net amount of the invoice", TEXT)
        self.assertIn("including the discount charge under Clause 38", TEXT)

    def test_part_ix_rules(self):
        self.assertIn("is not applied on a day the rig is on Standby", TEXT)                  # 17B
        self.assertIn("not applied to item PD-210", TEXT)                                      # 17B
        self.assertIn("the invoice charges one fewer", TEXT)                                   # 21A
        self.assertIn("by more than 1 per cent are payable as charged", TEXT)                  # 25A
        self.assertIn("for the month in which the tool was lost, rounded half to even", TEXT)  # 31A
        self.assertIn("a result exactly half way between two cents is rounded to the even cent", TEXT)  # 17

    def test_signature_and_condition_of_payment(self):
        self.assertIn("It is signed by the Company Representative and the Contractor's lead directional driller.", TEXT)
        self.assertIn("A charge for a service Schedule 5 lists is not payable until the document Schedule 5 names "
                      "has been delivered", TEXT)

    def test_pd210_call_off(self):
        self.assertIn("Item PD-210 is charged only on the performance-drilled sections nominated in the call-off.", TEXT)
        self.assertIn("1, performance-drilled sections", TEXT)           # Schedule 4, PD-201


if __name__ == "__main__":
    unittest.main()
