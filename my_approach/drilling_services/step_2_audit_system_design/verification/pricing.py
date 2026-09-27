"""Contract rate build-up for DDS-2025-118 with switchable interpretations.

`Reading` holds one choice per disputed point. `BASELINE` is the reading the architecture proposes;
the checks flip one switch at a time and count which billed lines change.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

from common import (A3_ISSUED, CLASS_FACTOR, CLASS_RATED, DISCOUNT_CODES, FLAT_RATES, FULL_ON_STANDBY,
                    HALALAS, INDEXED, LIH_SAR, LIH_USD_SCHED6, MONTHLY, PD210_BANDS, RATE_DISCOUNTS, RSI,
                    SCHEDULE_1, SECTION_FACTOR, SECTION_RATED, STANDBY_PCT, TERM_END, TERM_START, D, r2, ym)


@dataclass(frozen=True)
class Reading:
    # Clause 17B (p.35): no hole-section factor on a Standby day. False = Clause 18 (p.6) literal.
    no_section_factor_on_standby: bool = True
    # Clause 17B (p.35): no class factor on PD-210. False = Schedule 2 note / Sch.3 Pt2 list (pp.17, 20).
    no_class_factor_on_pd210: bool = True
    # Clause 17A (p.35) + Sch.2C (p.18): index MW-310 / HC-620. False = flat Schedule 1 rate.
    apply_index: bool = True
    # Instrument precedence for DD-120 from 2026-04: "later issued governs" -> A3 flat 416.00 beats S2
    # monthly; "later effective governs" -> S2 monthly beats A3.
    dd120_a3_over_s2_monthly: bool = True
    # S2 2.2 / A2 2.3: discount is a separate rounded step after standby (True) or folded into the
    # standby step before its rounding (False).
    discount_separate_step: bool = True
    # Clause 36A (p.35): an invoice submitted before A3's issue date is correct at the pre-A3 rate.
    a3_only_from_issue: bool = True
    # Clause 31A (p.35): SAR values converted at the month's rate (True) or Schedule 6 USD (False).
    lih_from_sar: bool = True
    # Clause 21A (p.35): the first hour of each period in the hole is not chargeable.
    chargeable_hour_minus_one: bool = False
    # Clause 25A (p.35): 1% tolerance on metres.
    metre_tolerance: bool = True
    # Clause 17 (p.6) / p.1: half to even. True = half up (tested as an alternative).
    half_up: bool = False


BASELINE = Reading()


def _r(x: Decimal, rd: Reading) -> Decimal:
    return r2(x, ROUND_HALF_UP if rd.half_up else ROUND_HALF_EVEN)


def _flat_rate(code: str, day: dt.date, invoice_date: dt.date | None, rd: Reading) -> tuple[Decimal, str]:
    unit, base = SCHEDULE_1[code]
    rate, src = D(base), "Sch1"
    candidates = []  # (issued, effective, rate, source)
    from common import INSTRUMENTS
    issued = {n: i for n, i, _ in INSTRUMENTS}
    for inst, eff, r in FLAT_RATES.get(code, []):
        if day >= eff:
            if inst == "A3" and rd.a3_only_from_issue and (invoice_date is None or invoice_date < A3_ISSUED):
                continue
            candidates.append((issued[inst], eff, r, inst))
    if code in MONTHLY:
        inst, table = MONTHLY[code]
        months = sorted(table)
        if ym(day) >= months[0]:
            m = max(x for x in months if x <= ym(day))
            candidates.append((issued[inst], dt.date(int(months[0][:4]), int(months[0][5:]), 1), D(table[m]), f"{inst}:{m}"))
    if candidates:
        if rd.dd120_a3_over_s2_monthly:
            key = lambda c: c[0]           # the later-issued instrument governs from its effective date
        else:
            key = lambda c: (c[1], c[0])   # the latest effective date governs
        _, _, rate, src = max(candidates, key=key)
    return rate, src


def rate_discount(code: str, day: dt.date) -> Decimal:
    if code not in DISCOUNT_CODES:
        return D(0)
    pct = D(0)
    for eff, p in RATE_DISCOUNTS:  # A2 7% replaces S2 4% ("the later governs")
        if day >= eff:
            pct = p
    return pct


def build_rate(code: str, day: dt.date, section: str, status: str, well_class: str,
               invoice_date: dt.date | None = None, rd: Reading = BASELINE) -> tuple[Decimal | None, list]:
    """Clause 18 build-up, each step rounded half-even (Clause 17). Returns (rate, trail).
    rate None = not chargeable on this status."""
    trail = []
    standby = status == "Standby"
    if not (TERM_START <= day <= TERM_END):
        return None, [f"{day} outside the Term as extended (p.1, A1 1.1, A2 2.1)"]
    if code == "DD-121" and not standby:
        return None, ["DD-121 only on a Standby day (Sch.3 Pt4)"]
    if standby and code not in FULL_ON_STANDBY and STANDBY_PCT.get(code, "missing") is None:
        return None, [f"{code} not chargeable on Standby (Sch.3 Pt3)"]
    rate, src = _flat_rate(code, day, invoice_date, rd)
    trail.append(f"base {rate} [{src}]")
    if code in INDEXED and rd.apply_index:
        rate = _r(rate * RSI[ym(day)] / D(100), rd)
        trail.append(f"index {RSI[ym(day)]} -> {rate}")
    if code in SECTION_RATED and not (standby and rd.no_section_factor_on_standby):
        rate = _r(rate * SECTION_FACTOR[section], rd)
        trail.append(f"section {SECTION_FACTOR[section]} -> {rate}")
    if code in CLASS_RATED and not (code == "PD-210" and rd.no_class_factor_on_pd210):
        rate = _r(rate * CLASS_FACTOR[well_class], rd)
        trail.append(f"class {CLASS_FACTOR[well_class]} -> {rate}")
    disc = rate_discount(code, day)
    if standby and code not in FULL_ON_STANDBY:
        pct = STANDBY_PCT[code]
        if disc and not rd.discount_separate_step:
            rate = _r(rate * pct * (1 - disc), rd)
            trail.append(f"standby {pct} x (1-{disc}) -> {rate}")
            return rate, trail
        rate = _r(rate * pct, rd)
        trail.append(f"standby {pct} -> {rate}")
    if disc:
        rate = _r(rate * (1 - disc), rd)
        trail.append(f"discount {disc} -> {rate}")
    return rate, trail


def pd210_rate(dfrom: int, dto: int, well_class: str, rd: Reading = BASELINE) -> Decimal | None:
    """Schedule 2 band for an interval lying wholly in one band (boundary depth -> shallower band)."""
    for lo, hi, r in PD210_BANDS:
        if lo <= dfrom and dto <= hi:
            if not rd.no_class_factor_on_pd210:
                r = _r(r * CLASS_FACTOR[well_class], rd)
            return r
    return None


def pd210_split(dstart: int, dend: int) -> list[tuple[int, int, Decimal]]:
    """Clause 23 (p.6): split the day's metres at 1,500 / 3,000 / 4,500 m."""
    out = []
    for lo, hi, r in PD210_BANDS:
        a, b = max(dstart, lo), min(dend, hi)
        if b > a:
            out.append((a, b, r))
    return out


def lih_value(code: str, loss_day: dt.date, hours: int, rd: Reading = BASELINE) -> tuple[Decimal, list]:
    """Clause 31 (p.7) with Clause 31A / Schedule 2D (pp.19, 35)."""
    if rd.lih_from_sar:
        hal = HALALAS[ym(loss_day)]
        usd = _r(LIH_SAR[code] * D(100) / hal, rd)
        trail = [f"SAR {LIH_SAR[code]} / {hal} halalas -> {usd}"]
    else:
        usd = LIH_USD_SCHED6[code]
        trail = [f"Sch6 {usd}"]
    dep = min(hours // 25, 50)
    val = _r(usd * (D(100) - dep) / D(100), rd)
    trail.append(f"depreciation {dep}% ({hours} h) -> {val}")
    return val, trail
