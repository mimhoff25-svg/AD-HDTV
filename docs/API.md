
# AD-HDTV Hub API Contract

This document describes the stable HTTP hub API used by thin clients such as Roku.


## Base URL

Preferred client-facing routes live under `/api/v1`.

Legacy aliases such as `/status`, `/channel_up`, `/channel_down`, and `/api_options` remain available for compatibility, but new clients should use the versioned paths below.

## Authentication and LAN policy

- Shared-token auth is optional and configured by the backend `hub.auth_token` setting or `ADHDTV_HUB_TOKEN`.
- Send the token with either `Authorization: Bearer <token>` or `X-ADHDTV-Token: <token>`.
- CORS headers are driven by `hub.allow_origins`.
- Optional IP filtering is driven by `hub.allowed_ips` and supports individual IPs or CIDR ranges.

## Discovery

- `GET /health` — Health check; does not require a token
- `GET /api/v1` — Capability and route discovery

## MVP endpoints

- `GET /api/v1/status` — Get current hub status
- `GET /api/v1/events` — Server-sent event stream for state changes
- `GET /api/v1/guide` — Get guide data
- `POST /api/v1/control/play` — Mark playback as active
- `POST /api/v1/control/pause` — Mark playback as paused
- `POST /api/v1/control/channel/next` — Increase channel number
- `POST /api/v1/control/channel/prev` — Decrease channel number
- `POST /api/v1/control/channel/set` — Set the current channel by `id`
- `POST /api/v1/control/select` — Update selected tile/guide coordinates
- `POST /api/v1/control/guide/show` — Mark guide as visible
- `POST /api/v1/control/guide/hide` — Mark guide as hidden
- `POST /api/v1/control/audio/solo` — Solo an audio source by `id`
- `POST /api/v1/control/audio/mute` — Set mute with `value`

Roku should use polling against `/api/v1/status` for the MVP and can later layer on `/api/v1/events` if needed.

---

## Example: /status

```json
{
	"version": "1.0",
	"started_at": "2026-01-27T18:00:00Z",
	"current_channel_id": 1,
	"current_channel_name": "Channel 1",
	"playing": true,
	"guide_visible": false,
	"selected": {
		"channel_id": 1,
		"row": 0,
		"col": 0,
		"start_time_iso": null
	},
	"audio": {
		"solo_source_id": null,
		"muted": false,
		"volume": 100
	},
	"last_updated_at": "2026-01-27T18:00:00Z",
	"revision": 42
}
```

## Example: /guide

```json
{
	"start_time_iso": "2026-01-27T18:00:00Z",
	"minutes_per_slot": 30,
	"slot_count": 4,
	"channels": [
		{"id": "ch1", "number": "101", "name": "Channel 1", "logo_key": "logo_1"},
		{"id": "ch2", "number": "102", "name": "Channel 2", "logo_key": "logo_2"}
	],
	"programs": [
		{"channel_id": "ch1", "title": "Show 1", "start_time_iso": "2026-01-27T18:00:00Z", "duration_minutes": 30},
		{"channel_id": "ch1", "title": "Show 2", "start_time_iso": "2026-01-27T18:30:00Z", "duration_minutes": 30}
	]
}
```

---

## Example control payloads

### `POST /api/v1/control/channel/set`

```json
{
  "id": 101
}
```

### `POST /api/v1/control/select`

```json
{
  "channel_id": "ch1",
  "row": 0,
  "col": 1,
  "start_time_iso": "2026-01-27T18:00:00"
}
```

### `POST /api/v1/control/audio/mute`

```json
{
  "value": true
}
```

See `src/adhdtv/api.py` for the latest implementation details.
