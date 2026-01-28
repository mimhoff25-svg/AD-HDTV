# AD-HDTV API Contract (Planned)

This document describes the planned HTTP API endpoints for remote control of AD-HDTV (ServerX backend).

## Endpoints

- `GET /status`
  - Returns: JSON status/health of the backend

- `POST /control/channel/next`
  - Action: Switch to next channel

- `POST /control/channel/prev`
  - Action: Switch to previous channel

- `POST /control/channel/set?id=N`
  - Params: `id` (channel number or ID)
  - Action: Set channel by ID

- `POST /control/select?row=X&col=Y`
  - Params: `row`, `col` (grid coordinates)
  - Action: Select a grid cell

---

These endpoints are subject to change as the API evolves. See the backend code for implementation status.
