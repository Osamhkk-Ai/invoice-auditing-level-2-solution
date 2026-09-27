"""Per-line eligibility, record matching and supported quantity (checks 2, 4, 5 and 6).

This stage looks at one line at a time. Rules that depend on other lines (duplicates,
daily limits, exclusions) run afterwards in ``cross_checks`` in the global order.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

from . import contract as C
from .categories import clause
from .config import AuditConfig
from .loader import Application, Line
from .records import Record


@dataclass
class Finding:
    category: str
    detail: str
    zeroes_line: bool = False

    @property
    def clause(self) -> str:
        return clause(self.category)


@dataclass
class LineAssessment:
    line: Line
    evidence_status: str = "not_required"    # not_required | ok | <problem codes joined by +>
    record_qty: int | None = None
    record_item: str | None = None
    supported_qty: int = 0
    quantity_basis: str = "as billed"
    findings: list[Finding] = field(default_factory=list)

    def zero(self, category: str, detail: str) -> None:
        self.findings.append(Finding(category, detail, zeroes_line=True))
        self.supported_qty = 0

    def reduce(self, category: str, detail: str, new_qty: int) -> None:
        self.findings.append(Finding(category, detail))
        self.supported_qty = new_qty

    @property
    def categories(self) -> list[str]:
        return list(dict.fromkeys(f.category for f in self.findings))


def _record_problems(ln: Line, rec: Record) -> list[tuple[str, str]]:
    """(category, detail) for every way the record fails to evidence the line."""
    out: list[tuple[str, str]] = []
    if rec.pattern_id == "":
        out.append(("record_unrecognised", f"{rec.ref}: body not in the 26 known patterns: {rec.body!r}"))
    elif rec.item is None:
        out.append(("record_unrecognised", f"{rec.ref}: {rec.item_reason} fits two items"))
    elif rec.item != ln.item_code:
        out.append(("record_mismatch", f"{rec.ref} describes {rec.item} ({rec.item_reason}), line is {ln.item_code}"))
    if rec.area != ln.site:
        out.append(("record_mismatch", f"{rec.ref} area {rec.area!r} != {ln.site!r}"))
    if rec.date is None:
        out.append(("record_mismatch", f"{rec.ref} has no readable date"))
    elif ln.item_code in C.WEEKLY_RECORD_ITEMS:
        if not rec.date <= ln.work_date <= rec.date + dt.timedelta(days=6):
            out.append(("record_mismatch", f"{rec.ref} week beginning {rec.date} does not contain {ln.work_date}"))
        if len(rec.week_days) < C.WEEKLY_MIN_DAYS:
            out.append(("week_under_five_days", f"{rec.ref} shows {len(rec.week_days)} days worked"))
    elif rec.date != ln.work_date:
        out.append(("record_mismatch", f"{rec.ref} dated {rec.date} != work date {ln.work_date}"))
    if rec.ground and ln.ground and rec.ground != ln.ground:
        out.append(("record_mismatch", f"{rec.ref} ground {rec.ground} != line {ln.ground}"))
    if not rec.signed:
        out.append(("record_not_signed", f"{rec.ref} has no foreman signature"))
    if not rec.countersigned:
        out.append(("record_not_countersigned", f"{rec.ref} has no Engineer's representative countersignature"))
    return out


def _record_quantity(la: LineAssessment, rq: int) -> None:
    """Supported quantity from a usable record (A3.4-A3.7)."""
    ln, billed = la.line, la.line.quantity
    if ln.item_code in C.HOURLY_ITEMS:                                   # Cl 6A
        cap = max(rq - 1, 0)
        la.quantity_basis = f"record {rq} h - 1 (Cl 6A) = {cap}"
        if billed > cap:
            la.reduce("chargeable_hour_not_deducted", f"billed {billed} h, record {rq} h, chargeable {cap}", cap)
    elif ln.item_code in C.SURVEYED_ITEMS:                               # Cl 33 / 33A
        limit = Decimal(rq) * (1 + C.SURVEY_TOLERANCE)
        la.quantity_basis = f"survey {rq}; payable as measured up to {limit} (Cl 33A)"
        if Decimal(billed) > limit:
            la.reduce("qty_above_survey_tolerance", f"billed {billed} > survey {rq} + 2 %", rq)
    else:                                                                # Cl 46; check 5
        la.quantity_basis = f"record {rq}"
        if billed > rq:
            la.reduce("qty_above_record", f"billed {billed} > record {rq}", rq)


def assess_line(ln: Line, app: Application, records: dict[str, Record], cfg: AuditConfig) -> LineAssessment:
    la = LineAssessment(ln, supported_qty=ln.quantity)
    # Check 6 / Cl 26: a quantity in the wrong unit is rejected in its entirety.
    sched_unit = C.SCHEDULE_1[ln.item_code][0]
    if ln.unit != sched_unit:
        la.zero("unit_not_per_schedule", f"billed in {ln.unit!r}; Schedule 1 unit is {sched_unit!r}")
    # Check 4 / Cl 46-47A: the record required by Schedule 5.
    series = C.RECORD_SERIES.get(ln.item_code)
    if series:
        rec = records.get(ln.record_ref) if ln.record_ref else None
        if not ln.record_ref:
            la.evidence_status = "missing_reference"
            la.zero("record_missing", f"no record reference; Schedule 5 requires a {series} record")
        elif rec is None:
            la.evidence_status = "file_missing"
            la.zero("record_missing", f"{ln.record_ref} cited but not delivered")
        elif ln.record_ref[:2] != series:
            la.evidence_status = "wrong_series"
            la.zero("record_wrong_series", f"{ln.record_ref} is a {ln.record_ref[:2]} record; {ln.item_code} needs {series}")
        else:
            problems = _record_problems(ln, rec)
            la.record_qty, la.record_item = rec.quantity, rec.item
            if problems:
                la.evidence_status = "+".join(dict.fromkeys(c for c, _ in problems))
                for cat, detail in problems:
                    la.zero(cat, detail)
            else:
                la.evidence_status = "ok"
                if la.supported_qty and rec.quantity is not None:
                    _record_quantity(la, rec.quantity)
    # Check 2: the contract was live on the work date.
    if ln.work_date > C.COMPLETION:
        la.zero("work_after_term", f"work {ln.work_date} after extended completion {C.COMPLETION}")
    if ln.work_date < C.COMMENCEMENT:
        la.zero("work_before_commencement", f"work {ln.work_date} before commencement {C.COMMENCEMENT}")
    # Check 3 / Cl 41: no item outside the stated period.
    if not app.period_from <= ln.work_date <= app.period_to:
        la.zero("line_outside_period", f"work {ln.work_date} outside stated period {app.period_from}..{app.period_to}")
    # Q3: only work executed by the submission date is valued (Agreement p1).
    if ln.work_date > app.application_date:
        detail = f"work {ln.work_date} after submission {app.application_date}"
        if cfg.zero_after_submission:
            la.zero("work_after_submission", detail)
        else:
            la.findings.append(Finding("work_after_submission", detail + " (valued under Q3 alternative)"))
    return la
