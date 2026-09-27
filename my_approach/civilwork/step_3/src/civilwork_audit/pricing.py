"""Clause 27 rate build-up and Schedule 4 Part 3 bands.

    base (instrument in force on the work date; 29A index / 26A USD, half-even)
      x zone (Sch 2, Series A-D) x ground (Sch 3 items; G2 after 27 Sep 2025, 27A)
      x (1 + night uplift | rest-day uplift)   -- rest-day alone when both (Cl 8, P11)
      x band per cent (Sch 4 Pt 3)             -- counted per Contract Year (3A)
      x (1 - discount)                         -- final factor (S2 s2.2, A2 s2.3)
      -> rounded once, half-up, to the halala (Cl 28)

A quantity crossing a band edge is priced as parts, each at its own rounded rate.
Band counters are global, so every line is priced in the Clause 30 order.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from . import contract as C
from .config import PricingOptions
from .loader import Application, Line

CENT = Decimal("0.01")
HUNDRED = Decimal(100)


@dataclass(frozen=True)
class BandPart:
    quantity: int
    percent: int
    rate: Decimal                 # rounded rate for this part


@dataclass(frozen=True)
class LinePrice:
    base: Decimal                 # after 29A index / 26A conversion
    base_source: str
    zone_factor: Decimal
    ground_used: str
    ground_factor: Decimal
    uplift_kind: str              # "", "night", "rest-day"
    uplift_percent: Decimal
    discount: Decimal
    discount_source: str
    unrounded: Decimal            # before band and discount
    band_position: int | None     # units already counted in the Contract Year
    parts: tuple[BandPart, ...]

    @property
    def amount(self) -> Decimal:
        return sum((p.rate * p.quantity for p in self.parts), Decimal(0))

    def amount_for(self, quantity: int) -> Decimal:
        """A reduced quantity keeps the band position of the billed quantity (arch. C1 [7])."""
        total, remaining = Decimal(0), quantity
        for p in self.parts:
            take = min(p.quantity, remaining)
            total += p.rate * take
            remaining -= take
        if remaining:
            raise ValueError("amount_for: quantity exceeds the priced quantity")
        return total

    def describe(self, quantity: int | None = None) -> str:
        steps = [f"base {self.base} [{self.base_source}]", f"zone x{self.zone_factor}"]
        if self.ground_used:
            steps.append(f"ground {self.ground_used} x{self.ground_factor}")
        if self.uplift_kind:
            steps.append(f"{self.uplift_kind} +{self.uplift_percent}%")
        s = " ".join(steps) + f" = {self.unrounded.normalize():f}"
        if self.discount:
            s += f"; discount {self.discount * 100:.0f}% [{self.discount_source}]"
        parts = self.parts if quantity is None else _trim(self.parts, quantity)
        s += "; " + " + ".join(f"{p.quantity} x {p.rate} @{p.percent}%" for p in parts)
        return s


def _trim(parts: tuple[BandPart, ...], quantity: int) -> list[BandPart]:
    out, remaining = [], quantity
    for p in parts:
        take = min(p.quantity, remaining)
        if take:
            out.append(BandPart(take, p.percent, p.rate))
        remaining -= take
    return out


def converted_base(item: str, work_date: dt.date, application_date: dt.date,
                   opts: PricingOptions) -> tuple[Decimal, str]:
    br = C.instrument_rate(item, work_date, application_date,
                           disabled=opts.disabled_instruments, retro_rule=opts.retro_rule)
    rate, source = br.rate, br.source
    month = C.month_key(work_date)
    if item in C.INDEXED_ITEMS and opts.index:                         # Cl 29A
        rate = (rate * C.SITE_MATERIALS_INDEX[month] / C.INDEX_BASE).quantize(CENT, opts.conversion_rounding)
        source += f" x index {month} {C.SITE_MATERIALS_INDEX[month]}/100"
    if item in C.USD_ITEMS and opts.usd:                                # Cl 26A
        rate = (rate * C.HALALAS_PER_USD[month] / HUNDRED).quantize(CENT, opts.conversion_rounding)
        source += f" USD x {C.HALALAS_PER_USD[month]} halalas"
    return rate, source


def factors(ln: Line, opts: PricingOptions) -> dict:
    item = ln.item_code
    zf = C.ZONE_FACTORS[ln.zone] if opts.zone and item[0] in C.ZONE_SERIES else Decimal(1)
    ground_used, gf = "", Decimal(1)
    if opts.ground and item in C.GROUND_ITEMS:
        ground_used = ln.ground
        if opts.ground_freeze and ln.work_date >= dt.date.fromisoformat(opts.ground_freeze_from):
            ground_used = "G2"
        gf = C.GROUND_FACTORS[ground_used]
    rest = opts.rest_day and ln.work_date.weekday() in C.REST_WEEKDAYS and item in C.REST_DAY_UPLIFT
    night = (opts.night and ln.night_work and item in C.NIGHT_UPLIFT and not rest
             and not (opts.night_zone_cap and zf > C.NIGHT_ZONE_CAP))
    kind, pct = ("rest-day", Decimal(C.REST_DAY_UPLIFT[item])) if rest else \
        ("night", Decimal(C.NIGHT_UPLIFT[item])) if night else ("", Decimal(0))
    disc, disc_src = C.discount_rate(item, ln.work_date) if opts.discount else (Decimal(0), "")
    return dict(zone_factor=zf, ground_used=ground_used, ground_factor=gf, uplift_kind=kind,
                uplift_percent=pct, discount=disc, discount_source=disc_src)


def split_into_bands(item: str, position: int, quantity: int) -> list[tuple[int, int]]:
    """[(quantity, per cent)] for ``quantity`` units following ``position`` counted units."""
    parts, remaining = [], quantity
    for upper, pct in C.BANDS[item]:
        if remaining <= 0:
            break
        if upper is None or position < upper:
            take = remaining if upper is None else min(remaining, upper - position)
            parts.append((take, pct))
            position += take
            remaining -= take
    return parts


def order_key(opts: PricingOptions, apps: dict[str, Application]):
    if opts.band_order == "work_date":
        return lambda l: (l.work_date, l.application_no, l.line_no)
    if opts.band_order == "application_date":
        return lambda l: (apps[l.application_no].application_date, l.application_no, l.line_no)
    if opts.band_order == "work_date_reverse_application":
        return lambda l: (l.work_date, -int(l.application_no[3:]), l.line_no)
    raise ValueError(opts.band_order)


def price_lines(lines: Iterable[Line], apps: dict[str, Application], opts: PricingOptions,
                band_quantity: dict[str, int] | None = None) -> dict[str, LinePrice]:
    """Price every line at its billed quantity. ``band_quantity`` optionally gives the
    quantity each line adds to the cumulative band count (default: billed)."""
    counters: dict[tuple, int] = defaultdict(int)
    out: dict[str, LinePrice] = {}
    for ln in sorted(lines, key=order_key(opts, apps)):
        app = apps[ln.application_no]
        base, source = converted_base(ln.item_code, ln.work_date, app.application_date, opts)
        f = factors(ln, opts)
        unrounded = base * f["zone_factor"] * f["ground_factor"] * (1 + f["uplift_percent"] / HUNDRED)
        split, position = [(ln.quantity, 100)], None
        year = C.contract_year(ln.work_date)
        if opts.bands and ln.item_code in C.BANDS and year is not None:
            key = (ln.item_code, year if opts.band_year_reset else 1)
            position = counters[key]
            counters[key] += ln.quantity if band_quantity is None else band_quantity[ln.line_ref]
            split = split_into_bands(ln.item_code, position, ln.quantity)
        parts = tuple(
            BandPart(q, pct, (unrounded * pct / HUNDRED * (1 - f["discount"])).quantize(CENT, opts.final_rounding))
            for q, pct in split)
        out[ln.line_ref] = LinePrice(base, source, f["zone_factor"], f["ground_used"], f["ground_factor"],
                                     f["uplift_kind"], f["uplift_percent"], f["discount"],
                                     f["discount_source"], unrounded, position, parts)
    return out
