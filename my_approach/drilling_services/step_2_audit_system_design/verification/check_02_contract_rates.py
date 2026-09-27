"""Check 02 - contract rate build-up: effective-date boundaries, worked examples, rounding points."""
from __future__ import annotations

import datetime as dt
from decimal import ROUND_HALF_UP

from common import D, DISCOUNT_PCT, DISCOUNT_THRESHOLD, VAT, r2
from pricing import BASELINE, Reading, build_rate, lih_value, pd210_split

d = dt.date
PRE_A3, POST_A3 = d(2026, 8, 16), d(2026, 8, 17)

# (code, day, section, status, class, invoice_date, expected rate, why)
BOUNDARIES = [
    ("DD-120", d(2025, 6, 30), '12-1/4"', "Operating", "Standard", None, "384.15", "Sch1 before S1"),
    ("DD-120", d(2025, 7, 1), '12-1/4"', "Operating", "Standard", None, "398.50", "S1 1.1 from 2025-07-01"),
    ("DD-121", d(2025, 6, 30), '8-1/2"', "Standby", "Standard", None, "2893.65", "Sch1 before S1"),
    ("DD-121", d(2025, 7, 1), '8-1/2"', "Standby", "Standard", None, "2984.00", "S1 1.1"),
    ("HC-601", d(2025, 6, 30), '17-1/2"', "Operating", "Standard", None, "689.35", "Sch1 before S1 1.2"),
    ("HC-601", d(2025, 7, 1), '17-1/2"', "Operating", "Standard", None, "701.50", "S1 1.2 July 2025"),
    ("HC-601", d(2026, 3, 15), '17-1/2"', "Operating", "Standard", None, "736.40", "S1 1.2 last published carries"),
    ("DD-101", d(2025, 12, 31), '8-1/2"', "Operating", "Standard", None, "1847.35", "Sch1"),
    ("DD-101", d(2026, 1, 1), '8-1/2"', "Operating", "Standard", None, "1916.50", "A1 1.2"),
    ("DD-101", d(2026, 1, 31), '8-1/2"', "Operating", "Standard", POST_A3, "1916.50", "A1 (A3 not yet effective)"),
    ("DD-101", d(2026, 2, 1), '8-1/2"', "Operating", "Standard", PRE_A3, "1916.50", "36A: pre-issue invoice at A1"),
    ("DD-101", d(2026, 2, 1), '8-1/2"', "Operating", "Standard", POST_A3, "1954.00", "A3 on/after issue"),
    ("DD-101", d(2026, 3, 31), '8-1/2"', "Operating", "Standard", POST_A3, "1954.00", "A3, no discount yet"),
    ("DD-101", d(2026, 4, 1), '8-1/2"', "Operating", "Standard", PRE_A3, "1839.84", "A1 x 0.96 (S2 2.2)"),
    ("DD-101", d(2026, 4, 1), '8-1/2"', "Operating", "Standard", POST_A3, "1875.84", "A3 x 0.96"),
    ("DD-101", d(2026, 6, 30), '8-1/2"', "Operating", "Standard", POST_A3, "1875.84", "A3 x 0.96"),
    ("DD-101", d(2026, 7, 1), '8-1/2"', "Operating", "Standard", POST_A3, "1817.22", "A3 x 0.93 (A2 2.3)"),
    ("DD-101", d(2026, 7, 1), '8-1/2"', "Standby", "Standard", POST_A3, "1453.78", "A3 x 0.80 -> 1563.20 x 0.93"),
    ("DD-120", d(2026, 1, 31), '12-1/4"', "Operating", "Standard", POST_A3, "398.50", "S1"),
    ("DD-120", d(2026, 2, 1), '12-1/4"', "Operating", "Standard", PRE_A3, "398.50", "36A pre-issue"),
    ("DD-120", d(2026, 2, 1), '12-1/4"', "Operating", "Standard", POST_A3, "416.00", "A3"),
    ("DD-120", d(2026, 4, 1), '12-1/4"', "Operating", "Standard", PRE_A3, "389.76", "S2 2.1 Apr 406.00 x 0.96"),
    ("DD-120", d(2026, 4, 1), '12-1/4"', "Operating", "Standard", POST_A3, "399.36", "A3 416.00 x 0.96 (later-issued governs)"),
    ("DD-120", d(2026, 7, 1), '8-1/2"', "Operating", "HPHT", POST_A3, "484.42", "416 x .945=393.12 x1.325=520.88 x.93=484.4184"),
    ("MW-301", d(2026, 6, 30), '8-1/2"', "Operating", "Standard", None, "1639.68", "A1 1708.00 x 0.96"),
    ("MW-301", d(2026, 7, 1), '8-1/2"', "Operating", "Standard", None, "1639.59", "A2 1763.00 x 0.93"),
    ("LW-401", d(2026, 3, 31), '8-1/2"', "Operating", "Standard", None, "1969.00", "A1"),
    ("LW-401", d(2026, 4, 1), '8-1/2"', "Operating", "Standard", None, "1890.24", "A1 x 0.96"),
    ("MB-701", d(2026, 3, 31), '26"', "Operating", "Standard", None, "18497.50", "Sch1"),
    ("MB-701", d(2026, 4, 1), '26"', "Operating", "Standard", None, "17757.60", "Sch1 x 0.96"),
    ("MB-701", d(2026, 7, 1), '26"', "Operating", "Standard", None, "17890.41", "A2 19237.00 x 0.93"),
    ("MW-310", d(2025, 1, 31), '12-1/4"', "Operating", "Standard", None, "2245.85", "index 100.00"),
    ("MW-310", d(2025, 2, 1), '12-1/4"', "Operating", "Standard", None, "2261.57", "index 100.70"),
    ("MW-310", d(2026, 12, 31), '26"', "Operating", "HPHT", None, "4543.12", "index 116.10 -> 2607.43 x1.315=3428.77 x1.325=4543.12"),
    ("MW-310", d(2025, 6, 4), '12-1/4"', "Standby", "HPHT", None, "1541.44", "index 103.60 -> 2326.70; no section (17B); x1.325=3082.88; x0.5=1541.44 half-even"),
    ("HC-620", d(2025, 5, 31), '8-1/2"', "Operating", "Standard", None, "556.38", "index 103.10"),
    ("DD-110", d(2025, 5, 1), '17-1/2"', "Standby", "Standard", None, "708.88", "no section factor on Standby (17B); 708.875 half-even"),
    ("MW-320", d(2025, 5, 1), '8-1/2"', "Standby", "Standard", None, "389.82", "389.825 -> half-even 389.82"),
    ("DD-121", d(2025, 8, 1), '12-1/4"', "Operating", "Standard", None, None, "DD-121 only on Standby (Sch.3 Pt4)"),
    ("HC-640", d(2025, 8, 1), '12-1/4"', "Standby", "Standard", None, None, "not chargeable on Standby"),
    ("DD-111", d(2025, 8, 1), '17-1/2"', "Standby", "Standard", None, "3589.45", "100% on Standby"),
    ("MW-330", d(2024, 12, 31), '26"', "Operating", "Standard", None, None, "before Commencement"),
    ("MW-330", d(2027, 1, 1), '26"', "Operating", "Standard", None, None, "after extended Expiry"),
]


def run() -> dict:
    res = {"boundary_cases": [], "boundary_failures": []}
    for code, day, sec, st, cls, idate, exp, why in BOUNDARIES:
        got, trail = build_rate(code, day, sec, st, cls, idate)
        ok = (got is None and exp is None) or (got is not None and exp is not None and got == D(exp))
        row = {"code": code, "day": str(day), "section": sec, "status": st, "class": cls,
               "invoice_date": str(idate), "expected": exp, "model": None if got is None else str(got), "ok": ok,
               "why": why, "trail": " | ".join(trail)}
        res["boundary_cases"].append(row)
        if not ok:
            res["boundary_failures"].append(row)

    # Appendix B (p.30) form of invoice: HPHT well, June 2025.
    appb = [("DD-101", "Standby", 2, "1477.88"), ("MW-310", "Operating", 1, "2975.75"),
            ("DD-120", "Operating", 18, "509.00")]
    pre_ix = Reading(apply_index=False)
    rows = []
    for code, st, q, printed in appb:
        day = d(2025, 6, 3) if st == "Standby" else d(2025, 6, 4)
        r_ix, _ = build_rate(code, day, '12-1/4"', st, "HPHT")
        r_pre, _ = build_rate(code, day, '12-1/4"', st, "HPHT", rd=pre_ix)
        rows.append({"code": code, "printed_rate": printed, "part_III_only": str(r_pre), "with_part_IX": str(r_ix),
                     "printed_qty": q})
    res["appendix_b_rates"] = rows
    res["appendix_b_pd210_split_2930_3085"] = [(a, b, str(r)) for a, b, r in pd210_split(2930, 3085)]
    net = D("2955.76") + D("2975.75") + D("9162.00") + D("4070.50") + D("6498.25")
    res["appendix_b_net_vat_total"] = [str(net), str(r2(net * VAT)), str(net + r2(net * VAT))]
    res["appendix_b_discount_on_312400"] = str(-r2((D("312400.00") - DISCOUNT_THRESHOLD) * DISCOUNT_PCT))
    # Appendix F (p.34): 412 h -> 16 per cent.
    v, trail = lih_value("LH-713", d(2025, 8, 22), 412, Reading(lih_from_sar=False))
    res["appendix_f_412h"] = trail
    v2, trail2 = lih_value("LH-713", d(2025, 8, 22), 412)
    res["appendix_f_412h_via_sar"] = trail2
    res["lih_cap_50pct_at_1300h"] = lih_value("LH-712", d(2025, 8, 22), 1300, Reading(lih_from_sar=False))[1]
    # Rounding mode demonstration: values that differ between half-even and half-up
    res["rounding_examples"] = [
        {"x": "708.875", "half_even": str(r2(D("708.875"))), "half_up": str(r2(D("708.875"), ROUND_HALF_UP))},
        {"x": "389.825", "half_even": str(r2(D("389.825"))), "half_up": str(r2(D("389.825"), ROUND_HALF_UP))},
    ]
    return res


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=1, default=str))
