"""Load and validate the drilling invoices, lines and submission template.

Everything is read as text. Money must carry exactly two decimals and becomes ``Decimal``;
quantities must be whole numbers. Any structural failure stops the run (``InputError``):
an audit built on a broken join would be wrong silently.
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

from .money import money

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 5))
DEFAULT_DATA_DIR = os.path.join(REPO_ROOT, "invoice-auditing-level-2", "drilling_services")
DEFAULT_TEMPLATE = os.path.join(REPO_ROOT, "invoice-auditing-level-2", "submission_template.csv")
EXPECTED_COUNTS = {"invoices": 1906, "lines": 91244, "reports": 8151}   # README
DRILLING_ID = re.compile(r"^MDS-\d{5}$")
REPORT_REF = re.compile(r"^DDR-(\d{3})-(\d{8})$")


class InputError(ValueError):
    pass


def pdate(text: str) -> dt.date:
    return dt.datetime.strptime(text, "%d-%b-%Y").date()


@dataclass(frozen=True)
class Invoice:
    invoice_no: str
    contract_ref: str
    contractor: str
    well: str
    rig: str
    field: str
    well_class: str
    period_start: dt.date
    period_end: dt.date
    invoice_date: dt.date
    net_amount: Decimal
    vat_amount: Decimal
    invoice_total: Decimal
    adjustment: Decimal
    invoice_total_text: str


@dataclass(frozen=True)
class Line:
    line_ref: str
    invoice_no: str
    line_no: int
    service_date: dt.date | None          # blank only on the DS-900 discount line
    well: str
    code: str
    description: str
    unit: str
    section: str
    status: str
    depth_from: int | None
    depth_to: int | None
    quantity: Decimal
    rate: Decimal
    amount: Decimal
    report_ref: str

    @property
    def is_discount(self) -> bool:
        return self.code == "DS-900"


@dataclass
class Inputs:
    invoices: dict[str, Invoice]
    lines: list[Line]
    records_dir: str

    def lines_by_invoice(self) -> dict[str, list[Line]]:
        out: dict[str, list[Line]] = {n: [] for n in self.invoices}
        for ln in self.lines:
            out[ln.invoice_no].append(ln)
        return out


def _read(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_invoices(path: str) -> dict[str, Invoice]:
    out: dict[str, Invoice] = {}
    for r in _read(path):
        inv = Invoice(
            invoice_no=r["invoice_no"], contract_ref=r["contract_ref"], contractor=r["contractor"],
            well=r["well_name"], rig=r["rig"], field=r["field"], well_class=r["well_class"],
            period_start=pdate(r["period_start"]), period_end=pdate(r["period_end"]),
            invoice_date=pdate(r["invoice_date"]), net_amount=money(r["net_amount"]),
            vat_amount=money(r["vat_amount"]), invoice_total=money(r["invoice_total"]),
            adjustment=money(r["adjustment"]), invoice_total_text=r["invoice_total"])
        if inv.invoice_no in out:
            raise InputError(f"duplicate invoice_no {inv.invoice_no}")
        out[inv.invoice_no] = inv
    return out


def _int_or_none(text: str) -> int | None:
    if text == "":
        return None
    if not re.fullmatch(r"\d+", text):
        raise InputError(f"depth {text!r} is not a whole number of metres")
    return int(text)


def load_lines(path: str) -> list[Line]:
    out = []
    for r in _read(path):
        qty = Decimal(r["quantity"])
        if qty != qty.to_integral_value():
            raise InputError(f"{r['line_ref']}: quantity {r['quantity']} is not whole")
        out.append(Line(
            line_ref=r["line_ref"], invoice_no=r["invoice_no"], line_no=int(r["line_no"]),
            service_date=pdate(r["service_date"]) if r["service_date"] else None, well=r["well_name"], code=r["service_code"],
            description=r["description"], unit=r["unit"], section=r["hole_section"], status=r["day_status"],
            depth_from=_int_or_none(r["depth_from_m"]), depth_to=_int_or_none(r["depth_to_m"]),
            quantity=qty, rate=money(r["unit_rate"]), amount=money(r["amount"]), report_ref=r["report_ref"]))
    return out


def validate(inputs: Inputs, expected_counts: dict[str, int] | None = EXPECTED_COUNTS) -> None:
    """Structural checks (architecture section 5.1). Raises ``InputError`` on the first failure."""
    inv, lines = inputs.invoices, inputs.lines
    n_reports = len([f for f in os.listdir(inputs.records_dir) if f.endswith(".txt")])
    if expected_counts:
        got = {"invoices": len(inv), "lines": len(lines), "reports": n_reports}
        if got != expected_counts:
            raise InputError(f"counts {got} != {expected_counts}")
    refs = Counter(ln.line_ref for ln in lines)
    dup = [k for k, v in refs.items() if v > 1]
    if dup:
        raise InputError(f"duplicate line_ref {dup[:3]}")
    per_inv: dict[str, list[int]] = {}
    for ln in lines:
        if ln.invoice_no not in inv:
            raise InputError(f"{ln.line_ref}: unknown invoice {ln.invoice_no}")
        if ln.line_ref != f"{ln.invoice_no}-{ln.line_no:03d}":
            raise InputError(f"{ln.line_ref}: line_ref does not match invoice and line number")
        if ln.well != inv[ln.invoice_no].well:
            raise InputError(f"{ln.line_ref}: well differs from its invoice")
        if ln.is_discount:
            if ln.report_ref or ln.service_date or ln.quantity != 1 or ln.amount >= 0:
                raise InputError(f"{ln.line_ref}: discount line is not a single undated negative charge")
        elif ln.service_date is None:
            raise InputError(f"{ln.line_ref}: service line without a date")
        else:
            m = REPORT_REF.match(ln.report_ref)
            if not m or m.group(1) != ln.well[-3:]:
                raise InputError(f"{ln.line_ref}: report_ref {ln.report_ref!r} does not name the line's well")
        per_inv.setdefault(ln.invoice_no, []).append(ln.line_no)
    missing = set(inv) - set(per_inv)
    if missing:
        raise InputError(f"invoices without lines: {sorted(missing)[:3]}")
    gaps = [n for n, v in per_inv.items() if sorted(v) != list(range(1, len(v) + 1))]
    if gaps:
        raise InputError(f"line numbers not contiguous on {gaps[:3]}")


def load_inputs(data_dir: str = DEFAULT_DATA_DIR, expected_counts: dict[str, int] | None = EXPECTED_COUNTS) -> Inputs:
    inputs = Inputs(
        invoices=load_invoices(os.path.join(data_dir, "invoices", "invoices.csv")),
        lines=load_lines(os.path.join(data_dir, "invoices", "invoice_lines.csv")),
        records_dir=os.path.join(data_dir, "records"))
    validate(inputs, expected_counts)
    return inputs


def load_template_ids(path: str = DEFAULT_TEMPLATE) -> tuple[list[str], list[str]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        ids = [r["invoice_id"] for r in reader]
        return list(reader.fieldnames or []), ids


def drilling_template_ids(path: str = DEFAULT_TEMPLATE) -> list[str]:
    return [i for i in load_template_ids(path)[1] if DRILLING_ID.match(i)]
