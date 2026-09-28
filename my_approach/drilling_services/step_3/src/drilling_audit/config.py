"""Audit configuration: the production reading and every alternative that the sensitivity runs use.

``PRODUCTION`` is the Step 2 baseline plus the owner's working choices (see the decision log):

* A3 carrier ``on_or_after`` -> MDS-01625 (Clause 36A wording; the only reading with a single first
  invoice).
* The A3 adjustment is part of the audited ``invoice_total`` and carries no VAT.
* A report without both signatures supports no charge on its day (Clause 15; guideline checks 2, 4).
* PD-210 on performance-drilled days identified by the "performance engineer" proxy.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class PricingOptions:
    no_section_factor_on_standby: bool = True     # Clause 17B; False = Clause 18 literal
    no_class_factor_on_pd210: bool = True         # Clause 17B; False = Schedule 2 note
    apply_index: bool = True                      # Clause 17A / Schedule 2C
    later_issued_governs: bool = True             # instruments in issue order; False = latest effective date
    discount_fold: str = "none"                   # S2 2.2 / A2 2.3 own rounded step; "standby" | "any" = folded
                                                  # into the preceding (standby / any) step before its rounding
    retro_only_from_issue: bool = True            # Clause 36A; False = A3 also reprices pre-issue invoices
    lih_from_sar: bool = True                     # Clause 31A / Sch.2D; False = Schedule 6 USD
    half_up: bool = False                         # Clause 17 half-even; True = alternative


@dataclass(frozen=True)
class EvidenceOptions:
    chargeable_hour: str = "per_day"              # Clause 21A: "per_day" | "per_run" | "off"
    minimum_order: str = "minus_then_minimum"     # max(h-1, 6) | "minimum_then_minus" = max(h, 6) - 1
    dd120_minimum: int = 6                        # Clause 21
    pd210_rule: str = "perf_engineer"             # "perf_engineer" | "section_only" | "perf_tools"
    lwd_map: str = "appendix_g"                   # "appendix_g" | "literal"
    apply_daily_limits: bool = True               # Clause 22 / Sch.3 Pt5
    metre_tolerance: bool = True                  # Clause 25A
    evidence_day: str = "service_date"            # "service_date" | "report_ref"


@dataclass(frozen=True)
class AuditConfig:
    # Clause 36A / A3 carrier: "on_or_after" (36A, MDS-01625) | "strictly_after_first_number" (A3,
    # lowest invoice number among the three on 2026-08-18) | an explicit invoice number.
    a3_carrier: str = "on_or_after"
    # Is the adjustment part of the audited invoice_total? "in_total" | "separate" (flag only).
    adjustment_treatment: str = "in_total"
    vat_on_adjustment: bool = False
    # Quantity the A3 difference is measured on: "supported" (the audited quantity) | "billed".
    a3_basis: str = "supported"
    # Unsigned report: "zero_day" (no charge on the day) | "zero_schedule5" (only the Clause 37
    # codes are unpayable) | "flag_only" (procedural flag, amounts kept).
    unsigned_policy: str = "zero_day"
    pricing: PricingOptions = field(default_factory=PricingOptions)
    evidence: EvidenceOptions = field(default_factory=EvidenceOptions)

    def with_(self, **changes) -> "AuditConfig":
        return replace(self, **changes)

    def with_pricing(self, **changes) -> "AuditConfig":
        return replace(self, pricing=replace(self.pricing, **changes))

    def with_evidence(self, **changes) -> "AuditConfig":
        return replace(self, evidence=replace(self.evidence, **changes))


PRODUCTION = AuditConfig()
