"""Regenerate the drilling submission part and its audit trail from the raw inputs.

    python my_approach/drilling_services/step_3/src/run_drilling_audit.py [--out DIR] [--skip-sensitivity]

Standard library only (Python >= 3.10). Deterministic: no timestamps, fixed row order, "\\n" endings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter

from drilling_audit import loader
from drilling_audit.audit import run_audit
from drilling_audit.config import PRODUCTION
from drilling_audit.money import to_cents
from drilling_audit.reports import load_reports
from drilling_audit.sensitivity import scenarios
from drilling_audit.submission import (SUBMISSION_COLUMNS, invoice_audit_rows, line_audit_rows, submission_rows,
                                       validate_rows, write_csv)

DEFAULT_OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))
SUBMISSION_PART = "drilling_submission_part.csv"


def sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=loader.DEFAULT_DATA_DIR)
    ap.add_argument("--template", default=loader.DEFAULT_TEMPLATE)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--skip-sensitivity", action="store_true")
    args = ap.parse_args(argv)

    inputs = loader.load_inputs(args.data)
    reports = load_reports(inputs.records_dir)
    result = run_audit(inputs, reports, PRODUCTION)

    columns, _ = loader.load_template_ids(args.template)
    if columns != SUBMISSION_COLUMNS:
        raise SystemExit(f"template columns {columns} != {SUBMISSION_COLUMNS}")
    ids = loader.drilling_template_ids(args.template)
    rows = submission_rows(result, ids)
    validate_rows(rows, ids)
    write_csv(os.path.join(args.out, SUBMISSION_PART), rows, SUBMISSION_COLUMNS)
    write_csv(os.path.join(args.out, "drilling_invoice_audit.csv"), invoice_audit_rows(result))
    write_csv(os.path.join(args.out, "drilling_line_exceptions.csv"), line_audit_rows(result, only_exceptions=True))
    write_csv(os.path.join(args.out, "drilling_line_audit.csv"), line_audit_rows(result))

    L = result.lines
    exact = [k for k, r in L.items() if not r.delta and not r.reasons]
    flagged = [n for n in ids if result.invoices[n].flagged]
    plan = result.plan
    summary = {
        "inputs": {os.path.relpath(p, loader.REPO_ROOT).replace(os.sep, "/"): sha256(p) for p in (
            os.path.join(args.data, "invoices", "invoices.csv"),
            os.path.join(args.data, "invoices", "invoice_lines.csv"), args.template)},
        "counts": {"invoices": len(inputs.invoices), "lines": len(inputs.lines), "reports": len(reports),
                   "priced_lines": len(L), "submission_rows": len(rows)},
        "reports": {"unreadable": result.unread_reports,
                    "unsigned": sorted(r.file for r in reports.values() if not r.signed),
                    "parts": dict(sorted(Counter("".join(r.parts) for r in reports.values()).items()))},
        "lines": {"exact_no_reason": len(exact), "exceptions": len(L) - len(exact),
                  "by_reason": dict(sorted(Counter(x for r in L.values() for x in r.reasons).items())),
                  "warnings": sorted(k for k, r in L.items() if r.warnings)},
        "invoices": {"flagged": len(flagged), "flagged_pct": round(100 * len(flagged) / len(ids), 2),
                     "expected_ne_billed": sum(1 for r in rows if r["expected_total_cents"] != r["billed_total_cents"]),
                     "by_category": dict(sorted(Counter(result.invoices[n].error_category for n in flagged).items())),
                     "flagged_ids": flagged,
                     "sum_billed_cents": sum(int(r["billed_total_cents"]) for r in rows),
                     "sum_expected_cents": sum(int(r["expected_total_cents"]) for r in rows)},
        "clause_36A": {"instrument": plan.instrument, "lines": len(plan.lines), "amount": str(plan.amount),
                       "by_basis": {k: str(v) for k, v in plan.by_basis.items()}, "carrier": plan.carrier,
                       "note": plan.note,
                       "carrier_expected_total_cents": to_cents(result.invoices[plan.carrier].expected_total),
                       "carrier_billed_total_cents": to_cents(result.invoices[plan.carrier].billed_total)},
        "config": repr(PRODUCTION),
    }
    if not args.skip_sensitivity:
        write_csv(os.path.join(args.out, "drilling_scenarios.csv"), scenarios(inputs, reports, result))
    with open(os.path.join(args.out, "drilling_run_summary.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, indent=1)
        f.write("\n")
    print(f"invoices {len(inputs.invoices)}  lines {len(inputs.lines)}  reports {len(reports)}")
    print(f"priced lines {len(L)}: exact {len(exact)}, exceptions {len(L) - len(exact)}")
    print(f"flagged {len(flagged)} of {len(rows)} drilling invoices; 36A {plan.amount} on {plan.carrier}")
    print(f"wrote {os.path.join(args.out, SUBMISSION_PART)} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
