#!/usr/bin/env python3
"""
WebGridPlayer Diagnostics
Checks for common issues preventing the application from starting
"""

import sys
import os

def check_environment():
    """Check the runtime environment."""
    print("🔍 WebGridPlayer Diagnostics")
    print("=" * 50)
    
    # Check Python version
    print(f"\n✅ Python Version: {sys.version}")
    
    # Check DISPLAY variable
    display = os.environ.get('DISPLAY', None)
    if display:
        print(f"✅ DISPLAY: {display}")
    else:
        print("❌ DISPLAY: Not set (no X11 display available)")
        print("   → WebGridPlayer requires a graphical display")
        print("   → Run on a desktop system or use X11 forwarding")
    
    # Check if running in SSH
    ssh_client = os.environ.get('SSH_CLIENT', None)
    if ssh_client:
        print(f"⚠️  Running via SSH from: {ssh_client.split()[0]}")
        print("   → Consider using X11 forwarding: ssh -X user@host")
    
    # Check dependencies
    print("\n📦 Checking Dependencies:")
    
    # PyQt
    try:
        from PyQt6 import QtCore, QtWidgets
        print(f"✅ PyQt6: {QtCore.PYQT_VERSION_STR} (Qt {QtCore.QT_VERSION_STR})")
    except ImportError:
        try:
            from PyQt5 import QtCore, QtWidgets
            print(f"✅ PyQt5: {QtCore.PYQT_VERSION_STR} (Qt {QtCore.QT_VERSION_STR})")
        except ImportError:
            print("❌ PyQt: Not installed")
            return False
    
    # VLC
    try:
        import vlc
        print("✅ python-vlc: Installed")
        
        # Test VLC instance creation
        try:
            instance = vlc.Instance('--quiet')
            print("✅ VLC: Instance created successfully")
            del instance
        except Exception as e:
            print(f"⚠️  VLC: Instance creation warning: {e}")
    except ImportError:
        print("❌ python-vlc: Not installed")
        return False
    
    # Web libraries
    try:
        import requests
        print("✅ requests: Installed")
    except ImportError:
        print("❌ requests: Not installed")
        return False
    
    try:
        import bs4
        print("✅ beautifulsoup4: Installed")
    except ImportError:
        print("❌ beautifulsoup4: Not installed")
        return False
    
    # Test Qt Platform
    print("\n🖥️  Testing Qt Platform:")
    if not display:
        print("⚠️  No display available - Qt will fail to start")
        print("\nPossible Solutions:")
        print("1. Run on a desktop system with graphical environment")
        print("2. Use X11 forwarding: ssh -X user@host")
        print("3. Use VNC or remote desktop")
        print("4. Set up Xvfb (virtual framebuffer): Xvfb :99 -screen 0 1024x768x24")
        return False
    
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication([])
        print("✅ Qt Application: Can initialize")
        app.quit()
    except Exception as e:
        print(f"❌ Qt Application: Failed to initialize: {e}")
        return False
    
    print("\n🎉 All checks passed! WebGridPlayer should work.")
    return True

def suggest_solutions():
    """Suggest solutions based on environment."""
    print("\n" + "=" * 50)
    print("💡 Solutions for Running WebGridPlayer:")
    print("=" * 50)
    
    if not os.environ.get('DISPLAY'):
        print("\n📌 Running on Server/Headless System:")
        print("   Option 1: Use X11 Forwarding")
        print("   $ ssh -X user@host")
        print("   $ cd /home/mike/projects/webgridplayer")
        print("   $ ./run_webgridplayer.sh")
        print()
        print("   Option 2: Use VNC")
        print("   $ sudo apt install tigervnc-standalone-server")
        print("   $ vncserver :1")
        print("   $ DISPLAY=:1 ./run_webgridplayer.sh")
        print()
        print("   Option 3: Use Xvfb (Virtual Display)")
        print("   $ sudo apt install xvfb")
        print("   $ Xvfb :99 -screen 0 1920x1080x24 &")
        print("   $ DISPLAY=:99 ./run_webgridplayer.sh")
    else:
        print("\n📌 Display is available - try running:")
        print("   $ ./run_webgridplayer.sh")
        print()
        print("   If it still fails, check for:")
        print("   - Window manager running")
        print("   - Graphics drivers installed")
        print("   - Sufficient permissions")

if __name__ == "__main__":
    print()
    success = check_environment()
    suggest_solutions()
    print()
    
    sys.exit(0 if success else 1)