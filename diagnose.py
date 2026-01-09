#!/usr/bin/env python3
"""Compatibility wrapper for scripts/diagnose.py."""

from __future__ import annotations

import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "diagnose.py"

if not SCRIPT.exists():
    raise SystemExit("scripts/diagnose.py not found. Run from the project root.")

runpy.run_path(str(SCRIPT), run_name="__main__")
