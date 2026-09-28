"""Rate build-up (Clause 18 as amended by Part IX and the instruments).

    r0  rate in force on the service date (Schedule 1 / instruments, Clause 36A for pre-issue invoices)
    r1  x Rig Services Index of the service month / 100            (17A; MW-310, HC-620)
    r2  x hole-section factor, not on a Standby day                 (Sch.3 Pt1; 17B)
    r3  x well-class factor, never on PD-210                        (Sch.3 Pt2; 17B)
    r4  x standby percentage on a Standby day                       (Sch.3 Pt3)
    r5  x (1 - rate discount) from 2026-04-01 / 2026-07-01          (S2 2.2, A2 2.3: last factor)
    amount = quantity x r5

Each step is rounded to the cent, half to even (Clause 17).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

from . import contract as C
from .config import PricingOptions
from .money import ZERO, r2

D = Decimal


@dataclass
class Rate:
    rate: Decimal | None               # None: not chargeable (reason in ``note``)
    steps: list[str] = field(default_factory=list)
    source: str = ""
    note: str = ""

    def describe(self) -> str:
        return " -> ".join(self.steps) if self.rate is not None else self.note


def base_rate(code: str, day: dt.date, invoice_date: dt.date | None, opt: PricingOptions) -> tuple[Decimal, str]:
    """The rate in force for a service performed on ``day``.

    Instruments are read in the order issued; the latest-issued one that prices the service on that
    day governs from its effective date (p.37 and each instrument's closing words). An instrument that
    takes effect before its issue date does not reprice an invoice submitted before that date
    (Clause 36A)."""
    rate, source = C.SCHEDULE_1[code][2], "Sch.1 p.15-16"
    best: tuple | None = None
    for ins in C.INSTRUMENTS:
        if opt.retro_only_from_issue and ins.retroactive and (invoice_date is None or invoice_date < ins.issued):
            continue
        cand = None
        if code in ins.rates and day >= ins.effective:
            cand = (ins.rates[code], f"{ins.name} p.{ins.page}")
        elif code in ins.monthly:
            months = sorted(ins.monthly[code])
            usable = [m for m in months if m <= C.ym(day)]
            if usable:    # the rate last published applies until superseded (S1 1.2, S2 2.1)
                cand = (ins.monthly[code][usable[-1]], f"{ins.name} p.{ins.page} {usable[-1]}")
        if cand is None:
            continue
        first_month = min(ins.monthly[code]) if code in ins.monthly else None
        eff = dt.date(int(first_month[:4]), int(first_month[5:]), 1) if first_month else ins.effective
        rank = (ins.issued, eff) if opt.later_issued_governs else (eff, ins.issued)
        if best is None or rank > best[0]:
            best = (rank, cand)
    if best is not None:
        rate, source = best[1]
    return rate, source


def rate_discount(code: str, day: dt.date) -> tuple[Decimal, str]:
    """S2 2.2 (4 % from 2026-04-01) replaced by A2 2.3 (7 % from 2026-07-01): the later governs."""
    pct, src = ZERO, ""
    for ins in C.INSTRUMENTS:
        if ins.discount is not None and code in ins.discount_codes and day >= ins.effective:
            pct, src = ins.discount, ins.name
    return pct, src


def build_rate(code: str, day: dt.date, section: str, status: str, well_class: str,
               invoice_date: dt.date | None, opt: PricingOptions = PricingOptions()) -> Rate:
    standby = status == "Standby"
    if code not in C.SCHEDULE_1:
        return Rate(None, note=f"{code} is not a Schedule 1 item")
    if not (C.TERM_START <= day <= C.TERM_END):
        return Rate(None, note=f"{day} outside the Term as extended to {C.TERM_END} (p.1, A1 1.1, A2 2.1)")
    if code in C.STANDBY_ONLY and not standby:
        return Rate(None, note=f"{code} only on a Standby day (Sch.3 Pt4 p.21)")
    if standby and code not in C.FULL_WHATEVER_STATUS and code not in C.STANDBY_ONLY \
            and C.STANDBY_PCT.get(code) is None:
        return Rate(None, note=f"{code} not chargeable on a Standby day (Sch.3 Pt3 p.20-21)")
    rate, source = base_rate(code, day, invoice_date, opt)
    if rate is None:
        return Rate(None, note=f"{code} has no Schedule 1 rate")
    out = Rate(rate, [f"{rate} [{source}]"], source)
    disc, disc_src = rate_discount(code, day)
    factors: list[tuple[str, Decimal]] = []
    if code in C.INDEXED and opt.apply_index:
        factors.append((f"index {C.RIG_SERVICES_INDEX[C.ym(day)]}", C.RIG_SERVICES_INDEX[C.ym(day)] / C.INDEX_BASE))
    if code in C.SECTION_RATED and not (standby and opt.no_section_factor_on_standby):
        factors.append((f"section {section}", C.SECTION_FACTOR[section]))
    if code in C.CLASS_RATED and not (code == "PD-210" and opt.no_class_factor_on_pd210):
        factors.append((f"class {well_class}", C.CLASS_FACTOR[well_class]))
    if standby and code not in C.FULL_WHATEVER_STATUS and code not in C.STANDBY_ONLY:
        factors.append(("standby", C.STANDBY_PCT[code]))
    if disc:
        fold = factors and (opt.discount_fold == "any" or (opt.discount_fold == "standby" and factors[-1][0] == "standby"))
        if fold:
            label, f = factors[-1]
            factors[-1] = (f"{label} x discount {disc} {disc_src}", f * (1 - disc))
        else:
            factors.append((f"discount {disc} {disc_src}", 1 - disc))
    for label, f in factors:
        out.rate = r2(out.rate * f, opt.half_up)
        out.steps.append(f"{label} -> {out.rate}")
    return out


def pd210_segments(depth_start: int, depth_end: int) -> list[tuple[int, int, Decimal]]:
    """Clause 23: the day's metres split at 1,500 / 3,000 / 4,500 m; a boundary depth is shallower."""
    out = []
    for lo, hi, rate in C.PD210_BANDS:
        a, b = max(depth_start, lo), depth_end if hi is None else min(depth_end, hi)
        if b > a:
            out.append((a, b, rate))
    return out


def pd210_volume_parts(already: int, metres: int) -> list[tuple[int, Decimal]]:
    """Schedule 2 Part 2: split ``metres`` drilled after ``already`` metres in the Contract Year into
    (metres, per cent) parts; an interval that crosses a volume band is divided at the band."""
    parts, pos, left = [], already, metres
    for lo, hi, pct in C.PD210_VOLUME_BANDS:
        if left <= 0:
            break
        if hi is not None and pos >= hi:
            continue
        take = left if hi is None else min(left, hi - pos)
        parts.append((take, pct))
        pos += take
        left -= take
    return parts


def pd210_amount(segment_rate: Decimal, qty: int, already: int, opt: PricingOptions,
                 well_class: str) -> tuple[Decimal, Decimal, list[str]]:
    """Amount for ``qty`` PD-210 metres of one depth band. Returns (amount, rate of the first part, trail)."""
    total, trail, first_rate = ZERO, [], None
    for metres, pct in pd210_volume_parts(already, qty):
        rate = segment_rate if pct == 1 else r2(segment_rate * pct, opt.half_up)
        if not opt.no_class_factor_on_pd210:
            rate = r2(rate * C.CLASS_FACTOR[well_class], opt.half_up)
        first_rate = rate if first_rate is None else first_rate
        total += r2(rate * metres, opt.half_up)
        trail.append(f"{metres} m x {rate} (band {segment_rate}, volume {pct:.0%})")
    return total, first_rate if first_rate is not None else segment_rate, trail


def lih_value(code: str, loss_day: dt.date, hours: int, opt: PricingOptions = PricingOptions()) -> Rate:
    """Clause 31 with 31A: SAR value / halalas of the month of loss (half-even), then depreciation of
    1 % per complete 25 circulating hours stated on Part E, at most 50 %, rounded (Clause 17)."""
    if opt.lih_from_sar:
        hal = C.HALALAS_PER_USD[C.ym(loss_day)]
        usd = r2(C.LIH_SAR[code] * 100 / hal, opt.half_up)
        steps = [f"SAR {C.LIH_SAR[code]} / {hal} halalas ({C.ym(loss_day)}) -> {usd} [Sch.2D p.19, 31A]"]
    else:
        usd = C.LIH_USD_SCHEDULE_6[code]
        steps = [f"Sch.6 {usd}"]
    dep = min(hours // C.LIH_DEPRECIATION_HOURS, C.LIH_DEPRECIATION_CAP)
    value = r2(usd * (100 - dep) / 100, opt.half_up)
    steps.append(f"depreciation {dep}% ({hours} h) -> {value} [Cl 31 p.7]")
    return Rate(value, steps, "Cl 31/31A")


def invoice_discount(services: Decimal, half_up: bool = False) -> Decimal:
    """Clause 38: 4 % of the services above 250,000.00 as one negative DS-900 charge (P11: per invoice)."""
    if services <= C.DISCOUNT_THRESHOLD:
        return ZERO
    return -r2((services - C.DISCOUNT_THRESHOLD) * C.DISCOUNT_RATE, half_up)


def vat(net: Decimal, half_up: bool = False) -> Decimal:
    return r2(net * C.VAT_RATE, half_up)       # Clause 39
