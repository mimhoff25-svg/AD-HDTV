#!/bin/bash

# AD-HDTV Desktop Integration Script
# Installs desktop file and creates application menu entry

set -e

echo "🖥️  Installing AD-HDTV Desktop Integration"
echo "==============================================="

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_FILE="WebGridPlayer.desktop"
DESKTOP_FILE_PATH="$PROJECT_ROOT/$DESKTOP_FILE"

echo "📁 AD-HDTV directory: $PROJECT_ROOT"

# Update desktop file paths to use actual installation directory
echo "🔧 Updating desktop file paths..."
sed -i \
    -e "s|^Icon=.*|Icon=$PROJECT_ROOT/adhdtv.svg|g" \
    -e "s|^Path=.*|Path=$PROJECT_ROOT|g" \
    -e "s|^Exec=.*run_adhdtv.sh --add-url|Exec=$PROJECT_ROOT/run_adhdtv.sh --add-url|g" \
    -e "s|^Exec=.*run_adhdtv.sh --fetch-web|Exec=$PROJECT_ROOT/run_adhdtv.sh --fetch-web|g" \
    -e "s|^Exec=.*run_adhdtv.sh$|Exec=$PROJECT_ROOT/run_adhdtv.sh|g" \
    -e "s|^Exec=.*run_webgridplayer.sh --fetch-web|Exec=$PROJECT_ROOT/run_webgridplayer.sh --fetch-web|g" \
    "$DESKTOP_FILE_PATH"

# Make the run script executable if it isn't already
chmod +x "$PROJECT_ROOT/run_webgridplayer.sh"
if [ -f "$PROJECT_ROOT/run_adhdtv.sh" ]; then
    chmod +x "$PROJECT_ROOT/run_adhdtv.sh"
fi

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
echo "AD-HDTV should now appear in your application menu under:"
echo "  • Applications → Audio & Video → AD-HDTV"
echo "  • Or search for 'AD-HDTV' in your app launcher"
echo ""
echo "You can also:"
echo "  • Right-click video files and choose 'Open with AD-HDTV'"
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
echo "🎉 Installation complete! You can now launch AD-HDTV from your application menu."
