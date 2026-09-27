"""Load the civil-works CSVs and validate their structure before any rule runs.

Money is parsed from text straight into Decimal and must carry exactly two decimal
places (README: "printed ... with two decimal places"). Structural failures raise
``InputError``; the pipeline never audits data it could not read cleanly.
"""
from __future__ import annotations

import csv
import datetime as dt
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from . import contract as C

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
DEFAULT_DATA_DIR = os.path.join(REPO_ROOT, "invoice-auditing-level-2", "civilwork")
DEFAULT_TEMPLATE = os.path.join(REPO_ROOT, "invoice-auditing-level-2", "submission_template.csv")

APPLICATION_COLUMNS = [
    "application_no", "contract_ref", "subcontractor", "site", "site_zone", "period_from",
    "period_to", "application_date", "application_total", "retention", "net_payable",
    "adjustment", "retention_released"]
LINE_COLUMNS = [
    "line_ref", "application_no", "line_no", "work_date", "site", "item_code", "description",
    "unit", "site_zone", "ground_class", "quantity", "rate_applied", "amount", "night_work",
    "record_ref"]


class InputError(ValueError):
    """The source data does not have the structure the audit relies on."""


@dataclass(frozen=True)
class Application:
    application_no: str
    contract_ref: str
    subcontractor: str
    site: str
    site_zone: str
    period_from: dt.date
    period_to: dt.date
    application_date: dt.date
    application_total: Decimal
    retention: Decimal
    net_payable: Decimal
    adjustment: Decimal
    retention_released: Decimal

    @property
    def zone(self) -> str:
        return C.zone_code(self.site_zone)


@dataclass(frozen=True)
class Line:
    line_ref: str
    application_no: str
    line_no: int
    work_date: dt.date
    site: str
    item_code: str
    description: str
    unit: str
    site_zone: str
    ground_class: str
    quantity: int
    rate_applied: Decimal
    amount: Decimal
    night_work: bool
    record_ref: str

    @property
    def zone(self) -> str:
        return C.zone_code(self.site_zone)

    @property
    def ground(self) -> str:
        return C.ground_code(self.ground_class)


@dataclass
class Inputs:
    applications: dict[str, Application]      # in file order
    lines: list[Line]                          # in file order
    lines_by_app: dict[str, list[Line]]
    records_dir: str
    data_dir: str


def parse_money(text: str, where: str) -> Decimal:
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise InputError(f"{where}: not a number: {text!r}") from exc
    if value.as_tuple().exponent != -2:
        raise InputError(f"{where}: money must have exactly two decimals: {text!r}")
    return value


def parse_date(text: str, where: str) -> dt.date:
    try:
        return dt.date.fromisoformat(text)
    except ValueError as exc:
        raise InputError(f"{where}: not an ISO date: {text!r}") from exc


def _read_csv(path: str, columns: list[str]) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != columns:
            raise InputError(f"{path}: columns {reader.fieldnames} != expected {columns}")
        return list(reader)


def load_inputs(data_dir: str = DEFAULT_DATA_DIR) -> Inputs:
    apps: dict[str, Application] = {}
    for r in _read_csv(os.path.join(data_dir, "invoices", "applications.csv"), APPLICATION_COLUMNS):
        no = r["application_no"]
        if no in apps:
            raise InputError(f"duplicate application {no}")
        apps[no] = Application(
            no, r["contract_ref"], r["subcontractor"], r["site"], r["site_zone"],
            parse_date(r["period_from"], no), parse_date(r["period_to"], no),
            parse_date(r["application_date"], no),
            *(parse_money(r[k], f"{no}.{k}") for k in (
                "application_total", "retention", "net_payable", "adjustment", "retention_released")))
    lines: list[Line] = []
    seen: set[str] = set()
    for r in _read_csv(os.path.join(data_dir, "invoices", "application_lines.csv"), LINE_COLUMNS):
        ref = r["line_ref"]
        if ref in seen:
            raise InputError(f"duplicate line {ref}")
        seen.add(ref)
        if r["night_work"] not in ("Y", "N"):
            raise InputError(f"{ref}: night_work must be Y or N, got {r['night_work']!r}")
        try:
            qty = int(r["quantity"])
        except ValueError as exc:
            raise InputError(f"{ref}: quantity is not an integer: {r['quantity']!r}") from exc
        lines.append(Line(
            ref, r["application_no"], int(r["line_no"]), parse_date(r["work_date"], ref), r["site"],
            r["item_code"], r["description"], r["unit"], r["site_zone"], r["ground_class"], qty,
            parse_money(r["rate_applied"], f"{ref}.rate_applied"),
            parse_money(r["amount"], f"{ref}.amount"), r["night_work"] == "Y",
            r["record_ref"].strip()))
    by_app: dict[str, list[Line]] = {no: [] for no in apps}
    for ln in lines:
        if ln.application_no not in by_app:
            raise InputError(f"{ln.line_ref}: unknown application {ln.application_no}")
        by_app[ln.application_no].append(ln)
    inputs = Inputs(apps, lines, by_app, os.path.join(data_dir, "records"), data_dir)
    validate(inputs)
    return inputs


def validate(inputs: Inputs) -> None:
    """Structural facts the rules depend on (architecture B1). Any failure is fatal."""
    problems: list[str] = []
    for no, ls in inputs.lines_by_app.items():
        if not ls:
            problems.append(f"{no}: no lines")
        if sorted(l.line_no for l in ls) != list(range(1, len(ls) + 1)):
            problems.append(f"{no}: line numbers are not 1..n")
    for ln in inputs.lines:
        app = inputs.applications[ln.application_no]
        if ln.item_code not in C.SCHEDULE_1:
            problems.append(f"{ln.line_ref}: item {ln.item_code} not in Schedule 1")
            continue
        if ln.site != app.site or ln.site_zone != app.site_zone:
            problems.append(f"{ln.line_ref}: site/zone differs from its application")
        if ln.zone not in C.ZONE_FACTORS:
            problems.append(f"{ln.line_ref}: unknown zone {ln.site_zone!r}")
        if ln.item_code in C.GROUND_ITEMS and ln.ground not in C.GROUND_FACTORS:
            problems.append(f"{ln.line_ref}: Schedule 3 item without a valid ground class")
        if ln.quantity <= 0:
            problems.append(f"{ln.line_ref}: non-positive quantity")
    if problems:
        raise InputError("input validation failed:\n  " + "\n  ".join(problems[:50]))


def load_template_ids(path: str = DEFAULT_TEMPLATE) -> tuple[list[str], list[str]]:
    """Return (column names, invoice ids in template order)."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        ids = [r["invoice_id"] for r in reader]
        return list(reader.fieldnames or []), ids
