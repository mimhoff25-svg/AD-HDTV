#!/bin/bash

# WebGridPlayer Desktop Integration Script
# Installs desktop file and creates application menu entry

set -e

echo "🖥️  Installing WebGridPlayer Desktop Integration"
echo "==============================================="

# Get the current directory (where WebGridPlayer is installed)
WEBGRIDPLAYER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_FILE="WebGridPlayer.desktop"
DESKTOP_FILE_PATH="$WEBGRIDPLAYER_DIR/$DESKTOP_FILE"

echo "📁 WebGridPlayer directory: $WEBGRIDPLAYER_DIR"

# Update desktop file paths to use actual installation directory
echo "🔧 Updating desktop file paths..."
sed -i "s|/home/mike/projects/webgridplayer|$WEBGRIDPLAYER_DIR|g" "$DESKTOP_FILE_PATH"

# Make the run script executable if it isn't already
chmod +x "$WEBGRIDPLAYER_DIR/run_webgridplayer.sh"

# Install desktop file to user applications
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

echo "📋 Installing desktop file to: $DESKTOP_DIR"
cp "$DESKTOP_FILE_PATH" "$DESKTOP_DIR/"

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    echo "🔄 Updating desktop database..."
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

# Make desktop file executable
chmod +x "$DESKTOP_DIR/$DESKTOP_FILE"

echo ""
echo "✅ Desktop integration installed successfully!"
echo ""
echo "WebGridPlayer should now appear in your application menu under:"
echo "  • Applications → Audio & Video → WebGridPlayer"
echo "  • Or search for 'WebGridPlayer' in your app launcher"
echo ""
echo "You can also:"
echo "  • Right-click video files and choose 'Open with WebGridPlayer'"
echo "  • Create a desktop shortcut by copying the .desktop file to ~/Desktop"
echo ""

# Optional: Install to desktop
read -p "📌 Would you like to create a desktop shortcut? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    DESKTOP_PATH="$HOME/Desktop"
    if [ -d "$DESKTOP_PATH" ]; then
        cp "$DESKTOP_FILE_PATH" "$DESKTOP_PATH/"
        chmod +x "$DESKTOP_PATH/$DESKTOP_FILE"
        echo "✅ Desktop shortcut created at: $DESKTOP_PATH/$DESKTOP_FILE"
    else
        echo "⚠️  Desktop directory not found: $DESKTOP_PATH"
    fi
fi

echo ""
echo "🎉 Installation complete! You can now launch WebGridPlayer from your application menu."