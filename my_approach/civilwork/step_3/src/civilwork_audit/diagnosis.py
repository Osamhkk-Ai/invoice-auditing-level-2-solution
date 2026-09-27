"""Explain a billed line that does not reproduce: which factor of the build-up differs?

A search over every base any instrument ever stated (every month for indexed and USD
items), every zone, ground, uplift, band per cent and discount keeps the combination
that reproduces the billed rate with the fewest differences from the contract build-up
(architecture C6). The ratio of billed to expected amount is never used on its own.
The diagnosis only names the category; the expected amount always comes from the
pricing engine.
"""
from __future__ import annotations

import itertools
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

from . import contract as C
from .loader import Application, Line
from .pricing import CENT, HUNDRED, LinePrice

_ZONES = sorted(set(C.ZONE_FACTORS.values()))
_GROUNDS = sorted(set(C.GROUND_FACTORS.values()))
_UPLIFTS = [Decimal(x) for x in (0, 18, 22, 25, 35)]
_PERCENTS = sorted({p for bands in C.BANDS.values() for _, p in bands}, reverse=True)
_DISCOUNTS = [Decimal(0)] + sorted({i.discount for i in C.INSTRUMENTS if i.discount is not None})


def _candidate_bases(item: str) -> list[tuple[Decimal, str]]:
    out: dict[Decimal, str] = {}
    for v in C.all_stated_base_rates(item):
        if item in C.INDEXED_ITEMS:
            for month, ix in C.SITE_MATERIALS_INDEX.items():
                out.setdefault((v * ix / C.INDEX_BASE).quantize(CENT, ROUND_HALF_EVEN), f"{v} @index {month}")
            out.setdefault(v, f"{v} (no index)")
        elif item in C.USD_ITEMS:
            for month, fx in C.HALALAS_PER_USD.items():
                out.setdefault((v * fx / HUNDRED).quantize(CENT, ROUND_HALF_EVEN), f"{v} @FX {month}")
            out.setdefault(v, f"{v} (no FX)")
        else:
            out.setdefault(v, str(v))
    return sorted(out.items())


def decompose(ln: Line, exp: LinePrice) -> list[str] | None:
    """Differences (fewest first) that reproduce the billed single rate, or None."""
    if ln.rate_applied * ln.quantity != ln.amount:
        return None
    exp_pct = exp.parts[0].percent if len(exp.parts) == 1 else None
    best: list[str] | None = None
    for b, bdesc in _candidate_bases(ln.item_code):
        for zf, gf, upl, pct, dsc in itertools.product(_ZONES, [Decimal(1)] + _GROUNDS, _UPLIFTS, _PERCENTS, _DISCOUNTS):
            u = b * zf * gf * (1 + upl / HUNDRED) * Decimal(pct) / HUNDRED * (1 - dsc)
            if u.quantize(CENT, ROUND_HALF_UP) != ln.rate_applied:
                continue
            diffs = []
            if b != exp.base:
                diffs.append(f"base {bdesc} (contract {exp.base})")
            if zf != exp.zone_factor:
                diffs.append(f"zone x{zf} (contract x{exp.zone_factor})")
            if gf != exp.ground_factor:
                diffs.append(f"ground x{gf} (contract x{exp.ground_factor})")
            if upl != exp.uplift_percent:
                diffs.append(f"uplift {upl}% (contract {exp.uplift_percent}%)")
            if exp_pct is None or pct != exp_pct:
                diffs.append(f"band {pct}% (contract {[p.percent for p in exp.parts]})")
            if dsc != exp.discount:
                diffs.append(f"discount {dsc} (contract {exp.discount})")
            if best is None or len(diffs) < len(best):
                best = diffs
    # Cl 28: rounding after each step instead of once at the end.
    if len(exp.parts) == 1:
        r = exp.base
        for step in (exp.zone_factor, exp.ground_factor, 1 + exp.uplift_percent / HUNDRED):
            r = (r * step).quantize(CENT, ROUND_HALF_UP)
        r = (r * exp.parts[0].percent / HUNDRED * (1 - exp.discount)).quantize(CENT, ROUND_HALF_UP)
        if r == ln.rate_applied and (best is None or len(best) > 1):
            best = ["intermediate rounding (Clause 28)"]
    return best


def price_categories(ln: Line, app: Application, exp: LinePrice, diffs: list[str] | None) -> list[str]:
    """Map a decomposition to error categories (architecture C6)."""
    if ln.rate_applied * ln.quantity != ln.amount and len(exp.parts) == 1 and exp.parts[0].rate == ln.rate_applied:
        return ["line_arithmetic"]            # right rate, wrong multiplication
    if diffs is None:
        return ["line_arithmetic"]
    cats: list[str] = []
    for d in diffs:
        if d.startswith("intermediate"):
            cats.append("intermediate_rounding")
        elif d.startswith("base"):
            if "@index" in d or "@FX" in d:
                cats.append("index_or_fx_month_wrong")
            elif _is_retro_rate_taken_early(ln, app, Decimal(d.split()[1])):
                cats.append("retro_rate_taken_early")
            else:
                cats.append("rate_superseded")
        elif d.startswith("zone"):
            cats.append("zone_factor_wrong")
        elif d.startswith("ground"):
            cats.append("ground_factor_after_freeze" if ln.work_date >= C.GROUND_FREEZE_FROM else "ground_factor_wrong")
        elif d.startswith("uplift"):
            if "zone_factor_wrong" in cats:
                continue                        # the uplift moved because the zone was wrong
            if ln.night_work and ln.item_code in C.NIGHT_UPLIFT and C.ZONE_FACTORS[ln.zone] > C.NIGHT_ZONE_CAP:
                cats.append("night_uplift_zone_cap")
            elif d.startswith("uplift 35") and ln.work_date.weekday() not in C.REST_WEEKDAYS:
                cats.append("rest_day_uplift_wrong_day")
            else:
                cats.append("uplift_not_eligible")
        elif d.startswith("band"):
            if cats and cats[0] == "rate_superseded":
                continue                        # band differs only because the build-up is stale
            cats.append("band_not_applied")
        elif d.startswith("discount"):
            cats.append("discount_early" if "contract 0)" in d else "discount_omitted")
    return cats or ["line_arithmetic"]


def _is_retro_rate_taken_early(ln: Line, app: Application, billed_base: Decimal) -> bool:
    """A retrospective instrument's rate used by an application submitted before its issue."""
    for ins in C.INSTRUMENTS:
        if not ins.retrospective or app.application_date >= ins.issued:
            continue
        for rc in ins.rates:
            if rc.item == ln.item_code and rc.rate == billed_base:
                return True
    return False
