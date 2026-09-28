"""Write the drilling submission rows and the line / invoice audit trails.

The submission part has exactly the template's six columns, one row per ``MDS-`` invoice in
template order, money in integer cents. ``validate_rows`` is the same schema guard the civil-works
merger applies.
"""
from __future__ import annotations

import csv
import os
import re
from decimal import Decimal

from . import categories as K
from .audit import AuditResult
from .money import to_cents

SUBMISSION_COLUMNS = ["invoice_id", "flagged", "error_category", "expected_total_cents",
                      "billed_total_cents", "confidence"]


class SubmissionError(ValueError):
    pass


def submission_rows(result: AuditResult, drilling_ids: list[str]) -> list[dict[str, str]]:
    if set(drilling_ids) != set(result.invoices) or len(drilling_ids) != len(set(drilling_ids)):
        raise SubmissionError("template drilling ids and invoices differ")
    rows = []
    for n in drilling_ids:
        d = result.invoices[n]
        rows.append({
            "invoice_id": n,
            "flagged": "1" if d.flagged else "0",
            "error_category": d.error_category if d.flagged else "",
            "expected_total_cents": str(to_cents(d.expected_total)),
            "billed_total_cents": str(to_cents(d.billed_total)),
            "confidence": f"{d.confidence:.2f}",
        })
    return rows


def validate_rows(rows: list[dict[str, str]], expected_ids: list[str]) -> None:
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
        if r["flagged"] == "0" and r["expected_total_cents"] != r["billed_total_cents"]:
            raise SubmissionError(f"{r['invoice_id']}: unflagged but expected != billed")
        if not Decimal(0) <= Decimal(r["confidence"]) <= Decimal(1):
            raise SubmissionError(f"{r['invoice_id']}: confidence outside [0, 1]")


def write_csv(path: str, rows: list[dict], columns: list[str] | None = None) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns or list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def line_audit_rows(result: AuditResult, only_exceptions: bool = False) -> list[dict[str, str]]:
    """One row per priced line. Clean lines carry the same fields, so the trail is complete."""
    rows = []
    for ref in sorted(result.lines):
        r = result.lines[ref]
        if only_exceptions and not (r.reasons or r.delta):
            continue
        ln = r.line
        diag = r.diagnosis
        rows.append({
            "line_ref": ref, "invoice_no": ln.invoice_no, "service_date": ln.service_date.isoformat(),
            "code": ln.code, "section_billed": ln.section, "status_billed": ln.status,
            "depths": f"{ln.depth_from}-{ln.depth_to}" if ln.depth_from is not None else "",
            "report": r.report.file if r.report else "", "report_ref": ln.report_ref,
            "section_report": r.report.section if r.report else "", "status_report": r.report.status if r.report else "",
            "billed_qty": str(ln.quantity), "billed_rate": str(ln.rate), "billed_amount": str(ln.amount),
            "supported_qty": "" if r.supported_qty is None else str(r.supported_qty),
            "evidence_basis": r.basis, "paid_qty": str(r.paid_qty),
            "expected_rate": "" if not r.rate or r.rate.rate is None else str(r.rate.rate),
            "rate_build_up": r.rate.describe() if r.rate else "",
            "expected_amount": str(r.expected_amount), "billed_minus_expected": str(r.delta),
            "expected_amount_cents": str(to_cents(r.expected_amount)), "billed_amount_cents": str(to_cents(ln.amount)),
            "reasons": ";".join(r.reasons), "categories": ";".join(r.categories),
            "clauses": " | ".join(K.clause(x) for x in r.reasons),
            "diagnosis": diag[0] if diag else "",
            "notes": " | ".join(r.notes + ([f"billed rate reproduced by: {'; '.join(diag[:3])}"] if diag else [])),
            "warnings": " | ".join(r.warnings),
            "policy": _policy(result, r),
        })
    return rows


def _policy(result: AuditResult, r) -> str:
    cfg = result.config
    out = []
    if "report_unsigned" in r.reasons:
        out.append(f"unsigned_policy={cfg.unsigned_policy}")
    if r.line.code == "PD-210":
        out.append(f"pd210_rule={cfg.evidence.pd210_rule}")
    if r.line.code in ("DD-120", "RM-530"):
        out.append(f"chargeable_hour={cfg.evidence.chargeable_hour}")
    return ";".join(out)


def invoice_audit_rows(result: AuditResult) -> list[dict[str, str]]:
    rows = []
    for n, d in result.invoices.items():
        I = d.invoice
        cats = d.all_categories
        flagged_lines = [r.line.line_ref for r in d.lines if r.reasons or r.delta]
        rows.append({
            "invoice_no": n, "well": I.well, "well_class": I.well_class, "period": f"{I.period_start}..{I.period_end}",
            "invoice_date": I.invoice_date.isoformat(), "flagged": str(int(d.flagged)),
            "error_category": d.error_category, "all_categories": ";".join(cats),
            "money_effect_by_category": ";".join(f"{c}={d.causes[c]:.2f}" for c in cats),
            "invoice_reasons": ";".join(d.reasons),
            "clauses": " | ".join(K.clause(x) for x in d.reasons),
            "billed_net": str(I.net_amount), "billed_vat": str(I.vat_amount), "billed_adjustment": str(I.adjustment),
            "billed_total": str(I.invoice_total),
            "expected_services": str(d.services), "expected_discount": str(d.discount), "expected_net": str(d.net),
            "expected_vat": str(d.vat), "expected_adjustment": str(d.adjustment),
            "expected_total": str(d.expected_total), "expected_minus_billed": str(d.expected_total - d.billed_total),
            "expected_total_cents": str(to_cents(d.expected_total)), "billed_total_cents": str(to_cents(d.billed_total)),
            "confidence": f"{d.confidence:.2f}", "exception_lines": ";".join(flagged_lines),
            "notes": " | ".join(d.notes), "warnings": " | ".join(d.warnings),
        })
    return rows
