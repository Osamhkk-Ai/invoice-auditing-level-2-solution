"""Check 07 - explain each wrong billed rate by the nearest plausible mechanism.

Diagnosis only: it names which mis-application reproduces the billed figure. It does not change the
expected amount, which always comes from the contract build-up in check_04.
"""
from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import replace

from common import (CLASS_FACTOR, HALALAS, LIH_SAR, SCHEDULE_1, SECTION_FACTOR, D, PD210_BANDS, RSI,
                    load_invoices, load_lines, load_reports, r2, ym)
from check_04_reprice import reprice
from pricing import BASELINE, build_rate, lih_value


def candidates(l, I, rep):
    code, day, idate = l["service_code"], l["date"], I["invoice_date_d"]
    sec, st, cls = rep.section, rep.status, I["well_class"]
    out = {}
    if code.startswith("LH-"):
        h = int(rep.fields["Circulating hours accumulated on the well"])
        out["LIH: Schedule 6 USD, no depreciation"] = __import__("common").LIH_USD_SCHED6[code]
        out["LIH: Schedule 6 USD instead of Sch.2D SAR"] = lih_value(code, day, h, replace(BASELINE, lih_from_sar=False))[0]
        dep = min(h // 25, 50)
        for m, hal in HALALAS.items():
            if m != ym(day):
                out[f"LIH: exchange rate of {m} instead of {ym(day)}"] = r2(r2(LIH_SAR[code] * 100 / hal) * (100 - dep) / 100)
        return out
    if code == "PD-210":
        for lo, hi, r in PD210_BANDS:
            out[f"PD-210: band rate {r}"] = r
            out[f"PD-210: band rate {r} x class"] = r2(r * CLASS_FACTOR[cls])
        return out
    for m in (-1, 1):  # index of an adjacent month
        other = (day.replace(day=15) + dt.timedelta(days=30 * m))
        if ym(other) in RSI:
            out[f"index of month {m:+d}"] = build_rate(code, other, sec, st, cls, idate)[0] if code in ("MW-310", "HC-620") else None
    out["status ignored (Operating rate on a Standby day)"] = build_rate(code, day, sec, "Operating", cls, idate)[0]
    out["previous instrument's rate (day one year earlier)"] = build_rate(code, day - dt.timedelta(days=365), sec, st, cls, idate)[0] if day.year == 2026 else None
    out["rate before 2025-07-01 (Supplement 1 missed)"] = build_rate(code, dt.date(2025, 6, 30), sec, st, cls, idate)[0] if day >= dt.date(2025, 7, 1) else None
    for eff, pct in ((dt.date(2026, 4, 1), D("0.04")), (dt.date(2026, 7, 1), D("0.07"))):
        base, _ = build_rate(code, day, sec, st, cls, idate)
        if base is not None:
            out[f"extra {pct} discount (taken early)"] = r2(base * (1 - pct))
    no_disc = build_rate(code, dt.date(2026, 3, 31), sec, st, cls, idate)[0] if day >= dt.date(2026, 4, 1) else None
    out["discount omitted"] = no_disc
    out["A3 rate on a pre-issue invoice / pre-A3 rate on a post-issue invoice"] = build_rate(
        code, day, sec, st, cls, dt.date(2026, 8, 17) if idate < dt.date(2026, 8, 17) else dt.date(2026, 8, 1))[0]
    for c2, f in CLASS_FACTOR.items():
        if c2 != cls:
            out[f"class factor of {c2}"] = build_rate(code, day, sec, st, c2, idate)[0]
    for s2 in ('26"', '17-1/2"', '12-1/4"', '8-1/2"', '6"'):
        if s2 != sec:
            out[f"section factor of {s2}"] = build_rate(code, day, s2, st, cls, idate)[0]
    if code in ("MW-310", "HC-620"):
        # labelled search: which of index / section / class / standby step departs from the contract
        base0 = D(SCHEDULE_1[code][1])
        for idx in [None] + sorted(RSI):
            b = base0 if idx is None else r2(base0 * RSI[idx] / 100)
            for sec2 in list(SECTION_FACTOR) + [None]:
                r1 = b if sec2 is None or code == "HC-620" else r2(b * SECTION_FACTOR[sec2])
                for cls2 in CLASS_FACTOR:
                    r_ = r2(r1 * CLASS_FACTOR[cls2]) if code == "MW-310" else r1
                    for sb in (False, True):
                        v = r2(r_ * D("0.5")) if sb else r_
                        parts = []
                        if idx is None:
                            parts.append("index omitted")
                        elif idx != ym(day):
                            parts.append(f"index {idx}")
                        if sec2 != (None if st == "Standby" else sec) and code == "MW-310":
                            parts.append(f"section {sec2}" if sec2 else "no section factor")
                        if cls2 != cls and code == "MW-310":
                            parts.append(f"class {cls2}")
                        if sb != (st == "Standby"):
                            parts.append("standby % " + ("applied" if sb else "omitted"))
                        if parts:
                            out.setdefault("; ".join(parts), v)
    out["S2 monthly rate instead of A3"] = build_rate(code, day, sec, st, cls, idate, replace(BASELINE, dd120_a3_over_s2_monthly=False))[0]
    return out


def run() -> dict:
    inv = load_invoices()
    lines = load_lines()
    reps = load_reports()
    priced = reprice(inv, lines, reps)
    diag = {}
    for ref, p in sorted(priced.items()):
        if "rate_differs" not in p["reasons"]:
            continue
        l = p["line"]
        I = inv[l["invoice_no"]]
        rep = reps[(l["well_name"], l["date"])]
        hits = sorted((k for k, v in candidates(l, I, rep).items() if v is not None and v == l["rate"]),
                      key=lambda k: (k.count(";"), k))
        diag[ref] = {"code": l["service_code"], "date": l["service_date"], "billed_rate": str(l["rate"]),
                     "contract_rate": str(p["exp_rate"]), "explained_by": hits or ["unexplained"]}
    res = {"rate_differs_lines": len(diag),
           "mechanisms": dict(Counter(v["explained_by"][0] for v in diag.values())),
           "lines": diag}
    return res


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=1, default=str))
