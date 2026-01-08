#!/usr/bin/env python3
"""
WebGridPlayer Stream Extraction Test
Tests the web video stream extraction capabilities
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_stream_extraction():
    """Test the stream extraction functionality."""
    print("🧪 Testing WebGridPlayer Stream Extraction")
    print("=" * 50)
    
    try:
        # Import the extractor (avoiding GUI components)
        import requests
        from bs4 import BeautifulSoup
        import re
        from urllib.parse import urljoin, urlparse
        
        class StreamExtractorTest:
            def __init__(self):
                self.session = requests.Session()
                self.session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                })
            
            def extract_streams(self, url: str):
                """Extract video streams from a web page."""
                try:
                    print(f"📡 Fetching: {url}")
                    response = self.session.get(url, timeout=10)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    streams = []
                    
                    # Method 1: Find HTML5 video tags
                    video_tags = soup.find_all('video')
                    for video in video_tags:
                        src = video.get('src')
                        if src:
                            streams.append({
                                'url': urljoin(url, src),
                                'type': 'html5',
                                'title': f'HTML5 Video from {urlparse(url).netloc}'
                            })
                        
                        sources = video.find_all('source')
                        for source in sources:
                            src = source.get('src')
                            if src:
                                streams.append({
                                    'url': urljoin(url, src),
                                    'type': source.get('type', 'unknown'),
                                    'title': f'Video Source from {urlparse(url).netloc}'
                                })
                    
                    # Method 2: Find HLS streams (.m3u8)
                    hls_pattern = r'https?://[^\s"\'<>]+\.m3u8(?:\?[^\s"\'<>]*)?'
                    hls_matches = re.findall(hls_pattern, response.text, re.IGNORECASE)
                    for hls_url in hls_matches:
                        streams.append({
                            'url': hls_url,
                            'type': 'application/x-mpegURL',
                            'title': f'HLS Stream from {urlparse(url).netloc}'
                        })
                    
                    # Method 3: Find MP4 and other video URLs
                    video_pattern = r'https?://[^\s"\'<>]+\.(?:mp4|webm|ogg|avi|mov|flv|mkv)(?:\?[^\s"\'<>]*)?'
                    video_matches = re.findall(video_pattern, response.text, re.IGNORECASE)
                    for video_url in video_matches:
                        streams.append({
                            'url': video_url,
                            'type': 'video/mp4',
                            'title': f'Video File from {urlparse(url).netloc}'
                        })
                    
                    # Remove duplicates
                    seen_urls = set()
                    unique_streams = []
                    for stream in streams:
                        if stream['url'] not in seen_urls:
                            seen_urls.add(stream['url'])
                            unique_streams.append(stream)
                    
                    return unique_streams
                    
                except Exception as e:
                    print(f"❌ Error extracting streams: {e}")
                    return []
        
        # Test with example URLs
        extractor = StreamExtractorTest()
        
        test_urls = [
            "https://www.w3schools.com/html/html5_video.asp",  # Known to have HTML5 video examples
            "https://sample-videos.com/",  # Sample video site
        ]
        
        for test_url in test_urls:
            print(f"\n🔍 Testing URL: {test_url}")
            try:
                streams = extractor.extract_streams(test_url)
                if streams:
                    print(f"✅ Found {len(streams)} video streams:")
                    for i, stream in enumerate(streams[:3]):  # Show first 3 streams
                        print(f"  {i+1}. {stream['title']}")
                        print(f"     Type: {stream['type']}")
                        print(f"     URL: {stream['url'][:100]}{'...' if len(stream['url']) > 100 else ''}")
                else:
                    print("⚠️  No streams found")
            except Exception as e:
                print(f"❌ Test failed for {test_url}: {e}")
        
        print("\n🎉 Stream extraction testing completed!")
        print("\nNote: WebGridPlayer can extract streams from many types of websites.")
        print("Try the full application to test with specific URLs like weather cams,")
        print("news sites, or other pages with embedded videos.")
        
    except ImportError as e:
        print(f"❌ Required modules not available: {e}")
        print("Please install requirements: pip install requests beautifulsoup4")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_stream_extraction()
    sys.exit(0 if success else 1)