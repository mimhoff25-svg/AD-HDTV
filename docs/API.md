
# AD-HDTV API Contract

This document describes the HTTP API endpoints for remote control of AD-HDTV (ServerX backend).

## Endpoints


- `GET /status` — Returns JSON status/health of the backend (**Implemented**)
- `GET /events` — Server-sent events stream of state updates (**Prototype**)
- `POST /control/channel/next` — Switch to next channel (**Implemented**)
- `POST /control/channel/prev` — Switch to previous channel (**Implemented**)
- `POST /control/channel/set?id=N` — Set channel by ID (**Implemented**)
- `POST /control/select?row=X&col=Y` — Select a grid cell (**Implemented**)
- `POST /control/guide/show` — Show guide (**Implemented**)
- `POST /control/guide/hide` — Hide guide (**Implemented**)
- `POST /control/audio/solo?id=SOURCE` — Solo audio source (**Implemented, engine wiring TODO**)
- `POST /control/audio/mute?value=1|0` — Mute/unmute audio (**Implemented, engine wiring TODO**)
- `GET /guide?hours=2&start=<iso_optional>` — Returns a fake EPG grid (**Implemented**)

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
