#!/usr/bin/env python3
"""
Test script for Fox7 Austin webcams
This script demonstrates how to extract and test the HLS streams
"""

import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import subprocess
import time

def extract_fox7_streams():
    """Extract streams from Fox7 Austin webcams page."""
    url = 'https://www.fox7austin.com/fox-7-web-cams'
    
    print(f"🔍 Extracting streams from: {url}")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        streams = []
        
        # Find wetmet.net iframes
        iframes = soup.find_all('iframe')
        print(f"📺 Found {len(iframes)} iframes")
        
        for i, iframe in enumerate(iframes, 1):
            src = iframe.get('src')
            if src and 'wetmet.net' in src:
                print(f"  Iframe {i}: {src}")
                
                try:
                    # Extract from iframe content
                    iframe_response = session.get(src, timeout=10)
                    iframe_response.raise_for_status()
                    
                    # Look for HLS streams in iframe
                    hls_matches = re.findall(r'https?://[^\s"\'<>]+\.m3u8(?:\?[^\s"\'<>]*)?', 
                                           iframe_response.text, re.IGNORECASE)
                    
                    for j, hls_url in enumerate(hls_matches, 1):
                        stream_info = {
                            'title': f'Fox7 Austin Webcam {i}-{j}',
                            'url': hls_url,
                            'type': 'hls',
                            'iframe_src': src
                        }
                        streams.append(stream_info)
                        print(f"    📡 Found HLS stream: {hls_url}")
                        
                except Exception as e:
                    print(f"    ❌ Error extracting from iframe: {e}")
        
        return streams
        
    except Exception as e:
        print(f"❌ Error extracting streams: {e}")
        return []

def test_stream_with_vlc(stream_url, title):
    """Test a stream with VLC to see if it works."""
    print(f"\n🧪 Testing stream: {title}")
    print(f"   URL: {stream_url}")
    
    try:
        # Test with curl first to check accessibility
        result = subprocess.run([
            'curl', '-I', '--connect-timeout', '5', '--max-time', '10',
            '-H', 'User-Agent: VLC/3.0.0 LibVLC/3.0.0',
            '-H', 'Referer: https://www.fox7austin.com/',
            stream_url
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("   ✅ Stream is accessible via curl")
            print(f"   Response: {result.stdout.splitlines()[0] if result.stdout.splitlines() else 'No response'}")
            
            # Try to get the actual m3u8 content
            result2 = subprocess.run([
                'curl', '--connect-timeout', '5', '--max-time', '10',
                '-H', 'User-Agent: VLC/3.0.0 LibVLC/3.0.0',
                '-H', 'Referer: https://www.fox7austin.com/',
                stream_url
            ], capture_output=True, text=True)
            
            if result2.returncode == 0 and result2.stdout:
                lines = result2.stdout.strip().split('\n')
                print(f"   📄 M3U8 content preview ({len(lines)} lines):")
                for line in lines[:5]:  # Show first 5 lines
                    print(f"      {line}")
                if len(lines) > 5:
                    print(f"      ... and {len(lines) - 5} more lines")
            
            return True
        else:
            print(f"   ❌ Stream not accessible: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing stream: {e}")
        return False

def main():
    print("🎥 Fox7 Austin Webcam Stream Test")
    print("=" * 50)
    
    streams = extract_fox7_streams()
    
    if not streams:
        print("❌ No streams found!")
        return
    
    print(f"\n✅ Found {len(streams)} streams")
    
    # Test each stream
    working_streams = []
    for stream in streams:
        if test_stream_with_vlc(stream['url'], stream['title']):
            working_streams.append(stream)
    
    print(f"\n📊 Summary:")
    print(f"   Total streams found: {len(streams)}")
    print(f"   Working streams: {len(working_streams)}")
    
    if working_streams:
        print(f"\n🎯 Working streams for WebGridPlayer:")
        for i, stream in enumerate(working_streams, 1):
            print(f"   {i}. {stream['title']}")
            print(f"      URL: {stream['url']}")
            print(f"      Type: {stream['type']}")
    else:
        print("\n⚠️  No working streams found. This could be due to:")
        print("   - Authentication token expiry")
        print("   - Network restrictions")
        print("   - Server-side blocking")

if __name__ == "__main__":
    main()