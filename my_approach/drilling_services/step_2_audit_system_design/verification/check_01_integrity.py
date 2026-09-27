"""Check 01 - file counts, keys, joins, types, currency precision, template coverage."""
from __future__ import annotations

import csv
import re
from collections import Counter

from common import (INVOICES_CSV, LINES_CSV, RECORDS_DIR, TEMPLATE_CSV, load_invoices, load_lines,
                    load_reports, r2, ref_to_key)


def run() -> dict:
    res = {}
    inv = load_invoices()
    lines = load_lines()
    reps = load_reports()
    files = list(RECORDS_DIR.iterdir())

    res["invoices"] = len(inv)
    res["lines"] = len(lines)
    res["report_files"] = len(files)
    assert (res["invoices"], res["lines"], res["report_files"]) == (1906, 91244, 8151), res

    # keys
    assert len({l["line_ref"] for l in lines}) == len(lines)
    assert all(l["line_ref"] == f"{l['invoice_no']}-{int(l['line_no']):03d}" for l in lines)
    per_inv = Counter(l["invoice_no"] for l in lines)
    assert set(per_inv) == set(inv), "every invoice has lines and every line an invoice"
    res["lines_per_invoice_min_max"] = [min(per_inv.values()), max(per_inv.values())]
    nums = {}
    for l in lines:
        nums.setdefault(l["invoice_no"], []).append(int(l["line_no"]))
    res["invoices_with_line_no_gaps"] = sum(1 for v in nums.values() if sorted(v) != list(range(1, len(v) + 1)))
    res["line_well_equals_invoice_well"] = all(l["well_name"] == inv[l["invoice_no"]]["well_name"] for l in lines)

    # money precision: every money field has exactly two decimals
    money_re = re.compile(r"^-?\d+\.\d{2}$")
    with open(INVOICES_CSV, encoding="utf-8") as fh:
        bad_inv = [r["invoice_no"] for r in csv.DictReader(fh)
                   if not all(money_re.match(r[k]) for k in ("net_amount", "vat_amount", "invoice_total", "adjustment"))]
    with open(LINES_CSV, encoding="utf-8") as fh:
        bad_ln = [r["line_ref"] for r in csv.DictReader(fh)
                  if not (money_re.match(r["unit_rate"]) and money_re.match(r["amount"]))]
    res["money_fields_not_2dp"] = len(bad_inv) + len(bad_ln)
    res["quantities_non_integer"] = sum(1 for l in lines if l["qty"] != l["qty"].to_integral_value())
    res["adjustment_values"] = dict(Counter(r["adjustment"] for r in inv.values()))
    res["contract_ref_values"] = dict(Counter(r["contract_ref"] for r in inv.values()))
    res["contractor_values"] = dict(Counter(r["contractor"] for r in inv.values()))
    res["currencies"] = "USD only (no currency column; Clause P14, p.11-12)"

    # report join
    blank = [l for l in lines if not l["report_ref"]]
    res["lines_blank_report_ref"] = len(blank)
    res["blank_ref_codes"] = dict(Counter(l["service_code"] for l in blank))
    unresolved = [l["line_ref"] for l in lines if l["report_ref"] and ref_to_key(l["report_ref"], l["well_name"]) not in reps]
    res["lines_ref_not_resolving_to_file"] = len(unresolved)
    referenced = {ref_to_key(l["report_ref"], l["well_name"]) for l in lines if l["report_ref"]}
    res["reports_never_referenced"] = len(set(reps) - referenced)
    res["well_number_collisions"] = sum(1 for n, c in Counter(w[-3:] for w in {k[0] for k in reps}).items() if c > 1)
    res["report_number_matches_file"] = all(r.number == f"DDR-{r.well[-3:]}-{r.date:%Y%m%d}" for r in reps.values())
    res["ref_date_differs_from_service_date"] = sorted(
        l["line_ref"] for l in lines if l["report_ref"] and ref_to_key(l["report_ref"], l["well_name"])[1] != l["date"])

    # well attributes stable across invoices
    attrs = {}
    for r in inv.values():
        attrs.setdefault(r["well_name"], set()).add((r["rig"], r["field"], r["well_class"]))
    res["wells"] = len(attrs)
    res["wells_with_conflicting_rig_field_class"] = sum(1 for v in attrs.values() if len(v) > 1)
    res["report_rig_differs_from_invoice_rig"] = sum(
        1 for r in reps.values() if (r.fields["Rig"],) != (next(iter(attrs[r.well]))[0],))
    res["well_class_counts_by_invoice"] = dict(Counter(r["well_class"] for r in inv.values()))
    res["date_range_lines"] = [str(min(l["date"] for l in lines if l["date"])), str(max(l["date"] for l in lines if l["date"]))]
    res["date_range_reports"] = [str(min(k[1] for k in reps)), str(max(k[1] for k in reps))]
    res["report_unknown_terms"] = sum(len(r.unknown_terms) for r in reps.values())
    res["reports_unsigned"] = sorted(r.file for r in reps.values() if not r.signed)
    res["report_parts_pattern"] = dict(Counter("".join(r.parts) for r in reps.values()))
    res["report_status"] = dict(Counter(r.status for r in reps.values()))
    res["tools_in_hole_equals_tools_in_run"] = sum(1 for r in reps.values() if r.tools == r.tools_run)

    # submission template
    with open(TEMPLATE_CSV, encoding="utf-8") as fh:
        ids = [r["invoice_id"] for r in csv.DictReader(fh)]
    mds = [i for i in ids if i.startswith("MDS-")]
    res["template_rows"] = len(ids)
    res["template_drilling_ids"] = len(mds)
    res["template_drilling_ids_matched_once"] = sum(1 for i in mds if i in inv) == len(mds) == len(set(mds))
    res["invoices_missing_from_template"] = len(set(inv) - set(mds))
    # arithmetic spot property: cents are exact after r2
    res["line_amount_ne_qty_x_rate"] = sorted(l["line_ref"] for l in lines if r2(l["qty"] * l["rate"]) != l["amt"])
    return res


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=1, default=str))
