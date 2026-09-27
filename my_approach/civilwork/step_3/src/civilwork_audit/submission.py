"""Write the civil-works submission rows and the line / application audit trails.

The submission artifact has exactly the template's columns, one row per civil-works
application in template order, money in integer halalas. It is *part* of the
challenge submission: ``merge_submission.py`` combines it with the drilling part and
refuses to write ``submission.csv`` unless every template id is covered exactly once.
"""
from __future__ import annotations

import csv
import os
import re
from decimal import Decimal

from . import categories as K
from .decisions import to_cents
from .pipeline import AuditResult

SUBMISSION_COLUMNS = ["invoice_id", "flagged", "error_category", "expected_total_cents",
                      "billed_total_cents", "confidence"]
CIVIL_ID = re.compile(r"^PA-\d{5}$")


class SubmissionError(ValueError):
    pass


def submission_rows(result: AuditResult, template_ids: list[str]) -> list[dict[str, str]]:
    civil_ids = [i for i in template_ids if CIVIL_ID.match(i)]
    if set(civil_ids) != set(result.applications):
        missing = set(civil_ids) ^ set(result.applications)
        raise SubmissionError(f"template and applications differ: {sorted(missing)[:10]}")
    rows = []
    for inv in civil_ids:
        d = result.applications[inv]
        rows.append({
            "invoice_id": inv,
            "flagged": "1" if d.flagged else "0",
            "error_category": d.error_category if d.flagged else "",
            "expected_total_cents": str(to_cents(d.expected_total)),
            "billed_total_cents": str(to_cents(d.billed_total)),
            "confidence": f"{d.confidence:.2f}",
        })
    return rows


def validate_rows(rows: list[dict[str, str]], expected_ids: list[str]) -> None:
    """Schema checks shared by the writer, the merger and the tests."""
    ids = [r["invoice_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise SubmissionError("duplicate invoice ids")
    if ids != expected_ids:
        raise SubmissionError("ids differ from the expected ids or their order")
    for r in rows:
        if list(r) != SUBMISSION_COLUMNS:
            raise SubmissionError(f"{r['invoice_id']}: columns {list(r)}")
        if r["flagged"] not in ("0", "1"):
            raise SubmissionError(f"{r['invoice_id']}: flagged must be 0 or 1")
        if (r["flagged"] == "1") != bool(r["error_category"]):
            raise SubmissionError(f"{r['invoice_id']}: error_category must be set exactly when flagged")
        for k in ("expected_total_cents", "billed_total_cents"):
            if not re.fullmatch(r"-?\d+", r[k]):
                raise SubmissionError(f"{r['invoice_id']}: {k} must be an integer, got {r[k]!r}")
        c = Decimal(r["confidence"])
        if not Decimal(0) <= c <= Decimal(1):
            raise SubmissionError(f"{r['invoice_id']}: confidence outside [0, 1]")


def write_csv(path: str, rows: list[dict], columns: list[str] | None = None) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns or list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def line_audit_rows(result: AuditResult) -> list[dict[str, str]]:
    rows = []
    for ref, r in result.lines.items():
        ln, la, p = r.line, r.assessment, r.price
        cats = r.categories
        rows.append({
            "line_ref": ref, "application_no": ln.application_no, "work_date": ln.work_date.isoformat(),
            "item_code": ln.item_code, "unit": ln.unit, "zone": ln.zone, "ground_billed": ln.ground,
            "night_work": "Y" if ln.night_work else "N", "record_ref": ln.record_ref,
            "billed_quantity": str(ln.quantity), "billed_rate": str(ln.rate_applied),
            "billed_amount": str(ln.amount),
            "evidence_status": la.evidence_status,
            "record_quantity": "" if la.record_qty is None else str(la.record_qty),
            "record_item": la.record_item or "",
            "quantity_basis": la.quantity_basis,
            "supported_quantity": str(la.supported_qty),
            "base_rate": str(p.base), "base_source": p.base_source,
            "zone_factor": str(p.zone_factor), "ground_used": p.ground_used,
            "uplift": f"{p.uplift_kind} {p.uplift_percent}%" if p.uplift_kind else "",
            "discount": str(p.discount), "band_position_before": "" if p.band_position is None else str(p.band_position),
            "contract_amount_at_billed_qty": str(p.amount),
            "calculation": p.describe(la.supported_qty),
            "expected_amount": str(r.expected_amount), "delta": str(r.delta),
            "categories": ";".join(cats),
            "clauses": " | ".join(K.clause(c) for c in cats),
            "reasons": " | ".join(_price_reasons(r) + [f.detail for f in la.findings]),
        })
    return rows


def _price_reasons(r) -> list[str]:
    ln, p = r.line, r.price
    if not r.price_categories:
        return []
    out = [f"billed {ln.quantity} x {ln.rate_applied} = {ln.amount}; contract {p.amount} at the billed quantity"]
    if ln.rate_applied * ln.quantity != ln.amount:
        out.append(f"quantity x billed rate = {ln.rate_applied * ln.quantity}, not the {ln.amount} billed")
    if r.diagnosis:
        out.append("billed rate reproduced with: " + "; ".join(r.diagnosis))
    return out


def application_audit_rows(result: AuditResult) -> list[dict[str, str]]:
    flagged_lines: dict[str, list[str]] = {no: [] for no in result.applications}
    for r in result.lines.values():
        if r.categories:
            flagged_lines[r.line.application_no].append(r.line.line_ref)
    rows = []
    for no, d in result.applications.items():
        causes = d.all_categories
        rows.append({
            "application_no": no, "flagged": str(int(d.flagged)), "error_category": d.error_category,
            "all_categories": ";".join(causes),
            "clauses": " | ".join(K.clause(c) for c in causes),
            "money_effect_by_category": ";".join(f"{c}={d.causes[c]:.2f}" for c in causes),
            "billed_total": str(d.billed_total), "line_sum": str(d.line_sum),
            "expected_total": str(d.expected_total), "difference": str(d.expected_total - d.billed_total),
            "adjustment_31A_due": f"{d.adjustment_due:.2f}", "retention_release_45A_due": f"{d.release_due:.2f}",
            "confidence": f"{d.confidence:.2f}",
            "flagged_lines": ";".join(flagged_lines[no]),
            "notes": " | ".join(d.notes),
        })
    return rows
