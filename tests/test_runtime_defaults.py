#!/usr/bin/env python3

import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from webgridplayer import (
    DEFAULT_PREWARM_DELAY_MS,
    DEFAULT_PREWARM_LIMIT,
    _parse_optional_int_setting,
    _parse_prewarm_limit,
)


def test_parse_prewarm_limit_defaults_to_small_working_set():
    assert _parse_prewarm_limit(None) == DEFAULT_PREWARM_LIMIT
    assert _parse_prewarm_limit("") == DEFAULT_PREWARM_LIMIT
    assert _parse_prewarm_limit("6") == 6


def test_parse_prewarm_limit_supports_all_and_off():
    assert _parse_prewarm_limit("all") is None
    assert _parse_prewarm_limit("-1") is None
    assert _parse_prewarm_limit("off") == 0


def test_parse_optional_int_setting_falls_back_to_default():
    assert _parse_optional_int_setting(None, DEFAULT_PREWARM_DELAY_MS) == DEFAULT_PREWARM_DELAY_MS
    assert _parse_optional_int_setting("2500", DEFAULT_PREWARM_DELAY_MS) == 2500
    assert _parse_optional_int_setting("-1", DEFAULT_PREWARM_DELAY_MS) == DEFAULT_PREWARM_DELAY_MS
