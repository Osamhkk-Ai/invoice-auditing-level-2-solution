"""The full civil-works audit in one fixed order (architecture C1).

    [1] load + validate CSVs          [2] parse records
    [3] per-line eligibility/evidence [4] cross-application checks (global order)
    [5] price every line (global band order)
    [6] expected line amount = supported quantity at the contract build-up
    [7] residual diagnosis            [8] 31A / 45A plan, application decisions
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from .config import ACCEPTED, AuditConfig
from .cross_checks import apply_cross_checks
from .decisions import AdjustmentPlan, AppDecision, decide_application, plan_adjustments
from .diagnosis import decompose, price_categories
from .evidence import LineAssessment, assess_line
from .loader import Inputs, Line
from .pricing import LinePrice, price_lines
from .records import Record


@dataclass
class LineResult:
    line: Line
    assessment: LineAssessment
    price: LinePrice                  # contract price at the billed quantity
    expected_amount: Decimal
    price_categories: list[str]
    diagnosis: list[str] | None

    @property
    def delta(self) -> Decimal:
        return self.expected_amount - self.line.amount

    @property
    def categories(self) -> list[str]:
        return list(dict.fromkeys(self.price_categories + self.assessment.categories))


@dataclass
class AuditResult:
    config: AuditConfig
    lines: dict[str, LineResult]              # in input order
    applications: dict[str, AppDecision]      # in input order
    plan: AdjustmentPlan
    records: dict[str, Record]


_DIAGNOSIS_CACHE: dict[tuple, list[str] | None] = {}


def run_audit(inputs: Inputs, records: dict[str, Record], cfg: AuditConfig = ACCEPTED) -> AuditResult:
    apps = inputs.applications
    assessments = {ln.line_ref: assess_line(ln, apps[ln.application_no], records, cfg) for ln in inputs.lines}
    apply_cross_checks(assessments, cfg)

    band_qty = ({ref: la.supported_qty for ref, la in assessments.items()}
                if cfg.band_count_basis == "supported" else None)
    prices = price_lines(inputs.lines, apps, cfg.pricing, band_qty)

    results: dict[str, LineResult] = {}
    for ln in inputs.lines:
        la, p = assessments[ln.line_ref], prices[ln.line_ref]
        expected = p.amount_for(la.supported_qty)
        cats: list[str] = []
        diag = None
        if p.amount != ln.amount:
            key = (ln, p)
            if key not in _DIAGNOSIS_CACHE:
                _DIAGNOSIS_CACHE[key] = decompose(ln, p)
            diag = _DIAGNOSIS_CACHE[key]
            cats = price_categories(ln, apps[ln.application_no], p, diag)
        r = LineResult(ln, la, p, expected, cats, diag)
        if r.delta != 0 and not r.categories:
            raise AssertionError(f"{ln.line_ref}: expected differs from billed with no category")
        results[ln.line_ref] = r

    new_rate_prices = price_lines(inputs.lines, apps, replace(cfg.pricing, retro_rule="off"), band_qty)
    plan = plan_adjustments(inputs, cfg, prices, new_rate_prices)
    decisions = {
        no: decide_application(app, [results[l.line_ref] for l in inputs.lines_by_app[no]], plan, cfg)
        for no, app in apps.items()}
    return AuditResult(cfg, results, decisions, plan, records)
