"""Rules that depend on lines in other applications (checks 9 and 10).

All of them run over the whole contract in one global order: work date, then
application number, then line number. Clause 30 (p6) states exactly this order for the
cumulative count ("measurements executed on the same date are taken in order of
application number and then line number"); the same order decides which of two
measurements is "the later" under Clause 44.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

from . import contract as C
from .config import AuditConfig
from .evidence import LineAssessment
from .loader import Line


def global_order_key(ln: Line) -> tuple:
    return (ln.work_date, ln.application_no, ln.line_no)


WEEKLY_DUPLICATE_ITEMS = {
    "A16": {"A.16.010"}, "A16_same_app": {"A.16.010"}, "A16+E54": {"A.16.010", "E.54.010"}}


def apply_cross_checks(assessments: dict[str, LineAssessment], cfg: AuditConfig) -> None:
    ordered = sorted(assessments.values(), key=lambda la: global_order_key(la.line))

    # Cl 44: the same item, work area and date more than once -> the later disallowed in full.
    first_seen: dict[tuple, str] = {}
    for la in ordered:
        ln = la.line
        key = (ln.item_code, ln.site, ln.work_date)
        if key in first_seen:
            la.zero("duplicate_measurement", f"same item, work area and date as {first_seen[key]}")
        else:
            first_seen[key] = ln.line_ref

    # A record evidences one measurement. A non-weekly record already relied on by an
    # earlier supported line cannot support a second one (weekly records: see Q2).
    record_used_by: dict[str, str] = {}
    for la in ordered:
        ln = la.line
        if la.evidence_status != "ok" or ln.item_code in C.WEEKLY_RECORD_ITEMS or la.supported_qty == 0:
            continue
        if ln.record_ref in record_used_by:
            la.zero("record_reused", f"{ln.record_ref} already evidences {record_used_by[ln.record_ref]}")
        else:
            record_used_by[ln.record_ref] = ln.line_ref

    # Cl 31 / Sch 4 Pt 4: daily limit per work area per day; the excess is not carried forward.
    used: dict[tuple, int] = defaultdict(int)
    for la in ordered:
        ln = la.line
        limit = C.DAILY_LIMITS.get(ln.item_code)
        if limit is None:
            continue
        key = (ln.item_code, ln.site, ln.work_date)
        room = max(limit - used[key], 0)
        if la.supported_qty > room:
            la.reduce("daily_limit_exceeded",
                      f"limit {limit}/day; {used[key]} already measured that day; {la.supported_qty} -> {room}", room)
        used[key] += la.supported_qty

    # Index of supported measurements by (work area, day) for P19 and P21.
    by_site_day: dict[tuple, list[LineAssessment]] = defaultdict(list)
    for la in ordered:
        if la.supported_qty > 0:
            by_site_day[(la.line.site, la.line.work_date)].append(la)

    # P19 / Cl 32 / Sch 4 Pt 5: A.14.020 not measurable within two days of A.14.010 (days 0..2).
    for excluded, excluding in C.MUTUALLY_EXCLUSIVE:
        for la in ordered:
            ln = la.line
            if ln.item_code != excluded or la.supported_qty == 0:
                continue
            for back in cfg.p19_window_days:
                day = ln.work_date - dt.timedelta(days=back)
                hits = [x for x in by_site_day.get((ln.site, day), []) if x.line.item_code == excluding]
                if hits:
                    la.zero("mutually_exclusive_item",
                            f"{excluding} measured on {day} ({hits[0].line.line_ref}), day +{back}")
                    break

    # Q2 alternatives only: one week per item, work area and calendar week.
    if cfg.weekly_duplicate:
        codes = WEEKLY_DUPLICATE_ITEMS[cfg.weekly_duplicate]
        seen_week: dict[tuple, str] = {}
        for la in ordered:
            ln = la.line
            if ln.item_code not in codes or la.supported_qty == 0:
                continue
            monday = ln.work_date - dt.timedelta(days=ln.work_date.weekday())
            key = (ln.item_code, ln.site, monday)
            if cfg.weekly_duplicate == "A16_same_app":
                key += (ln.application_no,)
            if key in seen_week:
                la.zero("duplicate_week", f"week of {monday} already measured by {seen_week[key]}")
            else:
                seen_week[key] = ln.line_ref

    # P21: E.51.020 not measurable on a day a surfacing item is measured for that work area.
    for la in ordered:
        ln = la.line
        if ln.item_code != C.P21_EXCLUDED_ITEM or la.supported_qty == 0:
            continue
        surfacing = [x for x in by_site_day.get((ln.site, ln.work_date), [])
                     if x.line.item_code in C.P21_SURFACING_ITEMS]
        if surfacing:
            la.zero("traffic_management_during_surfacing",
                    f"{surfacing[0].line.item_code} measured the same day ({surfacing[0].line.line_ref})")
