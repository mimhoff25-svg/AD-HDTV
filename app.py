#!/usr/bin/env python3
"""AD-HDTV application entrypoint."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@dataclass
class AppState:
    app_name: str
    version: str
    profile: str
    debug: bool
    tick_rate_hz: int
    display_mode: str
    resolution: Tuple[int, int] | None
    current_channel: int | None
    started_at: float


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: Path, profile: str | None) -> Dict[str, Any]:
    base = _read_json(config_path)
    if profile:
        profile_path = config_path.parent / "profiles" / f"{profile}.json"
        profile_data = _read_json(profile_path)
        return _merge_dicts(base, profile_data)
    return base


def build_app_state(config: Dict[str, Any], profile: str) -> AppState:
    display = config.get("display", {})
    resolution = display.get("resolution")
    if isinstance(resolution, list) and len(resolution) == 2:
        resolution_value: Tuple[int, int] | None = (
            int(resolution[0]),
            int(resolution[1]),
        )
    else:
        resolution_value = None
    return AppState(
        app_name=config.get("app_name", "AD-HDTV"),
        version=config.get("version", "0.0.0"),
        profile=profile,
        debug=bool(config.get("debug", False)),
        tick_rate_hz=int(config.get("tick_rate_hz", 60)),
        display_mode=display.get("mode", "windowed"),
        resolution=resolution_value,
        current_channel=config.get("startup", {}).get("channel"),
        started_at=time.time(),
    )


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AD-HDTV launcher")
    parser.add_argument(
        "--profile",
        default=os.environ.get("ADHDTV_PROFILE", "dev"),
        help="Config profile to load (default: env ADHDTV_PROFILE or dev)",
    )
    parser.add_argument(
        "--config",
        default=os.environ.get("ADHDTV_CONFIG"),
        help="Path to base config JSON (default: config/app.json)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    launch_cwd = Path.cwd()
    if args.config:
        config_path = Path(args.config).expanduser()
        if not config_path.is_absolute():
            config_path = (launch_cwd / config_path).resolve()
    else:
        config_path = PROJECT_ROOT / "config" / "app.json"
    # Ensure state/log paths resolve relative to the project root (desktop launchers
    # often use $HOME as the working directory).
    os.chdir(PROJECT_ROOT)
    config = load_config(config_path, args.profile)
    app_state = build_app_state(config, args.profile)

    from adhdtv.api import build_state_manager, run_api
    from webgridplayer import main as app_main
    from webgridplayer import setup_logging

    # Start remote API server in background thread
    try:
        hub_config = config.get("hub", {})
        if hub_config.get("enabled", True):
            state_manager = build_state_manager(
                version=app_state.version,
                current_channel_id=app_state.current_channel or 1,
            )
            threading.Thread(
                target=run_api,
                kwargs={"state_mgr": state_manager, "config": config},
                daemon=True,
            ).start()
    except Exception as e:
        print(f"[WARN] Could not start remote API server: {e}")

    logger, _ = setup_logging(
        app_name=app_state.app_name,
        log_level=config.get("logging", {}).get("level", "INFO"),
    )

    logger.info("Lifecycle: init")
    logger.info("Lifecycle: config loaded (%s)", config_path)
    logger.info("Lifecycle: starting UI")

    exit_code = app_main(app_state=app_state, config=config)

    logger.info("Lifecycle: shutdown")
    return int(exit_code) if exit_code is not None else 0


if __name__ == "__main__":
    sys.exit(main())
