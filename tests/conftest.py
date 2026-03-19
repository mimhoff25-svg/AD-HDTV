"""Pytest configuration for AD-HDTV.

Manual and interactive scripts are excluded from automated collection.
"""

from __future__ import annotations

from typing import Set


MANUAL_TESTS: Set[str] = {
    "test_manual_check.py",
    "test_visual.py",
    "test_startup_grid.py",
    "test_stream_extraction.py",
    "test_stream_extraction_root.py",
    "test_url_extraction_root.py",
    "test_browser_mode_root.py",
    "test_fox7_streams_root.py",
    "test_vlc_hls_options_root.py",
    "test_webgridplayer_extraction_root.py",
}


def pytest_ignore_collect(collection_path, config):
    name = getattr(collection_path, "name", "")
    return name in MANUAL_TESTS
