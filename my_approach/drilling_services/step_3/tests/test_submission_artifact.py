"""The generated artifacts: determinism, currency of the committed files, schema, and the merge guard."""
import csv
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest

from _support import OUTPUT, REPO, SRC

RUNNER = os.path.join(SRC, "run_drilling_audit.py")
CIVIL_SRC = os.path.join(REPO, "my_approach", "civilwork", "step_3", "src")
CIVIL_PART = os.path.join(REPO, "my_approach", "civilwork", "step_3", "output", "civilwork_submission_part.csv")
DRILL_PART = os.path.join(OUTPUT, "drilling_submission_part.csv")
TEMPLATE = os.path.join(REPO, "invoice-auditing-level-2", "submission_template.csv")
SUBMISSION = os.path.join(REPO, "submission.csv")
COMPARED = ["drilling_submission_part.csv", "drilling_invoice_audit.csv", "drilling_line_exceptions.csv",
            "drilling_line_audit.csv", "drilling_run_summary.json"]


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Determinism(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dirs = [tempfile.mkdtemp(), tempfile.mkdtemp()]
        for out in cls.dirs:
            subprocess.run([sys.executable, RUNNER, "--out", out, "--skip-sensitivity"], check=True,
                           capture_output=True, cwd=REPO)

    def test_two_runs_identical(self):
        for name in COMPARED:
            self.assertEqual(sha(os.path.join(self.dirs[0], name)), sha(os.path.join(self.dirs[1], name)), name)

    def test_committed_outputs_are_current(self):
        for name in COMPARED:
            if name == "drilling_line_audit.csv" and not os.path.exists(os.path.join(OUTPUT, name)):
                continue        # regenerated, not committed (see .gitignore)
            self.assertEqual(sha(os.path.join(self.dirs[0], name)), sha(os.path.join(OUTPUT, name)), name)


class Schema(unittest.TestCase):
    def test_drilling_part(self):
        rows = read(DRILL_PART)
        with open(TEMPLATE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            template_ids = [r["invoice_id"] for r in reader]
            columns = reader.fieldnames
        self.assertEqual(list(rows[0]), columns)
        self.assertEqual([r["invoice_id"] for r in rows], [i for i in template_ids if i.startswith("MDS-")])
        raw = {r["invoice_no"]: r["invoice_total"] for r in read(os.path.join(
            REPO, "invoice-auditing-level-2", "drilling_services", "invoices", "invoices.csv"))}
        for r in rows:
            self.assertRegex(r["expected_total_cents"], r"^-?\d+$")
            self.assertEqual(r["billed_total_cents"], raw[r["invoice_id"]].replace(".", "").lstrip("0") or "0")
            self.assertIn(r["flagged"], ("0", "1"))
            self.assertEqual(r["flagged"] == "1", bool(r["error_category"]))
            if r["flagged"] == "0":
                self.assertEqual(r["expected_total_cents"], r["billed_total_cents"])
            self.assertTrue(0 <= float(r["confidence"]) <= 1)
        self.assertEqual(sum(r["flagged"] == "1" for r in rows), 120)


class Merge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, CIVIL_SRC)
        import merge_submission
        from civilwork_audit.submission import SubmissionError
        cls.merge, cls.err = staticmethod(merge_submission.merge), SubmissionError

    def write_part(self, rows):
        f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8")
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        f.close()
        return f.name

    def test_missing_ids_refused(self):
        with self.assertRaisesRegex(self.err, "900 template ids missing"):
            self.merge(TEMPLATE, [DRILL_PART])
        rows = read(DRILL_PART)[:-1]
        with self.assertRaisesRegex(self.err, "1 template ids missing"):
            self.merge(TEMPLATE, [CIVIL_PART, self.write_part(rows)])

    def test_extra_id_refused(self):
        rows = read(DRILL_PART) + [dict(read(DRILL_PART)[0], invoice_id="MDS-09999")]
        with self.assertRaisesRegex(self.err, "not in the template"):
            self.merge(TEMPLATE, [CIVIL_PART, self.write_part(rows)])

    def test_duplicate_id_refused(self):
        with self.assertRaisesRegex(self.err, "more than one part"):
            self.merge(TEMPLATE, [CIVIL_PART, DRILL_PART, DRILL_PART])
        rows = read(DRILL_PART)
        with self.assertRaisesRegex(self.err, "more than one part"):
            self.merge(TEMPLATE, [CIVIL_PART, self.write_part(rows + rows[:1])])

    def test_submission_csv_is_the_merge(self):
        merged = self.merge(TEMPLATE, [CIVIL_PART, DRILL_PART])
        self.assertEqual(read(SUBMISSION), merged)
        self.assertEqual(len(merged), 2806)
        self.assertEqual(len({r["invoice_id"] for r in merged}), 2806)
        civil = {r["application_no"]: r["application_total"] for r in read(os.path.join(
            REPO, "invoice-auditing-level-2", "civilwork", "invoices", "applications.csv"))}
        drill = {r["invoice_no"]: r["invoice_total"] for r in read(os.path.join(
            REPO, "invoice-auditing-level-2", "drilling_services", "invoices", "invoices.csv"))}
        raw = {**civil, **drill}
        for r in merged:
            a, b = raw[r["invoice_id"]].split(".")
            self.assertEqual(int(r["billed_total_cents"]), int(a) * 100 + int(b), r["invoice_id"])
            self.assertNotEqual(r["flagged"], "")


if __name__ == "__main__":
    unittest.main()
