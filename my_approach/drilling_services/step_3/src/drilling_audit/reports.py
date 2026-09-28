"""Parser for the Daily Drilling Report (Clause 15 p.5, Schedule 5 p.24, Appendix D p.30).

Each report is read against an explicit grammar: the header, Part A on every day, Part B on every
day of a run, and the conditional Parts C (gyro), D (source handling) and E (lost in hole), then the
two signatures. Free words (tools, crew, lost tool) are mapped with Appendix G only. Anything the
grammar or Appendix G does not know is kept on ``Report.problems`` so the audit can raise a query
for that day; nothing is guessed.
"""
from __future__ import annotations

import datetime as dt
import os
import re
from dataclasses import dataclass, field

from . import contract as C

SIGNATURE_BLANK = re.compile(r"^_*$")
PART_HEADING = re.compile(r"^PART ([A-E]) — (.+)$")
FIELD = re.compile(r"^([^:]{1,60}):\s?(.*)$")

HEADER_FIELDS = ("Report", "Contract", "Well", "Rig", "Date")
PART_FIELDS: dict[str, tuple[str, ...]] = {
    "A": ("Hole section", "Status", "Depth start (m MD)", "Depth end (m MD)", "Circulating hours", "BHA run",
          "In the hole", "Crew on tour", "Gyro surveys", "Pressure points", "Wiper trips",
          "Back-reaming hours", "Clean-out runs"),
    "B": ("Run", "Run first day", "Run last day", "Tools in run", "Run circulating hours", "Metres logged",
          "Metres reamed", "Radioactive source carried"),
    "C": ("Gyro surveys taken", "Surveyed section"),
    "D": ("Source run", "Sources handled", "Source handling certified"),
    "E": ("Lost in hole run", "Lost in hole tool", "Circulating hours accumulated on the well"),
}
SIGNATURE_FIELDS = ("Signed (Company Representative)", "Signed (lead directional driller)")
INT_FIELDS = {"Depth start (m MD)", "Depth end (m MD)", "Circulating hours", "BHA run", "Gyro surveys",
              "Pressure points", "Wiper trips", "Back-reaming hours", "Clean-out runs", "Run",
              "Run circulating hours", "Metres logged", "Metres reamed", "Gyro surveys taken", "Source run",
              "Lost in hole run", "Circulating hours accumulated on the well"}
STATUSES = ("Operating", "Standby")


@dataclass
class Report:
    file: str
    number: str = ""
    contract: str = ""
    well: str = ""
    rig: str = ""
    date: dt.date | None = None
    parts: tuple[str, ...] = ()
    fields: dict[str, str] = field(default_factory=dict)
    section: str = ""
    status: str = ""
    depth_start: int = 0
    depth_end: int = 0
    circulating_hours: int = 0
    run: int = 0
    tools: tuple[str, ...] = ()           # Appendix G codes of "In the hole"
    run_tools: tuple[str, ...] = ()       # Appendix G codes of "Tools in run"
    crew: dict[str, int] = field(default_factory=dict)
    lost_code: str | None = None          # Part E, via Appendix G
    signatures: tuple[str, str] = ("", "")
    problems: list[str] = field(default_factory=list)

    @property
    def key(self) -> tuple[str, dt.date | None]:
        return self.well, self.date

    @property
    def metres(self) -> int:
        return self.depth_end - self.depth_start

    @property
    def operating(self) -> bool:
        return self.status == "Operating"

    @property
    def signed(self) -> bool:
        """Clause 15: signed by the Company Representative and the lead directional driller."""
        return all(not SIGNATURE_BLANK.match(s) for s in self.signatures)

    @property
    def missing_signatures(self) -> list[str]:
        return [n for n, s in zip(SIGNATURE_FIELDS, self.signatures) if SIGNATURE_BLANK.match(s)]

    def count(self, name: str) -> int:
        return int(self.fields[name])

    @property
    def run_first_day(self) -> bool:
        return self.fields.get("Run first day") == self.fields.get("Date")

    @property
    def run_last_day(self) -> bool:
        return self.fields.get("Run last day") == self.fields.get("Date")

    @property
    def source_carried(self) -> bool:
        return self.fields.get("Radioactive source carried") == "Yes"


def _words(text: str) -> list[str]:
    return [t.strip() for t in text.split(",") if t.strip()]


def _map_tools(text: str, rep: Report, label: str) -> tuple[str, ...]:
    codes = []
    for word in _words(text):
        code = C.TOOL_WORDS.get(word)
        if code is None:
            rep.problems.append(f"{label}: unknown tool wording {word!r} (Appendix G)")
        else:
            codes.append(code)
    return tuple(codes)


def parse_text(text: str, name: str = "<report>") -> Report:
    rep = Report(file=name)
    lines = text.splitlines()
    if not lines or lines[0].strip() != "DAILY DRILLING REPORT":
        rep.problems.append("not a Daily Drilling Report")
    seen_parts: list[str] = []
    current = "header"
    for raw in lines[1:]:
        line = raw.strip()
        if not line:
            continue
        m = PART_HEADING.match(line)
        if m:
            current = m.group(1)
            if current in seen_parts:
                rep.problems.append(f"Part {current} appears twice")
            seen_parts.append(current)
            continue
        m = FIELD.match(line)
        if not m:
            rep.problems.append(f"unparsed line {line!r}")
            continue
        key, value = m.group(1).strip(), m.group(2).strip()
        allowed = (HEADER_FIELDS if current == "header" else PART_FIELDS.get(current, ())) + SIGNATURE_FIELDS
        if key not in allowed:
            rep.problems.append(f"field {key!r} not expected in {current}")
        if key in rep.fields:
            rep.problems.append(f"field {key!r} repeated")
        rep.fields[key] = value
    rep.parts = tuple(seen_parts)
    f = rep.fields
    for k in HEADER_FIELDS + SIGNATURE_FIELDS:
        if k not in f:
            rep.problems.append(f"missing {k!r}")
    for p in rep.parts:
        for k in PART_FIELDS[p]:
            if k not in f:
                rep.problems.append(f"Part {p}: missing {k!r}")
    for p in ("A", "B"):
        if p not in rep.parts:
            rep.problems.append(f"Part {p} absent (Schedule 5: completed every day / every day of a run)")
    for k in INT_FIELDS & set(f):
        if not re.fullmatch(r"\d+", f[k]):
            rep.problems.append(f"{k}: {f[k]!r} is not a whole number")
            f[k] = "0"
    rep.number, rep.contract = f.get("Report", ""), f.get("Contract", "")
    rep.well, rep.rig = f.get("Well", ""), f.get("Rig", "")
    try:
        rep.date = dt.datetime.strptime(f.get("Date", ""), "%d-%b-%Y").date()
    except ValueError:
        rep.problems.append(f"date {f.get('Date')!r} unreadable")
    rep.section = f.get("Hole section", "")
    if rep.section not in C.SECTION_FACTOR:
        rep.problems.append(f"hole section {rep.section!r} not in Schedule 3 Part 1")
    rep.status = f.get("Status", "")
    if rep.status not in STATUSES:
        rep.problems.append(f"status {rep.status!r} is neither Operating nor Standby")
    rep.depth_start = int(f.get("Depth start (m MD)", "0"))
    rep.depth_end = int(f.get("Depth end (m MD)", "0"))
    if rep.depth_end < rep.depth_start:
        rep.problems.append("depth end above depth start")
    rep.circulating_hours = int(f.get("Circulating hours", "0"))
    rep.run = int(f.get("BHA run", "0"))
    rep.tools = _map_tools(f.get("In the hole", ""), rep, "In the hole")
    rep.run_tools = _map_tools(f.get("Tools in run", ""), rep, "Tools in run")
    for item in _words(f.get("Crew on tour", "")):
        m = re.fullmatch(r"(\d+)\s+(.+)", item)
        code = C.CREW_WORDS.get(m.group(2)) if m else None
        if code is None:
            rep.problems.append(f"Crew on tour: unknown wording {item!r} (Appendix G)")
            continue
        rep.crew[code] = rep.crew.get(code, 0) + int(m.group(1))
    if "E" in rep.parts:
        rep.lost_code = C.LOST_WORDS.get(f.get("Lost in hole tool", ""))
        if rep.lost_code is None:
            rep.problems.append(f"Lost in hole tool: unknown wording {f.get('Lost in hole tool')!r}")
    rep.signatures = (f.get(SIGNATURE_FIELDS[0], ""), f.get(SIGNATURE_FIELDS[1], ""))
    if rep.date and rep.well and rep.number != f"DDR-{rep.well[-3:]}-{rep.date:%Y%m%d}":
        rep.problems.append(f"report number {rep.number!r} does not match well and date (Clause 19A)")
    if rep.contract != C.CONTRACT_REF:
        rep.problems.append(f"report names contract {rep.contract!r}")
    return rep


def parse_file(path: str) -> Report:
    with open(path, encoding="utf-8") as f:
        return parse_text(f.read(), os.path.basename(path))


def load_reports(records_dir: str) -> dict[tuple[str, dt.date], Report]:
    out: dict[tuple[str, dt.date], Report] = {}
    for name in sorted(os.listdir(records_dir)):
        if not name.endswith(".txt"):
            continue
        rep = parse_file(os.path.join(records_dir, name))
        expected = f"DDR_{rep.well}_{rep.date:%Y%m%d}.txt" if rep.date else None
        if name != expected:
            rep.problems.append(f"file name does not match its well and date ({expected})")
        if rep.key in out:
            raise ValueError(f"two reports for {rep.key}: {out[rep.key].file}, {name}")
        out[rep.key] = rep
    return out
