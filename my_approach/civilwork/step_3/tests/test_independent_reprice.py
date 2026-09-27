"""An independent re-pricing of the two Amendment No. 3 items, written from the
contract text and reading the raw CSV (no engine code), used to check the engine's
prices on those items and the Clause 31A adjustment of 60,508.18.

C.32.010 (p17): 1,860.00; A3 1,984.00 from 2025-11-01. Zone (Sch 2), ground (Sch 3,
frozen at G2 after 27 Sep 2025), no uplift, 5 % from 2025-12-01 and 8 % from
2026-04-01 (S2, A2). A.14.010: 53.20; A3 56.80. Zone, night 18 % where zone <= 1.1,
bands 2,000 / 8,000 at 100 / 95 / 91 % per Contract Year. Rounded once, half-up.
"""
import csv
import datetime as dt
import os
import unittest
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal as D

from _support import REPO, accepted

DATA = os.path.join(REPO, "invoice-auditing-level-2", "civilwork", "invoices")
ZONE = {"Z1": D("1"), "Z2": D("1.06"), "Z3": D("1.145"), "Z4": D("1.28")}
GROUND = {"G1": D("0.94"), "G2": D("1"), "G3": D("1.12"), "G4": D("1.375"), "G5": D("1.63")}
ISSUE = dt.date(2026, 5, 12)


def r2(x):
    return x.quantize(D("0.01"), ROUND_HALF_UP)


def reprice(new_rate_everywhere: bool) -> dict[str, D]:
    with open(os.path.join(DATA, "applications.csv"), encoding="utf-8") as f:
        app_date = {r["application_no"]: dt.date.fromisoformat(r["application_date"]) for r in csv.DictReader(f)}
    with open(os.path.join(DATA, "application_lines.csv"), encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["item_code"] in ("C.32.010", "A.14.010")]
    rows.sort(key=lambda r: (r["work_date"], r["application_no"], int(r["line_no"])))
    counted = defaultdict(int)
    out = {}
    for r in rows:
        wd = dt.date.fromisoformat(r["work_date"])
        zone = ZONE[r["site_zone"][:2]]
        new = wd >= dt.date(2025, 11, 1) and (new_rate_everywhere or app_date[r["application_no"]] >= ISSUE)
        q = int(r["quantity"])
        if r["item_code"] == "C.32.010":
            base = D("1984.00") if new else D("1860.00")
            ground = GROUND["G2" if wd > dt.date(2025, 9, 27) else r["ground_class"][:2]]
            disc = D("0.08") if wd >= dt.date(2026, 4, 1) else D("0.05") if wd >= dt.date(2025, 12, 1) else D(0)
            out[r["line_ref"]] = q * r2(base * zone * ground * (1 - disc))
        else:
            base = D("56.80") if new else D("53.20")
            unit = base * zone * (D("1.18") if r["night_work"] == "Y" and zone <= D("1.1") else 1)
            year = 1 if wd < dt.date(2026, 1, 5) else 2
            amount, pos = D(0), counted[year]
            for unit_no in range(pos + 1, pos + q + 1):          # unit by unit: no band arithmetic to share
                pct = 100 if unit_no <= 2000 else 95 if unit_no <= 8000 else 91
                amount += r2(unit * pct / 100)
            counted[year] += q
            out[r["line_ref"]] = amount
    return out


class IndependentReprice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = reprice(new_rate_everywhere=False)
        cls.retro = reprice(new_rate_everywhere=True)
        cls.res = accepted()

    def test_engine_agrees_on_every_line_of_both_items(self):
        for ref, amount in self.contract.items():
            self.assertEqual(self.res.lines[ref].price.amount, amount, ref)

    def test_billing_matches_except_known_residuals(self):
        mismatched = sorted(ref for ref, a in self.contract.items() if self.res.lines[ref].line.amount != a)
        # Appendix B: stale A.14.010 rate after issue (-00248-05, -00889-08); A3 rate taken
        # early plus 18 % (-00350-02); band not applied (-00374-02); qty x rate != amount (-00659-03).
        self.assertEqual(mismatched, ["PA-00248-05", "PA-00350-02", "PA-00374-02", "PA-00659-03", "PA-00889-08"])

    def test_clause_31A_adjustment(self):
        pre_issue = [ref for ref in self.contract if ref in self.res.plan.a31_lines]
        self.assertEqual(len(pre_issue), 89)
        by_item = defaultdict(D)
        for ref in pre_issue:
            by_item[self.res.lines[ref].line.item_code] += self.retro[ref] - self.contract[ref]
        self.assertEqual(by_item["C.32.010"], D("26521.21"))
        self.assertEqual(by_item["A.14.010"], D("33986.97"))
        self.assertEqual(sum(by_item.values()), D("60508.18"))
        self.assertEqual(self.res.plan.a31_amount, D("60508.18"))
        self.assertEqual(len({self.res.lines[r].line.application_no for r in pre_issue}), 72)


if __name__ == "__main__":
    unittest.main()
