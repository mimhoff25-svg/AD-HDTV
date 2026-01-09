# AD-HDTV Architecture

## Overview
AD-HDTV is a PyQt application that coordinates a grid of VLC-backed players plus optional browser-mode slots. The app is driven by a single Qt event loop, with time-based behavior handled via QTimer callbacks.

## Lifecycle (Entry Discipline)
1. `app.py` loads configuration and builds `AppState`.
2. Logging is configured once for the session.
3. `webgridplayer.main()` creates the Qt application instance.
4. `WebGridPlayer` initializes UI, loads persisted state, and builds the player grid.
5. The Qt event loop runs until shutdown.
6. `closeEvent` tears down VLC resources and background workers.

## App State
`AppState` captures runtime intent and is passed downward into the window:
- `current_channel`
- `resolution` and `display_mode`
- `debug` and `tick_rate_hz`
- `profile` (dev/demo/live)

Configuration lives in `config/app.json` and optional overrides in `config/profiles/*.json`.

## Channels
Channel data is persisted in `state/channels.json` (number, title, url). The UI reads and writes this file for channel tuning and labeling. A future plugin-style channel system lives under `channels/` and will follow a strict interface:

```
init(state)
update(state, dt)
render(context)
```

## Rendering and Timing
- VLC renders video frames directly into each player widget.
- Browser mode uses QtWebEngine when available.
- QTimer drives periodic tasks (health checks, token refresh, debug overlay).

## How a Frame Happens
1. VLC (or WebEngine) renders into the widget surface.
2. Qt schedules paint events and repaints the window.
3. Timers update state (refresh, monitoring) without blocking the UI.
4. UI state changes trigger light re-layout or label updates.

## Error Containment
Errors are logged via the structured logger. Player-level failures do not crash the app; recovery paths re-init VLC or fallback to browser mode when needed.

## Where to Extend
- Add config defaults in `config/app.json`.
- Add profile overrides in `config/profiles/`.
- Place new channel plugins in `channels/`.
- Use `WebGridPlayer` methods for UI wiring and grid management.
