from __future__ import annotations

import ipaddress
import json
import os
import time
from datetime import UTC, datetime
from typing import Any, Dict, Iterable, Optional

from flask import Flask, Response, jsonify, request

from .guide_generator import generate_fake_guide
from .state import AudioState, Selected, State
from .state_manager import StateManager

API_PREFIX = "/api/v1"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5005


def _utc_now() -> datetime:
    return datetime.now(UTC)


def build_state_manager(
    *,
    version: str = "1.0",
    current_channel_id: int = 1,
    current_channel_name: str | None = None,
    playing: bool = True,
) -> StateManager:
    channel_name = current_channel_name or f"Channel {current_channel_id}"
    state = State(
        version=version,
        started_at=_utc_now(),
        current_channel_id=current_channel_id,
        current_channel_name=channel_name,
        selected=Selected(channel_id=current_channel_id),
        audio=AudioState(),
        playing=playing,
    )
    return StateManager(state)


def build_server_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    hub = dict((config or {}).get("hub", {}))

    env_overrides = {
        "host": os.environ.get("ADHDTV_HUB_HOST"),
        "port": os.environ.get("ADHDTV_HUB_PORT"),
        "auth_token": os.environ.get("ADHDTV_HUB_TOKEN"),
        "allowed_ips": os.environ.get("ADHDTV_HUB_ALLOWED_IPS"),
        "allow_origins": os.environ.get("ADHDTV_HUB_ALLOW_ORIGINS"),
    }
    for key, value in env_overrides.items():
        if value not in (None, ""):
            hub[key] = value

    allowed_ips = hub.get("allowed_ips", [])
    if isinstance(allowed_ips, str):
        allowed_ips = [
            entry.strip() for entry in allowed_ips.split(",") if entry.strip()
        ]

    allow_origins = hub.get("allow_origins", ["*"])
    if isinstance(allow_origins, str):
        allow_origins = [
            entry.strip() for entry in allow_origins.split(",") if entry.strip()
        ]

    auth_token = str(hub.get("auth_token", "")).strip()

    return {
        "enabled": bool(hub.get("enabled", True)),
        "host": str(hub.get("host", DEFAULT_HOST)),
        "port": int(hub.get("port", DEFAULT_PORT)),
        "auth_token": auth_token,
        "allowed_ips": allowed_ips,
        "allow_origins": allow_origins or [],
    }


def _manager_from_app(app: Flask) -> StateManager:
    return app.config["STATE_MANAGER"]


def _server_config_from_app(app: Flask) -> Dict[str, Any]:
    return app.config["SERVER_CONFIG"]


def _is_ip_allowed(remote_addr: str | None, allowed_ips: Iterable[str]) -> bool:
    entries = [entry for entry in allowed_ips if entry]
    if not entries:
        return True
    if not remote_addr:
        return False
    try:
        remote_ip = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False
    for entry in entries:
        try:
            if "/" in entry:
                if remote_ip in ipaddress.ip_network(entry, strict=False):
                    return True
            elif remote_ip == ipaddress.ip_address(entry):
                return True
        except ValueError:
            continue
    return False


def _resolve_allowed_origin(
    origin: str | None,
    allow_origins: Iterable[str],
) -> str | None:
    entries = [entry for entry in allow_origins if entry]
    if not entries:
        return None
    if "*" in entries:
        return "*" if origin is None else origin
    if origin and origin in entries:
        return origin
    return None


def _json_body() -> Dict[str, Any]:
    return request.get_json(silent=True) or {}


def _get_request_value(name: str, *, cast=None) -> Any:
    body = _json_body()
    value = request.args.get(name)
    if value is None:
        value = body.get(name)
    if value is None or cast is None:
        return value
    return cast(value)


def _state_response(app: Flask, status_code: int = 200):
    return jsonify(_manager_from_app(app).get_snapshot()), status_code


def create_app(
    *,
    state_mgr: StateManager | None = None,
    config: Optional[Dict[str, Any]] = None,
    include_legacy_aliases: bool = True,
) -> Flask:
    app = Flask(__name__)
    app.config["STATE_MANAGER"] = state_mgr or build_state_manager()
    app.config["SERVER_CONFIG"] = build_server_config(config)

    def add_route(
        rule: str,
        endpoint: str,
        view_func,
        methods: Iterable[str],
        *legacy_rules: str,
    ) -> None:
        method_list = sorted(set(methods) | {"OPTIONS"})
        app.add_url_rule(
            rule,
            endpoint=endpoint,
            view_func=view_func,
            methods=method_list,
        )
        if include_legacy_aliases:
            for index, legacy_rule in enumerate(legacy_rules):
                app.add_url_rule(
                    legacy_rule,
                    endpoint=f"{endpoint}_legacy_{index}",
                    view_func=view_func,
                    methods=method_list,
                )

    @app.before_request
    def enforce_network_policy():
        server_config = _server_config_from_app(app)
        if request.method == "OPTIONS":
            return ("", 204)
        if not _is_ip_allowed(request.remote_addr, server_config["allowed_ips"]):
            return jsonify({"error": "Client IP is not allowed"}), 403

        exempt_paths = {"/health"}
        if request.path in exempt_paths:
            return None

        token = server_config["auth_token"]
        if not token:
            return None

        provided = request.headers.get("X-ADHDTV-Token", "").strip()
        auth_header = request.headers.get("Authorization", "").strip()
        if auth_header.startswith("Bearer "):
            provided = auth_header[7:].strip()
        if provided != token:
            return jsonify({"error": "Unauthorized"}), 401
        return None

    @app.after_request
    def apply_cors(response):
        server_config = _server_config_from_app(app)
        allowed_origin = _resolve_allowed_origin(
            request.headers.get("Origin"),
            server_config["allow_origins"],
        )
        if allowed_origin:
            response.headers["Access-Control-Allow-Origin"] = allowed_origin
            response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type, X-ADHDTV-Token"
        )
        response.headers["Access-Control-Max-Age"] = "600"
        return response

    def api_index():
        server_config = _server_config_from_app(app)
        return jsonify(
            {
                "name": "AD-HDTV Hub API",
                "version": "1",
                "prefix": API_PREFIX,
                "events": f"{API_PREFIX}/events",
                "guide": f"{API_PREFIX}/guide",
                "status": f"{API_PREFIX}/status",
                "controls": {
                    "play": f"{API_PREFIX}/control/play",
                    "pause": f"{API_PREFIX}/control/pause",
                    "channel_next": f"{API_PREFIX}/control/channel/next",
                    "channel_prev": f"{API_PREFIX}/control/channel/prev",
                    "channel_set": f"{API_PREFIX}/control/channel/set",
                    "select": f"{API_PREFIX}/control/select",
                    "guide_show": f"{API_PREFIX}/control/guide/show",
                    "guide_hide": f"{API_PREFIX}/control/guide/hide",
                    "audio_solo": f"{API_PREFIX}/control/audio/solo",
                    "audio_mute": f"{API_PREFIX}/control/audio/mute",
                },
                "authentication": {
                    "required": bool(server_config["auth_token"]),
                    "header": "Authorization: Bearer <token> or X-ADHDTV-Token",
                },
            }
        )

    def health():
        server_config = _server_config_from_app(app)
        return jsonify(
            {
                "ok": True,
                "auth_required": bool(server_config["auth_token"]),
                "ip_filtering": bool(server_config["allowed_ips"]),
            }
        )

    def status():
        return _state_response(app)

    def events():
        manager = _manager_from_app(app)

        def event_stream():
            last_rev = manager.revision
            while True:
                time.sleep(0.5)
                rev = manager.revision
                if rev != last_rev:
                    data = json.dumps(manager.get_snapshot())
                    yield f"data: {data}\n\n"
                    last_rev = rev

        return Response(
            event_stream(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    def play():
        manager = _manager_from_app(app)

        def mut(state: State):
            state.playing = True

        manager.update(mut)
        return _state_response(app)

    def pause():
        manager = _manager_from_app(app)

        def mut(state: State):
            state.playing = False

        manager.update(mut)
        return _state_response(app)

    def channel_next():
        manager = _manager_from_app(app)

        def mut(state: State):
            state.current_channel_id = int(state.current_channel_id) + 1
            state.current_channel_name = f"Channel {state.current_channel_id}"
            state.selected.channel_id = state.current_channel_id

        manager.update(mut)
        return _state_response(app)

    def channel_prev():
        manager = _manager_from_app(app)

        def mut(state: State):
            state.current_channel_id = max(1, int(state.current_channel_id) - 1)
            state.current_channel_name = f"Channel {state.current_channel_id}"
            state.selected.channel_id = state.current_channel_id

        manager.update(mut)
        return _state_response(app)

    def channel_set():
        channel_id = _get_request_value("id")
        if channel_id is None:
            return jsonify({"error": "Missing id"}), 400

        manager = _manager_from_app(app)

        def mut(state: State):
            state.current_channel_id = channel_id
            state.current_channel_name = f"Channel {channel_id}"
            state.selected.channel_id = channel_id

        manager.update(mut)
        return _state_response(app)

    def select():
        row = _get_request_value("row")
        col = _get_request_value("col")
        channel_id = _get_request_value("channel_id")
        start_time_iso = _get_request_value("start_time_iso")
        if (
            row is None
            and col is None
            and channel_id is None
            and start_time_iso is None
        ):
            return jsonify({"error": "Missing selection values"}), 400

        manager = _manager_from_app(app)

        def mut(state: State):
            if row is not None:
                state.selected.row = int(row)
            if col is not None:
                state.selected.col = int(col)
            if channel_id is not None:
                state.selected.channel_id = channel_id
            if start_time_iso is not None:
                state.selected.start_time_iso = start_time_iso

        manager.update(mut)
        return _state_response(app)

    def guide_show():
        manager = _manager_from_app(app)

        def mut(state: State):
            state.guide_visible = True

        manager.update(mut)
        return _state_response(app)

    def guide_hide():
        manager = _manager_from_app(app)

        def mut(state: State):
            state.guide_visible = False

        manager.update(mut)
        return _state_response(app)

    def audio_solo():
        source_id = _get_request_value("id")
        if not source_id:
            return jsonify({"error": "Missing id"}), 400

        manager = _manager_from_app(app)

        def mut(state: State):
            state.audio.solo_source_id = source_id

        manager.update(mut)
        return _state_response(app)

    def audio_mute():
        raw_value = _get_request_value("value")
        if raw_value is None:
            return jsonify({"error": "Missing or invalid value"}), 400

        text_value = str(raw_value).lower()
        if text_value in {"1", "true", "yes", "on"}:
            muted = True
        elif text_value in {"0", "false", "no", "off"}:
            muted = False
        else:
            return jsonify({"error": "Missing or invalid value"}), 400

        manager = _manager_from_app(app)

        def mut(state: State):
            state.audio.muted = muted

        manager.update(mut)
        return _state_response(app)

    def guide():
        try:
            hours = int(_get_request_value("hours") or 2)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid hours"}), 400
        start = _get_request_value("start")
        if start:
            try:
                start_dt = datetime.fromisoformat(start)
            except ValueError:
                return jsonify({"error": "Invalid start"}), 400
        else:
            start_dt = None
        guide_data = generate_fake_guide(hours=hours, start=start_dt)
        return jsonify(guide_data.__dict__)

    add_route(API_PREFIX, "api_index", api_index, {"GET"})
    add_route("/health", "health", health, {"GET"})
    add_route(f"{API_PREFIX}/status", "status", status, {"GET"}, "/status")
    add_route(f"{API_PREFIX}/events", "events", events, {"GET"}, "/events")
    add_route(f"{API_PREFIX}/guide", "guide", guide, {"GET"}, "/guide")
    add_route(f"{API_PREFIX}/control/play", "play", play, {"POST"}, "/play")
    add_route(f"{API_PREFIX}/control/pause", "pause", pause, {"POST"}, "/pause")
    add_route(
        f"{API_PREFIX}/control/channel/next",
        "channel_next",
        channel_next,
        {"POST"},
        "/control/channel/next",
        "/channel_up",
    )
    add_route(
        f"{API_PREFIX}/control/channel/prev",
        "channel_prev",
        channel_prev,
        {"POST"},
        "/control/channel/prev",
        "/channel_down",
    )
    add_route(
        f"{API_PREFIX}/control/channel/set",
        "channel_set",
        channel_set,
        {"POST"},
        "/control/channel/set",
    )
    add_route(
        f"{API_PREFIX}/control/select",
        "select",
        select,
        {"POST"},
        "/control/select",
    )
    add_route(
        f"{API_PREFIX}/control/guide/show",
        "guide_show",
        guide_show,
        {"POST"},
        "/control/guide/show",
    )
    add_route(
        f"{API_PREFIX}/control/guide/hide",
        "guide_hide",
        guide_hide,
        {"POST"},
        "/control/guide/hide",
    )
    add_route(
        f"{API_PREFIX}/control/audio/solo",
        "audio_solo",
        audio_solo,
        {"POST"},
        "/control/audio/solo",
    )
    add_route(
        f"{API_PREFIX}/control/audio/mute",
        "audio_mute",
        audio_mute,
        {"POST"},
        "/control/audio/mute",
    )
    if include_legacy_aliases:
        add_route("/api_options", "api_options", api_index, {"GET"})
    return app


def run_api(
    state_mgr: StateManager,
    config: Optional[Dict[str, Any]] = None,
    *,
    include_legacy_aliases: bool = True,
) -> None:
    app = create_app(
        state_mgr=state_mgr,
        config=config,
        include_legacy_aliases=include_legacy_aliases,
    )
    server_config = _server_config_from_app(app)
    app.run(
        host=server_config["host"],
        port=server_config["port"],
        debug=False,
        threaded=True,
    )
