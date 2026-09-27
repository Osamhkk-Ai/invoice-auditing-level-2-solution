"""Run every verification check twice, confirm identical results, and run the hand-calculation tests.

Usage (from this folder):  python run_all.py
Writes out/results.json, out/flagged_invoices.csv, out/line_exceptions.csv.
"""
from __future__ import annotations

import hashlib
import json
import sys
import unittest

import check_01_integrity
import check_02_contract_rates
import check_03_evidence
import check_04_reprice
import check_05_state
import check_06_controls
import check_07_rate_diagnosis
from common import OUT_DIR

CHECKS = [check_01_integrity, check_02_contract_rates, check_03_evidence, check_04_reprice, check_05_state,
          check_06_controls, check_07_rate_diagnosis]


def run_once() -> tuple[dict, str]:
    results = {m.__name__: m.run() for m in CHECKS}
    blob = json.dumps(results, sort_keys=True, default=str, indent=1)
    return results, hashlib.sha256(blob.encode()).hexdigest()


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromName("test_hand_calcs")
    tests = unittest.TextTestRunner(verbosity=1).run(suite)
    r1, h1 = run_once()
    _, h2 = run_once()
    OUT_DIR.mkdir(exist_ok=True)
    r1["_meta"] = {"sha256_run1": h1, "sha256_run2": h2, "deterministic": h1 == h2,
                   "tests_run": tests.testsRun, "tests_failed": len(tests.failures) + len(tests.errors)}
    (OUT_DIR / "results.json").write_text(json.dumps(r1, sort_keys=True, default=str, indent=1), encoding="utf-8")
    print(json.dumps(r1["_meta"], indent=1))
    ok = h1 == h2 and tests.wasSuccessful() and not r1["check_02_contract_rates"]["boundary_failures"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
