# AD-HDTV Roku MVP

This directory contains a simple Roku SceneGraph client that treats the AD-HDTV Python backend as its hub.

## What it does

- Connects to the AD-HDTV hub over HTTP
- Polls hub status for reliable now-playing updates
- Maps Roku remote keys to hub control endpoints
- Opens a lightweight guide view using the hub `/api/v1/guide` response
- Shows connection and authentication errors in-app

## Project layout

- `manifest` — Roku package metadata
- `source/` — app bootstrap and HTTP adapter
- `components/` — SceneGraph UI components

## Hub configuration

The Roku client expects the backend hub to expose:

- `GET /api/v1/status`
- `GET /api/v1/guide`
- `POST /api/v1/control/channel/next`
- `POST /api/v1/control/channel/prev`
- `POST /api/v1/control/channel/set`
- `POST /api/v1/control/select`
- `POST /api/v1/control/guide/show`
- `POST /api/v1/control/guide/hide`
- `POST /api/v1/control/audio/solo`
- `POST /api/v1/control/audio/mute`

If your hub requires auth, set a shared token in the app launch arguments or edit `source/app.brs` defaults for local testing.

## Packaging

Create a Roku channel package from this folder with the standard Roku developer workflow:

1. Copy this folder into a Roku app workspace.
2. Zip the contents of `clients/roku/`.
3. Sideload the package to a Roku device in developer mode.

This MVP uses polling instead of SSE because polling is more predictable on low-friction Roku deployments.
