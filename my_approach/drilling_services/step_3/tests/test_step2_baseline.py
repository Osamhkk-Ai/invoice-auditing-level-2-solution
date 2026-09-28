"""Production against the Step 2 verification prototype, field by field (independent evidence kept in
``step_2_audit_system_design/verification``), and against the committed Step 2 outputs."""
import csv
import os
import unittest
from decimal import Decimal as D

from _support import REPO, SRC, audit

import sys
sys.path.insert(0, SRC)
import compare_with_step2  # noqa: E402

STEP2_OUT = os.path.join(REPO, "my_approach", "drilling_services", "step_2_audit_system_design", "verification", "out")


class Step2Prototype(unittest.TestCase):
    def test_field_by_field_identical(self):
        res = compare_with_step2.compare(audit(), compare_with_step2.run_step2())
        self.assertEqual(res["differences"], {k: 0 for k in res["differences"]})
        self.assertTrue(res["a3_identical"])
        self.assertEqual((res["lines_compared"], res["invoices_compared"]), (91181, 1906))

    def test_committed_step2_outputs(self):
        with open(os.path.join(STEP2_OUT, "flagged_invoices.csv"), encoding="utf-8") as f:
            flagged = {r["invoice_no"]: D(r["expected_total"]) for r in csv.DictReader(f)}
        with open(os.path.join(STEP2_OUT, "line_exceptions.csv"), encoding="utf-8") as f:
            lines = {r["line_ref"]: D(r["exp_amount"]) for r in csv.DictReader(f)}
        res = audit()
        self.assertEqual(sorted(flagged), sorted(n for n, i in res.invoices.items() if i.flagged))
        self.assertEqual({n: res.invoices[n].expected_total for n in flagged}, flagged)
        self.assertEqual(len(lines), 134)
        self.assertEqual({k: res.lines[k].expected_amount for k in lines}, lines)


if __name__ == "__main__":
    unittest.main()
