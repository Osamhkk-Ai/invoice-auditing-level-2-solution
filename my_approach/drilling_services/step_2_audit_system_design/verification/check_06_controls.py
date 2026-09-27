"""Check 06 - negative controls: unusual lines the contract allows must stay unflagged."""
from __future__ import annotations

import datetime as dt

from common import A3_ISSUED, D, load_invoices, load_lines, load_reports
from check_04_reprice import a3_adjustment, reprice


def run() -> dict:
    inv = load_invoices()
    lines = load_lines()
    reps = load_reports()
    priced = reprice(inv, lines, reps)
    clean = lambda l: priced[l["line_ref"]]["delta"] == 0 and not priced[l["line_ref"]]["reasons"]

    def group(pred):
        g = [l for l in lines if l["service_code"] != "DS-900" and pred(l)]
        bad = [l["line_ref"] for l in g if not clean(l)]
        return {"lines": len(g), "flagged": len(bad), "flagged_refs": bad[:10]}

    res = {
        "DD-111 on a Standby day (100%, Sch.3 Pt3)": group(lambda l: l["service_code"] == "DD-111" and l["day_status"] == "Standby"),
        "LW-420 on a Standby day (100%)": group(lambda l: l["service_code"] == "LW-420" and l["day_status"] == "Standby"),
        "DD-121 on a Standby day": group(lambda l: l["service_code"] == "DD-121" and l["day_status"] == "Standby"),
        "personnel on a Standby day (80%/100%)": group(lambda l: l["service_code"] in ("DD-101", "DD-102", "MW-301", "PD-201", "LW-401") and l["day_status"] == "Standby"),
        "PD-210 lines split at a band boundary": group(lambda l: l["service_code"] == "PD-210" and l["dfrom"] in (1500, 3000, 4500) or l["dto"] in (1500, 3000, 4500) if l["service_code"] == "PD-210" else False),
        "DD-120 billed one hour below the report (21A)": group(lambda l: l["service_code"] == "DD-120" and l["qty"] == reps[(l["well_name"], l["date"])].circ - 1),
        "HC-601 in 2026 at the last published S1 rate 736.40": group(lambda l: l["service_code"] == "HC-601" and l["date"] >= dt.date(2026, 1, 1)),
        "DD-101/DD-120 >= 2026-02-01 invoiced before A3 issue (old rate, 36A)": group(
            lambda l: l["service_code"] in ("DD-101", "DD-120") and l["date"] >= dt.date(2026, 2, 1) and inv[l["invoice_no"]]["invoice_date_d"] < A3_ISSUED),
        "DD-120 Apr-Dec 2026 invoiced after A3 at 416.00 not S2 monthly": group(
            lambda l: l["service_code"] == "DD-120" and l["date"] >= dt.date(2026, 4, 1) and inv[l["invoice_no"]]["invoice_date_d"] >= A3_ISSUED),
        "lost-in-hole lines": group(lambda l: l["service_code"].startswith("LH-")),
        "report_ref date differs but same-day report supports it (MDS-00128-026, MDS-01352-007)": group(
            lambda l: l["line_ref"] in ("MDS-00128-026", "MDS-01352-007")),
    }
    # invoices with a DS-900 line that is correct
    by_inv = {}
    for l in lines:
        by_inv.setdefault(l["invoice_no"], []).append(l)
    ds_ok = 0
    for n, L in by_inv.items():
        if any(l["service_code"] == "DS-900" for l in L):
            svc = sum((l["amt"] for l in L if l["service_code"] != "DS-900"), D(0))
            ds = sum((l["amt"] for l in L if l["service_code"] == "DS-900"), D(0))
            ds_ok += ds == -((svc - D("250000.00")) * D("0.04")).quantize(D("0.01"))
    res["invoices_with_correct_DS-900"] = ds_ok
    res["a3_adjustment_target"] = {k: str(v) for k, v in a3_adjustment(inv, lines).items()}
    return res


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=1, default=str))
