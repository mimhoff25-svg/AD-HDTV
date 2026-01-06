#!/bin/bash

# WebGridPlayer Run Script
# Activates the virtual environment and launches the application

set -e

# Auto-detect Chrome Remote Desktop display
if [ -z "$DISPLAY" ]; then
    # Check for Chrome Remote Desktop X server
    CRD_DISPLAY=$(ps aux | grep "Xorg :" | grep -v grep | sed -n 's/.*Xorg \(:[0-9]*\).*/\1/p' | head -1)
    if [ -n "$CRD_DISPLAY" ]; then
        export DISPLAY="$CRD_DISPLAY"
        echo "🖥️  Detected Chrome Remote Desktop display: $DISPLAY"
    else
        echo "⚠️  No DISPLAY variable set and no X server found"
        echo "   If using Chrome Remote Desktop, this should auto-detect"
        echo "   Try: export DISPLAY=:20"
    fi
fi

# Use gridplayer venv if webgridplayer venv doesn't exist
if [ ! -d "venv" ] && [ -d "../gridplayer/venv" ]; then
    echo "📦 Using gridplayer virtual environment..."
    source ../gridplayer/venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Using virtual environment"
else
    echo "⚠️  No virtual environment found, using system Python"
fi

# Check if webgridplayer.py exists
if [ ! -f "webgridplayer.py" ]; then
    echo "❌ webgridplayer.py not found in current directory."
    exit 1
fi

echo "🚀 Starting WebGridPlayer..."
python webgridplayer.py