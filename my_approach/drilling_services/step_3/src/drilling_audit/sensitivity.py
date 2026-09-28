"""Scenario runs: each switches one reading and reports which invoices and expected totals change.

``MATERIAL`` are readings the contract leaves open (the decision log). ``REJECTED`` are readings the
Step 2 design rejected because they reprice lines that reconcile exactly as billed; they are rerun to
show that the rejection still holds in production.
"""
from __future__ import annotations

from .audit import AuditResult, run_audit
from .config import PRODUCTION, AuditConfig
from .money import to_cents

MATERIAL: dict[str, AuditConfig] = {
    "A3 carrier: strictly after issue (A3 text), first by invoice number": PRODUCTION.with_(a3_carrier="strictly_after_first_number"),
    "A3 carrier: MDS-01631 (another invoice tied on 2026-08-18)": PRODUCTION.with_(a3_carrier="MDS-01631"),
    "A3 carrier: MDS-01645 (another invoice tied on 2026-08-18)": PRODUCTION.with_(a3_carrier="MDS-01645"),
    "A3 adjustment separate from invoice_total (flag only)": PRODUCTION.with_(adjustment_treatment="separate"),
    "A3 adjustment inside net, so VAT charged on it": PRODUCTION.with_(vat_on_adjustment=True),
    "A3 difference measured on billed quantity": PRODUCTION.with_(a3_basis="billed"),
    "Unsigned report: only Clause 37 (Schedule 5) codes unpayable": PRODUCTION.with_(unsigned_policy="zero_schedule5"),
    "Unsigned report: flag only, amounts kept": PRODUCTION.with_(unsigned_policy="flag_only"),
    "PD-210 on every 12-1/4\"/8-1/2\" Operating day": PRODUCTION.with_evidence(pd210_rule="section_only"),
    "PD-210 only with 'bit and reamer' in the hole": PRODUCTION.with_evidence(pd210_rule="perf_tools"),
    "Evidence day from report_ref, not service_date": PRODUCTION.with_evidence(evidence_day="report_ref"),
    "Clause 21A once per BHA run (first day)": PRODUCTION.with_evidence(chargeable_hour="per_run"),
    "Clause 21 minimum applied before 21A (max(h,6)-1)": PRODUCTION.with_evidence(minimum_order="minimum_then_minus"),
    "No Clause 25A metre tolerance": PRODUCTION.with_evidence(metre_tolerance=False),
    "Rate discount folded into the standby step's rounding": PRODUCTION.with_pricing(discount_fold="standby"),
}
REJECTED: dict[str, AuditConfig] = {
    "Section factor kept on Standby (Clause 18 literal)": PRODUCTION.with_pricing(no_section_factor_on_standby=False),
    "Class factor on PD-210 (Schedule 2 note)": PRODUCTION.with_pricing(no_class_factor_on_pd210=False),
    "No Rig Services Index (Appendix B)": PRODUCTION.with_pricing(apply_index=False),
    "Latest effective date governs (S2 monthly beats A3)": PRODUCTION.with_pricing(later_issued_governs=False),
    "A3 also reprices pre-issue invoices": PRODUCTION.with_pricing(retro_only_from_issue=False),
    "Lost in hole at Schedule 6 USD": PRODUCTION.with_pricing(lih_from_sar=False),
    "Round half up": PRODUCTION.with_pricing(half_up=True),
    "Clause 21A off": PRODUCTION.with_evidence(chargeable_hour="off"),
    "LWD words read literally, not by Appendix G": PRODUCTION.with_evidence(lwd_map="literal"),
    "Daily limits not applied": PRODUCTION.with_evidence(apply_daily_limits=False),
    "Rate discount folded into any preceding step's rounding": PRODUCTION.with_pricing(discount_fold="any"),
}


def compare(base: AuditResult, alt: AuditResult, name: str, kind: str) -> dict[str, str]:
    lines_changed = sum(1 for k, r in alt.lines.items() if r.expected_amount != base.lines[k].expected_amount)
    changed = [n for n, d in alt.invoices.items() if d.expected_total != base.invoices[n].expected_total]
    flag_on = [n for n, d in alt.invoices.items() if d.flagged and not base.invoices[n].flagged]
    flag_off = [n for n, d in alt.invoices.items() if not d.flagged and base.invoices[n].flagged]
    disagree = sum(1 for d in alt.invoices.values() if d.expected_total != d.billed_total)
    detail = "; ".join(f"{n}: {to_cents(base.invoices[n].expected_total)} -> {to_cents(alt.invoices[n].expected_total)}"
                       for n in changed[:8])
    return {
        "kind": kind, "scenario": name,
        "lines_amount_changed": str(lines_changed),
        "invoices_expected_total_changed": str(len(changed)),
        "invoices_flagged": str(sum(d.flagged for d in alt.invoices.values())),
        "newly_flagged": ";".join(flag_on[:20]) + (f" (+{len(flag_on) - 20} more)" if len(flag_on) > 20 else ""),
        "no_longer_flagged": ";".join(flag_off[:20]) + (f" (+{len(flag_off) - 20} more)" if len(flag_off) > 20 else ""),
        "invoices_expected_ne_billed": str(disagree),
        "a3_adjustment": f"{alt.plan.amount} on {alt.plan.carrier}",
        "expected_total_cents_changes": detail + (f" (+{len(changed) - 8} more)" if len(changed) > 8 else ""),
    }


def scenarios(inputs, reports, base: AuditResult, include_rejected: bool = True) -> list[dict[str, str]]:
    rows = []
    sets = [("material", MATERIAL)] + ([("rejected", REJECTED)] if include_rejected else [])
    for kind, table in sets:
        for name, cfg in table.items():
            rows.append(compare(base, run_audit(inputs, reports, cfg), name, kind))
    return rows
