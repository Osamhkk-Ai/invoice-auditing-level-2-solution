"""An independent re-pricer, written from the contract text, for three families of lines:

* personnel (DD-101, DD-102, MW-301, LW-401, PD-201): 13,000+ lines, instruments, standby %, rate discounts
* indexed rentals (MW-310, HC-620): Rig Services Index, section and class factors, standby %
* lost in hole (LH-711..714): SAR at the month's exchange rate, depreciation

and for the Clause 36A difference and every invoice's billed arithmetic. It shares no code with the
engine: its own tables (typed from the contract pages), its own report reader, and integer-cent
arithmetic with its own half-even division. Every line of those codes must agree with production.
"""
import csv
import datetime as dt
import os
import re
import unittest
from collections import defaultdict

from _support import REPO, audit

DATA = os.path.join(REPO, "invoice-auditing-level-2", "drilling_services")


def div_half_even(num: int, den: int) -> int:
    q, r = divmod(num, den)
    if 2 * r > den or (2 * r == den and q % 2 == 1):
        q += 1
    return q


def step(cents: int, factor: str) -> int:
    """cents x decimal factor, rounded half-even to the cent (Clause 17), with integers only."""
    whole, _, frac = factor.partition(".")
    den = 10 ** len(frac)
    return div_half_even(cents * int(whole + frac), den)


def cents(text: str) -> int:
    sign = -1 if text.startswith("-") else 1
    a, b = text.lstrip("-").split(".")
    return sign * (int(a) * 100 + int(b))


# Typed from pp.15-21, 38-42.
def personnel_base(code, day, invoice_date):
    a3 = invoice_date >= dt.date(2026, 8, 17)          # Clause 36A
    if code == "DD-101":
        if day >= dt.date(2026, 2, 1) and a3:
            return 195400
        return 191650 if day >= dt.date(2026, 1, 1) else 184735
    if code == "MW-301":
        return 176300 if day >= dt.date(2026, 7, 1) else 170800 if day >= dt.date(2026, 1, 1) else 164655
    if code == "LW-401":
        return 196900 if day >= dt.date(2026, 1, 1) else 189845
    return {"DD-102": 94860, "PD-201": 209485}[code]


STANDBY = {"DD-101": "0.80", "DD-102": "1.00", "MW-301": "0.80", "LW-401": "0.80", "PD-201": "0.80",
           "MW-310": "0.50", "HC-620": "0.50"}
DISCOUNTED = {"DD-101", "MW-301", "LW-401"}
CREW = {"directional hands": "DD-101", "night man": "DD-102", "MWD engineers": "MW-301",
        "logging engineers": "LW-401", "performance engineer": "PD-201"}
INDEX = "100.00 100.70 101.50 102.30 103.10 103.60 104.80 105.40 104.90 106.20 107.10 108.00 " \
        "109.30 110.00 110.60 111.40 110.90 112.20 113.00 112.60 113.90 114.70 115.30 116.10".split()
HALALAS = "375.00 375.10 375.00 374.90 375.20 375.30 375.10 375.00 374.80 375.40 375.60 375.50 " \
          "376.00 375.80 375.90 376.20 376.40 376.10 375.70 376.30 376.60 376.80 377.00 376.50".split()
SECTION = {'26"': "1.315", '17-1/2"': "1.145", '12-1/4"': "1.00", '8-1/2"': "0.945", '6"': "0.885"}
CLASS = {"Standard": "1.00", "Extended Reach": "1.175", "HPHT": "1.325"}
LIH = {"LH-711": ("mud motor", 54375000), "LH-712": ("rotary steerable", 468750000),
       "LH-713": ("MWD collar", 144375000), "LH-714": ("gamma tool", 195000000)}


def month_index(day, table):
    return table[(day.year - 2025) * 12 + day.month - 1]


def discount(code, day):
    if code not in DISCOUNTED and code != "DD-120":
        return None
    return "0.93" if day >= dt.date(2026, 7, 1) else "0.96" if day >= dt.date(2026, 4, 1) else None


def read_report(well, day):
    path = os.path.join(DATA, "records", f"DDR_{well}_{day:%Y%m%d}.txt")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        text = f.read()
    field = lambda k: (re.search(rf"^{re.escape(k)}: ?(.*)$", text, re.M) or [None, None])[1]
    crew = {}
    for m in re.finditer(r"(\d+) ([A-Za-z ]+?)(?:,|$)", field("Crew on tour").strip()):
        crew[CREW[m.group(2).strip()]] = int(m.group(1))
    signed = all(not re.fullmatch(r"_*", (field(k) or "").strip())
                 for k in ("Signed (Company Representative)", "Signed (lead directional driller)"))
    return {"status": field("Status").strip(), "section": field("Hole section").strip(), "crew": crew,
            "tools": [t.strip() for t in field("In the hole").split(",")], "signed": signed,
            "lost": (field("Lost in hole tool") or "").strip(),
            "lost_hours": int(field("Circulating hours accumulated on the well") or 0)}


def load():
    with open(os.path.join(DATA, "invoices", "invoices.csv"), encoding="utf-8") as f:
        inv = {r["invoice_no"]: r for r in csv.DictReader(f)}
    with open(os.path.join(DATA, "invoices", "invoice_lines.csv"), encoding="utf-8") as f:
        lines = list(csv.DictReader(f))
    p = lambda s: dt.datetime.strptime(s, "%d-%b-%Y").date()
    for r in inv.values():
        r["_d"], r["_ps"], r["_pe"] = p(r["invoice_date"]), p(r["period_start"]), p(r["period_end"])
    for ln in lines:
        ln["_d"] = p(ln["service_date"]) if ln["service_date"] else None
    return inv, lines, p


def reprice_independently():
    inv, lines, _ = load()
    codes = set(STANDBY) | set(LIH)
    order = sorted((ln for ln in lines if ln["service_code"] in codes),
                   key=lambda ln: (inv[ln["invoice_no"]]["_d"], ln["invoice_no"], int(ln["line_no"])))
    used = defaultdict(int)
    out = {}
    cache = {}
    for ln in order:
        I, code, day = inv[ln["invoice_no"]], ln["service_code"], ln["_d"]
        key = (ln["well_name"], day)
        if key not in cache:
            cache[key] = read_report(*key)
        rep = cache[key]
        if not (dt.date(2025, 1, 1) <= day <= dt.date(2026, 12, 31)) or not (I["_ps"] <= day <= I["_pe"]) \
                or rep is None or not rep["signed"]:
            out[ln["line_ref"]] = 0
            continue
        standby = rep["status"] == "Standby"
        if code in LIH:
            word, sar = LIH[code]
            if rep["lost"] != word:
                out[ln["line_ref"]] = 0
                continue
            # SAR cents x 100 halalas / (halalas per USD, in hundredths) -> USD cents, half-even (31A)
            usd = div_half_even(sar * 10000, cents(month_index(day, HALALAS)))
            dep = min(rep["lost_hours"] // 25, 50)
            out[ln["line_ref"]] = div_half_even(usd * (100 - dep), 100)
            continue
        if code in STANDBY and code not in ("MW-310", "HC-620"):
            supported = rep["crew"].get(code, 0)
            rate = personnel_base(code, day, I["_d"])
        else:
            word = {"MW-310": "MWD collar", "HC-620": "drilling jars"}[code]
            supported = 1 if word in rep["tools"] else 0
            # Clause 17A: base x index / 100.00, half-even (index in hundredths -> divide by 10,000)
            rate = div_half_even({"MW-310": 224585, "HC-620": 53965}[code] * cents(month_index(day, INDEX)), 10000)
            if code == "MW-310":
                if not standby:
                    rate = step(rate, SECTION[rep["section"]])
                rate = step(rate, CLASS[I["well_class"]])
        supported = min(supported, {"DD-101": 2, "MW-301": 2}.get(code, 1))           # Sch.3 Pt5
        if standby:
            rate = step(rate, STANDBY[code])
        disc = discount(code, day)
        if disc:
            rate = step(rate, disc)
        k = (ln["well_name"], day, code)
        qty = max(0, min(int(ln["quantity"]), supported - used[k]))
        used[k] += qty
        out[ln["line_ref"]] = qty * rate
    return out


class IndependentLines(unittest.TestCase):
    def test_every_line_of_three_families_agrees(self):
        mine = reprice_independently()
        prod = audit().lines
        self.assertGreater(len(mine), 30000)
        diff = [(ref, v, prod[ref].expected_amount) for ref, v in mine.items() if v != int(prod[ref].expected_amount * 100)]
        self.assertEqual(diff, [])
        families = defaultdict(int)
        for ref in mine:
            families[prod[ref].line.code[:2]] += 1
        self.assertEqual(set(families), {"DD", "MW", "LW", "PD", "HC", "LH"})


class IndependentAdjustment(unittest.TestCase):
    def test_36A_difference(self):
        """DD-101 / DD-120 performed on or after 2026-02-01 on invoices submitted before 2026-08-17,
        re-priced at A3 (DD-101 1,954.00; DD-120 416.00) minus the rate then in force."""
        inv, lines, _ = load()
        s2_monthly = {4: 40600, 5: 41150, 6: 41150, 7: 42300, 8: 42950, 9: 43400, 10: 43400, 11: 44100, 12: 44750}
        total = 0
        n = 0
        for ln in lines:
            code, day = ln["service_code"], ln["_d"]
            I = inv[ln["invoice_no"]]
            if code not in ("DD-101", "DD-120") or day is None or day < dt.date(2026, 2, 1) or I["_d"] >= dt.date(2026, 8, 17):
                continue
            rep = read_report(ln["well_name"], day)
            standby = rep["status"] == "Standby"
            if code == "DD-101":
                old, new = 191650, 195400
                if standby:
                    old, new = step(old, "0.80"), step(new, "0.80")
            else:
                old = s2_monthly.get(day.month, 39850) if day >= dt.date(2026, 4, 1) else 39850
                new = 41600
                old, new = step(old, SECTION[rep["section"]]), step(new, SECTION[rep["section"]])
                old, new = step(old, CLASS[I["well_class"]]), step(new, CLASS[I["well_class"]])
            disc = discount(code, day)
            if disc:
                old, new = step(old, disc), step(new, disc)
            q = int(ln["quantity"])
            total += q * new - q * old
            n += 1
        self.assertEqual(n, 3309)
        self.assertEqual(total, 30996552)                          # +309,965.52 USD
        plan = audit().plan
        self.assertEqual((int(plan.amount * 100), plan.carrier, len(plan.lines)), (total, "MDS-01625", n))


class IndependentInvoiceArithmetic(unittest.TestCase):
    def test_billed_arithmetic_and_unflagged_rows(self):
        inv, lines, _ = load()
        by = defaultdict(list)
        for ln in lines:
            by[ln["invoice_no"]].append(ln)
        res = audit().invoices
        bad_disc, bad_total = [], []
        for n, I in inv.items():
            svc = sum(cents(ln["amount"]) for ln in by[n] if ln["service_code"] != "DS-900")
            ds = sum(cents(ln["amount"]) for ln in by[n] if ln["service_code"] == "DS-900")
            want = -div_half_even((svc - 25000000) * 4, 100) if svc > 25000000 else 0
            if ds != want:
                bad_disc.append(n)
            net, vat, total = cents(I["net_amount"]), cents(I["vat_amount"]), cents(I["invoice_total"])
            self.assertEqual(net, svc + ds, n)
            self.assertEqual(vat, div_half_even(net * 15, 100), n)
            if net + vat + cents(I["adjustment"]) != total:
                bad_total.append(n)
            if not res[n].flagged:          # an unflagged row must reconcile exactly on its own figures
                self.assertEqual(int(res[n].expected_total * 100), total, n)
        self.assertEqual(sorted(bad_disc), ["MDS-00072", "MDS-00282", "MDS-01049"])
        self.assertEqual(sorted(bad_total), ["MDS-00551", "MDS-00916", "MDS-01317"])
        for n in bad_disc + bad_total:
            self.assertTrue(res[n].flagged, n)


if __name__ == "__main__":
    unittest.main()
