"""Parse site records and identify the priced item their words describe.

Clause 47A (p33) lets a record use the worker's own words, so the item is identified
from the record series plus the body wording and unit (architecture C3), never from an
item code. Each of the 26 body patterns found in the data is listed explicitly with the
position of its quantity. A body that matches no pattern is reported as
``unrecognised`` for manual review rather than guessed at.
"""
from __future__ import annotations

import datetime as dt
import os
import re
from dataclasses import dataclass, field
from decimal import Decimal

SERIES_TITLES = {
    "CT": "COMPACTION TEST CERTIFICATE", "CV": "CCTV SURVEY REPORT", "DW": "DEWATERING LOG",
    "DX": "DAILY EXCAVATION RECORD", "JS": "JOINT SURVEY SHEET", "MO": "METEOROLOGICAL RECORD",
    "PR": "CONCRETE POUR RECORD", "PS": "PLANT STANDING RECORD", "PT": "PRESSURE TEST CERTIFICATE"}

FOREMAN = "Signed (foreman)"
ENGINEER = "Countersigned (Engineer's representative)"

N = r"(\d+)"


def _depth_item(depth: Decimal) -> str | None:
    """P13 p13 / Schedule 1: trench depth decides A.12.020 / .030 / .040. A depth of
    exactly 2 m or 4 m fits two descriptions, so it is left unresolved (guideline 6)."""
    if depth in (Decimal(2), Decimal(4)):
        return None
    if depth > 4:
        return "A.12.040"
    if depth > 2:
        return "A.12.030"
    return "A.12.020"


@dataclass(frozen=True)
class BodyPattern:
    pattern_id: str
    series: str
    regex: re.Pattern
    item: str | None                  # fixed item, or None when decided by depth
    unit: str                         # the unit the record states the quantity in
    reason: str


def _p(pid, series, rx, item, unit, reason):
    return BodyPattern(pid, series, re.compile("^" + rx + "$"), item, unit, reason)


BODY_PATTERNS: list[BodyPattern] = [
    _p("CT1", "CT", rf"{N} square metres of sub-base in and compacted", "D.41.010", "m2", "sub-base, m2"),
    _p("CT2", "CT", rf"laid and rolled {N} m2 of Type 1", "D.41.010", "m2", "Type 1 sub-base, m2"),
    _p("CT3", "CT", rf"capping layer, {N} m2 placed and compacted", "D.41.040", "m2", "capping layer, m2"),
    _p("CT4", "CT", rf"brought in {N} cube of fill, compacted in layers", "A.14.010", "m3", "imported fill by volume"),
    _p("CT5", "CT", rf"placed and whacked {N} m3 of imported stone", "A.14.010", "m3", "imported granular fill by volume"),
    _p("CV1", "CV", rf"surveyed {N} m of the finished run with the camera", "C.35.010", "lm", "CCTV survey, linear metres"),
    _p("DW1", "DW", rf"pumps kept going {N} week this period", "A.16.010", "week", "wellpoint dewatering week"),
    _p("DW2", "DW", rf"wellpoints running, {N} week on the dewatering", "A.16.010", "week", "wellpoint dewatering week"),
    _p("DX1", "DX", rf"deep trench {N} m3, between two and four metres", "A.12.030", "m3", "trench 2-4 m deep"),
    _p("DX2", "DX", rf"trench dig {N} cube, (\d+(?:\.\d+)?) m deep section", None, "m3", "trench, depth stated"),
    _p("DX3", "DX", rf"trench over four metres, {N} m3 dug", "A.12.040", "m3", "trench over 4 m deep"),
    _p("JS1", "JS", rf"fixed {N} tonne of bar, cut and bent to schedule", "B.23.010", "tonne", "bar reinforcement, tonnes"),
    _p("JS2", "JS", rf"steel fixers placed {N} t of high yield bar", "B.23.010", "tonne", "high-yield bar, tonnes"),
    _p("JS3", "JS", rf"laid {N} m2 of A393 mesh with laps", "B.23.020", "m2", "A393 mesh, m2"),
    _p("JS4", "JS", rf"set out and agreed {N} chainage band with the Engineer", "E.52.010", "no.", "setting out by chainage band"),
    _p("MO1", "MO", rf"no work possible, weather, {N} hours standing", "E.51.010", "hour", "weather standby hours"),
    _p("MO2", "MO", rf"rained off -- crew and plant stood for {N} hours", "E.51.010", "hour", "weather standby hours"),
    _p("PR1", "PR", rf"foundation pour {N} cube, C32/40 off the truck", "B.21.020", "m3", "C32/40 foundations"),
    _p("PR2", "PR", rf"poured {N} m3 into the foundations, 32/40 mix", "B.21.020", "m3", "C32/40 foundations"),
    _p("PR3", "PR", rf"poured the slab, {N} cube of C32/40", "B.21.030", "m3", "C32/40 slab"),
    _p("PR4", "PR", rf"slab pour {N} m3, 32/40", "B.21.030", "m3", "C32/40 slab"),
    _p("PR5", "PR", rf"wall pour {N} m3, 32/40 mix", "B.21.040", "m3", "C32/40 wall"),
    _p("PS1", "PS", rf"excavator and driver held up {N} hours", "E.51.030", "hour", "excavator standing hours"),
    _p("PS2", "PS", rf"tracked machine stood idle {N} hours waiting on access", "E.51.030", "hour", "tracked plant standing hours"),
    _p("PT1", "PT", rf"built {N} large chamber, 1800 dia precast", "C.32.030", "no.", "1800 mm precast chamber"),
    _p("PT2", "PT", rf"laid {N} m of 400 ductile main", "C.31.020", "lm", "400 mm ductile iron main"),
]


@dataclass
class Record:
    ref: str
    series: str
    title: str
    fields: dict[str, str]
    body: str
    pattern_id: str = ""              # "" when the body matches no known pattern
    item: str | None = None           # None when unrecognised or ambiguous
    item_reason: str = ""
    quantity: int | None = None
    quantity_unit: str = ""
    area: str = ""
    date: dt.date | None = None       # the day, or the week beginning for DW
    week_days: list[dt.date] = field(default_factory=list)
    ground: str = ""
    signed: bool = False
    countersigned: bool = False
    problems: list[str] = field(default_factory=list)


def _signature_present(value: str) -> bool:
    """A blank or an underscore line is a missing signature (Cl 47 p8; P22 p14)."""
    v = value.strip()
    return bool(v) and "_" not in v


def _dmy(text: str) -> dt.date:
    d, m, y = text.strip().split("/")
    return dt.date(int(y), int(m), int(d))


def parse_record_text(ref: str, text: str) -> Record:
    raw = text.splitlines()
    title = raw[0].strip() if raw else ""
    fields: dict[str, str] = {}
    body_parts: list[str] = []
    for line in raw[1:]:
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z' ()]+):\s*(.*)$", line)
        if m and not re.match(r"^\s*\d", line):
            fields[m.group(1).strip()] = m.group(2).strip()
        else:
            body_parts.append(line.strip())
    series = ref[:2]
    rec = Record(ref, series, title, fields, " ".join(body_parts))
    if SERIES_TITLES.get(series) != title:
        rec.problems.append(f"title {title!r} does not match series {series}")
    if fields.get("Ticket", ref) != ref:
        rec.problems.append(f"ticket {fields.get('Ticket')!r} does not match file name")
    rec.area = fields.get("Area", "")
    rec.ground = fields.get("Ground", "").split()[0] if fields.get("Ground") else ""
    try:
        if "Date" in fields:
            rec.date = _dmy(fields["Date"])
        elif "Week beginning" in fields:
            rec.date = _dmy(fields["Week beginning"])
            rec.week_days = _days_on(rec.date, fields.get("Days on", ""))
    except ValueError:
        rec.problems.append("unreadable date")
    rec.signed = _signature_present(fields.get(FOREMAN, ""))
    rec.countersigned = _signature_present(fields.get(ENGINEER, ""))
    for pat in BODY_PATTERNS:
        if pat.series != series:
            continue
        m = pat.regex.match(rec.body)
        if not m:
            continue
        rec.pattern_id, rec.quantity, rec.quantity_unit = pat.pattern_id, int(m.group(1)), pat.unit
        if pat.item is None:
            depth = Decimal(m.group(2))
            rec.item, rec.item_reason = _depth_item(depth), f"trench {depth} m deep (P13)"
        else:
            rec.item, rec.item_reason = pat.item, pat.reason
        break
    return rec


def _days_on(week_beginning: dt.date, text: str) -> list[dt.date]:
    """'Mon 27/01, Tue 28/01, ...' -> dates inside [week beginning, +6]."""
    days = []
    for d, m in re.findall(r"(\d{2})/(\d{2})", text):
        for year in (week_beginning.year, week_beginning.year + 1):
            try:
                day = dt.date(year, int(m), int(d))
            except ValueError:
                continue
            if week_beginning <= day <= week_beginning + dt.timedelta(days=6):
                days.append(day)
                break
    return days


def load_records(records_dir: str) -> dict[str, Record]:
    out = {}
    for name in sorted(os.listdir(records_dir)):
        if name.endswith(".txt"):
            with open(os.path.join(records_dir, name), encoding="utf-8") as f:
                ref = name[:-4]
                out[ref] = parse_record_text(ref, f.read())
    return out
