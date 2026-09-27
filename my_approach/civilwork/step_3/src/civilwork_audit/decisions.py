"""Application-level decisions (checks 1, 3, 11 and 12; Clauses 31A, 43, 45, 45A).

``expected_total`` is the measured total the contract supports: the sum of expected
line amounts (Cl 43; Cl 45A separates the measured total from the 31A adjustment and
the 45A release). An application is flagged when the total differs, when any line or
procedural breach exists, or when a required 31A/45A entry is wrong, so a flagged
application can have expected == billed.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_FLOOR, Decimal

from . import categories as K
from . import contract as C
from .config import AuditConfig
from .loader import Application, Inputs

CENT = Decimal("0.01")


def floor_cent(x: Decimal) -> Decimal:
    return x.quantize(CENT, ROUND_FLOOR)


def to_cents(x: Decimal) -> int:
    cents = x * 100
    if cents != cents.to_integral_value():
        raise ValueError(f"{x} is not a whole number of halalas")
    return int(cents)


@dataclass
class AdjustmentPlan:
    """What Clauses 31A and 45A require, contract-wide."""
    a31_instrument: str
    a31_amount: Decimal
    a31_lines: list[str]
    a31_carriers: list[str]
    a31_note: str
    a45_carrier: str | None
    a45_basis: Decimal
    a45_amount: Decimal


@dataclass
class AppDecision:
    application_no: str
    billed_total: Decimal
    line_sum: Decimal
    expected_total: Decimal
    causes: dict[str, Decimal]                  # category -> money effect (abs)
    adjustment_due: Decimal
    release_due: Decimal
    flagged: bool
    error_category: str
    confidence: float
    notes: list[str] = field(default_factory=list)

    @property
    def all_categories(self) -> list[str]:
        return sorted(self.causes, key=lambda c: K.ORDER[c])


def choose_a31_carriers(apps: dict[str, Application], issued: dt.date, cfg: AuditConfig) -> tuple[list[str], str]:
    after = sorted((a.application_date, no) for no, a in apps.items() if a.application_date > issued)
    on_day = sorted(no for no, a in apps.items() if a.application_date == issued)
    first_after = [no for d, no in after if d == after[0][0]] if after else []
    note = (f"Cl 31A 'on or after' -> {on_day + first_after[:1]}; A3 'after' -> {first_after}. "
            f"Q1 rule: {cfg.a31_carrier}")
    if cfg.a31_carrier == "after_issue":
        return first_after, note
    if cfg.a31_carrier == "all_candidates":
        return on_day + first_after, note
    if cfg.a31_carrier in apps:
        return [cfg.a31_carrier], note
    raise ValueError(f"unknown a31_carrier {cfg.a31_carrier!r}")


def plan_adjustments(inputs: Inputs, cfg: AuditConfig, contract_price, new_rate_price) -> AdjustmentPlan:
    """31A: the rate difference on pre-issue work, priced at billed quantity with the
    same band position; 45A: half the retention held on all earlier applications."""
    apps = inputs.applications
    ins = C.A3
    lines, amount = [], Decimal(0)
    for ln in inputs.lines:
        app = apps[ln.application_no]
        if app.application_date >= ins.issued:
            continue
        if not any(rc.item == ln.item_code and ln.work_date >= rc.effective for rc in ins.rates):
            continue
        lines.append(ln.line_ref)
        if cfg.a31_basis == "exclude_misvalued" and contract_price[ln.line_ref].amount != ln.amount:
            continue
        amount += new_rate_price[ln.line_ref].amount - contract_price[ln.line_ref].amount
    carriers, note = choose_a31_carriers(apps, ins.issued, cfg)
    after = sorted((a.application_date, no) for no, a in apps.items() if a.application_date > C.COMPLETION)
    carrier45 = after[0][1] if after else None
    basis = Decimal(0)
    if carrier45:
        cutoff = apps[carrier45].application_date
        basis = sum((a.retention for a in apps.values() if a.application_date < cutoff), Decimal(0))
    return AdjustmentPlan(ins.name, amount, lines, carriers, note, carrier45, basis, floor_cent(basis / 2))


def decide_application(app: Application, line_results: list, plan: AdjustmentPlan, cfg: AuditConfig) -> AppDecision:
    billed = app.application_total
    line_sum = sum((r.line.amount for r in line_results), Decimal(0))
    expected = sum((r.expected_amount for r in line_results), Decimal(0))
    causes: dict[str, Decimal] = defaultdict(Decimal)
    for r in line_results:
        for cat in r.categories:
            causes[cat] += abs(r.delta)
    notes: list[str] = []
    procedural: list[str] = []
    # Check 1: contract reference and issuer.
    if app.contract_ref != C.CONTRACT_REF or app.subcontractor != C.SUBCONTRACTOR:
        procedural.append("wrong_contract_ref")
        notes.append(f"contract_ref {app.contract_ref!r} / issuer {app.subcontractor!r}")
    # Check 3 / Cl 41: after the period closed, within 21 days.
    if app.application_date < app.period_to:
        procedural.append("submitted_before_period_end")
        notes.append(f"submitted {app.application_date} before period end {app.period_to}")
    lag = (app.application_date - app.period_to).days
    if lag > C.SUBMISSION_WINDOW_DAYS:
        procedural.append("submitted_late")
        notes.append(f"submitted {lag} days after period end (limit {C.SUBMISSION_WINDOW_DAYS})")
    # Check 11 / Cl 43: total = sum of line amounts.
    if billed != line_sum:
        procedural.append("total_arithmetic")
        causes["total_arithmetic"] += abs(billed - line_sum)
        notes.append(f"billed total {billed} != sum of lines {line_sum}")
    # Cl 45 / 45A: retention and net on the application's own figures.
    exp_retention = floor_cent(billed * C.RETENTION_RATE)
    exp_net = billed + app.adjustment - app.retention + app.retention_released
    if app.retention != exp_retention or app.net_payable != exp_net:
        procedural.append("retention_or_net_arithmetic")
        notes.append(f"retention {app.retention} (expected {exp_retention}); net {app.net_payable} (expected {exp_net})")
    for c in procedural:
        causes.setdefault(c, Decimal(0))
    # Cl 40: the stated period should be the first and last work day (recorded, no flag).
    days = [r.line.work_date for r in line_results]
    if (min(days), max(days)) != (app.period_from, app.period_to):
        notes.append(f"Cl 40: stated period {app.period_from}..{app.period_to}, items span {min(days)}..{max(days)}")
    # Q3 alternatives: zero a total for procedural defects.
    if cfg.procedural_zero == "all" and procedural:
        expected = Decimal(0)
    elif cfg.procedural_zero == "cl43_and_early" and {"total_arithmetic", "submitted_before_period_end"} & set(procedural):
        expected = Decimal(0)
    # Cl 31A / 45A entries (not part of the measured total).
    adj_due = plan.a31_amount if app.application_no in plan.a31_carriers else Decimal(0)
    rel_due = plan.a45_amount if app.application_no == plan.a45_carrier else Decimal(0)
    if app.adjustment != adj_due:
        causes["adjustment_31A_omitted"] += Decimal(0)
        notes.append(f"Cl 31A adjustment due {adj_due}, shown {app.adjustment}")
    if app.retention_released != rel_due:
        causes["retention_release_45A_omitted"] += Decimal(0)
        notes.append(f"Cl 45A release due {rel_due}, shown {app.retention_released}")
    flagged = bool(causes) or to_cents(expected) != to_cents(billed)
    primary = min(causes.items(), key=lambda kv: (-kv[1], K.ORDER[kv[0]]))[0] if causes else ""
    conf = K.confidence(set(causes)) if flagged else K.CONFIDENCE_NOT_FLAGGED
    return AppDecision(app.application_no, billed, line_sum, expected, dict(causes), adj_due, rel_due,
                       flagged, primary, conf, notes)
