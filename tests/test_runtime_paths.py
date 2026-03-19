#!/usr/bin/env python3

import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import webgridplayer


def test_runtime_paths_anchor_to_project_root():
    project_root = Path(__file__).resolve().parents[1]

    assert webgridplayer.PROJECT_ROOT == project_root
    assert webgridplayer.STATE_DIR == project_root / "state"
    assert webgridplayer.ASSETS_DIR == project_root / "assets"
    assert webgridplayer.LOGS_DIR == project_root / "logs"
