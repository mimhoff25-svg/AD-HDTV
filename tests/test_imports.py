#!/usr/bin/env python3
"""
Test that all imports work correctly
"""

import os
import sys

# Set headless Qt platform
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

print("Testing imports...")
print("=" * 60)

try:
    print("\n1. Testing PyQt6 imports...")
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QIcon
    print("   ✅ PyQt6 imports successful")
except ImportError as e:
    print(f"   ❌ PyQt6 import failed: {e}")
    sys.exit(1)

try:
    print("\n2. Testing VLC imports...")
    import vlc
    print("   ✅ VLC imports successful")
except ImportError as e:
    print(f"   ❌ VLC import failed: {e}")
    sys.exit(1)

try:
    print("\n3. Testing web scraping libraries...")
    from bs4 import BeautifulSoup
    import requests
    print("   ✅ Web scraping libraries successful")
except ImportError as e:
    print(f"   ❌ Web scraping import failed: {e}")
    sys.exit(1)

try:
    print("\n4. Testing webgridplayer module imports...")
    from webgridplayer import VideoPlayer, VideoStreamExtractor, WebGridPlayer
    print("   ✅ VideoPlayer imported")
    print("   ✅ VideoStreamExtractor imported")
    print("   ✅ WebGridPlayer imported")
except ImportError as e:
    print(f"   ❌ Webgridplayer import failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL IMPORTS SUCCESSFUL!")
print("=" * 60)
print("\nApplication is ready to run.")
