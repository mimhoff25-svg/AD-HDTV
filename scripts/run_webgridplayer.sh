#!/bin/bash

# WebGridPlayer Run Script
# Activates the virtual environment and launches the application

set -e

DIAG_ENV=0
if [ "$1" = "--diag-env" ]; then
    DIAG_ENV=1
    shift
fi

# Resolve project root (supports running from anywhere)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Auto-detect Chrome Remote Desktop display
if [ -z "$DISPLAY" ]; then
    # Check for Chrome Remote Desktop X server
    CRD_DISPLAY=$(ps aux | grep "Xorg :" | grep -v grep | sed -n 's/.*Xorg \(:[0-9]*\).*/\1/p' | head -1)
    if [ -n "$CRD_DISPLAY" ]; then
        export DISPLAY="$CRD_DISPLAY"
        export XAUTHORITY="$HOME/.Xauthority"
        echo "🖥️  Detected Chrome Remote Desktop display: $DISPLAY"
    else
        echo "⚠️  No DISPLAY variable set and no X server found"
        echo "   If using Chrome Remote Desktop, this should auto-detect"
        echo "   Try: export DISPLAY=:20"
        echo "   Or run: bash scripts/run_with_xvfb.sh"
    fi
fi

# Ensure XAUTHORITY is set if not already
if [ -z "$XAUTHORITY" ]; then
    export XAUTHORITY="$HOME/.Xauthority"
fi

# Fix GDbus warnings (if running in restricted environment)
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=/var/run/dbus/system_bus_socket"

# Prefer a local venv, then a workspace-level .venv, then gridplayer's venv.
if [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
    echo "✅ Using project virtual environment ($PROJECT_ROOT/venv)"
elif [ -d "$PROJECT_ROOT/../.venv" ]; then
    source "$PROJECT_ROOT/../.venv/bin/activate"
    echo "✅ Using workspace virtual environment ($PROJECT_ROOT/../.venv)"
elif [ -d "$PROJECT_ROOT/../gridplayer/venv" ]; then
    echo "📦 Using gridplayer virtual environment ($PROJECT_ROOT/../gridplayer/venv)..."
    source "$PROJECT_ROOT/../gridplayer/venv/bin/activate"
else
    echo "⚠️  No virtual environment found, using system Python"
fi

if [ "$DIAG_ENV" = "1" ]; then
    python - <<'PY'
import os
import sys
import importlib.util

print("sys.executable:", sys.executable)
print("VIRTUAL_ENV:", os.environ.get("VIRTUAL_ENV"))

try:
    import PyQt6  # noqa: F401
    print("PyQt6: OK")
except Exception as e:
    print("PyQt6: FAIL", repr(e))

spec6 = importlib.util.find_spec("PyQt6.QtWebEngineWidgets")
try:
    spec5 = importlib.util.find_spec("PyQt5.QtWebEngineWidgets")
except ModuleNotFoundError:
    spec5 = None
print("QtWebEngine spec (PyQt6):", bool(spec6))
print("QtWebEngine spec (PyQt5):", bool(spec5))

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
    print("QWebEngineView import (PyQt6): OK")
except Exception as e6:
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineView  # noqa: F401
        print("QWebEngineView import (PyQt5): OK")
    except Exception as e5:
        print("QWebEngineView import: FAIL")
        print("  PyQt6 error:", repr(e6))
        print("  PyQt5 error:", repr(e5))
PY
    exit 0
fi

# Check if webgridplayer.py exists
if [ ! -f "$PROJECT_ROOT/src/webgridplayer.py" ]; then
    echo "❌ src/webgridplayer.py not found in current directory."
    exit 1
fi

echo "🚀 Starting WebGridPlayer..."
python "$PROJECT_ROOT/src/webgridplayer.py"