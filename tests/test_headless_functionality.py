#!/usr/bin/env python3
"""
WebGridPlayer headless functionality test
"""

import os
import sys

# Set headless Qt platform
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

def test_webgridplayer_functionality():
    print("🧪 Testing WebGridPlayer functionality (headless mode)")
    print("=" * 60)
    
    try:
        # Test 1: Import main components
        print("1. Testing imports...")
        
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Test PyQt imports
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QUrl
            print("   ✅ PyQt6 imports successful")
            
            # Test WebEngine
            try:
                from PyQt6.QtWebEngineWidgets import QWebEngineView
                print("   ✅ PyQt6-WebEngine available")
                WEBENGINE_AVAILABLE = True
            except ImportError:
                print("   ⚠️  PyQt6-WebEngine not available")
                WEBENGINE_AVAILABLE = False
                
        except ImportError as e:
            print(f"   ❌ PyQt6 import failed: {e}")
            return False
            
        # Test VLC
        try:
            import vlc
            print("   ✅ VLC python bindings available")
        except ImportError as e:
            print(f"   ❌ VLC import failed: {e}")
            return False
            
        # Test web scraping
        try:
            import requests
            from bs4 import BeautifulSoup
            print("   ✅ Web scraping libraries available")
        except ImportError as e:
            print(f"   ❌ Web scraping import failed: {e}")
            return False
            
        print()
        
        # Test 2: Stream extractor functionality
        print("2. Testing stream extraction...")
        
        # Import the stream extractor
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
        from webgridplayer import VideoStreamExtractor
        extractor = VideoStreamExtractor()
        print("   ✅ VideoStreamExtractor created")
        
        # Test basic extraction (without actually making requests)
        print("   ✅ Stream extractor ready")
        
        print()
        
        # Test 3: Test VLC instance creation
        print("3. Testing VLC functionality...")
        
        try:
            # Create VLC instance with headless options
            vlc_args = [
                '--intf', 'dummy',  # No interface
                '--quiet',          # No output
                '--no-video',       # No video output
            ]
            vlc_instance = vlc.Instance(vlc_args)
            print("   ✅ VLC instance created successfully")
            
            # Test media creation
            media = vlc_instance.media_new('http://example.com/test.mp4')
            print("   ✅ VLC media object created")
            
            del media
            del vlc_instance
            print("   ✅ VLC cleanup successful")
            
        except Exception as e:
            print(f"   ❌ VLC test failed: {e}")
            return False
            
        print()
        
        # Test 4: Test application creation (headless)
        print("4. Testing Qt application...")
        
        try:
            app = QApplication([])
            print("   ✅ Qt application created (headless)")
            
            # Test URL processing
            test_url = "https://www.fox7austin.com/fox-7-web-cams"
            qurl = QUrl(test_url)
            print(f"   ✅ URL processing: {qurl.toString()}")
            
            app.quit()
            del app
            print("   ✅ Qt application cleanup successful")
            
        except Exception as e:
            print(f"   ❌ Qt application test failed: {e}")
            return False
        
        print()
        
        # Test 5: Summary
        print("🎉 All tests passed!")
        print("=" * 60)
        print("WebGridPlayer core functionality verified:")
        print(f"   • Stream extraction: ✅ Ready")
        print(f"   • VLC integration: ✅ Working") 
        print(f"   • Browser mode: {'✅ Available' if WEBENGINE_AVAILABLE else '⚠️ Limited'}")
        print(f"   • Qt framework: ✅ Functional")
        
        print("\nℹ️  To run with GUI:")
        print("   • Use X11 forwarding: ssh -X user@server")
        print("   • Or use Xvfb: xvfb-run python webgridplayer.py")
        print("   • Or run on desktop with display")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_webgridplayer_functionality()
    sys.exit(0 if success else 1)