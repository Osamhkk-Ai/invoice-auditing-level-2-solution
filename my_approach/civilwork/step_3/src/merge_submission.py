"""Merge per-contract submission parts into the challenge's submission.csv.

    python my_approach/civilwork/step_3/src/merge_submission.py \\
        --part my_approach/civilwork/step_3/output/civilwork_submission_part.csv \\
        --part <drilling part>.csv --out submission.csv

Every template id must appear in exactly one part, with the template's columns. The
merge refuses to write a file with missing rows: a blank row is not a "0" claim.
"""
from __future__ import annotations

import argparse
import csv
import sys

from civilwork_audit import loader
from civilwork_audit.submission import SUBMISSION_COLUMNS, SubmissionError, validate_rows, write_csv


def merge(template: str, parts: list[str]) -> list[dict[str, str]]:
    columns, ids = loader.load_template_ids(template)
    if columns != SUBMISSION_COLUMNS:
        raise SubmissionError(f"template columns {columns}")
    by_id: dict[str, dict[str, str]] = {}
    for path in parts:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != SUBMISSION_COLUMNS:
                raise SubmissionError(f"{path}: columns {reader.fieldnames}")
            for row in reader:
                if row["invoice_id"] in by_id:
                    raise SubmissionError(f"{row['invoice_id']} appears in more than one part")
                by_id[row["invoice_id"]] = row
    missing = [i for i in ids if i not in by_id]
    extra = sorted(set(by_id) - set(ids))
    if missing or extra:
        raise SubmissionError(f"{len(missing)} template ids missing (e.g. {missing[:3]}); "
                              f"{len(extra)} ids not in the template (e.g. {extra[:3]})")
    rows = [by_id[i] for i in ids]
    validate_rows(rows, ids)
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", default=loader.DEFAULT_TEMPLATE)
    ap.add_argument("--part", action="append", required=True, help="a submission part (repeat)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        rows = merge(args.template, args.part)
    except SubmissionError as exc:
        print(f"merge refused: {exc}", file=sys.stderr)
        return 2
    write_csv(args.out, rows, SUBMISSION_COLUMNS)
    print(f"wrote {args.out}: {len(rows)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
