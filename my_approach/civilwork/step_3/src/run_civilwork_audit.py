"""Regenerate the civil-works submission part and its audit trail from the raw inputs.

    python my_approach/civilwork/step_3/src/run_civilwork_audit.py [--out DIR] [--data DIR] [--template CSV]

Standard library only (Python >= 3.10). Output is deterministic: no timestamps, fixed
row order, "\\n" line endings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter

from civilwork_audit import loader
from civilwork_audit.config import ACCEPTED
from civilwork_audit.pipeline import run_audit
from civilwork_audit.records import load_records
from civilwork_audit.sensitivity import ablation, scenarios
from civilwork_audit.submission import (SUBMISSION_COLUMNS, application_audit_rows, line_audit_rows,
                                        submission_rows, validate_rows, write_csv)

DEFAULT_OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))
SUBMISSION_PART = "civilwork_submission_part.csv"


def sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=loader.DEFAULT_DATA_DIR, help="civilwork input folder")
    ap.add_argument("--template", default=loader.DEFAULT_TEMPLATE, help="submission_template.csv")
    ap.add_argument("--out", default=DEFAULT_OUT, help="output folder")
    ap.add_argument("--skip-sensitivity", action="store_true", help="skip ablation and scenario runs")
    args = ap.parse_args(argv)

    inputs = loader.load_inputs(args.data)
    records = load_records(inputs.records_dir)
    result = run_audit(inputs, records, ACCEPTED)

    columns, template_ids = loader.load_template_ids(args.template)
    if columns != SUBMISSION_COLUMNS:
        raise SystemExit(f"template columns {columns} != {SUBMISSION_COLUMNS}")
    rows = submission_rows(result, template_ids)
    validate_rows(rows, [i for i in template_ids if i.startswith("PA-")])
    write_csv(os.path.join(args.out, SUBMISSION_PART), rows, SUBMISSION_COLUMNS)
    write_csv(os.path.join(args.out, "civilwork_line_audit.csv"), line_audit_rows(result))
    write_csv(os.path.join(args.out, "civilwork_application_audit.csv"), application_audit_rows(result))

    matched = {r for r, x in result.lines.items() if x.price.amount == x.line.amount}
    residual_apps = sorted({x.line.application_no for r, x in result.lines.items() if r not in matched})
    flagged = [k for k, d in result.applications.items() if d.flagged]
    summary = {
        "inputs": {os.path.relpath(p, loader.REPO_ROOT).replace(os.sep, "/"): sha256(p) for p in (
            os.path.join(args.data, "invoices", "applications.csv"),
            os.path.join(args.data, "invoices", "application_lines.csv"), args.template)},
        "counts": {"applications": len(inputs.applications), "lines": len(inputs.lines),
                   "records": len(records), "submission_rows": len(rows)},
        "pricing": {"lines_reproduced": len(matched), "residual_lines": len(inputs.lines) - len(matched),
                    "residual_applications": len(residual_apps)},
        "flagged": {"count": len(flagged), "ids": flagged,
                    "by_category": dict(sorted(Counter(result.applications[k].error_category for k in flagged).items()))},
        "clause_31A": {"instrument": result.plan.a31_instrument, "lines": len(result.plan.a31_lines),
                       "adjustment": str(result.plan.a31_amount), "carriers": result.plan.a31_carriers,
                       "note": result.plan.a31_note},
        "clause_45A": {"carrier": result.plan.a45_carrier, "retention_basis": str(result.plan.a45_basis),
                       "release": str(result.plan.a45_amount)},
        "records_unrecognised": sorted(r.ref for r in records.values() if not r.pattern_id),
    }
    if not args.skip_sensitivity:
        _, abl = ablation(inputs)
        write_csv(os.path.join(args.out, "civilwork_ablation.csv"), abl)
        write_csv(os.path.join(args.out, "civilwork_scenarios.csv"), scenarios(inputs, records, result))
    with open(os.path.join(args.out, "civilwork_run_summary.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, indent=1)
        f.write("\n")

    print(f"applications {len(inputs.applications)}  lines {len(inputs.lines)}  records {len(records)}")
    print(f"lines reproduced {len(matched)}; residual {len(inputs.lines) - len(matched)} lines "
          f"in {len(residual_apps)} applications")
    print(f"flagged {len(flagged)} of {len(rows)} civil-works applications")
    print(f"wrote {os.path.join(args.out, SUBMISSION_PART)} ({len(rows)} rows; civil works only, "
          f"not the full 2,806-row submission)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
