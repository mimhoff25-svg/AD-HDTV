"""Compatibility wrapper around the consolidated AD-HDTV hub API."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adhdtv.api import build_state_manager, create_app, run_api as _run_api


app = create_app(state_mgr=build_state_manager(), include_legacy_aliases=True)


def run_api(config=None):
    _run_api(build_state_manager(), config=config, include_legacy_aliases=True)


if __name__ == '__main__':
    run_api()
