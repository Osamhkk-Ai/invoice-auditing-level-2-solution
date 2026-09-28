"""Compare the production auditor with the Step 2 verification prototype, field by field.

    python my_approach/drilling_services/step_3/src/compare_with_step2.py

Runs the prototype (``step_2_audit_system_design/verification``) and production on the same raw
inputs and compares, for every priced line, the supported quantity paid, the contract rate, the
expected amount and the reason codes; for every invoice, the rebuilt total, the flag and the defect
set; and the Clause 36A amount and carrier. Writes ``output/drilling_step2_comparison.json`` and
exits non-zero on any difference.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
STEP2 = os.path.abspath(os.path.join(HERE, "..", "..", "step_2_audit_system_design", "verification"))

# Step 2 reason names that production spells differently.
REASON_ALIASES = {"section_or_status_differs_from_report": "section_or_status_differs",
                  "discount_DS900_wrong": "discount_DS900_missing", "net_ne_sum_lines": "net_ne_sum_of_lines"}


def run_step2():
    sys.path.insert(0, STEP2)
    try:
        import check_04_reprice as c4
        import common
        inv, lines, reps = common.load_invoices(), common.load_lines(), common.load_reports()
        priced = c4.reprice(inv, lines, reps)
        adj = c4.a3_adjustment(inv, lines)
        rebuilt = c4.rebuild_invoices(inv, lines, priced, adj)
        flags = c4.invoice_flags(inv, lines, priced, rebuilt)
        return priced, adj, rebuilt, flags
    finally:
        sys.path.remove(STEP2)


def compare(prod, step2) -> dict:
    priced, adj, rebuilt, flags = step2
    diffs: dict[str, list] = {"line_qty": [], "line_rate": [], "line_amount": [], "line_reasons": [],
                              "invoice_total": [], "invoice_flag": [], "invoice_reasons": []}
    for ref, p in priced.items():
        r = prod.lines[ref]
        if p["exp_qty"] != r.paid_qty:
            diffs["line_qty"].append([ref, str(p["exp_qty"]), str(r.paid_qty)])
        prod_rate = r.rate.rate if r.rate else None
        if p["exp_qty"] and p["exp_rate"] != prod_rate:
            diffs["line_rate"].append([ref, str(p["exp_rate"]), str(prod_rate)])
        if p["exp_amt"] != r.expected_amount:
            diffs["line_amount"].append([ref, str(p["exp_amt"]), str(r.expected_amount)])
        a = sorted(REASON_ALIASES.get(x, x) for x in p["reasons"])
        if a != sorted(r.reasons):
            diffs["line_reasons"].append([ref, a, sorted(r.reasons)])
    line_level = {"rate_differs", "qty_above_report", "not_supported_by_report", "already_billed", "report_unsigned",
                  "outside_invoice_period", "outside_term", "amount_ne_qty_x_rate", "part_C_absent", "part_D_absent",
                  "not_chargeable_on_status", "section_or_status_differs_from_report", "lih_code_differs_from_part_E",
                  "no_report_for_day", "amount_differs"}
    for n, rb in rebuilt.items():
        d = prod.invoices[n]
        if rb["total"] != d.expected_total:
            diffs["invoice_total"].append([n, str(rb["total"]), str(d.expected_total)])
        if bool(flags[n]) != d.flagged:
            diffs["invoice_flag"].append([n, bool(flags[n]), d.flagged])
        a = sorted(REASON_ALIASES.get(x, x) for x in flags[n] if x not in line_level)
        if a != sorted(d.reasons):
            diffs["invoice_reasons"].append([n, a, sorted(d.reasons)])
    prod_adj = {prod.plan.carrier: prod.plan.amount}
    out = {
        "lines_compared": len(priced), "invoices_compared": len(rebuilt),
        "step2": {"lines_exact": sum(1 for p in priced.values() if p["delta"] == 0 and not p["reasons"]),
                  "flagged": sum(1 for c in flags.values() if c),
                  "a3": {k: str(v) for k, v in adj.items()},
                  "line_reasons": dict(sorted(Counter(x for p in priced.values() for x in p["reasons"]).items()))},
        "production": {"lines_exact": sum(1 for r in prod.lines.values() if not r.delta and not r.reasons),
                       "flagged": sum(d.flagged for d in prod.invoices.values()),
                       "a3": {k: str(v) for k, v in prod_adj.items()},
                       "line_reasons": dict(sorted(Counter(x for r in prod.lines.values() for x in r.reasons).items()))},
        "a3_identical": {k: str(v) for k, v in adj.items()} == {k: str(v) for k, v in prod_adj.items()},
        "differences": {k: len(v) for k, v in diffs.items()},
        "difference_examples": {k: v[:10] for k, v in diffs.items() if v},
    }
    out["identical"] = out["a3_identical"] and not any(diffs.values())
    return out


def main() -> int:
    sys.path.insert(0, HERE)
    from drilling_audit import loader
    from drilling_audit.audit import run_audit
    from drilling_audit.reports import load_reports
    inputs = loader.load_inputs()
    prod = run_audit(inputs, load_reports(inputs.records_dir))
    res = compare(prod, run_step2())
    path = os.path.join(HERE, "..", "output", "drilling_step2_comparison.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1)
        f.write("\n")
    print(json.dumps({k: res[k] for k in ("differences", "a3_identical", "identical")}, indent=1))
    return 0 if res["identical"] else 1


if __name__ == "__main__":
    sys.exit(main())
