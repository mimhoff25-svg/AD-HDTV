#!/usr/bin/env python3
"""
End-to-end test of WebGridPlayer workflow: Extract → Select → Load
"""

import os
import sys

# Set headless Qt platform for testing
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

def test_full_workflow():
    print("🎬 WebGridPlayer Full Workflow Test")
    print("=" * 60)
    
    try:
        # Import required components
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
        
        from PyQt6.QtWidgets import QApplication
        import vlc
        
        # Create Qt application
        app = QApplication([])
        
        # Import WebGridPlayer components
        from webgridplayer import VideoStreamExtractor, VideoPlayer
        
        print("✅ All imports successful")
        
        # Step 1: Extract streams from Fox7 Austin
        print("\n🔍 Step 1: Extracting streams from Fox7 Austin...")
        
        extractor = VideoStreamExtractor()
        url = 'https://www.fox7austin.com/fox-7-web-cams'
        streams = extractor.extract_streams(url)
        
        print(f"   Found {len(streams)} streams")
        hls_streams = [s for s in streams if s['type'] == 'iframe_hls']
        print(f"   HLS streams: {len(hls_streams)}")
        
        if not hls_streams:
            print("❌ No HLS streams found to test")
            return False
        
        # Step 2: Create player grid (2x2)
        print("\n🎮 Step 2: Creating player grid...")
        
        players = []
        for i in range(4):  # 2x2 grid
            player = VideoPlayer(player_id=i+1)
            players.append(player)
            print(f"   Player {i+1}: {'✅ Ready' if player.media_player else '❌ Failed'}")
        
        working_players = [p for p in players if p.media_player]
        print(f"   Working players: {len(working_players)}/4")
        
        # Step 3: Load streams into players
        print("\n📺 Step 3: Loading streams into players...")
        
        loaded_count = 0
        for i, stream in enumerate(hls_streams[:len(working_players)]):
            player = working_players[i]
            print(f"   Loading into Player {player.player_id}:")
            print(f"     Title: {stream['title']}")
            print(f"     URL: {stream['url'][:60]}...")
            print(f"     Type: {stream['type']}")
            
            # Simulate the same process as the dialog
            success = player.load_media(stream['url'], stream['title'])
            player.source_page = url  # Track source page for refresh
            
            if success:
                loaded_count += 1
                print(f"     Result: ✅ Success")
                print(f"     Status: {player.status_label.text()}")
                print(f"     Current URL set: {'Yes' if player.current_url else 'No'}")
            else:
                print(f"     Result: ❌ Failed")
        
        # Step 4: Verify player states
        print(f"\n🔍 Step 4: Verifying player states...")
        
        available_players = [p for p in working_players if not p.current_url]
        occupied_players = [p for p in working_players if p.current_url]
        
        print(f"   Total players: {len(working_players)}")
        print(f"   Occupied players: {len(occupied_players)}")
        print(f"   Available players: {len(available_players)}")
        
        for player in occupied_players:
            print(f"   Player {player.player_id}:")
            print(f"     URL: {player.current_url[:50]}...")
            print(f"     Status: {player.status_label.text()}")
            print(f"     Mode: {'Browser' if player.browser_mode else 'VLC'}")
        
        # Step 5: Test browser mode functionality
        print(f"\n🌐 Step 5: Testing browser mode...")
        
        if available_players:
            test_player = available_players[0]
            print(f"   Using Player {test_player.player_id} for browser test")
            
            # Switch to browser mode
            if hasattr(test_player, 'web_view') and test_player.web_view:
                test_player.browser_mode = True
                test_player.mode_stack.setCurrentIndex(1)
                test_player.load_url_in_browser(url)
                print(f"     Browser mode: ✅ Activated")
                print(f"     URL loaded: {test_player.current_url}")
            else:
                print(f"     Browser mode: ⚠️ WebEngine not available")
        else:
            print(f"   No available players for browser test")
        
        # Summary
        print(f"\n🎉 Workflow Test Results:")
        print(f"=" * 60)
        print(f"   Stream extraction: {'✅ Success' if streams else '❌ Failed'} ({len(streams)} found)")
        print(f"   Player creation: {'✅ Success' if working_players else '❌ Failed'} ({len(working_players)}/4)")
        print(f"   Stream loading: {'✅ Success' if loaded_count > 0 else '❌ Failed'} ({loaded_count} loaded)")
        print(f"   Player assignment: {'✅ Correct' if len(occupied_players) == loaded_count else '❌ Incorrect'}")
        
        success = streams and working_players and loaded_count > 0
        
        if success:
            print(f"\n✨ WebGridPlayer workflow is working correctly!")
            print(f"   Videos should now appear in the assigned player slots")
            print(f"   Stream extraction ↔ Player loading pipeline verified")
        else:
            print(f"\n❌ Workflow test failed - videos won't load in grid slots")
        
        # Cleanup
        app.quit()
        
        return success
        
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_full_workflow()
    sys.exit(0 if success else 1)