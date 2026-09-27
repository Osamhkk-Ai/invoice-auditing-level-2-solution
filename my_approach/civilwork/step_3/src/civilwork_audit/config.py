"""Audit configuration: the accepted decisions (Q1-Q3) and their configurable alternatives.

The defaults reproduce the decisions the project owner accepted on 2026-09-27
(civilwork_audit_architecture_final.md, Part D1). Every alternative is still selectable
so that sensitivity runs can be regenerated (see ``sensitivity.py``).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP


@dataclass(frozen=True)
class PricingOptions:
    """Switches for the Clause 27 build-up. Defaults are the contract reading; the others
    exist for the ablation table only."""
    zone: bool = True
    ground: bool = True
    ground_freeze: bool = True
    ground_freeze_from: str = "2025-09-28"          # Cl 27A "after 27 September 2025"
    night: bool = True
    night_zone_cap: bool = True                      # Cl 27A
    rest_day: bool = True
    bands: bool = True
    band_year_reset: bool = True                     # Cl 3A
    band_order: str = "work_date"                    # Cl 30: date, then application, then line
    discount: bool = True
    index: bool = True                               # Cl 29A
    usd: bool = True                                 # Cl 26A
    retro_rule: str = "before_issue"                 # Cl 31A; "on_or_before_issue" | "off"
    disabled_instruments: frozenset[str] = frozenset()   # rates only, e.g. {"S1"}
    final_rounding: str = ROUND_HALF_UP              # Cl 28
    conversion_rounding: str = ROUND_HALF_EVEN       # Cl 26A / 29A


@dataclass(frozen=True)
class AuditConfig:
    # Q1: carrier of the Clause 31A adjustment. "after_issue" = A3 p43 (first application
    # submitted strictly after the issue date -> PA-00443). "all_candidates" flags every
    # application submitted on the issue date plus the first after it. Any application
    # number may also be given explicitly.
    a31_carrier: str = "after_issue"
    # Basis of the 31A amount: "all_valued" (all pre-issue lines) or "exclude_misvalued"
    # (drop lines not billed at the pre-issue contract rate). Reporting only.
    a31_basis: str = "all_valued"
    # Q2: repeated dewatering / haul-road week with different work dates. None = not a
    # Clause 44 duplicate (accepted). Alternatives: "A16_same_app", "A16", "A16+E54".
    weekly_duplicate: str | None = None
    # Q3: value only work executed by the submission date (accepted).
    zero_after_submission: bool = True
    # Q3: procedural defects never zero a total ("none", accepted). Alternatives: "all"
    # (every procedural defect -> 0) and "cl43_and_early" (Cl 43 arithmetic and
    # submitted-before-period-end -> 0).
    procedural_zero: str = "none"
    # Sensitivity readings resolved by text (architecture D2 / C2)
    band_count_basis: str = "billed"                 # or "supported"
    p19_window_days: tuple[int, ...] = (0, 1, 2)     # P19 "within two days of"
    pricing: PricingOptions = field(default_factory=PricingOptions)

    def with_(self, **changes) -> "AuditConfig":
        return replace(self, **changes)


ACCEPTED = AuditConfig()
