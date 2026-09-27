"""The hand-typed constants in contract.py agree with the Step 1 transcription of the
scanned contract (which was compared page by page against the scans in Step 2).

These tests parse the transcription tables themselves, so a typo in contract.py and
the same typo in a test cannot agree by construction.
"""
import datetime as dt
import os
import re
import unittest

from _support import D, TRANSCRIPTION

from civilwork_audit import contract as C


def page(n: int) -> str:
    with open(os.path.join(TRANSCRIPTION, f"page_{n:03d}.md"), encoding="utf-8") as f:
        return f.read()


def rows(text: str) -> list[list[str]]:
    out = []
    for ln in text.splitlines():
        if ln.startswith("|") and not re.match(r"^\|[-:| ]+\|$", ln):
            out.append([c.strip() for c in ln.strip().strip("|").split("|")])
    return out


def num(s: str):
    return D(s.replace(",", "").rstrip("%"))


def section(text: str, start: str, end: str | None = None) -> str:
    i = text.index(start)
    j = text.index(end, i) if end else len(text)
    return text[i:j]


MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July",
                                       "August", "September", "October", "November", "December"], 1)}


class ScheduleTables(unittest.TestCase):
    def test_schedule_1_units_and_rates(self):
        found = {}
        for n in (17, 18, 19):
            for r in rows(page(n)):
                if re.fullmatch(r"[A-E]\.\d\d\.\d{3}", r[0]) and len(r) == 5:
                    found[r[0]] = (r[2], num(r[4]))
        self.assertEqual(len(found), 60)
        self.assertEqual(found, C.SCHEDULE_1)

    def test_zone_factors_and_series(self):
        text = page(20)
        found = {r[0].split()[0]: num(r[2]) for r in rows(text) if re.match(r"Z\d ", r[0])}
        self.assertEqual(found, C.ZONE_FACTORS)
        self.assertIn("apply to every item in Series A, B, C and D", text)
        self.assertIn("do not apply to Series E", text)

    def test_index_and_exchange_tables(self):
        for n, table in ((21, C.SITE_MATERIALS_INDEX), (22, C.HALALAS_PER_USD)):
            found = {}
            for r in rows(page(n)):
                if len(r) == 4 and re.fullmatch(r"\d{4}-\d\d", r[0]):
                    found[r[0]], found[r[2]] = num(r[1]), num(r[3])
            self.assertEqual(found, table, f"page {n}")
        self.assertEqual({r[0] for r in rows(page(21)) if re.fullmatch(r"[A-E]\.\d\d\.\d{3}", r[0])}, C.INDEXED_ITEMS)
        self.assertEqual({r[0] for r in rows(page(22)) if re.fullmatch(r"[A-E]\.\d\d\.\d{3}", r[0])}, C.USD_ITEMS)

    def test_ground_factors_and_items(self):
        text = page(23)
        found = {r[0].split()[0]: num(r[2]) for r in rows(text) if re.match(r"G\d ", r[0])}
        self.assertEqual(found, C.GROUND_FACTORS)
        items = set(re.findall(r"[A-E]\.\d\d\.\d{3}", section(text, "Items to which Schedule 3 applies")))
        self.assertEqual(items, C.GROUND_ITEMS)

    def test_uplifts(self):
        text = page(24)
        night = section(text, "Part 1", "Part 2")
        rest = section(text, "Part 2", "Part 3")
        self.assertEqual({r[0]: int(num(r[2])) for r in rows(night) if r[0][:1] in "ABCDE" and "." in r[0]}, C.NIGHT_UPLIFT)
        self.assertEqual({r[0]: int(num(r[2])) for r in rows(rest) if r[0][:1] in "ABCDE" and "." in r[0]}, C.REST_DAY_UPLIFT)

    def test_bands(self):
        text = section(page(24), "Part 3") + section(page(25), "|", "Part 4")
        found: dict[str, list] = {}
        for r in rows(text):
            if len(r) == 5 and r[4].endswith("%"):
                band = r[2]
                upper = None if band.startswith("above") else int(num(band.split(" to ")[1]))
                found.setdefault(r[0], []).append((upper, int(num(r[4]))))
        self.assertEqual(found, C.BANDS)

    def test_daily_limits_exclusion_and_surveyed(self):
        text = page(26)
        limits = section(text, "|", "Part 5")
        self.assertEqual({r[0]: int(num(r[2])) for r in rows(limits) if "." in r[0]}, C.DAILY_LIMITS)
        excl = [r for r in rows(section(text, "Part 5", "Part 6")) if "." in r[0]]
        self.assertEqual([(r[0], r[1]) for r in excl], C.MUTUALLY_EXCLUSIVE)
        self.assertEqual(excl[0][2], "2 days")
        surveyed = {r[0] for r in rows(section(text, "Part 6")) if "." in r[0]}
        self.assertEqual(surveyed, C.SURVEYED_ITEMS)

    def test_schedule_5_record_series(self):
        found = {r[0]: r[3] for r in rows(page(27)) if "." in r[0]}
        self.assertEqual(found, C.RECORD_SERIES)


class Instruments(unittest.TestCase):
    def test_issue_and_effective_dates_from_schedule_of_variations(self):
        names = {"Supplement No. 1": "S1", "Amendment No. 1": "A1", "Supplement No. 2": "S2",
                 "Amendment No. 2": "A2", "Amendment No. 3": "A3"}
        found = [(names[r[0]], dt.date.fromisoformat(r[1]), dt.date.fromisoformat(r[2]))
                 for r in rows(page(38)) if r[0] in names]
        self.assertEqual(found, [(i.name, i.issued, i.effective) for i in C.INSTRUMENTS])

    def test_substituted_rates(self):
        for ins in C.INSTRUMENTS:
            text = page(ins.page)
            fixed = {(r[0], num(r[4]), dt.date.fromisoformat(r[5])) for r in rows(text)
                     if len(r) == 6 and "." in r[0]}
            ours = {(rc.item, rc.rate, rc.effective) for rc in ins.rates if rc.rate is not None}
            self.assertEqual(fixed, ours, ins.name)

    def test_monthly_rates(self):
        for ins in C.INSTRUMENTS:
            monthly = [rc for rc in ins.rates if rc.monthly]
            text = page(ins.page)
            found = {}
            for r in rows(text):
                m = re.fullmatch(r"(\w+) (\d{4})", r[0])
                if m and m.group(1) in MONTHS:
                    found[f"{m.group(2)}-{MONTHS[m.group(1)]:02d}"] = num(r[1])
            self.assertEqual(found, monthly[0].monthly if monthly else {}, ins.name)

    def test_discounts_and_completion_dates(self):
        for ins in C.INSTRUMENTS:
            text = page(ins.page)
            m = re.search(r"A discount of (\d+) per cent", text)
            self.assertEqual(D(m.group(1)) / 100 if m else None, ins.discount, ins.name)
            if m:
                items = {r[0] for r in rows(section(text, "Discount on principal items")) if "." in r[0]}
                self.assertEqual(items, ins.discount_items, ins.name)
            m = re.search(r"Date for Completion stated in the Form of Subcontract is extended to (\d+) (\w+) (\d{4})", text)
            self.assertEqual(dt.date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1))) if m else None,
                             ins.completion, ins.name)
        self.assertEqual(C.COMPLETION, C.INSTRUMENTS[-2].completion)   # A2, the last extension


class ConditionsText(unittest.TestCase):
    """Words the rules turn on, quoted from the transcription."""

    def test_clause_words(self):
        p6, p8, p13, p32 = page(6), page(8), page(13), page(32)
        self.assertIn("a half halala being rounded upward", p6)                     # Cl 28
        self.assertIn("taken in order of application number and then line number", p6)  # Cl 30
        self.assertIn("within 21 days of the end of the period", p8)                # Cl 41
        self.assertIn("returned unpaid", p8)                                        # Cl 43
        self.assertIn("is rounded down to the nearest halala", p8)                  # Cl 45
        self.assertIn("within two days of the measurement of item A.14.010", p13)   # P19
        self.assertIn("for work executed after 27 September 2025", p32)             # 27A
        self.assertIn("zone factor exceeding 1.1", p32)                             # 27A
        self.assertIn("submitted on or after the date of issue", p32)               # 31A
        self.assertIn("first Application for Payment submitted after the date of issue", page(43))  # A3
        self.assertIn("more than 2 per cent", p32)                                  # 33A
        self.assertIn("the quantity measured is one hour fewer", p32)              # 6A
        self.assertIn("not fewer than five days", page(33))                         # 47A

    def test_agreement_facts(self):
        p1 = page(1)
        self.assertIn(f"Contract reference: {C.CONTRACT_REF}", p1)
        self.assertIn(C.SUBCONTRACTOR.upper(), p1)
        self.assertIn("05 January 2025", p1)
        self.assertIn("Friday and Saturday", p1)
        self.assertIn("work actually executed", p1)


if __name__ == "__main__":
    unittest.main()
