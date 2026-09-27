"""Shared loaders, report parser and contract tables for the DDS-2025-118 verification checks.

Analysis tooling only; not the production auditor. Every contract figure below cites the
PDF page it was read from (page numbers of DDS-2025-118.pdf, checked against the scan).
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DATA = ROOT / "invoice-auditing-level-2" / "drilling_services"
INVOICES_CSV = DATA / "invoices" / "invoices.csv"
LINES_CSV = DATA / "invoices" / "invoice_lines.csv"
RECORDS_DIR = DATA / "records"
TEMPLATE_CSV = ROOT / "invoice-auditing-level-2" / "submission_template.csv"
OUT_DIR = Path(__file__).resolve().parent / "out"

CENT = Decimal("0.01")
D = Decimal


def r2(x: Decimal, mode=ROUND_HALF_EVEN) -> Decimal:
    """Clause 17 (p.6): round each step to the cent, half to even."""
    return x.quantize(CENT, rounding=mode)


def pdate(s: str) -> dt.date | None:
    return dt.datetime.strptime(s, "%d-%b-%Y").date() if s else None


def dec(s: str) -> Decimal | None:
    return Decimal(s) if s not in ("", None) else None


# ---------------------------------------------------------------- data loading

def load_invoices() -> dict[str, dict]:
    out = {}
    with open(INVOICES_CSV, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            for k in ("period_start", "period_end", "invoice_date"):
                r[k + "_d"] = pdate(r[k])
            for k in ("net_amount", "vat_amount", "invoice_total", "adjustment"):
                r[k + "_d"] = dec(r[k])
            out[r["invoice_no"]] = r
    return out


def load_lines() -> list[dict]:
    out = []
    with open(LINES_CSV, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            r["date"] = pdate(r["service_date"])
            r["qty"] = dec(r["quantity"])
            r["rate"] = dec(r["unit_rate"])
            r["amt"] = dec(r["amount"])
            r["dfrom"] = int(r["depth_from_m"]) if r["depth_from_m"] else None
            r["dto"] = int(r["depth_to_m"]) if r["depth_to_m"] else None
            out.append(r)
    return out


# ---------------------------------------------------------------- report parser

# Appendix G (p.36): field words -> Schedule 1 codes. Printed pairings are used as-is,
# including the non-obvious ones (gamma tool -> LW-410, resistivity tool -> LW-411,
# density-neutron -> LW-412, float sub -> HC-640, survey package -> MW-320).
TOOL_TERMS = {
    "mud motor": "DD-110",
    "rotary steerable": "DD-120",
    "circulating sub": "HC-601",
    "drilling jars": "HC-620",
    "float sub": "HC-640",
    "gamma tool": "LW-410",
    "resistivity tool": "LW-411",
    "density-neutron": "LW-412",
    "MWD collar": "MW-310",
    "survey package": "MW-320",
    "real-time link": "MW-330",
    "bit and reamer": "PD-220",
    "hydraulics package": "PD-230",
    "hole opener": "RM-511",
    "stabiliser string": "RM-520",
}
CREW_TERMS = {
    "directional hands": "DD-101",
    "night man": "DD-102",
    "MWD engineers": "MW-301",
    "logging engineers": "LW-401",
    "performance engineer": "PD-201",
}
# Appendix G lost-in-hole words (p.36); "gamma tool" -> LH-714 per the printed row.
LOST_TERMS = {"mud motor": "LH-711", "rotary steerable": "LH-712", "MWD collar": "LH-713", "gamma tool": "LH-714"}

BLANK_SIG = re.compile(r"^_+$")


@dataclass
class Report:
    file: str
    fields: dict
    parts: list
    well: str = ""
    date: dt.date | None = None
    number: str = ""
    section: str = ""
    status: str = ""
    dstart: int = 0
    dend: int = 0
    circ: int = 0
    run: int = 0
    tools: list = field(default_factory=list)
    tools_run: list = field(default_factory=list)
    crew: dict = field(default_factory=dict)
    unknown_terms: list = field(default_factory=list)

    @property
    def metres(self) -> int:
        return self.dend - self.dstart

    @property
    def signed(self) -> bool:
        a = self.fields.get("Signed (Company Representative)", "")
        b = self.fields.get("Signed (lead directional driller)", "")
        return bool(a) and bool(b) and not BLANK_SIG.match(a) and not BLANK_SIG.match(b)

    def i(self, k: str) -> int:
        return int(self.fields[k])

    @property
    def tool_codes(self) -> set:
        return {TOOL_TERMS[t] for t in self.tools if t in TOOL_TERMS}


def parse_report(path: Path) -> Report:
    text = path.read_text(encoding="utf-8")
    fields, parts = {}, []
    for line in text.splitlines():
        if line.startswith("PART "):
            parts.append(line[5])
            continue
        m = re.match(r"^([^:]{1,60}):\s?(.*)$", line)
        if m:
            fields[m.group(1).strip()] = m.group(2).strip()
    r = Report(file=path.name, fields=fields, parts=parts)
    r.well = fields["Well"]
    r.date = pdate(fields["Date"])
    r.number = fields["Report"]
    r.section = fields["Hole section"]
    r.status = fields["Status"]
    r.dstart = int(fields["Depth start (m MD)"])
    r.dend = int(fields["Depth end (m MD)"])
    r.circ = int(fields["Circulating hours"])
    r.run = int(fields["BHA run"])
    r.tools = [t.strip() for t in fields["In the hole"].split(",") if t.strip()]
    r.tools_run = [t.strip() for t in fields["Tools in run"].split(",") if t.strip()]
    for item in fields["Crew on tour"].split(","):
        m = re.match(r"^\s*(\d+)\s+(.+?)\s*$", item)
        if not m:
            r.unknown_terms.append(item)
            continue
        code = CREW_TERMS.get(m.group(2))
        if code is None:
            r.unknown_terms.append(m.group(2))
        else:
            r.crew[code] = r.crew.get(code, 0) + int(m.group(1))
    r.unknown_terms += [t for t in r.tools + r.tools_run if t not in TOOL_TERMS]
    return r


def load_reports() -> dict[tuple, Report]:
    out = {}
    for name in sorted(os.listdir(RECORDS_DIR)):
        rep = parse_report(RECORDS_DIR / name)
        key = (rep.well, rep.date)
        assert key not in out, f"two reports for {key}"
        out[key] = rep
    return out


def ref_to_key(report_ref: str, well: str):
    """DDR-<well number>-<yyyymmdd> (Clause 19A, p.35) -> (well, date) of the report file."""
    m = re.match(r"^DDR-(\d{3})-(\d{8})$", report_ref or "")
    if not m or well[-3:] != m.group(1):
        return None
    return well, dt.datetime.strptime(m.group(2), "%Y%m%d").date()


# ---------------------------------------------------------------- contract tables

# Schedule 1 (pp.15-16): (unit, rate)
SCHEDULE_1 = {
    "DD-101": ("person-day", "1847.35"), "DD-102": ("day", "948.60"), "DD-110": ("day", "1417.75"),
    "DD-111": ("run", "3589.45"), "DD-120": ("hour", "384.15"), "DD-121": ("day", "2893.65"),
    "DD-130": ("survey", "2446.15"), "DD-140": ("well", "12489.50"),
    "PD-201": ("person-day", "2094.85"), "PD-210": ("metre", None), "PD-220": ("day", "1148.35"),
    "PD-230": ("day", "639.15"),
    "MW-301": ("person-day", "1646.55"), "MW-310": ("day", "2245.85"), "MW-320": ("day", "779.65"),
    "MW-330": ("day", "309.75"),
    "LW-401": ("person-day", "1898.45"), "LW-410": ("metre", "11.37"), "LW-411": ("metre", "16.83"),
    "LW-412": ("metre", "13.29"), "LW-413": ("point", "1849.65"), "LW-420": ("run", "2746.55"),
    "LW-430": ("well", "8394.75"),
    "RM-510": ("metre", "38.45"), "RM-511": ("day", "1379.15"), "RM-520": ("day", "419.85"),
    "RM-530": ("hour", "264.55"),
    "HC-601": ("day", "689.35"), "HC-610": ("trip", "1947.15"), "HC-620": ("day", "539.65"),
    "HC-630": ("run", "4295.85"), "HC-640": ("day", "719.55"),
    "MB-701": ("well", "18497.50"), "MB-702": ("well", "14196.25"),
    "LH-711": ("each", None), "LH-712": ("each", None), "LH-713": ("each", None), "LH-714": ("each", None),
}
PERSONNEL = {"DD-101", "DD-102", "MW-301", "LW-401", "PD-201"}

# Schedule 2 (p.17): PD-210 depth bands, boundary depth belongs to the shallower band.
PD210_BANDS = [(0, 1500, D("42.35")), (1500, 3000, D("58.15")), (3000, 4500, D("76.45")), (4500, 10**9, D("98.70"))]

# Schedule 2C (p.18): Rig Services Index, base 100.00, for MW-310 and HC-620 (Clause 17A p.35).
INDEXED = {"MW-310", "HC-620"}
RSI = dict(zip(
    [f"2025-{m:02d}" for m in range(1, 13)] + [f"2026-{m:02d}" for m in range(1, 13)],
    map(D, "100.00 100.70 101.50 102.30 103.10 103.60 104.80 105.40 104.90 106.20 107.10 108.00 "
           "109.30 110.00 110.60 111.40 110.90 112.20 113.00 112.60 113.90 114.70 115.30 116.10".split())))

# Schedule 2D (p.19): SAR replacement values and halalas per USD, converted under Clause 31A (p.35).
LIH_SAR = {"LH-711": D("543750.00"), "LH-712": D("4687500.00"), "LH-713": D("1443750.00"), "LH-714": D("1950000.00")}
LIH_USD_SCHED6 = {"LH-711": D("145000.00"), "LH-712": D("1250000.00"), "LH-713": D("385000.00"), "LH-714": D("520000.00")}
HALALAS = dict(zip(
    [f"2025-{m:02d}" for m in range(1, 13)] + [f"2026-{m:02d}" for m in range(1, 13)],
    map(D, "375.00 375.10 375.00 374.90 375.20 375.30 375.10 375.00 374.80 375.40 375.60 375.50 "
           "376.00 375.80 375.90 376.20 376.40 376.10 375.70 376.30 376.60 376.80 377.00 376.50".split())))

# Schedule 3 Part 1 (p.20): hole-section factors and section-rated services.
SECTION_FACTOR = {'26"': D("1.315"), '17-1/2"': D("1.145"), '12-1/4"': D("1.00"), '8-1/2"': D("0.945"), '6"': D("0.885")}
SECTION_RATED = {"DD-110", "DD-120", "PD-220", "MW-310", "RM-510", "RM-511"}
# Schedule 3 Part 2 (p.20): well-class factors and class-rated services.
CLASS_FACTOR = {"Standard": D("1.00"), "Extended Reach": D("1.175"), "HPHT": D("1.325")}
CLASS_RATED = {"DD-120", "PD-210", "MW-310", "MW-320", "LW-410", "LW-411", "LW-412", "LW-413"}
# Schedule 3 Part 3 (pp.20-21): standby percentage; None = not chargeable on a Standby day.
STANDBY_PCT = {
    "DD-101": D("0.80"), "DD-102": D("1.00"), "DD-110": D("0.50"), "DD-111": D("1.00"), "DD-120": None,
    "DD-130": None, "PD-201": D("0.80"), "PD-210": None, "PD-220": D("0.50"), "PD-230": D("0.50"),
    "MW-301": D("0.80"), "MW-310": D("0.50"), "MW-320": D("0.50"), "MW-330": D("1.00"), "LW-401": D("0.80"),
    "LW-410": None, "LW-411": None, "LW-412": None, "LW-413": None, "LW-420": D("1.00"), "RM-510": None,
    "RM-511": D("0.50"), "RM-520": D("0.50"), "RM-530": None, "HC-601": D("0.50"), "HC-610": None,
    "HC-620": D("0.50"), "HC-630": None, "HC-640": None,
}
# Per-well / loss items are "charged in full whatever the status" (Sch.3 Pt3 intro, p.20); DD-121 is
# standby-only (Pt4, p.21) and has no percentage row.
FULL_ON_STANDBY = {"DD-140", "LW-430", "MB-701", "MB-702", "LH-711", "LH-712", "LH-713", "LH-714", "DD-121"}
# Schedule 3 Part 5 (pp.21-22): daily limits.
DAILY_LIMIT = {
    "DD-101": 2, "DD-102": 1, "DD-110": 1, "DD-120": 24, "DD-121": 1, "DD-130": 3, "PD-201": 1, "PD-220": 1,
    "PD-230": 1, "MW-301": 2, "MW-310": 1, "MW-320": 1, "MW-330": 1, "LW-401": 1, "LW-413": 12, "RM-511": 1,
    "RM-520": 1, "RM-530": 24, "HC-601": 1, "HC-610": 2, "HC-620": 1, "HC-640": 1,
}
ONCE_PER_WELL = {"DD-140", "LW-430", "MB-701", "MB-702"}  # Sch.3 Pt6 (p.22), Clause 27 (p.7)

# Instruments (Schedule of Variations p.37; instruments pp.38-42).
INSTRUMENTS = [  # (name, issued, effective)
    ("S1", dt.date(2025, 5, 19), dt.date(2025, 7, 1)),
    ("A1", dt.date(2025, 11, 7), dt.date(2026, 1, 1)),
    ("S2", dt.date(2026, 2, 24), dt.date(2026, 4, 1)),
    ("A2", dt.date(2026, 5, 21), dt.date(2026, 7, 1)),
    ("A3", dt.date(2026, 8, 17), dt.date(2026, 2, 1)),
]
A3_ISSUED = dt.date(2026, 8, 17)
# Flat substitutions: code -> list of (instrument, effective, rate)
FLAT_RATES = {
    "DD-120": [("S1", dt.date(2025, 7, 1), D("398.50")), ("A3", dt.date(2026, 2, 1), D("416.00"))],
    "DD-121": [("S1", dt.date(2025, 7, 1), D("2984.00"))],
    "DD-101": [("A1", dt.date(2026, 1, 1), D("1916.50")), ("A3", dt.date(2026, 2, 1), D("1954.00"))],
    "MW-301": [("A1", dt.date(2026, 1, 1), D("1708.00")), ("A2", dt.date(2026, 7, 1), D("1763.00"))],
    "LW-401": [("A1", dt.date(2026, 1, 1), D("1969.00"))],
    "MB-701": [("A2", dt.date(2026, 7, 1), D("19237.00"))],
}
# Monthly re-publications: S1 1.2 HC-601 (p.38) and S2 2.1 DD-120 (p.40); last published carries forward.
MONTHLY = {
    "HC-601": ("S1", {"2025-07": "701.50", "2025-08": "714.00", "2025-09": "722.60", "2025-10": "719.80",
                      "2025-11": "731.00", "2025-12": "736.40"}),
    "DD-120": ("S2", {"2026-04": "406.00", "2026-05": "411.50", "2026-06": "411.50", "2026-07": "423.00",
                      "2026-08": "429.50", "2026-09": "434.00", "2026-10": "434.00", "2026-11": "441.00",
                      "2026-12": "447.50"}),
}
# Rate discounts on principal services: S2 2.2 (4% from 2026-04-01, p.40), A2 2.3 (7% from 2026-07-01, p.41).
DISCOUNT_CODES = {"DD-101", "MW-301", "LW-401", "DD-120", "MB-701"}
RATE_DISCOUNTS = [(dt.date(2026, 4, 1), D("0.04")), (dt.date(2026, 7, 1), D("0.07"))]

TERM_START, TERM_END = dt.date(2025, 1, 1), dt.date(2026, 12, 31)  # p.1, A1 1.1, A2 2.1
VAT = D("0.15")                     # Clause 39 (p.8)
DISCOUNT_THRESHOLD = D("250000.00")  # Clause 38 (p.8)
DISCOUNT_PCT = D("0.04")


def ym(d: dt.date) -> str:
    return f"{d.year}-{d.month:02d}"


def by_well_date(lines):
    g = defaultdict(list)
    for l in lines:
        g[(l["well_name"], l["date"])].append(l)
    return g


def write_out(name: str, rows: list[dict]):
    OUT_DIR.mkdir(exist_ok=True)
    if not rows:
        (OUT_DIR / name).write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with open(OUT_DIR / name, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
