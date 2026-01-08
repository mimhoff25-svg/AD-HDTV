#!/usr/bin/env python3
"""
Test the enhanced WebGridPlayer stream extraction and VLC options
"""

import vlc
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time

def test_vlc_with_hls_options():
    """Test VLC with enhanced HLS options."""
    print("🧪 Testing VLC with enhanced HLS streaming options")
    print("=" * 60)
    
    # Extract a fresh Fox7 Austin stream
    url = 'https://www.fox7austin.com/fox-7-web-cams'
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find wetmet.net iframe
        iframes = soup.find_all('iframe')
        hls_url = None
        
        for iframe in iframes:
            src = iframe.get('src')
            if src and 'wetmet.net' in src:
                print(f"📺 Found iframe: {src}")
                
                iframe_response = session.get(src, timeout=10)
                hls_matches = re.findall(r'https?://[^\s"\'<>]+\.m3u8(?:\?[^\s"\'<>]*)?', 
                                       iframe_response.text, re.IGNORECASE)
                
                if hls_matches:
                    hls_url = hls_matches[0]  # Take first one
                    print(f"📡 Found HLS stream: {hls_url}")
                    break
        
        if not hls_url:
            print("❌ No HLS stream found")
            return
        
        print(f"\n🎯 Testing HLS stream with enhanced VLC options:")
        print(f"   URL: {hls_url}")
        
        # Test with enhanced VLC options (like our webgridplayer improvements)
        vlc_args = [
            '--quiet',
            '--network-caching=1500',
            '--live-caching=1500',
            '--http-reconnect',
            '--adaptive-logic=highest',
            '--hls-fakeua',
        ]
        
        print(f"   VLC args: {vlc_args}")
        
        vlc_instance = vlc.Instance(vlc_args)
        media = vlc_instance.media_new(hls_url)
        
        # Add HLS-specific options
        media.add_option(':http-user-agent=Mozilla/5.0 (compatible; VLC)')
        media.add_option(':network-caching=1500')
        media.add_option(':live-caching=1500')
        media.add_option(':http-reconnect')
        
        # Parse media to get information
        media.parse()
        
        # Wait for parsing
        for i in range(10):  # Wait up to 10 seconds
            if media.get_parsed_status() != vlc.MediaParsedStatus.skipped:
                break
            time.sleep(1)
        
        print(f"   Media parse status: {media.get_parsed_status()}")
        print(f"   Media duration: {media.get_duration()}")
        print(f"   Media state: {media.get_state()}")
        
        # Get media info
        tracks = media.tracks_get()
        if tracks:
            print(f"   Found {len(tracks)} track(s):")
            for i, track in enumerate(tracks):
                print(f"      Track {i+1}: {track}")
        else:
            print("   No track information available")
        
        # Test accessibility with curl
        print(f"\n🌐 Testing stream accessibility with curl:")
        import subprocess
        result = subprocess.run([
            'curl', '-I', '--connect-timeout', '5', '--max-time', '10',
            '-H', 'User-Agent: VLC/3.0.0 LibVLC/3.0.0',
            hls_url
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            status_line = result.stdout.split('\n')[0] if result.stdout else 'No response'
            print(f"   ✅ Stream accessible: {status_line}")
            
            # Check if it's a valid HLS playlist
            result2 = subprocess.run([
                'curl', '--connect-timeout', '5', '--max-time', '10',
                '-H', 'User-Agent: VLC/3.0.0 LibVLC/3.0.0',
                hls_url
            ], capture_output=True, text=True)
            
            if result2.returncode == 0 and '#EXTM3U' in result2.stdout:
                print(f"   ✅ Valid HLS playlist format")
                lines = result2.stdout.strip().split('\n')
                print(f"   📄 Playlist info: {len(lines)} lines")
                for line in lines[:3]:
                    print(f"      {line}")
            else:
                print(f"   ⚠️  Response not a valid HLS playlist")
        else:
            print(f"   ❌ Stream not accessible: {result.stderr}")
        
        print(f"\n🎉 VLC HLS test completed!")
        print(f"\nℹ️  Summary:")
        print(f"   - Stream URL: {'✅ Found' if hls_url else '❌ Not found'}")
        print(f"   - VLC parsing: {'✅ Success' if media.get_parsed_status() != vlc.MediaParsedStatus.skipped else '⚠️  Limited'}")
        print(f"   - Network access: {'✅ Good' if result.returncode == 0 else '❌ Failed'}")
        print(f"   - HLS format: {'✅ Valid' if '#EXTM3U' in result2.stdout else '⚠️  Unknown'}")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    test_vlc_with_hls_options()