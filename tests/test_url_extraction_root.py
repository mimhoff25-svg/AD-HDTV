#!/usr/bin/env python3
"""Test stream extraction from a URL."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'src')
for p in (ROOT, SRC):
    if p not in sys.path:
        sys.path.insert(0, p)

from webgridplayer import VideoStreamExtractor

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_url_extraction_root.py <URL>")
        print("\nExample URLs to test:")
        print("  https://www.youtube.com/watch?v=...")
        print("  https://www.twitch.tv/...")
        print("  Any webpage with embedded video")
        sys.exit(1)
    
    url = sys.argv[1]
    print(f"\n{'='*60}")
    print(f"Testing stream extraction from: {url}")
    print('='*60)
    
    extractor = VideoStreamExtractor()
    try:
        streams = extractor.extract_streams(url)
        print(f"\n✓ Found {len(streams)} stream(s):\n")
        
        for i, stream in enumerate(streams, 1):
            print(f"{i}. {stream.get('title', 'Untitled')}")
            print(f"   Type: {stream.get('type', 'unknown')}")
            print(f"   URL: {stream.get('url', 'N/A')[:80]}...")
            print()
        
        if not streams:
            print("⚠ No streams found - this URL will trigger the 'No Streams Found' dialog")
            print("   Options: Browser mode or direct URL loading")
    
    except Exception as e:
        print(f"\n✗ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
