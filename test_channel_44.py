#!/usr/bin/env python3
"""
Test channel 44 (Cartoon Network) extraction
"""

import time
import requests
from bs4 import BeautifulSoup

class TestExtractor:
    """Test version of VideoStreamExtractor with updated headers"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"'
        })
        self.request_delay = 1.0

    def test_channel_44(self):
        """Test channel 44 specifically"""
        url = "https://thetvapp.to/tv/cartoon-network-live-stream/"

        print(f"Testing Channel 44 (Cartoon Network): {url}")
        print("=" * 60)

        try:
            # Add delay before request
            print(f"Waiting {self.request_delay}s before request...")
            time.sleep(self.request_delay)

            print("Making request...")
            response = self.session.get(url, timeout=45)
            print(f"Response status: {response.status_code}")

            if response.status_code == 200:
                print("✅ Request successful!")
                print(f"Content length: {len(response.content)} bytes")

                # Parse the HTML
                soup = BeautifulSoup(response.content, 'html.parser')

                # Check for stream_name element
                stream_node = soup.find(id='stream_name')
                if stream_node:
                    stream_name = (stream_node.get('name') or stream_node.get('data-name') or stream_node.text or '').strip()
                    print(f"✅ Found stream_name: '{stream_name}'")

                    # Try to get token
                    token_url = f"https://thetvapp.to/token/{stream_name}"
                    print(f"Token URL: {token_url}")

                    # Add delay before token request
                    time.sleep(self.request_delay)

                    token_resp = self.session.get(token_url, headers={'Referer': url}, timeout=20)
                    print(f"Token response status: {token_resp.status_code}")

                    if token_resp.status_code == 200:
                        data = token_resp.json()
                        stream_url = data.get('url') if isinstance(data, dict) else None
                        if stream_url:
                            print(f"✅ Token extraction successful!")
                            print(f"Stream URL: {stream_url[:100]}...")
                            return True
                        else:
                            print("❌ No stream URL in token response")
                    else:
                        print(f"❌ Token request failed with status {token_resp.status_code}")
                else:
                    print("❌ No stream_name element found")
                    print("Page content preview:")
                    print(response.text[:500] + "..." if len(response.text) > 500 else response.text)
            else:
                print(f"❌ Request failed with status {response.status_code}")

        except Exception as e:
            print(f"❌ Request failed: {e}")
            import traceback
            traceback.print_exc()

        return False

def test_channel_44():
    """Test channel 44 extraction"""
    extractor = TestExtractor()
    success = extractor.test_channel_44()

    if success:
        print("\n🎉 Channel 44 extraction successful!")
    else:
        print("\n❌ Channel 44 extraction failed")

if __name__ == "__main__":
    test_channel_44()
