#!/usr/bin/env python3
"""
Test WebGridPlayer stream extraction without GUI
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the extractor from webgridplayer
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse

class StreamExtractor:
    """Extract streams like WebGridPlayer does"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _extract_thetvapp_stream(self, soup, url):
        """Extract TheTVApp tokenized stream (from webgridplayer.py)"""
        streams = []
        
        # Look for "token" parameter in scripts
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'token' in script.string.lower():
                # Extract token value
                token_match = re.search(r'["\']token["\']\s*:\s*["\']([^"\']+)["\']', script.string)
                if token_match:
                    token = token_match.group(1)
                    
                    # Look for stream URL pattern with token
                    stream_pattern = r'["\']([^"\']+\.m3u8[^"\']*)["\']'
                    stream_matches = re.findall(stream_pattern, script.string)
                    
                    for stream_url in stream_matches:
                        if 'token=' in stream_url or token in stream_url:
                            streams.append({
                                'url': stream_url,
                                'type': 'thetvapp_token',
                                'title': f'TheTVApp Token Stream from {urlparse(url).netloc}'
                            })
        
        return streams
    
    def extract_streams(self, url: str):
        """Extract video streams from a web page (simplified version of webgridplayer)."""
        try:
            print(f"\n=== Extracting from: {url} ===")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            streams = []
            
            # Method 0: TheTVApp tokenized stream (jwplayer setup)
            thetvapp_streams = self._extract_thetvapp_stream(soup, url)
            streams.extend(thetvapp_streams)
            if thetvapp_streams:
                print(f"Found {len(thetvapp_streams)} TheTVApp token streams")
            
            # Method 1: Find iframes with video sources
            iframes = soup.find_all('iframe')
            print(f"Found {len(iframes)} iframes")
            for idx, iframe in enumerate(iframes, 1):
                src = iframe.get('src') or iframe.get('data-src') or iframe.get('data-lazy-src')
                if src:
                    abs_src = urljoin(url, src)
                    print(f"  Iframe #{idx}: {abs_src}")
                    
                    # Skip non-video iframes (like Google Tag Manager)
                    if any(skip in abs_src.lower() for skip in ['googletagmanager', 'google-analytics', 'facebook', 'twitter']):
                        print(f"    Skipping non-video iframe")
                        continue
                    
                    # Add iframe URL
                    streams.append({
                        'url': abs_src,
                        'type': 'iframe',
                        'title': f'📺 Iframe #{idx}: {urlparse(abs_src).netloc}'
                    })
                    
                    # Try to extract from iframe content
                    try:
                        self.session.headers['Referer'] = url
                        iframe_response = self.session.get(abs_src, timeout=5)
                        iframe_soup = BeautifulSoup(iframe_response.content, 'html.parser')
                        
                        # Look for .m3u8 in iframe
                        iframe_m3u8 = re.findall(r'https?://[^\s"\'<>]+\.m3u8(?:\?[^\s"\'<>]*)?', 
                                                iframe_response.text, re.IGNORECASE)
                        for m3u8_url in iframe_m3u8:
                            # Remove duplicates
                            if m3u8_url not in [s['url'] for s in streams]:
                                streams.append({
                                    'url': m3u8_url,
                                    'type': 'iframe_hls',
                                    'title': f'📡 HLS from Iframe #{idx}: {urlparse(abs_src).netloc}'
                                })
                                print(f"    Found HLS in iframe: {m3u8_url}")
                                
                        # Look for videos in iframe
                        iframe_videos = iframe_soup.find_all('video')
                        for v_idx, video in enumerate(iframe_videos, 1):
                            v_src = video.get('src') or video.get('data-src')
                            if v_src and not v_src.startswith('blob:'):
                                video_url = urljoin(abs_src, v_src)
                                if video_url not in [s['url'] for s in streams]:
                                    streams.append({
                                        'url': video_url,
                                        'type': 'iframe_video',
                                        'title': f'🎥 Video from Iframe #{idx}'
                                    })
                                    print(f"    Found video in iframe: {v_src}")
                                    
                    except Exception as e:
                        print(f"    Could not extract from iframe: {e}")
            
            # Method 2: Direct video tags
            video_tags = soup.find_all('video')
            print(f"Found {len(video_tags)} video tags")
            for idx, video in enumerate(video_tags, 1):
                src = video.get('src') or video.get('data-src') or video.get('data-video-src')
                if src and not src.startswith('blob:'):
                    video_url = urljoin(url, src)
                    if video_url not in [s['url'] for s in streams]:
                        streams.append({
                            'url': video_url,
                            'type': 'html5',
                            'title': f'🎥 HTML5 Video #{idx}'
                        })
                        print(f"  Found video: {src}")
            
            # Method 3: Look for HLS streams in scripts
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string:
                    # Find .m3u8 URLs in JavaScript
                    hls_pattern = r'https?://[^\s"\'<>]+\.m3u8(?:\?[^\s"\'<>]*)?'
                    script_urls = re.findall(hls_pattern, script.string, re.IGNORECASE)
                    for script_url in script_urls:
                        if script_url not in [s['url'] for s in streams]:
                            streams.append({
                                'url': script_url,
                                'type': 'script_hls',
                                'title': f'📡 HLS from Script: {urlparse(url).netloc}'
                            })
                            print(f"  Found HLS in script: {script_url}")
            
            print(f"\n✅ Total streams found: {len(streams)}")
            return streams
            
        except Exception as e:
            print(f"❌ Error extracting streams: {e}")
            return []

def test_urls():
    """Test various URLs"""
    extractor = StreamExtractor()
    
    test_urls = [
        'https://www.fox7austin.com/fox-7-web-cams'
    ]
    
    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"Testing: {url}")
        print('='*60)
        
        streams = extractor.extract_streams(url)
        
        if streams:
            print(f"\n📋 Stream Summary:")
            for i, stream in enumerate(streams, 1):
                print(f"  {i}. {stream['title']}")
                print(f"     Type: {stream['type']}")
                print(f"     URL: {stream['url']}")
        else:
            print("\n❌ No streams found")

if __name__ == "__main__":
    test_urls()