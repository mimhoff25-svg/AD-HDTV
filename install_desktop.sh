#!/bin/bash

# Compatibility wrapper for the canonical installer in scripts/.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/scripts/install_desktop.sh" "$@"
