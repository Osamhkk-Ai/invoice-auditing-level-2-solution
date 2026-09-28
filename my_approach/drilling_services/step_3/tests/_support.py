"""Shared fixtures: one production run per test process (unittest discover imports every module
into the same interpreter), plus paths."""
from __future__ import annotations

import functools
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "src"))
OUTPUT = os.path.abspath(os.path.join(HERE, "..", "output"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from drilling_audit import loader  # noqa: E402
from drilling_audit.audit import run_audit  # noqa: E402
from drilling_audit.config import PRODUCTION  # noqa: E402
from drilling_audit.reports import load_reports  # noqa: E402

REPO = loader.REPO_ROOT
TRANSCRIPTION = os.path.join(REPO, "my_approach", "output_ocr", "drilling_services",
                             "drilling_services_contract_combined.md")


@functools.lru_cache(maxsize=None)
def inputs():
    return loader.load_inputs()


@functools.lru_cache(maxsize=None)
def reports():
    return load_reports(inputs().records_dir)


@functools.lru_cache(maxsize=None)
def audit(cfg=PRODUCTION):
    return run_audit(inputs(), reports(), cfg)
