"""What each Daily Drilling Report supports, as (code -> quantity) per well and day.

Each rule cites the clause it implements. Options let the checks swap one interpretation at a time.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from common import (DAILY_LIMIT, FULL_ON_STANDBY, LOST_TERMS, STANDBY_PCT, TOOL_TERMS)

DAY_RENTALS = {"DD-110", "HC-601", "HC-620", "HC-640", "MW-310", "MW-320", "MW-330", "PD-220", "PD-230",
               "RM-511", "RM-520"}
METRE_TOOLS = {"LW-410", "LW-411", "LW-412"}


@dataclass(frozen=True)
class EvidenceOptions:
    dd120_minimum: int = 6              # Clause 21 / Sch.3 Pt7 / P10
    chargeable_hour_minus_one: bool = False  # Clause 21A (tested as an alternative)
    pd210_rule: str = "perf_engineer"   # which days carry PD-210: see check_03 for alternatives
    lwd_map: str = "appendix_g"         # "appendix_g" or "literal" (resistivity tool -> LW-410 ...)
    apply_daily_limits: bool = True     # Clause 22 / Sch.3 Pt5


LITERAL_LWD = {"resistivity tool": "LW-410", "density-neutron": "LW-411", "gamma tool": None}


def lwd_codes(rep, opt: EvidenceOptions) -> set:
    if opt.lwd_map == "literal":
        return {LITERAL_LWD[t] for t in rep.tools if t in LITERAL_LWD and LITERAL_LWD[t]}
    return {TOOL_TERMS[t] for t in rep.tools if TOOL_TERMS.get(t) in METRE_TOOLS}


def well_spans(reports: dict) -> dict:
    spans = {}
    for (well, day) in reports:
        a, b = spans.get(well, (day, day))
        spans[well] = (min(a, day), max(b, day))
    return spans


def supported(rep, spans: dict, well_has_lwd: set, opt: EvidenceOptions = EvidenceOptions()) -> dict:
    """Return {code: qty} the report supports for its day (before pricing)."""
    s: dict[str, int] = defaultdict(int)
    op = rep.status == "Operating"
    tools = rep.tool_codes
    f = rep.fields

    for code, n in rep.crew.items():                       # Clause 22, Sch.8
        s[code] += n
    for code in tools & DAY_RENTALS:                       # Clause 28
        s[code] += 1
    if "DD-120" in tools:                                  # Clause 21
        if op:
            h = rep.circ - (1 if opt.chargeable_hour_minus_one and rep.circ > 0 else 0)
            s["DD-120"] += max(h, opt.dd120_minimum)
        else:
            s["DD-121"] += 1
    if op:                                                 # Clause 30 counts, Operating day only
        for code, key in (("DD-130", "Gyro surveys"), ("LW-413", "Pressure points"), ("HC-610", "Wiper trips"),
                          ("RM-530", "Back-reaming hours"), ("HC-630", "Clean-out runs")):
            n = rep.i(key)
            if code == "RM-530" and opt.chargeable_hour_minus_one and n > 0:
                n -= 1                                     # Clause 21A: RM-530 is charged by the hour
            if n:
                s[code] += n
        if rep.metres > 0:                                 # Clauses 24, 25
            for code in lwd_codes(rep, opt):
                s[code] += rep.metres
            if "RM-511" in tools:
                s["RM-510"] += rep.metres
            if pd210_day(rep, opt):
                s["PD-210"] += rep.metres                  # split into bands at pricing time (Clause 23)
    # Clause 26: per-run charges
    if "DD-110" in {TOOL_TERMS.get(t) for t in rep.tools_run} and f["Run last day"] == f["Date"]:
        s["DD-111"] += 1
    if f["Radioactive source carried"] == "Yes" and f["Run first day"] == f["Date"]:
        s["LW-420"] += 1
    # Clause 27: per-well charges
    first, last = spans[rep.well]
    if rep.date == first:
        s["MB-701"] += 1
        s["DD-140"] += 1
    if rep.date == last:
        s["MB-702"] += 1
        if rep.well in well_has_lwd:
            s["LW-430"] += 1
    # Clause 31: lost in hole (Part E)
    if "Lost in hole tool" in f:
        s[LOST_TERMS[f["Lost in hole tool"]]] += 1
    # Standby exclusions (Sch.3 Pt3)
    if not op:
        for code in list(s):
            if code not in FULL_ON_STANDBY and STANDBY_PCT.get(code, 0) is None:
                del s[code]
    if opt.apply_daily_limits:
        for code, lim in DAILY_LIMIT.items():
            if s.get(code, 0) > lim:
                s[code] = lim
    return dict(s)


def pd210_day(rep, opt: EvidenceOptions) -> bool:
    """PD-210 only on performance-drilled sections nominated in the call-off (Clause 23, App. A).
    The call-off is not in the data, so a proxy is needed; alternatives are compared in check_03."""
    if rep.section not in ('12-1/4"', '8-1/2"'):
        return False
    if opt.pd210_rule == "perf_engineer":
        return "PD-201" in rep.crew
    if opt.pd210_rule == "section_only":
        return True
    if opt.pd210_rule == "perf_tools":
        return "PD-220" in rep.tool_codes
    raise ValueError(opt.pd210_rule)
