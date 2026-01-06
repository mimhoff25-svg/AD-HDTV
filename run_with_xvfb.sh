#!/bin/bash

# WebGridPlayer with Virtual Display
# Runs WebGridPlayer using Xvfb (virtual framebuffer)

echo "🖥️  Starting WebGridPlayer with Virtual Display"
echo "==============================================="

# Check if Xvfb is installed
if ! command -v Xvfb &> /dev/null; then
    echo "📦 Xvfb not found. Installing..."
    sudo apt update
    sudo apt install -y xvfb
fi

# Check if virtual environment exists, if not use system Python
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Using virtual environment"
else
    echo "⚠️  No virtual environment found, using system Python"
fi

# Start Xvfb on display :99
echo "🚀 Starting virtual display..."
Xvfb :99 -screen 0 1920x1080x24 &
XVFB_PID=$!
export DISPLAY=:99

# Give Xvfb time to start
sleep 2

echo "✅ Virtual display ready on :99"
echo "🎬 Launching WebGridPlayer..."
echo ""

# Run WebGridPlayer
python webgridplayer.py "$@"

# Cleanup
echo ""
echo "🛑 Stopping virtual display..."
kill $XVFB_PID 2>/dev/null

echo "✅ Done!"