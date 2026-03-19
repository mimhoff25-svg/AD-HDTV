#!/usr/bin/env bash
# AD-HDTV launcher script

set -e

# Get the directory where this script resides
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Decide whether to run with a GUI or headless. Default to GUI when a display
# is available; fall back to offscreen only when explicitly requested or when
# no display is present (CI/servers).
MODE="gui"
if [[ -n "${ADHDTV_HEADLESS:-}" || ( -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ) ]]; then
  export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
  MODE="headless"
elif [[ "${QT_QPA_PLATFORM:-}" == "offscreen" ]]; then
  # Prevent inherited headless setting from hiding the window in desktop launches
  unset QT_QPA_PLATFORM
fi

echo "🚀 Starting AD-HDTV (${MODE} mode)..."
exec python3 app.py "$@"
