"""Ablation of pricing rules and the Q1-Q3 / reading scenarios, from one baseline.

Ablation: how many billed line amounts the build-up reproduces when one rule is
removed or changed. A rule the billing applied loses lines when removed.
Scenarios: how the flagged set and the expected totals move under each alternative.
"""
from __future__ import annotations

from dataclasses import replace
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

from .config import ACCEPTED, PricingOptions
from .loader import Inputs
from .pipeline import AuditResult, run_audit
from .pricing import price_lines
from .records import Record

ABLATIONS: list[tuple[str, dict]] = [
    ("without 27A ground freeze", dict(ground_freeze=False)),
    ("without Sch 4 Pt 3 bands", dict(bands=False)),
    ("bands not reset at Contract Year 2 (3A)", dict(band_year_reset=False)),
    ("without 26A USD conversion", dict(usd=False)),
    ("without 29A indexation", dict(index=False)),
    ("without S2/A2 discount", dict(discount=False)),
    ("without rest-day uplift", dict(rest_day=False)),
    ("night uplift also in Z3/Z4 (no 27A cap)", dict(night_zone_cap=False)),
    ("without 31A (reprice pre-issue applications)", dict(retro_rule="off")),
    ("31A boundary 'on or before' issue day", dict(retro_rule="on_or_before_issue")),
    ("freeze from 27 Sep 2025", dict(ground_freeze_from="2025-09-27")),
    ("freeze from 29 Sep 2025", dict(ground_freeze_from="2025-09-29")),
    ("band order by application date", dict(band_order="application_date")),
    ("band tie-break by reverse application no.", dict(band_order="work_date_reverse_application")),
    ("final rounding half-even (not Cl 28 half-up)", dict(final_rounding=ROUND_HALF_EVEN)),
    ("conversion rounding half-up (not 26A/29A half-even)", dict(conversion_rounding=ROUND_HALF_UP)),
    ("without Supplement No. 1 rates", dict(disabled_instruments=frozenset({"S1"}))),
    ("without Amendment No. 1 rates", dict(disabled_instruments=frozenset({"A1"}))),
    ("without Supplement No. 2 rate", dict(disabled_instruments=frozenset({"S2"}))),
    ("without Amendment No. 2 monthly E.54.010", dict(disabled_instruments=frozenset({"A2"}))),
    ("without zone factors", dict(zone=False)),
    ("without ground factors", dict(ground=False)),
    ("without night uplift", dict(night=False)),
]

SCENARIOS: list[tuple[str, dict]] = [
    ("accepted baseline (Q1 after issue, Q2 not duplicate, Q3 supported at submission)", {}),
    ("Q1: 31A carrier PA-00006", dict(a31_carrier="PA-00006")),
    ("Q1: 31A carrier PA-00023", dict(a31_carrier="PA-00023")),
    ("Q1: 31A carrier PA-00380", dict(a31_carrier="PA-00380")),
    ("Q1: flag all four candidates", dict(a31_carrier="all_candidates")),
    ("Q2: repeated A.16.010 week within one application only", dict(weekly_duplicate="A16_same_app")),
    ("Q2: repeated A.16.010 week disallowed", dict(weekly_duplicate="A16")),
    ("Q2: repeated A.16.010 and E.54.010 week disallowed", dict(weekly_duplicate="A16+E54")),
    ("Q3: keep lines executed after submission", dict(zero_after_submission=False)),
    ("Q3: every procedural defect -> expected 0", dict(procedural_zero="all")),
    ("Q3: Cl 43 and submitted-early -> expected 0", dict(procedural_zero="cl43_and_early")),
    ("reading: bands counted on supported quantity", dict(band_count_basis="supported")),
    ("reading: P19 window days 1..2 only", dict(p19_window_days=(1, 2))),
    ("reading: P19 window days 0..3", dict(p19_window_days=(0, 1, 2, 3))),
]


def matched_lines(inputs: Inputs, opts: PricingOptions) -> set[str]:
    prices = price_lines(inputs.lines, inputs.applications, opts)
    return {ln.line_ref for ln in inputs.lines if prices[ln.line_ref].amount == ln.amount}


def ablation(inputs: Inputs) -> tuple[set[str], list[dict[str, str]]]:
    base = matched_lines(inputs, PricingOptions())
    rows = []
    for name, change in ABLATIONS:
        s = matched_lines(inputs, replace(PricingOptions(), **change))
        rows.append(dict(reading=name, matched=str(len(s)), lost=str(len(base - s)),
                         gained=str(len(s - base)), gained_lines=";".join(sorted(s - base))))
    return base, rows


def scenarios(inputs: Inputs, records: dict[str, Record], baseline: AuditResult) -> list[dict[str, str]]:
    base_flagged = {k for k, d in baseline.applications.items() if d.flagged}
    rows = []
    for name, change in SCENARIOS:
        res = baseline if not change else run_audit(inputs, records, ACCEPTED.with_(**change))
        flagged = {k for k, d in res.applications.items() if d.flagged}
        changed = sorted(k for k, d in res.applications.items()
                         if d.expected_total != baseline.applications[k].expected_total)
        delta = sum((res.applications[k].expected_total - baseline.applications[k].expected_total
                     for k in changed), Decimal(0))
        rows.append(dict(scenario=name, flagged=str(len(flagged)),
                         added=";".join(sorted(flagged - base_flagged)),
                         removed=";".join(sorted(base_flagged - flagged)),
                         expected_total_changed=";".join(changed), expected_delta_sar=str(delta)))
    return rows
