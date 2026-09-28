"""Contract DDS-2025-118 as data. Every figure cites the page of DDS-2025-118.pdf it was read from
(page = PDF page = printed footer). ``tests/test_contract_transcription.py`` re-reads each table from
the validated transcription and compares it with these constants.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

D = Decimal
d = dt.date

CONTRACT_REF = "DDS-2025-118"                       # p.1
CONTRACTOR = "Meridian Downhole Services Ltd"       # p.1
TERM_START = d(2025, 1, 1)                          # p.1
TERM_END_AS_LET = d(2025, 12, 31)                   # p.1, p.37
SUBMISSION_WINDOW_DAYS = 30                         # Clause 33, p.8
VAT_RATE = D("0.15")                                # Clause 39, p.8
DISCOUNT_THRESHOLD = D("250000.00")                 # Clause 38, p.8
DISCOUNT_RATE = D("0.04")                           # Clause 38, p.8
DISCOUNT_CODE = "DS-900"                            # Clause 38, p.8

# Schedule 1 (pp.15-16): code -> (description, unit, rate). PD-210 is rated in Schedule 2 and
# LH-711..714 under Clause 31, so their rate is None.
SCHEDULE_1: dict[str, tuple[str, str, Decimal | None]] = {
    "DD-101": ("Directional driller, 24-hour coverage", "person-day", D("1847.35")),
    "DD-102": ("Directional coordinator, office based", "day", D("948.60")),
    "DD-110": ("Positive displacement motor rental", "day", D("1417.75")),
    "DD-111": ("Motor redress and inspection", "run", D("3589.45")),
    "DD-120": ("Rotary steerable system, circulating", "hour", D("384.15")),
    "DD-121": ("Rotary steerable system on standby", "day", D("2893.65")),
    "DD-130": ("Gyro survey", "survey", D("2446.15")),
    "DD-140": ("Well planning and anti-collision study", "well", D("12489.50")),
    "PD-201": ("Drilling optimisation engineer", "person-day", D("2094.85")),
    "PD-210": ("Performance drilling footage", "metre", None),
    "PD-220": ("Downhole vibration mitigation tool", "day", D("1148.35")),
    "PD-230": ("Drilling dynamics memory sub", "day", D("639.15")),
    "MW-301": ("MWD engineer", "person-day", D("1646.55")),
    "MW-310": ("MWD directional and gamma tool", "day", D("2245.85")),
    "MW-320": ("Pressure while drilling module", "day", D("779.65")),
    "MW-330": ("Real-time data transmission", "day", D("309.75")),
    "LW-401": ("LWD engineer", "person-day", D("1898.45")),
    "LW-410": ("LWD resistivity, logged", "metre", D("11.37")),
    "LW-411": ("LWD density and neutron, logged", "metre", D("16.83")),
    "LW-412": ("LWD sonic, logged", "metre", D("13.29")),
    "LW-413": ("Formation pressure tester, per pressure point", "point", D("1849.65")),
    "LW-420": ("Radioactive source handling", "run", D("2746.55")),
    "LW-430": ("LWD data processing and final log", "well", D("8394.75")),
    "RM-510": ("Hydraulic underreaming, reamed", "metre", D("38.45")),
    "RM-511": ("Underreamer rental", "day", D("1379.15")),
    "RM-520": ("Roller reamer and stabiliser rental", "day", D("419.85")),
    "RM-530": ("Back-reaming while tripping", "hour", D("264.55")),
    "HC-601": ("Hole cleaning circulating sub", "day", D("689.35")),
    "HC-610": ("Wiper trip supervision", "trip", D("1947.15")),
    "HC-620": ("Drilling jar rental", "day", D("539.65")),
    "HC-630": ("Casing drift and clean-out run", "run", D("4295.85")),
    "HC-640": ("Cuttings bed monitoring", "day", D("719.55")),
    "MB-701": ("Mobilisation to rig site", "well", D("18497.50")),
    "MB-702": ("Demobilisation from rig site", "well", D("14196.25")),
    "LH-711": ("Lost in hole, positive displacement motor", "each", None),
    "LH-712": ("Lost in hole, rotary steerable system", "each", None),
    "LH-713": ("Lost in hole, MWD tool", "each", None),
    "LH-714": ("Lost in hole, LWD resistivity tool", "each", None),
}
PERSONNEL = frozenset({"DD-101", "DD-102", "MW-301", "LW-401", "PD-201"})   # Clause 22, Sch.4 p.23
LOST_IN_HOLE = frozenset({"LH-711", "LH-712", "LH-713", "LH-714"})

# Schedule 2 (p.17): PD-210 depth bands (upper bound inclusive; a boundary depth belongs to the
# shallower band, Clause 23 p.6).
PD210_BANDS: list[tuple[int, int | None, Decimal]] = [
    (0, 1500, D("42.35")), (1500, 3000, D("58.15")), (3000, 4500, D("76.45")), (4500, None, D("98.70"))]
# Schedule 2 Part 2 (p.17): per cent of the PD-210 rate by metres already drilled on the well in the
# Contract Year: 1..40,000 -> 100 %, 40,001..120,000 -> 96 %, above 120,000 -> 92 %.
PD210_VOLUME_BANDS: list[tuple[int, int | None, Decimal]] = [
    (0, 40000, D("1.00")), (40000, 120000, D("0.96")), (120000, None, D("0.92"))]
CONTRACT_YEAR_2_START = d(2026, 1, 1)               # Clause 3A p.35: anniversary of Commencement

# Schedule 2C (p.18): Rig Services Index (base 100.00) for MW-310 and HC-620 (Clause 17A, p.35).
INDEXED = frozenset({"MW-310", "HC-620"})
INDEX_BASE = D("100.00")
_MONTHS = [f"2025-{m:02d}" for m in range(1, 13)] + [f"2026-{m:02d}" for m in range(1, 13)]
RIG_SERVICES_INDEX: dict[str, Decimal] = dict(zip(_MONTHS, map(D, (
    "100.00 100.70 101.50 102.30 103.10 103.60 104.80 105.40 104.90 106.20 107.10 108.00 "
    "109.30 110.00 110.60 111.40 110.90 112.20 113.00 112.60 113.90 114.70 115.30 116.10").split())))

# Schedule 2D (p.19): replacement values in SAR and halalas per USD, converted under Clause 31A (p.35).
LIH_SAR: dict[str, Decimal] = {"LH-711": D("543750.00"), "LH-712": D("4687500.00"),
                               "LH-713": D("1443750.00"), "LH-714": D("1950000.00")}
HALALAS_PER_USD: dict[str, Decimal] = dict(zip(_MONTHS, map(D, (
    "375.00 375.10 375.00 374.90 375.20 375.30 375.10 375.00 374.80 375.40 375.60 375.50 "
    "376.00 375.80 375.90 376.20 376.40 376.10 375.70 376.30 376.60 376.80 377.00 376.50").split())))
# Schedule 6 (p.25): the same values in USD as let; superseded by Schedule 2D (Clause 31A).
LIH_USD_SCHEDULE_6: dict[str, Decimal] = {"LH-711": D("145000.00"), "LH-712": D("1250000.00"),
                                          "LH-713": D("385000.00"), "LH-714": D("520000.00")}
LIH_DEPRECIATION_HOURS = 25                          # Clause 31 p.7: 1 % per complete 25 h
LIH_DEPRECIATION_CAP = 50                            # ... to not more than 50 %

# Schedule 3 Part 1 (p.20)
SECTION_FACTOR: dict[str, Decimal] = {'26"': D("1.315"), '17-1/2"': D("1.145"), '12-1/4"': D("1.00"),
                                      '8-1/2"': D("0.945"), '6"': D("0.885")}
SECTION_RATED = frozenset({"DD-110", "DD-120", "PD-220", "MW-310", "RM-510", "RM-511"})
# Schedule 3 Part 2 (p.20); Clause 17B (p.35) removes PD-210 from the list.
CLASS_FACTOR: dict[str, Decimal] = {"Standard": D("1.00"), "Extended Reach": D("1.175"), "HPHT": D("1.325")}
CLASS_RATED = frozenset({"DD-120", "PD-210", "MW-310", "MW-320", "LW-410", "LW-411", "LW-412", "LW-413"})
# Schedule 3 Part 3 (pp.20-21): per cent of the operating rate on a Standby day; None = not chargeable.
STANDBY_PCT: dict[str, Decimal | None] = {
    "DD-101": D("0.80"), "DD-102": D("1.00"), "DD-110": D("0.50"), "DD-111": D("1.00"), "DD-120": None,
    "DD-130": None, "PD-201": D("0.80"), "PD-210": None, "PD-220": D("0.50"), "PD-230": D("0.50"),
    "MW-301": D("0.80"), "MW-310": D("0.50"), "MW-320": D("0.50"), "MW-330": D("1.00"), "LW-401": D("0.80"),
    "LW-410": None, "LW-411": None, "LW-412": None, "LW-413": None, "LW-420": D("1.00"), "RM-510": None,
    "RM-511": D("0.50"), "RM-520": D("0.50"), "RM-530": None, "HC-601": D("0.50"), "HC-610": None,
    "HC-620": D("0.50"), "HC-630": None, "HC-640": None,
}
# Sch.3 Pt3 intro (p.20): per-well and loss charges are charged in full whatever the status.
# Sch.3 Pt4 (p.21): DD-121 is charged only on a Standby day, in place of DD-120; it has no percentage.
FULL_WHATEVER_STATUS = frozenset({"DD-140", "LW-430", "MB-701", "MB-702"}) | LOST_IN_HOLE
STANDBY_ONLY = frozenset({"DD-121"})
# Schedule 3 Part 5 (pp.21-22): daily limits.
DAILY_LIMIT: dict[str, int] = {
    "DD-101": 2, "DD-102": 1, "DD-110": 1, "DD-120": 24, "DD-121": 1, "DD-130": 3, "PD-201": 1, "PD-220": 1,
    "PD-230": 1, "MW-301": 2, "MW-310": 1, "MW-320": 1, "MW-330": 1, "LW-401": 1, "LW-413": 12, "RM-511": 1,
    "RM-520": 1, "RM-530": 24, "HC-601": 1, "HC-610": 2, "HC-620": 1, "HC-640": 1,
}
ONCE_PER_WELL_FIRST_DAY = frozenset({"MB-701", "DD-140"})    # Clause 27 p.7, Sch.3 Pt6 p.22
ONCE_PER_WELL_LAST_DAY = frozenset({"LW-430", "MB-702"})
DD120_MINIMUM_HOURS = 6                                       # Clause 21 p.6, Sch.3 Pt7 p.22, P10 p.11
HOURLY_SERVICES = frozenset({"DD-120", "RM-530"})             # Schedule 1 unit "hour" (Clause 21A)
METRE_SERVICES = frozenset({"LW-410", "LW-411", "LW-412", "RM-510", "PD-210"})   # unit "metre"
METRE_TOLERANCE = D("0.01")                                   # Clause 25A p.35

# Schedule 5 (p.24): part of the Daily Drilling Report required before a charge is payable (Clause 37).
PART_REQUIRED: dict[str, str] = {
    "DD-111": "B", "DD-130": "C", "LW-410": "B", "LW-411": "B", "LW-412": "B", "LW-413": "B",
    "LW-420": "D", "RM-510": "B", "LH-711": "E", "LH-712": "E", "LH-713": "E", "LH-714": "E"}

# Appendix G (p.36): the words of the rig -> Schedule 1 codes, as printed (including the pairings that
# do not follow the English: "gamma tool" -> LW-410, "resistivity tool" -> LW-411, "density-neutron" ->
# LW-412, "float sub" -> HC-640, "survey package" -> MW-320, "night man" -> DD-102).
TOOL_WORDS: dict[str, str] = {
    "mud motor": "DD-110", "rotary steerable": "DD-120", "circulating sub": "HC-601",
    "drilling jars": "HC-620", "float sub": "HC-640", "gamma tool": "LW-410", "resistivity tool": "LW-411",
    "density-neutron": "LW-412", "MWD collar": "MW-310", "survey package": "MW-320",
    "real-time link": "MW-330", "bit and reamer": "PD-220", "hydraulics package": "PD-230",
    "hole opener": "RM-511", "stabiliser string": "RM-520",
}
CREW_WORDS: dict[str, str] = {
    "directional hands": "DD-101", "night man": "DD-102", "MWD engineers": "MW-301",
    "logging engineers": "LW-401", "performance engineer": "PD-201",
}
LOST_WORDS: dict[str, str] = {"mud motor": "LH-711", "rotary steerable": "LH-712", "MWD collar": "LH-713",
                              "gamma tool": "LH-714"}
DAY_RENTALS = frozenset({"DD-110", "HC-601", "HC-620", "HC-640", "MW-310", "MW-320", "MW-330", "PD-220",
                         "PD-230", "RM-511", "RM-520"})       # unit "day", Clause 28
LWD_METRE_TOOLS = frozenset({"LW-410", "LW-411", "LW-412"})    # Clause 24
PERFORMANCE_SECTIONS = frozenset({'12-1/4"', '8-1/2"'})        # Appendix A p.29
# Clause 30 (p.7): counts from the report, Operating day only.
COUNT_FIELDS: dict[str, str] = {"DD-130": "Gyro surveys", "LW-413": "Pressure points", "HC-610": "Wiper trips",
                                "RM-530": "Back-reaming hours", "HC-630": "Clean-out runs"}


@dataclass(frozen=True)
class Instrument:
    """A supplement or amendment (Schedule of Variations p.37 and the instrument's own page)."""
    name: str
    page: int
    issued: dt.date
    effective: dt.date
    rates: dict[str, Decimal] = field(default_factory=dict)             # flat substitution
    monthly: dict[str, dict[str, Decimal]] = field(default_factory=dict)  # code -> {yyyy-mm: rate}
    discount: Decimal | None = None                                      # rate discount (S2 2.2, A2 2.3)
    discount_codes: frozenset[str] = frozenset()
    expiry: dt.date | None = None                                        # extension of the Term

    @property
    def retroactive(self) -> bool:
        """Clause 36A (p.35): takes effect before the date it was issued."""
        return self.effective < self.issued


_PRINCIPAL = frozenset({"DD-101", "MW-301", "LW-401", "DD-120", "MB-701"})
INSTRUMENTS: tuple[Instrument, ...] = (
    Instrument("S1", 38, d(2025, 5, 19), d(2025, 7, 1),
               rates={"DD-120": D("398.50"), "DD-121": D("2984.00")},
               monthly={"HC-601": {"2025-07": D("701.50"), "2025-08": D("714.00"), "2025-09": D("722.60"),
                                   "2025-10": D("719.80"), "2025-11": D("731.00"), "2025-12": D("736.40")}}),
    Instrument("A1", 39, d(2025, 11, 7), d(2026, 1, 1),
               rates={"DD-101": D("1916.50"), "MW-301": D("1708.00"), "LW-401": D("1969.00")},
               expiry=d(2026, 6, 30)),
    Instrument("S2", 40, d(2026, 2, 24), d(2026, 4, 1),
               monthly={"DD-120": {"2026-04": D("406.00"), "2026-05": D("411.50"), "2026-06": D("411.50"),
                                   "2026-07": D("423.00"), "2026-08": D("429.50"), "2026-09": D("434.00"),
                                   "2026-10": D("434.00"), "2026-11": D("441.00"), "2026-12": D("447.50")}},
               discount=D("0.04"), discount_codes=_PRINCIPAL),
    Instrument("A2", 41, d(2026, 5, 21), d(2026, 7, 1),
               rates={"MW-301": D("1763.00"), "MB-701": D("19237.00")},
               discount=D("0.07"), discount_codes=_PRINCIPAL, expiry=d(2026, 12, 31)),
    Instrument("A3", 42, d(2026, 8, 17), d(2026, 2, 1),
               rates={"DD-120": D("416.00"), "DD-101": D("1954.00")}),
)
INSTRUMENT = {i.name: i for i in INSTRUMENTS}
TERM_END = max(i.expiry for i in INSTRUMENTS if i.expiry)       # 2026-12-31 (A2 2.1, p.41)


def ym(day: dt.date) -> str:
    return f"{day.year}-{day.month:02d}"


def contract_year(day: dt.date) -> int:
    """Clause 3A (p.35): Year 1 from Commencement, Year 2 from the first anniversary; an extension does
    not begin a new year."""
    return 1 if day < CONTRACT_YEAR_2_START else 2
