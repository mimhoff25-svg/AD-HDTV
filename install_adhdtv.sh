#!/bin/bash

# AD-HDTV installer alias.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/scripts/install_webgridplayer.sh" "$@"
