"""Report parsing (Clause 15, Schedule 5, Appendix G) and what a report supports (Clauses 20-31),
on the real reports and on synthetic reports for rules the data never exercises."""
import dataclasses
import datetime as dt
import unittest
from collections import Counter
from decimal import Decimal as D

from _support import inputs, reports
from drilling_audit import contract as C
from drilling_audit.audit import run_audit
from drilling_audit.config import PRODUCTION, EvidenceOptions
from drilling_audit.evidence import WellFacts, supported
from drilling_audit.loader import Inputs, Invoice, Line
from drilling_audit.reports import parse_text

d = dt.date


def report_text(**kw) -> str:
    """A synthetic report in the dataset's layout; keyword overrides replace field values."""
    f = {"Report": "DDR-900-20250610", "Contract": "DDS-2025-118", "Well": "TST-XX-900", "Rig": "NG-Rig 1",
         "Date": "10-Jun-2025", "Hole section": '12-1/4"', "Status": "Operating", "Depth start (m MD)": "1400",
         "Depth end (m MD)": "1600", "Circulating hours": "12", "BHA run": "2",
         "In the hole": "MWD collar, rotary steerable, gamma tool", "Crew on tour": "2 directional hands, 1 night man, "
         "2 MWD engineers, 1 logging engineers, 1 performance engineer", "Gyro surveys": "0", "Pressure points": "0",
         "Wiper trips": "0", "Back-reaming hours": "0", "Clean-out runs": "0", "Run": "2",
         "Run first day": "09-Jun-2025", "Run last day": "12-Jun-2025", "Run circulating hours": "40",
         "Metres logged": "600", "Metres reamed": "0", "Radioactive source carried": "No",
         "Signed (Company Representative)": "A. Rep", "Signed (lead directional driller)": "B. Lead"}
    extra_parts = kw.pop("extra_parts", "")
    f.update(kw)
    f["Tools in run"] = kw.get("Tools in run", f["In the hole"])
    a = ["Hole section", "Status", "Depth start (m MD)", "Depth end (m MD)", "Circulating hours", "BHA run",
         "In the hole", "Crew on tour", "Gyro surveys", "Pressure points", "Wiper trips", "Back-reaming hours",
         "Clean-out runs"]
    b = ["Run", "Run first day", "Run last day", "Tools in run", "Run circulating hours", "Metres logged",
         "Metres reamed", "Radioactive source carried"]
    out = ["DAILY DRILLING REPORT"] + [f"{k}: {f[k]}" for k in ("Report", "Contract", "Well", "Rig", "Date")]
    out += ["", "PART A — OPERATIONS SUMMARY"] + [f"{k}: {f[k]}" for k in a]
    out += ["", "PART B — BHA RUN RECORD"] + [f"{k}: {f[k]}" for k in b]
    if extra_parts:
        out += ["", extra_parts]
    out += ["", f"Signed (Company Representative): {f['Signed (Company Representative)']}",
            f"Signed (lead directional driller): {f['Signed (lead directional driller)']}"]
    return "\r\n".join(out) + "\r\n"


FACTS = WellFacts(d(2025, 6, 1), d(2025, 6, 30), True)


class RealReports(unittest.TestCase):
    def test_all_reports_parse_cleanly(self):
        reps = reports()
        self.assertEqual(len(reps), 8151)
        self.assertEqual([r.file for r in reps.values() if r.problems], [])

    def test_parts_status_signatures(self):
        reps = reports().values()
        self.assertEqual(Counter("".join(r.parts) for r in reps),
                         Counter({"AB": 7258, "ABC": 476, "ABD": 363, "ABE": 47, "ABDE": 4, "ABCE": 3}))
        self.assertEqual(Counter(r.status for r in reps), Counter({"Operating": 7770, "Standby": 381}))
        self.assertEqual(sorted(r.file for r in reps if not r.signed),
                         ["DDR_NGP-BD-149_20251122.txt", "DDR_NGP-BD-218_20251029.txt", "DDR_NGP-WS-055_20250503.txt"])

    def test_known_report_BD_011_20260225(self):
        r = reports()[("NGP-BD-011", d(2026, 2, 25))]
        self.assertEqual(r.crew, {"DD-101": 2, "DD-102": 1, "MW-301": 2})
        self.assertEqual(set(r.tools), {"MW-310", "HC-620", "DD-110", "MW-330"})
        self.assertEqual((r.depth_start, r.depth_end, r.circulating_hours, r.run, r.parts), (0, 275, 15, 1, ("A", "B", "C")))
        s = supported(r, WellFacts(d(2026, 2, 25), d(2026, 4, 10), True))
        self.assertEqual(s.qty["DD-130"], 1)
        self.assertEqual((s.qty["MB-701"], s.qty["DD-140"]), (1, 1))
        self.assertNotIn("DD-120", s.qty)
        self.assertNotIn("PD-210", s.qty)             # 26" is not a performance section

    def test_chargeable_hour_on_real_report(self):
        r = reports()[("NGP-BD-011", d(2026, 3, 8))]
        self.assertEqual(r.circulating_hours, 16)
        self.assertEqual(supported(r, WellFacts(d(2026, 2, 25), d(2026, 4, 10), True)).qty["DD-120"], 15)

    def test_run_records_agree_with_daily_reports(self):
        # Part B figures equal the sums of the daily figures on every run: independent support for reading
        # metres and hours from each day's Part A.
        runs = {}
        for r in reports().values():
            runs.setdefault((r.well, r.run), []).append(r)
        self.assertEqual(len(runs), 1369)
        for (well, run), rs in runs.items():
            f = rs[0].fields
            self.assertEqual(sum(x.circulating_hours for x in rs), int(f["Run circulating hours"]), (well, run))
            logged = sum(x.metres for x in rs if x.operating and set(x.tools) & C.LWD_METRE_TOOLS)
            reamed = sum(x.metres for x in rs if x.operating and "RM-511" in x.tools)
            self.assertEqual((logged, reamed), (int(f["Metres logged"]), int(f["Metres reamed"])), (well, run))

    def test_conditional_parts_absent_only_where_flagged(self):
        reps = reports().values()
        gyro_no_c = [r.file for r in reps if r.count("Gyro surveys") and "C" not in r.parts]
        source_no_d = sorted(r.file for r in reps if r.source_carried and r.run_first_day and "D" not in r.parts)
        self.assertEqual(gyro_no_c, ["DDR_NGP-WS-009_20251211.txt"])
        self.assertEqual(source_no_d, ["DDR_NGP-WS-029_20260515.txt", "DDR_NGP-WS-201_20251115.txt"])
        self.assertTrue(all(r.count("Gyro surveys taken") == r.count("Gyro surveys") for r in reps if "C" in r.parts))

    def test_resistivity_word_travels_with_the_source(self):
        # Appendix G maps "resistivity tool" to LW-411 (density-neutron, the radioactive tool).
        reps = reports().values()
        self.assertTrue(all(r.source_carried == ("LW-411" in r.tools) for r in reps))


class ParserSynthetic(unittest.TestCase):
    def test_clean_synthetic(self):
        r = parse_text(report_text())
        self.assertEqual(r.problems, [])
        self.assertTrue(r.signed)

    def test_unknown_wording_is_a_problem_not_a_guess(self):
        r = parse_text(report_text(**{"In the hole": "MWD collar, steerable motor"}))
        self.assertIn("MW-310", r.tools)
        self.assertNotIn("DD-120", r.tools)
        self.assertTrue(any("steerable motor" in p for p in r.problems))
        r = parse_text(report_text(**{"Crew on tour": "2 directional drillers"}))
        self.assertTrue(any("directional drillers" in p for p in r.problems))

    def test_one_missing_signature_is_unsigned(self):
        r = parse_text(report_text(**{"Signed (lead directional driller)": "____________________"}))
        self.assertFalse(r.signed)
        self.assertEqual(r.missing_signatures, ["Signed (lead directional driller)"])
        r = parse_text(report_text(**{"Signed (Company Representative)": ""}))
        self.assertFalse(r.signed)

    def test_structure_problems(self):
        self.assertTrue(parse_text(report_text(Status="Rig move")).problems)
        self.assertTrue(parse_text(report_text(**{"Hole section": '9-7/8"'})).problems)
        self.assertTrue(parse_text(report_text(Report="DDR-901-20250610")).problems)
        self.assertTrue(parse_text(report_text(Contract="DDS-2025-181")).problems)
        e = "PART E — LOST IN HOLE\r\nLost in hole run: 2\r\nLost in hole tool: jar\r\nCirculating hours accumulated on the well: 80"
        self.assertTrue(any("Lost in hole tool" in p for p in parse_text(report_text(extra_parts=e)).problems))


class Support(unittest.TestCase):
    def sup(self, opt=EvidenceOptions(), facts=FACTS, **kw):
        return supported(parse_text(report_text(**kw)), facts, opt)

    def test_operating_day(self):
        s = self.sup()
        self.assertEqual(s.qty["DD-120"], 11)                 # 12 h - 1 (21A)
        self.assertEqual(s.qty["LW-410"], 200)                # "gamma tool" -> LW-410 (Appendix G)
        self.assertEqual(s.qty["PD-210"], 200)                # performance engineer on a 12-1/4" day
        self.assertEqual(s.pd210_segments, [(1400, 1500), (1500, 1600)])
        self.assertEqual(s.qty["LW-401"], 1)

    def test_minimum_hours_and_21A_order(self):
        # Clause 21 minimum never engages in the data (lowest Operating RSS day: 8 h). Synthetic:
        self.assertEqual(self.sup(**{"Circulating hours": "5"}).qty["DD-120"], 6)            # max(4, 6)
        self.assertEqual(self.sup(**{"Circulating hours": "7"}).qty["DD-120"], 6)            # max(6, 6)
        self.assertEqual(self.sup(**{"Circulating hours": "0"}).qty["DD-120"], 6)            # tool in hole, 0 h
        alt = EvidenceOptions(minimum_order="minimum_then_minus")
        self.assertEqual(self.sup(alt, **{"Circulating hours": "5"}).qty["DD-120"], 5)       # max(5, 6) - 1
        self.assertEqual(self.sup(alt, **{"Circulating hours": "9"}).qty["DD-120"], 8)
        self.assertEqual(self.sup(EvidenceOptions(chargeable_hour="off"), **{"Circulating hours": "9"}).qty["DD-120"], 9)

    def test_chargeable_hour_per_run_alternative(self):
        per_run = EvidenceOptions(chargeable_hour="per_run")
        self.assertEqual(self.sup(per_run).qty["DD-120"], 12)                                # not the run's first day
        self.assertEqual(self.sup(per_run, **{"Run first day": "10-Jun-2025"}).qty["DD-120"], 11)

    def test_back_reaming_hours_21A(self):
        self.assertEqual(self.sup(**{"Back-reaming hours": "4"}).qty["RM-530"], 3)
        self.assertNotIn("RM-530", self.sup(**{"Back-reaming hours": "1"}).qty)

    def test_standby_day(self):
        s = self.sup(Status="Standby", **{"In the hole": "MWD collar, rotary steerable, float sub, gamma tool"})
        self.assertEqual(s.qty.get("DD-121"), 1)
        for code in ("DD-120", "HC-640", "LW-410", "PD-210"):
            self.assertNotIn(code, s.qty)
        self.assertEqual(s.qty["MW-310"], 1)
        self.assertEqual(s.qty["DD-101"], 2)

    def test_daily_limits(self):
        s = self.sup(**{"Crew on tour": "3 directional hands, 2 logging engineers", "Circulating hours": "26"})
        self.assertEqual((s.qty["DD-101"], s.qty["LW-401"], s.qty["DD-120"]), (2, 1, 24))
        s = supported(parse_text(report_text(**{"Crew on tour": "3 directional hands"})), FACTS,
                      EvidenceOptions(apply_daily_limits=False))
        self.assertEqual(s.qty["DD-101"], 3)

    def test_per_run_and_per_well(self):
        s = self.sup(**{"In the hole": "mud motor", "Run last day": "10-Jun-2025",
                        "Radioactive source carried": "Yes", "Run first day": "10-Jun-2025"})
        self.assertEqual((s.qty["DD-111"], s.qty["LW-420"]), (1, 1))
        s = self.sup(facts=WellFacts(d(2025, 6, 10), d(2025, 6, 10), False))
        self.assertEqual({c: s.qty[c] for c in ("MB-701", "DD-140", "MB-702")}, {"MB-701": 1, "DD-140": 1, "MB-702": 1})
        self.assertNotIn("LW-430", s.qty)                       # no LWD on the well
        s = self.sup(facts=WellFacts(d(2025, 6, 1), d(2025, 6, 10), True))
        self.assertEqual(s.qty["LW-430"], 1)

    def test_pd210_proxy_alternatives(self):
        crew = {"Crew on tour": "2 directional hands"}
        self.assertNotIn("PD-210", self.sup(**crew).qty)
        self.assertIn("PD-210", self.sup(EvidenceOptions(pd210_rule="section_only"), **crew).qty)
        self.assertNotIn("PD-210", self.sup(**{"Hole section": '17-1/2"'}).qty)
        self.assertNotIn("PD-210", self.sup(Status="Standby").qty)


def synthetic_audit(lines_spec, report_kw_list, cfg=PRODUCTION, invoices_spec=None):
    """Run the full pipeline on hand-made invoices, lines and reports."""
    reps = {}
    for kw in report_kw_list:
        r = parse_text(report_text(**kw))
        reps[r.key] = r
    invs = {}
    for spec in invoices_spec or [("MDS-90001", d(2025, 6, 9), d(2025, 6, 12), d(2025, 6, 20))]:
        n, a, b, idate = spec
        invs[n] = Invoice(n, "DDS-2025-118", C.CONTRACTOR, "TST-XX-900", "NG-Rig 1", "Test", "Standard", a, b, idate,
                          D(0), D(0), D(0), D(0), "0.00")
    lines, count = [], Counter()
    for inv_no, day, code, qty, rate, extra in lines_spec:
        count[inv_no] += 1
        desc, unit, _ = C.SCHEDULE_1[code]
        lines.append(Line(f"{inv_no}-{count[inv_no]:03d}", inv_no, count[inv_no], day, "TST-XX-900", code, desc, unit,
                          extra.get("section", '12-1/4"'), extra.get("status", "Operating"), extra.get("dfrom"),
                          extra.get("dto"), D(qty), D(rate), (D(qty) * D(rate)).quantize(D("0.01")),
                          f"DDR-900-{day:%Y%m%d}"))
    for n, I in list(invs.items()):              # billed figures consistent with the lines (Cl 36, 39, 40)
        net = sum((ln.amount for ln in lines if ln.invoice_no == n), D(0))
        tax = (net * C.VAT_RATE).quantize(D("0.01"))
        invs[n] = dataclasses.replace(I, net_amount=net, vat_amount=tax, invoice_total=net + tax)
    return run_audit(Inputs(invs, lines, ""), reps, cfg)


class SyntheticPipeline(unittest.TestCase):
    DAY = d(2025, 6, 10)

    def test_metre_tolerance_25A(self):
        # 200 m supported; 202 m is within 1 % (payable as charged); 203 m is beyond (paid at 200)
        res = synthetic_audit([("MDS-90001", self.DAY, "LW-410", 202, "11.37", {})], [{}])
        r = res.lines["MDS-90001-001"]
        self.assertEqual((r.paid_qty, r.reasons), (D(202), []))
        res = synthetic_audit([("MDS-90001", self.DAY, "LW-410", 203, "11.37", {})], [{}])
        r = res.lines["MDS-90001-001"]
        self.assertEqual((r.paid_qty, r.reasons, r.expected_amount), (D(200), ["qty_above_report"], D("2274.00")))
        res = synthetic_audit([("MDS-90001", self.DAY, "LW-410", 202, "11.37", {})], [{}],
                              PRODUCTION.with_evidence(metre_tolerance=False))
        self.assertEqual(res.lines["MDS-90001-001"].paid_qty, D(200))

    def test_unknown_wording_becomes_query(self):
        res = synthetic_audit([("MDS-90001", self.DAY, "MW-310", 1, "2326.70", {})],
                              [{"In the hole": "MWD collar, steerable motor"}])
        r, inv = res.lines["MDS-90001-001"], res.invoices["MDS-90001"]
        self.assertEqual(r.reasons, ["report_unreadable"])
        self.assertTrue(r.query)
        self.assertEqual(r.expected_amount, r.line.amount)          # not priced, not zeroed
        self.assertTrue(inv.flagged)
        self.assertEqual((inv.error_category, inv.confidence), ("record_unrecognised", 0.5))

    def test_duplicate_across_invoices(self):
        spec = [("MDS-90001", self.DAY, "MW-310", 1, "2326.70", {}), ("MDS-90002", self.DAY, "MW-310", 1, "2326.70", {})]
        invs = [("MDS-90001", d(2025, 6, 9), d(2025, 6, 12), d(2025, 6, 20)),
                ("MDS-90002", d(2025, 6, 10), d(2025, 6, 10), d(2025, 6, 21))]
        res = synthetic_audit(spec, [{}], invoices_spec=invs)
        self.assertEqual(res.lines["MDS-90001-001"].reasons, [])     # MW-310 12-1/4" June 2025: 2,326.70
        self.assertEqual(res.lines["MDS-90002-001"].reasons, ["already_billed"])

    def test_unsigned_policies(self):
        spec = [("MDS-90001", self.DAY, "MW-310", 1, "2326.70", {}), ("MDS-90001", self.DAY, "LW-410", 200, "11.37", {})]
        rep = [{"Signed (Company Representative)": "____"}]
        a = synthetic_audit(spec, rep)
        self.assertEqual([a.lines[k].expected_amount for k in ("MDS-90001-001", "MDS-90001-002")], [D(0), D(0)])
        b = synthetic_audit(spec, rep, PRODUCTION.with_(unsigned_policy="zero_schedule5"))
        self.assertEqual([b.lines[k].expected_amount for k in ("MDS-90001-001", "MDS-90001-002")], [D("2326.70"), D(0)])
        c = synthetic_audit(spec, rep, PRODUCTION.with_(unsigned_policy="flag_only"))
        self.assertEqual([c.lines[k].expected_amount for k in ("MDS-90001-001", "MDS-90001-002")],
                         [D("2326.70"), D("2274.00")])
        for res in (a, b, c):
            self.assertTrue(res.invoices["MDS-90001"].flagged)
            self.assertIn("record_not_signed", res.invoices["MDS-90001"].causes)

    def test_wrong_unit_and_status(self):
        res = synthetic_audit([("MDS-90001", self.DAY, "MW-320", 1, "779.65", {"status": "Standby"})],
                              [{"In the hole": "survey package"}])
        r = res.lines["MDS-90001-001"]
        self.assertIn("section_or_status_differs", r.reasons)       # report says Operating; it governs
        self.assertEqual(r.expected_amount, D("779.65"))


if __name__ == "__main__":
    unittest.main()
