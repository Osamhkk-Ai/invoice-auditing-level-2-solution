"""What one Daily Drilling Report supports: ``{code: quantity}`` for its well and day, with the basis.

Every rule names its clause. Nothing here looks at the invoice: the code a charge belongs to comes
from the report's words through Appendix G, never from the billed rate (guideline check 6).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from . import contract as C
from .config import EvidenceOptions
from .pricing import pd210_segments
from .reports import Report

LITERAL_LWD = {"LW-411": "LW-410", "LW-412": "LW-411"}   # alternative: "resistivity tool" read as resistivity


@dataclass
class WellFacts:
    """Facts about a well that need all of its reports (Clause 27)."""
    first_day: dt.date
    last_day: dt.date
    ran_lwd: bool


@dataclass
class Support:
    qty: dict[str, int] = field(default_factory=dict)
    basis: dict[str, str] = field(default_factory=dict)
    pd210_segments: list[tuple[int, int]] = field(default_factory=list)

    def add(self, code: str, n: int, why: str) -> None:
        self.qty[code] = self.qty.get(code, 0) + n
        self.basis[code] = why if code not in self.basis else f"{self.basis[code]}; {why}"


def lwd_codes(rep: Report, opt: EvidenceOptions) -> set[str]:
    codes = {c for c in rep.tools if c in C.LWD_METRE_TOOLS}
    if opt.lwd_map == "literal":
        codes = {LITERAL_LWD[c] for c in codes if c in LITERAL_LWD}
    return codes


def well_facts(reports: dict, opt: EvidenceOptions) -> dict[str, WellFacts]:
    out: dict[str, WellFacts] = {}
    for (well, day), rep in reports.items():
        w = out.get(well)
        lwd = bool(lwd_codes(rep, opt))
        if w is None:
            out[well] = WellFacts(day, day, lwd)
        else:
            w.first_day, w.last_day, w.ran_lwd = min(w.first_day, day), max(w.last_day, day), w.ran_lwd or lwd
    return out


def chargeable_hours(hours: int, rep: Report, opt: EvidenceOptions) -> tuple[int, str]:
    """Clause 21A: the first hour of each period in the hole is rig-up, not a Chargeable Hour."""
    if hours <= 0 or opt.chargeable_hour == "off":
        return hours, f"{hours} h as reported"
    if opt.chargeable_hour == "per_run" and not rep.run_first_day:
        return hours, f"{hours} h (not the run's first day)"
    return hours - 1, f"{hours} h reported - 1 rig-up hour (21A)"


def is_performance_day(rep: Report, opt: EvidenceOptions) -> bool:
    """Clause 23 / Appendix A: PD-210 only on the performance-drilled sections nominated in the call-off.
    The call-off is not in the data; the production proxy is a 12-1/4" or 8-1/2" day with a
    "performance engineer" (PD-201, Schedule 4: "performance-drilled sections") on the rig."""
    if rep.section not in C.PERFORMANCE_SECTIONS:
        return False
    if opt.pd210_rule == "perf_engineer":
        return "PD-201" in rep.crew
    if opt.pd210_rule == "section_only":
        return True
    if opt.pd210_rule == "perf_tools":
        return "PD-220" in rep.tools
    raise ValueError(opt.pd210_rule)


def supported(rep: Report, facts: WellFacts, opt: EvidenceOptions = EvidenceOptions()) -> Support:
    s = Support()
    op = rep.operating
    tools = set(rep.tools)
    for code, n in sorted(rep.crew.items()):                                  # Clause 22, P13
        s.add(code, n, f"Crew on tour: {n} (Cl 22)")
    for code in sorted(tools & C.DAY_RENTALS):                                 # Clause 28
        s.add(code, 1, "tool in the hole (Cl 28)")
    if "DD-120" in tools:                                                      # Clause 21
        if op:
            h, why = chargeable_hours(rep.circulating_hours, rep, opt)
            if opt.minimum_order == "minimum_then_minus":
                q, why = chargeable_hours(max(rep.circulating_hours, opt.dd120_minimum), rep, opt)
                why = f"minimum {opt.dd120_minimum} h first, then {why}"
            else:
                q = max(h, opt.dd120_minimum)
                if q != h:
                    why += f"; minimum {opt.dd120_minimum} h (Cl 21, P10)"
            s.add("DD-120", q, why)
        else:
            s.add("DD-121", 1, "rotary steerable in the hole on a Standby day (Cl 21, Sch.3 Pt4)")
    if op:                                                                     # Clause 30
        for code, name in C.COUNT_FIELDS.items():
            n = rep.count(name)
            why = f"{name}: {n} (Cl 30)"
            if code in C.HOURLY_SERVICES:
                n, why = chargeable_hours(n, rep, opt)
            if n:
                s.add(code, n, why)
        if rep.metres > 0:                                                     # Clauses 23-25
            span = f"{rep.depth_start}-{rep.depth_end} m"
            for code in sorted(lwd_codes(rep, opt)):
                s.add(code, rep.metres, f"metres drilled {span}, tool in the hole (Cl 24)")
            if "RM-511" in tools:
                s.add("RM-510", rep.metres, f"metres drilled {span}, underreamer in the hole (Cl 25)")
            if is_performance_day(rep, opt):
                s.pd210_segments = [(a, b) for a, b, _ in pd210_segments(rep.depth_start, rep.depth_end)]
                s.add("PD-210", rep.metres, f"metres drilled {span} on a performance-drilled day (Cl 23)")
    if "DD-110" in rep.run_tools and rep.run_last_day:                         # Clause 26
        s.add("DD-111", 1, f"last day of motor run {rep.run} (Cl 26)")
    if rep.source_carried and rep.run_first_day:
        s.add("LW-420", 1, f"first day of source run {rep.run} (Cl 26)")
    if rep.date == facts.first_day:                                            # Clause 27
        s.add("MB-701", 1, "first day on the well (Cl 27)")
        s.add("DD-140", 1, "first day on the well (Cl 27)")
    if rep.date == facts.last_day:
        s.add("MB-702", 1, "last day on the well (Cl 27)")
        if facts.ran_lwd:
            s.add("LW-430", 1, "last day on a well that ran LWD (Cl 27)")
    if rep.lost_code:                                                          # Clause 31, Part E
        s.add(rep.lost_code, 1, f"Part E: {rep.fields['Lost in hole tool']} lost (Cl 31)")
    if not op:                                                                 # Sch.3 Pt3
        for code in list(s.qty):
            if code not in C.FULL_WHATEVER_STATUS and code not in C.STANDBY_ONLY and C.STANDBY_PCT.get(code, 0) is None:
                del s.qty[code]
                s.basis[code] += "; not chargeable on Standby (Sch.3 Pt3)"
    if opt.apply_daily_limits:                                                 # Clause 22, Sch.3 Pt5
        for code, lim in C.DAILY_LIMIT.items():
            if s.qty.get(code, 0) > lim:
                s.qty[code] = lim
                s.basis[code] += f"; cut to the daily limit {lim} (Sch.3 Pt5)"
    return s
