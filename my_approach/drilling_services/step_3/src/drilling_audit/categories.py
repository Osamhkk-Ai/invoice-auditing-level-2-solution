"""Reason codes, the submission's ``error_category`` vocabulary, clauses relied on, and confidence.

A *reason* is the specific finding on a line or invoice; the *category* is the failure kind written to
the submission. The vocabulary is shared with the civil-works auditor wherever the kind is the same
(``record_missing``, ``line_outside_period``, ``rate_superseded``, ``index_or_fx_month_wrong`` ...), so
one label means one kind across the whole submission. A wrong rate is labelled by the mis-application
that reproduces it (``diagnosis.py``), as civil works does. Confidence values are the Step 2 proposal
(architecture section 5.10) and are not calibrated: there is no labelled data.
"""
from __future__ import annotations

# reason -> (category, clause relied on)
REASONS: dict[str, tuple[str, str]] = {
    # line level
    "unknown_service_code": ("record_unrecognised", "Cl 35 p.8; Sch.1 pp.15-16; guideline check 6"),
    "unit_or_description_wrong": ("unit_not_per_schedule", "Cl 35 p.8"),
    "before_term": ("work_before_commencement", "p.1"),
    "outside_term": ("work_after_term", "p.1; A1 1.1 p.39; A2 2.1 p.41"),
    "outside_invoice_period": ("line_outside_period", "Cl 32 p.8"),
    "no_report_for_day": ("record_missing", "Cl 15 p.5; guideline check 4"),
    "report_unreadable": ("record_unrecognised", "Cl 19A p.35; App. G p.36; guideline 3"),
    "report_unsigned": ("record_not_signed", "Cl 15 p.5; Cl 37 p.8; guideline check 4"),
    "part_B_absent": ("record_missing", "Cl 37 p.8; Sch.5 p.24"),
    "part_C_absent": ("record_missing", "Cl 37 p.8; Sch.5 p.24"),
    "part_D_absent": ("record_missing", "Cl 37 p.8; Sch.5 p.24"),
    "part_E_absent": ("record_missing", "Cl 37 p.8; Sch.5 p.24"),
    "not_supported_by_report": ("charge_not_in_record", "Cl 20-31 pp.6-7; App. G p.36; guideline 2"),
    "not_chargeable_on_status": ("charge_not_in_record", "Cl 20-21 p.6; Sch.3 Pt3-4 pp.20-21"),
    "already_billed": ("duplicate_measurement", "Cl 29 p.7; guideline check 10"),
    "qty_above_report": ("qty_above_record", "Cl 21-30 pp.6-7; Cl 25A p.35; guideline check 5"),
    "rate_differs": ("rate_wrong", "Cl 17-18 p.6; Part IX p.35; Schedules 1-3; instruments pp.37-42"),
    "amount_ne_qty_x_rate": ("line_arithmetic", "Cl 18 p.6"),
    "section_or_status_differs": ("status_or_section_wrong", "Cl 19 p.6"),
    # invoice level
    "contract_ref_wrong": ("wrong_contract_ref", "p.1; guideline check 1"),
    "contractor_wrong": ("wrong_contract_ref", "p.1; guideline check 1"),
    "submitted_before_period_end": ("submitted_before_period_end", "Cl 33 p.8"),
    "submitted_over_30_days": ("submitted_late", "Cl 33 p.8 (30 days)"),
    "period_outside_term": ("work_after_term", "p.1; A2 2.1 p.41; Cl 32 p.8"),
    "discount_DS900_missing": ("invoice_discount_omitted", "Cl 38 p.8; P11 p.11"),
    "discount_DS900_wrong": ("invoice_discount_wrong", "Cl 38 p.8; P11 p.11"),
    "net_ne_sum_of_lines": ("total_arithmetic", "Cl 36 p.8"),
    "vat_wrong": ("total_arithmetic", "Cl 39 p.8"),
    "total_ne_net_plus_vat": ("total_arithmetic", "Cl 40 p.8"),
    "rebuilt_total_differs": ("total_arithmetic", "Cl 36-40 p.8 (rounding of the rebuilt total under the reading)"),
    "a3_adjustment_missing": ("adjustment_36A_omitted", "Cl 36A p.35; A3 p.42"),
    "a3_adjustment_not_due": ("adjustment_36A_wrong", "Cl 36A p.35 ('on no other')"),
    "a3_adjustment_wrong_amount": ("adjustment_36A_wrong", "Cl 36A p.35; A3 p.42"),
}

# Specific labels for a wrong rate, chosen from the diagnosis (the first matching rule wins).
RATE_CATEGORIES = [
    ("lost in hole converted at the", "index_or_fx_month_wrong"),
    ("index", "index_or_fx_month_wrong"),
    ("lost in hole at Schedule 6", "lost_in_hole_value_wrong"),
    ("with a class factor", "class_factor_wrong"),
    ("PD-210 at band rate", "depth_band_wrong"),
    ("standby", "standby_rate_wrong"),
    ("section", "section_factor_wrong"),
    ("class", "class_factor_wrong"),
    ("taken before it started", "discount_early"),
    ("discount omitted", "discount_omitted"),
    ("A3 rate / pre-A3 rate", "rate_superseded"),     # relabelled retro_rate_taken_early before issue
    ("superseded", "rate_superseded"),
    ("S2 monthly", "rate_superseded"),
]

# Order used to break ties between categories with the same money effect (most specific first).
CATEGORY_ORDER = [
    "adjustment_36A_omitted", "adjustment_36A_wrong", "invoice_discount_omitted", "invoice_discount_wrong",
    "total_arithmetic", "line_arithmetic", "retro_rate_taken_early", "rate_superseded", "index_or_fx_month_wrong",
    "section_factor_wrong", "class_factor_wrong", "standby_rate_wrong", "depth_band_wrong", "discount_early",
    "discount_omitted", "lost_in_hole_value_wrong", "rate_wrong", "chargeable_hour_not_deducted",
    "daily_limit_exceeded", "qty_above_record", "duplicate_measurement", "charge_not_in_record", "record_missing",
    "record_not_signed", "unit_not_per_schedule", "status_or_section_wrong", "line_outside_period",
    "work_before_commencement", "work_after_term", "submitted_before_period_end", "submitted_late",
    "wrong_contract_ref", "record_unrecognised",
]
ORDER = {c: i for i, c in enumerate(CATEGORY_ORDER)}

_RATE = ("retro_rate_taken_early", "rate_superseded", "index_or_fx_month_wrong", "section_factor_wrong",
         "class_factor_wrong", "standby_rate_wrong", "depth_band_wrong", "discount_early", "discount_omitted",
         "lost_in_hole_value_wrong", "rate_wrong")
CONFIDENCE = {
    **{c: 0.95 for c in ("line_arithmetic", "invoice_discount_omitted", "invoice_discount_wrong", "total_arithmetic")},
    **{c: 0.90 for c in _RATE},
    **{c: 0.90 for c in ("chargeable_hour_not_deducted", "daily_limit_exceeded", "qty_above_record",
                         "duplicate_measurement", "charge_not_in_record", "record_missing")},
    **{c: 0.85 for c in ("unit_not_per_schedule", "status_or_section_wrong", "line_outside_period",
                         "work_before_commencement", "work_after_term")},
    **{c: 0.80 for c in ("submitted_before_period_end", "submitted_late", "wrong_contract_ref")},
    **{c: 0.70 for c in ("record_not_signed", "adjustment_36A_omitted", "adjustment_36A_wrong")},
    "record_unrecognised": 0.50,
}
CONFIDENCE_LIH_EXCHANGE = 0.85      # lost-in-hole value at another month's exchange rate (section 5.10)
CONFIDENCE_NOT_FLAGGED = 0.90
CONFIDENCE_NOT_FLAGGED_WARNED = 0.75  # an unflagged invoice a documented alternative reading would flag


def category(reason: str) -> str:
    return REASONS[reason][0]


def clause(reason: str) -> str:
    return REASONS[reason][1]


def rate_category(diagnosis: list[str], pre_issue_invoice: bool) -> str:
    """Label a wrong rate by the simplest mechanism that reproduces it."""
    if not diagnosis:
        return "rate_wrong"
    first = diagnosis[0]
    if first.startswith("A3 rate / pre-A3 rate") and pre_issue_invoice:
        return "retro_rate_taken_early"
    for needle, cat in RATE_CATEGORIES:
        if needle in first:
            return cat
    return "rate_wrong"
