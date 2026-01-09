#!/bin/bash

# AD-HDTV with Virtual Display
# Runs AD-HDTV using Xvfb (virtual framebuffer)

echo "🖥️  Starting AD-HDTV with Virtual Display"
echo "==============================================="

# Check if Xvfb is installed
if ! command -v Xvfb &> /dev/null; then
    echo "📦 Xvfb not found. Installing..."
    sudo apt update
    sudo apt install -y xvfb
fi

# Check if virtual environment exists, if not use system Python
# Resolve project root (supports running from anywhere)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Prefer a local venv, then a workspace-level .venv, then system Python.
if [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
    echo "✅ Using project virtual environment ($PROJECT_ROOT/venv)"
elif [ -d "$PROJECT_ROOT/../.venv" ]; then
    source "$PROJECT_ROOT/../.venv/bin/activate"
    echo "✅ Using workspace virtual environment ($PROJECT_ROOT/../.venv)"
else
    echo "⚠️  No virtual environment found, using system Python"
fi

# Start Xvfb on display :99
echo "🚀 Starting virtual display..."
Xvfb :99 -screen 0 1920x1080x24 &
XVFB_PID=$!
export DISPLAY=:99
export XAUTHORITY="$HOME/.Xauthority"
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=/var/run/dbus/system_bus_socket"

# Give Xvfb time to start
sleep 2

echo "✅ Virtual display ready on :99"
echo "🎬 Launching AD-HDTV..."
echo ""

# Run AD-HDTV
if [ -f "$PROJECT_ROOT/app.py" ]; then
    python "$PROJECT_ROOT/app.py" "$@"
else
    python "$PROJECT_ROOT/src/webgridplayer.py" "$@"
fi

# Cleanup
echo ""
echo "🛑 Stopping virtual display..."
kill $XVFB_PID 2>/dev/null

echo "✅ Done!"
