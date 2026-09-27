"""Check 03 - what the Daily Drilling Reports support, per well-day and code, against billed quantities.

Runs the baseline evidence reading and one-switch alternatives; an alternative that makes thousands of
agreeing day-codes disagree is recorded as rejected by the data (README calibration note), not as proof.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from common import D, load_invoices, load_lines, load_reports, ref_to_key
from evidence import EvidenceOptions, lwd_codes, supported, well_spans

BASE = EvidenceOptions(chargeable_hour_minus_one=True)
ALTERNATIVES = {
    "21A off (charge the hours the report states)": EvidenceOptions(chargeable_hour_minus_one=False),
    "LWD words read literally, not by Appendix G": EvidenceOptions(chargeable_hour_minus_one=True, lwd_map="literal"),
    "PD-210 on every 12-1/4 / 8-1/2 Operating day": EvidenceOptions(chargeable_hour_minus_one=True, pd210_rule="section_only"),
    "PD-210 only when 'bit and reamer' in hole": EvidenceOptions(chargeable_hour_minus_one=True, pd210_rule="perf_tools"),
    "daily limits not applied": EvidenceOptions(chargeable_hour_minus_one=True, apply_daily_limits=False),
}


def billed_by_day(lines, key_by="service_date"):
    b = defaultdict(lambda: defaultdict(D))
    for l in lines:
        if l["service_code"] == "DS-900":
            continue
        k = (l["well_name"], l["date"]) if key_by == "service_date" else ref_to_key(l["report_ref"], l["well_name"])
        b[k][l["service_code"]] += l["qty"]
    return b


def compare(reps, billed, opt, extra=None):
    spans = well_spans(reps)
    lwd = {r.well for r in reps.values() if lwd_codes(r, opt)}
    out = Counter()
    detail = defaultdict(list)
    for key, rep in reps.items():
        sup = supported(rep, spans, lwd, opt)
        if extra:
            extra(rep, sup)
        b = billed.get(key, {})
        for code in set(sup) | set(b):
            s, q = D(sup.get(code, 0)), b.get(code, D(0))
            kind = "eq" if s == q else ("over" if s and q > s else "unsupported" if q > s else
                                        "under" if q else "not_billed")
            out[(code, kind)] += 1
            if kind != "eq":
                detail[(code, kind)].append((rep.file, int(s), int(q)))
    return out, detail


def summarise(out):
    return {"eq": sum(v for (c, k), v in out.items() if k == "eq"),
            "ne": sum(v for (c, k), v in out.items() if k != "eq")}


def run() -> dict:
    inv = load_invoices()
    lines = load_lines()
    reps = load_reports()
    billed = billed_by_day(lines)
    res = {}
    out, detail = compare(reps, billed, BASE)
    res["baseline_day_code_pairs"] = summarise(out)
    by_code = defaultdict(dict)
    for (c, k), v in sorted(out.items()):
        by_code[c][k] = v
    res["baseline_by_code"] = dict(by_code)
    res["baseline_exceptions"] = {f"{c}:{k}": v for (c, k), v in sorted(detail.items())}

    # keyed by report_ref instead of service_date (tests Clause 19A number as the join)
    out_ref, _ = compare(reps, billed_by_day(lines, key_by="report_ref"), BASE)
    res["join_by_report_ref_instead"] = summarise(out_ref)

    res["alternatives"] = {}
    for name, opt in ALTERNATIVES.items():
        o, _ = compare(reps, billed, opt)
        s = summarise(o)
        s["day_codes_changed_vs_baseline"] = s["ne"] - res["baseline_day_code_pairs"]["ne"]
        res["alternatives"][name] = s

    # Schedule 8 wording: DD-120 "each circulating or back-reaming hour" -> add back-reaming hours to DD-120
    def add_backream(rep, sup):
        if "DD-120" in sup and rep.i("Back-reaming hours"):
            sup["DD-120"] += rep.i("Back-reaming hours")
    o, _ = compare(reps, billed, BASE, add_backream)
    res["alternatives"]["Sch.8: DD-120 also per back-reaming hour"] = summarise(o)
    # Schedule 8 wording: HC-630 per BHA run (once, on run last day) instead of Clause 30 count
    def hc630_per_run(rep, sup):
        sup.pop("HC-630", None)
        if rep.fields["Run last day"] == rep.fields["Date"] and rep.status == "Operating":
            sup["HC-630"] = 1
    o, _ = compare(reps, billed, BASE, hc630_per_run)
    res["alternatives"]["Sch.8: HC-630 once per BHA run"] = summarise(o)

    # Clause 21 minimum: does it ever engage?
    res["operating_rss_days_with_circ_below_7"] = sum(
        1 for r in reps.values() if r.status == "Operating" and "DD-120" in r.tool_codes and r.circ < 7)
    res["min_circ_on_operating_rss_day"] = min(
        r.circ for r in reps.values() if r.status == "Operating" and "DD-120" in r.tool_codes)
    # Clause 25A tolerance: billed metres above the report but within 1 per cent
    within, beyond = [], []
    for (c, k), rows in detail.items():
        if k == "over" and c in ("LW-410", "LW-411", "LW-412", "RM-510", "PD-210"):
            for f, s, q in rows:
                (within if q <= s * 1.01 else beyond).append((c, f, s, q))
    res["metres_over_within_1pct"] = within
    res["metres_over_beyond_1pct"] = beyond
    # Crew wording vs Schedule 4 "normally on the rig"
    res["crew_counts_seen"] = {c: dict(Counter(r.crew.get(c, 0) for r in reps.values()))
                               for c in ("DD-101", "DD-102", "MW-301", "LW-401", "PD-201")}
    # Part E hours stated vs sum of daily circulating hours (P12 alternative)
    diffs = []
    for (w, d), r in reps.items():
        if "Lost in hole tool" in r.fields:
            tot = sum(x.circ for (w2, d2), x in reps.items() if w2 == w and d2 <= d)
            if tot != int(r.fields["Circulating hours accumulated on the well"]):
                diffs.append(r.file)
    res["lih_reports"] = sum(1 for r in reps.values() if "Lost in hole tool" in r.fields)
    res["lih_stated_hours_ne_sum_daily_circ"] = len(diffs)
    # Radioactive source flag vs 'resistivity tool' (Appendix G -> LW-411 density-neutron)
    res["source_yes_iff_resistivity_tool"] = sum(
        1 for r in reps.values() if (r.fields["Radioactive source carried"] == "Yes") == ("resistivity tool" in r.tools))
    return res


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=1, default=str))
