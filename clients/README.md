# AD-HDTV Clients

This folder contains thin frontend clients for AD-HDTV. Each client connects to the AD-HDTV hub backend via HTTP API.

- `android/`: Android remote controller app (planned)
- `roku/`: Roku MVP client using the stable `/api/v1` hub contract

Clients are intentionally lightweight and should keep hub-specific integration details local to each client folder.
