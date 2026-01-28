
# AD-HDTV API Contract

This document describes the HTTP API endpoints for remote control of AD-HDTV (ServerX backend).


## Endpoints

- `POST /play` — Start playback (**Implemented**)
- `POST /pause` — Pause playback (**Implemented**)
- `POST /channel_up` — Increase channel number (**Implemented**)
- `POST /channel_down` — Decrease channel number (**Implemented**)
- `GET /status` — Get current player status (**Implemented**)

Other endpoints are planned or in progress. See remote_api.py for current implementation.

---

## Example: /status

```json
{
	"version": "1.0",
	"started_at": "2026-01-27T18:00:00Z",
	"current_channel_id": 1,
	"current_channel_name": "Channel 1",
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

See backend code for latest implementation status.
