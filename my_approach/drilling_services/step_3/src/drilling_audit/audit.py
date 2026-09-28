"""The audit pipeline, in a fixed and documented order.

    [1] inputs validated (loader)            [2] reports parsed (reports)
    [3] per report: supported quantities -> pools keyed (well, day, code[, PD-210 interval])
    [4] lines in (invoice_date, invoice_no, line_no) order:
          unknown code / unit -> term -> invoice period -> report exists -> report readable
          -> signatures (policy) -> Schedule 5 part (Cl 37) -> consume the pool (Cl 29, 25A)
          -> rate build-up -> amount; plus billed arithmetic and section/status checks
    [5] Clause 36A difference on pre-issue invoices -> one carrier
    [6] per invoice: discount, VAT, total rebuilt; billed-figure checks; flag, category, confidence

The first reason in [4] that removes a line's evidence decides it; later checks still run where
they can (e.g. billed arithmetic) so the audit trail shows every defect.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from . import categories as K
from . import contract as C
from .config import AuditConfig, PRODUCTION
from .diagnosis import explain
from .evidence import Support, supported, well_facts
from .loader import Inputs, Invoice, Line
from .money import ZERO, r2
from .pricing import Rate, build_rate, invoice_discount, lih_value, pd210_amount, pd210_segments, vat
from .reports import Report

@dataclass
class LineResult:
    line: Line
    report: Report | None
    evidence_day: dt.date
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    supported_qty: Decimal | None = None      # pool available when the line was reached
    paid_qty: Decimal = ZERO
    rate: Rate | None = None
    expected_amount: Decimal = ZERO
    basis: str = ""
    notes: list[str] = field(default_factory=list)
    query: bool = False                       # cannot be priced: expected amount = billed amount
    diagnosis: list[str] = field(default_factory=list)   # mechanisms reproducing a wrong billed rate
    labels: dict[str, str] = field(default_factory=dict)  # reason -> specific category, where refined

    @property
    def delta(self) -> Decimal:
        return self.line.amount - self.expected_amount

    @property
    def categories(self) -> list[str]:
        return sorted({self.labels.get(r, K.category(r)) for r in self.reasons}, key=K.ORDER.__getitem__)


@dataclass
class AdjustmentPlan:
    instrument: str
    lines: list[str]
    by_basis: dict[str, Decimal]
    amount: Decimal
    carrier: str | None
    candidates_on_or_after: list[str]
    candidates_strictly_after: list[str]
    note: str


@dataclass
class InvoiceResult:
    invoice: Invoice
    lines: list[LineResult]
    services: Decimal
    discount: Decimal
    net: Decimal
    vat: Decimal
    adjustment: Decimal
    expected_total: Decimal
    causes: dict[str, Decimal]                 # category -> money effect
    reasons: list[str]                          # invoice-level reasons
    flagged: bool
    error_category: str
    confidence: float
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def billed_total(self) -> Decimal:
        return self.invoice.invoice_total

    @property
    def all_categories(self) -> list[str]:
        return sorted(self.causes, key=K.ORDER.__getitem__)


@dataclass
class AuditResult:
    config: AuditConfig
    lines: dict[str, LineResult]
    invoices: dict[str, InvoiceResult]
    plan: AdjustmentPlan
    reports: dict
    unread_reports: list[str]


# ------------------------------------------------------------------ [3] pools

def build_pools(reports: dict, cfg: AuditConfig) -> tuple[dict, dict, dict]:
    """Supported quantity per (well, day, code, interval) and the evidence basis, plus metres already
    drilled on the well in the Contract Year before each report (Schedule 2 Part 2)."""
    facts = well_facts(reports, cfg.evidence)
    pools: dict[tuple, Decimal] = {}
    support: dict[tuple, Support] = {}
    for key, rep in reports.items():
        if rep.problems:
            continue               # a report we cannot read supports nothing until reviewed
        s = supported(rep, facts[rep.well], cfg.evidence)
        support[key] = s
        for code, q in s.qty.items():
            if code == "PD-210":
                for a, b in s.pd210_segments:
                    pools[(key, code, a, b)] = Decimal(b - a)
            else:
                pools[(key, code, None, None)] = Decimal(q)
    drilled_before: dict[tuple, int] = {}
    cum: dict[tuple, int] = defaultdict(int)
    for key in sorted(reports, key=lambda k: (k[0], k[1])):
        rep = reports[key]
        cy = (rep.well, C.contract_year(rep.date))
        drilled_before[key] = cum[cy]
        if rep.operating and rep.metres > 0:
            cum[cy] += rep.metres
    return pools, support, drilled_before


# ------------------------------------------------------------------ [4] lines

def _evidence_day(ln: Line, cfg: AuditConfig) -> dt.date:
    if cfg.evidence.evidence_day == "report_ref" and ln.report_ref:
        return dt.datetime.strptime(ln.report_ref[-8:], "%Y%m%d").date()
    return ln.service_date


def assess_lines(inputs: Inputs, reports: dict, cfg: AuditConfig) -> dict[str, LineResult]:
    pools, support, drilled_before = build_pools(reports, cfg)
    inv = inputs.invoices
    order = sorted((ln for ln in inputs.lines if not ln.is_discount),
                   key=lambda ln: (inv[ln.invoice_no].invoice_date, ln.invoice_no, ln.line_no))
    out: dict[str, LineResult] = {}
    for ln in order:
        I = inv[ln.invoice_no]
        day = _evidence_day(ln, cfg)
        rep = reports.get((ln.well, day))
        r = LineResult(ln, rep, day)
        out[ln.line_ref] = r
        if ln.report_ref and ln.report_ref != f"DDR-{ln.well[-3:]}-{ln.service_date:%Y%m%d}":
            r.warnings.append(f"report_ref {ln.report_ref} is not the number of the {ln.service_date} report (Cl 19A)")
        if r2(ln.quantity * ln.rate) != ln.amount:
            r.reasons.append("amount_ne_qty_x_rate")
            r.notes.append(f"{ln.quantity} x {ln.rate} = {r2(ln.quantity * ln.rate)}, billed {ln.amount}")
        _assess_one(r, I, pools, support, drilled_before, cfg)
    return out


def _assess_one(r: LineResult, I: Invoice, pools: dict, support: dict, drilled_before: dict,
                cfg: AuditConfig) -> None:
    ln, rep, day = r.line, r.report, r.evidence_day
    sched = C.SCHEDULE_1.get(ln.code)
    if sched is None:
        r.reasons.append("unknown_service_code")
        r.query, r.expected_amount = True, ln.amount
        return
    if (ln.description, ln.unit) != sched[:2]:
        r.reasons.append("unit_or_description_wrong")
        r.notes.append(f"billed {ln.description!r} per {ln.unit}; Schedule 1: {sched[0]!r} per {sched[1]}")
        return
    if day < C.TERM_START:
        r.reasons.append("before_term")
        r.notes.append(f"{day} is before the Commencement Date {C.TERM_START}")
        return
    if day > C.TERM_END:
        r.reasons.append("outside_term")
        r.notes.append(f"{day} is after the Term as extended ({C.TERM_END})")
        return
    if not (I.period_start <= day <= I.period_end):
        r.reasons.append("outside_invoice_period")
        r.notes.append(f"{day} outside the invoice period {I.period_start}..{I.period_end}")
        return
    if rep is None:
        r.reasons.append("no_report_for_day")
        return
    if rep.problems:
        r.reasons.append("report_unreadable")
        r.notes.append("; ".join(rep.problems))
        r.query, r.expected_amount = True, ln.amount
        return
    if not rep.signed:
        r.notes.append(f"{rep.file} lacks: {', '.join(rep.missing_signatures)} (policy {cfg.unsigned_policy})")
        if cfg.unsigned_policy == "zero_day" or (cfg.unsigned_policy == "zero_schedule5" and ln.code in C.PART_REQUIRED):
            r.reasons.append("report_unsigned")
            return
        r.reasons.append("report_unsigned")        # flagged, charge still priced from the report
    part = C.PART_REQUIRED.get(ln.code)
    if part and part not in rep.parts:
        r.reasons.append(f"part_{part}_absent")
        r.notes.append(f"{ln.code} needs Part {part}; {rep.file} has Parts {''.join(rep.parts)}")
        return
    if ln.code == "PD-210":
        pk = (rep.key, ln.code, ln.depth_from, ln.depth_to)
    else:
        pk = (rep.key, ln.code, None, None)
    s = support[rep.key]
    r.basis = s.basis.get(ln.code, "not recorded")
    avail = pools.get(pk)
    r.supported_qty = avail
    if avail is None:
        r.reasons.append("not_supported_by_report")
        why = s.basis.get(ln.code)
        r.notes.append(f"{rep.file} ({rep.status}, {rep.section}) supports no {ln.code}"
                       + (f" {ln.depth_from}-{ln.depth_to} m" if ln.code == "PD-210" else "")
                       + (f": {why}" if why else "; its words do not record the service"))
        return
    if avail <= 0:
        r.reasons.append("already_billed")
        r.notes.append("the report's quantity was used by an earlier line (Cl 29)")
        return
    billed = ln.quantity
    if billed <= avail:
        qty = billed
    elif ln.code in C.METRE_SERVICES and cfg.evidence.metre_tolerance and billed <= avail * (1 + C.METRE_TOLERANCE):
        qty = billed
        r.notes.append(f"{billed} m within 1 % of the {avail} m supported: payable as charged (Cl 25A)")
    else:
        qty = avail
        r.reasons.append("qty_above_report")
        r.notes.append(f"billed {billed}, report supports {avail}")
        reported = {"DD-120": rep.circulating_hours, "RM-530": rep.count("Back-reaming hours")}.get(ln.code)
        if reported is not None and billed == reported:
            r.labels["qty_above_report"] = "chargeable_hour_not_deducted"
            r.notes.append("billed the hours the report states, without the Clause 21A rig-up hour")
        elif "daily limit" in r.basis:
            r.labels["qty_above_report"] = "daily_limit_exceeded"
    pools[pk] = max(avail - qty, ZERO)
    r.paid_qty = qty
    if (ln.section, ln.status) != (rep.section, rep.status):
        r.reasons.append("section_or_status_differs")
        r.notes.append(f"billed {ln.section}/{ln.status}; report {rep.section}/{rep.status} governs (Cl 19)")
    opt = cfg.pricing
    if ln.code in C.LOST_IN_HOLE:
        hours = rep.count("Circulating hours accumulated on the well")
        rate = lih_value(ln.code, day, hours, opt)
        amount = r2(qty * rate.rate, opt.half_up)
    elif ln.code == "PD-210":
        seg_rate = next(rt for a, b, rt in pd210_segments(rep.depth_start, rep.depth_end)
                        if (a, b) == (ln.depth_from, ln.depth_to))
        already = drilled_before[rep.key] + (ln.depth_from - rep.depth_start)
        amount, first, trail = pd210_amount(seg_rate, int(qty), already, opt, I.well_class)
        rate = Rate(first, [f"Sch.2 band {ln.depth_from}-{ln.depth_to} m: {seg_rate} [p.17]"] + trail, "Sch.2 p.17")
    else:
        rate = build_rate(ln.code, day, rep.section, rep.status, I.well_class, I.invoice_date, opt)
        amount = r2(qty * rate.rate, opt.half_up) if rate.rate is not None else ZERO
    r.rate = rate
    if rate.rate is None:
        r.reasons.append("not_chargeable_on_status")
        r.notes.append(rate.note)
        r.paid_qty = ZERO
        return
    r.expected_amount = amount
    if ln.rate != rate.rate:
        r.reasons.append("rate_differs")
        r.diagnosis = explain(r, I)
        r.labels["rate_differs"] = K.rate_category(r.diagnosis, I.invoice_date < C.INSTRUMENT["A3"].issued)


# ------------------------------------------------------------------ [5] Clause 36A

def plan_adjustment(inputs: Inputs, lines: dict[str, LineResult], reports: dict, cfg: AuditConfig) -> AdjustmentPlan:
    """Clause 36A: the difference, at the retroactive instrument's rates, on services performed on or
    after its effective date and invoiced before its issue date, as one adjustment on one invoice."""
    ins = next(i for i in C.INSTRUMENTS if i.retroactive)
    inv = inputs.invoices
    by_basis = {"supported": ZERO, "billed": ZERO}
    refs = []
    for ref in sorted(lines):
        r = lines[ref]
        ln, I = r.line, inv[r.line.invoice_no]
        if ln.code not in ins.rates or ln.service_date < ins.effective or I.invoice_date >= ins.issued:
            continue
        rep = r.report
        section, status = (rep.section, rep.status) if rep else (ln.section, ln.status)
        old = build_rate(ln.code, ln.service_date, section, status, I.well_class, I.invoice_date, cfg.pricing).rate
        new = build_rate(ln.code, ln.service_date, section, status, I.well_class, ins.issued, cfg.pricing).rate
        if old is None or new is None:
            continue
        refs.append(ref)
        for basis, q in (("supported", r.paid_qty), ("billed", ln.quantity)):
            by_basis[basis] += r2(q * new, cfg.pricing.half_up) - r2(q * old, cfg.pricing.half_up)
    dates = sorted((I.invoice_date, n) for n, I in inv.items())
    on_or_after = [n for d_, n in dates if d_ >= ins.issued]
    strictly = [n for d_, n in dates if d_ > ins.issued]
    first_day = lambda ns: [n for n in ns if inv[n].invoice_date == inv[ns[0]].invoice_date] if ns else []
    oa, sa = first_day(on_or_after), first_day(strictly)
    if cfg.a3_carrier == "on_or_after":
        carrier = min(oa) if oa else None
    elif cfg.a3_carrier == "strictly_after_first_number":
        carrier = min(sa) if sa else None
    elif cfg.a3_carrier in inv:
        carrier = cfg.a3_carrier
    else:
        raise ValueError(f"unknown a3_carrier {cfg.a3_carrier!r}")
    note = (f"36A 'on or after' {ins.issued}: first invoice(s) {oa}; A3 'after': first invoice(s) {sa} "
            f"(tie broken by lowest number only under the strict reading). Policy {cfg.a3_carrier} -> {carrier}.")
    return AdjustmentPlan(ins.name, refs, by_basis, by_basis[cfg.a3_basis], carrier, oa, sa, note)


# ------------------------------------------------------------------ [6] invoices

def decide_invoice(I: Invoice, lines: list[Line], results: list[LineResult], plan: AdjustmentPlan,
                   cfg: AuditConfig) -> InvoiceResult:
    causes: dict[str, Decimal] = defaultdict(Decimal)
    reasons: list[str] = []
    notes: list[str] = []
    for r in results:
        for c in r.categories:
            causes[c] += abs(r.delta)
    services = sum((r.expected_amount for r in results), ZERO)
    discount = invoice_discount(services, cfg.pricing.half_up)
    net = services + discount
    due = plan.amount if I.invoice_no == plan.carrier else ZERO
    in_total = cfg.adjustment_treatment == "in_total"
    if in_total and cfg.vat_on_adjustment:
        net_for_vat = net + due
        tax = vat(net_for_vat, cfg.pricing.half_up)
        total = net_for_vat + tax
    else:
        tax = vat(net, cfg.pricing.half_up)
        total = net + tax + (due if in_total else ZERO)

    def add(reason: str, effect: Decimal, note: str) -> None:
        reasons.append(reason)
        causes[K.category(reason)] += abs(effect)
        notes.append(note)

    billed_services = sum((ln.amount for ln in lines if not ln.is_discount), ZERO)
    billed_disc = sum((ln.amount for ln in lines if ln.is_discount), ZERO)
    want_disc = invoice_discount(billed_services, cfg.pricing.half_up)
    if billed_disc != want_disc:
        reason = "discount_DS900_missing" if not any(ln.is_discount for ln in lines) else "discount_DS900_wrong"
        effect = (want_disc - billed_disc) * (1 + C.VAT_RATE)
        add(reason, effect, f"DS-900 on billed services {billed_services}: due {want_disc}, billed {billed_disc}")
    if billed_services + billed_disc != I.net_amount:
        add("net_ne_sum_of_lines", I.net_amount - billed_services - billed_disc,
            f"net {I.net_amount} != lines {billed_services + billed_disc}")
    if vat(I.net_amount) != I.vat_amount:
        add("vat_wrong", I.vat_amount - vat(I.net_amount), f"VAT {I.vat_amount} != 15 % of {I.net_amount}")
    if I.net_amount + I.vat_amount + I.adjustment != I.invoice_total:
        add("total_ne_net_plus_vat", I.invoice_total - I.net_amount - I.vat_amount - I.adjustment,
            f"total {I.invoice_total} != net {I.net_amount} + VAT {I.vat_amount} + adjustment {I.adjustment}")
    if I.adjustment != due:
        if due and not I.adjustment:
            add("a3_adjustment_missing", due, f"Clause 36A adjustment {due} due on this invoice; billed 0.00 "
                f"({'inside' if in_total else 'separate from'} the audited total)")
        elif I.adjustment and not due:
            add("a3_adjustment_not_due", I.adjustment, f"adjustment {I.adjustment} shown on an invoice that is not the carrier")
        else:
            add("a3_adjustment_wrong_amount", due - I.adjustment, f"adjustment due {due}, billed {I.adjustment}")
    if I.contract_ref != C.CONTRACT_REF:
        add("contract_ref_wrong", ZERO, f"contract_ref {I.contract_ref!r}; amount valued under {C.CONTRACT_REF}")
    if I.contractor != C.CONTRACTOR:
        add("contractor_wrong", ZERO, f"issuer {I.contractor!r}")
    if I.invoice_date < I.period_end:
        add("submitted_before_period_end", ZERO, f"submitted {I.invoice_date}, before period end {I.period_end}")
    lag = (I.invoice_date - I.period_end).days
    if lag > C.SUBMISSION_WINDOW_DAYS:
        add("submitted_over_30_days", ZERO, f"submitted {lag} days after the period ended")
    if I.period_end > C.TERM_END or I.period_start < C.TERM_START:
        add("period_outside_term", ZERO, f"period {I.period_start}..{I.period_end} runs outside the Term")
    warnings = [w for r in results for w in r.warnings]
    if I.invoice_no in plan.candidates_strictly_after + plan.candidates_on_or_after and I.invoice_no != plan.carrier:
        warnings.append(f"A3 carrier under the other reading of 36A/A3 ({plan.note})")
    if not causes and total != I.invoice_total:
        add("rebuilt_total_differs", total - I.invoice_total,
            f"rebuilt total {total} differs from billed {I.invoice_total} with no line or billed-figure defect")
    flagged = bool(causes)
    if flagged:
        primary = min(causes.items(), key=lambda kv: (-kv[1], K.ORDER[kv[0]]))[0]
        conf = min(K.CONFIDENCE[c] for c in causes)
        if causes.keys() == {"index_or_fx_month_wrong"} and all(
                r.line.code in C.LOST_IN_HOLE for r in results if "rate_differs" in r.reasons):
            conf = K.CONFIDENCE_LIH_EXCHANGE
    else:
        primary = ""
        conf = K.CONFIDENCE_NOT_FLAGGED_WARNED if warnings else K.CONFIDENCE_NOT_FLAGGED
    return InvoiceResult(I, results, services, discount, net, tax, due, total, dict(causes), reasons, flagged,
                         primary, conf, notes, warnings)


def run_audit(inputs: Inputs, reports: dict, cfg: AuditConfig = PRODUCTION) -> AuditResult:
    lines = assess_lines(inputs, reports, cfg)
    plan = plan_adjustment(inputs, lines, reports, cfg)
    by_inv = inputs.lines_by_invoice()
    invoices = {}
    for n in sorted(inputs.invoices):
        ls = by_inv[n]
        invoices[n] = decide_invoice(inputs.invoices[n], ls, [lines[ln.line_ref] for ln in ls if not ln.is_discount],
                                     plan, cfg)
    unread = sorted(rep.file for rep in reports.values() if rep.problems)
    return AuditResult(cfg, lines, invoices, plan, reports, unread)
