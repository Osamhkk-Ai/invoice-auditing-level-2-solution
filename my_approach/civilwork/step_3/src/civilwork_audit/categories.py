"""Error categories: the clause each relies on, its evidence class, and the fixed
tie-break order used when two categories have the same money effect (architecture C6).

Confidence is assigned by evidence class (architecture C7). The values are not
calibrated: there are no labels to calibrate against.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    name: str
    clause: str
    evidence_class: str


_C = Category
CATEGORIES: list[Category] = [
    _C("wrong_contract_ref", "Agreement p1 (check 1)", "procedural"),
    _C("submitted_before_period_end", "Cl 41 p8", "explicit"),
    _C("submitted_late", "Cl 41 p8 (21 days)", "procedural"),
    _C("total_arithmetic", "Cl 43 p8", "explicit"),
    _C("retention_or_net_arithmetic", "Cl 45 p8; Cl 45A p32", "explicit"),
    _C("work_before_commencement", "Agreement p1", "explicit"),
    _C("work_after_term", "A2 s2.1 p42; A1 s1.1 p40", "explicit"),
    _C("line_outside_period", "Cl 41 p8", "explicit"),
    _C("duplicate_measurement", "Cl 44 p8", "cross"),
    _C("duplicate_week", "Cl 44 p8 (Q2 alternative)", "cross"),
    _C("record_reused", "Cl 44 p8; Cl 47 p8", "cross"),
    _C("record_missing", "Cl 46 p8; Sch 5 p27", "record"),
    _C("record_wrong_series", "Cl 47A p33; Sch 5 p27", "record"),
    _C("record_not_countersigned", "Cl 47 p8; P22 p14", "record"),
    _C("record_not_signed", "Cl 47 p8; P22 p14", "record"),
    _C("record_mismatch", "Cl 47 p8; Cl 47A p33", "record"),
    _C("record_unrecognised", "Cl 47A p33 (manual review)", "query"),
    _C("week_under_five_days", "Cl 47A p33; Sch 5 p27", "record"),
    _C("unit_not_per_schedule", "Cl 26 p6", "explicit"),
    _C("qty_above_survey_tolerance", "Cl 33A p32", "record"),
    _C("chargeable_hour_not_deducted", "Cl 6A p32", "record"),
    _C("qty_above_record", "Cl 46 p8; guideline check 5", "record"),
    _C("daily_limit_exceeded", "Cl 31 p6; Sch 4 Pt 4 p26", "cross"),
    _C("mutually_exclusive_item", "P19 p13; Cl 32 p6; Sch 4 Pt 5 p26", "cross"),
    _C("traffic_management_during_surfacing", "P21 p13", "cross"),
    _C("work_after_submission", "Agreement p1; Cl 41 p8 (Q3)", "explicit"),
    _C("rate_superseded", "Cl 27 p6; Sch of Variations p38", "rebuild"),
    _C("retro_rate_taken_early", "Cl 31A p32; A3 p43", "rebuild"),
    _C("index_or_fx_month_wrong", "Cl 26A / 29A p32", "rebuild"),
    _C("zone_factor_wrong", "Sch 2 p20; Cl 29 p6", "rebuild"),
    _C("ground_factor_wrong", "Sch 3 p23; Cl 29 p6", "rebuild"),
    _C("ground_factor_after_freeze", "Cl 27A p32", "rebuild"),
    _C("night_uplift_zone_cap", "Cl 27A p32", "rebuild"),
    _C("uplift_not_eligible", "Sch 4 Pt 1-2 p24", "rebuild"),
    _C("rest_day_uplift_wrong_day", "Sch 4 Pt 2 p24; Cl 8 p3", "rebuild"),
    _C("band_not_applied", "Sch 4 Pt 3 pp24-25", "rebuild"),
    _C("discount_omitted", "S2 s2.2 p41; A2 s2.3 p42", "rebuild"),
    _C("discount_early", "S2 s2.2 p41; A2 s2.3 p42", "rebuild"),
    _C("intermediate_rounding", "Cl 28 p6", "rebuild"),
    _C("line_arithmetic", "Cl 28 p6; Cl 42 p8", "explicit"),
    _C("adjustment_31A_omitted", "Cl 31A p32; A3 p43 (Q1)", "adjustment"),
    _C("retention_release_45A_omitted", "Cl 45A p32", "adjustment"),
]
BY_NAME = {c.name: c for c in CATEGORIES}
ORDER = {c.name: i for i, c in enumerate(CATEGORIES)}

CONFIDENCE_BY_CLASS = {
    "explicit": 0.93, "rebuild": 0.88, "record": 0.85, "cross": 0.82,
    "procedural": 0.75, "adjustment": 0.60, "query": 0.50}
CONFIDENCE_NOT_FLAGGED = 0.90


def clause(name: str) -> str:
    return BY_NAME[name].clause


def confidence(causes: set[str]) -> float:
    """The confidence of the strongest cause (architecture C7)."""
    if not causes:
        return CONFIDENCE_NOT_FLAGGED
    return max(CONFIDENCE_BY_CLASS[BY_NAME[c].evidence_class] for c in causes)
