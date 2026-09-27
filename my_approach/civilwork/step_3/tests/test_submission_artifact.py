"""The generated civil-works submission part: schema, ids, cents, determinism, the
committed copy being current, the merge guard, and the sensitivity outputs."""
import csv
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from _support import REPO, SRC, STEP3

TEMPLATE = os.path.join(REPO, "invoice-auditing-level-2", "submission_template.csv")
APPS = os.path.join(REPO, "invoice-auditing-level-2", "civilwork", "invoices", "applications.csv")
COMMITTED = os.path.join(STEP3, "output")
PART = "civilwork_submission_part.csv"
OUTPUTS = [PART, "civilwork_line_audit.csv", "civilwork_application_audit.csv", "civilwork_ablation.csv",
           "civilwork_scenarios.csv", "civilwork_run_summary.json"]


def run(script, *args):
    return subprocess.run([sys.executable, os.path.join(SRC, script), *args], capture_output=True, text=True, cwd=REPO)


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class GeneratedArtifact(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.out1, cls.out2 = os.path.join(cls.tmp, "run1"), os.path.join(cls.tmp, "run2")
        for out in (cls.out1, cls.out2):
            p = run("run_civilwork_audit.py", "--out", out)
            if p.returncode:
                raise RuntimeError(p.stderr)
        cls.rows = read(os.path.join(cls.out1, PART))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_two_runs_are_byte_identical(self):
        for name in OUTPUTS:
            self.assertTrue(filecmp.cmp(os.path.join(self.out1, name), os.path.join(self.out2, name), shallow=False), name)

    def test_committed_artifacts_are_current(self):
        for name in OUTPUTS:
            self.assertTrue(filecmp.cmp(os.path.join(self.out1, name), os.path.join(COMMITTED, name), shallow=False),
                            f"{name} is stale: rerun run_civilwork_audit.py")

    def test_columns_and_ids(self):
        with open(os.path.join(self.out1, PART), encoding="utf-8") as f:
            header = f.readline().strip()
        with open(TEMPLATE, encoding="utf-8") as f:
            self.assertEqual(header, f.readline().strip())
        ids = [r["invoice_id"] for r in self.rows]
        template_pa = [r["invoice_id"] for r in read(TEMPLATE) if r["invoice_id"].startswith("PA-")]
        self.assertEqual(len(ids), 900)
        self.assertEqual(len(set(ids)), 900)
        self.assertEqual(ids, template_pa)
        self.assertEqual(ids, [f"PA-{i:05d}" for i in range(1, 901)])

    def test_billed_cents_from_csv_text(self):
        billed = {r["application_no"]: r["application_total"] for r in read(APPS)}
        for r in self.rows:
            text = billed[r["invoice_id"]]
            whole, frac = text.split(".")
            self.assertEqual(len(frac), 2)
            self.assertEqual(r["billed_total_cents"], str(int(whole) * 100 + int(frac)))

    def test_values(self):
        flagged = 0
        for r in self.rows:
            self.assertIn(r["flagged"], ("0", "1"))
            self.assertRegex(r["expected_total_cents"], r"^\d+$")
            self.assertRegex(r["billed_total_cents"], r"^\d+$")
            self.assertTrue(0 <= float(r["confidence"]) <= 1)
            self.assertEqual(r["flagged"] == "1", r["error_category"] != "")
            if r["flagged"] == "0":
                self.assertEqual(r["expected_total_cents"], r["billed_total_cents"])
            flagged += r["flagged"] == "1"
        self.assertEqual(flagged, 59)
        by_id = {r["invoice_id"]: r for r in self.rows}
        self.assertEqual(by_id["PA-00043"]["expected_total_cents"], "23142526")
        self.assertEqual(by_id["PA-00125"]["expected_total_cents"], "0")
        self.assertEqual(by_id["PA-00443"]["expected_total_cents"], by_id["PA-00443"]["billed_total_cents"])

    def test_audit_trail_covers_every_line_and_application(self):
        lines = read(os.path.join(self.out1, "civilwork_line_audit.csv"))
        apps = read(os.path.join(self.out1, "civilwork_application_audit.csv"))
        self.assertEqual((len(lines), len({l["line_ref"] for l in lines})), (7746, 7746))
        self.assertEqual(len(apps), 900)
        for l in lines:
            if l["categories"]:
                self.assertTrue(l["clauses"] and l["reasons"], l["line_ref"])
            self.assertTrue(l["calculation"], l["line_ref"])

    def test_merge_refuses_without_drilling_rows(self):
        p = run("merge_submission.py", "--part", os.path.join(self.out1, PART), "--out", os.path.join(self.tmp, "s.csv"))
        self.assertEqual(p.returncode, 2)
        self.assertIn("1906 template ids missing", p.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "s.csv")))

    def test_merge_with_a_complete_second_part(self):
        # A placeholder drilling part exists only inside this test's temp folder.
        dummy = os.path.join(self.tmp, "drilling_dummy.csv")
        with open(dummy, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["invoice_id", "flagged", "error_category", "expected_total_cents", "billed_total_cents", "confidence"])
            for r in read(TEMPLATE):
                if not r["invoice_id"].startswith("PA-"):
                    w.writerow([r["invoice_id"], 0, "", 0, 0, "0.50"])
        out = os.path.join(self.tmp, "merged.csv")
        p = run("merge_submission.py", "--part", os.path.join(self.out1, PART), "--part", dummy, "--out", out)
        self.assertEqual(p.returncode, 0, p.stderr)
        merged = read(out)
        self.assertEqual([r["invoice_id"] for r in merged], [r["invoice_id"] for r in read(TEMPLATE)])
        self.assertEqual(len(merged), 2806)

    def test_ablation_matches_verification_report(self):
        abl = {r["reading"]: (int(r["lost"]), int(r["gained"])) for r in read(os.path.join(self.out1, "civilwork_ablation.csv"))}
        self.assertEqual(abl["without 27A ground freeze"], (837, 2))
        self.assertEqual(abl["without Sch 4 Pt 3 bands"], (859, 4))
        self.assertEqual(abl["bands not reset at Contract Year 2 (3A)"], (268, 0))
        self.assertEqual(abl["without 31A (reprice pre-issue applications)"], (88, 0))
        self.assertEqual(abl["band order by application date"], (72, 0))
        self.assertEqual(abl["final rounding half-even (not Cl 28 half-up)"], (116, 0))
        self.assertEqual(abl["conversion rounding half-up (not 26A/29A half-even)"], (18, 0))

    def test_scenarios_match_verification_report(self):
        sc = {r["scenario"]: r for r in read(os.path.join(self.out1, "civilwork_scenarios.csv"))}
        flagged = {k: int(r["flagged"]) for k, r in sc.items()}
        self.assertEqual(list(flagged.values()), [59, 59, 59, 59, 62, 61, 77, 94, 59, 59, 59, 59, 58, 67], flagged)
        self.assertEqual(sc["Q2: repeated A.16.010 week within one application only"]["added"], "PA-00116;PA-00395")
        self.assertEqual(sc["Q3: keep lines executed after submission"]["expected_delta_sar"], "25068.53")
        self.assertEqual(sc["reading: bands counted on supported quantity"]["expected_total_changed"], "")


if __name__ == "__main__":
    unittest.main()
