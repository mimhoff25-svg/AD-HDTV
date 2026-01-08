#!/usr/bin/env python3
"""
WebGridPlayer - A VLC-based multi-video player with web stream extraction capabilities
Author: WebGridPlayer Development Team
License: GPL-3.0
"""

import sys
import os
import re
import json
import threading
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor

try:
    from PyQt6.QtWidgets import *
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *
    PYQT_VERSION = 6
    # Try to import WebEngine, but make it optional
    try:
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        WEBENGINE_AVAILABLE = True
    except ImportError:
        WEBENGINE_AVAILABLE = False
        QWebEngineView = None
except ImportError:
    try:
        from PyQt5.QtWidgets import *
        from PyQt5.QtCore import *
        from PyQt5.QtGui import *
        PYQT_VERSION = 5
        # Try to import WebEngine, but make it optional
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView
            WEBENGINE_AVAILABLE = True
        except ImportError:
            WEBENGINE_AVAILABLE = False
            QWebEngineView = None
    except ImportError:
        print("Error: PyQt6 or PyQt5 is required. Install with: pip install PyQt6")
        sys.exit(1)

try:
    import vlc
except ImportError:
    print("Error: python-vlc is required. Install with: pip install python-vlc")
    sys.exit(1)

# Allow disabling WebEngine via environment for headless/testing environments
if os.environ.get("WGP_DISABLE_WEBENGINE", "") == "1":
    WEBENGINE_AVAILABLE = False
    QWebEngineView = None

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: requests and beautifulsoup4 are required. Install with: pip install requests beautifulsoup4")
    sys.exit(1)


class VideoStreamExtractor:
    """Extracts video streams from web pages."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/'
        })

    def _extract_thetvapp_stream(self, soup: BeautifulSoup, page_url: str) -> List[Dict[str, str]]:
        """Extract TheTVApp tokenized stream URLs if present."""
        streams = []
        stream_node = soup.find(id='stream_name')
        if not stream_node:
            return streams

        stream_name = (stream_node.get('name') or stream_node.get('data-name') or stream_node.text or '').strip()
        if not stream_name:
            print("Stream name element not found or invalid.")
            return streams

        token_url = urljoin(page_url, f"/token/{stream_name}")
        try:
            token_resp = self.session.get(token_url, headers={'Referer': page_url}, timeout=10)
            token_resp.raise_for_status()
            data = token_resp.json()
            stream_url = data.get('url') if isinstance(data, dict) else None
            if not stream_url:
                print("m3u8 URL not found in the response.")
                return streams

            streams.append({
                'url': stream_url,
                'type': 'application/x-mpegURL',
                'title': f'TVApp HLS: {stream_name}'
            })
        except Exception as e:
            print(f"Error fetching token stream from {token_url}: {e}")

        return streams
    
    def extract_streams(self, url: str) -> List[Dict[str, str]]:
        """Extract video streams from a web page. Always returns at least browser mode as fallback."""
        streams = []
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            print(f"\n=== Extracting from: {url} ===")

            # Method 0: Check for Video.js or blob URLs (requires browser mode)
            blob_videos = re.findall(r'blob:[a-zA-Z0-9-_:/]+', response.text)
            videojs_present = 'video-js' in response.text or 'vjs' in response.text or 'videojs' in response.text.lower()
            
            if blob_videos or videojs_present:
                print(f"Detected Video.js / Blob video player - suggesting browser mode")
                # Add the page URL itself as a browser mode option
                streams.append({
                    'url': url,
                    'type': 'browser',
                    'title': f'🌐 Browser Mode (Video.js) - {urlparse(url).netloc}'
                })
                if blob_videos:
                    print(f"  Found {len(blob_videos)} blob URL(s) - these require browser rendering")
            
            # Method 0: TheTVApp tokenized stream (jwplayer setup)
            streams.extend(self._extract_thetvapp_stream(soup, url))

            # Method 1: Find iframes with video sources and try to extract from them
            iframes = soup.find_all('iframe')
            print(f"Found {len(iframes)} iframes")
            for idx, iframe in enumerate(iframes, 1):
                src = iframe.get('src') or iframe.get('data-src') or iframe.get('data-lazy-src')
                if src:
                    abs_src = urljoin(url, src)
                    print(f"  Iframe #{idx}: {abs_src}")
                    
                    # Add iframe URL
                    streams.append({
                        'url': abs_src,
                        'type': 'iframe',
                        'title': f'📺 Iframe #{idx}: {urlparse(abs_src).netloc}'
                    })
                    
                    # Try to extract from iframe content
                    try:
                        iframe_response = self.session.get(abs_src, timeout=5)
                        iframe_soup = BeautifulSoup(iframe_response.content, 'html.parser')
                        
                        # Look for videos in iframe
                        iframe_videos = iframe_soup.find_all('video')
                        for v_idx, video in enumerate(iframe_videos, 1):
                            v_src = video.get('src') or video.get('data-src')
                            if v_src and not v_src.startswith('blob:'):
                                streams.append({
                                    'url': urljoin(abs_src, v_src),
                                    'type': 'iframe_video',
                                    'title': f'🎥 Video from Iframe #{idx}'
                                })
                                print(f"    Found video in iframe: {v_src}")
                        
                        # Look for .m3u8 in iframe
                        iframe_m3u8 = re.findall(r'https?://[^\s"\'<>]+\.m3u8(?:\?[^\s"\'<>]*)?', 
                                                iframe_response.text, re.IGNORECASE)
                        for m3u8_url in iframe_m3u8:
                            if m3u8_url not in [s['url'] for s in streams]:
                                streams.append({
                                    'url': m3u8_url,
                                    'type': 'iframe_hls',
                                    'title': f'📡 HLS from Iframe #{idx}'
                                })
                                print(f"    Found HLS in iframe: {m3u8_url}")
                    except Exception as e:
                        print(f"    Could not extract from iframe: {e}")
            
            # Method 2: Find HTML5 video tags with all attributes
            video_tags = soup.find_all('video')
            print(f"Found {len(video_tags)} video tags")
            for idx, video in enumerate(video_tags, 1):
                # Get video ID for better identification
                video_id = video.get('id', f'video-{idx}')
                video_class = video.get('class', [])
                video_class_str = ' '.join(video_class) if isinstance(video_class, list) else str(video_class)
                
                print(f"  Video #{idx}: id='{video_id}', class='{video_class_str}'")
                
                # Check direct src attribute
                src = video.get('src') or video.get('data-src') or video.get('data-video-src')
                if src:
                    print(f"    src: {src[:100]}")
                    if not src.startswith('blob:'):
                        streams.append({
                            'url': urljoin(url, src),
                            'type': 'html5',
                            'title': f'🎬 Video #{idx} ({video_id})'
                        })
                
                # Check source tags within video
                sources = video.find_all('source')
                for s_idx, source in enumerate(sources, 1):
                    src = source.get('src') or source.get('data-src')
                    if src:
                        print(f"    source[{s_idx}]: {src[:100]}")
                        if not src.startswith('blob:'):
                            streams.append({
                                'url': urljoin(url, src),
                                'type': source.get('type', 'video/mp4'),
                                'title': f'🎥 Video #{idx} Source {s_idx}'
                            })
                
                # If blob URL, note that we found a dynamic player
                if video.get('src', '').startswith('blob:'):
                    streams.append({
                        'url': f'[DYNAMIC] Video player detected: {video_id} (class: {video_class_str})',
                        'type': 'dynamic',
                        'title': f'🎬 Dynamic Video #{idx} ({video_id}) - Check browser DevTools Network tab',
                        'note': 'This video uses dynamic blob URLs. Look for .m3u8 or .mp4 files in Network tab'
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
            
            # Method 4: Look for YouTube embeds
            youtube_pattern = r'(?:youtube\.com/embed/|youtu\.be/)([a-zA-Z0-9_-]+)'
            youtube_matches = re.findall(youtube_pattern, response.text)
            for video_id in youtube_matches:
                streams.append({
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'type': 'youtube',
                    'title': f'YouTube Video: {video_id}'
                })
            
            # Method 4b: Look for streaming CDN URLs (common patterns)
            cdn_pattern = r'https?://[^\s"\x27<>]*(?:cloudfront\.net|cdn|stream|vod)[^\s"\x27<>]*\.(?:m3u8|mp4|ts)(?:\?[^\s"\x27<>]*)?'
            cdn_matches = re.findall(cdn_pattern, response.text, re.IGNORECASE)
            for cdn_url in cdn_matches:
                if cdn_url not in [s['url'] for s in streams]:  # Avoid duplicates
                    streams.append({
                        'url': cdn_url,
                        'type': 'cdn_stream',
                        'title': f'CDN Stream from {urlparse(url).netloc}'
                    })
            
            # Method 4c: Look for JWPlayer, VideoJS, and player configurations
            # JWPlayer pattern
            jwplayer_pattern = r'file["\x27]?\s*:\s*["\x27]([^"\x27]+\.(?:m3u8|mp4|webm)(?:\?[^"\x27]*)?)'
            jwplayer_matches = re.findall(jwplayer_pattern, response.text, re.IGNORECASE)
            for jwp_url in jwplayer_matches:
                abs_jwp_url = urljoin(url, jwp_url)
                if abs_jwp_url not in [s['url'] for s in streams]:
                    streams.append({
                        'url': abs_jwp_url,
                        'type': 'jwplayer',
                        'title': f'JWPlayer Stream from {urlparse(url).netloc}'
                    })
            
            # VideoJS/HTML5 source pattern
            videojs_pattern = r'sources?["\x27]?\s*:\s*\[\s*\{[^}]*["\x27]src["\x27]\s*:\s*["\x27]([^"\x27]+)["\x27]'
            videojs_matches = re.findall(videojs_pattern, response.text, re.IGNORECASE)
            for vjs_url in videojs_matches:
                abs_vjs_url = urljoin(url, vjs_url)
                if abs_vjs_url not in [s['url'] for s in streams]:
                    streams.append({
                        'url': abs_vjs_url,
                        'type': 'videojs',
                        'title': f'VideoJS Stream from {urlparse(url).netloc}'
                    })
            
            # Look for any URLs ending in common video extensions in script tags
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string:
                    # Find URLs in JavaScript
                    url_pattern = r'https?://[^\s"\x27<>]+\.(?:m3u8|mp4|webm|ts)(?:\?[^\s"\x27<>]*)?'
                    script_urls = re.findall(url_pattern, script.string, re.IGNORECASE)
                    for script_url in script_urls:
                        if script_url not in [s['url'] for s in streams]:
                            streams.append({
                                'url': script_url,
                                'type': 'script_embedded',
                                'title': f'Script Embedded Stream from {urlparse(url).netloc}'
                            })
            
            # Method 5: Look for blob URLs and note them
            blob_pattern = r'blob:[a-zA-Z0-9-_]+:[a-zA-Z0-9-_]+'
            blob_matches = re.findall(blob_pattern, response.text)
            for blob_url in blob_matches:
                streams.append({
                    'url': blob_url,
                    'type': 'blob',
                    'title': f'Blob Video from {urlparse(url).netloc}',
                    'note': 'May not work directly - requires special handling'
                })
            
            # Remove duplicates
            seen_urls = set()
            unique_streams = []
            for stream in streams:
                if stream['url'] not in seen_urls:
                    seen_urls.add(stream['url'])
                    unique_streams.append(stream)
            
            # Fallback: If no streams found, suggest browser mode
            # (useful for JavaScript-heavy sites like LocalNow with Video.js)
            if not unique_streams:
                print(f"No direct streams found - suggesting browser mode for dynamic content")
                unique_streams.append({
                    'url': url,
                    'type': 'browser',
                    'title': f'🌐 Browser Mode - {urlparse(url).netloc}'
                })
            
            return unique_streams
            
        except Exception as e:
            print(f"Error extracting streams from {url}: {e}")
            # Always return browser mode as fallback
            print(f"Returning browser mode as fallback")
            return [{
                'url': url,
                'type': 'browser',
                'title': f'🌐 Browser Mode - {urlparse(url).netloc}'
            }]


class VideoPlayer(QFrame):
    """Individual video player widget with VLC integration."""
    
    def __init__(self, player_id: int, parent=None):
        super().__init__(parent)
        self.player_id = player_id
        self.media_player = None
        self.media = None
        self.current_url = ""
        self.start_time = 0
        self.end_time = 0
        self.is_clipped = False
        
        # Browser mode support
        self.browser_mode = False
        self.web_view = None
        self.video_widget = None
        
        # Loop and refresh support
        self.loop_enabled = False
        self.auto_refresh_enabled = False
        self.auto_refresh_interval = 300  # 5 minutes in seconds
        self.refresh_timer = None
        
        self.init_ui()
        self.init_vlc()
    
    def init_ui(self):
        """Initialize the UI components."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setMinimumSize(200, 150)  # Smaller minimum for better scaling
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)  # Minimal margins
        layout.setSpacing(0)
        
        # Create stacked widget to switch between VLC and Browser
        self.mode_stack = QStackedWidget()
        
        # VLC video widget
        self.video_widget = QWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.mode_stack.addWidget(self.video_widget)  # Index 0
        
        # Web browser widget (if available)
        if WEBENGINE_AVAILABLE:
            self.web_view = QWebEngineView()
            self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            # Enable fullscreen support for web view
            self.web_view.settings().setAttribute(self.web_view.settings().WebAttribute.FullScreenSupportEnabled, True)
            self.mode_stack.addWidget(self.web_view)  # Index 1
        else:
            # Fallback: simple label explaining WebEngine is not available
            fallback_label = QLabel(
                "Web browser mode not available\n"
                "(QtWebEngine not installed)\n\n"
                f"Python: {sys.executable}\n"
                f"VIRTUAL_ENV: {os.environ.get('VIRTUAL_ENV', '')}"
            )
            fallback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback_label.setStyleSheet("color: white; background-color: black; padding: 20px;")
            self.mode_stack.addWidget(fallback_label)  # Index 1
        
        layout.addWidget(self.mode_stack, 1)  # Stretch factor 1
        
        # Info panel (compact)
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(2, 2, 2, 2)
        info_layout.setSpacing(2)
        
        self.url_label = QLabel("Empty")
        self.url_label.setStyleSheet("color: white; background-color: rgba(0,0,0,180); padding: 2px; font-size: 9pt;")
        self.url_label.setWordWrap(False)
        self.url_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        info_layout.addWidget(self.url_label)
        
        # Mode toggle button
        self.mode_button = QPushButton("🎬")
        self.mode_button.setFixedSize(30, 20)
        self.mode_button.setStyleSheet("background-color: rgba(0,0,0,180); color: white; border: none; font-size: 10pt;")
        self.mode_button.clicked.connect(self.toggle_mode)
        self.mode_button.setToolTip("Toggle VLC/Browser mode")
        info_layout.addWidget(self.mode_button)
        
        # Mute button
        self.mute_button = QPushButton("🔊")
        self.mute_button.setFixedSize(30, 20)
        self.mute_button.setStyleSheet("background-color: rgba(0,0,0,180); color: white; border: none; font-size: 10pt;")
        self.mute_button.clicked.connect(self.toggle_mute)
        self.mute_button.setToolTip("Toggle mute")
        self.is_muted = False
        info_layout.addWidget(self.mute_button)
        
        # Caption toggle button
        self.caption_button = QPushButton("CC")
        self.caption_button.setFixedSize(30, 20)
        self.caption_button.setStyleSheet("background-color: rgba(0,0,0,180); color: white; border: none; font-size: 9pt;")
        self.caption_button.clicked.connect(self.toggle_captions)
        self.caption_button.setToolTip("Toggle captions (V key)")
        self.captions_enabled = False
        info_layout.addWidget(self.caption_button)
        
        # Fullscreen button (window-level)
        self.fullscreen_button = QPushButton("⛶")
        self.fullscreen_button.setFixedSize(30, 20)
        self.fullscreen_button.setStyleSheet("background-color: rgba(0,0,0,180); color: white; border: none; font-size: 10pt;")
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)
        self.fullscreen_button.setToolTip("Toggle fullscreen (Esc to exit)")
        # Initially visible; main window will control visibility based on grid size
        info_layout.addWidget(self.fullscreen_button)
        
        # Loop button
        self.loop_button = QPushButton("🔁")
        self.loop_button.setFixedSize(30, 20)
        self.loop_button.setStyleSheet("background-color: rgba(0,0,0,180); color: white; border: none; font-size: 9pt;")
        self.loop_button.clicked.connect(self.toggle_loop)
        self.loop_button.setToolTip("Loop video (L key)")
        info_layout.addWidget(self.loop_button)
        
        # Auto-refresh button
        self.refresh_button = QPushButton("🔄")
        self.refresh_button.setFixedSize(30, 20)
        self.refresh_button.setStyleSheet("background-color: rgba(0,0,0,180); color: white; border: none; font-size: 9pt;")
        self.refresh_button.clicked.connect(self.toggle_auto_refresh)
        self.refresh_button.setToolTip("Auto-refresh (R key)")
        info_layout.addWidget(self.refresh_button)
        
        self.status_label = QLabel("⭕")
        self.status_label.setStyleSheet("color: #FFD700; background-color: rgba(0,0,0,180); padding: 2px; font-size: 9pt;")
        self.status_label.setFixedWidth(40)
        info_layout.addWidget(self.status_label)
        
        layout.addLayout(info_layout)
        self.setLayout(layout)
    
    def init_vlc(self):
        """Initialize VLC media player."""
        try:
            # Create VLC instance with platform-specific options
            vlc_args = [
                '--quiet',  # Don't print debug messages
                '--aout=alsa',  # Use ALSA audio output on Linux
                '--no-video-title-show',  # Don't show video title
                '--network-caching=1000',  # Network caching (ms) for better streaming
                '--live-caching=1000',     # Live stream caching
                '--http-reconnect',        # Reconnect on HTTP errors
                '--adaptive-logic=highest', # Best quality for adaptive streams
                '--hls-fakeua',           # Use fake User-Agent for HLS
            ]
            
            # Add platform-specific options
            if sys.platform.startswith('linux'):
                vlc_args.append('--no-xlib')  # Don't use X11 on Linux
            
            self.vlc_instance = vlc.Instance(vlc_args)
            
            # Create media player
            self.media_player = self.vlc_instance.media_player_new()
            
            # Set the video output to our widget
            if sys.platform.startswith('linux'):
                self.media_player.set_xwindow(int(self.video_widget.winId()))
            elif sys.platform == "win32":
                self.media_player.set_hwnd(int(self.video_widget.winId()))
            elif sys.platform == "darwin":
                self.media_player.set_nsobject(int(self.video_widget.winId()))
            
            # Set up event manager
            self.event_manager = self.media_player.event_manager()
            self.event_manager.event_attach(vlc.EventType.MediaPlayerMediaChanged, self._on_media_changed)
            self.event_manager.event_attach(vlc.EventType.MediaPlayerTimeChanged, self._on_time_changed)
            self.event_manager.event_attach(vlc.EventType.MediaPlayerPositionChanged, self._on_position_changed)
            self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_media_end)
            
        except Exception as e:
            print(f"Error initializing VLC for player {self.player_id}: {e}")
            self.status_label.setText("VLC Error")
    
    def load_media(self, url: str, title: str = None):
        """Load media from URL or file path."""
        try:
            if not self.media_player:
                self.status_label.setText("No Player")
                return False
                
            self.current_url = url
            
            # Create media with additional options for HLS streams
            if url.startswith(('http://', 'https://')):
                self.media = self.vlc_instance.media_new(url)
                
                # Add specific options for HLS/m3u8 streams
                if '.m3u8' in url.lower():
                    self.media.add_option(':http-user-agent=Mozilla/5.0 (compatible; VLC)')
                    self.media.add_option(':network-caching=1500')
                    self.media.add_option(':live-caching=1500')
                    self.media.add_option(':http-reconnect')
                    print(f"Applied HLS options for: {url}")
            else:
                self.media = self.vlc_instance.media_new_path(url)
            
            if not self.media:
                self.status_label.setText("Media Error")
                return False
            
            # Set media to player
            self.media_player.set_media(self.media)
            
            # Update UI
            display_title = title or os.path.basename(url) if not url.startswith(('http://', 'https://')) else url
            self.url_label.setText(display_title)
            self.status_label.setText("Loading...")
            
            # Auto-play after a short delay to ensure media is ready
            QTimer.singleShot(200, self.play)
            
            return True
            
        except Exception as e:
            print(f"Error loading media {url}: {e}")
            self.status_label.setText("Load Error")
            return False
    
    def play(self):
        """Play the media."""
        if self.media_player and self.media:
            self.media_player.play()
            self.status_label.setText("Playing")
            
            # Handle clipping
            if self.is_clipped and self.start_time > 0:
                # Wait a bit for the media to start, then seek to start time
                QTimer.singleShot(100, lambda: self.media_player.set_time(int(self.start_time * 1000)))
    
    def pause(self):
        """Pause the media."""
        if self.media_player:
            self.media_player.pause()
            self.status_label.setText("Paused")
    
    def stop(self):
        """Stop the media."""
        if self.media_player:
            self.media_player.stop()
            self.status_label.setText("Stopped")
    
    def set_volume(self, volume: int):
        """Set volume (0-100)."""
        if self.media_player:
            self.media_player.audio_set_volume(volume)    
    def toggle_mute(self):
        """Toggle mute for this player."""
        if self.media_player:
            self.is_muted = not self.is_muted
            self.media_player.audio_set_mute(self.is_muted)
            self.mute_button.setText("🔇" if self.is_muted else "🔊")
            self.mute_button.setToolTip("Unmute" if self.is_muted else "Mute")
    
    def toggle_captions(self):
        """Toggle captions/subtitles for this player."""
        if not self.media_player:
            return
        try:
            self.captions_enabled = not self.captions_enabled
            
            if self.captions_enabled:
                # Try to enable the first available subtitle track
                spu_count = self.media_player.video_get_spu_count()
                if spu_count > 0:
                    # Get list of available SPU (subtitle) tracks
                    spus = self.media_player.video_get_spu_description()
                    if spus and len(spus) > 0:
                        # Enable first subtitle track
                        self.media_player.video_set_spu(spus[0][0])
                        self.caption_button.setText("CC✓")
                        self.caption_button.setStyleSheet("background-color: rgba(0,200,0,200); color: white; border: none; font-size: 9pt;")
                        self.caption_button.setToolTip("Captions ON (V key)")
                        print(f"Captions enabled: {spus[0][1]}")
                    else:
                        self.caption_button.setText("CC✗")
                        self.caption_button.setToolTip("No captions available")
                        self.captions_enabled = False
                else:
                    self.caption_button.setText("CC✗")
                    self.caption_button.setToolTip("No captions available")
                    self.captions_enabled = False
            else:
                # Disable subtitles
                self.media_player.video_set_spu(-1)
                self.caption_button.setText("CC")
                self.caption_button.setStyleSheet("background-color: rgba(0,0,0,180); color: white; border: none; font-size: 9pt;")
                self.caption_button.setToolTip("Toggle captions (V key)")
                print("Captions disabled")
        except Exception as e:
            print(f"Error toggling captions: {e}")
            self.caption_button.setText("CC")
            self.caption_button.setToolTip("Captions unavailable")
            self.captions_enabled = False
    
    def toggle_loop(self):
        """Toggle video looping."""
        self.loop_enabled = not self.loop_enabled
        if self.media_player:
            self.media_player.video_set_aspect_ratio(None)  # Keep aspect ratio
        
        if self.loop_enabled:
            self.loop_button.setText("🔁✓")
            self.loop_button.setStyleSheet("background-color: rgba(0,150,0,200); color: white; border: none; font-size: 9pt;")
            self.loop_button.setToolTip("Loop ON (L key)")
            print("Loop enabled")
        else:
            self.loop_button.setText("🔁")
            self.loop_button.setStyleSheet("background-color: rgba(0,0,0,180); color: white; border: none; font-size: 9pt;")
            self.loop_button.setToolTip("Loop video (L key)")
            print("Loop disabled")
    
    def toggle_auto_refresh(self):
        """Toggle auto-refresh of stream."""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        
        if self.auto_refresh_enabled:
            self.refresh_button.setText("🔄✓")
            self.refresh_button.setStyleSheet("background-color: rgba(0,100,200,200); color: white; border: none; font-size: 9pt;")
            self.refresh_button.setToolTip(f"Auto-refresh ON every {self.auto_refresh_interval}s (R key)")
            self.start_auto_refresh()
            print(f"Auto-refresh enabled (interval: {self.auto_refresh_interval}s)")
        else:
            self.refresh_button.setText("🔄")
            self.refresh_button.setStyleSheet("background-color: rgba(0,0,0,180); color: white; border: none; font-size: 9pt;")
            self.refresh_button.setToolTip("Auto-refresh (R key)")
            self.stop_auto_refresh()
            print("Auto-refresh disabled")
    
    def start_auto_refresh(self):
        """Start the auto-refresh timer."""
        if self.refresh_timer is None:
            self.refresh_timer = QTimer()
            self.refresh_timer.timeout.connect(self._do_auto_refresh)
        self.refresh_timer.start(self.auto_refresh_interval * 1000)  # Convert to milliseconds
    
    def stop_auto_refresh(self):
        """Stop the auto-refresh timer."""
        if self.refresh_timer:
            self.refresh_timer.stop()
    
    def _do_auto_refresh(self):
        """Perform auto-refresh by reloading the current stream."""
        if self.current_url and self.media_player:
            print(f"Auto-refreshing: {self.current_url[:60]}")
            self.load_media(self.current_url, "Auto-Refreshed")
    
    def toggle_mode(self):
        """Toggle between VLC and browser mode."""
        if not WEBENGINE_AVAILABLE:
            return
            
        self.browser_mode = not self.browser_mode
        
        if self.browser_mode:
            # Switch to browser mode
            self.mode_stack.setCurrentIndex(1)
            self.mode_button.setText("📺")
            self.mode_button.setToolTip("Switch to VLC mode")
            # Visibility managed by main window based on grid size
            wnd = self.window()
            updater = getattr(wnd, 'update_fullscreen_button_visibility', None)
            if callable(updater):
                updater()
            self.status_label.setText("🌐")
            
            # Load current URL in browser if available
            if self.current_url and self.web_view:
                self.load_url_in_browser(self.current_url)
        else:
            # Switch to VLC mode
            self.mode_stack.setCurrentIndex(0)
            self.mode_button.setText("🎬")
            self.mode_button.setToolTip("Switch to browser mode")
            # Visibility managed by main window based on grid size
            wnd = self.window()
            updater = getattr(wnd, 'update_fullscreen_button_visibility', None)
            if callable(updater):
                updater()
            self.status_label.setText("📺")
    
    def toggle_fullscreen(self):
        """Toggle application window fullscreen."""
        wnd = self.window()
        # Prefer calling main window's toggle if available
        toggle = getattr(wnd, 'toggle_fullscreen', None)
        if callable(toggle):
            toggle()
            # Update icon based on window state
            if wnd.isFullScreen():
                self.fullscreen_button.setText("⛏")
                self.fullscreen_button.setToolTip("Exit fullscreen (Esc)")
            else:
                self.fullscreen_button.setText("⛶")
                self.fullscreen_button.setToolTip("Enter fullscreen")
            return
        # Fallback: directly toggle window fullscreen
        if wnd.isFullScreen():
            wnd.showNormal()
            self.fullscreen_button.setText("⛶")
            self.fullscreen_button.setToolTip("Enter fullscreen")
        else:
            wnd.showFullScreen()
            self.fullscreen_button.setText("⛏")
            self.fullscreen_button.setToolTip("Exit fullscreen (Esc)")
    
    def load_url_in_browser(self, url: str):
        """Load URL in browser mode."""
        if self.web_view and WEBENGINE_AVAILABLE:
            self.web_view.setUrl(QUrl(url))
            self.current_url = url
            self.url_label.setText(f"Browser: {url}")
            print(f"🌐 Loading in browser: {url}")    
    def set_position(self, position: float):
        """Set playback position (0.0-1.0)."""
        if self.media_player:
            self.media_player.set_position(position)
    
    def get_position(self) -> float:
        """Get current playback position (0.0-1.0)."""
        if self.media_player:
            return self.media_player.get_position()
        return 0.0
    
    def set_clip_range(self, start_seconds: float, end_seconds: float):
        """Set the clip range for this player."""
        self.start_time = start_seconds
        self.end_time = end_seconds
        self.is_clipped = end_seconds > start_seconds > 0
    
    def _on_media_changed(self, event):
        """Handle media changed event."""
        pass
    
    def _on_time_changed(self, event):
        """Handle time changed event."""
        if self.is_clipped and self.end_time > 0:
            current_time = self.media_player.get_time() / 1000.0  # Convert to seconds
            if current_time >= self.end_time:
                self.media_player.set_time(int(self.start_time * 1000))  # Loop back to start
    
    def _on_position_changed(self, event):
        """Handle position changed event."""
        pass
    
    def _on_media_end(self, event):
        """Handle media end reached event - restart if looping."""
        if self.loop_enabled and self.media_player and self.current_url:
            print(f"Media ended, restarting (loop enabled)")
            self.media_player.set_time(0)
            self.media_player.play()


class WebGridPlayer(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.grid_size = (1, 1)  # rows, cols - default to 1x1 for single video
        self.players: List[VideoPlayer] = []
        # Channel navigation state
        self.channels: List[Dict[str, Any]] = []
        self.channel_numbers: List[int] = []
        self.current_channel_idx: int = 0
        self.current_volume = 70
        self.extractor = VideoStreamExtractor()
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.control_panel_visible = True
        self.control_panel = None
        
        # Track time-sensitive streams for refresh
        self.active_streams = {}  # {url: {'last_refresh': timestamp, 'original_url': url}}
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.check_stream_refresh)
        self.refresh_timer.start(60000)  # Check every minute
        
        self._fullscreen_active = False
        # Load available channels from state/channels.json (if present)
        self.load_channels()
        self.init_ui()
        self.create_grid()
        # Defer button visibility update to next event loop so layout is ready
        QTimer.singleShot(0, self.update_fullscreen_button_visibility)
        # Start in fullscreen for 1x1 mode
        QTimer.singleShot(100, self.enter_fullscreen)
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("WebGridPlayer - Multi-Video Player with Web Stream Extraction")
        self.setGeometry(100, 100, 1200, 800)
        
        # Enable right-click context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Control panel
        self.control_panel = self.create_control_panel()
        main_layout.addWidget(self.control_panel)
        
        # Toggle control panel button (small, in corner)
        self.toggle_button = QPushButton("▼ Hide Controls")
        self.toggle_button.setMaximumWidth(150)
        self.toggle_button.clicked.connect(self.toggle_control_panel)
        main_layout.addWidget(self.toggle_button)
        
        # Grid container
        self.grid_container = QWidget()
        main_layout.addWidget(self.grid_container)
        
        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # Shortcuts for fullscreen and channel navigation
        try:
            self._esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
            self._esc_shortcut.activated.connect(self.exit_fullscreen)
            self._f11_shortcut = QShortcut(QKeySequence(Qt.Key.Key_F11), self)
            self._f11_shortcut.activated.connect(self.toggle_fullscreen)
            # Channel up/down: map multiple keys for reliability
            # '=' and '+' → Channel Up
            self._chan_up_equal = QShortcut(QKeySequence(Qt.Key.Key_Equal), self)
            self._chan_up_equal.activated.connect(self.channel_up)
            self._chan_up_plus = QShortcut(QKeySequence(Qt.Key.Key_Plus), self)
            self._chan_up_plus.activated.connect(self.channel_up)
            # '-' → Channel Down
            self._chan_down_minus = QShortcut(QKeySequence(Qt.Key.Key_Minus), self)
            self._chan_down_minus.activated.connect(self.channel_down)
            # 'V' → Toggle Captions/Subtitles
            self._caption_shortcut = QShortcut(QKeySequence(Qt.Key.Key_V), self)
            self._caption_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            self._caption_shortcut.activated.connect(self.toggle_captions_global)
            # 'L' → Toggle Loop
            self._loop_shortcut = QShortcut(QKeySequence(Qt.Key.Key_L), self)
            self._loop_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            self._loop_shortcut.activated.connect(self.toggle_loop_global)
            # 'R' → Toggle Auto-Refresh
            self._refresh_shortcut = QShortcut(QKeySequence(Qt.Key.Key_R), self)
            self._refresh_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            self._refresh_shortcut.activated.connect(self.toggle_refresh_global)
        except Exception:
            pass

    def enter_fullscreen(self):
        """Enter fullscreen and hide chrome."""
        if self._fullscreen_active and self.isFullScreen():
            return
        self._fullscreen_active = True
        try:
            if self.menuBar():
                self.menuBar().setVisible(False)
        except Exception:
            pass
        try:
            if getattr(self, 'control_panel', None):
                self.control_panel.setVisible(False)
        except Exception:
            pass
        try:
            if getattr(self, 'toggle_button', None):
                self.toggle_button.setVisible(False)
        except Exception:
            pass
        try:
            if getattr(self, 'status_bar', None):
                self.status_bar.setVisible(False)
        except Exception:
            pass
        self.showFullScreen()

    def exit_fullscreen(self):
        """Exit fullscreen and restore chrome."""
        if not self.isFullScreen() and not self._fullscreen_active:
            return
        self.showNormal()
        try:
            if self.menuBar():
                self.menuBar().setVisible(True)
        except Exception:
            pass
        try:
            if getattr(self, 'control_panel', None):
                self.control_panel.setVisible(self.control_panel_visible)
        except Exception:
            pass
        try:
            if getattr(self, 'toggle_button', None):
                self.toggle_button.setVisible(True)
        except Exception:
            pass
        try:
            if getattr(self, 'status_bar', None):
                self.status_bar.setVisible(True)
        except Exception:
            pass
        self._fullscreen_active = False

    def toggle_fullscreen(self):
        """Toggle window fullscreen state."""
        if self.isFullScreen():
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    def get_primary_player(self) -> Optional[VideoPlayer]:
        """Return the primary player to tune (first slot)."""
        return self.players[0] if self.players else None

    # ===== Channels: load + navigation =====
    def load_channels(self):
        """Load channels from state/channels.json into memory."""
        try:
            state_path = Path("state/channels.json")
            if not state_path.exists():
                return
            with open(state_path, "r") as f:
                data = json.load(f)
            # channels.json is a dict of number -> {title, source_url, ...}
            items = []
            for num_str, info in data.items():
                try:
                    num = int(num_str)
                except ValueError:
                    continue
                items.append({"number": num, **info})
            # Sort by channel number
            items.sort(key=lambda x: x["number"])
            self.channels = items
            self.channel_numbers = [c["number"] for c in items]
            # Default to first channel
            self.current_channel_idx = 0 if items else 0
        except Exception as e:
            print(f"Failed to load channels: {e}")

    def tune_to_channel(self, idx: int):
        """Tune to channel at index: extract streams or fallback to browser/direct."""
        if not self.channels:
            self.status_bar.showMessage("No channels available")
            return
        # Clamp index
        idx = max(0, min(idx, len(self.channels) - 1))
        self.current_channel_idx = idx
        ch = self.channels[idx]
        title = ch.get("title", f"Channel {ch.get('number')}")
        src = ch.get("source_url") or ch.get("url")
        if not src:
            self.status_bar.showMessage("Channel has no source URL")
            return
        self.status_bar.showMessage(f"Tuning: {title}")
        # Auto tune: extract in background and immediately play best stream
        def worker():
            try:
                streams = self.extractor.extract_streams(src)
            except Exception as e:
                streams = []
                print(f"Channel extract error: {e}")

            # Choose best candidate
            best = None
            # Prefer HLS (.m3u8)
            for s in streams:
                if '.m3u8' in s.get('url', '').lower():
                    best = s
                    break
            # Next, any direct video
            if not best:
                for s in streams:
                    if s.get('type') in ('iframe_video', 'video'):
                        best = s
                        break
            # Next, iframe
            if not best and streams:
                best = streams[0]

            def apply():
                player = self.get_primary_player()
                if not player:
                    return
                if best and '.m3u8' in best.get('url', '').lower():
                    player.load_media(best['url'], best.get('title'))
                elif best and best.get('type') == 'iframe' and WEBENGINE_AVAILABLE:
                    # Browser mode for iframe pages
                    player.browser_mode = True
                    player.mode_stack.setCurrentIndex(1)
                    player.mode_button.setText("📺")
                    player.mode_button.setToolTip("Switch to VLC mode")
                    player.fullscreen_button.setVisible(self.is_single_grid())
                    player.status_label.setText("🌐")
                    player.load_url_in_browser(best['url'])
                elif best:
                    player.load_media(best['url'], best.get('title'))
                else:
                    # No streams → open source page in browser
                    if WEBENGINE_AVAILABLE:
                        self.add_url_to_browser_mode(src)
                    else:
                        self.add_url_to_grid(src)

            QTimer.singleShot(0, apply)

        # Run extraction in background
        self.thread_pool.submit(worker)

    def channel_up(self):
        """Go to next channel (higher index)."""
        if not self.channels:
            self.load_channels()
            if not self.channels:
                return
        self.tune_to_channel(self.current_channel_idx + 1)

    def channel_down(self):
        """Go to previous channel (lower index)."""
        if not self.channels:
            self.load_channels()
            if not self.channels:
                return
        self.tune_to_channel(self.current_channel_idx - 1)

    def toggle_captions_global(self):
        """Toggle captions on the primary player."""
        player = self.get_primary_player()
        if player:
            player.toggle_captions()

    def toggle_loop_global(self):
        """Toggle loop on the primary player."""
        player = self.get_primary_player()
        if player:
            player.toggle_loop()

    def toggle_refresh_global(self):
        """Toggle auto-refresh on the primary player."""
        player = self.get_primary_player()
        if player:
            player.toggle_auto_refresh()

    def show_context_menu(self, position):
        """Show context menu on right-click."""
        context_menu = QMenu(self)
        
        add_url_action = QAction('➕ Add URL...', self)
        add_url_action.triggered.connect(self.add_url_dialog)
        context_menu.addAction(add_url_action)
        
        add_files_action = QAction('📁 Add Files...', self)
        add_files_action.triggered.connect(self.open_files)
        context_menu.addAction(add_files_action)
        
        fetch_web_action = QAction('🌐 Fetch from Web...', self)
        fetch_web_action.triggered.connect(self.fetch_web_streams)
        context_menu.addAction(fetch_web_action)
        
        if WEBENGINE_AVAILABLE:
            browse_web_action = QAction('🌎 Browse Web Page...', self)
            browse_web_action.triggered.connect(self.browse_web_page)
            context_menu.addAction(browse_web_action)
        
        context_menu.addSeparator()

        # Channel controls
        chan_up_action = QAction('Ch+ Channel Up', self)
        chan_up_action.triggered.connect(self.channel_up)
        context_menu.addAction(chan_up_action)

        chan_down_action = QAction('Ch- Channel Down', self)
        chan_down_action.triggered.connect(self.channel_down)
        context_menu.addAction(chan_down_action)
        
        # Fullscreen option
        fullscreen_action = QAction('⛶ Toggle Fullscreen', self)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        context_menu.addAction(fullscreen_action)
        
        context_menu.addSeparator()
        
        clear_all_action = QAction('❌ Clear All Players', self)
        clear_all_action.triggered.connect(self.stop_all)
        context_menu.addAction(clear_all_action)
        
        context_menu.exec(self.mapToGlobal(position))        
        # Enable drag and drop
        self.setAcceptDrops(True)
    
    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        open_files_action = QAction('Open Files...', self)
        open_files_action.setShortcut('Ctrl+O')
        open_files_action.triggered.connect(self.open_files)
        file_menu.addAction(open_files_action)
        
        add_url_action = QAction('Add URL...', self)
        add_url_action.setShortcut('Ctrl+U')
        add_url_action.triggered.connect(self.add_url_dialog)
        file_menu.addAction(add_url_action)
        
        file_menu.addSeparator()
        
        save_state_action = QAction('💾 Save State...', self)
        save_state_action.setShortcut('Ctrl+S')
        save_state_action.triggered.connect(self.save_state)
        file_menu.addAction(save_state_action)
        
        load_state_action = QAction('📂 Load State...', self)
        load_state_action.setShortcut('Ctrl+L')
        load_state_action.triggered.connect(self.load_state)
        file_menu.addAction(load_state_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Grid menu
        grid_menu = menubar.addMenu('Grid')
        
        # Simplified grid options: 1, 4, or 8 screens
        grid_options = [
            (1, 1, '1 Screen'),
            (2, 2, '4 Screens (2×2)'),
            (2, 4, '8 Screens (2×4)'),
        ]
        for rows, cols, label in grid_options:
            action = QAction(label, self)
            action.triggered.connect(lambda checked, r=rows, c=cols: self.change_grid_size(r, c))
            grid_menu.addAction(action)
        
        # Web menu
        web_menu = menubar.addMenu('Web')
        fetch_action = QAction('Fetch from Web Page...', self)
        fetch_action.setShortcut('Ctrl+F')
        fetch_action.triggered.connect(self.fetch_web_streams)
        web_menu.addAction(fetch_action)

        # Channel menu
        channel_menu = menubar.addMenu('Channel')
        chan_up = QAction('Ch+ Channel Up', self)
        chan_up.setShortcut('+')
        chan_up.triggered.connect(self.channel_up)
        channel_menu.addAction(chan_up)

        chan_down = QAction('Ch- Channel Down', self)
        chan_down.setShortcut('-')
        chan_down.triggered.connect(self.channel_down)
        channel_menu.addAction(chan_down)
    
    def create_control_panel(self):
        """Create the control panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setMaximumHeight(100)
        
        layout = QHBoxLayout()
        panel.setLayout(layout)
        
        # Playback controls - dropdown menu
        controls_group = QGroupBox("Playback Controls")
        controls_layout = QHBoxLayout()
        controls_group.setLayout(controls_layout)
        
        controls_layout.addWidget(QLabel("Playback:"))
        self.playback_combo = QComboBox()
        self.playback_combo.addItems(["▶ Play All", "⏸ Pause All", "⏹ Stop All"])
        self.playback_combo.setCurrentIndex(-1)  # No selection by default
        self.playback_combo.currentTextChanged.connect(self.handle_playback_action)
        controls_layout.addWidget(self.playback_combo)
        
        # Add URL button for quick access
        self.quick_add_button = QPushButton("+ Add URL")
        self.quick_add_button.clicked.connect(self.add_url_dialog)
        controls_layout.addWidget(self.quick_add_button)
        
        layout.addWidget(controls_group)
        
        # Volume control
        volume_group = QGroupBox("Volume")
        volume_layout = QHBoxLayout()
        volume_group.setLayout(volume_layout)
        
        volume_layout.addWidget(QLabel("Volume:"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.current_volume)
        self.volume_slider.valueChanged.connect(self.set_volume_all)
        volume_layout.addWidget(self.volume_slider)
        
        self.volume_label = QLabel(f"{self.current_volume}%")
        volume_layout.addWidget(self.volume_label)
        
        layout.addWidget(volume_group)
        
        # Clipping controls
        clip_group = QGroupBox("Video Clipping (All Players)")
        clip_layout = QHBoxLayout()
        clip_group.setLayout(clip_layout)
        
        clip_layout.addWidget(QLabel("Start:"))
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setDisplayFormat("mm:ss")
        clip_layout.addWidget(self.start_time_edit)
        
        clip_layout.addWidget(QLabel("End:"))
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setDisplayFormat("mm:ss")
        clip_layout.addWidget(self.end_time_edit)
        
        self.apply_clip_button = QPushButton("Apply Clip")
        self.apply_clip_button.clicked.connect(self.apply_clip_range)
        clip_layout.addWidget(self.apply_clip_button)
        
        self.clear_clip_button = QPushButton("Clear Clip")
        self.clear_clip_button.clicked.connect(self.clear_clip_range)
        clip_layout.addWidget(self.clear_clip_button)
        
        layout.addWidget(clip_group)
        
        return panel
    
    def create_grid(self):
        """Create the video player grid."""
        # Clear existing players
        if hasattr(self, 'grid_layout'):
            for i in reversed(range(self.grid_layout.count())):
                child = self.grid_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
        
        self.players.clear()
        
        # Create new grid layout
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(2)  # Minimal spacing for cleaner look
        self.grid_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        self.grid_container.setLayout(self.grid_layout)
        
        # Create players for the grid
        rows, cols = self.grid_size
        player_id = 0
        
        for row in range(rows):
            for col in range(cols):
                player = VideoPlayer(player_id, self)
                self.players.append(player)
                self.grid_layout.addWidget(player, row, col)
                player_id += 1
        
        # Make grid cells expand equally
        for i in range(rows):
            self.grid_layout.setRowStretch(i, 1)
        for i in range(cols):
            self.grid_layout.setColumnStretch(i, 1)
        
        self.status_bar.showMessage(f"Grid: {rows}×{cols} ({len(self.players)} screens)")
        # Update fullscreen button visibility based on grid size
        self.update_fullscreen_button_visibility()
    
    def change_grid_size(self, rows: int, cols: int):
        """Change the grid size."""
        self.grid_size = (rows, cols)
        self.create_grid()

    def is_single_grid(self) -> bool:
        """Return True if grid is 1×1."""
        r, c = self.grid_size
        return r == 1 and c == 1

    def update_fullscreen_button_visibility(self):
        """Show fullscreen button only in 1×1 grid."""
        single = self.is_single_grid()
        for p in self.players:
            if hasattr(p, 'fullscreen_button'):
                btn = p.fullscreen_button
                if single:
                    btn.show()  # Explicitly show
                else:
                    btn.hide()  # Explicitly hide
    
    def open_files(self):
        """Open file dialog to add local video files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Video Files",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm *.m4v *.3gp);;All Files (*.*)"
        )
        
        if files:
            self.add_files_to_grid(files)
    
    def add_files_to_grid(self, files: List[str]):
        """Add files to available grid slots."""
        available_players = [p for p in self.players if not p.current_url]
        
        for i, file_path in enumerate(files):
            if i < len(available_players):
                player = available_players[i]
                player.load_media(file_path)
    
    def add_url_dialog(self):
        """Show dialog to add a URL."""
        url, ok = QInputDialog.getText(self, 'Add URL', 'Enter video URL or webpage URL:')
        if ok and url:
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Check if URL is a direct video file
            is_direct_video = any(url.lower().endswith(ext) for ext in ['.mp4', '.webm', '.ogg', '.avi', '.mov', '.flv', '.mkv'])
            
            # Direct video files - load immediately in VLC
            if is_direct_video:
                self.add_url_to_grid(url)
            else:
                # Everything else - try extraction and show preview dialog
                # (works for streams, iframes, embedded videos, and websites)
                self.extract_and_show_streams(url)
    
    def add_url_to_grid(self, url: str):
        """Add URL to the first available grid slot."""
        for player in self.players:
            if not player.current_url:
                player.load_media(url)
                break
    
    def browse_web_page(self):
        """Open a web page directly in browser mode."""
        url, ok = QInputDialog.getText(
            self, 
            'Browse Web Page',
            'Enter the web page URL to browse:'
        )
        
        if ok and url:
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            self.add_url_to_browser_mode(url)
    
    def extract_and_show_streams(self, url: str):
        """Extract streams from URL and show selection dialog, or load directly if only browser mode."""
        print(f"\n>>> extract_and_show_streams() called with URL: {url}")
        self.status_bar.showMessage("Extracting video streams...")
        
        # Run extraction in background thread
        print(f">>> Starting background extraction thread...")
        future = self.thread_pool.submit(self.extractor.extract_streams, url)
        
        # Show progress dialog
        progress = QProgressDialog("Extracting video streams...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        # Check for completion
        def check_completion():
            if future.done():
                print(f">>> Extraction completed!")
                progress.close()
                try:
                    streams = future.result()
                    print(f">>> Extracted {len(streams) if streams else 0} streams from {url}")
                    
                    if not streams:
                        # No streams found - load URL directly in browser mode
                        print(f">>> No streams found - calling load_url_directly()")
                        self.load_url_directly(url)
                        return
                    
                    # Check if we only got browser mode (no extractable streams)
                    non_browser = [s for s in streams if s.get('type') != 'browser']
                    print(f">>> Filtered streams: {len(non_browser)} non-browser, {len(streams)-len(non_browser)} browser-only")
                    
                    if not non_browser:
                        # Only browser mode available - load directly
                        print(f">>> Only browser mode available - calling load_url_directly()")
                        self.load_url_directly(url)
                    else:
                        # Show dialog with extraction results
                        print(f">>> Showing stream selection dialog with {len(non_browser)} streams")
                        self.show_stream_selection_dialog(streams, url)
                        self.status_bar.showMessage(f"Found {len(non_browser)} stream(s)")
                        
                except Exception as e:
                    print(f"✗ Extraction error in check_completion: {e}")
                    import traceback
                    traceback.print_exc()
                    # On error, try loading URL directly
                    print(f">>> Failed to extract, calling load_url_directly(): {url}")
                    self.load_url_directly(url)
            else:
                QTimer.singleShot(100, check_completion)
        
        QTimer.singleShot(100, check_completion)
    
    def load_url_directly(self, url: str):
        """Load a URL directly - in browser mode if no streams, or VLC if it's a direct video file."""
        print(f"\n>>> load_url_directly() called with URL: {url}")
        
        # Find first available player
        print(f">>> Looking for available player... (total players: {len(self.players)})")
        available_player = None
        for idx, player in enumerate(self.players):
            print(f"    Player {idx}: current_url={player.current_url}")
            if not player.current_url:
                available_player = player
                print(f"    ✓ Found available player at index {idx}")
                break
        
        if not available_player:
            print(f"✗ No available players found!")
            QMessageBox.warning(self, "Grid Full", "All grid slots are occupied. Please clear a slot first.")
            return
        
        # Check if it's a direct video file
        is_direct_video = any(url.lower().endswith(ext) for ext in ['.mp4', '.webm', '.ogg', '.avi', '.mov', '.flv', '.mkv', '.m3u8', '.ts'])
        print(f">>> is_direct_video={is_direct_video}, WEBENGINE_AVAILABLE={WEBENGINE_AVAILABLE}")
        
        try:
            if is_direct_video or WEBENGINE_AVAILABLE is False:
                # Load in VLC mode
                print(f">>> Loading in VLC mode")
                available_player.load_media(url)
                self.status_bar.showMessage(f"Loading: {url}")
            else:
                # Load in browser mode for web pages
                print(f">>> Loading in browser mode")
                available_player.browser_mode = True
                available_player.mode_stack.setCurrentIndex(1)
                available_player.mode_button.setText("📺")
                available_player.mode_button.setToolTip("Switch to VLC mode")
                available_player.fullscreen_button.setVisible(self.is_single_grid())
                available_player.status_label.setText("🌐")
                available_player.load_url_in_browser(url)
                self.status_bar.showMessage(f"Loading in browser mode: {url}")
            
            print(f"✓ Successfully loaded URL")
        except Exception as e:
            print(f"✗ Error loading URL: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Load Error", f"Failed to load URL: {e}")
    
    def fetch_web_streams(self):
        """Fetch video streams from a web page."""
        url, ok = QInputDialog.getText(
            self, 
            'Fetch Web Video Streams',
            'Enter the web page URL (e.g., https://www.kiiitv.com/tower-cam):'
        )
        
        if ok and url:
            self.status_bar.showMessage("Extracting video streams...")
            
            # Run extraction in background thread
            future = self.thread_pool.submit(self.extractor.extract_streams, url)
            
            # Show progress dialog
            progress = QProgressDialog("Extracting video streams...", "Cancel", 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            # Check for completion
            def check_completion():
                if future.done():
                    progress.close()
                    try:
                        streams = future.result()
                        if streams:
                            self.show_stream_selection_dialog(streams, url)
                            self.status_bar.showMessage("Stream extraction completed")
                        else:
                            # No streams found - offer browser mode option
                            self.handle_no_streams_found(url)
                    except Exception as e:
                        QMessageBox.warning(self, "Extraction Error", f"Failed to extract streams: {e}")
                        self.status_bar.showMessage("Stream extraction failed")
                else:
                    QTimer.singleShot(100, check_completion)
            
            QTimer.singleShot(100, check_completion)
    
    def show_stream_selection_dialog(self, streams: List[Dict[str, str]], source_url: str = None):
        """Show dialog to select which streams to add to the grid."""
        if not streams:
            if source_url:
                self.handle_no_streams_found(source_url)
            else:
                QMessageBox.information(self, "No Streams Found", "No video streams were found on the page.")
            return
        
        # Sort streams by priority: HLS first, then iframes, then others
        priority_order = {'application/x-mpegURL': 0, 'hls': 0, 'iframe_hls': 1, 'iframe': 2, 
                         'html5': 3, 'iframe_video': 4, 'browser': 5}
        streams_sorted = sorted(streams, key=lambda s: (priority_order.get(s.get('type'), 99), streams.index(s)))
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Select Embedded Video ({len(streams_sorted)} found)")
        dialog.setModal(True)
        dialog.resize(1000, 600)
        
        main_layout = QHBoxLayout()
        dialog.setLayout(main_layout)
        
        # Left side - stream list
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel(f"Found {len(streams_sorted)} video source(s). Click to select:"))
        
        # Stream table
        stream_table = QTableWidget()
        stream_table.setColumnCount(3)
        stream_table.setHorizontalHeaderLabels(["#", "Title", "Type"])
        stream_table.setRowCount(len(streams_sorted))
        stream_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        stream_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        stream_table.horizontalHeader().setStretchLastSection(True)
        stream_table.setColumnWidth(0, 40)
        stream_table.setColumnWidth(1, 250)
        
        # Preview VLC player
        preview_widget = QWidget()
        preview_widget.setStyleSheet("background-color: black;")
        preview_widget.setMinimumSize(400, 300)
        
        preview_vlc_instance = vlc.Instance(['--quiet'])
        preview_player = preview_vlc_instance.media_player_new()
        
        if sys.platform.startswith('linux'):
            preview_player.set_xwindow(int(preview_widget.winId()))
        elif sys.platform == "win32":
            preview_player.set_hwnd(int(preview_widget.winId()))
        elif sys.platform == "darwin":
            preview_player.set_nsobject(int(preview_widget.winId()))
        
        # Populate table
        for idx, stream in enumerate(streams_sorted):
            item_num = QTableWidgetItem(str(idx + 1))
            item_title = QTableWidgetItem(stream.get('title', 'Unknown'))
            item_title.setData(Qt.ItemDataRole.UserRole, stream)  # Store stream data
            item_type = QTableWidgetItem(stream.get('type', 'unknown').upper())
            
            # Color code by type
            type_name = stream.get('type', '').lower()
            if 'hls' in type_name or 'mpegURL' in type_name:
                item_title.setForeground(QColor('green'))  # HLS streams in green
            elif 'iframe' in type_name:
                item_title.setForeground(QColor('blue'))   # Iframes in blue
            
            stream_table.setItem(idx, 0, item_num)
            stream_table.setItem(idx, 1, item_title)
            stream_table.setItem(idx, 2, item_type)
        
        # Selection changed handler
        def on_selection_changed():
            current_row = stream_table.currentRow()
            if current_row >= 0:
                title_item = stream_table.item(current_row, 1)
                stream = title_item.data(Qt.ItemDataRole.UserRole)
                stream_url = stream.get('url', '')
                
                # Stop current preview
                preview_player.stop()
                
                # Load and play new stream
                try:
                    if stream_url.startswith(('http://', 'https://')):
                        media = preview_vlc_instance.media_new(stream_url)
                    else:
                        media = preview_vlc_instance.media_new_path(stream_url)
                    
                    preview_player.set_media(media)
                    preview_player.play()
                    preview_player.audio_set_mute(True)  # Mute preview by default
                except Exception as e:
                    print(f"Preview error: {e}")
        
        stream_table.currentCellChanged.connect(lambda: on_selection_changed())
        
        # Double-click to add single stream
        stream_table.itemDoubleClicked.connect(lambda item: self.add_single_stream_from_table(stream_table, dialog))
        
        left_layout.addWidget(stream_table)
        
        for i, stream in enumerate(streams):
            stream_type = stream.get('type', 'unknown')
            stream_url = stream.get('url', '')
            stream_title = stream.get('title', 'Unknown')
            
            # Column 0: Number
            num_item = QTableWidgetItem(str(i + 1))
            num_item.setFlags(num_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            stream_table.setItem(i, 0, num_item)
            
            # Column 1: Title
            title_item = QTableWidgetItem(stream_title)
            title_item.setData(Qt.ItemDataRole.UserRole, stream)
            title_item.setToolTip(stream_url)  # Full URL in tooltip
            title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            stream_table.setItem(i, 1, title_item)
            
            # Column 2: Type
            type_item = QTableWidgetItem(stream_type)
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            stream_table.setItem(i, 2, type_item)
        
        # Auto-select first item
        if stream_table.rowCount() > 0:
            stream_table.selectRow(0)
            QTimer.singleShot(200, on_selection_changed)  # Start preview after dialog shown
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_selected_button = QPushButton("Add Selected")
        add_selected_button.clicked.connect(lambda: self.add_selected_streams_from_table(stream_table, dialog, source_url))
        add_selected_button.setDefault(True)
        button_layout.addWidget(add_selected_button)
        
        add_all_button = QPushButton("Add All")
        add_all_button.clicked.connect(lambda: self.add_all_streams(streams, dialog, source_url))
        button_layout.addWidget(add_all_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(lambda: [preview_player.stop(), dialog.reject()])
        button_layout.addWidget(cancel_button)
        
        left_layout.addLayout(button_layout)
        
        # Right side - video preview
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("📺 Video Preview:"))
        right_layout.addWidget(preview_widget)
        
        preview_info = QLabel("Select a stream to preview")
        preview_info.setStyleSheet("color: gray; padding: 5px;")
        preview_info.setWordWrap(True)
        right_layout.addWidget(preview_info)
        
        # Update preview info when selection changes
        def update_preview_info():
            current_row = stream_table.currentRow()
            if current_row >= 0:
                title_item = stream_table.item(current_row, 1)
                stream = title_item.data(Qt.ItemDataRole.UserRole)
                preview_info.setText(f"URL: {stream.get('url', 'N/A')}\\nType: {stream.get('type', 'unknown')}")
        
        stream_table.currentCellChanged.connect(lambda: update_preview_info())
        
        # Add layouts to main layout
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 1)
        
        # Cleanup on close
        def cleanup():
            preview_player.stop()
            preview_player.release()
        
        dialog.finished.connect(cleanup)
        
        dialog.exec()
    
    def add_single_stream_from_table(self, table: QTableWidget, dialog: QDialog):
        """Add a single stream when double-clicked from table."""
        current_row = table.currentRow()
        if current_row >= 0:
            title_item = table.item(current_row, 1)
            stream = title_item.data(Qt.ItemDataRole.UserRole)
            available_players = [p for p in self.players if not p.current_url]
            
            if available_players:
                player = available_players[0]
                stream_type = stream.get('type', '').lower()
                
                # If it's a browser-mode stream, load in browser mode
                if stream_type == 'browser':
                    player.browser_mode = True
                    player.mode_stack.setCurrentIndex(1)  # Switch to browser view
                    player.mode_button.setStyleSheet("background-color: rgba(150,100,0,200); color: white; border: none; font-size: 10pt;")
                    player.load_url_in_browser(stream['url'])
                else:
                    player.load_media(stream['url'], stream['title'])
                
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "Grid Full", "All grid slots are occupied. Please clear a slot first.")
    
    def add_selected_streams_from_table(self, table: QTableWidget, dialog: QDialog, source_url: str = None):
        """Add selected streams from table to the grid."""
        selected_rows = sorted(set(item.row() for item in table.selectedItems()))
        
        if not selected_rows:
            QMessageBox.information(dialog, "No Selection", "Please select at least one stream.")
            return
        
        available_players = [p for p in self.players if not p.current_url]
        
        for i, row in enumerate(selected_rows):
            if i < len(available_players):
                title_item = table.item(row, 1)
                stream = title_item.data(Qt.ItemDataRole.UserRole)
                player = available_players[i]
                stream_type = stream.get('type', '').lower()
                
                # If it's a browser-mode stream, load in browser mode
                if stream_type == 'browser':
                    player.browser_mode = True
                    player.mode_stack.setCurrentIndex(1)  # Switch to browser view
                    player.mode_button.setStyleSheet("background-color: rgba(150,100,0,200); color: white; border: none; font-size: 10pt;")
                    player.load_url_in_browser(stream['url'])
                else:
                    player.load_media(stream['url'], stream['title'])
                
                # Track source page for token refresh
                if source_url:
                    player.source_page = source_url
        
        dialog.accept()
    
    def add_single_stream(self, item: QListWidgetItem, dialog: QDialog):
        """Add a single stream when double-clicked."""
        stream = item.data(Qt.ItemDataRole.UserRole)
        available_players = [p for p in self.players if not p.current_url]
        
        if available_players:
            player = available_players[0]
            player.load_media(stream['url'], stream['title'])
            dialog.accept()
        else:
            QMessageBox.warning(dialog, "Grid Full", "All grid slots are occupied. Please clear a slot first.")
    
    def add_selected_streams(self, stream_list: QListWidget, dialog: QDialog, source_url: str = None):
        """Add selected streams to the grid."""
        selected_items = stream_list.selectedItems()
        
        if not selected_items:
            QMessageBox.information(dialog, "No Selection", "Please select at least one stream.")
            return
        
        available_players = [p for p in self.players if not p.current_url]
        
        for i, item in enumerate(selected_items):
            if i < len(available_players):
                stream = item.data(Qt.ItemDataRole.UserRole)
                player = available_players[i]
                player.load_media(stream['url'], stream['title'])
                
                # Track source page for token refresh
                if source_url:
                    player.source_page = source_url
        
        dialog.accept()
    
    def add_all_streams(self, streams: List[Dict[str, str]], dialog: QDialog, source_url: str = None):
        """Add all streams to the grid."""
        available_players = [p for p in self.players if not p.current_url]
        
        for i, stream in enumerate(streams):
            if i < len(available_players):
                player = available_players[i]
                player.load_media(stream['url'], stream['title'])
                
                # Track source page for token refresh
                if source_url:
                    player.source_page = source_url
        
        dialog.accept()
    
    def play_all(self):
        """Play all loaded media."""
        for player in self.players:
            if player.current_url:
                player.play()
        self.status_bar.showMessage("Playing all media")
    
    def handle_playback_action(self, text):
        """Handle playback dropdown selection."""
        if "▶ Play" in text:
            self.play_all()
        elif "⏸ Pause" in text:
            self.pause_all()
        elif "⏹ Stop" in text:
            self.stop_all()
        
        # Reset dropdown after action
        QTimer.singleShot(100, lambda: self.playback_combo.setCurrentIndex(-1))
    
    def pause_all(self):
        """Pause all playing media."""
        for player in self.players:
            if player.current_url:
                player.pause()
        self.status_bar.showMessage("Paused all media")
    
    def stop_all(self):
        """Stop all media."""
        for player in self.players:
            if player.current_url:
                player.stop()
        self.status_bar.showMessage("Stopped all media")
    
    def set_volume_all(self, volume: int):
        """Set volume for all players."""
        self.current_volume = volume
        self.volume_label.setText(f"{volume}%")
        
        for player in self.players:
            if player.current_url:
                player.set_volume(volume)
    
    def toggle_control_panel(self):
        """Toggle control panel visibility."""
        self.control_panel_visible = not self.control_panel_visible
        self.control_panel.setVisible(self.control_panel_visible)
        self.toggle_button.setText("▼ Hide Controls" if self.control_panel_visible else "▲ Show Controls")
    
    def handle_no_streams_found(self, url: str):
        """Handle case when no streams are found - offer browser mode option."""
        if not WEBENGINE_AVAILABLE:
            # Fallback to direct URL loading if WebEngine not available
            QMessageBox.information(self, "No Streams Found", 
                "No video streams found. Trying to load URL directly...")
            self.add_url_to_grid(url)
            return
        
        # Create dialog with options
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("No Video Streams Found")
        msg_box.setText("No extractable video streams were found on this page.")
        msg_box.setInformativeText("Would you like to:")
        
        # Add custom buttons
        browser_button = msg_box.addButton("Open in Browser Mode", QMessageBox.ButtonRole.AcceptRole)
        direct_button = msg_box.addButton("Try Direct URL", QMessageBox.ButtonRole.AcceptRole)
        cancel_button = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg_box.setDefaultButton(browser_button)
        msg_box.exec()
        
        if msg_box.clickedButton() == browser_button:
            self.add_url_to_browser_mode(url)
        elif msg_box.clickedButton() == direct_button:
            self.add_url_to_grid(url)
    
    def add_url_to_browser_mode(self, url: str):
        """Add URL to grid in browser mode."""
        # Find first available player
        available_player = None
        for player in self.players:
            if not player.current_url:
                available_player = player
                break
        
        if not available_player:
            QMessageBox.warning(self, "Grid Full", "All grid slots are occupied. Please clear a slot first.")
            return
        
        # Switch player to browser mode and load URL
        available_player.browser_mode = True
        available_player.mode_stack.setCurrentIndex(1)
        available_player.mode_button.setText("📺")
        available_player.mode_button.setToolTip("Switch to VLC mode")
        # Visible only in 1×1 grid
        available_player.fullscreen_button.setVisible(self.is_single_grid())
        available_player.status_label.setText("🌐")
        
        # Load URL in browser
        available_player.load_url_in_browser(url)
        
        self.status_bar.showMessage(f"Loaded in browser mode: {url}")
        print(f"🌐 Added to browser mode: {url}")
    
    def save_state(self):
        """Save current grid state to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Grid State",
            "webgridplayer_state.json",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        state = {
            'grid_size': self.grid_size,
            'volume': self.current_volume,
            'players': []
        }
        
        for i, player in enumerate(self.players):
            if player.current_url:
                player_state = {
                    'index': i,
                    'url': player.current_url,
                    'title': player.url_label.text(),
                    'is_muted': player.is_muted,
                    'start_time': player.start_time,
                    'end_time': player.end_time,
                    'is_clipped': player.is_clipped
                }
                state['players'].append(player_state)
        
        try:
            with open(file_path, 'w') as f:
                json.dump(state, f, indent=2)
            self.status_bar.showMessage(f"State saved to {file_path}")
            QMessageBox.information(self, "Save Successful", f"Grid state saved to:\\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Save Failed", f"Failed to save state: {e}")
    
    def load_state(self):
        """Load grid state from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Grid State",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r') as f:
                state = json.load(f)
            
            # Stop all current players
            self.stop_all()
            
            # Change grid size if needed
            grid_size = tuple(state.get('grid_size', (2, 2)))
            if grid_size != self.grid_size:
                self.grid_size = grid_size
                self.create_grid()
            
            # Set volume
            volume = state.get('volume', 70)
            self.volume_slider.setValue(volume)
            
            # Load player states
            for player_state in state.get('players', []):
                index = player_state.get('index', 0)
                if index < len(self.players):
                    player = self.players[index]
                    url = player_state.get('url', '')
                    title = player_state.get('title', '')
                    
                    # Load media
                    player.load_media(url, title)
                    
                    # Restore mute state
                    if player_state.get('is_muted', False):
                        player.toggle_mute()
                    
                    # Restore clip settings
                    player.start_time = player_state.get('start_time', 0)
                    player.end_time = player_state.get('end_time', 0)
                    player.is_clipped = player_state.get('is_clipped', False)
            
            self.status_bar.showMessage(f"State loaded from {file_path}")
            QMessageBox.information(self, "Load Successful", "Grid state restored successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Load Failed", f"Failed to load state: {e}")
    
    def apply_clip_range(self):
        """Apply clip range to all players."""
        start_time = self.start_time_edit.time()
        end_time = self.end_time_edit.time()
        
        start_seconds = start_time.minute() * 60 + start_time.second()
        end_seconds = end_time.minute() * 60 + end_time.second()
        
        if end_seconds <= start_seconds:
            QMessageBox.warning(self, "Invalid Range", "End time must be greater than start time.")
            return
        
        for player in self.players:
            if player.current_url:
                player.set_clip_range(start_seconds, end_seconds)
        
        self.status_bar.showMessage(f"Applied clip range: {start_seconds}s - {end_seconds}s to all players")
    
    def clear_clip_range(self):
        """Clear clip range for all players."""
        self.start_time_edit.setTime(QTime(0, 0, 0))
        self.end_time_edit.setTime(QTime(0, 0, 0))
        
        for player in self.players:
            player.set_clip_range(0, 0)
        
        self.status_bar.showMessage("Cleared clip range for all players")
    
    def dragEnterEvent(self, event):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        """Handle drop event."""
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                files.append(url.toLocalFile())
        
        if files:
            self.add_files_to_grid(files)
    
    def closeEvent(self, event):
        """Handle application close event."""
        # Stop all players and clean up VLC resources
        for player in self.players:
            if player.media_player:
                player.media_player.stop()
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=False)
        
        event.accept()
    
    def check_stream_refresh(self):
        """Check if any active streams need token refresh."""
        import time
        current_time = time.time()
        
        for player in self.players:
            if not player.current_url or not player.media_player:
                continue
                
            url = player.current_url
            
            # Check if this is a time-sensitive stream (has auth tokens)
            if 'wmsAuthSign=' in url or 'token=' in url:
                # Track this stream
                if url not in self.active_streams:
                    self.active_streams[url] = {
                        'last_refresh': current_time,
                        'original_page': getattr(player, 'source_page', None)
                    }
                    continue
                
                # Check if stream needs refresh (refresh every 25 minutes for 30min tokens)
                last_refresh = self.active_streams[url]['last_refresh']
                if current_time - last_refresh > 1500:  # 25 minutes
                    print(f"🔄 Refreshing time-sensitive stream: {url}")
                    self.refresh_stream_token(player, url)
    
    def refresh_stream_token(self, player, old_url):
        """Refresh a stream with expiring token."""
        source_page = self.active_streams.get(old_url, {}).get('original_page')
        if not source_page:
            print("⚠️  No source page available for token refresh")
            return
            
        print(f"🔄 Extracting fresh streams from: {source_page}")
        
        def refresh_worker():
            try:
                # Re-extract streams from the original page
                streams = self.extractor.extract_streams(source_page)
                
                # Find a new HLS stream (prefer same type as current)
                new_stream = None
                for stream in streams:
                    if stream['type'] == 'iframe_hls' and '.m3u8' in stream['url']:
                        # Check if this is a different URL (fresh token)
                        if stream['url'] != old_url:
                            new_stream = stream
                            break
                
                if new_stream:
                    # Update on main thread
                    QTimer.singleShot(0, lambda: self.apply_stream_refresh(player, new_stream, source_page))
                else:
                    print("⚠️  No fresh stream found for refresh")
                    
            except Exception as e:
                print(f"❌ Error refreshing stream: {e}")
        
        # Run in background
        self.thread_pool.submit(refresh_worker)
    
    def apply_stream_refresh(self, player, new_stream, source_page):
        """Apply refreshed stream to player."""
        import time
        
        old_url = player.current_url
        new_url = new_stream['url']
        
        print(f"✅ Applying refreshed stream: {new_stream['title']}")
        
        # Load new stream
        if player.load_media(new_url, new_stream['title']):
            # Update tracking
            self.active_streams[new_url] = {
                'last_refresh': time.time(),
                'original_page': source_page
            }
            
            # Remove old URL from tracking
            if old_url in self.active_streams:
                del self.active_streams[old_url]
            
            # Store source page reference in player
            player.source_page = source_page
            
            print(f"🎉 Stream refresh successful")


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("WebGridPlayer")
    app.setApplicationVersion("1.0.0")
    
    # Check for VLC
    try:
        vlc_instance = vlc.Instance()
        del vlc_instance
    except Exception as e:
        QMessageBox.critical(None, "VLC Error", 
                           f"VLC media player is not properly installed or configured.\n"
                           f"Please install VLC media player and ensure python-vlc is working.\n"
                           f"Error: {e}")
        return 1
    
    # Create and show main window
    window = WebGridPlayer()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
