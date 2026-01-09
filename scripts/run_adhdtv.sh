#!/bin/bash

# AD-HDTV launcher alias.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/run_webgridplayer.sh" "$@"
