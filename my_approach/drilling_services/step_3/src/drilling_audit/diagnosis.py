"""Name the mis-application that reproduces a wrong billed rate (for the audit trail and error analysis).

Diagnosis only: the expected amount always comes from the contract build-up in ``audit.py``.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import replace
from decimal import Decimal

from . import contract as C
from .config import PricingOptions
from .money import r2
from .pricing import build_rate, lih_value

D = Decimal


def _br(code, day, section, status, cls, idate, opt=PricingOptions()):
    return build_rate(code, day, section, status, cls, idate, opt).rate


def candidates(code: str, day: dt.date, section: str, status: str, cls: str, idate: dt.date,
               hours: int | None = None) -> dict[str, Decimal | None]:
    out: dict[str, Decimal | None] = {}
    if code in C.LOST_IN_HOLE:
        out["lost in hole at Schedule 6 USD, no depreciation"] = C.LIH_USD_SCHEDULE_6[code]
        out["lost in hole at Schedule 6 USD (not Sch.2D SAR)"] = lih_value(code, day, hours, PricingOptions(lih_from_sar=False)).rate
        dep = min(hours // 25, 50)
        for m, hal in C.HALALAS_PER_USD.items():
            if m != C.ym(day):
                out[f"lost in hole converted at the {m} exchange rate"] = r2(r2(C.LIH_SAR[code] * 100 / hal) * (100 - dep) / 100)
        return out
    if code == "PD-210":
        for _, _, r in C.PD210_BANDS:
            out[f"PD-210 at band rate {r}"] = r
            out[f"PD-210 at band rate {r} with a class factor"] = r2(r * C.CLASS_FACTOR[cls])
        return out
    if code in C.INDEXED:
        for m in (-1, 1):
            other = day.replace(day=15) + dt.timedelta(days=30 * m)
            if C.ym(other) in C.RIG_SERVICES_INDEX:
                out[f"index of the {'previous' if m < 0 else 'next'} month"] = _br(code, other, section, status, cls, idate)
    out["standby percentage ignored"] = _br(code, day, section, "Operating", cls, idate) if status == "Standby" else None
    out["section factor applied on a Standby day"] = _br(code, day, section, status, cls, idate,
                                                         PricingOptions(no_section_factor_on_standby=False))
    out["superseded instrument rate (Supplement 1 missed)"] = _br(code, dt.date(2025, 6, 30), section, status, cls, idate) \
        if day >= dt.date(2025, 7, 1) and day.year == 2025 else None
    out["superseded instrument rate (previous year)"] = _br(code, day - dt.timedelta(days=365), section, status, cls, idate) \
        if day.year == 2026 else None
    base = _br(code, day, section, status, cls, idate)
    if base is not None and code in {c for i in C.INSTRUMENTS for c in i.discount_codes}:
        for pct in (D("0.04"), D("0.07")):
            out[f"rate discount {pct} taken before it started"] = r2(base * (1 - pct))
        if day >= dt.date(2026, 4, 1):
            out["rate discount omitted"] = _br(code, dt.date(2026, 3, 31), section, status, cls, idate)
    out["A3 rate / pre-A3 rate on the wrong side of the issue date"] = _br(
        code, day, section, status, cls, dt.date(2026, 8, 17) if idate < dt.date(2026, 8, 17) else dt.date(2026, 8, 1))
    for c2 in C.CLASS_FACTOR:
        if c2 != cls:
            out[f"class factor of {c2}"] = _br(code, day, section, status, c2, idate)
    for s2 in C.SECTION_FACTOR:
        if s2 != section:
            out[f"section factor of {s2}"] = _br(code, day, s2, status, cls, idate)
    out["S2 monthly rate instead of A3"] = _br(code, day, section, status, cls, idate, PricingOptions(later_issued_governs=False))
    if code == "MW-310":   # labelled search over the index / section / class / standby steps
        b0 = C.SCHEDULE_1[code][2]
        for idx in [None] + sorted(C.RIG_SERVICES_INDEX):
            b = b0 if idx is None else r2(b0 * C.RIG_SERVICES_INDEX[idx] / 100)
            for sec2 in list(C.SECTION_FACTOR) + [None]:
                r1 = b if sec2 is None else r2(b * C.SECTION_FACTOR[sec2])
                for cls2 in C.CLASS_FACTOR:
                    rc = r2(r1 * C.CLASS_FACTOR[cls2])
                    for sb in (False, True):
                        v = r2(rc * D("0.5")) if sb else rc
                        parts = []
                        if idx is None:
                            parts.append("index omitted")
                        elif idx != C.ym(day):
                            parts.append(f"index of {idx}")
                        if sec2 != (None if status == "Standby" else section):
                            parts.append(f"section {sec2}" if sec2 else "no section factor")
                        if cls2 != cls:
                            parts.append(f"class {cls2}")
                        if sb != (status == "Standby"):
                            parts.append("standby % " + ("applied" if sb else "omitted"))
                        if parts:
                            out.setdefault("MW-310: " + "; ".join(parts), v)
    return out


def explain(result, invoice) -> list[str]:
    """Mechanisms that reproduce the billed rate of a ``rate_differs`` line, simplest first."""
    ln, rep = result.line, result.report
    hours = rep.count("Circulating hours accumulated on the well") if ln.code in C.LOST_IN_HOLE else None
    cand = candidates(ln.code, ln.service_date, rep.section, rep.status, invoice.well_class, invoice.invoice_date, hours)
    return sorted((k for k, v in cand.items() if v is not None and v == ln.rate), key=lambda k: (k.count(";"), k))
