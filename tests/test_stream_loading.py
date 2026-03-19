#!/usr/bin/env python3
"""
Test stream loading functionality
"""

import os
import sys

# Set headless Qt platform for testing
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

def test_stream_loading():
    print("🧪 Testing WebGridPlayer Stream Loading")
    print("=" * 50)
    
    try:
        # Import required components
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
        
        from PyQt6.QtWidgets import QApplication
        import vlc
        
        # Create Qt application
        app = QApplication([])
        
        # Import WebGridPlayer components
        from webgridplayer import VideoPlayer
        
        print("✅ Imports successful")
        
        # Create a test video player
        player = VideoPlayer(player_id=1)
        print("✅ VideoPlayer created")
        
        # Test stream data (similar to what would come from extraction)
        test_stream = {
            'url': 'https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4',
            'title': 'Test Video Stream',
            'type': 'video/mp4'
        }
        
        print(f"\n🎯 Testing stream loading:")
        print(f"   Title: {test_stream['title']}")
        print(f"   URL: {test_stream['url']}")
        print(f"   Type: {test_stream['type']}")
        
        # Test loading media
        success = player.load_media(test_stream['url'], test_stream['title'])
        
        print(f"\n📊 Results:")
        print(f"   Media loading: {'✅ Success' if success else '❌ Failed'}")
        print(f"   Current URL set: {'✅ Yes' if player.current_url else '❌ No'}")
        print(f"   Media object created: {'✅ Yes' if player.media else '❌ No'}")
        print(f"   Player state: {player.status_label.text()}")
        
        # Test with HLS stream
        hls_stream = {
            'url': 'https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8',
            'title': 'Test HLS Stream',
            'type': 'application/x-mpegURL'
        }
        
        print(f"\n🎯 Testing HLS stream loading:")
        print(f"   Title: {hls_stream['title']}")
        print(f"   URL: {hls_stream['url']}")
        
        # Create second player for HLS test
        player2 = VideoPlayer(player_id=2)
        success2 = player2.load_media(hls_stream['url'], hls_stream['title'])
        
        print(f"\n📊 HLS Results:")
        print(f"   HLS loading: {'✅ Success' if success2 else '❌ Failed'}")
        print(f"   Current URL set: {'✅ Yes' if player2.current_url else '❌ No'}")
        print(f"   Media object created: {'✅ Yes' if player2.media else '❌ No'}")
        print(f"   Player state: {player2.status_label.text()}")
        
        # Test player availability detection
        print(f"\n🎮 Player Status:")
        print(f"   Player 1 current_url: {player.current_url[:50] if player.current_url else 'None'}")
        print(f"   Player 2 current_url: {player2.current_url[:50] if player2.current_url else 'None'}")
        print(f"   Player 1 available: {'❌ No' if player.current_url else '✅ Yes'}")
        print(f"   Player 2 available: {'❌ No' if player2.current_url else '✅ Yes'}")
        
        print(f"\n🎉 Stream loading test completed!")
        print(f"Summary: {2 if success and success2 else 1 if success or success2 else 0}/2 streams loaded successfully")
        
        # Cleanup
        app.quit()
        
        assert success and success2
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        assert False, str(e)

if __name__ == "__main__":
    success = test_stream_loading()
    sys.exit(0 if success else 1)