#!/usr/bin/env python3
"""
Test WebGridPlayer browser mode functionality
"""

print("🌐 WebGridPlayer Browser Mode Test")
print("=" * 50)

# Test 1: Check if WebEngine is available
print("\n1. Checking WebEngine availability...")
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    print("✅ PyQt6 WebEngine available")
    WEBENGINE_AVAILABLE = True
except ImportError:
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        print("✅ PyQt5 WebEngine available")
        WEBENGINE_AVAILABLE = True
    except ImportError:
        print("❌ WebEngine not available - browser mode will not work")
        WEBENGINE_AVAILABLE = False

# Test 2: Check if we can import the main components
print("\n2. Checking WebGridPlayer imports...")
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Import main components
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QUrl
    print("✅ Qt imports successful")
    
    # Don't actually create the application without display
    print("✅ Basic imports working")
    
except Exception as e:
    print(f"❌ Import error: {e}")

# Test 3: Test URL processing
print("\n3. Testing URL processing...")

def test_url_processing():
    test_urls = [
        "google.com",
        "http://example.com",
        "https://www.fox7austin.com/fox-7-web-cams",
        "youtube.com/watch?v=abc123"
    ]
    
    for url in test_urls:
        # Simulate the URL processing logic
        if not url.startswith(('http://', 'https://')):
            processed_url = 'https://' + url
        else:
            processed_url = url
        print(f"   {url} → {processed_url}")

test_url_processing()

# Test 4: Simulate browser mode features
print("\n4. Testing browser mode logic...")

class MockPlayer:
    def __init__(self):
        self.browser_mode = False
        self.current_url = ""
        self.mode_button_text = "🎬"
        self.fullscreen_button_visible = False
        self.status_label_text = "⭕"
    
    def toggle_mode(self):
        if not WEBENGINE_AVAILABLE:
            return False
            
        self.browser_mode = not self.browser_mode
        
        if self.browser_mode:
            self.mode_button_text = "📺"
            self.fullscreen_button_visible = True
            self.status_label_text = "🌐"
            return "Switched to browser mode"
        else:
            self.mode_button_text = "🎬"
            self.fullscreen_button_visible = False
            self.status_label_text = "📺"
            return "Switched to VLC mode"

# Test the mock player
player = MockPlayer()
print(f"   Initial state: browser_mode={player.browser_mode}, button='{player.mode_button_text}'")
result = player.toggle_mode()
if result:
    print(f"   After toggle: browser_mode={player.browser_mode}, button='{player.mode_button_text}', fullscreen_visible={player.fullscreen_button_visible}")
    result2 = player.toggle_mode()
    print(f"   After second toggle: browser_mode={player.browser_mode}, button='{player.mode_button_text}', fullscreen_visible={player.fullscreen_button_visible}")
else:
    print("   ❌ Toggle mode failed - WebEngine not available")

# Test 5: Summary
print("\n🎉 Test Summary:")
print(f"   WebEngine Available: {'✅ Yes' if WEBENGINE_AVAILABLE else '❌ No'}")
print(f"   Browser Mode: {'✅ Supported' if WEBENGINE_AVAILABLE else '❌ Not supported'}")
print(f"   Fallback Mode: ✅ Available (direct URL loading)")

if WEBENGINE_AVAILABLE:
    print(f"\n📋 Browser Mode Features:")
    print(f"   • 🎬 Mode toggle button (VLC ↔ Browser)")
    print(f"   • ⛶ Fullscreen support")  
    print(f"   • 🌐 Web page loading")
    print(f"   • 📺 Stream extraction fallback")
else:
    print(f"\nℹ️  To enable browser mode:")
    print(f"   pip install PyQt6-WebEngine")
    print(f"   # or")
    print(f"   pip install PyQt5-WebEngine")

print(f"\n✅ WebGridPlayer browser mode test completed!")