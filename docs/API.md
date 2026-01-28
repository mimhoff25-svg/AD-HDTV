# AD-HDTV API Contract (Planned)

This document describes the planned HTTP API endpoints for remote control of AD-HDTV (ServerX backend).

## Endpoints (Planned)

- `GET /status` — Returns JSON status/health of the backend
- `POST /control/channel/next` — Switch to next channel
- `POST /control/channel/prev` — Switch to previous channel
- `POST /control/channel/set?id=N` — Set channel by ID
- `POST /control/select?row=X&col=Y` — Select a grid cell

---

These endpoints are planned and may change as the API evolves. See backend code for implementation status.
