"""Check 05 - rules that need state across days or invoices."""
from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict

from common import ONCE_PER_WELL, TOOL_TERMS, D, load_invoices, load_lines, load_reports, ref_to_key
from evidence import EvidenceOptions, lwd_codes


def contract_year(day: dt.date) -> int:
    """Clause 3A (p.35): CY1 = 2025-01-01..2025-12-31, CY2 from 2026-01-01; extensions add no new year."""
    return 1 if day < dt.date(2026, 1, 1) else 2


def run() -> dict:
    inv = load_invoices()
    lines = load_lines()
    reps = load_reports()
    res = {}

    # Schedule 2 Part 2 (p.17): PD-210 percentage by metres already drilled "on the well in the Contract Year".
    pd = sorted((l for l in lines if l["service_code"] == "PD-210"), key=lambda l: (l["date"], l["dfrom"]))
    per_well = defaultdict(int)
    for l in pd:
        per_well[(l["well_name"], contract_year(l["date"]))] += int(l["qty"])
    res["pd210_max_metres_one_well_one_contract_year"] = max(per_well.values())
    res["pd210_lines_past_40000m_per_well_reading"] = 0 if max(per_well.values()) <= 40000 else "check"
    # Alternative: cumulate across all wells (not the printed wording) -> how many lines would be discounted
    cum = defaultdict(int)
    crossed = Counter()
    for l in pd:
        cy = contract_year(l["date"])
        before = cum[cy]
        cum[cy] += int(l["qty"])
        if cum[cy] > 40000:
            crossed["96%" if cum[cy] <= 120000 else "92%"] += 1
    res["pd210_all_wells_cumulative_by_CY"] = dict(cum)
    res["pd210_lines_repriced_if_cumulated_across_wells"] = dict(crossed)
    res["pd210_billed_rates_all_at_100pct"] = all(
        l["rate"] in (D("42.35"), D("58.15"), D("76.45"), D("98.70")) for l in pd if l["line_ref"] not in (
            "MDS-00977-053", "MDS-01387-037"))

    # Once-per-well items (Sch.3 Pt6, Clause 27)
    spans = {}
    for (w, d) in reps:
        a, b = spans.get(w, (d, d))
        spans[w] = (min(a, d), max(b, d))
    once = defaultdict(list)
    for l in lines:
        if l["service_code"] in ONCE_PER_WELL:
            once[(l["well_name"], l["service_code"])].append(l)
    res["once_per_well_counts"] = dict(Counter(len(v) for v in once.values()))
    wrong_day = []
    for (w, c), ls in once.items():
        want = spans[w][0] if c in ("MB-701", "DD-140") else spans[w][1]
        for l in ls:
            if l["date"] != want:
                wrong_day.append((l["line_ref"], c, l["service_date"], str(want)))
    res["once_per_well_on_wrong_day"] = wrong_day
    lwd_wells = {r.well for r in reps.values() if lwd_codes(r, EvidenceOptions())}
    res["wells_with_lwd"] = len(lwd_wells)
    res["lw430_on_wells_without_lwd"] = sorted(w for (w, c) in once if c == "LW-430" and w not in lwd_wells)

    # Per-run items (Clause 26): DD-111 on last day of motor runs; LW-420 on first day of source runs.
    runs = defaultdict(dict)
    for r in reps.values():
        runs[(r.well, r.run)] = r.fields
    motor_runs = {k for k, f in runs.items() if "mud motor" in f["Tools in run"]}
    source_runs = {k for k, f in runs.items() if f["Radioactive source carried"] == "Yes"}
    dd111 = Counter((l["well_name"], reps[(l["well_name"], l["date"])].run) for l in lines if l["service_code"] == "DD-111")
    lw420 = Counter((l["well_name"], reps[(l["well_name"], l["date"])].run) for l in lines if l["service_code"] == "LW-420")
    res["motor_runs"] = len(motor_runs)
    res["dd111_runs_billed"] = len(dd111)
    res["dd111_runs_billed_more_than_once"] = [k for k, v in dd111.items() if v > 1]
    res["motor_runs_without_dd111"] = len(motor_runs - set(dd111))
    res["source_runs"] = len(source_runs)
    res["lw420_runs_billed"] = len(lw420)
    res["source_runs_without_lw420"] = len(source_runs - set(lw420))
    run_days = defaultdict(list)
    for (w, d), r in reps.items():
        run_days[(w, r.run)].append(d)
    res["runs"] = len(runs)
    res["runs_whose_stated_first_last_differ_from_report_days"] = sorted(
        f"{w} run {n}" for (w, n), ds in run_days.items()
        if (min(ds).strftime("%d-%b-%Y"), max(ds).strftime("%d-%b-%Y")) != (runs[(w, n)]["Run first day"], runs[(w, n)]["Run last day"]))

    # Duplicate billing across invoices: same well/day/code (PD-210 by interval)
    seen = defaultdict(list)
    for l in lines:
        if l["service_code"] != "DS-900":
            seen[(l["well_name"], l["date"], l["service_code"], l["dfrom"])].append(l)
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    res["duplicate_well_day_code_groups"] = [
        {"key": f"{k[0]} {k[1]} {k[2]}", "lines": [x["line_ref"] for x in v],
         "same_invoice": len({x["invoice_no"] for x in v}) == 1} for k, v in dups.items()]
    # Ordering key: invoice_date, invoice_no, line_no. Would a different key change which line is the duplicate?
    alt_differs = 0
    for v in dups.values():
        a = min(v, key=lambda x: (inv[x["invoice_no"]]["invoice_date_d"], x["invoice_no"], int(x["line_no"])))
        b = min(v, key=lambda x: (inv[x["invoice_no"]]["period_start_d"], x["invoice_no"], int(x["line_no"])))
        alt_differs += a is not b
    res["duplicate_keeper_changes_if_ordered_by_period_start"] = alt_differs

    # Invoice sequencing per well
    per_w = defaultdict(list)
    for n, I in inv.items():
        per_w[I["well_name"]].append((I["period_start_d"], I["period_end_d"], n))
    overlaps, gaps = [], []
    for w, P in per_w.items():
        P.sort()
        for a, b in zip(P, P[1:]):
            if b[0] <= a[1]:
                overlaps.append((a[2], b[2]))
            elif (b[0] - a[1]).days > 1:
                gaps.append((a[2], b[2]))
    res["overlapping_invoice_periods"] = overlaps
    res["gaps_between_invoice_periods"] = len(gaps)
    first_last = [(w, min(p[0] for p in P) == spans[w][0], max(p[1] for p in P) >= spans[w][1]) for w, P in per_w.items()]
    res["wells_invoices_cover_all_report_days"] = sum(1 for _, a, b in first_last if a and b)
    # Rig moves (P4): report days per well contiguous?
    noncontig = []
    for w, (a, b) in spans.items():
        n = sum(1 for (w2, _) in reps if w2 == w)
        if n != (b - a).days + 1:
            noncontig.append(w)
    res["wells_with_non_contiguous_report_days"] = noncontig
    return res


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=1, default=str))
