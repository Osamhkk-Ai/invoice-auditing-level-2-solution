"""Regenerate the civil, drilling, and combined submission files.

Run from any directory with: python path/to/generate_output.py
Only Python's standard library is required.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
CIVIL_STEP = ROOT / "my_approach" / "civilwork" / "step_3"
DRILL_STEP = ROOT / "my_approach" / "drilling_services" / "step_3"


def run(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    run(str(CIVIL_STEP / "src" / "run_civilwork_audit.py"))
    run(str(DRILL_STEP / "src" / "run_drilling_audit.py"))

    civil = OUTPUT / "civilwork_submission.csv"
    drilling = OUTPUT / "drilling_submission.csv"
    shutil.copyfile(CIVIL_STEP / "output" / "civilwork_submission_part.csv", civil)
    shutil.copyfile(DRILL_STEP / "output" / "drilling_submission_part.csv", drilling)

    combined = OUTPUT / "submission.csv"
    run(
        str(CIVIL_STEP / "src" / "merge_submission.py"),
        "--part", str(civil),
        "--part", str(drilling),
        "--out", str(combined),
    )
    # Keep the challenge's root-level artifact and existing tests in sync.
    shutil.copyfile(combined, ROOT / "submission.csv")
    print("Ready:")
    for path in (civil, drilling, combined):
        print(f"  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
