#!/bin/bash

# Compatibility wrapper for the canonical launcher in scripts/.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/scripts/run_webgridplayer.sh" "$@"
