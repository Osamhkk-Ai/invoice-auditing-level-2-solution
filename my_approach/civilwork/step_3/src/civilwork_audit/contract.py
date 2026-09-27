"""Contract constants for CW-2025-0417-CIV and the effective-dated rate lookup.

Every constant cites the scanned page it was read from (PDF page = printed footer).
``tests/test_contract_transcription.py`` re-reads the Step 1 transcription and checks
these tables against it, so a typo here cannot pass silently.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

D = Decimal

# --- Agreement (p1), Schedule of Variations (p38), A1 s1.1 (p40), A2 s2.1 (p42) ---------
CONTRACT_REF = "CW-2025-0417-CIV"
SUBCONTRACTOR = "Ridgeway Civil Engineering LLC"
COMMENCEMENT = dt.date(2025, 1, 5)
ORIGINAL_COMPLETION = dt.date(2025, 9, 27)
COMPLETION = dt.date(2026, 9, 30)            # as twice extended (A1 then A2)
REST_WEEKDAYS = (4, 5)                        # Friday, Saturday (p1; Cl 8 p3)
SUBMISSION_WINDOW_DAYS = 21                   # Cl 41 p8
RETENTION_RATE = D("0.05")                    # Cl 45 p8, rounded down
YEAR2_START = dt.date(2026, 1, 5)             # Cl 3A p32: first anniversary of commencement
GROUND_FREEZE_FROM = dt.date(2025, 9, 28)     # Cl 27A p32: "work executed after 27 September 2025"
NIGHT_ZONE_CAP = D("1.1")                     # Cl 27A p32
SURVEY_TOLERANCE = D("0.02")                  # Cl 33A p32

# --- Schedule 1, pp17-19: code -> (unit, base rate). USD items are in USD (Sch 2B p22). ---
SCHEDULE_1: dict[str, tuple[str, Decimal]] = {code: (unit, D(rate)) for code, unit, rate in [
    ("A.11.010", "m2", "3.85"), ("A.11.020", "m2", "12.40"), ("A.12.010", "m3", "21.50"),
    ("A.12.020", "m3", "34.80"), ("A.12.030", "m3", "47.60"), ("A.13.010", "m3", "18.90"),
    ("A.13.020", "m3", "6.40"), ("A.14.010", "m3", "53.20"), ("A.14.020", "m3", "22.40"),
    ("A.11.030", "no.", "148.00"), ("A.12.040", "m3", "69.20"), ("A.12.050", "m3", "52.40"),
    ("A.12.060", "m2", "6.90"), ("A.13.030", "m3", "9.80"), ("A.14.030", "m2", "14.60"),
    ("A.15.010", "m2", "31.80"), ("A.15.020", "m2", "49.50"), ("A.16.010", "week", "1480.00"),
    ("B.21.010", "m2", "29.60"), ("B.21.020", "m3", "415.00"), ("B.21.030", "m3", "389.00"),
    ("B.22.010", "m2", "74.50"), ("B.22.020", "m2", "91.80"), ("B.23.010", "tonne", "4120.00"),
    ("B.24.010", "lm", "67.40"), ("B.21.040", "m3", "448.00"), ("B.21.050", "m3", "296.00"),
    ("B.22.030", "lm", "42.60"), ("B.23.020", "m2", "38.40"), ("B.25.010", "no.", "219.00"),
    ("B.26.010", "m2", "17.20"), ("B.27.010", "lm", "89.50"),
    ("C.31.010", "lm", "86.20"), ("C.31.020", "lm", "214.00"), ("C.32.010", "no.", "1860.00"),
    ("C.32.020", "no.", "287.00"), ("C.33.010", "lm", "59.10"), ("C.31.030", "lm", "54.80"),
    ("C.31.040", "lm", "73.10"), ("C.32.030", "no.", "3120.00"), ("C.32.040", "no.", "423.00"),
    ("C.34.010", "no.", "965.00"), ("C.35.010", "lm", "9.40"),
    ("D.41.010", "m2", "41.80"), ("D.41.020", "m2", "63.50"), ("D.41.030", "m2", "89.40"),
    ("D.42.010", "lm", "71.20"), ("D.43.010", "lm", "14.80"), ("D.41.040", "m2", "32.60"),
    ("D.41.050", "m2", "6.20"), ("D.42.020", "lm", "64.80"), ("D.42.030", "lm", "39.40"),
    ("D.43.020", "m2", "42.60"), ("D.44.010", "no.", "31.80"),
    ("E.51.010", "hour", "246.00"), ("E.51.020", "day", "684.00"), ("E.52.010", "no.", "478.00"),
    ("E.51.030", "hour", "312.00"), ("E.53.010", "day", "389.00"), ("E.54.010", "week", "876.00"),
]}

ZONE_FACTORS = {"Z1": D("1"), "Z2": D("1.06"), "Z3": D("1.145"), "Z4": D("1.28")}    # Sch 2 p20
ZONE_SERIES = ("A", "B", "C", "D")                                                   # Sch 2 p20; Cl 29 p6

GROUND_FACTORS = {"G1": D("0.94"), "G2": D("1"), "G3": D("1.12"),
                  "G4": D("1.375"), "G5": D("1.63")}                                  # Sch 3 p23
GROUND_ITEMS = frozenset({
    "A.11.020", "A.12.010", "A.12.020", "A.12.030", "A.12.040", "A.12.050", "A.14.020",
    "A.15.010", "A.15.020", "C.31.010", "C.31.020", "C.31.030", "C.32.010", "C.32.030",
    "C.33.010"})                                                                      # Sch 3 p23

NIGHT_UPLIFT = {  # Sch 4 Pt 1 p24, per cent
    "A.12.020": 18, "A.12.030": 18, "A.14.010": 18, "B.21.020": 22, "B.21.030": 22,
    "C.31.010": 18, "D.41.020": 25, "D.41.030": 25, "D.43.010": 25, "A.12.040": 18,
    "B.21.040": 22, "C.31.030": 18, "D.43.020": 25}
REST_DAY_UPLIFT = {"B.21.020": 35, "B.21.030": 35, "D.41.030": 35, "B.21.040": 35}   # Sch 4 Pt 2 p24

# Sch 4 Pt 3 pp24-25: (last unit in band, or None for the open band; per cent of rate)
BANDS: dict[str, list[tuple[int | None, int]]] = {
    "A.12.010": [(4000, 100), (16000, 96), (None, 93)],
    "A.12.020": [(1500, 100), (6000, 97), (None, 94)],
    "A.13.010": [(5000, 100), (20000, 94), (None, 90)],
    "A.14.010": [(2000, 100), (8000, 95), (None, 91)],
    "B.22.010": [(1200, 100), (4800, 96), (None, 93)],
    "B.23.010": [(60, 100), (240, 97), (None, 94)],
    "D.41.010": [(4500, 100), (18000, 95), (None, 92)],
    "D.41.040": [(3500, 100), (14500, 95), (None, 92)],
}

DAILY_LIMITS = {  # Sch 4 Pt 4 p26 (Cl 31 p6; Cl 19 p4; P6 p12): per work area per day
    "A.11.010": 4500, "A.12.010": 1200, "B.21.020": 140, "C.32.010": 6, "D.41.030": 3200,
    "E.51.020": 1, "A.13.030": 800, "C.32.030": 3, "E.53.010": 2}

# Sch 4 Pt 5 p26 / Cl 32 p6 / P19 p13: (excluded item, excluding item). P19 (Part V) says
# "within two days of the measurement", read as days 0..2 (see config.p19_window_days).
MUTUALLY_EXCLUSIVE = [("A.14.020", "A.14.010")]

SURVEYED_ITEMS = frozenset({"B.23.010", "E.52.010", "B.23.020"})                     # Sch 4 Pt 6 p26
HOURLY_ITEMS = frozenset({"E.51.010", "E.51.030"})                                   # Cl 6A p32
WEEKLY_RECORD_ITEMS = frozenset({"A.16.010"})                                        # Cl 47A p33
WEEKLY_MIN_DAYS = 5                                                                  # Cl 47A p33; Sch 5 p27
P21_SURFACING_ITEMS = frozenset({"D.41.020", "D.41.030", "D.41.050", "D.43.010", "D.43.020"})  # P21 p13
P21_EXCLUDED_ITEM = "E.51.020"

RECORD_SERIES = {  # Sch 5 p27: item -> reference series of the required record
    "A.12.030": "DX", "A.14.010": "CT", "B.21.020": "PR", "B.21.030": "PR", "C.31.020": "PT",
    "D.41.010": "CT", "E.51.010": "MO", "A.12.040": "DX", "A.16.010": "DW", "B.21.040": "PR",
    "C.32.030": "PT", "C.35.010": "CV", "D.41.040": "CT", "E.51.030": "PS", "B.23.010": "JS",
    "E.52.010": "JS", "B.23.020": "JS"}

INDEXED_ITEMS = frozenset({"C.31.010", "D.41.030"})                                  # Sch 2A p21
USD_ITEMS = frozenset({"B.23.020", "B.25.010", "C.32.040"})                          # Sch 2B p22


def _monthly(values: list[str]) -> dict[str, Decimal]:
    months = [f"{y}-{m:02d}" for y in (2025, 2026) for m in range(1, 13)]
    return dict(zip(months, map(D, values)))


SITE_MATERIALS_INDEX = _monthly([                                                    # Sch 2A p21
    "100.00", "100.40", "101.10", "101.80", "102.60", "103.90", "104.70", "104.20", "105.30",
    "106.80", "107.40", "108.10", "109.60", "110.20", "109.80", "111.50", "112.30", "113.10",
    "112.40", "113.80", "114.60", "115.20", "115.90", "116.50"])
INDEX_BASE = D("100.00")
HALALAS_PER_USD = _monthly([                                                         # Sch 2B p22
    "375.00", "375.10", "375.00", "374.90", "375.20", "375.30", "375.10", "375.00", "374.80",
    "375.40", "375.60", "375.50", "376.00", "375.80", "375.90", "376.20", "376.40", "376.10",
    "375.70", "376.30", "376.60", "376.80", "377.00", "376.50"])


# --- Instruments (Schedule of Variations p38; pp39-43) ------------------------------------
@dataclass(frozen=True)
class RateChange:
    item: str
    effective: dt.date
    rate: Decimal | None = None                       # a fixed substituted rate, or
    monthly: dict[str, Decimal] | None = None         # a monthly published rate


@dataclass(frozen=True)
class Instrument:
    name: str
    issued: dt.date
    effective: dt.date
    rates: tuple[RateChange, ...] = ()
    discount: Decimal | None = None
    discount_items: frozenset[str] = frozenset()
    completion: dt.date | None = None
    page: int = 0

    @property
    def retrospective(self) -> bool:
        """Takes effect before its date of issue: the Clause 31A case."""
        return any(rc.effective < self.issued for rc in self.rates)


_DISCOUNT_ITEMS = frozenset({"C.32.030", "C.32.010", "D.41.020", "B.23.010"})

INSTRUMENTS: tuple[Instrument, ...] = (  # in the order issued (p38)
    Instrument("S1", dt.date(2025, 3, 24), dt.date(2025, 5, 1), page=39, rates=(
        RateChange("B.23.010", dt.date(2025, 5, 1), D("4385.00")),
        RateChange("B.21.020", dt.date(2025, 5, 1), D("431.50")),
        RateChange("A.16.010", dt.date(2025, 5, 1), D("1524.00")),
        RateChange("D.41.020", dt.date(2025, 5, 1), monthly={
            "2025-05": D("214.50"), "2025-06": D("219.80"), "2025-07": D("226.40"),
            "2025-08": D("223.10"), "2025-09": D("220.50")}),
    )),
    # A1 takes effect 28 Sep 2025 but its rates are effective 1 Oct 2025 (p40).
    Instrument("A1", dt.date(2025, 8, 18), dt.date(2025, 9, 28), page=40,
               completion=dt.date(2026, 3, 31), rates=(
                   RateChange("E.54.010", dt.date(2025, 10, 1), D("948.00")),
                   RateChange("B.23.010", dt.date(2025, 10, 1), D("4450.00")),
               )),
    Instrument("S2", dt.date(2025, 11, 12), dt.date(2025, 12, 1), page=41,
               discount=D("0.05"), discount_items=_DISCOUNT_ITEMS, rates=(
                   RateChange("D.41.020", dt.date(2025, 12, 1), D("228.00")),
               )),
    Instrument("A2", dt.date(2026, 2, 16), dt.date(2026, 4, 1), page=42,
               completion=dt.date(2026, 9, 30), discount=D("0.08"),
               discount_items=_DISCOUNT_ITEMS, rates=(
                   RateChange("E.54.010", dt.date(2026, 4, 1), monthly={
                       "2026-04": D("976.00"), "2026-05": D("991.00"), "2026-06": D("1013.00"),
                       "2026-07": D("1038.00"), "2026-08": D("1038.00"), "2026-09": D("1052.00")}),
               )),
    Instrument("A3", dt.date(2026, 5, 12), dt.date(2025, 11, 1), page=43, rates=(
        RateChange("C.32.010", dt.date(2025, 11, 1), D("1984.00")),
        RateChange("A.14.010", dt.date(2025, 11, 1), D("56.80")),
    )),
)
INSTRUMENT_BY_NAME = {i.name: i for i in INSTRUMENTS}
A3 = INSTRUMENT_BY_NAME["A3"]


def month_key(day: dt.date) -> str:
    return f"{day.year}-{day.month:02d}"


def contract_year(work_date: dt.date) -> int | None:
    """Cl 3A p32. None outside the term (no band applies to unpayable work)."""
    if work_date < COMMENCEMENT or work_date > COMPLETION:
        return None
    return 1 if work_date < YEAR2_START else 2


def zone_code(site_zone: str) -> str:
    return site_zone.split()[0]


def ground_code(ground_class: str) -> str:
    return ground_class.split()[0] if ground_class else ""


@dataclass(frozen=True)
class BaseRate:
    rate: Decimal
    source: str


def _monthly_rate(rc: RateChange, work_date: dt.date) -> Decimal:
    """S1 s1.2 / A2 s2.2: the month's rate; after the last month the last published rate."""
    assert rc.monthly is not None
    key = month_key(work_date)
    if key in rc.monthly:
        return rc.monthly[key]
    return rc.monthly[max(m for m in rc.monthly if m <= key)]


def instrument_rate(item: str, work_date: dt.date, application_date: dt.date, *,
                    disabled: frozenset[str] = frozenset(), retro_rule: str = "before_issue"
                    ) -> BaseRate:
    """The base rate in force on the work date, before indexation or currency conversion.

    Instruments are read in the order issued; the later governs work on or after its
    effective date (closing words of pp39-43). Clause 31A (p32): a retrospective
    instrument does not reprice an application submitted before its date of issue.
    ``retro_rule``: "before_issue" (31A text), "on_or_before_issue" (ablation), "off".
    """
    rate, source = SCHEDULE_1[item][1], "Sch1"
    for ins in INSTRUMENTS:                      # issue order; later overrides earlier
        if ins.name in disabled:
            continue
        for rc in ins.rates:
            if rc.item != item or work_date < rc.effective:
                continue
            if ins.retrospective and retro_rule != "off":
                pre_issue = (application_date < ins.issued if retro_rule == "before_issue"
                             else application_date <= ins.issued)
                if pre_issue:
                    source = f"{source} (31A: submitted before {ins.name} issue)"
                    continue
            if rc.monthly is not None:
                rate, source = _monthly_rate(rc, work_date), f"{ins.name} monthly {month_key(work_date)}"
            else:
                rate, source = rc.rate, ins.name
    return BaseRate(rate, source)


def discount_rate(item: str, work_date: dt.date) -> tuple[Decimal, str]:
    """S2 s2.2 p41 / A2 s2.3 p42: the later instrument's percentage from its date."""
    pct, src = D(0), ""
    for ins in INSTRUMENTS:
        if ins.discount is not None and item in ins.discount_items and work_date >= ins.effective:
            pct, src = ins.discount, ins.name
    return pct, src


def all_stated_base_rates(item: str) -> list[Decimal]:
    """Every base rate any document states for the item (for residual diagnosis)."""
    vals = {SCHEDULE_1[item][1]}
    for ins in INSTRUMENTS:
        for rc in ins.rates:
            if rc.item == item:
                vals |= set(rc.monthly.values()) if rc.monthly else {rc.rate}
    return sorted(vals)
