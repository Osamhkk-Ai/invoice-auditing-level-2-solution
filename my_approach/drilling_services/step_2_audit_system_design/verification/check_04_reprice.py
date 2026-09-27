"""Check 04 - reprice every billed line from its report and the contract, then rebuild each invoice.

Order (fixed): term -> invoice period -> report exists/signed -> Schedule 5 part -> supported quantity
(pooled per well-day-code, consumed in invoice_date, invoice_no, line_no order) -> rate build-up ->
amount -> invoice discount, VAT, total, Amendment No. 3 adjustment.
"""
from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from dataclasses import replace
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP

from common import (A3_ISSUED, CLASS_FACTOR, D, DISCOUNT_PCT, DISCOUNT_THRESHOLD, LOST_TERMS, TERM_END, TERM_START, VAT,
                    load_invoices, load_lines, load_reports, r2, ref_to_key, write_out)
from evidence import EvidenceOptions, lwd_codes, supported, well_spans
from pricing import BASELINE, Reading, build_rate, lih_value, pd210_split

EVIDENCE = EvidenceOptions(chargeable_hour_minus_one=True)
METRE_CODES = {"LW-410", "LW-411", "LW-412", "RM-510", "PD-210"}
PART_REQUIRED = {"DD-111": "B", "DD-130": "C", "LW-410": "B", "LW-411": "B", "LW-412": "B", "LW-413": "B",
                 "LW-420": "D", "RM-510": "B", "LH-711": "E", "LH-712": "E", "LH-713": "E", "LH-714": "E"}


def build_pools(reps, opt=EVIDENCE):
    spans = well_spans(reps)
    lwd = {r.well for r in reps.values() if lwd_codes(r, opt)}
    pools = {}
    for key, rep in reps.items():
        sup = supported(rep, spans, lwd, opt)
        for code, q in sup.items():
            if code == "PD-210":
                for a, b, _ in pd210_split(rep.dstart, rep.dend):
                    pools[(key, code, a, b)] = D(b - a)
            else:
                pools[(key, code, None, None)] = D(q)
    return pools


def reprice(inv, lines, reps, rd: Reading = BASELINE, opt=EVIDENCE, date_source="service_date"):
    pools = build_pools(reps, opt)
    order = sorted(lines, key=lambda l: (inv[l["invoice_no"]]["invoice_date_d"], l["invoice_no"], int(l["line_no"])))
    out = {}
    for l in order:
        code = l["service_code"]
        if code == "DS-900":
            continue
        I = inv[l["invoice_no"]]
        day = l["date"]
        if date_source == "report_ref":
            k = ref_to_key(l["report_ref"], l["well_name"])
            day = k[1] if k else day
        reasons = []
        rep = reps.get((l["well_name"], day))
        qty = D(0)
        rate = None
        if not (TERM_START <= day <= TERM_END):
            reasons.append("outside_term")
        elif not (I["period_start_d"] <= day <= I["period_end_d"]):
            reasons.append("outside_invoice_period")
        elif rep is None:
            reasons.append("no_report_for_day")
        elif not rep.signed:
            reasons.append("report_unsigned")
        elif code in PART_REQUIRED and PART_REQUIRED[code] not in rep.parts:
            reasons.append(f"part_{PART_REQUIRED[code]}_absent")
        else:
            if code == "PD-210":
                pk = ((rep.well, rep.date), code, l["dfrom"], l["dto"])
            else:
                pk = ((rep.well, rep.date), code, None, None)
            avail = pools.get(pk, D(0))
            billed = l["qty"]
            if avail <= 0:
                reasons.append("not_supported_by_report" if pk not in pools else "already_billed")
            else:
                if billed <= avail:
                    qty = billed
                elif code in METRE_CODES and rd.metre_tolerance and billed <= avail * D("1.01"):
                    qty = billed                           # Clause 25A tolerance
                else:
                    qty = avail
                    reasons.append("qty_above_report")
                pools[pk] = avail - qty
            if code.startswith("LH-"):
                hours = int(rep.fields["Circulating hours accumulated on the well"])
                if LOST_TERMS.get(rep.fields.get("Lost in hole tool")) != code:
                    reasons.append("lih_code_differs_from_part_E")
                rate, _ = lih_value(code, day, hours, rd)
            elif code == "PD-210":
                segs = {(a, b): r for a, b, r in pd210_split(rep.dstart, rep.dend)}
                rate = segs.get((l["dfrom"], l["dto"]))
                if rate is not None and not rd.no_class_factor_on_pd210:
                    rate = r2(rate * CLASS_FACTOR[I["well_class"]], ROUND_HALF_UP if rd.half_up else ROUND_HALF_EVEN)
            else:
                rate, _ = build_rate(code, day, rep.section, rep.status, I["well_class"], I["invoice_date_d"], rd)
            if rate is None and qty:
                reasons.append("not_chargeable_on_status")
                qty = D(0)
            if l["hole_section"] != rep.section or l["day_status"] != rep.status:
                reasons.append("section_or_status_differs_from_report")
        exp_amt = r2(qty * rate, ROUND_HALF_UP if rd.half_up else ROUND_HALF_EVEN) if (qty and rate is not None) else D(0)
        if rate is not None and l["rate"] != rate and qty:
            reasons.append("rate_differs")
        if r2(l["qty"] * l["rate"]) != l["amt"]:
            reasons.append("amount_ne_qty_x_rate")
        out[l["line_ref"]] = {"line": l, "exp_qty": qty, "exp_rate": rate, "exp_amt": exp_amt,
                              "delta": l["amt"] - exp_amt, "reasons": reasons}
    return out


def a3_adjustment(inv, lines, rd: Reading = BASELINE, per_well=False):
    """Clause 36A: difference on DD-101/DD-120 services performed >= 2026-02-01 and invoiced before the
    issue date, carried once on the first invoice submitted on or after 2026-08-17."""
    diff = defaultdict(lambda: D(0))
    for l in lines:
        I = inv[l["invoice_no"]]
        if l["service_code"] in ("DD-101", "DD-120") and l["date"] >= dt.date(2026, 2, 1) and I["invoice_date_d"] < A3_ISSUED:
            old, _ = build_rate(l["service_code"], l["date"], l["hole_section"], l["day_status"], I["well_class"], I["invoice_date_d"], rd)
            new, _ = build_rate(l["service_code"], l["date"], l["hole_section"], l["day_status"], I["well_class"], A3_ISSUED, rd)
            if old is not None and new is not None:
                diff[I["well_name"] if per_well else "*"] += r2(l["qty"] * new) - r2(l["qty"] * old)
    after = sorted((I["invoice_date_d"], n, I["well_name"]) for n, I in inv.items() if I["invoice_date_d"] >= A3_ISSUED)
    target = {}
    if per_well:
        for dte, n, w in after:
            if w in diff and w not in target:
                target[w] = n
        return {target[w]: diff[w] for w in target}
    return {after[0][1]: diff["*"]} if after else {}


def rebuild_invoices(inv, lines, priced, adjustments, vat_on_adjustment=False):
    by_inv = defaultdict(list)
    for l in lines:
        by_inv[l["invoice_no"]].append(l)
    res = {}
    for n, I in inv.items():
        L = by_inv[n]
        svc = sum((priced[l["line_ref"]]["exp_amt"] for l in L if l["service_code"] != "DS-900"), D(0))
        disc = -r2((svc - DISCOUNT_THRESHOLD) * DISCOUNT_PCT) if svc > DISCOUNT_THRESHOLD else D(0)
        net = svc + disc
        adj = adjustments.get(n, D(0))
        if vat_on_adjustment:
            net += adj
            adj = D(0)
        vat = r2(net * VAT)
        total = net + vat + adj
        res[n] = {"svc": svc, "disc": disc, "net": net, "vat": vat, "adj": adj, "total": total,
                  "billed_total": I["invoice_total_d"]}
    return res


def invoice_flags(inv, lines, priced, rebuilt):
    by_inv = defaultdict(list)
    for l in lines:
        by_inv[l["invoice_no"]].append(l)
    flags = {}
    for n, I in inv.items():
        cats = Counter()
        for l in by_inv[n]:
            if l["service_code"] == "DS-900":
                continue
            p = priced[l["line_ref"]]
            if p["delta"] != 0 or p["reasons"]:
                for r in p["reasons"] or ["amount_differs"]:
                    cats[r] += 1
        billed_disc = sum((l["amt"] for l in by_inv[n] if l["service_code"] == "DS-900"), D(0))
        billed_svc = sum((l["amt"] for l in by_inv[n] if l["service_code"] != "DS-900"), D(0))
        exp_disc_on_billed = -r2((billed_svc - DISCOUNT_THRESHOLD) * DISCOUNT_PCT) if billed_svc > DISCOUNT_THRESHOLD else D(0)
        if billed_disc != exp_disc_on_billed:
            cats["discount_DS900_wrong"] += 1
        if billed_svc + billed_disc != I["net_amount_d"]:
            cats["net_ne_sum_lines"] += 1
        if r2(I["net_amount_d"] * VAT) != I["vat_amount_d"]:
            cats["vat_wrong"] += 1
        if I["net_amount_d"] + I["vat_amount_d"] + I["adjustment_d"] != I["invoice_total_d"]:
            cats["total_ne_net_plus_vat"] += 1
        if rebuilt[n]["adj"] != I["adjustment_d"]:
            cats["a3_adjustment_missing"] += 1
        if I["contract_ref"] != "DDS-2025-118":
            cats["contract_ref_wrong"] += 1
        if I["invoice_date_d"] < I["period_end_d"]:
            cats["submitted_before_period_end"] += 1
        if (I["invoice_date_d"] - I["period_end_d"]).days > 30:
            cats["submitted_over_30_days"] += 1
        if I["period_end_d"] > TERM_END or I["period_start_d"] < TERM_START:
            cats["period_outside_term"] += 1
        flags[n] = cats
    return flags


def run() -> dict:
    inv = load_invoices()
    lines = load_lines()
    reps = load_reports()
    res = {}
    priced = reprice(inv, lines, reps)
    adj = a3_adjustment(inv, lines)
    rebuilt = rebuild_invoices(inv, lines, priced, adj)
    flags = invoice_flags(inv, lines, priced, rebuilt)

    n_lines = len(priced)
    exact = sum(1 for p in priced.values() if p["delta"] == 0 and not p["reasons"])
    res["priced_lines"] = n_lines
    res["lines_exact_match_no_reason"] = exact
    res["lines_with_delta"] = sum(1 for p in priced.values() if p["delta"] != 0)
    res["lines_by_reason"] = dict(Counter(r for p in priced.values() for r in p["reasons"]))
    res["lines_supported_but_unpriceable"] = sum(1 for p in priced.values() if p["exp_rate"] is None and p["exp_qty"])
    res["a3_adjustment"] = {k: str(v) for k, v in adj.items()}
    res["a3_adjustment_per_well_alternative"] = {k: str(v) for k, v in a3_adjustment(inv, lines, per_well=True).items()}
    flagged = {n for n, c in flags.items() if c}
    res["invoices_flagged"] = len(flagged)
    res["invoices_flagged_pct"] = round(100 * len(flagged) / len(inv), 2)
    res["invoices_by_category"] = dict(Counter(c for cs in flags.values() for c in cs))
    res["invoices_total_changes"] = sum(1 for n, r in rebuilt.items() if r["total"] != r["billed_total"])
    res["flagged_but_total_unchanged"] = sorted(n for n in flagged if rebuilt[n]["total"] == rebuilt[n]["billed_total"])
    res["total_changed_but_not_flagged"] = sorted(n for n in inv if n not in flagged and rebuilt[n]["total"] != rebuilt[n]["billed_total"])
    res["sum_billed_minus_expected_usd"] = str(sum((r["billed_total"] - r["total"] for r in rebuilt.values()), D(0)))

    rows = []
    for n in sorted(flagged):
        r = rebuilt[n]
        rows.append({"invoice_no": n, "categories": ";".join(sorted(flags[n])), "billed_total": str(r["billed_total"]),
                     "expected_total": str(r["total"]), "difference": str(r["billed_total"] - r["total"])})
    write_out("flagged_invoices.csv", rows)
    lrows = []
    for ref, p in sorted(priced.items()):
        if p["delta"] != 0 or p["reasons"]:
            l = p["line"]
            lrows.append({"line_ref": ref, "code": l["service_code"], "date": l["service_date"], "report_ref": l["report_ref"],
                          "billed_qty": str(l["qty"]), "billed_rate": str(l["rate"]), "billed_amount": str(l["amt"]),
                          "exp_qty": str(p["exp_qty"]), "exp_rate": str(p["exp_rate"]), "exp_amount": str(p["exp_amt"]),
                          "reasons": ";".join(p["reasons"])})
    write_out("line_exceptions.csv", lrows)
    res["examples_per_reason"] = {}
    for rr in lrows:
        for reason in rr["reasons"].split(";"):
            res["examples_per_reason"].setdefault(reason, [])
            if len(res["examples_per_reason"][reason]) < 3:
                res["examples_per_reason"][reason].append(
                    f"{rr['line_ref']} {rr['code']} {rr['date']} billed {rr['billed_qty']}x{rr['billed_rate']}={rr['billed_amount']} "
                    f"-> {rr['exp_qty']}x{rr['exp_rate']}={rr['exp_amount']}")

    # --- alternatives: one switch at a time
    base_amt = {k: p["exp_amt"] for k, p in priced.items()}
    base_tot = {n: r["total"] for n, r in rebuilt.items()}
    alts = {
        "section factor kept on Standby (Clause 18 literal)": (replace(BASELINE, no_section_factor_on_standby=False), EVIDENCE),
        "class factor applied to PD-210 (Sch.2 note)": (replace(BASELINE, no_class_factor_on_pd210=False), EVIDENCE),
        "no index on MW-310/HC-620 (Appendix B)": (replace(BASELINE, apply_index=False), EVIDENCE),
        "S2 monthly DD-120 beats A3 from Apr-2026": (replace(BASELINE, dd120_a3_over_s2_monthly=False), EVIDENCE),
        "rate discount folded into standby step": (replace(BASELINE, discount_separate_step=False), EVIDENCE),
        "A3 applied to pre-issue invoices too": (replace(BASELINE, a3_only_from_issue=False), EVIDENCE),
        "LIH at Schedule 6 USD, not Sch.2D SAR": (replace(BASELINE, lih_from_sar=False), EVIDENCE),
        "no Clause 25A metre tolerance": (replace(BASELINE, metre_tolerance=False), EVIDENCE),
        "round half up instead of half to even": (replace(BASELINE, half_up=True), EVIDENCE),
        "Clause 21A off": (BASELINE, EvidenceOptions(chargeable_hour_minus_one=False)),
        "LWD words read literally": (BASELINE, EvidenceOptions(chargeable_hour_minus_one=True, lwd_map="literal")),
        "PD-210 on every 12-1/4/8-1/2 Operating day": (BASELINE, EvidenceOptions(chargeable_hour_minus_one=True, pd210_rule="section_only")),
    }
    res["alternatives"] = {}
    for name, (rd, opt) in alts.items():
        p2 = reprice(inv, lines, reps, rd, opt)
        a2 = a3_adjustment(inv, lines, rd)
        r2_ = rebuild_invoices(inv, lines, p2, a2)
        res["alternatives"][name] = {
            "lines_amount_changed_vs_baseline": sum(1 for k in p2 if p2[k]["exp_amt"] != base_amt[k]),
            "invoices_total_changed_vs_baseline": sum(1 for n in r2_ if r2_[n]["total"] != base_tot[n]),
            "invoices_disagreeing_with_billed": sum(1 for n in r2_ if r2_[n]["total"] != r2_[n]["billed_total"]),
        }
    # join by report_ref date instead of service_date
    p3 = reprice(inv, lines, reps, date_source="report_ref")
    r3 = rebuild_invoices(inv, lines, p3, adj)
    res["alternatives"]["evidence day taken from report_ref"] = {
        "lines_amount_changed_vs_baseline": sum(1 for k in p3 if p3[k]["exp_amt"] != base_amt[k]),
        "invoices_total_changed_vs_baseline": sum(1 for n in r3 if r3[n]["total"] != base_tot[n]),
        "invoices_disagreeing_with_billed": sum(1 for n in r3 if r3[n]["total"] != r3[n]["billed_total"]),
    }
    r4 = rebuild_invoices(inv, lines, priced, adj, vat_on_adjustment=True)
    res["a3_adjustment_invoice_total_without_vat_vs_with_vat"] = {
        n: [str(rebuilt[n]["total"]), str(r4[n]["total"])] for n in adj}
    res["_flags"] = {n: dict(c) for n, c in flags.items() if c}
    res["_rebuilt_totals"] = {n: str(r["total"]) for n, r in rebuilt.items()}
    return res


if __name__ == "__main__":
    import json
    r = run()
    r.pop("_flags"); r.pop("_rebuilt_totals")
    print(json.dumps(r, indent=1, default=str))
