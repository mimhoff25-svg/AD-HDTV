#!/bin/bash

# AD-HDTV Installation Script
# This script installs AD-HDTV and its dependencies

set -e  # Exit on any error

echo "🚀 AD-HDTV Installation Script"
echo "===================================="
echo "Version: 1.1.1b1"
echo "Repository: https://github.com/yourusername/adhdtv"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3.8+ and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Found Python $PYTHON_VERSION"

# Check if VLC is installed
if ! command -v vlc &> /dev/null; then
    echo "⚠️  VLC Media Player not found."
    echo "Installing VLC..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt &> /dev/null; then
            sudo apt update
            sudo apt install -y vlc libvlc-dev python3-vlc
        elif command -v yum &> /dev/null; then
            sudo yum install -y vlc vlc-devel
        elif command -v pacman &> /dev/null; then
            sudo pacman -S vlc
        else
            echo "❌ Unable to install VLC automatically. Please install VLC manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install vlc
        else
            echo "❌ Please install Homebrew or download VLC from https://www.videolan.org/vlc/"
            exit 1
        fi
    else
        echo "❌ Please install VLC manually from https://www.videolan.org/vlc/"
        exit 1
    fi
else
    echo "✅ VLC Media Player found"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Test installation
echo "🧪 Testing installation..."
python3 -c "
import sys
try:
    import PyQt6
    print('✅ PyQt6 imported successfully')
    qt_version = 6
except ImportError:
    try:
        import PyQt5
        print('✅ PyQt5 imported successfully')
        qt_version = 5
    except ImportError:
        print('❌ Neither PyQt6 nor PyQt5 could be imported')
        sys.exit(1)

try:
    import vlc
    print('✅ VLC Python bindings imported successfully')
except ImportError:
    print('❌ VLC Python bindings not available')
    sys.exit(1)

try:
    import requests, bs4
    print('✅ Web scraping libraries imported successfully')
except ImportError:
    print('❌ Web scraping libraries not available')
    sys.exit(1)

print('🎉 All dependencies installed successfully!')
print(f'Using PyQt{qt_version}')
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Installation completed successfully!"
    echo ""
    
    # Ask about desktop integration
    read -p "📌 Would you like to install desktop integration (application menu entry)? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🖥️  Installing desktop integration..."
        if [ -f "./install_desktop.sh" ]; then
            ./install_desktop.sh
        else
            echo "⚠️  Desktop installation script not found."
        fi
    fi
    
    echo ""
    echo "To run AD-HDTV:"
    echo "1. From application menu: Search for 'AD-HDTV'"
    echo "2. From command line: ./run_adhdtv.sh"
    echo "3. From virtual environment: source venv/bin/activate && python app.py"
    echo ""
else
    echo "❌ Installation failed. Please check the error messages above."
    exit 1
fi
