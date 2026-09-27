"""Shared test helpers: put src/ on the path and run the accepted audit once."""
from __future__ import annotations

import datetime as dt
import functools
import os
import sys
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
STEP3 = os.path.dirname(HERE)
SRC = os.path.join(STEP3, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from civilwork_audit import loader  # noqa: E402
from civilwork_audit.loader import Application, Line  # noqa: E402
from civilwork_audit.pipeline import run_audit  # noqa: E402
from civilwork_audit.records import load_records  # noqa: E402

REPO = loader.REPO_ROOT
TRANSCRIPTION = os.path.join(REPO, "my_approach", "output_ocr", "civilwork")
D = Decimal


@functools.lru_cache(maxsize=None)
def inputs():
    return loader.load_inputs()


@functools.lru_cache(maxsize=None)
def records():
    return load_records(inputs().records_dir)


@functools.lru_cache(maxsize=None)
def accepted():
    return run_audit(inputs(), records())


def line(ref: str) -> Line:
    return accepted().lines[ref].line


def make_line(**kw) -> Line:
    """A synthetic line for rules the data never exercises."""
    base = dict(line_ref="T-00001-01", application_no="T-00001", line_no=1, work_date=dt.date(2025, 6, 2),
                site="S-01 Platform North", item_code="A.11.010", description="", unit="m2",
                site_zone="Z1 Compound", ground_class="", quantity=1, rate_applied=D("0.00"),
                amount=D("0.00"), night_work=False, record_ref="")
    base.update(kw)
    return Line(**base)


def make_app(**kw) -> Application:
    base = dict(application_no="T-00001", contract_ref="CW-2025-0417-CIV",
                subcontractor="Ridgeway Civil Engineering LLC", site="S-01 Platform North",
                site_zone="Z1 Compound", period_from=dt.date(2025, 6, 1), period_to=dt.date(2025, 6, 30),
                application_date=dt.date(2025, 7, 5), application_total=D("0.00"), retention=D("0.00"),
                net_payable=D("0.00"), adjustment=D("0.00"), retention_released=D("0.00"))
    base.update(kw)
    return Application(**base)
