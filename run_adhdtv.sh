#!/bin/bash

# AD-HDTV launcher alias (wrapper around scripts/run_webgridplayer.sh).
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/scripts/run_adhdtv.sh" "$@"
