#!/usr/bin/env python3
"""
AD-HDTV - A VLC-based multi-video player with web stream extraction capabilities
Author: AD-HDTV Development Team
License: MIT
"""

import sys
import os
import re
import json
import threading
import time
import logging
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from multiprocessing import get_context
from guide import GuideDialog, LogoResolver, build_sample_data

APP_NAME = "AD-HDTV"
LOGGER_NAME = "adhdtv"
ACTION_LOGGER_NAME = "adhdtv.actions"
KNOWN_ERRORS_LOGGER_NAME = "adhdtv.known_errors"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_runtime_path(env_name: str, default_relative: str) -> Path:
    raw_path = os.environ.get(env_name)
    if raw_path:
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
    else:
        path = PROJECT_ROOT / default_relative
    return path.resolve()


STATE_DIR = _resolve_runtime_path("ADHDTV_STATE_DIR", "state")
ASSETS_DIR = _resolve_runtime_path("ADHDTV_ASSETS_DIR", "assets")
LOGS_DIR = _resolve_runtime_path("ADHDTV_LOG_DIR", "logs")
DEFAULT_PREWARM_LIMIT = 8
DEFAULT_PREWARM_DELAY_MS = 1500


def _parse_optional_int_setting(raw_value: Any, default: int) -> int:
    try:
        value = int(raw_value)
        return value if value >= 0 else default
    except Exception:
        return default


def _parse_prewarm_limit(raw_value: Any, default_limit: int = DEFAULT_PREWARM_LIMIT) -> Optional[int]:
    if raw_value is None:
        return default_limit
    text = str(raw_value).strip().lower()
    if not text:
        return default_limit
    if text in {"all", "unlimited"}:
        return None
    if text in {"off", "false", "disabled", "disable"}:
        return 0
    try:
        value = int(text)
        if value < 0:
            return None
        return value
    except Exception:
        return default_limit

try:
    from PyQt6.QtWidgets import *
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *
    try:
        from PyQt6.QtSvg import QSvgRenderer
    except ImportError:
        QSvgRenderer = None
    PYQT_VERSION = 6
    # Detect WebEngine without importing it (importing QtWebEngine is expensive)
    WEBENGINE_AVAILABLE = importlib.util.find_spec('PyQt6.QtWebEngineWidgets') is not None
    QWebEngineView = None
except ImportError:
    try:
        from PyQt5.QtWidgets import *
        from PyQt5.QtCore import *
        from PyQt5.QtGui import *
        try:
            from PyQt5.QtSvg import QSvgRenderer
        except ImportError:
            QSvgRenderer = None
        PYQT_VERSION = 5
        # Detect WebEngine without importing it (importing QtWebEngine is expensive)
        WEBENGINE_AVAILABLE = importlib.util.find_spec('PyQt5.QtWebEngineWidgets') is not None
        QWebEngineView = None
    except ImportError:
        print("Error: PyQt6 or PyQt5 is required. Install with: pip install PyQt6")
        sys.exit(1)


_QWEBENGINEVIEW_CLASS = None


def get_webengine_view_class():
    """Return QWebEngineView class if available, importing it lazily."""
    global _QWEBENGINEVIEW_CLASS, WEBENGINE_AVAILABLE

    if _QWEBENGINEVIEW_CLASS is not None:
        return _QWEBENGINEVIEW_CLASS

    if not WEBENGINE_AVAILABLE:
        return None

    try:
        if PYQT_VERSION == 6:
            from PyQt6.QtWebEngineWidgets import QWebEngineView as _QWebEngineView
        else:
            from PyQt5.QtWebEngineWidgets import QWebEngineView as _QWebEngineView
        _QWEBENGINEVIEW_CLASS = _QWebEngineView
        return _QWEBENGINEVIEW_CLASS
    except Exception:
        WEBENGINE_AVAILABLE = False
        return None

try:
    import vlc
except ImportError:
    print("Error: python-vlc is required. Install with: pip install python-vlc")
    sys.exit(1)

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: requests and beautifulsoup4 are required. Install with: pip install requests beautifulsoup4")
    sys.exit(1)


def _slugify_app_name(app_name: str) -> str:
    safe = app_name.strip().lower().replace(" ", "_")
    return safe or "app"


def setup_logging(app_name: str = APP_NAME, log_level: str = "INFO") -> Tuple[logging.Logger, logging.Logger]:
    """Setup comprehensive logging for AD-HDTV."""
    # Create logs directory
    logs_dir = LOGS_DIR
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup main logger
    logger = logging.getLogger(LOGGER_NAME)
    action_logger = logging.getLogger(ACTION_LOGGER_NAME)
    if getattr(logger, "_adhdtv_configured", False):
        return logger, action_logger

    level = getattr(logging, str(log_level).upper(), logging.INFO)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    for handler in action_logger.handlers[:]:
        action_logger.removeHandler(handler)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # File handler for all logs
    today = datetime.now().strftime("%Y%m%d")
    log_prefix = _slugify_app_name(app_name)
    main_log_file = logs_dir / f"{log_prefix}_{today}.log"
    file_handler = logging.FileHandler(main_log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # File handler for user actions only
    action_log_file = logs_dir / f"user_actions_{today}.log"
    action_handler = logging.FileHandler(action_log_file)
    action_handler.setLevel(logging.INFO)
    action_handler.setFormatter(simple_formatter)
    
    # Create action logger
    action_logger.setLevel(logging.INFO)
    action_logger.addHandler(action_handler)
    action_logger.addHandler(file_handler)  # Also log to main file
    
    # File handler for errors only
    error_log_file = logs_dir / f"errors_{today}.log"
    error_handler = logging.FileHandler(error_log_file)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    # Console handler for important messages
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # Log startup
    logger.info("%s logging system initialized", app_name)
    action_logger.info("Application started")
    logger._adhdtv_configured = True
    return logger, action_logger
    

def _load_logo_pixmap(url: str, target_size: QSize, ua: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) AD-HDTV/1.0") -> Tuple[Optional[QPixmap], str]:
    """Fetch logo from URL (png/jpg/svg) and return (pixmap, error_message)."""
    if not url:
        return None, ""

    def fetch_bytes(candidate_url: str) -> Tuple[Optional[bytes], str]:
        headers = {"User-Agent": ua, "Accept": "image/*,application/xml"}
        try:
            resp = requests.get(candidate_url, headers=headers, timeout=6)
            if resp.ok and resp.content:
                return resp.content, ""
            # Retry allowing insecure if cert issues
            resp = requests.get(candidate_url, headers=headers, timeout=6, verify=False)
            if resp.ok and resp.content:
                return resp.content, ""
            return None, f"HTTP {resp.status_code}"
        except Exception as e:
            return None, str(e)

    candidates = [url]
    if url.lower().endswith('.svg'):
        # Common raster fallback for Wikimedia-style URLs
        candidates.append(url + ".png")
        candidates.append(url.replace('.svg', '.svg.png'))

    last_err = ""
    data = None
    used_url = None
    for cand in candidates:
        data, err = fetch_bytes(cand)
        last_err = err
        used_url = cand
        if data:
            break
    if not data:
        return None, last_err or "No data"

    try:
        if used_url.lower().endswith('.svg') and QSvgRenderer:
            renderer = QSvgRenderer()
            if renderer.load(QByteArray(data)):
                pixmap = QPixmap(target_size)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                renderer.render(painter)
                painter.end()
                return pixmap, ""
        pix = QPixmap()
        pix.loadFromData(data)
        if pix.isNull():
            return None, "Invalid image"
        return pix.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation), ""
    except Exception as e:
        return None, str(e)


def _fallback_text_logo(text: str, target_size: QSize) -> QPixmap:
    """Create a simple text placeholder pixmap when logo fetch fails."""
    pixmap = QPixmap(target_size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.fillRect(pixmap.rect(), QColor(30, 30, 30))
    painter.setPen(QColor(220, 220, 220))
    font = painter.font()
    font.setBold(True)
    font.setPointSize(12)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text[:8] or "?")
    painter.end()
    return pixmap

# Initialize default loggers (configured via setup_logging in app entrypoint)
app_logger = logging.getLogger(LOGGER_NAME)
action_logger = logging.getLogger(ACTION_LOGGER_NAME)

# Known error patterns for automatic recognition
KNOWN_ERRORS = {
    'vlc_init_failed': {
        'patterns': ['vlc.Instance().*failed', 'Media player creation failed', 'Player error #'],
        'category': 'VLC/Player Initialization',
        'severity': 'Critical',
        'solution': 'Use minimal VLC arguments, check widget initialization timing',
        'prevention': 'Test VLC instance creation before use'
    },
    'audio_glitch': {
        'patterns': ['audio.*crackling', 'volume.*pop', 'audio.*distorted'],
        'category': 'Audio Issues', 
        'severity': 'Major',
        'solution': 'Increase buffering, use direct VLC volume control',
        'prevention': 'Test audio settings on target platform'
    },
    'network_timeout': {
        'patterns': ['Connection.*timeout', 'requests.*timeout', 'Stream.*unavailable'],
        'category': 'Network/Streaming',
        'severity': 'Major',
        'solution': 'Increase timeout values, add retry logic',
        'prevention': 'Validate URLs before attempting to load'
    },
    'css_warning': {
        'patterns': ['Unknown property.*box-shadow', 'CSS.*not supported'],
        'category': 'UI/Widget',
        'severity': 'Cosmetic',
        'solution': 'Use Qt-native styling properties',
        'prevention': 'Test CSS on target Qt version'
    },
    'file_permission': {
        'patterns': ['Permission denied', 'Cannot write.*file', 'Directory.*not exist'],
        'category': 'File System',
        'severity': 'Major',
        'solution': 'Check file permissions, create directories',
        'prevention': 'Validate paths and permissions on startup'
    }
}

_STREAM_EXTS = ('.m3u8', '.mp4', '.webm', '.ogg', '.avi', '.mov', '.flv', '.mkv', '.ts')


def _is_playable_stream(url: str, stream_type: str = "") -> bool:
    """Return True when the URL looks directly playable by VLC (not a browser fallback)."""
    if not url:
        return False
    stype = (stream_type or "").lower()
    # Explicit browser fallback should never be treated as playable
    if stype == "browser":
        return False
    url_lower = url.lower()
    if any(url_lower.endswith(ext) for ext in _STREAM_EXTS):
        return True
    if '.m3u8' in url_lower:
        return True
    playable_markers = [
        'hls', 'm3u8', 'jwplayer', 'videojs', 'html5',
        'iframe_hls', 'cdn_stream', 'iframe_video', 'thetvapp_token',
        'application/x-mpegurl'
    ]
    return any(marker in stype for marker in playable_markers)


def _select_best_stream(streams: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Pick the best playable stream from a list, falling back to the first entry."""
    if not streams:
        return None
    for stream in streams:
        if _is_playable_stream(stream.get('url', ''), stream.get('type', '')):
            return stream
    return streams[0]

def classify_error(error_message: str) -> Dict[str, str]:
    """Classify error message against known patterns."""
    import re
    
    error_lower = error_message.lower()
    for error_id, error_info in KNOWN_ERRORS.items():
        for pattern in error_info['patterns']:
            if re.search(pattern.lower(), error_lower):
                return {
                    'error_id': error_id,
                    'category': error_info['category'],
                    'severity': error_info['severity'],
                    'solution': error_info['solution'],
                    'prevention': error_info['prevention']
                }
    
    return {
        'error_id': 'unknown',
        'category': 'Unclassified',
        'severity': 'Unknown',
        'solution': 'Check logs and documentation',
        'prevention': 'Update known error database'
    }

def log_error_with_context(error_message: str, context: str = '', exception: Exception = None) -> None:
    """Log error with automatic classification and context."""
    error_info = classify_error(error_message)
    
    # Format comprehensive error log
    log_entry = f"ERROR DETECTED\n"
    log_entry += f"  Message: {error_message}\n"
    log_entry += f"  Category: {error_info['category']}\n"
    log_entry += f"  Severity: {error_info['severity']}\n"
    log_entry += f"  Solution: {error_info['solution']}\n"
    log_entry += f"  Prevention: {error_info['prevention']}\n"
    
    if context:
        log_entry += f"  Context: {context}\n"
    
    if exception:
        import traceback
        log_entry += f"  Exception: {type(exception).__name__}: {str(exception)}\n"
        log_entry += f"  Traceback: {traceback.format_exc()}\n"
    
    # Log to appropriate handlers
    app_logger.error(log_entry)
    
    # Also create a specific known errors log entry
    known_errors_logger = logging.getLogger(KNOWN_ERRORS_LOGGER_NAME)
    if not known_errors_logger.handlers:
        logs_dir = LOGS_DIR
        logs_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y%m%d")
        known_errors_file = logs_dir / f"known_errors_{today}.log"
        handler = logging.FileHandler(known_errors_file)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        known_errors_logger.addHandler(handler)
        known_errors_logger.setLevel(logging.ERROR)
    
    known_errors_logger.error(f"{error_info['error_id']}: {error_message}")

def log_error_recovery(error_id: str, recovery_action: str) -> None:
    """Log successful error recovery actions."""
    app_logger.info(f"ERROR RECOVERY - {error_id}: {recovery_action}")
    action_logger.info(f"Recovered from {error_id}: {recovery_action}")


class VideoStreamExtractor:
    """Extracts video streams from web pages."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{LOGGER_NAME}.extractor")
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
        self.max_retries = 3
        self.retry_backoff = 2.0  # seconds - increased delay
        self.domain_timeouts = {
            'tvpass.org': 15,     # tvpass pages are JS-heavy but need time to load
            'thetvapp.to': 45,    # thetvapp can be slow, give it more time
        }
        self.fast_token_timeout = 20  # increased timeout
        self.request_delay = 1.0  # Add delay between requests to avoid rate limiting

    def _extract_thetvapp_stream(self, soup: BeautifulSoup, page_url: str) -> List[Dict[str, str]]:
        """Extract TheTVApp tokenized stream URLs if present."""
        streams = []
        stream_node = soup.find(id='stream_name')
        if not stream_node:
            return streams

        stream_name = (stream_node.get('name') or stream_node.get('data-name') or stream_node.text or '').strip()
        if not stream_name:
            self.logger.debug("Stream name element not found or invalid.")
            return streams

        # The token endpoint requires the CSRF token from the page and the session cookies.
        csrf_meta = soup.find('meta', attrs={'name': 'csrf-token'})
        csrf_token = csrf_meta.get('content', '') if csrf_meta else ''
        token_headers = {
            'Referer': page_url,
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        if csrf_token:
            token_headers['X-CSRF-TOKEN'] = csrf_token

        token_url = urljoin(page_url, f"/token/{stream_name}")
        try:
            # Retry logic for slow TheTVApp servers
            max_retries = self.max_retries
            for attempt in range(max_retries):
                try:
                    # Add delay between token requests
                    if attempt > 0:
                        time.sleep(self.request_delay)
                    token_resp = self.session.get(token_url, headers=token_headers, timeout=20)
                    if token_resp.status_code >= 500 and attempt < max_retries - 1:
                        time.sleep(self.retry_backoff * (attempt + 1))
                        continue
                    token_resp.raise_for_status()
                    data = token_resp.json()
                    stream_url = data.get('url') if isinstance(data, dict) else None
                    if not stream_url:
                        self.logger.debug("m3u8 URL not found in the response.")
                        return streams

                    streams.append({
                        'url': stream_url,
                        'type': 'application/x-mpegURL',
                        'title': f'TVApp HLS: {stream_name}'
                    })
                    return streams
                except Exception as e:
                    if attempt < max_retries - 1:
                        self.logger.debug(f"TheTVApp token fetch attempt {attempt + 1} failed, retrying...")
                        continue
                    else:
                        raise
        except Exception as e:
            error_msg = f"Token stream fetch failed from {token_url}"
            log_error_with_context(error_msg, f"Token URL: {token_url}, Stream name: {stream_name}", e)

        return streams

    def extract_streams(self, url: str) -> List[Dict[str, str]]:
        """Extract video streams from a web page.

        Always returns at least a browser-mode fallback entry for JavaScript-heavy sites.
        """
        response = None
        try:
            # JS-heavy sites: return browser mode immediately to avoid useless scraping
            _browser_only_domains = ('tvpass.org', 'kristv.com', 'kiiitv.com', 'ewtn.com')
            if any(d in urlparse(url).netloc for d in _browser_only_domains):
                return [{
                    'url': url,
                    'type': 'browser',
                    'title': f'🌐 Browser Mode - {urlparse(url).netloc}'
                }]

            # Domain-specific timeout/attempt policy
            netloc = urlparse(url).netloc
            base_timeout = self.domain_timeouts.get(netloc, 20)
            max_attempts = 3  # Always retry, especially for thetvapp.to

            # Retry on timeout or server errors
            for attempt in range(max_attempts):
                try:
                    # Add delay between requests to avoid rate limiting
                    if attempt > 0:
                        time.sleep(self.request_delay)
                    response = self.session.get(url, timeout=base_timeout, allow_redirects=True)
                    if response.status_code >= 500 and attempt < max_attempts - 1:
                        time.sleep(self.retry_backoff * (attempt + 1))
                        continue
                    response.raise_for_status()
                    break
                except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
                    if attempt < max_attempts - 1:
                        self.logger.warning(f"Timeout on {url}, retry {attempt+1}/{max_attempts}")
                        time.sleep(self.retry_backoff * (attempt + 1))
                        continue
                    else:
                        raise
            
            soup = BeautifulSoup(response.content, 'html.parser')
            streams = []
            
            self.logger.debug("Extracting from: %s", url)

            # Method -1: Detect Video.js / blob-based playback (requires browser rendering)
            blob_videos = re.findall(r'blob:[a-zA-Z0-9-_:/]+', response.text)
            videojs_present = (
                'video-js' in response.text
                or 'videojs' in response.text.lower()
                or 'vjs' in response.text
            )
            if blob_videos or videojs_present:
                streams.append({
                    'url': url,
                    'type': 'browser',
                    'title': f'🌐 Browser Mode - {urlparse(url).netloc}'
                })

            # Method 0: TheTVApp tokenized stream (jwplayer setup)
            streams.extend(self._extract_thetvapp_stream(soup, url))

            # tvpass pages are JS-app heavy; after primary token check, bail early to browser
            if netloc == 'tvpass.org' and not streams:
                return [{
                    'url': url,
                    'type': 'browser',
                    'title': f'🌐 Browser Mode - {urlparse(url).netloc}'
                }]

            # Method 1: Find iframes with video sources and try to extract from them
            iframes = soup.find_all('iframe')
            self.logger.debug("Found %d iframes", len(iframes))
            for idx, iframe in enumerate(iframes, 1):
                src = iframe.get('src') or iframe.get('data-src') or iframe.get('data-lazy-src')
                if src:
                    abs_src = urljoin(url, src)
                    self.logger.debug("Iframe #%d: %s", idx, abs_src)
                    
                    # Add iframe URL
                    streams.append({
                        'url': abs_src,
                        'type': 'iframe',
                        'title': f'📺 Iframe #{idx}: {urlparse(abs_src).netloc}'
                    })
                    
                    # Try to extract from iframe content
                    try:
                        # Add delay before iframe request
                        time.sleep(self.request_delay)
                        iframe_response = self.session.get(abs_src, timeout=15)
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
                                self.logger.debug("Found video in iframe: %s", v_src)
                        
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
                                self.logger.debug("Found HLS in iframe: %s", m3u8_url)
                    except Exception as e:
                        error_msg = f"Iframe stream extraction failed"
                        log_error_with_context(error_msg, f"Iframe src: {abs_src}", e)
            
            # Method 2: Find HTML5 video tags with all attributes
            video_tags = soup.find_all('video')
            self.logger.debug("Found %d video tags", len(video_tags))
            for idx, video in enumerate(video_tags, 1):
                # Get video ID for better identification
                video_id = video.get('id', f'video-{idx}')
                video_class = video.get('class', [])
                video_class_str = ' '.join(video_class) if isinstance(video_class, list) else str(video_class)
                
                self.logger.debug("Video #%d: id='%s', class='%s'", idx, video_id, video_class_str)
                
                # Check direct src attribute
                src = video.get('src') or video.get('data-src') or video.get('data-video-src')
                if src:
                    self.logger.debug("Video src: %s", src[:100])
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
                        self.logger.debug("Video source[%d]: %s", s_idx, src[:100])
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

            # Fallback: If no extractable streams, offer browser mode
            if not unique_streams:
                unique_streams.append({
                    'url': url,
                    'type': 'browser',
                    'title': f'🌐 Browser Mode - {urlparse(url).netloc}'
                })
            
            return unique_streams
            
        except Exception as e:
            status_code = getattr(response, 'status_code', 'unknown') if response else 'connection_failed'
            error_msg = f"Stream extraction failed from {url}"
            log_error_with_context(error_msg, f"URL: {url}, Status: {status_code}", e)
            # Always return browser mode fallback so channels don't fail completely
            return [{
                'url': url,
                'type': 'browser',
                'title': f'🌐 Browser Mode - {urlparse(url).netloc}'
            }]


def _extract_streams_worker(url: str) -> List[Dict[str, str]]:
    """Helper for ProcessPoolExecutor to keep extraction out of the UI process."""
    extractor = VideoStreamExtractor()
    return extractor.extract_streams(url)


class VideoPlayer(QFrame):
    """Individual video player widget with VLC integration."""
    
    def __init__(self, player_id: int, parent=None):
        super().__init__(parent)
        self.player_id = player_id
        self.display_id = player_id + 1  # 1-based for user-facing labels
        self.media_player = None
        self.media = None
        self.current_url = ""
        self.source_url = ""  # Original webpage URL where stream was extracted from
        self.current_channel_number: Optional[int] = None
        self.start_time = 0
        self.end_time = 0
        self.is_clipped = False
        self.is_solo = False
        
        # Browser mode support
        self.browser_mode = False
        self.web_view = None
        self.video_widget = None
        
        # Smart refresh tracking
        self.refresh_attempt_count = 0
        self.last_refresh_time = 0
        
        # Token refresh tracking (enabled by default for tokenized streams)
        self.token_refresh_enabled = True
        self.token_refresh_timer = None
        # Subtitles
        self.captions_enabled = False
        self._apply_cc_style()

        # Auto-recovery tracking
        self.auto_recovery_enabled = True  # Enable by default
        self.last_known_state = None
        self.consecutive_error_count = 0
        self.max_auto_recovery_attempts = 3
        self.auto_recovery_count = 0
        self.was_playing = False
        self.monitor_timer = None
        
        # Concurrency guards
        self.is_reextracting = False
        self.is_token_refreshing = False

        # Blank/silence detection
        self.blank_check_failures = 0
        self.last_blank_refresh_time = 0
        self.last_media_load_time = 0
        self.last_auto_recovery_time = 0
        self.browser_fallback_attempted = False
        
        self.init_ui()
        # Audio state tracking
        self._manually_muted = False
        self._solo_silenced = False
        self._volume_before_mute = 60
        # VLC is expensive to initialize; create it on first media load.
        self.vlc_instance = None
        self.event_manager = None
    
    def log_event(self, event: str, **kwargs):
        """Standardized logging for player actions.
        Writes to both core and actions loggers with consistent context."""
        logger = logging.getLogger(LOGGER_NAME)
        action_logger = logging.getLogger(ACTION_LOGGER_NAME)
        try:
            context = {
                'player': getattr(self, 'display_id', self.player_id + 1),
                'channel': getattr(self, 'current_channel_number', None),
                'title': self.get_display_text() if hasattr(self, 'get_display_text') else '',
                'url': (self.current_url[:100] + '...') if (self.current_url and len(self.current_url) > 100) else (self.current_url or ''),
                'source_url': getattr(self, 'source_url', '')
            }
            context.update(kwargs or {})
            # Build single-line message
            parts = [f"{event}"] + [f"{k}={v}" for k, v in context.items() if v is not None and v != '']
            msg = " | ".join(parts)
            logger.info(msg)
            action_logger.info(msg)
        except Exception:
            # Fallback minimal log
            logger.info(event)
            action_logger.info(event)
    
    def init_ui(self):
        """Initialize the UI components."""
        self.selected = False
        self.setFrameStyle(QFrame.Shape.NoFrame)
        # Modern sleek styling with rounded corners
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1a1a1a);
                border: 2px solid #444;
                border-radius: 8px;
            }
        """)
        # Keep tiles flexible so the grid can shrink/grow smoothly during window drags
        self.setMinimumSize(160, 120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Enable context menu for this player
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_player_context_menu)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)  # Minimal margins
        layout.setSpacing(0)
        
        # Create stacked widget to switch between VLC and Browser
        self.mode_stack = QStackedWidget()
        
        # VLC video widget
        self.video_widget = QWidget()
        self.video_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a1a, stop:1 #0a0a0a);
                border: none;
                border-radius: 4px;
            }
        """)
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.mode_stack.addWidget(self.video_widget)  # Index 0

        # Browser view is expensive to create; use a placeholder and create WebEngine lazily.
        self.web_view = None
        if WEBENGINE_AVAILABLE:
            web_placeholder_text = "Browser mode ready"
        else:
            web_placeholder_text = (
                "Web browser mode not available\n"
                "(QtWebEngine not installed)\n\n"
                f"Python: {sys.executable}\n"
                f"VIRTUAL_ENV: {os.environ.get('VIRTUAL_ENV', '')}"
            )

        self._web_placeholder = QLabel(web_placeholder_text)
        self._web_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._web_placeholder.setStyleSheet("color: white; background-color: black; padding: 20px;")
        self.mode_stack.addWidget(self._web_placeholder)  # Index 1
        
        layout.addWidget(self.mode_stack, 1)  # Stretch factor 1
        
        # Info panel (compact)
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(2, 2, 2, 2)
        info_layout.setSpacing(2)
        
        # Channel badge (logo + number)
        self.channel_logo_label = QLabel("Logo")
        self.channel_logo_label.setFixedSize(70, 40)
        self.channel_logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.channel_logo_label.setStyleSheet("border: 1px solid #999; background: #e5e5e5; color: #333;")
        self.channel_logo_label.setScaledContents(False)
        # Keep logo imagery small while preserving the original badge footprint
        self.logo_pixmap_size = QSize(45, 26)
        info_layout.addWidget(self.channel_logo_label)

        self.channel_number_label = QLabel("")
        self.channel_number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.channel_number_label.setStyleSheet("color: #5ac8fa; font-weight: bold; font-size: 9pt; padding: 0 2px;")
        self.channel_number_label.setFixedWidth(60)
        info_layout.addWidget(self.channel_number_label)

        # Channel title display (replaces channel-selector combo box)
        self.title_label = QLabel("—")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background: transparent;
                padding: 2px 6px;
                font-size: 10pt;
                font-weight: 500;
            }
        """)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        info_layout.addWidget(self.title_label)
        
        # Modern button styling
        button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a4a4a, stop:1 #3a3a3a);
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 6px;
                font-size: 11pt;
                font-weight: bold;
                padding: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a5a5a, stop:1 #4a4a4a);
                border: 1px solid #666;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a3a, stop:1 #2a2a2a);
            }
        """
        # Reuse styles later
        self.button_style_default = button_style
        self.button_style_cc_on = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5ac8fa, stop:1 #3da9e0);
                color: #0d1b2a;
                border: 1px solid #2d8ccf;
                border-radius: 6px;
                font-size: 11pt;
                font-weight: bold;
                padding: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6ad5ff, stop:1 #4cbcf0);
                border: 1px solid #3097d6;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498db, stop:1 #2c82c1);
            }
        """
        
        # Mode toggle button
        self.mode_button = QPushButton("🎬")
        self.mode_button.setFixedSize(32, 24)
        self.mode_button.setStyleSheet(button_style)
        self.mode_button.clicked.connect(self.toggle_mode)
        self.mode_button.setToolTip("Toggle VLC/Browser mode")
        info_layout.addWidget(self.mode_button)
        
        # Mute button
        self.mute_button = QPushButton("🔊")
        self.mute_button.setFixedSize(32, 24)
        self.mute_button.setStyleSheet(button_style)
        self.mute_button.clicked.connect(self.toggle_mute)
        self.mute_button.setToolTip("Toggle mute")
        self.is_muted = False
        info_layout.addWidget(self.mute_button)

        # Captions (CC) button
        self.cc_button = QPushButton("CC")
        self.cc_button.setFixedSize(32, 24)
        self.cc_button.setStyleSheet(self.button_style_default)
        self.cc_button.clicked.connect(self.toggle_captions)
        self.cc_button.setToolTip("Toggle closed captions (if available)")
        self.captions_enabled = False
        info_layout.addWidget(self.cc_button)

        # Refresh button
        self.refresh_button = QPushButton("🔄")
        self.refresh_button.setFixedSize(32, 24)
        self.refresh_button.setStyleSheet(button_style)
        self.refresh_button.clicked.connect(self.refresh_media)
        self.refresh_button.setToolTip("Refresh this player")
        info_layout.addWidget(self.refresh_button)
        
        # Fullscreen button (for browser mode)
        self.fullscreen_button = QPushButton("⛶")
        self.fullscreen_button.setFixedSize(32, 24)
        self.fullscreen_button.setStyleSheet(button_style)
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)
        self.fullscreen_button.setToolTip("Toggle fullscreen (browser mode)")
        self.fullscreen_button.setVisible(False)  # Hidden by default
        info_layout.addWidget(self.fullscreen_button)
        
        self.status_label = QLabel("⭕")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #ffd700;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(42, 42, 42, 200), stop:1 rgba(26, 26, 26, 200));
                padding: 4px;
                border-radius: 4px;
                font-size: 10pt;
                font-weight: bold;
            }
        """)
        self.status_label.setFixedWidth(45)
        info_layout.addWidget(self.status_label)
        
        layout.addLayout(info_layout)
        self.setLayout(layout)

    def update_channel_list(self):
        """Refresh the title label and channel badge for the current channel."""
        main_window = self.get_main_window()
        if getattr(self, 'current_channel_number', None) is not None and main_window:
            ch = main_window.channels.get(self.current_channel_number)
            if ch:
                self.refresh_channel_badge(self.current_channel_number, ch)
                self.title_label.setText(ch.get('title', str(self.current_channel_number)))

    def set_display_text(self, text: str):
        """Update the title label. Shows channel name when tuned to a channel."""
        if getattr(self, 'current_channel_number', None) is not None:
            main_window = self.get_main_window()
            if main_window:
                ch = main_window.channels.get(self.current_channel_number, {})
                if ch:
                    self.title_label.setText(ch.get('title', str(self.current_channel_number)))
                    self.refresh_channel_badge(self.current_channel_number, ch)
                    return
        self.title_label.setText(text)

    def get_display_text(self) -> str:
        """Return the current title label text."""
        if hasattr(self, 'title_label'):
            text = self.title_label.text()
            if text and text != '—':
                return text
        return self.current_url or ""

    def set_selected(self, selected: bool):
        """Visual highlight for the selected player."""
        self.selected = selected
        self.update_selection_style()
    
    def update_selection_style(self):
        """Update the visual style based on selection status."""
        if hasattr(self, 'selected') and self.selected:
            self.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2a2a2a, stop:1 #1a1a1a);
                    border: 3px solid #4da3ff;
                    border-radius: 8px;
                    box-shadow: 0 0 20px rgba(77, 163, 255, 0.5);
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2a2a2a, stop:1 #1a1a1a);
                    border: 2px solid #444;
                    border-radius: 8px;
                }
            """)

    def refresh_channel_badge(self, channel_num: Optional[int], channel_data: Optional[Dict[str, str]] = None):
        """Update the logo + channel number badge in the player header."""
        if not hasattr(self, 'channel_logo_label'):
            return
        logger = logging.getLogger(LOGGER_NAME)
        main_window = self.get_main_window()
        ch = channel_data
        if not ch and main_window and channel_num is not None:
            ch = main_window.channels.get(channel_num)
        if channel_num:
            self.channel_number_label.setText(f"Ch {channel_num}")
        else:
            self.channel_number_label.setText("")
        pix = None
        logo_path = None
        if ch:
            logo_path = ch.get('logo') or ch.get('logo_path')
        target_size = getattr(self, 'logo_pixmap_size', self.channel_logo_label.size())
        if logo_path:
            try:
                candidates = []
                p = Path(logo_path)
                candidates.append(p)
                if not p.is_absolute():
                    candidates.append(Path.cwd() / logo_path)
                    candidates.append(Path.cwd() / "assets" / "logos" / p.name)
                for cand in candidates:
                    if cand.exists():
                        pixmap = QPixmap(str(cand.resolve()))
                        if not pixmap.isNull():
                            pix = pixmap.scaled(
                                target_size,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                            break
                if pix is None:
                    logger.debug("Logo not loaded for channel %s (candidates tried: %s)", channel_num, candidates)
            except Exception as e:
                logger.debug("Logo load error for channel %s: %s", channel_num, e)
                pix = None
        if not pix:
            # Fallback text badge using channel title or URL
            title_text = ""
            if ch:
                title_text = ch.get('title') or ch.get('source_url') or str(channel_num or "")
            if not title_text:
                title_text = self.current_url or "Channel"
            pix, _ = _load_logo_pixmap("", target_size)
            if not pix:
                pix = _fallback_text_logo(title_text, target_size)
        self.channel_logo_label.setPixmap(pix)

    def show_player_context_menu(self, position):
        """Show right-click context menu for this player."""
        context_menu = QMenu(self)
        
        # URL Management section
        if self.current_url:
            # Save to Channel option (new feature)
            save_channel_action = QAction(f'📺 Save to Channel...', self)
            save_channel_action.triggered.connect(self.save_to_channel)
            context_menu.addAction(save_channel_action)

            edit_channel_action = QAction('✏️ Edit Channel Profile...', self)
            edit_channel_action.triggered.connect(self.edit_channel_profile)
            context_menu.addAction(edit_channel_action)
            
            # Add to Favorites option
            save_fav_action = QAction(f'⭐ Add to Favorites', self)
            save_fav_action.triggered.connect(self.add_to_favorites)
            context_menu.addAction(save_fav_action)
            
            context_menu.addSeparator()
            
            # Original URL settings options
            edit_url_action = QAction(f'✏️ Edit URL...', self)
            edit_url_action.triggered.connect(self.edit_current_url)
            context_menu.addAction(edit_url_action)
            
            reload_url_action = QAction(f'🔄 Reload URL', self)
            reload_url_action.triggered.connect(self.refresh_media)
            context_menu.addAction(reload_url_action)
            
            # Copy URL option
            copy_url_action = QAction(f'📋 Copy URL', self)
            copy_url_action.triggered.connect(self.copy_url)
            context_menu.addAction(copy_url_action)
            
            # Manual re-extraction to refresh tokenized URLs
            if self.source_url:
                refresh_action = QAction('🔁 Refresh from Source', self)
                refresh_action.setToolTip('Re-extract streams from the original page to get a fresh URL/token')
                refresh_action.triggered.connect(self.reextract_from_source)
                context_menu.addAction(refresh_action)
            
            context_menu.addSeparator()
            
            # Add "Load Channel" submenu if channels exist
            main_window = self.get_main_window()
            if main_window and main_window.channels:
                channels_submenu = QMenu('📺 Load Channel', self)
                sorted_channels = sorted(main_window.channels.keys())
                for ch_num in sorted_channels:
                    ch_data = main_window.channels[ch_num]
                    ch_title = ch_data.get('title', str(ch_num))
                    channel_action = QAction(f"Ch {ch_num}: {ch_title}", self)
                    channel_action.triggered.connect(lambda checked=False, num=ch_num: self.load_channel_by_number(num))
                    channels_submenu.addAction(channel_action)
                context_menu.addMenu(channels_submenu)
                context_menu.addSeparator()
            
            # Player controls
            if hasattr(self, 'media_player') and self.media_player:
                play_pause_action = QAction(f'⏯️ Play/Pause', self)
                play_pause_action.triggered.connect(self.toggle_play_pause)
                context_menu.addAction(play_pause_action)
                
                stop_action = QAction(f'⏹️ Stop', self)
                stop_action.triggered.connect(self.stop)
                context_menu.addAction(stop_action)
            
            context_menu.addSeparator()
        else:
            # No URL loaded - show load options
            load_url_action = QAction(f'🌐 Load URL...', self)
            load_url_action.triggered.connect(self.load_url_dialog)
            context_menu.addAction(load_url_action)
            
            load_file_action = QAction(f'📁 Load File...', self)
            load_file_action.triggered.connect(self.load_file_dialog)
            context_menu.addAction(load_file_action)
            
            # Add "Load Channel" submenu if channels exist
            main_window = self.get_main_window()
            if main_window and main_window.channels:
                channels_submenu = QMenu('📺 Load Channel', self)
                sorted_channels = sorted(main_window.channels.keys())
                for ch_num in sorted_channels:
                    ch_data = main_window.channels[ch_num]
                    ch_title = ch_data.get('title', str(ch_num))
                    channel_action = QAction(f"Ch {ch_num}: {ch_title}", self)
                    channel_action.triggered.connect(lambda checked=False, num=ch_num: self.load_channel_by_number(num))
                    channels_submenu.addAction(channel_action)
                context_menu.addMenu(channels_submenu)
            
            context_menu.addSeparator()
        
        # Player management
        if self.current_url:
            # Clear this player
            clear_action = QAction(f'❌ Clear Player', self)
            clear_action.triggered.connect(self.clear_player)
            context_menu.addAction(clear_action)
        
        # Mode switching
        if WEBENGINE_AVAILABLE:
            mode_text = "🎬 Switch to VLC" if self.browser_mode else "🌐 Switch to Browser"
            switch_mode_action = QAction(mode_text, self)
            switch_mode_action.triggered.connect(self.toggle_mode)
            context_menu.addAction(switch_mode_action)
        
        context_menu.exec(self.mapToGlobal(position))
    
    def reextract_from_source(self):
        """Manually re-extract streams from the source_url and load the first candidate."""
        if not self.source_url:
            return
        if self.is_reextracting:
            return
        main_window = self.get_main_window()
        if not main_window:
            return
        logger = logging.getLogger(LOGGER_NAME)
        self.status_label.setText("🔍 Re-extracting...")
        future = main_window.submit_stream_extraction(self.source_url)
        
        def handle_extraction():
            if future.done():
                try:
                    candidate = _select_best_stream(future.result())
                    new_url = candidate.get('url') if candidate else None
                    stream_type = candidate.get('type', '') if candidate else ''
                    title = candidate.get('title', self.get_display_text()) if candidate else self.get_display_text()

                    if new_url and _is_playable_stream(new_url, stream_type):
                        self.log_event('manual_reextract_update')
                        self.load_media(new_url, title=title, source_url=self.source_url)
                        self.status_label.setText("✅ Updated")
                        main_window.status_bar.showMessage(
                            f"Player #{self.player_id + 1}: Loaded fresh stream from source", 3000
                        )
                    elif new_url and WEBENGINE_AVAILABLE:
                        main_window.set_active_player(self)
                        main_window.add_url_to_browser_mode(self.source_url or new_url)
                        self.status_label.setText("🌐 Browser")
                    else:
                        self.status_label.setText("❌ No streams")
                        self.log_event('manual_reextract_empty')
                except Exception as e:
                    self.status_label.setText("❌ Extract failed")
                    self.log_event('manual_reextract_error', error=str(e))
                finally:
                    self.is_reextracting = False
        
        self.is_reextracting = True
        future.add_done_callback(lambda _: QTimer.singleShot(0, handle_extraction))
    
    def save_to_channel(self):
        """Save current URL to a channel number."""
        logger = logging.getLogger(LOGGER_NAME)
        action_logger = logging.getLogger(ACTION_LOGGER_NAME)
        
        if not self.current_url:
            logger.warning(f"Player {self.player_id}: Attempted to save empty URL to channel")
            return
            
        # Get the main window reference
        main_window = self.get_main_window()
        if not main_window:
            logger.error(f"Player {self.player_id}: Could not find main window reference")
            return
            
        # Derive a friendly display title from the title label (falls back to URL)
        display_title = self.get_display_text() or self.current_url
        # Prompt for channel number
        channel_num, ok = QInputDialog.getInt(
            self, 
            'Save to Channel', 
            f'Enter channel number to save this stream:\n\nTitle: {display_title}\nURL: {self.current_url[:50]}...',
            min=1, max=9999, value=1
        )
        
        if ok:
            # Create channel name from the current display text or fallback to the channel number
            channel_name = display_title or f"Channel {channel_num}"

            # Canonical save: persist only the source page URL and title
            channel_data = {'title': channel_name}
            if self.source_url:
                channel_data['source_url'] = self.source_url
            else:
                # Fallback: if no source_url, persist the current input URL as source_url
                channel_data['source_url'] = self.current_url

            # Keep current token URL only in memory, not persisted
            channel_data['url'] = self.current_url

            main_window.channels[channel_num] = channel_data
            main_window._save_channels_to_disk()
            
            # Replace the URL display with the channel name
            self.set_display_text(channel_name)
            
            # Log the action
            self.log_event('save_to_channel', channel=channel_num, name=channel_name)
            
            # Update status
            main_window.status_bar.showMessage(f"Player #{self.player_id + 1} saved as '{channel_name}'")
            self.refresh_channel_badge(channel_num, channel_data)

    def edit_channel_profile(self):
        """Edit or create a channel profile tied to this player."""
        main_window = self.get_main_window()
        if not main_window:
            return
        # Determine defaults
        current_num = getattr(self, 'current_channel_number', None)
        existing = main_window.channels.get(current_num) if current_num else None
        dlg = QDialog(self)
        dlg.setWindowTitle("Edit Channel Profile")
        dlg.resize(700, 540)
        layout = QVBoxLayout(dlg)

        num_input = QLineEdit(str(current_num or ""))
        name_input = QLineEdit(existing.get('title', '') if existing else "")
        url_input = QLineEdit(existing.get('source_url', '') if existing else (self.source_url or self.current_url or ""))
        logo_input = QLineEdit(existing.get('logo', '') if existing else "")
        guide_combo = QComboBox()
        guide_combo.addItem("Unlinked", userData=None)
        guide_data = getattr(main_window, 'guide_data', None)
        guide_map = {}
        if guide_data:
            for ch in guide_data.channels:
                label = f"{ch.number}: {ch.name}" if hasattr(ch, 'number') else ch.name
                guide_combo.addItem(label, userData=ch.id)
                guide_map[ch.id] = label
        # Preselect guide link
        if existing and existing.get('guide_id'):
            idx = guide_combo.findData(existing.get('guide_id'))
            if idx >= 0:
                guide_combo.setCurrentIndex(idx)

        # Logo preview with drag-and-drop
        class LogoDropLabel(QLabel):
            def __init__(self, set_preview, save_logo):
                super().__init__()
                self._set_preview = set_preview
                self._save_logo = save_logo
                self.setAcceptDrops(True)

            def dragEnterEvent(self, event):
                if event.mimeData().hasUrls() or event.mimeData().hasImage():
                    event.acceptProposedAction()
                else:
                    super().dragEnterEvent(event)

            def dropEvent(self, event):
                for url in event.mimeData().urls():
                    local_path = url.toLocalFile()
                    src = local_path or url.toString()
                    saved = self._save_logo(src)
                    if saved:
                        logo_input.setText(saved)
                        self._set_preview(saved)
                    break
                event.acceptProposedAction()

        def set_preview(path: str):
            """Load a preview for local or remote logos without crashing on missing files."""
            logo_preview.setPixmap(QPixmap())
            logo_preview.setText("Drop logo here")
            if not path:
                return

            pix = QPixmap()
            # Support remote logos (e.g., Imgur links) used by some channels
            if path.startswith(("http://", "https://")):
                try:
                    resp = requests.get(path, timeout=6)
                    if resp.ok:
                        pix.loadFromData(resp.content)
                except Exception:
                    pix = QPixmap()  # keep as null if fetch fails

            if pix.isNull():
                p = Path(path)
                candidates = [p]
                if not p.is_absolute():
                    candidates.append(Path.cwd() / p)
                    candidates.append(PROJECT_ROOT / p)
                    candidates.append(Path.cwd() / "assets" / "logos" / p.name)
                    candidates.append(ASSETS_DIR / "logos" / p.name)
                # Do not reference self.status_bar here; this dialog may be constructed before UI init
                for cand in candidates:
                    cand = cand.resolve()
                    if cand.exists():
                        pix = QPixmap(str(cand))
                        if not pix.isNull():
                            break

            if not pix.isNull():
                logo_preview.setPixmap(pix.scaled(logo_preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation))
                logo_preview.setText("")

        def save_logo_to_assets(src: str) -> Optional[str]:
            try:
                logos_dir = ASSETS_DIR / "logos"
                logos_dir.mkdir(parents=True, exist_ok=True)
                ext = Path(src).suffix or ".png"
                base_name = name_input.text().strip() or f"channel_{num_input.text().strip() or 'logo'}"
                safe = "".join(ch if ch.isalnum() else "_" for ch in base_name)
                target = logos_dir / f"{safe}{ext}"
                if src.startswith("http://") or src.startswith("https://"):
                    resp = requests.get(src, timeout=10)
                    resp.raise_for_status()
                    target.write_bytes(resp.content)
                else:
                    target.write_bytes(Path(src).read_bytes())
                return str(target)
            except Exception:
                return None

        logo_preview = LogoDropLabel(set_preview, save_logo_to_assets)
        logo_preview.setFixedSize(220, 130)
        logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_preview.setStyleSheet("border: 1px solid #555; background: #111; color: #777;")
        logo_preview.setText("Drop logo here")

        form_rows = [
            ("Channel Number", num_input),
            ("Name/Title", name_input),
            ("Source URL", url_input),
            ("Logo Path", logo_input),
            ("Guide Link", guide_combo),
        ]
        for label, widget in form_rows:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(widget)
            if label == "Logo Path":
                pick_btn = QPushButton("Browse")
                def pick_logo():
                    path, _ = QFileDialog.getOpenFileName(self, "Choose Logo", "", "Images (*.png *.jpg *.jpeg)")
                    if path:
                        logo_input.setText(path)
                        set_preview(path)
                pick_btn.clicked.connect(pick_logo)
                row.addWidget(pick_btn)
                pick_local_btn = QPushButton("From logos/")
                def pick_local():
                    logos_dir = ASSETS_DIR / "logos"
                    logos_dir.mkdir(parents=True, exist_ok=True)
                    files = list(logos_dir.glob("**/*.[pj][pn]g")) + list(logos_dir.glob("**/*.jpeg"))
                    if not files:
                        QMessageBox.information(dlg, "No logos", f"No logo files found under {logos_dir}.")
                        return
                    chooser = QDialog(dlg)
                    chooser.setWindowTitle("Pick Logo")
                    chooser.resize(480, 360)
                    v = QVBoxLayout(chooser)
                    lw = QListWidget()
                    lw.setIconSize(QSize(140, 70))
                    for f in files:
                        item = QListWidgetItem(f.name)
                        pix = QPixmap(str(f))
                        if not pix.isNull():
                            item.setIcon(QIcon(pix.scaled(lw.iconSize(), Qt.AspectRatioMode.KeepAspectRatio,
                                                          Qt.TransformationMode.SmoothTransformation)))
                        item.setData(Qt.ItemDataRole.UserRole, str(f))
                        lw.addItem(item)
                    v.addWidget(lw)
                    buttons = QHBoxLayout()
                    okb = QPushButton("Select")
                    cancelb = QPushButton("Cancel")
                    buttons.addWidget(okb); buttons.addWidget(cancelb)
                    v.addLayout(buttons)
                    picked = {}
                    def choose():
                        it = lw.currentItem()
                        if it:
                            picked["path"] = it.data(Qt.ItemDataRole.UserRole)
                        chooser.accept()
                    okb.clicked.connect(choose)
                    cancelb.clicked.connect(chooser.reject)
                    lw.itemDoubleClicked.connect(lambda _: choose())
                    if chooser.exec() == QDialog.DialogCode.Accepted and picked.get("path"):
                        logo_input.setText(picked["path"])
                        set_preview(picked["path"])
                pick_local_btn.clicked.connect(pick_local)
                row.addWidget(pick_local_btn)
            layout.addLayout(row)

        # Add preview below logo controls
        preview_row = QHBoxLayout()
        preview_row.addWidget(QLabel("Preview"))
        preview_row.addWidget(logo_preview)
        layout.addLayout(preview_row)
        set_preview(logo_input.text().strip())

        btns = QHBoxLayout()
        ok_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        btns.addWidget(ok_btn); btns.addWidget(cancel_btn)
        layout.addLayout(btns)

        def save():
            try:
                num = int(num_input.text().strip())
            except Exception:
                QMessageBox.warning(dlg, "Invalid", "Channel number must be a number.")
                return
            title = name_input.text().strip() or f"Channel {num}"
            src = url_input.text().strip() or self.current_url or self.source_url or ""
            logo_path = logo_input.text().strip()
            guide_id = guide_combo.currentData()
            entry = {'title': title}
            if src:
                entry['source_url'] = src
            if logo_path:
                entry['logo'] = logo_path
            if guide_id:
                entry['guide_id'] = guide_id
            # Remove old number if changed
            if current_num and current_num != num and current_num in main_window.channels:
                del main_window.channels[current_num]
            main_window.channels[num] = entry
            main_window._save_channels_to_disk()
            self.current_channel_number = num
            self.set_display_text(f"Ch {num}: {title}")
            self.refresh_channel_badge(num, entry)
            dlg.accept()

        ok_btn.clicked.connect(save)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec()
    
    def add_to_favorites(self):
        """Add current URL to favorites."""
        if not self.current_url:
            return
            
        main_window = self.get_main_window()
        if not main_window:
            return
            
        entry = {
            'url': self.current_url,
            'title': self.get_display_text() or self.current_url
        }
        # Include source URL if available for auto-recovery
        if self.source_url:
            entry['source_url'] = self.source_url
        
        # Check for duplicates
        existing_urls = {fav['url'] for fav in main_window.favorites}
        if entry['url'] in existing_urls:
            QMessageBox.information(self, "Already in Favorites", "This URL is already saved to favorites.")
            return
        
        main_window.favorites.append(entry)
        main_window._save_favorites_to_disk()
        main_window.status_bar.showMessage(f"Added to favorites: {entry['title']}")
    
    def copy_url(self):
        """Copy current URL to clipboard."""
        if not self.current_url:
            return
            
        clipboard = QApplication.clipboard()
        clipboard.setText(self.current_url)
        
        main_window = self.get_main_window()
        if main_window:
            main_window.status_bar.showMessage(f"Copied URL to clipboard")
    
    def clear_player(self):
        """Clear this player."""
        self.stop()
        self.current_url = ""
        self.current_channel_number = None
        self.set_display_text("Empty")
        self.status_label.setText("⭕")
        main_window = self.get_main_window()
        if main_window:
            main_window.status_bar.showMessage(f"Cleared Player #{self.player_id + 1}")
    
    def get_main_window(self):
        """Get reference to the main WebGridPlayer window."""
        parent = self.parent()
        while parent:
            if isinstance(parent, WebGridPlayer):
                return parent
            parent = parent.parent()
        return None
    
    def edit_current_url(self):
        """Edit the current URL."""
        if not self.current_url:
            return
            
        new_url, ok = QInputDialog.getText(
            self, 
            'Edit URL', 
            'Edit the current URL:',
            text=self.current_url
        )
        
        if ok and new_url.strip():
            new_url = new_url.strip()
            if new_url != self.current_url:
                # If this is a webpage URL, re-open stream selection and load chosen stream
                if not any(new_url.lower().endswith(ext) for ext in ['.mp4', '.webm', '.ogg', '.avi', '.mov', '.flv', '.mkv', '.m3u8']):
                    main_window = self.get_main_window()
                    if main_window:
                        # Make this the active player for the selection
                        main_window.set_active_player(self)
                        main_window.extract_and_show_streams(new_url)
                    else:
                        # Fallback to loading as-is if main window not found
                        current_title = self.get_display_text()
                        self.load_media(new_url, title=current_title, source_url=self.source_url)
                else:
                    # Direct media URL: load immediately, preserving source_url if any
                    current_title = self.get_display_text()
                    self.load_media(new_url, title=current_title, source_url=self.source_url)
                
                # Log the URL change
                logger = logging.getLogger(LOGGER_NAME)
                action_logger = logging.getLogger(ACTION_LOGGER_NAME)
                self.log_event('edit_url', new_url=new_url)
    
    def toggle_play_pause(self):
        """Toggle play/pause for this player."""
        if self.media_player:
            if self.media_player.is_playing():
                self.pause()
            else:
                self.play()
    
    def load_url_dialog(self):
        """Show dialog to load URL into this specific player."""
        url, ok = QInputDialog.getText(self, 'Load URL', 'Enter video URL or webpage URL:')
        if ok and url.strip():
            url = url.strip()
            # Check if URL is a direct video file
            if any(url.lower().endswith(ext) for ext in ['.mp4', '.webm', '.ogg', '.avi', '.mov', '.flv', '.mkv', '.m3u8']):
                # Direct video - load immediately (no source_url for direct links)
                self.load_media(url, title=None, source_url=None)
            else:
                # Webpage - need to extract streams
                main_window = self.get_main_window()
                if main_window:
                    # Temporarily set this player as active for stream loading
                    original_active = main_window.active_player
                    main_window.set_active_player(self)
                    main_window.extract_and_show_streams(url)
                    # Restore original active player if different
                    if original_active and original_active != self:
                        main_window.set_active_player(original_active)
    
    def load_file_dialog(self):
        """Show dialog to load file into this specific player."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm *.m4v *.3gp);;All Files (*.*)"
        )
        
        if file_path:
            # Local files don't have source URLs
            self.load_media(file_path, title=None, source_url=None)
    
    def load_channel_by_number(self, channel_num: int):
        """Load a specific channel by number into this player."""
        main_window = self.get_main_window()
        if not main_window:
            return
        channel = main_window.channels.get(channel_num)
        if not channel:
            QMessageBox.warning(self, "Channel Not Found", f"Channel {channel_num} is not assigned.")
            return
        
        channel_url = channel.get('url', '')
        cached_type = channel.get('url_type', '')
        channel_expiry_valid = True
        if channel_url and not _is_playable_stream(channel_url, cached_type):
            channel_url = ''
            cached_type = ''
            channel.pop('url', None)
            channel.pop('url_type', None)
        if channel_url and not main_window._is_cached_stream_valid(channel_num):
            # Allow stale-but-usable to start fast, refresh in background
            if main_window._is_cached_stream_stale_but_usable(channel_num):
                channel_expiry_valid = True
                main_window._refresh_channel_in_background(channel_num)
            else:
                channel_expiry_valid = False
                channel_url = ''
                cached_type = ''
                for k in ('url', 'url_type', 'url_expiry'):
                    channel.pop(k, None)
        channel_title = channel.get('title', str(channel_num))
        source_url = channel.get('source_url')
        
        display_title = channel_title
        self.current_channel_number = channel_num

        def load_with_url(url_to_use: str):
            if url_to_use:
                self.load_media(url_to_use, title=display_title, source_url=source_url)
                main_window.status_bar.showMessage(f"Loaded channel {channel_num} into Player #{self.display_id}")
                self.refresh_channel_badge(channel_num, channel)

        if channel_url and channel_expiry_valid:
            load_with_url(channel_url)
        elif source_url:
            # Extract fresh token/URL in background and then load
            self.status_label.setText("🔍 Loading...")
            future = main_window.submit_stream_extraction(source_url)

            def on_done():
                if future.done():
                    try:
                        streams = future.result()
                        candidate = _select_best_stream(streams) if streams else None
                        new_url = candidate.get('url') if candidate else None
                        stream_type = candidate.get('type', '') if candidate else ''

                        if new_url and _is_playable_stream(new_url, stream_type):
                            main_window._cache_channel_stream(channel_num, new_url, stream_type)
                            load_with_url(new_url)
                        elif candidate and WEBENGINE_AVAILABLE:
                            # Fall back to browser mode if that's all we have
                            main_window.set_active_player(self)
                            main_window.add_url_to_browser_mode(source_url or new_url or self.source_url)
                            self.status_label.setText("🌐 Browser")
                        else:
                            QMessageBox.information(self, "No Streams", f"No streams found for Channel {channel_num}.")
                    finally:
                        return

            future.add_done_callback(lambda _: QTimer.singleShot(0, on_done))
        else:
            QMessageBox.warning(self, "Channel Missing URL", f"Channel {channel_num} has no URL or source page.")
    
    def mousePressEvent(self, event):
        """Notify parent when clicked to set active player."""
        # Walk up the parent chain to find the main WebGridPlayer window
        parent_widget = self.parent()
        while parent_widget and not isinstance(parent_widget, WebGridPlayer):
            parent_widget = parent_widget.parent()
        
        if parent_widget and hasattr(parent_widget, 'set_active_player'):
            parent_widget.set_active_player(self)
            
        # Provide visual feedback on click
        self.setStyleSheet("QFrame { border: 2px solid #66d9ff; }")
        QTimer.singleShot(100, lambda: self.update_selection_style())
        
        super().mousePressEvent(event)
    
    def init_vlc(self):
        """Initialize VLC media player."""
        try:
            # Create VLC instance with balanced optimizations (tested and stable)
            vlc_args = [
                '--quiet',                 # Don't print debug messages
                '--no-video-title-show',   # Don't show video title
                '--network-caching=500',   # Reduced caching for faster start (ms)
                '--live-caching=300',      # Lower live cache for responsiveness
                '--http-reconnect',        # Reconnect on HTTP errors
                '--no-stats',              # Disable statistics for performance
                '--no-osd',                # Disable on-screen display
                '--intf=dummy',            # Use dummy interface
                '--verbose=0',             # Minimal verbosity
            ]
            
            # Add conservative platform-specific options (only well-tested ones)
            if sys.platform.startswith('linux'):
                vlc_args.extend([
                    '--no-xlib',
                    '--avcodec-hw=any',        # Try hardware acceleration
                ])
            elif sys.platform == "win32":
                vlc_args.extend([
                    '--avcodec-hw=any',        # Try hardware acceleration on Windows
                ])
            elif sys.platform == "darwin":
                vlc_args.extend([
                    '--avcodec-hw=any',        # Try hardware acceleration on macOS
                ])
            
            self.vlc_instance = vlc.Instance(vlc_args)
            
            if not self.vlc_instance:
                raise Exception("Failed to create VLC instance")
            
            # Create media player
            self.media_player = self.vlc_instance.media_player_new()
            
            if not self.media_player:
                raise Exception("Failed to create VLC media player")
            
            # Set initial volume (use conservative default during init)
            self.media_player.audio_set_volume(60)
            
            # Set the video output to our widget
            if sys.platform.startswith('linux'):
                self.media_player.set_xwindow(int(self.video_widget.winId()))
            elif sys.platform == "win32":
                self.media_player.set_hwnd(int(self.video_widget.winId()))
            elif sys.platform == "darwin":
                self.media_player.set_nsobject(int(self.video_widget.winId()))
            
            # Set up basic event manager
            self.event_manager = self.media_player.event_manager()
            self.event_manager.event_attach(vlc.EventType.MediaPlayerMediaChanged, self._on_media_changed)
            self.event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_media_playing)
            
            # Set up monitoring timer for auto-recovery
            self.monitor_timer = QTimer(self)
            self.monitor_timer.timeout.connect(self._monitor_playback)
            self.monitor_timer.start(15000)  # Check every 15 seconds
            
        except Exception as e:
            error_msg = f"VLC initialization failed for player {self.player_id}"
            log_error_with_context(error_msg, f"Player ID: {self.player_id}, Platform: {sys.platform}", e)
            self.status_label.setText(f"Player error #{self.player_id}")
            # Set fallback state
            self.media_player = None
            self.vlc_instance = None

    def _ensure_vlc(self) -> bool:
        """Ensure VLC instance + media player exist and are bound to the video widget."""
        if self.media_player and self.vlc_instance:
            return True
        self.init_vlc()
        return bool(self.media_player and self.vlc_instance)
    
    def load_media(self, url: str, title: str = None, source_url: str = None):
        """Load media from URL or file path.
        
        Args:
            url: Direct media URL or file path
            title: Optional display title
            source_url: Optional source webpage URL where stream was extracted from
        """
        logger = logging.getLogger(LOGGER_NAME)
        action_logger = logging.getLogger(ACTION_LOGGER_NAME)
        
        try:
            # Lazily initialize VLC on first use
            if not self._ensure_vlc():
                error_msg = f"Media player unavailable for player {self.player_id}"
                log_error_with_context(error_msg, f"URL: {url}, Title: {title}")
                self.status_label.setText("No Player")
                return False
            
            # Ensure we're in VLC mode for media loading
            if self.browser_mode:
                self.browser_mode = False
                self.mode_stack.setCurrentIndex(0)
                self.mode_button.setText("🎬")
                self.mode_button.setToolTip("Switch to browser mode")
                self.fullscreen_button.setVisible(False)
                self.status_label.setText("📺")
                logger.debug(f"Player {self.player_id}: Switched from browser to VLC mode")
                
            previous_url = self.current_url
            self.current_url = url
            try:
                import time
                self.last_media_load_time = time.time()
            except Exception:
                self.last_media_load_time = 0
            if source_url:
                # Store source for smart refresh/token updates
                self.source_url = source_url
                # Backward-compatible alias used by token refresh tracker
                self.source_page = source_url

            # Reset transient audio flags when loading fresh media so it doesn't stay muted
            self._manually_muted = False
            self._solo_silenced = False
            main_window = self.get_main_window()
            if main_window:
                self._volume_before_mute = getattr(main_window, 'current_volume', 60)
            else:
                self._volume_before_mute = 60
            
            # Reset auto-recovery tracking for new media
            self.auto_recovery_count = 0
            self.was_playing = False
            self.consecutive_error_count = 0
            self.blank_check_failures = 0
            self.browser_fallback_attempted = False
            # Reset captions state on new media load
            # Keep user intent: if captions were enabled, try to re-enable on the new stream.
            # We keep the flag and reapply after media is ready.
            if not hasattr(self, 'captions_enabled'):
                self.captions_enabled = False
            self._apply_cc_style()
            
            # Log the media loading attempt
            media_type = "file" if not url.startswith(('http://', 'https://')) else "stream"
            self.log_event('load_media', media_type=media_type)
            
            # Create media with additional options for HLS streams
            if url.startswith(('http://', 'https://')):
                self.media = self.vlc_instance.media_new(url)
                
                # Add specific options for HLS/m3u8 streams - balanced performance
                if '.m3u8' in url.lower():
                    # Use a modern browser UA and include referrer when available
                    self.media.add_option(':http-user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36')
                    
                    # For TheTVApp streams, use TheTVApp domain as referer
                    if 'thetvapp.to' in url:
                        self.media.add_option(':http-referrer=https://thetvapp.to')
                        # Use VLC's native adaptive demuxer (not avformat) — it properly
                        # refreshes the live HLS segment list and handles token URLs.
                        self.media.add_option(':network-caching=3000')
                        self.media.add_option(':live-caching=3000')
                        self.media.add_option(':http-reconnect')
                        self.media.add_option(':http-timeout=60000')
                        logger.info("Applied TheTVApp optimizations for: %s", url[:50])
                    elif self.source_url:
                        self.media.add_option(f':http-referrer={self.source_url}')
                        # Standard HLS caching
                        self.media.add_option(':network-caching=500')     # Slightly higher for token validation
                        self.media.add_option(':live-caching=300')        # Higher live cache for token streams
                        self.media.add_option(':http-reconnect')
                        self.media.add_option(':http-continuous-stream')
                        logger.info("Applied HLS optimizations for: %s", url[:50])
                    else:
                        # Generic HLS
                        self.media.add_option(':network-caching=500')
                        self.media.add_option(':live-caching=300')
                        self.media.add_option(':http-reconnect')
                    
                    # Common options for all HLS
                    self.media.add_option(':avcodec-hw=any')
            else:
                self.media = self.vlc_instance.media_new_path(url)
            
            if not self.media:
                self.status_label.setText("Media Error")
                return False
            
            # Avoid blocking channel changes on a synchronous VLC stop for live streams.
            # `stop()` can hang for many seconds on HLS teardown; swapping media directly
            # is much more responsive for TV-style tuning.
            try:
                if self.media_player:
                    old_is_stream = bool(previous_url and previous_url.startswith(('http://', 'https://')))
                    new_is_stream = bool(url.startswith(('http://', 'https://')))
                    if not (old_is_stream and new_is_stream):
                        self.media_player.stop()
            except Exception:
                pass
            
            # Set media to player
            self.media_player.set_media(self.media)
            
            # Update UI immediately
            display_title = title or os.path.basename(url) if not url.startswith(('http://', 'https://')) else url[:50] + "..." if len(url) > 50 else url
            self.set_display_text(display_title)
            self.status_label.setText("⏳ Loading...")
            
            # Apply audio policy immediately (handles solo/manual mute states)
            self._apply_audio_policy()
            
            # Force UI update
            self.repaint()
            # Update badge if tuned to a channel
            if getattr(self, 'current_channel_number', None) is not None:
                main_window = self.get_main_window()
                ch = None
                if main_window:
                    ch = main_window.channels.get(self.current_channel_number)
                if ch:
                    self.refresh_channel_badge(self.current_channel_number, ch)
            
            # Auto-play after a short delay to ensure media is ready (reduced for faster start)
            QTimer.singleShot(100, self.play)
            # After initial load, verify playback and attempt re-extraction if needed
            QTimer.singleShot(2000, self._check_playback_and_retry)
            # If captions were enabled, attempt to enable first available track shortly after load
            if self.captions_enabled:
                QTimer.singleShot(400, self._enable_preferred_subtitle)

            logger.info("Loading media in VLC player %s: %s", self.player_id, url)
            # If eligible, start token refresh monitoring
            if 'thetvapp.to' in url:
                # Force token refresh enabled for TheTVApp streams (they expire quickly)
                self.token_refresh_enabled = True
            self._maybe_start_token_refresh()
            return True
            
        except Exception as e:
            logger.error("Error loading media %s: %s", url, e)
            self.status_label.setText("Load Error")
            return False
    
    def play(self):
        """Play the media."""
        logger = logging.getLogger(LOGGER_NAME)
        if self.media_player and self.media:
            try:
                result = self.media_player.play()
                if result == 0:  # VLC play() returns 0 on success
                    self.status_label.setText("▶️ Playing")
                    self.was_playing = True  # Mark as playing for monitoring
                    # Enforce current audio policy (solo/manual mute)
                    self._apply_audio_policy()
                    
                    logger.info("Started playing in player %s", self.player_id)
                else:
                    self.status_label.setText("❌ Play Failed") 
                    logger.warning("Play failed for player %s, result: %s", self.player_id, result)
                
                # Handle clipping
                if self.is_clipped and self.start_time > 0:
                    # Wait a bit for the media to start, then seek to start time
                    QTimer.singleShot(100, lambda: self.media_player.set_time(int(self.start_time * 1000)))
            except Exception as e:
                self.status_label.setText("❌ Error")
                logger.error("Error playing media in player %s: %s", self.player_id, e)
        else:
            self.status_label.setText("❌ No Media")
            logger.warning("No media loaded in player %s", self.player_id)
    
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
    
    def cleanup(self):
        """Clean up VLC resources for grid switching."""
        logger = logging.getLogger(LOGGER_NAME)
        try:
            # Stop playback and clear media
            if self.media_player:
                self.media_player.stop()
                
            if self.media:
                self.media.release()
                self.media = None
                
            # Clear state but keep VLC player and instance for reuse
            self.current_url = ""
            self.start_time = 0
            self.end_time = 0
            self.is_clipped = False
            self.set_display_text("Empty")
            self.status_label.setText("Empty")

            # Stop token refresh timer if running
            if hasattr(self, 'token_refresh_timer') and self.token_refresh_timer:
                self.token_refresh_timer.stop()
                self.token_refresh_timer.deleteLater()
                self.token_refresh_timer = None
            
        except Exception as e:
            logger.error("Error during VideoPlayer cleanup for player %s: %s", self.player_id, e)
    
    def destroy_vlc(self):
        """Completely destroy VLC resources when player is being removed permanently."""
        logger = logging.getLogger(LOGGER_NAME)
        try:
            # Stop monitoring timer
            if hasattr(self, 'monitor_timer') and self.monitor_timer:
                self.monitor_timer.stop()
                self.monitor_timer.deleteLater()
                self.monitor_timer = None

            # Stop token refresh timer
            if hasattr(self, 'token_refresh_timer') and self.token_refresh_timer:
                self.token_refresh_timer.stop()
                self.token_refresh_timer.deleteLater()
                self.token_refresh_timer = None
            
            if self.media_player:
                self.media_player.stop()
                
                # Detach from video widget
                if sys.platform.startswith('linux'):
                    self.media_player.set_xwindow(0)
                elif sys.platform == "win32":
                    self.media_player.set_hwnd(0)
                elif sys.platform == "darwin":
                    self.media_player.set_nsobject(0)
                
                # Release VLC objects
                if hasattr(self, 'event_manager') and self.event_manager:
                    try:
                        self.event_manager.event_detach(vlc.EventType.MediaPlayerMediaChanged)
                        self.event_manager.event_detach(vlc.EventType.MediaPlayerPlaying)
                        self.event_manager.event_detach(vlc.EventType.MediaPlayerTimeChanged)
                        self.event_manager.event_detach(vlc.EventType.MediaPlayerPositionChanged)
                    except:
                        pass
                
                self.media_player.release()
                self.media_player = None
            
            if self.media:
                self.media.release()
                self.media = None
                
            if hasattr(self, 'vlc_instance') and self.vlc_instance:
                self.vlc_instance.release()
                self.vlc_instance = None
                
        except Exception as e:
            logger.error("Error destroying VLC for player %s: %s", self.player_id, e)

    def _apply_audio_policy(self):
        """Delegate audio policy enforcement to main window."""
        if not self.media_player:
            return

        main_window = self.get_main_window()
        if main_window and hasattr(main_window, 'enforce_audio_policy'):
            main_window.enforce_audio_policy()
            return

        # Fallback: simple manual mute handling
        manual_muted = getattr(self, '_manually_muted', False)
        target_volume = getattr(self, '_volume_before_mute', 60)
        if manual_muted:
            self.media_player.audio_set_volume(0)
            self.media_player.audio_set_mute(True)
            self.is_muted = True
            self.mute_button.setText("🔇")
        else:
            self.media_player.audio_set_mute(False)
            self.media_player.audio_set_volume(target_volume)
            self.is_muted = False
            self.mute_button.setText("🔊")

    def set_volume(self, volume: int):
        """Set desired volume; actual output follows audio policy."""
        if not self.media_player:
            return
        self._volume_before_mute = volume
        self._apply_audio_policy()

    def toggle_mute(self):
        """Toggle manual mute for this player."""
        if not self.media_player:
            return

        if not hasattr(self, '_volume_before_mute'):
            self._volume_before_mute = self.media_player.audio_get_volume() or 60

        self._manually_muted = not getattr(self, '_manually_muted', False)
        self._apply_audio_policy()

        self.mute_button.setToolTip("Unmute" if self.is_muted else "Mute")

    # ---- Captions / Subtitles ----
    def _first_subtitle_id(self) -> Optional[int]:
        """Return the first available subtitle track id, or None if none."""
        if not self.media_player:
            return None
        try:
            desc = self.media_player.video_get_spu_description()
            if not desc:
                return None
            # desc is list of (id, name)
            for track_id, _name in desc:
                if track_id >= 0:  # libVLC: -1 off, -2 default
                    return track_id
        except Exception:
            return None
        return None

    def _apply_cc_style(self):
        """Apply button style reflecting caption state."""
        if hasattr(self, 'cc_button'):
            self.cc_button.setStyleSheet(
                self.button_style_cc_on if getattr(self, 'captions_enabled', False) else self.button_style_default
            )

    def _on_media_playing(self, event=None):
        """When playback starts, re-apply preferred subtitle track if enabled."""
        if not self.captions_enabled or not self.media_player:
            return
        try:
            track_id = self._first_subtitle_id()
            if track_id is not None:
                self.media_player.video_set_spu(track_id)
        except Exception:
            pass

    def _enable_preferred_subtitle(self):
        """Enable first available subtitle track if captions are desired."""
        if not self.captions_enabled or not self.media_player:
            return
        try:
            track_id = self._first_subtitle_id()
            if track_id is not None:
                self.media_player.video_set_spu(track_id)
        except Exception:
            pass

    def _ensure_captions_active(self):
        """Keep captions on if user enabled them and VLC turned them off."""
        if not self.captions_enabled or not self.media_player:
            return
        try:
            current = self.media_player.video_get_spu()
            if current == -1:
                track_id = self._first_subtitle_id()
                if track_id is not None:
                    self.media_player.video_set_spu(track_id)
        except Exception:
            pass

    def toggle_captions(self):
        """Toggle closed captions/subtitles for this player."""
        if not self.media_player:
            # Allow users to set caption intent before media initializes.
            self.captions_enabled = not getattr(self, 'captions_enabled', False)
            self._apply_cc_style()
            self.status_label.setText("CC?" if self.captions_enabled else "⭕")
            mw = self.get_main_window()
            if mw:
                mw.status_bar.showMessage(
                    f"Player {self.display_id}: Captions {'ON' if self.captions_enabled else 'OFF'} (pending media)"
                )
            return
        try:
            current = self.media_player.video_get_spu()
            if current == -1:
                track_id = self._first_subtitle_id()
                # Even if no track yet, keep intent so we can auto-apply when available
                self.captions_enabled = True
                self.cc_button.setText("CC")
                self._apply_cc_style()
                if track_id is not None:
                    self.media_player.video_set_spu(track_id)
                    self.status_label.setText("CC")
                    mw = self.get_main_window()
                    if mw:
                        mw.status_bar.showMessage(f"Player {self.display_id}: Captions ON (track {track_id})")
                else:
                    self.status_label.setText("CC?")
                    mw = self.get_main_window()
                    if mw:
                        mw.status_bar.showMessage(f"Player {self.display_id}: No captions available (will keep trying)")
            else:
                self.media_player.video_set_spu(-1)
                self.captions_enabled = False
                self.cc_button.setText("CC")
                self._apply_cc_style()
                self.status_label.setText("⭕")
                mw = self.get_main_window()
                if mw:
                    mw.status_bar.showMessage(f"Player {self.display_id}: Captions OFF")
        except Exception:
            self.status_label.setText("Ⓧ")
            mw = self.get_main_window()
            if mw:
                mw.status_bar.showMessage(f"Player {self.display_id}: Caption toggle failed")
    
    def toggle_solo(self):
        """Toggle solo mode for this player (mutes others AND scales to fill grid)."""
        if not self.current_url or not self.media_player:
            return
            
        self.is_solo = not self.is_solo
        main_window = self.get_main_window()
        
        if self.is_solo:
            # Activate solo mode
            self.solo_button.setText("🔥")
            self.solo_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ff6b35, stop:1 #e55a2b);
                    color: #ffffff;
                    border: 1px solid #d14820;
                    border-radius: 6px;
                    font-size: 11pt;
                    font-weight: bold;
                    padding: 2px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ff7b45, stop:1 #f56a3b);
                }
            """)
            self.solo_button.setToolTip("Exit solo mode (scales to full grid)")
            
            if main_window:
                main_window.handle_solo_activated(self)
                main_window.status_bar.showMessage(f"Solo Mode: Player #{self.display_id} - All others muted and hidden")
                
        else:
            # Deactivate solo mode
            self.solo_button.setText("🎯")
            # Reset to default button style
            button_style = """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #4a4a4a, stop:1 #3a3a3a);
                    color: #ffffff;
                    border: 1px solid #555;
                    border-radius: 6px;
                    font-size: 11pt;
                    font-weight: bold;
                    padding: 2px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #5a5a5a, stop:1 #4a4a4a);
                    border: 1px solid #666;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #3a3a3a, stop:1 #2a2a2a);
                }
            """
            self.solo_button.setStyleSheet(button_style)
            self.solo_button.setToolTip("Solo this player (mute all others & scale)")
            
            if main_window:
                main_window.handle_solo_deactivated(self)
                main_window.status_bar.showMessage(f"Solo Mode OFF - All players restored")
        
        # Log the solo action
        logger = logging.getLogger(LOGGER_NAME)
        action_logger = logging.getLogger(ACTION_LOGGER_NAME)
        logger.info(f"Player {self.player_id}: Solo {'activated' if self.is_solo else 'deactivated'}")
        action_logger.info(f"Player {self.player_id}: Solo {'ON' if self.is_solo else 'OFF'}")
    
    def toggle_mode(self):
        """Toggle between VLC and browser mode."""
        if not WEBENGINE_AVAILABLE:
            return
            
        self.browser_mode = not self.browser_mode
        
        if self.browser_mode:
            # Switch to browser mode
            if not self._ensure_web_view():
                self.browser_mode = False
                return
            self.mode_stack.setCurrentIndex(1)
            self.mode_button.setText("📺")
            self.mode_button.setToolTip("Switch to VLC mode")
            self.fullscreen_button.setVisible(True)
            self.status_label.setText("🌐")
            
            # Load current URL in browser if available
            if self.current_url:
                self.load_url_in_browser(self.current_url)
        else:
            # Switch to VLC mode
            self.mode_stack.setCurrentIndex(0)
            self.mode_button.setText("🎬")
            self.mode_button.setToolTip("Switch to browser mode")
            self.fullscreen_button.setVisible(False)
            self.status_label.setText("📺")

    def refresh_media(self):
        """Reload the current URL into this player with smart re-extraction if needed."""
        if not self.current_url:
            self.status_label.setText("⭕")
            return
            
        # For browser mode, simple reload
        if self.browser_mode and self.web_view and WEBENGINE_AVAILABLE:
            self.load_url_in_browser(self.current_url)
            self.status_label.setText("🌐")
            return
        
        # Track refresh attempts
        import time
        current_time = time.time()
        
        # Reset counter if it's been more than 30 seconds since last refresh
        if current_time - self.last_refresh_time > 30:
            self.refresh_attempt_count = 0
        
        self.last_refresh_time = current_time
        self.refresh_attempt_count += 1
        
        # First attempt: Simple refresh (just reload the same URL)
        if self.refresh_attempt_count == 1:
            self.load_media(self.current_url, title=self.get_display_text())
            self.status_label.setText("⟳")
            
            # Check if playback started after 3 seconds
            QTimer.singleShot(3000, self._check_playback_and_retry)
            
        # Second+ attempt: Try re-extraction if we have a source URL
        elif self.source_url:
            self.status_label.setText("🔍 Re-extracting...")
            main_window = self.get_main_window()
            if main_window:
                # Prevent overlapping re-extraction
                if self.is_reextracting:
                    return
                self.is_reextracting = True
                # Store current player info
                current_title = self.get_display_text()
                
                # Try to re-extract streams from source
                self.log_event('smart_reextract_start')
                
                # Run extraction in background
                future = main_window.submit_stream_extraction(self.source_url)
                
                def handle_extraction():
                    if future.done():
                        try:
                            streams = future.result()
                            candidate = _select_best_stream(streams) if streams else None
                            new_url = candidate.get('url') if candidate else None
                            stream_type = candidate.get('type', '') if candidate else ''
                            if candidate and new_url and _is_playable_stream(new_url, stream_type):
                                self.load_media(
                                    new_url,
                                    title=candidate.get('title', current_title),
                                    source_url=self.source_url
                                )
                                self.status_label.setText("🔄 Re-extracted")
                                
                                self.log_event('smart_reextract_success')
                                
                                # Show success message briefly
                                if main_window:
                                    main_window.status_bar.showMessage(
                                        f"Player #{self.player_id + 1}: Found fresh stream from source page", 
                                        3000
                                    )
                            else:
                                # No streams found in re-extraction
                                self.status_label.setText("❌ No streams")
                                self.log_event('smart_reextract_empty')
                                if main_window:
                                    main_window.status_bar.showMessage(
                                        f"Player #{self.player_id + 1}: Could not find new streams", 
                                        3000
                                    )
                        except Exception as e:
                            self.status_label.setText("❌ Extract failed")
                            logger.error(f"Player {self.player_id}: Smart refresh extraction error: {e}")
                        finally:
                            self.is_reextracting = False
                
                future.add_done_callback(lambda _: QTimer.singleShot(0, handle_extraction))
        else:
            # No source URL available, just try regular refresh again
            self.load_media(self.current_url, title=self.get_display_text())
            self.status_label.setText("⟳ Retry")
            
    def _check_playback_and_retry(self):
        """Check if playback started, and trigger re-extraction if not."""
        if self.media_player:
            state = self.media_player.get_state()
            # If stuck opening/buffering too long, treat as failed
            try:
                import time
                if state in [vlc.State.Opening, vlc.State.Buffering]:
                    if self.last_media_load_time and (time.time() - self.last_media_load_time) > 15:
                        if self.source_url:
                            self.refresh_media()
                        return
            except Exception:
                pass

            # If not playing after simple refresh, the stream might be dead
            if state not in [vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering]:
                if self.source_url:
                    logger = logging.getLogger(LOGGER_NAME)
                    # If this is the initial load (no refresh yet), jump to re-extraction path
                    if self.refresh_attempt_count == 0:
                        self.last_refresh_time = time.time()
                        self.refresh_attempt_count = 1  # so refresh_media moves to re-extraction branch
                        logger.info(f"Player {self.player_id}: Initial load failed, attempting smart re-extraction")
                        self.refresh_media()
                    elif self.refresh_attempt_count == 1:
                        logger.info(f"Player {self.player_id}: Simple refresh failed, attempting smart re-extraction")
                        self.refresh_media()
                    elif self.refresh_attempt_count >= 2 and not self.browser_fallback_attempted:
                        # Universal fallback: open source page in browser mode if VLC fails repeatedly
                        if WEBENGINE_AVAILABLE:
                            main_window = self.get_main_window()
                            if main_window:
                                self.browser_fallback_attempted = True
                                main_window.set_active_player(self)
                                main_window.add_url_to_browser_mode(self.source_url)
                                self.status_label.setText("🌐 Browser")
                                main_window.status_bar.showMessage(
                                    f"Player {self.display_id}: VLC failed, opened source in browser mode"
                                )
    
    def _monitor_playback(self):
        """Monitor playback state and auto-recover if stream dies."""
        if not self.auto_recovery_enabled or not self.media_player or not self.current_url:
            return
        
        # Skip monitoring for browser mode or non-stream URLs
        if self.browser_mode or not self.current_url.startswith(('http://', 'https://')):
            return
        
        # Skip if we don't have a source URL to recover from
        if not self.source_url:
            return
        
        try:
            state = self.media_player.get_state()

            # If we're stuck opening/buffering for too long, try recovery
            if state in [vlc.State.Opening, vlc.State.Buffering]:
                try:
                    now = time.time()
                    if self.last_media_load_time and (now - self.last_media_load_time) > 30:
                        if (now - self.last_refresh_time) > 60 and not self.is_reextracting:
                            self.status_label.setText("⏳ Refreshing")
                            self.refresh_media()
                            return
                except Exception:
                    pass

            # Detect persistent blank video while "playing"
            if state == vlc.State.Playing and not self.browser_mode:
                try:
                    width, height = self.media_player.video_get_size(0)
                except Exception:
                    width, height = (1, 1)
                if width == 0 or height == 0:
                    now = time.time()
                    # Avoid aggressive refresh right after load or recent refresh
                    if self.last_media_load_time and (now - self.last_media_load_time) < 12:
                        return
                    if self.last_refresh_time and (now - self.last_refresh_time) < 60:
                        return
                    self.blank_check_failures += 1
                    # Require more consecutive checks + longer cooldown to avoid loops
                    if self.blank_check_failures >= 4 and (now - self.last_blank_refresh_time) > 90:
                        # Trigger a refresh if we appear black for several checks
                        self.last_blank_refresh_time = now
                        self.blank_check_failures = 0
                        if not self.is_reextracting:
                            self.status_label.setText("⬛ Refreshing (blank)")
                            self.refresh_media()
                else:
                    self.blank_check_failures = 0
            
            # Keep captions applied if user wants them
            self._ensure_captions_active()
            
            # Track if we were playing
            if state == vlc.State.Playing:
                self.was_playing = True
                self.consecutive_error_count = 0
                self.last_known_state = state
                return
            
            # Detect if stream died (was playing, now stopped/error)
            # NOTE: State.Ended is normal for HLS live streams between segments - don't treat as failure
            if self.was_playing and state in [vlc.State.Stopped, vlc.State.Error]:
                self.consecutive_error_count += 1
                
                # Only trigger recovery after confirming error persists
                if self.consecutive_error_count >= 2 and self.auto_recovery_count < self.max_auto_recovery_attempts:
                    logger = logging.getLogger(LOGGER_NAME)
                    logger.warning(f"Player {self.player_id}: Stream died (state={state}), attempting auto-recovery")
                    
                    self.auto_recovery_count += 1
                    self.was_playing = False
                    self.consecutive_error_count = 0
                    
                    # Trigger automatic recovery
                    now = time.time()
                    if not self.is_reextracting and (now - self.last_auto_recovery_time) > 90:
                        self.last_auto_recovery_time = now
                        self.auto_recover_stream()
            
            self.last_known_state = state
            
        except Exception as e:
            logger = logging.getLogger(LOGGER_NAME)
            logger.error(f"Player {self.player_id}: Monitor error: {e}")
    
    def auto_recover_stream(self):
        """Automatically attempt to recover a dead stream by re-extracting."""
        if not self.source_url:
            return
        if self.is_reextracting:
            return
        
        logger = logging.getLogger(LOGGER_NAME)
        self.log_event('auto_recover_attempt', attempt=self.auto_recovery_count, max=self.max_auto_recovery_attempts)
        
        self.status_label.setText("🔄 Auto-recovering...")
        
        main_window = self.get_main_window()
        if not main_window:
            return
        
        # Store current title
        current_title = self.get_display_text()
        
        # Run extraction in background
        future = main_window.submit_stream_extraction(self.source_url)
        
        def handle_auto_recovery():
            if future.done():
                try:
                    streams = future.result()
                    candidate = _select_best_stream(streams) if streams else None
                    new_url = candidate.get('url') if candidate else None
                    stream_type = candidate.get('type', '') if candidate else ''
                    if candidate and new_url and _is_playable_stream(new_url, stream_type):
                        self.load_media(
                            new_url,
                            title=candidate.get('title', current_title),
                            source_url=self.source_url
                        )
                        self.status_label.setText("✅ Recovered")
                        
                        self.log_event('auto_recover_success')
                        
                        # Reset recovery counter on success
                        self.auto_recovery_count = 0
                        self.was_playing = False
                        
                        # Show brief notification
                        if main_window:
                            main_window.status_bar.showMessage(
                                f"Player #{self.player_id + 1}: Auto-recovered stream from {urlparse(self.source_url).netloc}", 
                                4000
                            )
                    else:
                        # No streams found
                        self.status_label.setText("❌ Dead stream")
                        self.log_event('auto_recover_empty')
                        
                        if main_window:
                            main_window.status_bar.showMessage(
                                f"Player #{self.player_id + 1}: Could not recover - no streams found", 
                                4000
                            )
                except Exception as e:
                    self.status_label.setText("❌ Recovery failed")
                    logger.error(f"Player {self.player_id}: Auto-recovery error: {e}")
                finally:
                    self.is_reextracting = False
        
        self.is_reextracting = True
        future.add_done_callback(lambda _: QTimer.singleShot(0, handle_auto_recovery))

    def _maybe_start_token_refresh(self):
        """Start a periodic token refresh if conditions suggest tokenized HLS."""
        try:
            if not self.token_refresh_enabled:
                return
            # Require source_url and an HLS stream
            if not self.source_url or not self.current_url:
                return
            if '.m3u8' not in self.current_url.lower():
                return
            # Heuristic: enable if URL has a query string (likely signed or tokenized)
            has_query = '?' in self.current_url
            if not has_query:
                return

            # Create and start timer if not already running
            if not self.token_refresh_timer:
                self.token_refresh_timer = QTimer(self)
                self.token_refresh_timer.timeout.connect(self._token_refresh_tick)
                # 8 minutes: tokens are typically valid 30+ min; re-extract only if needed
                self.token_refresh_timer.start(8 * 60 * 1000)
        except Exception as e:
            logger = logging.getLogger(LOGGER_NAME)
            logger.error(f"Player {self.player_id}: Failed to start token refresh: {e}")

    def _token_refresh_tick(self):
        """Timer tick: re-extract stream and update if tokenized URL changed."""
        try:
            # Preconditions
            if not self.source_url or not self.current_url:
                return
            # Avoid overlapping refresh operations
            if self.is_token_refreshing or self.is_reextracting:
                return

            main_window = self.get_main_window()
            if not main_window:
                return

            logger = logging.getLogger(LOGGER_NAME)
            logger.info(f"Player {self.player_id}: Token refresh tick - checking for updated stream URL")

            # Run extraction in background
            self.is_token_refreshing = True
            future = main_window.submit_stream_extraction(self.source_url)

            def handle_refresh():
                if future.done():
                    try:
                        candidate = _select_best_stream(future.result())
                        new_url = candidate.get('url') if candidate else None
                        stream_type = candidate.get('type', '') if candidate else ''

                        if new_url and _is_playable_stream(new_url, stream_type) and new_url != self.current_url:
                            title = candidate.get('title', self.get_display_text()) if candidate else self.get_display_text()
                            logger.info(f"Player {self.player_id}: Token refresh updating URL")
                            self.load_media(new_url, title=title, source_url=self.source_url)
                            self.status_label.setText("🔁 Token refreshed")
                        elif candidate is None:
                            logger.warning(f"Player {self.player_id}: Token refresh found no streams")
                    except Exception as e:
                        logger.error(f"Player {self.player_id}: Token refresh error: {e}")
                    finally:
                        self.is_token_refreshing = False

            future.add_done_callback(lambda _: QTimer.singleShot(0, handle_refresh))
        except Exception as e:
            logger = logging.getLogger(LOGGER_NAME)
            logger.error(f"Player {self.player_id}: Token refresh tick failed: {e}")

    
    def toggle_fullscreen(self):
        """Toggle fullscreen for browser mode."""
        # Make the player truly fullscreen: cover the desktop, hide overlays
        main_window = self.get_main_window()
        if main_window:
            if main_window.isFullScreen():
                main_window.showNormal()
                self.fullscreen_button.setText("⛶")
                self.fullscreen_button.setToolTip("Enter fullscreen")
                # Restore overlays
                self._set_overlay_visibility(True)
            else:
                main_window.showFullScreen()
                self.fullscreen_button.setText("⛏")
                self.fullscreen_button.setToolTip("Exit fullscreen")
                # Hide overlays
                self._set_overlay_visibility(False)
        else:
            # Fallback: old behavior
            if self.browser_mode and self.web_view and WEBENGINE_AVAILABLE:
                if self.web_view.isFullScreen():
                    self.web_view.showNormal()
                    self.fullscreen_button.setText("⛶")
                    self.fullscreen_button.setToolTip("Enter fullscreen")
                    self._set_overlay_visibility(True)
                else:
                    self.web_view.showFullScreen()
                    self.fullscreen_button.setText("⛏")
                    self.fullscreen_button.setToolTip("Exit fullscreen")
                    self._set_overlay_visibility(False)

    def _set_overlay_visibility(self, visible: bool):
        # Hide/show overlays: logo, channel name, info panel
        if hasattr(self, 'channel_logo_label'):
            self.channel_logo_label.setVisible(visible)
        if hasattr(self, 'channel_number_label'):
            self.channel_number_label.setVisible(visible)
        if hasattr(self, 'title_label'):
            self.title_label.setVisible(visible)
        if hasattr(self, 'mode_button'):
            self.mode_button.setVisible(visible)
        if hasattr(self, 'mute_button'):
            self.mute_button.setVisible(visible)
        if hasattr(self, 'cc_button'):
            self.cc_button.setVisible(visible)
        if hasattr(self, 'refresh_button'):
            self.refresh_button.setVisible(visible)
        if hasattr(self, 'status_label'):
            self.status_label.setVisible(visible)
        if hasattr(self, 'fullscreen_button'):
            # Keep fullscreen button visible only when not in fullscreen
            self.fullscreen_button.setVisible(visible)
    
    def toggle_vlc_fullscreen(self):
        """Toggle VLC's native fullscreen for this player (VLC-style fullscreen)."""
        if not self.media_player:
            return
        try:
            # libvlc has toggle_fullscreen; fall back to set_fullscreen if missing
            if hasattr(self.media_player, "toggle_fullscreen"):
                self.media_player.toggle_fullscreen()
                current = bool(self.media_player.get_fullscreen())
            else:
                current = bool(self.media_player.get_fullscreen())
                self.media_player.set_fullscreen(not current)
                current = not current
            main_window = self.get_main_window()
            if main_window and hasattr(main_window, "status_bar") and main_window.status_bar:
                msg = "Exited VLC fullscreen" if not current else "VLC fullscreen (Press Esc to exit)"
                main_window.status_bar.showMessage(msg)
        except Exception as e:
            # If VLC fullscreen fails, fall back to in-app fullscreen for this player
            logger = logging.getLogger(LOGGER_NAME)
            logger.debug("VLC fullscreen toggle failed: %s", e)
            mw = self.get_main_window()
            if mw and hasattr(mw, "enter_player_fullscreen"):
                mw.enter_player_fullscreen()
    
    def load_url_in_browser(self, url: str):
        """Load URL in browser mode."""
        if not WEBENGINE_AVAILABLE:
            return
        if not self._ensure_web_view():
            return
        self.web_view.setUrl(QUrl(url))
        self.current_url = url
        self.set_display_text(f"Browser: {url}")
        logging.getLogger(LOGGER_NAME).info("Loading in browser: %s", url)

    def _ensure_web_view(self) -> bool:
        """Create QWebEngineView on-demand and swap it into the mode stack."""
        if self.web_view is not None:
            return True

        view_cls = get_webengine_view_class()
        if view_cls is None:
            return False

        try:
            self.web_view = view_cls()
            self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            # Enable fullscreen support for web view
            self.web_view.settings().setAttribute(
                self.web_view.settings().WebAttribute.FullScreenSupportEnabled,
                True,
            )

            # Replace placeholder at index 1
            old = getattr(self, '_web_placeholder', None)
            if old is not None:
                self.mode_stack.removeWidget(old)
                old.deleteLater()
                self._web_placeholder = None
            self.mode_stack.insertWidget(1, self.web_view)
            return True
        except Exception:
            logger = logging.getLogger(LOGGER_NAME)
            logger.exception("Failed to initialize WebEngine view")
            self.web_view = None
            return False
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

class ADHDTVPlayer(QMainWindow):
    """Main application window."""

    def showEvent(self, event):
        super().showEvent(event)
        # On first show, just refresh tile minimums based on the current layout size.
        self._update_tile_min_sizes()
    
    def resizeEvent(self, event):
        """Keep the grid filling the window while the user drags to resize."""
        super().resizeEvent(event)
        # Use timer to ensure layout has updated before recalculating sizes
        QTimer.singleShot(0, self._update_tile_min_sizes)

    def changeEvent(self, event):
        """Handle window state changes like maximize/minimize."""
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            # Update tile sizes when window state changes (maximize/minimize/restore)
            QTimer.singleShot(0, self._update_tile_min_sizes)

    def __init__(self, app_state: Optional[Any] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.app_state = app_state
        self.config = config or {}
        self.logger = logging.getLogger(LOGGER_NAME)
        self.action_logger = logging.getLogger(ACTION_LOGGER_NAME)
        self._prev_window_state = None

        window_geometry = self.config.get("window_geometry", {})
        self.window_title = self.config.get(
            "window_title", f"{APP_NAME} - Multi-Video Player"
        )
        self.window_geometry = {
            "x": int(window_geometry.get("x", 100)),
            "y": int(window_geometry.get("y", 100)),
            "width": int(window_geometry.get("width", 1200)),
            "height": int(window_geometry.get("height", 800)),
        }

        default_grid = self.config.get("default_grid", [1, 1])
        if isinstance(default_grid, (list, tuple)) and len(default_grid) == 2:
            self.grid_size = (int(default_grid[0]), int(default_grid[1]))
        else:
            self.grid_size = (1, 1)
        self.players: List[VideoPlayer] = []
        self.active_player: Optional[VideoPlayer] = None
        self.current_volume = int(self.config.get("default_volume", 70))
        self.extractor = VideoStreamExtractor()
        # Foreground pool handles user-visible actions such as tune/load/recovery.
        pool_workers = int(os.environ.get("ADHDTV_THREAD_WORKERS", 3))
        self.thread_pool = ThreadPoolExecutor(max_workers=pool_workers, thread_name_prefix='webgrid')
        extraction_workers = int(os.environ.get("ADHDTV_EXTRACTION_WORKERS", 2))
        ctx = get_context("spawn")
        self.extractor_pool = ProcessPoolExecutor(
            max_workers=max(1, extraction_workers),
            mp_context=ctx,
        )
        self._prewarm_thread = None
        self._prefetch_pending = set()
        self._idle_refresh_pending = set()
        self._tune_request_id = 0
        self.control_panel_visible = bool(self.config.get("control_panel_visible", True))
        self.control_panel = None
        self.tick_rate_hz = int(self.config.get("tick_rate_hz", 60))
        self.debug_overlay_enabled = bool(self.config.get("debug_overlay", False)) or bool(
            getattr(app_state, "debug", False)
        )
        self.display_mode = self.config.get("display", {}).get("mode", "windowed")
        self.display_resolution = None
        resolution = self.config.get("display", {}).get("resolution")
        if isinstance(resolution, (list, tuple)) and len(resolution) == 2:
            self.display_resolution = (int(resolution[0]), int(resolution[1]))
        
        # Performance monitoring for 8-video optimization
        self.performance_stats = {
            'active_streams': 0,
            'failed_streams': 0,
            'memory_warnings': 0,
            'last_performance_check': 0,
            'last_perf_log': 0
        }
        
        # Performance timer for monitoring 8-video load (will be started after init)
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._monitor_performance)

        self.logger.info("AD-HDTV main window initialized")
        self.action_logger.info("Application window created")
        # Favorites storage
        self.favorites: List[Dict[str, str]] = []  # [{url, title}]
        self.favorites_file = STATE_DIR / "favorites.json"
        self.favorites_file.parent.mkdir(parents=True, exist_ok=True)
        # Playlists storage (named grid snapshots)
        self.playlists: Dict[str, Dict[str, Any]] = {}
        self.playlists_file = STATE_DIR / "playlists.json"
        self.playlists_file.parent.mkdir(parents=True, exist_ok=True)
        # Channel map storage (cable-box style)
        self.channels: Dict[int, Dict[str, str]] = {}  # {number: {url, title}}
        self.channels_file = STATE_DIR / "channels.json"
        self.channels_file.parent.mkdir(parents=True, exist_ok=True)
        self.current_channel: Optional[int] = getattr(app_state, "current_channel", None)
        # Guide assets & data (fixed-size renderer)
        self.guide_logo_resolver = LogoResolver(ASSETS_DIR / "logos")
        self.guide_data = build_sample_data(datetime.now())
        self._guide_fetch_inflight = False
        QTimer.singleShot(0, lambda: self._load_guide_data_async(force=False, on_done=None))
        self._channel_entry_buffer: str = ""
        self._channel_entry_timer = QTimer()
        self._channel_entry_timer.setSingleShot(True)
        self._channel_entry_timer.setInterval(1500)  # 1.5s to commit typed numbers
        self._channel_entry_timer.timeout.connect(self._commit_channel_buffer)
        # Lineup label for user tracking (e.g., "Spectrum Corpus Christi")
        self.channel_lineup_label: str = self.config.get("channels", {}).get(
            "lineup_label", ""
        )
        # Player fullscreen (single video) state
        self._player_fullscreen_active = False
        self._player_fullscreen_restore = {}
        
        # Track time-sensitive streams for refresh
        self.active_streams = {}  # {url: {'last_refresh': timestamp, 'original_url': url}}
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.check_stream_refresh)
        self.refresh_timer.start(120000)  # Check every 2 minutes
        
        # Background idle channel refresh for faster switching
        # Refreshes cached tokens for channels without active playback
        self.idle_refresh_timer = QTimer()
        self.idle_refresh_timer.timeout.connect(self._refresh_idle_channels)
        self.idle_refresh_timer.start(300000)  # Every 5 minutes, only when idle
        self._last_channel_tune_time = 0

        self.init_ui()
        self._apply_initial_layout()
        self._load_favorites_from_disk()
        self._load_playlists_from_disk()
        self._load_channels_from_disk()
        channel_config = self.config.get("channels", {})
        # Keep startup responsive by warming a small working set unless the user
        # explicitly opts into prewarming everything.
        raw_limit = os.environ.get("ADHDTV_PREWARM_LIMIT", channel_config.get("prewarm_limit"))
        self.prewarm_limit = _parse_prewarm_limit(raw_limit)
        env_prewarm_conc = os.environ.get("ADHDTV_PREWARM_CONCURRENCY")
        if env_prewarm_conc and env_prewarm_conc.isdigit():
            self.prewarm_concurrency = int(env_prewarm_conc)
        else:
            self.prewarm_concurrency = int(channel_config.get("prewarm_concurrency", 3))
        raw_delay = os.environ.get("ADHDTV_PREWARM_DELAY_MS", channel_config.get("prewarm_delay_ms"))
        self.prewarm_delay_ms = _parse_optional_int_setting(raw_delay, DEFAULT_PREWARM_DELAY_MS)
        self.create_grid()
        # Update players with loaded channels after grid is created
        self.update_all_player_channel_lists()
        QTimer.singleShot(self.prewarm_delay_ms, self._start_initial_prewarm)
        
        # Log performance optimization status for 8-video setup
        self.logger.info(f"AD-HDTV initialized for {self.grid_size[0]}x{self.grid_size[1]} grid with performance optimizations")
        if self.grid_size[0] * self.grid_size[1] >= 8:
            self.logger.info("8+ video optimization mode enabled: reduced caching, hardware acceleration, multi-threading")

        # Start performance monitoring now that everything is initialized
        self.performance_timer.start(30000)  # Check every 30 seconds

    def submit_stream_extraction(self, url: str):
        """Run extraction in a thread pool (process pool spawn is unreliable with Qt/VLC imports)."""

        if not url:
            return self.thread_pool.submit(lambda: [])

        return self.thread_pool.submit(_extract_streams_worker, url)

    def _monitor_performance(self):
        """Monitor performance metrics for 8-video optimization."""
        try:
            import time
            
            # Safety check - ensure players list exists
            if not hasattr(self, 'players') or not self.players:
                return
            
            current_time = time.time()
            
            # Count active streams (with safety checks)
            active_count = 0
            failed_count = 0
            
            for p in self.players:
                try:
                    if hasattr(p, 'current_url') and p.current_url and hasattr(p, 'media_player') and p.media_player:
                        active_count += 1
                    if hasattr(p, 'status_label') and p.status_label and '❌' in p.status_label.text():
                        failed_count += 1
                except Exception:
                    pass  # Skip problematic players
            
            self.performance_stats['active_streams'] = active_count
            self.performance_stats['failed_streams'] = failed_count
            self.performance_stats['last_performance_check'] = current_time
            
            # Memory check for 8+ videos
            if active_count >= 8:
                try:
                    import psutil
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    cpu_percent = process.cpu_percent()
                    
                    if memory_mb > 2048:  # 2GB threshold
                        self.performance_stats['memory_warnings'] += 1
                        self.logger.warning(f"High memory usage: {memory_mb:.0f}MB with {active_count} active videos")
                        
                        # Suggest optimization if memory is high
                        if memory_mb > 3072 and active_count >= 8:  # 3GB threshold for 8 videos
                            if hasattr(self, 'status_bar') and self.status_bar:
                                self.status_bar.showMessage(f"⚠️ High memory usage ({memory_mb:.0f}MB) - Consider reducing video quality or count")
                    
                    if cpu_percent > 80:  # High CPU usage
                        self.logger.warning(f"High CPU usage: {cpu_percent:.1f}% with {active_count} active videos")
                    
                    # Log performance stats every 2 minutes when running 8 videos
                    if active_count >= 8 and current_time - self.performance_stats.get('last_perf_log', 0) > 120:
                        self.logger.info(f"8-video performance: {active_count} streams, {memory_mb:.0f}MB RAM, {cpu_percent:.1f}% CPU")
                        self.performance_stats['last_perf_log'] = current_time
                        
                except ImportError:
                    pass  # psutil not available
                except Exception as e:
                    self.logger.debug(f"Performance monitoring error: {e}")
                    
            # Update status bar with stream count for 6+ videos
            if active_count >= 6:
                try:
                    status_msg = f"🎬 {active_count} active streams"
                    if failed_count > 0:
                        status_msg += f" ({failed_count} failed)"
                    if hasattr(self, 'status_bar') and self.status_bar:
                        current_msg = self.status_bar.currentMessage()
                        if not current_msg or "streams" not in current_msg:
                            self.status_bar.showMessage(status_msg, 5000)
                except Exception:
                    pass  # Skip status bar updates if there are issues
                    
        except Exception as e:
            # Catch all errors to prevent performance monitoring from crashing the app
            if hasattr(self, 'logger'):
                self.logger.debug(f"Performance monitor error: {e}")
            # Don't re-raise the exception - keep the app running
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle(self.window_title)
        geom = self.window_geometry
        self.setGeometry(geom["x"], geom["y"], geom["width"], geom["height"])
        
        # Load and set application icon
        self._set_application_icon()
        
        # Apply modern dark theme to main window
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2b2b2b, stop:1 #1a1a1a);
                color: #ffffff;
                border: none;
            }
            QWidget {
                background-color: transparent;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QMenuBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a3a, stop:1 #2a2a2a);
                color: #ffffff;
                border: none;
                padding: 4px;
            }
            QMenuBar::item {
                background: transparent;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a9eff, stop:1 #357abd);
            }
            QMenu {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a3a, stop:1 #2a2a2a);
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a9eff, stop:1 #357abd);
            }
            QStatusBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1a1a1a);
                color: #cccccc;
                border-top: 1px solid #555;
                padding: 2px;
            }
        """)
        
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

        # Auto-hide: thin hover-strip at the top so users can reveal the panel by
        # moving the mouse to the very top of the window (like a Windows taskbar).
        self._autohide_pending = False
        self._autohide_delay_timer = QTimer(self)
        self._autohide_delay_timer.setSingleShot(True)
        self._autohide_delay_timer.setInterval(2200)   # ms before hiding
        self._autohide_delay_timer.timeout.connect(self._run_autohide)
        # Poll cursor position every 80 ms — lightweight check
        self._hover_poll_timer = QTimer(self)
        self._hover_poll_timer.setInterval(80)
        self._hover_poll_timer.timeout.connect(self._poll_hover_autohide)
        self._hover_poll_timer.start()

        # Grid container
        self.grid_container = QWidget()
        self.grid_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Initialize grid layout once and reuse to avoid reassign warnings
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(2)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_container.setLayout(self.grid_layout)
        main_layout.addWidget(self.grid_container)
        # Make sure the grid gets nearly all vertical space when resizing
        main_layout.setStretch(0, 0)  # control panel
        main_layout.setStretch(1, 1)  # grid container
        
        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")    
        # Allow resizing from bottom-right via native size grip
        self.status_bar.setSizeGripEnabled(True)

        # Arrow-key navigation for moving the highlighted/active player.
        # Use shortcuts so Up/Down work even when focus is inside child widgets.
        self._selection_nav_shortcuts = []
        for key_name, d_row, d_col in (
            ("Left", 0, -1),
            ("Right", 0, 1),
            ("Up", -1, 0),
            ("Down", 1, 0),
        ):
            sc = QShortcut(QKeySequence(key_name), self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(lambda dr=d_row, dc=d_col: self.move_active_selection(dr, dc))
            self._selection_nav_shortcuts.append(sc)

    def _apply_initial_layout(self):
        if self.display_resolution:
            self.resize(self.display_resolution[0], self.display_resolution[1])
        if not self.control_panel_visible:
            self.control_panel.setVisible(False)
        if self.debug_overlay_enabled:
            self._init_debug_overlay()

    def _init_debug_overlay(self):
        self._debug_timer = QTimer(self)
        self._debug_timer.timeout.connect(self._update_debug_overlay)
        self._debug_timer.start(1000)
        self._update_debug_overlay()

    def _update_debug_overlay(self):
        if not hasattr(self, "status_bar") or not self.status_bar:
            return
        rows, cols = self.grid_size
        active_id = self.active_player.player_id if self.active_player else "None"
        current_channel = self.current_channel if self.current_channel is not None else "None"
        profile = getattr(self.app_state, "profile", "default")
        self.status_bar.showMessage(
            f"Profile: {profile} | Grid: {rows}x{cols} | Active: {active_id} | Channel: {current_channel}",
            0,
        )

    def show_context_menu(self, position):
        """Show context menu on right-click."""
        context_menu = QMenu(self)
        
        context_menu.addAction(QAction('💡 Tip: Right-click video boxes to save to channels', self))
        context_menu.addSeparator()
        
        add_url_action = QAction('➕ Add URL...', self)
        add_url_action.triggered.connect(self.add_url_dialog)
        context_menu.addAction(add_url_action)
        
        add_files_action = QAction('📁 Add Files...', self)
        add_files_action.triggered.connect(self.open_files)
        context_menu.addAction(add_files_action)
        
        fetch_web_action = QAction('🌐 Fetch from Web...', self)
        fetch_web_action.triggered.connect(self.fetch_web_streams)
        context_menu.addAction(fetch_web_action)

        # Channel selector for this window
        channel_action = QAction('📺 Tune Channel...', self)
        channel_action.triggered.connect(self.tune_channel_from_input)
        context_menu.addAction(channel_action)

        ch_up_action = QAction('Channel Up', self)
        ch_up_action.triggered.connect(self.channel_up)
        context_menu.addAction(ch_up_action)

        ch_dn_action = QAction('Channel Down', self)
        ch_dn_action.triggered.connect(self.channel_down)
        context_menu.addAction(ch_dn_action)
        
        if WEBENGINE_AVAILABLE:
            browse_web_action = QAction('🌎 Browse Web Page...', self)
            browse_web_action.triggered.connect(self.browse_web_page)
            context_menu.addAction(browse_web_action)
        
        context_menu.addSeparator()
        
        clear_all_action = QAction('❌ Clear All Players', self)
        clear_all_action.triggered.connect(self.stop_all)
        context_menu.addAction(clear_all_action)
        
        context_menu.exec(self.mapToGlobal(position))        
        # Enable drag and drop
        self.setAcceptDrops(True)
    
    def _set_application_icon(self):
        """Load and set the application icon."""
        try:
            # Try multiple icon locations
            icon_paths = [
                Path(__file__).parent.parent / 'docs' / 'adhdtv.svg',
                Path(__file__).parent.parent / 'adhdtv.svg',
                Path.cwd() / 'docs' / 'adhdtv.svg',
                Path.cwd() / 'adhdtv.svg',
            ]
            
            for icon_path in icon_paths:
                if icon_path.exists():
                    icon = QIcon(str(icon_path))
                    if not icon.isNull():
                        self.setWindowIcon(icon)
                        self.logger.info(f"✅ Application icon loaded from: {icon_path}")
                        return
            
            # If no icon found, create a simple default icon
            pixmap = QPixmap(128, 128)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw a simple blue play button icon
            painter.fillRect(pixmap.rect(), QColor("#2b7fff"))
            pen = QPen(Qt.GlobalColor.white)
            pen.setWidth(3)
            painter.setPen(pen)
            
            # Draw play triangle
            triangle = QPolygon([
                QPoint(40, 30),
                QPoint(40, 98),
                QPoint(100, 64)
            ])
            painter.drawPolygon(triangle)
            painter.fillPath(QPainterPath(triangle), QColor(Qt.GlobalColor.white))
            painter.end()
            
            icon = QIcon(pixmap)
            self.setWindowIcon(icon)
            self.logger.info("✅ Default application icon created (no SVG found)")
            
        except Exception as e:
            self.logger.warning(f"⚠️  Could not load application icon: {e}")
    
    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        open_files_action = QAction('Open Files...', self)
        open_files_action.setShortcut('Ctrl+O')
        open_files_action.triggered.connect(self.open_files)
        file_menu.addAction(open_files_action)
        
        state = self._snapshot_state()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Grid menu
        grid_menu = menubar.addMenu('Grid')
        
        # Simplified grid options: 1, 4, 8, or 6 screens
        grid_options = [
            (1, 1, '1 Screen'),
            (2, 2, '4 Screens (2×2)'),
            (2, 4, '8 Screens (2×4)'),
            (2, 3, '6 Screens (2×3)'),
        ]
        for rows, cols, label in grid_options:
            action = QAction(label, self)
            action.triggered.connect(lambda checked, r=rows, c=cols: self.change_grid_size(r, c))
            grid_menu.addAction(action)

        # Favorites menu
        fav_menu = menubar.addMenu('Favorites')

        add_fav_action = QAction('Add Active to Favorites', self)
        add_fav_action.triggered.connect(self.add_active_to_favorites)
        fav_menu.addAction(add_fav_action)

        pick_fav_action = QAction('Load Favorite...', self)
        pick_fav_action.triggered.connect(self.pick_favorite_and_load)
        fav_menu.addAction(pick_fav_action)

        manage_fav_action = QAction('Manage Favorites...', self)
        manage_fav_action.triggered.connect(self.manage_favorites_dialog)
        fav_menu.addAction(manage_fav_action)

        fav_menu.addSeparator()

        save_fav_action = QAction('Save Favorites', self)
        save_fav_action.triggered.connect(self._save_favorites_to_disk)
        fav_menu.addAction(save_fav_action)

        load_fav_action = QAction('Reload Favorites', self)
        load_fav_action.triggered.connect(self._load_favorites_from_disk)
        fav_menu.addAction(load_fav_action)

        # Playlist menu (aliases state save/load)
        playlist_menu = menubar.addMenu('Playlist')
        save_pl_action = QAction('Save Current as Playlist...', self)
        save_pl_action.setShortcut('Ctrl+Shift+S')
        save_pl_action.triggered.connect(self.save_playlist_prompt)
        playlist_menu.addAction(save_pl_action)

        load_pl_action = QAction('Load Playlist...', self)
        load_pl_action.setShortcut('Ctrl+Shift+L')
        load_pl_action.triggered.connect(self.load_playlist_prompt)
        playlist_menu.addAction(load_pl_action)

        delete_pl_action = QAction('Delete Playlist...', self)
        delete_pl_action.triggered.connect(self.delete_playlist_prompt)
        playlist_menu.addAction(delete_pl_action)

        playlist_menu.addSeparator()

        reload_pl_action = QAction('Reload Playlists from Disk', self)
        reload_pl_action.triggered.connect(self._load_playlists_from_disk)
        playlist_menu.addAction(reload_pl_action)

        # Channels menu
        channel_menu = menubar.addMenu('Channels')

        tune_channel_action = QAction('Tune Channel...', self)
        tune_channel_action.setShortcut('Ctrl+T')
        tune_channel_action.triggered.connect(self.tune_channel_from_input)
        channel_menu.addAction(tune_channel_action)

        ch_up_action = QAction('Channel Up', self)
        ch_up_action.setShortcut('Ctrl+Up')
        ch_up_action.triggered.connect(self.channel_up)
        channel_menu.addAction(ch_up_action)

        ch_dn_action = QAction('Channel Down', self)
        ch_dn_action.setShortcut('Ctrl+Down')
        ch_dn_action.triggered.connect(self.channel_down)
        channel_menu.addAction(ch_dn_action)

        channel_menu.addSeparator()

        manage_channels_action = QAction('Manage Channels...', self)
        manage_channels_action.triggered.connect(self.manage_channels_dialog)
        channel_menu.addAction(manage_channels_action)
        
        set_lineup_action = QAction('Set Lineup Label...', self)
        set_lineup_action.triggered.connect(self.set_channel_lineup)
        channel_menu.addAction(set_lineup_action)
        
        reload_channels_action = QAction('Reload Channels', self)
        reload_channels_action.triggered.connect(self._load_channels_from_disk)
        channel_menu.addAction(reload_channels_action)

        refresh_tokens_action = QAction('Refresh All Channel Tokens', self)
        refresh_tokens_action.setToolTip('Re-extract fresh URLs for channels with source pages')
        refresh_tokens_action.triggered.connect(self.refresh_all_channel_tokens)
        channel_menu.addAction(refresh_tokens_action)
        
        # Web menu
        web_menu = menubar.addMenu('Web')
        
        fetch_action = QAction('Fetch from Web Page...', self)
        fetch_action.setShortcut('Ctrl+F')
        fetch_action.triggered.connect(self.fetch_web_streams)
        web_menu.addAction(fetch_action)
        
        # Tools menu for troubleshooting
        tools_menu = menubar.addMenu('Tools')
        

        restore_audio_action = QAction('🔊 Restore All Audio', self)
        restore_audio_action.setToolTip('Emergency fix: Restore audio to all players')
        restore_audio_action.triggered.connect(self.force_audio_restore_all)
        tools_menu.addAction(restore_audio_action)


        # API Server Settings menu entry
        api_server_settings_action = QAction('API Server Settings', self)
        api_server_settings_action.setToolTip('Configure API server address')
        api_server_settings_action.triggered.connect(self.show_api_server_settings_dialog)
        tools_menu.addAction(api_server_settings_action)

        # API Options menu entry
        api_options_action = QAction('API Options', self)
        api_options_action.setToolTip('Show available remote API endpoints')
        api_options_action.triggered.connect(self.show_api_options_dialog)
        tools_menu.addAction(api_options_action)

    def get_api_server_url(self):
        import os
        # Use a config file or environment variable for persistence
        config_path = os.path.expanduser('~/.adhdtv_api_server_url')
        default_url = 'http://localhost:5005'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                url = f.read().strip()
                if url:
                    return url
        return default_url

    def set_api_server_url(self, url):
        import os
        config_path = os.path.expanduser('~/.adhdtv_api_server_url')
        with open(config_path, 'w') as f:
            f.write(url.strip())

    def show_api_server_settings_dialog(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
        dialog = QDialog(self)
        dialog.setWindowTitle('API Server Settings')
        layout = QVBoxLayout()
        label = QLabel('API Server URL:')
        layout.addWidget(label)
        url_edit = QLineEdit()
        url_edit.setText(self.get_api_server_url())
        layout.addWidget(url_edit)
        save_btn = QPushButton('Save')
        save_btn.clicked.connect(lambda: self.save_api_server_url(dialog, url_edit.text()))
        layout.addWidget(save_btn)
        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(dialog.reject)
        layout.addWidget(cancel_btn)
        dialog.setLayout(layout)
        dialog.exec()

    def save_api_server_url(self, dialog, url):
        self.set_api_server_url(url)
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, 'Saved', f'API server URL saved: {url}')
        dialog.accept()

    def show_api_options_dialog(self):
        import requests
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit
        dialog = QDialog(self)
        dialog.setWindowTitle('AD-HDTV Remote API Options')
        layout = QVBoxLayout()
        info_label = QLabel('Fetching API options from /api_options...')
        layout.addWidget(info_label)
        text_area = QTextEdit()
        text_area.setReadOnly(True)
        layout.addWidget(text_area)
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.setLayout(layout)
        api_url = self.get_api_server_url().rstrip('/') + '/api_options'
        try:
            resp = requests.get(api_url, timeout=3)
            if resp.ok:
                options = resp.json().get('api_options', [])
                text = '\n'.join([
                    f"{opt['method']} {opt['endpoint']}: {opt['description']}" for opt in options
                ])
                text_area.setText(text)
                info_label.setText(f'Available API endpoints from {api_url}:')
            else:
                text_area.setText(f'Failed to fetch API options from {api_url}.')
        except Exception as e:
            text_area.setText(f'Error fetching API options from {api_url}: {e}')
        dialog.exec()

        # Guide menu (classic TV listings)
        guide_menu = menubar.addMenu('Guide')
        open_guide_action = QAction('Open TV Guide...', self)
        open_guide_action.setShortcut('Ctrl+G')
        open_guide_action.triggered.connect(self.open_tv_guide_dialog)
        guide_menu.addAction(open_guide_action)

    def create_control_panel(self):
        """Create the control panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.NoFrame)
        panel.setMaximumHeight(120)
        panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a3a, stop:1 #2a2a2a);
                border: none;
                border-radius: 8px;
                margin: 4px;
            }
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                font-size: 11pt;
                border: 2px solid #555;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                color: #4da3ff;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a9eff, stop:1 #357abd);
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5aafff, stop:1 #4585cd);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #357abd, stop:1 #2a6fad);
            }
            QComboBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a4a4a, stop:1 #3a3a3a);
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 10pt;
            }
            QComboBox:hover {
                border: 1px solid #4da3ff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QLineEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a4a4a, stop:1 #3a3a3a);
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 1px solid #4da3ff;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a3a, stop:1 #2a2a2a);
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4da3ff, stop:1 #357abd);
                border: 1px solid #357abd;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5aafff, stop:1 #4585cd);
            }
            QTimeEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a4a4a, stop:1 #3a3a3a);
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 10pt;
            }
            QTimeEdit:focus {
                border: 1px solid #4da3ff;
            }
            QLabel {
                color: #cccccc;
                font-size: 10pt;
            }
        """)
        
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
        
        # Audio Management
        audio_group = QGroupBox("Audio")
        audio_layout = QHBoxLayout()
        audio_group.setLayout(audio_layout)
        
        # Mute all button
        self.mute_all_button = QPushButton("🔇 Mute All")
        self.mute_all_button.clicked.connect(self.mute_all_players)
        audio_layout.addWidget(self.mute_all_button)
        
        # Solo mode - completely isolates audio to selected player
        self.solo_mode_button = QPushButton("🎵 Solo Mode: OFF")
        self.solo_mode_button.clicked.connect(self.toggle_solo_mode)
        self.solo_mode_button.setToolTip("When ON, ONLY selected player has audio - all others completely silenced")
        self.solo_mode_active = False
        audio_layout.addWidget(self.solo_mode_button)
        
        # Fullscreen toggles
        self.app_fullscreen_button = QPushButton("⛶ App Fullscreen")
        self.app_fullscreen_button.setToolTip("Toggle fullscreen for the entire app window")
        self.app_fullscreen_button.clicked.connect(self.toggle_fullscreen_mode)
        audio_layout.addWidget(self.app_fullscreen_button)

        self.player_fullscreen_button = QPushButton("🖥️ Video Fullscreen")
        self.player_fullscreen_button.setToolTip("Show the selected video fullscreen on desktop")
        self.player_fullscreen_button.clicked.connect(self.toggle_player_fullscreen)
        audio_layout.addWidget(self.player_fullscreen_button)
        
        layout.addWidget(audio_group)
        
        # Channels (cable-box style)
        channel_group = QGroupBox("📺 Channels")
        channel_outer = QVBoxLayout()
        channel_group.setLayout(channel_outer)

        # Row 1: number input + nav buttons + Tune
        ch_row1 = QHBoxLayout()
        ch_row1.setSpacing(4)

        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("Ch #")
        self.channel_input.setFixedWidth(56)
        self.channel_input.setStyleSheet("""
            QLineEdit {
                font-size: 13pt;
                font-weight: bold;
                padding: 3px 6px;
                background: #1e1e2e;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 5px;
            }
            QLineEdit:focus { border: 1px solid #4da3ff; }
        """)
        self.channel_input.returnPressed.connect(self.tune_channel_from_input)
        ch_row1.addWidget(self.channel_input)

        tune_btn = QPushButton("⏎ Tune")
        tune_btn.setFixedHeight(30)
        tune_btn.clicked.connect(self.tune_channel_from_input)
        ch_row1.addWidget(tune_btn)

        ch_up_btn = QPushButton("▲")
        ch_up_btn.setFixedSize(30, 30)
        ch_up_btn.setToolTip("Channel Up")
        ch_up_btn.clicked.connect(self.channel_up)
        ch_row1.addWidget(ch_up_btn)

        ch_dn_btn = QPushButton("▼")
        ch_dn_btn.setFixedSize(30, 30)
        ch_dn_btn.setToolTip("Channel Down")
        ch_dn_btn.clicked.connect(self.channel_down)
        ch_row1.addWidget(ch_dn_btn)

        channel_outer.addLayout(ch_row1)

        # Row 2: now-on label + Manage + Guide
        ch_row2 = QHBoxLayout()
        ch_row2.setSpacing(4)

        self.lineup_label = QLabel("")
        self.lineup_label.setStyleSheet("""
            QLabel {
                color: #aaaacc;
                font-size: 9pt;
                padding-left: 2px;
            }
        """)
        self.lineup_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        ch_row2.addWidget(self.lineup_label)

        manage_ch_btn = QPushButton("⚙ Manage")
        manage_ch_btn.setFixedHeight(24)
        manage_ch_btn.setStyleSheet("font-size: 9pt; padding: 2px 6px;")
        manage_ch_btn.clicked.connect(self.manage_channels_dialog)
        ch_row2.addWidget(manage_ch_btn)

        guide_btn = QPushButton("📋 Guide")
        guide_btn.setFixedHeight(24)
        guide_btn.setStyleSheet("font-size: 9pt; padding: 2px 6px;")
        guide_btn.setToolTip("Open TV Guide (fixed 1280x720 grid)")
        guide_btn.clicked.connect(self.open_tv_guide_dialog)
        ch_row2.addWidget(guide_btn)

        channel_outer.addLayout(ch_row2)

        layout.addWidget(channel_group)

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
    
    def _apply_player_size_constraints(self, player: 'VideoPlayer'):
        """Adjust per-tile minimum size based on current grid to improve auto-scaling while resizing."""
        rows, cols = self.grid_size
        base_w, base_h = 320, 240
        min_w = max(120, base_w // max(cols, 1))
        min_h = max(90, base_h // max(rows, 1))
        player.setMinimumSize(min_w, min_h)
        player.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _update_tile_min_sizes(self):
        """Recalculate tile minimum sizes based on current viewport to allow horizontal as well as vertical shrink/grow."""
        if not getattr(self, "players", None) or not getattr(self, "grid_container", None):
            return
        rows, cols = self.grid_size
        if rows <= 0 or cols <= 0:
            return

        spacing_x = max(self.grid_layout.horizontalSpacing() or 0, 0)
        spacing_y = max(self.grid_layout.verticalSpacing() or 0, 0)
        margins = self.grid_layout.contentsMargins()

        available_w = max(
            0,
            self.grid_container.width()
            - margins.left() - margins.right()
            - spacing_x * (cols - 1),
        )
        available_h = max(
            0,
            self.grid_container.height()
            - margins.top() - margins.bottom()
            - spacing_y * (rows - 1),
        )

        per_w = max(96, available_w // max(cols, 1))
        per_h = max(72, available_h // max(rows, 1))

        for player in self.players:
            player.setMinimumSize(per_w, per_h)
            player.updateGeometry()
        
        # Force layout recalculation
        self.grid_layout.invalidate()
        self.grid_container.update()
    
    def create_grid(self):
        """Create the video player grid."""
        try:
            # Snapshot existing player states to preserve streams across resize
            old_states = []
            active_index = None
            if hasattr(self, 'players') and self.players:
                for idx, player in enumerate(self.players):
                    # Prefer channel label if player is tuned to a channel
                    channel_num = getattr(player, 'current_channel_number', None)
                    display_title = player.get_display_text() if hasattr(player, 'get_display_text') else ''
                    if channel_num is not None and self.channels:
                        channel = self.channels.get(channel_num, {})
                        ch_title = channel.get('title', str(channel_num))
                        display_title = f"Ch {channel_num}: {ch_title}"

                    state = {
                        'url': getattr(player, 'current_url', ''),
                        'title': display_title,
                        'source_url': getattr(player, 'source_url', ''),
                        'is_muted': getattr(player, 'is_muted', False),
                        'start_time': getattr(player, 'start_time', 0),
                        'end_time': getattr(player, 'end_time', 0),
                        'is_clipped': getattr(player, 'is_clipped', False),
                        'current_channel_number': channel_num,
                    }
                    old_states.append(state)
                    if self.active_player is player:
                        active_index = idx

            # Light cleanup of existing players (stop playback, clear media)
            if hasattr(self, 'players') and self.players:
                for player in self.players:
                    try:
                        player.cleanup()  # Light cleanup - preserve VLC instances
                    except Exception as e:
                        self.logger.warning("Error cleaning up player %s: %s", player.player_id, e)
            
            # Clear existing grid layout widgets (but reuse the layout instance)
            if hasattr(self, 'grid_layout'):
                for i in reversed(range(self.grid_layout.count())):
                    child = self.grid_layout.itemAt(i).widget()
                    if child:
                        child.setParent(None)
            
            self.players.clear()
            self.active_player = None
            
            # Create players for the grid
            rows, cols = self.grid_size
            player_id = 0
            
            for row in range(rows):
                for col in range(cols):
                    try:
                        player = VideoPlayer(player_id, self)
                        # Verify player was created successfully
                        if player and hasattr(player, 'video_widget'):
                            self._apply_player_size_constraints(player)
                            self.players.append(player)
                            self.grid_layout.addWidget(player, row, col)
                            self.logger.debug(f"Successfully created player {player_id}")
                        else:
                            raise Exception("Player creation returned invalid object")
                        player_id += 1
                    except Exception as e:
                        self.logger.error("Error creating player %s: %s", player_id, e)
                        # Create a more informative error placeholder
                        placeholder = QLabel(f"Player Error #{player_id}\n{str(e)[:50]}...")
                        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        placeholder.setStyleSheet("""
                            QLabel {
                                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #3a1a1a, stop:1 #2a1010);
                                color: #ff6666;
                                border: 2px solid #aa3333;
                                border-radius: 8px;
                                padding: 8px;
                                font-weight: bold;
                            }
                        """)
                        placeholder.setWordWrap(True)
                        self.grid_layout.addWidget(placeholder, row, col)
                        player_id += 1
            
            # Ensure every cell has a widget; fill missing with placeholders
            expected_cells = rows * cols
            current_cells = self.grid_layout.count()
            if current_cells < expected_cells:
                for idx in range(current_cells, expected_cells):
                    row = idx // cols
                    col = idx % cols
                    filler = QLabel("(empty)")
                    filler.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    filler.setStyleSheet("background: #111; color: #888; padding: 6px;")
                    self.grid_layout.addWidget(filler, row, col)
            
            # Make grid cells expand equally
            for i in range(rows):
                self.grid_layout.setRowStretch(i, 1)
            for i in range(cols):
                self.grid_layout.setColumnStretch(i, 1)

            # Recompute minimums against the current viewport so tiles can shrink/grow both horizontally and vertically.
            self._update_tile_min_sizes()

            # Restore previous player states where possible (position-stable)
            for idx, state in enumerate(old_states):
                if idx >= len(self.players):
                    break
                player = self.players[idx]
                if state.get('url'):
                    player.load_media(state.get('url', ''), title=state.get('title', ''), source_url=state.get('source_url'))
                    # Restore channel number if it was tuned to a channel
                    if state.get('current_channel_number') is not None:
                        player.current_channel_number = state.get('current_channel_number')
                        # Rebuild label from channels data if available
                        ch_num = state.get('current_channel_number')
                        channel = self.channels.get(ch_num, {}) if self.channels else {}
                        ch_title = channel.get('title', state.get('title', f"Ch {ch_num}"))
                        player.set_display_text(f"Ch {ch_num}: {ch_title}")
                    if state.get('is_muted', False) != getattr(player, 'is_muted', False):
                        player.toggle_mute()
                    player.start_time = state.get('start_time', 0)
                    player.end_time = state.get('end_time', 0)
                    player.is_clipped = state.get('is_clipped', False)

            # Restore active player if previous index is still valid
            if active_index is not None and active_index < len(self.players):
                self.set_active_player(self.players[active_index])
            elif self.players:
                self.set_active_player(self.players[0])

            # Populate each player's channel dropdown after grid rebuild
            if hasattr(self, 'update_all_player_channel_lists'):
                self.update_all_player_channel_lists()
            
            self.status_bar.showMessage(f"Grid: {rows}×{cols} ({len(self.players)} screens) - Click to select, right-click to save")
            self.logger.info("Successfully created grid: %sx%s with %s players", rows, cols, len(self.players))
            
        except Exception as e:
            self.logger.error("Critical error in create_grid: %s", e)
            self.status_bar.showMessage(f"Error creating grid: {e}")
            # Try to recover by creating a minimal 1x1 grid using existing layout
            try:
                self.grid_size = (1, 1)
                self.players.clear()
                if hasattr(self, 'grid_layout'):
                    for i in reversed(range(self.grid_layout.count())):
                        child = self.grid_layout.itemAt(i).widget()
                        if child:
                            child.setParent(None)
                player = VideoPlayer(0, self)
                self.players.append(player)
                self.grid_layout.addWidget(player, 0, 0)
                self.grid_layout.setRowStretch(0, 1)
                self.grid_layout.setColumnStretch(0, 1)
                self.status_bar.showMessage("Recovered with 1×1 grid")
            except Exception as recovery_error:
                self.logger.error("Failed to recover grid: %s", recovery_error)
                self.status_bar.showMessage("Critical grid error - restart recommended")

    def prewarm_channels(self, limit: int = None):
        """Extract and cache token URLs for channels to accelerate tuning.
        
        Args:
            limit: Maximum channels to prewarm. If None, prewarms ALL channels.
                   If 0, prewarming is disabled for this run.
                   Stores token URLs in-memory under `channels[num]['url']` without persisting to disk.
        
        Parallelizes extraction for faster startup. Runs in a background thread to
        avoid blocking UI during startup.
        """
        if not self.channels:
            return
        if limit == 0:
            self.logger.info("Prewarm disabled for this run")
            return

        if threading.current_thread() is threading.main_thread():
            if self._prewarm_thread and self._prewarm_thread.is_alive():
                return
            self._prewarm_thread = threading.Thread(
                target=self._prewarm_channels_worker,
                args=(limit,),
                daemon=True,
            )
            self._prewarm_thread.start()
            return

        self._prewarm_channels_worker(limit)

    def _start_initial_prewarm(self):
        """Kick off startup prewarm after the initial UI has settled."""
        if self.prewarm_limit == 0:
            self.logger.info("Skipping initial prewarm (disabled)")
            return
        try:
            self.prewarm_channels(limit=self.prewarm_limit)
        except Exception as exc:
            self.logger.debug("Initial prewarm failed to start: %s", exc)

    def _prewarm_channels_worker(self, limit: int = None):
        def update_status(message: str):
            if threading.current_thread() is threading.main_thread() and hasattr(self, "status_bar"):
                self.status_bar.showMessage(message)
            else:
                self.logger.debug(message)

        try:
            # If limit is None, prewarm ALL channels; otherwise limit the count
            all_nums = sorted(self.channels.keys())
            if limit is None:
                nums = all_nums
            else:
                nums = all_nums[:limit]
            
            # Filter out channels that already have cached tokens
            to_extract = []
            for num in nums:
                ch = self.channels.get(num, {})
                # Skip if already cached or no source URL
                if ch.get('source_url') and ch.get('url') and self._is_cached_stream_valid(num):
                    continue
                if not ch.get('source_url'):
                    continue
                to_extract.append(num)
            
            if not to_extract:
                return  # All channels already cached
            
            update_status(f"⏳ Prewarming {len(to_extract)} channel(s)...")
            self.logger.info(f"Starting prewarm for channels: {to_extract}")
            
            # Use a bounded pool to avoid hammering upstream sites
            max_workers = max(1, int(getattr(self, "prewarm_concurrency", 4)))
            futures = {}
            completed = 0
            from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
            with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='prewarm') as prewarm_pool:
                for num in to_extract:
                    ch = self.channels.get(num, {})
                    src = ch.get('source_url')
                    if src:
                        # Use _extract_streams_worker so each thread gets its own
                        # VideoStreamExtractor (and its own requests.Session).
                        # Sharing self.extractor across threads causes CSRF/cookie
                        # races on sites like thetvapp.to that require per-request
                        # session cookies + CSRF tokens.
                        futures[num] = prewarm_pool.submit(_extract_streams_worker, src)

                for future in as_completed(futures.values()):
                    # Identify which channel this future belongs to
                    num = next((n for n, f in futures.items() if f is future), None)
                    if num is None:
                        continue
                    try:
                        candidate = _select_best_stream(future.result(timeout=45))  # 45 sec per extraction (thetvapp is slow)
                        if candidate:
                            url = candidate.get('url')
                            stype = candidate.get('type', '')
                            if url and _is_playable_stream(url, stype):
                                self._cache_channel_stream(num, url, stype)
                                self.logger.debug(f"Cached token for channel {num}")
                    except FutureTimeoutError:
                        self.logger.warning(f"Extraction timeout for channel {num}")
                    except Exception as e:
                        self.logger.debug(f"Prewarm extraction error for channel {num}: {e}")
                    finally:
                        completed += 1
                        progress = f"{completed}/{len(to_extract)}"
                        update_status(f"⏳ Prewarming channels: {progress}")
            
            if completed > 0:
                update_status(f"✓ Prewarmed {completed}/{len(to_extract)} channels for fast switching")
                self.logger.info(f"Prewarm completed: {completed}/{len(to_extract)} channels cached")
            
        except Exception as e:
            self.logger.error(f"Prewarm error: {e}")
    
    def change_grid_size(self, rows: int, cols: int):
        """Change the grid size."""
        self.grid_size = (rows, cols)
        self.create_grid()

    def set_active_player(self, player: VideoPlayer):
        """Set which player receives new loads and highlight it."""
        if self.active_player is player:
            return
            
        # Clear previous selection
        if self.active_player:
            self.active_player.set_selected(False)
            
        # Set new active player
        self.active_player = player
        if self.active_player:
            self.active_player.set_selected(True)
                
            player_id = getattr(self.active_player, 'player_id', 'unknown')
            display_id = getattr(self.active_player, 'display_id', player_id + 1)
            self.status_bar.showMessage(f"Selected Player #{display_id} - New content will load here")
            
            # Log player selection
            self.logger.debug(f"Active player changed to Player #{display_id}")
            self.action_logger.info(f"Selected Player #{display_id}")

            # Sync top-bar channel controls to newly selected player's channel
            ch_num = getattr(self.active_player, 'current_channel_number', None)
            if ch_num is not None:
                self.current_channel = ch_num
                if hasattr(self, 'channel_input'):
                    self.channel_input.setText(str(ch_num))
                if hasattr(self, 'lineup_label'):
                    ch_title = self.channels.get(ch_num, {}).get('title', '')
                    self.lineup_label.setText(ch_title)

            # Re-apply audio policies after selection change
            # If global solo is on, ensure the new active is unmuted and others follow policy
            if getattr(self, 'solo_mode_active', False):
                setattr(self.active_player, '_manually_muted', False)
            self.refresh_audio_states()
    
    def refresh_audio_states(self):
        """Alias to enforce_audio_policy for compatibility."""
        self.enforce_audio_policy()

    def enforce_audio_policy(self):
        """Centralized audio policy: manual mute + solo priority."""
        if not hasattr(self, 'players'):
            return

        # Determine solo target: per-player solo wins, else global solo uses active player
        solo_player = next((p for p in self.players if getattr(p, 'is_solo', False) and getattr(p, 'current_url', '')), None)
        target_player = None
        if solo_player:
            target_player = solo_player
        elif getattr(self, 'solo_mode_active', False) and getattr(self, 'active_player', None):
            target_player = self.active_player if getattr(self.active_player, 'current_url', '') else None

        # If solo is active, auto-clear manual mute on the target so audio comes through
        if target_player and getattr(target_player, '_manually_muted', False):
            target_player._manually_muted = False

        # Build allowed set
        any_solo_active = bool(solo_player) or getattr(self, 'solo_mode_active', False)
        allowed = set()
        if target_player:
            allowed.add(target_player)
        elif not any_solo_active:
            # Normal mode: all players with content get audio
            allowed.update([p for p in self.players if getattr(p, 'current_url', '')])
        # else: solo mode is on but active player is empty → keep allowed empty (silence all)

        master_volume = getattr(self, 'current_volume', 60)

        for player in self.players:
            mp = getattr(player, 'media_player', None)
            if not mp:
                continue

            should_play = player in allowed
            manual_muted = getattr(player, '_manually_muted', False)

            if should_play and not manual_muted:
                mp.audio_set_mute(False)
                mp.audio_set_volume(master_volume)
                player.is_muted = False
                player._solo_silenced = False
                if hasattr(player, 'mute_button'):
                    player.mute_button.setText("🔊")
            else:
                mp.audio_set_volume(0)
                mp.audio_set_mute(True)
                player.is_muted = True
                player._solo_silenced = not should_play and bool(target_player)
                if hasattr(player, 'mute_button'):
                    player.mute_button.setText("🔇")

    def apply_solo_mode(self):
        """Apply solo policy via centralized enforcer."""
        self.enforce_audio_policy()
    
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
        """Add files to grid slots, starting with the selected player."""
        if not files:
            return

        # If only one file and we have a selected player, use just that
        if len(files) == 1 and self.active_player:
            success = self.active_player.load_media(files[0], title=None, source_url=None)
            if success:
                player_id = getattr(self.active_player, 'player_id', 'unknown')
                display_id = getattr(self.active_player, 'display_id', player_id + 1)
                self.status_bar.showMessage(f"Loaded file into selected Player #{display_id}")
            return

        # For multiple files, prioritize the active player for the first file
        targets: List[VideoPlayer] = []
        if self.active_player:
            targets.append(self.active_player)

        # Then use empty slots (excluding the active one already added)
        empty_players = [p for p in self.players if (not p.current_url) and p is not self.active_player]
        targets.extend(empty_players)

        # If more files than empty slots, fall back to remaining players (may overwrite)
        remaining_players = [p for p in self.players if p not in targets]
        targets.extend(remaining_players)

        loaded_count = 0
        for file_path, player in zip(files, targets):
            if player.load_media(file_path, title=None, source_url=None):
                loaded_count += 1
                
        # Apply solo mode immediately after loading files if active
        if self.solo_mode_active:
            self.apply_solo_mode()
                
        self.status_bar.showMessage(f"Loaded {loaded_count} files starting with selected player")
    
    def add_url_dialog(self):
        """Show dialog to add a URL."""
        if not self.active_player:
            QMessageBox.information(self, "No Player Selected", "Please click a video box to select it first, then add a URL.")
            return
            
        url, ok = QInputDialog.getText(self, 'Add URL', 'Enter video URL or webpage URL:')
        if ok and url:
            # Check if URL is a direct video file
            if any(url.lower().endswith(ext) for ext in ['.mp4', '.webm', '.ogg', '.avi', '.mov', '.flv', '.mkv', '.m3u8']):
                # Direct video - load immediately
                self.add_url_to_grid(url)
            else:
                # Webpage - extract and show selection
                self.extract_and_show_streams(url)

    def add_active_to_favorites(self):
        """Add currently active player's URL to favorites."""
        if not self.active_player or not self.active_player.current_url:
            QMessageBox.information(self, "No Active Player", "Click a player with a loaded URL before adding to favorites.")
            return

        entry = {
            'url': self.active_player.current_url,
            'title': self.active_player.get_display_text() or self.active_player.current_url
        }

        # Deduplicate by URL
        existing_urls = {fav['url'] for fav in self.favorites}
        if entry['url'] in existing_urls:
            QMessageBox.information(self, "Already in Favorites", "This URL is already saved to favorites.")
            return

        self.favorites.append(entry)
        self._save_favorites_to_disk()
        self.status_bar.showMessage(f"Added to favorites: {entry['title']}")

    def pick_favorite_and_load(self):
        """Prompt to choose a favorite and load into the active player/slot."""
        if not self.favorites:
            QMessageBox.information(self, "No Favorites", "Favorites list is empty. Add one first.")
            return

        labels = [fav.get('title') or fav.get('url') for fav in self.favorites]
        choice, ok = QInputDialog.getItem(self, "Load Favorite", "Choose a favorite to load:", labels, 0, False)
        if not ok:
            return

        idx = labels.index(choice)
        url = self.favorites[idx]['url']
        self.add_url_to_grid(url)

    def manage_favorites_dialog(self):
        """Simple dialog to load or remove favorites."""
        if not self.favorites:
            QMessageBox.information(self, "No Favorites", "Favorites list is empty. Add one first.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Favorites")
        dialog.resize(400, 300)

        layout = QVBoxLayout(dialog)
        list_widget = QListWidget()
        for fav in self.favorites:
            label = fav.get('title') or fav.get('url')
            list_widget.addItem(label)
        layout.addWidget(list_widget)

        btn_row = QHBoxLayout()
        load_btn = QPushButton("Load Selected")
        remove_btn = QPushButton("Remove Selected")
        close_btn = QPushButton("Close")
        btn_row.addWidget(load_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        def load_selected():
            row = list_widget.currentRow()
            if row < 0:
                return
            fav = self.favorites[row]
            url = fav['url']
            source_url = fav.get('source_url')  # May be None for old entries
            
            # Load with source URL if available for auto-recovery
            if self.active_player and url:
                self.active_player.load_media(
                    url,
                    title=fav.get('title', ''),
                    source_url=source_url
                )
            else:
                self.add_url_to_grid(url)
            dialog.accept()

        def remove_selected():
            row = list_widget.currentRow()
            if row < 0:
                return
            self.favorites.pop(row)
            self._save_favorites_to_disk()
            list_widget.takeItem(row)

        load_btn.clicked.connect(load_selected)
        remove_btn.clicked.connect(remove_selected)
        close_btn.clicked.connect(dialog.reject)

        dialog.exec()

    def _load_favorites_from_disk(self):
        """Load favorites JSON if present."""
        try:
            if self.favorites_file.exists():
                with open(self.favorites_file, 'r') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.favorites = [fav for fav in data if isinstance(fav, dict) and 'url' in fav]
                self.status_bar.showMessage(f"Loaded {len(self.favorites)} favorites")
        except Exception as e:
            self.logger.error("Failed to load favorites: %s", e)

    def _save_favorites_to_disk(self):
        """Persist favorites to JSON."""
        try:
            with open(self.favorites_file, 'w') as f:
                json.dump(self.favorites, f, indent=2)
            self.status_bar.showMessage(f"Saved {len(self.favorites)} favorites")
        except Exception as e:
            self.logger.error("Failed to save favorites: %s", e)

    # ------------------- Playlists -------------------

    def _snapshot_state(self) -> Dict[str, Any]:
        """Capture current grid/player state into a dict."""
        state: Dict[str, Any] = {
            'grid_size': self.grid_size,
            'volume': self.current_volume,
            'players': []
        }

        for i, player in enumerate(self.players):
            if player.current_url:
                channel_num = getattr(player, 'current_channel_number', None)
                display_title = player.get_display_text()
                # Prefer channel label when tuned to a channel
                if channel_num is not None and self.channels:
                    ch = self.channels.get(channel_num, {})
                    ch_title = ch.get('title', str(channel_num))
                    display_title = f"Ch {channel_num}: {ch_title}"

                player_data = {
                    'index': i,
                    'url': player.current_url,
                    'title': display_title,
                    'is_muted': player.is_muted,
                    'start_time': player.start_time,
                    'end_time': player.end_time,
                    'is_clipped': player.is_clipped,
                    'current_channel_number': channel_num
                }
                # Include source URL if available for auto-recovery
                if player.source_url:
                    player_data['source_url'] = player.source_url
                state['players'].append(player_data)
        return state

    def _apply_state(self, state: Dict[str, Any]):
        """Apply a state snapshot to the grid."""
        # Stop current
        self.stop_all()

        grid_size = tuple(state.get('grid_size', (2, 2)))
        if grid_size != self.grid_size:
            self.grid_size = grid_size
            self.create_grid()

        volume = state.get('volume', 70)
        self.volume_slider.setValue(volume)

        for player_state in state.get('players', []):
            index = player_state.get('index', 0)
            if index < len(self.players):
                player = self.players[index]
                url = player_state.get('url', '')
                source_url = player_state.get('source_url')  # May be None for old playlists

                # Derive channel number if present or inferable
                channel_num = player_state.get('current_channel_number') or player_state.get('channel')
                if channel_num is None and source_url and self.channels:
                    for num, ch in self.channels.items():
                        if ch.get('source_url') and ch.get('source_url') == source_url:
                            channel_num = num
                            break
                if channel_num is None:
                    title_text = player_state.get('title', '')
                    match = re.match(r'^Ch\s+(\d+)', title_text)
                    if match:
                        try:
                            channel_num = int(match.group(1))
                        except Exception:
                            channel_num = None

                # Rebuild title from channel data when possible
                display_title = player_state.get('title', '')
                if channel_num is not None and self.channels:
                    ch = self.channels.get(channel_num, {})
                    ch_title = ch.get('title', display_title or str(channel_num))
                    display_title = f"Ch {channel_num}: {ch_title}"

                # Ensure player label logic knows the channel before loading
                player.current_channel_number = channel_num if channel_num is not None else None
                player.load_media(url, display_title, source_url=source_url)

                if player_state.get('is_muted', False):
                    if not player.is_muted:
                        player.toggle_mute()
                player.start_time = player_state.get('start_time', 0)
                player.end_time = player_state.get('end_time', 0)
                player.is_clipped = player_state.get('is_clipped', False)

    def _load_playlists_from_disk(self):
        try:
            if self.playlists_file.exists():
                with open(self.playlists_file, 'r') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.playlists = data
                    self.status_bar.showMessage(f"Loaded {len(self.playlists)} playlists")
        except Exception as e:
            self.logger.error("Failed to load playlists: %s", e)

    def _save_playlists_to_disk(self):
        try:
            with open(self.playlists_file, 'w') as f:
                json.dump(self.playlists, f, indent=2)
            self.status_bar.showMessage(f"Saved {len(self.playlists)} playlists")
        except Exception as e:
            self.logger.error("Failed to save playlists: %s", e)

    def save_playlist_prompt(self):
        name, ok = QInputDialog.getText(self, 'Save Playlist', 'Enter playlist name:')
        if not ok or not name.strip():
            return
        name = name.strip()
        self.playlists[name] = self._snapshot_state()
        self._save_playlists_to_disk()
        self.status_bar.showMessage(f"Saved playlist: {name}")

    def load_playlist_prompt(self):
        if not self.playlists:
            QMessageBox.information(self, "No Playlists", "No playlists saved yet.")
            return
        names = sorted(self.playlists.keys())
        choice, ok = QInputDialog.getItem(self, 'Load Playlist', 'Choose playlist:', names, 0, False)
        if not ok:
            return
        state = self.playlists.get(choice)
        if state:
            self._apply_state(state)
            self.status_bar.showMessage(f"Loaded playlist: {choice}")

    def delete_playlist_prompt(self):
        if not self.playlists:
            QMessageBox.information(self, "No Playlists", "No playlists to delete.")
            return
        names = sorted(self.playlists.keys())
        choice, ok = QInputDialog.getItem(self, 'Delete Playlist', 'Choose playlist to delete:', names, 0, False)
        if not ok:
            return
        if choice in self.playlists:
            del self.playlists[choice]
            self._save_playlists_to_disk()
            self.status_bar.showMessage(f"Deleted playlist: {choice}")
    
    def add_url_to_grid(self, url: str, title: Optional[str] = None, source_url: Optional[str] = None):
        """Add URL to the selected player."""
        # Only load into active/selected player
        if self.active_player:
            success = self.active_player.load_media(url, title=title, source_url=source_url)
            if success:
                # Apply solo mode immediately if active
                if self.solo_mode_active:
                    self.apply_solo_mode()
                player_id = getattr(self.active_player, 'display_id', getattr(self.active_player, 'player_id', 'unknown'))
                self.status_bar.showMessage(f"Loading URL into selected Player #{player_id}")
            return

        # If no player is selected, select the first empty one
        for player in self.players:
            if not player.current_url:
                self.set_active_player(player)
                success = player.load_media(url, title=title, source_url=source_url)
                if success and self.solo_mode_active:
                    self.apply_solo_mode()
                return

        # If all players have content, select and overwrite the first one
        if self.players:
            self.set_active_player(self.players[0])
            success = self.players[0].load_media(url, title=title, source_url=source_url)
            if success and self.solo_mode_active:
                self.apply_solo_mode()

    # ------------------- Channels (cable-box style) -------------------

    def _load_channels_from_disk(self):
        try:
            if self.channels_file.exists():
                with open(self.channels_file, 'r') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    # Normalize keys to int where possible
                    normalized = {}
                    for k, v in data.items():
                        try:
                            num = int(k)
                        except Exception:
                            continue
                        if isinstance(v, dict):
                            # Support legacy entries with 'url' and new entries with 'source_url'
                            entry = {
                                'title': v.get('title', str(num))
                            }
                            if 'source_url' in v:
                                entry['source_url'] = v.get('source_url', '')
                            if 'logo' in v:
                                entry['logo'] = v.get('logo', '')
                            if 'guide_id' in v:
                                entry['guide_id'] = v.get('guide_id', '')
                            if 'url' in v:
                                # Keep in-memory only; will not be persisted going forward
                                entry['url'] = v.get('url', '')
                            if 'url_type' in v:
                                entry['url_type'] = v.get('url_type', '')
                            normalized[num] = entry
                    self.channels = normalized
                    # Load lineup label if stored
                    if isinstance(data.get('_lineup_label'), str):
                        self.channel_lineup_label = data.get('_lineup_label')
                        if hasattr(self, 'lineup_label'):
                            self.lineup_label.setText(self.channel_lineup_label)
                    self.status_bar.showMessage(f"Loaded {len(self.channels)} channels")
        except Exception as e:
            self.logger.error("Failed to load channels: %s", e)

    def _save_channels_to_disk(self):
        try:
            # Persist only canonical data (title + source_url + logo). Do not persist tokenized 'url'.
            payload = {}
            for num, ch in self.channels.items():
                entry = {'title': ch.get('title', str(num))}
                if 'source_url' in ch and ch.get('source_url'):
                    entry['source_url'] = ch.get('source_url')
                if 'logo' in ch and ch.get('logo'):
                    entry['logo'] = ch.get('logo')
                if 'guide_id' in ch and ch.get('guide_id'):
                    entry['guide_id'] = ch.get('guide_id')
                payload[str(num)] = entry
            if self.channel_lineup_label:
                payload['_lineup_label'] = self.channel_lineup_label
            with open(self.channels_file, 'w') as f:
                json.dump(payload, f, indent=2)
            self.status_bar.showMessage(f"Saved {len(self.channels)} channels")
            # Update all player channel dropdowns
            self.update_all_player_channel_lists()
        except Exception as e:
            self.logger.error("Failed to save channels: %s", e)

    # ------------ Channel stream caching helpers -------------
    def _parse_url_expiry(self, url: str) -> Optional[int]:
        """Extract expires= epoch from tokenized URLs when present."""
        if not url or 'expires=' not in url:
            return None
        try:
            from urllib.parse import parse_qs
            qs = parse_qs(urlparse(url).query)
            exp = qs.get('expires')
            if exp:
                return int(exp[0])
        except Exception:
            return None
        return None

    def _cache_channel_stream(self, num: int, url: str, stream_type: str = ""):
        """Cache stream URL with optional type and expiry for quick reuse."""
        if num not in self.channels or not url:
            return
        self.channels[num]['url'] = url
        if stream_type:
            self.channels[num]['url_type'] = stream_type
        exp = self._parse_url_expiry(url)
        if exp:
            self.channels[num]['url_expiry'] = exp

    def _is_cached_stream_valid(self, num: int, buffer_seconds: int = 30) -> bool:
        """Return True if cached stream exists and has not expired (with buffer)."""
        ch = self.channels.get(num, {})
        url = ch.get('url')
        if not url:
            return False
        exp = ch.get('url_expiry')
        if exp:
            now = int(time.time())
            if now >= exp - buffer_seconds:
                return False
        return True

    def _is_cached_stream_stale_but_usable(self, num: int, grace_seconds: int = 180) -> bool:
        """Allow using slightly expired tokens to reduce tune latency."""
        ch = self.channels.get(num, {})
        url = ch.get('url')
        if not url:
            return False
        exp = ch.get('url_expiry')
        if not exp:
            return False
        now = int(time.time())
        return (exp <= now < exp + grace_seconds)

    def _refresh_channel_in_background(self, num: int):
        """Refresh token for a specific channel without interrupting playback."""
        ch = self.channels.get(num, {})
        src = ch.get('source_url')
        if not src:
            return
        future = self.submit_stream_extraction(src)

        def on_done():
            if future.done():
                try:
                    candidate = _select_best_stream(future.result())
                    new_url = candidate.get('url') if candidate else None
                    stype = candidate.get('type', '') if candidate else ''
                    if new_url and _is_playable_stream(new_url, stype):
                        self._cache_channel_stream(num, new_url, stype)
                        self.logger.debug(f"Background refresh updated channel {num}")
                except Exception as e:
                    self.logger.debug(f"Background refresh failed for channel {num}: {e}")

        future.add_done_callback(lambda _: QTimer.singleShot(0, on_done))

    def update_all_player_channel_lists(self):
        """Update channel dropdown lists in all players."""
        for player in self.players:
            if hasattr(player, 'update_channel_list'):
                player.update_channel_list()

    def _commit_channel_buffer(self):
        if not self._channel_entry_buffer:
            return
        try:
            num = int(self._channel_entry_buffer)
        except ValueError:
            self._channel_entry_buffer = ""
            return
        self._channel_entry_buffer = ""
        self.tune_channel(num)

    def _is_text_input_focused(self) -> bool:
        """Return True if a text-editing widget currently has focus.

        This prevents hijacking arrow keys when the user is editing an input.
        """
        try:
            fw = QApplication.focusWidget()
        except Exception:
            fw = None
        if fw is None:
            return False
        return isinstance(
            fw,
            (
                QLineEdit,
                QTextEdit,
                QPlainTextEdit,
                QComboBox,
                QSpinBox,
                QDoubleSpinBox,
                QDateTimeEdit,
                QTimeEdit,
            ),
        )

    def move_active_selection(self, d_row: int, d_col: int):
        """Move the highlighted/active player by grid delta (rows/cols)."""
        if not hasattr(self, 'players') or not self.players:
            return

        rows, cols = getattr(self, 'grid_size', (1, 1))
        if not cols:
            return

        try:
            idx = self.players.index(self.active_player) if self.active_player in self.players else 0
        except Exception:
            idx = 0

        row = idx // cols
        col = idx % cols

        new_row = max(0, min(rows - 1, row + d_row))
        new_col = max(0, min(cols - 1, col + d_col))

        new_idx = new_row * cols + new_col
        new_idx = max(0, min(len(self.players) - 1, new_idx))
        self.set_active_player(self.players[new_idx])

    def keyPressEvent(self, event):
        """Capture numeric keypresses to emulate cable box entry."""
        try:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                # Exit VLC-native fullscreen first if active
                ap = getattr(self, "active_player", None)
                if ap and getattr(ap, "media_player", None):
                    try:
                        if ap.media_player.get_fullscreen():
                            ap.toggle_vlc_fullscreen()
                            return
                    except Exception:
                        pass
                if getattr(self, "_player_fullscreen_active", False):
                    self.exit_player_fullscreen()
                    return
                if self.isFullScreen():
                    self.toggle_fullscreen_mode()
                    return
            if key in (Qt.Key.Key_F, Qt.Key.Key_Enter, Qt.Key.Key_Return) and (event.modifiers() & Qt.KeyboardModifier.AltModifier):
                # Alt+Enter / Alt+Return and 'F' toggle VLC-style fullscreen on active player
                ap = getattr(self, "active_player", None)
                if ap and not getattr(ap, "browser_mode", False) and getattr(ap, "media_player", None):
                    ap.toggle_vlc_fullscreen()
                    return
            if key in (Qt.Key.Key_Plus, Qt.Key.Key_Minus):
                # Secondary control: Numpad + / - for channel up/down
                if event.isAutoRepeat():
                    return
                if event.modifiers() & Qt.KeyboardModifier.KeypadModifier:
                    if self._is_text_input_focused():
                        super().keyPressEvent(event)
                        return
                    if key == Qt.Key.Key_Plus:
                        self.channel_up()
                    else:
                        self.channel_down()
                    return
            if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
                digit = key - Qt.Key.Key_0
                self._channel_entry_buffer += str(digit)
                self._channel_entry_timer.start()
                if hasattr(self, "status_bar") and self.status_bar:
                    self.status_bar.showMessage(f"Channel entry: {self._channel_entry_buffer}")
                return
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._commit_channel_buffer()
                return
            super().keyPressEvent(event)
        except Exception as e:
            # Avoid crashing the UI on unexpected key handling errors
            self.logger.exception("Key press handling failed: %s", e)
            try:
                super().keyPressEvent(event)
            except Exception:
                pass

    def toggle_player_fullscreen(self):
        """Toggle fullscreen for the currently active player.

        - In VLC mode: use VLC's native fullscreen (like pressing 'f').
        - In browser mode: expand the player and hide other UI.
        """
        player = self.active_player if hasattr(self, "active_player") else None
        if not player and self.players:
            player = self.players[0]
        if not player:
            return

        # VLC mode: use native fullscreen toggle
        if not getattr(player, "browser_mode", False) and getattr(player, "media_player", None):
            player.toggle_vlc_fullscreen()
            return

        # Browser mode fallback: expand the player within the app window
        if self._player_fullscreen_active:
            self.exit_player_fullscreen()
        else:
            self.enter_player_fullscreen()

    def enter_player_fullscreen(self):
        player = self.active_player if hasattr(self, "active_player") else None
        if not player and self.players:
            player = self.players[0]
        if not player:
            return

        self._player_fullscreen_active = True
        self._player_fullscreen_restore = {
            "was_fullscreen": self.isFullScreen(),
            "window_state": self.windowState(),
            "control_panel_visible": self.control_panel_visible,
        }

        # Hide control panel for an uncluttered view
        if hasattr(self, "control_panel"):
            self.control_panel_visible = False
        # Hide all overlays for true fullscreen
        self.set_overlay_visibility(False)

        # Hide other players and let the active one expand
        for p in self.players:
            if p is player:
                p.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                p.show()
            else:
                p.hide()

        self.showFullScreen()
        self.status_bar.showMessage(f"Fullscreen video: Player #{getattr(player, 'display_id', player.player_id) + 1}")

    def exit_player_fullscreen(self):
        """Restore grid and controls after fullscreen video."""
        restore = self._player_fullscreen_restore or {}
        for p in self.players:
            p.show()
            p.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        if hasattr(self, "control_panel"):
            self.control_panel_visible = restore.get("control_panel_visible", True)
        # Show overlays again
        self.set_overlay_visibility(True)

        if not restore.get("was_fullscreen", False):
            prev_state = restore.get("window_state")
            if prev_state is not None:
                self.setWindowState(prev_state)
            else:
                self.showNormal()

        self._player_fullscreen_active = False
        self._player_fullscreen_restore = {}
        if hasattr(self, "status_bar") and self.status_bar:
            self.status_bar.showMessage("Exited video fullscreen")

    def set_overlay_visibility(self, visible: bool):
        """Hide/show UI overlays in fullscreen mode."""
        if hasattr(self, 'control_panel') and self.control_panel:
            self.control_panel.setVisible(visible)
        if hasattr(self, 'status_bar') and self.status_bar:
            self.status_bar.setVisible(visible)

    def toggle_fullscreen_mode(self):
        """Toggle fullscreen for the main window."""
        if self.isFullScreen():
            prev_state = getattr(self, "_prev_window_state", None)
            if prev_state is not None:
                self.setWindowState(prev_state)
            else:
                self.showNormal()
            self.set_overlay_visibility(True)
            self.status_bar.showMessage("Exited fullscreen")
        else:
            # If video fullscreen is active, exit it first to avoid conflicting states
            if self._player_fullscreen_active:
                self.exit_player_fullscreen()
            # Remember prior state (maximized vs normal) so we can restore it
            self._prev_window_state = self.windowState()
            self.showFullScreen()
            self.set_overlay_visibility(False)
            self.status_bar.showMessage("Entered fullscreen (Press Esc to exit)")

    def tune_channel_from_input(self):
        text = self.channel_input.text().strip() if hasattr(self, 'channel_input') else ""
        if not text:
            return
        try:
            num = int(text)
        except ValueError:
            QMessageBox.warning(self, "Invalid Channel", "Please enter a number.")
            return
        self.tune_channel(num)

    def tune_channel(self, number: int):
        # Track when user last tuned a channel (for idle background refresh)
        import time
        self._last_channel_tune_time = time.time()
        self._tune_request_id += 1
        tune_request_id = self._tune_request_id
        
        channel = self.channels.get(number)
        if not channel:
            self.logger.warning(f"Attempted to tune to non-existent channel {number}")
            QMessageBox.information(self, "Channel Not Found", f"Channel {number} is not assigned.")
            return

        self.current_channel = number
        if hasattr(self, 'channel_input'):
            self.channel_input.setText(str(number))

        title = channel.get('title', str(number))
        source_url = channel.get('source_url')
        current_token_url = channel.get('url')  # Ephemeral; may be missing or expired
        cached_type = channel.get('url_type', '')

        # Discard invalid, but allow slightly stale tokens for fast start
        if current_token_url and not _is_playable_stream(current_token_url, cached_type):
            current_token_url = None
        elif current_token_url and not self._is_cached_stream_valid(number):
            if self._is_cached_stream_stale_but_usable(number):
                # Use stale token to start fast; refresh in background
                self._refresh_channel_in_background(number)
            else:
                current_token_url = None
                for k in ('url', 'url_type', 'url_expiry'):
                    channel.pop(k, None)

        display_title = f"Ch {number}: {title}" if title else f"Ch {number}"

        # If we have a cached token URL, try it first (fast path)
        if current_token_url:
            self.logger.info(f"Tuning to channel {number} with cached token: {title}")
            if self.active_player:
                if hasattr(self.active_player, 'current_channel_number'):
                    self.active_player.current_channel_number = number
                self.active_player.load_media(current_token_url, title=display_title, source_url=source_url)
                self.refresh_audio_states()
                self.status_bar.showMessage(f"Tuned to channel {number}: {title}")
                return
            else:
                self.add_url_to_grid(current_token_url, title=display_title, source_url=source_url)
                return

        # Otherwise, extract fresh stream from source_url if available
        if source_url:
            self.logger.info(f"Tuning to channel {number} via source: {title} - {source_url}")
            self.action_logger.info(f"Tuned to Channel {number}: {title}")
            self.status_bar.showMessage(f"Loading channel {number}: {title}...")

            # Show loading state immediately on the active player so the user knows to wait
            if self.active_player:
                if hasattr(self.active_player, 'current_channel_number'):
                    self.active_player.current_channel_number = number
                if hasattr(self.active_player, 'set_display_text'):
                    self.active_player.set_display_text(f"⏳ {display_title}")
                if hasattr(self.active_player, 'status_label'):
                    self.active_player.status_label.setText("⏳")

            future = self.submit_stream_extraction(source_url)

            def on_done():
                if future.done():
                    # Only discard if user has navigated to a different channel
                    if self.current_channel != number:
                        self.logger.debug(
                            "Ignoring stale tune result for channel %s (now on %s)",
                            number,
                            self.current_channel,
                        )
                        return
                    try:
                        candidate = _select_best_stream(future.result())
                        new_url = candidate.get('url') if candidate else None
                        stream_type = candidate.get('type', '') if candidate else ''

                        if self.active_player and new_url and _is_playable_stream(new_url, stream_type):
                            if hasattr(self.active_player, 'current_channel_number'):
                                self.active_player.current_channel_number = number
                            self.active_player.load_media(new_url, title=display_title, source_url=source_url)
                            self.refresh_audio_states()
                            self._cache_channel_stream(number, new_url, stream_type)
                            self.status_bar.showMessage(f"✓ Tuned to channel {number}: {title}")
                        elif candidate and WEBENGINE_AVAILABLE:
                            # Use browser mode fallback when only a webpage is available
                            if self.active_player:
                                if hasattr(self.active_player, 'current_channel_number'):
                                    self.active_player.current_channel_number = number
                            target = self.active_player or (self.players[0] if self.players else None)
                            if target:
                                self.add_url_to_browser_mode(source_url or new_url)
                            self.status_bar.showMessage(f"🌐 Browser mode for Channel {number}")
                        elif new_url:
                            # Last resort: try to load even if not clearly playable
                            self.add_url_to_grid(new_url, title=display_title, source_url=source_url)
                        else:
                            self.status_bar.showMessage(f"No playable streams for Channel {number}")
                            self.logger.warning(f"No streams found for Channel {number}")
                    except Exception as e:
                        self.logger.error(f"Channel {number} extraction error: {e}")
                        self.status_bar.showMessage(f"Error loading Channel {number}: {type(e).__name__}")
                    finally:
                        return

            future.add_done_callback(lambda _: QTimer.singleShot(0, on_done))
            
            # Prefetch next channel in background for smooth up/down navigation
            self._prefetch_next_channel(number)
            return

        QMessageBox.information(self, "Channel Missing URL", f"Channel {number} has no source or stream URL set.")

    def _prefetch_next_channel(self, current_number: int):
        """Prefetch the next and previous channels in background for faster up/down switching."""
        try:
            if not self.channels:
                return
            
            numbers = sorted(self.channels.keys())
            if current_number not in numbers:
                return
            
            idx = numbers.index(current_number)
            # Prefetch next and previous channels
            to_prefetch = [
                numbers[(idx + 1) % len(numbers)],  # Next
                numbers[(idx - 1) % len(numbers)],  # Previous
            ]
            
            for ch_num in to_prefetch:
                ch = self.channels.get(ch_num, {})
                # Skip if already cached or no source URL
                if (ch.get('url') and self._is_cached_stream_valid(ch_num)) or not ch.get('source_url'):
                    continue
                if ch_num in self._prefetch_pending:
                    continue
                
                src = ch.get('source_url')
                self._prefetch_pending.add(ch_num)
                # Submit low-priority background extraction
                future = self.submit_stream_extraction(src)
                
                def on_prefetch_done(n=ch_num, f=future):
                    if f.done():
                        try:
                            candidate = _select_best_stream(f.result(timeout=45))  # 45 sec timeout for slow thetvapp
                            if candidate:
                                url = candidate.get('url')
                                stype = candidate.get('type', '')
                                if url and _is_playable_stream(url, stype):
                                    self._cache_channel_stream(n, url, stype)
                                    self.logger.debug(f"Prefetched token for channel {n}")
                                    # If the user is currently waiting on this channel, load it now
                                    if self.current_channel == n and self.active_player:
                                        ch_data = self.channels.get(n, {})
                                        t = ch_data.get('title', str(n))
                                        dtitle = f"Ch {n}: {t}" if t else f"Ch {n}"
                                        if hasattr(self.active_player, 'current_channel_number'):
                                            self.active_player.current_channel_number = n
                                        self.active_player.load_media(url, title=dtitle, source_url=ch_data.get('source_url'))
                                        self.refresh_audio_states()
                                        self.status_bar.showMessage(f"✓ Tuned to channel {n}: {t}")
                        except Exception as e:
                            self.logger.debug(f"Prefetch failed for channel {n}: {e}")
                        finally:
                            self._prefetch_pending.discard(n)
                    else:
                        # Still processing, check again later
                        QTimer.singleShot(50, lambda: on_prefetch_done(n, f))
                
                QTimer.singleShot(50, lambda: on_prefetch_done(ch_num, future))
        except Exception as e:
            self.logger.debug(f"Prefetch error: {e}")

    def channel_up(self):
        if not self.channels:
            return
        numbers = sorted(self.channels.keys())
        if self.current_channel in numbers:
            idx = numbers.index(self.current_channel)
            next_idx = (idx + 1) % len(numbers)
        else:
            next_idx = 0
        self.tune_channel(numbers[next_idx])

    def channel_down(self):
        if not self.channels:
            return
        numbers = sorted(self.channels.keys())
        if self.current_channel in numbers:
            idx = numbers.index(self.current_channel)
            prev_idx = (idx - 1) % len(numbers)
        else:
            prev_idx = len(numbers) - 1
        self.tune_channel(numbers[prev_idx])

    def manage_channels_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Channels")
        dialog.resize(520, 420)

        # Simple in-memory cache so multiple opens do not refetch the whole DB
        if not hasattr(self, '_open_logo_db_cache'):
            self._open_logo_db_cache = {}

        layout = QVBoxLayout(dialog)
        list_widget = QListWidget()
        for num in sorted(self.channels.keys()):
            ch = self.channels[num]
            list_widget.addItem(f"{num}: {ch.get('title', ch.get('url'))}")
        layout.addWidget(list_widget)

        form_layout = QVBoxLayout()
        row1 = QHBoxLayout(); row2 = QHBoxLayout()
        num_input = QLineEdit(); num_input.setPlaceholderText("Number")
        title_input = QLineEdit(); title_input.setPlaceholderText("Title (optional)")
        url_input = QLineEdit(); url_input.setPlaceholderText("Source Page URL")
        logo_input = QLineEdit(); logo_input.setPlaceholderText("Logo URL or path (optional)")

        row1.addWidget(num_input)
        row1.addWidget(title_input)
        row2.addWidget(url_input)
        row2.addWidget(logo_input)
        row2.addStretch(1)
        form_layout.addLayout(row1)
        form_layout.addLayout(row2)

        # In-memory cache to avoid repeated logo fetches while dialog is open
        logo_cache: Dict[Tuple[str, int, int, bool], QPixmap] = {}

        def _logo_pixmap(path: str, size: QSize, allow_remote: bool = True) -> QPixmap:
            """Shared logo loader for list and preview with caching."""
            key = (path, size.width(), size.height(), allow_remote)
            if path and key in logo_cache:
                return logo_cache[key]

            pix = QPixmap()
            if not path:
                logo_cache[key] = pix
                return pix

            if allow_remote and path.startswith(("http://", "https://")):
                try:
                    resp = requests.get(path, timeout=3)
                    if resp.ok:
                        pix.loadFromData(resp.content)
                except Exception:
                    pix = QPixmap()

            if pix.isNull():
                p = Path(path)
                candidates = [p]
                if not p.is_absolute():
                    candidates.append(Path.cwd() / path)
                    candidates.append(Path.cwd() / "assets" / "logos" / p.name)
                for cand in candidates:
                    cand = cand.resolve()
                    if cand.exists():
                        pix = QPixmap(str(cand))
                        if not pix.isNull():
                            break

            if not pix.isNull():
                pix = pix.scaled(size, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)

            logo_cache[key] = pix
            return pix

        # Preview box for current logo
        preview_box = QGroupBox("Logo Preview")
        preview_layout = QVBoxLayout(preview_box)
        logo_preview = QLabel()
        logo_preview.setFixedSize(140, 80)
        logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Match the player badge background (light gray with subtle border)
        logo_preview.setStyleSheet("border: 1px solid #999; background: #e5e5e5; color: #333;")
        preview_layout.addWidget(logo_preview)
        form_layout.addWidget(preview_box)

        layout.addLayout(form_layout)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add")
        update_btn = QPushButton("Update")
        delete_btn = QPushButton("Delete")
        close_btn = QPushButton("Close")
        btn_row.addWidget(add_btn)
        btn_row.addWidget(update_btn)
        btn_row.addWidget(delete_btn)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        def refresh_list():
            list_widget.clear()
            for num in sorted(self.channels.keys()):
                ch = self.channels[num]
                text = f"{num}: {ch.get('title', ch.get('url'))}"
                item = QListWidgetItem(text)
                # Avoid remote fetches while building the list to keep the UI responsive
                pix = _logo_pixmap(ch.get('logo', ''), QSize(80, 45), allow_remote=False)
                if pix and not pix.isNull():
                    item.setIcon(QIcon(pix))
                list_widget.addItem(item)

        def update_logo_preview(path: str):
            """Unified preview loader (matches edit dialog behavior)."""
            logo_preview.setPixmap(QPixmap())
            logo_preview.setText("No logo")
            if not path:
                return
            pix = _logo_pixmap(path, logo_preview.size(), allow_remote=True)
            if pix.isNull():
                title_text = title_input.text().strip() or num_input.text().strip() or "Channel"
                logo_preview.setPixmap(_fallback_text_logo(title_text, logo_preview.size()))
                logo_preview.setText("")
                return

            logo_preview.setPixmap(pix)
            logo_preview.setText("")

        def build_entry(num: int, require_existing: bool):
            url = url_input.text().strip()
            if not url:
                QMessageBox.warning(dialog, "Missing URL", "Source page URL is required.")
                return None
            title = title_input.text().strip() or str(num)
            exists = num in self.channels
            if require_existing and not exists:
                QMessageBox.warning(dialog, "Not found", "Channel does not exist. Use Add instead.")
                return None
            entry = {'title': title, 'source_url': url}
            logo = logo_input.text().strip()
            if logo:
                entry['logo'] = logo
            if exists:
                # Preserve existing tokenized url if any
                if 'url' in self.channels[num]:
                    entry['url'] = self.channels[num]['url']
                if 'url_type' in self.channels[num]:
                    entry['url_type'] = self.channels[num]['url_type']
            return entry

        def add_channel():
            try:
                num = int(num_input.text().strip())
            except ValueError:
                QMessageBox.warning(dialog, "Invalid", "Channel number must be a number.")
                return
            entry = build_entry(num, require_existing=False)
            if not entry:
                return
            self.channels[num] = entry
            self._save_channels_to_disk()
            refresh_list()
            if getattr(self, 'current_channel', None) == num and self.active_player:
                display_title = f"Ch {num}: {entry['title']}" if entry.get('title') else f"Ch {num}"
                self.active_player.set_display_text(display_title)

        def update_channel():
            try:
                num = int(num_input.text().strip())
            except ValueError:
                QMessageBox.warning(dialog, "Invalid", "Channel number must be a number.")
                return
            entry = build_entry(num, require_existing=True)
            if not entry:
                return
            self.channels[num] = entry
            self._save_channels_to_disk()
            refresh_list()
            if getattr(self, 'current_channel', None) == num and self.active_player:
                display_title = f"Ch {num}: {entry['title']}" if entry.get('title') else f"Ch {num}"
                self.active_player.set_display_text(display_title)

        def delete_selected():
            row = list_widget.currentRow()
            if row < 0:
                return
            item_text = list_widget.item(row).text()
            try:
                num = int(item_text.split(":",1)[0])
            except Exception:
                return
            if num in self.channels:
                del self.channels[num]
                self._save_channels_to_disk()
                refresh_list()
                logo_preview.setPixmap(QPixmap())
                logo_preview.setText("No logo")

        add_btn.clicked.connect(add_channel)
        update_btn.clicked.connect(update_channel)
        delete_btn.clicked.connect(delete_selected)
        close_btn.clicked.connect(dialog.reject)

        # Prefill fields when selecting list entry
        def on_select():
            row = list_widget.currentRow()
            if row < 0:
                return
            item_text = list_widget.item(row).text()
            try:
                num = int(item_text.split(":",1)[0])
            except Exception:
                return
            ch = self.channels.get(num, {})
            num_input.setText(str(num))
            title_input.setText(ch.get('title', ''))
            url_input.setText(ch.get('source_url', ch.get('url', '')))
            logo_input.setText(ch.get('logo', ''))
            update_logo_preview(ch.get('logo', ''))

        list_widget.currentRowChanged.connect(lambda _: on_select())
        logo_input.textChanged.connect(lambda text: update_logo_preview(text))

        dialog.exec()

    def open_tv_guide_dialog(self):
        """Open the fixed-size TV Guide renderer."""
        try:
            known = [(num, ch.get("title", str(num))) for num, ch in self.channels.items()]
            dlg = GuideDialog(
                guide_data=self.guide_data,
                logo_resolver=self.guide_logo_resolver,
                known_channels=known,
                parent=self,
            )
            # If we only have the sample stub, trigger a fetch and refresh the dialog on completion
            if len(self.guide_data.channels) <= 4:
                self._load_guide_data_async(force=True, on_done=lambda data: dlg.update_data(data))
            dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "Guide Error", f"Failed to open guide: {e}")

    def _load_guide_data_async(self, force: bool = False, on_done=None):
        """Fetch a broad US guide lineup from TVMaze without blocking UI."""
        if self._guide_fetch_inflight:
            return
        if not force and len(getattr(self, 'guide_data', {}).channels) > 4:
            return
        self._guide_fetch_inflight = True

        def work():
            try:
                adapter = TVMazeAdapter(self.guide_logo_resolver)
                known = [(num, ch.get("title", str(num))) for num, ch in self.channels.items()]
                data = adapter.fetch(country="US", max_channels=200, known_channels=known)
                return data, ""
            except Exception as e:
                return None, str(e)

        def done(result):
            self._guide_fetch_inflight = False
            data, err = result
            if data:
                self.guide_data = data
                self.status_bar.showMessage(f"Guide data loaded ({len(data.channels)} channels)")
                if on_done:
                    try:
                        on_done(data)
                    except Exception:
                        pass
            elif err:
                self.status_bar.showMessage(f"Guide load failed: {err}")

        thread_result = {}

        def runner():
            thread_result["value"] = work()

        t = threading.Thread(target=runner, daemon=True)
        t.start()

        def poll():
            if "value" in thread_result:
                done(thread_result["value"])
            else:
                QTimer.singleShot(150, poll)

        poll()

    def set_channel_lineup(self):
        text, ok = QInputDialog.getText(self, 'Set Lineup', 'Enter lineup label (e.g., "Spectrum Corpus Christi"):')
        if not ok:
            return
        self.channel_lineup_label = text.strip()
        if hasattr(self, 'lineup_label'):
            self.lineup_label.setText(self.channel_lineup_label)
        self._save_channels_to_disk()
    
    def refresh_all_channel_tokens(self):
        """Refresh tokenized URLs for all channels that have a source_url."""
        numbers = sorted(self.channels.keys())
        idx = 0
        logger = logging.getLogger(LOGGER_NAME)
        
        def process_next():
            nonlocal idx
            if idx >= len(numbers):
                self._save_channels_to_disk()
                self.status_bar.showMessage("Channel tokens refreshed")
                return
            num = numbers[idx]
            ch = self.channels.get(num, {})
            src = ch.get('source_url')
            if not src:
                idx += 1
                QTimer.singleShot(10, process_next)
                return
            title = ch.get('title', str(num))
            self.status_bar.showMessage(f"Refreshing Ch {num}: {title}")
            future = self.submit_stream_extraction(src)
            
            def on_done():
                if future.done():
                    try:
                        streams = future.result()
                        candidate = _select_best_stream(streams)
                        new_url = candidate.get('url') if candidate else None
                        stream_type = candidate.get('type', '') if candidate else ''
                        if new_url and _is_playable_stream(new_url, stream_type):
                            self._cache_channel_stream(num, new_url, stream_type)
                            if candidate and candidate.get('title'):
                                self.channels[num]['title'] = candidate['title']
                            logger.info(f"Refreshed token for Ch {num}: {self.channels[num]['title']}")
                        else:
                            logger.warning(f"No streams for Ch {num} during refresh")
                    except Exception as e:
                        logger.error(f"Channel {num} refresh error: {e}")
                    finally:
                        idx += 1
                        QTimer.singleShot(10, process_next)

            future.add_done_callback(lambda _: QTimer.singleShot(0, on_done))
        
        process_next()
    
    def _maybe_save_channel_mapping(self, channel_num_text: str, channel_title_text: str, stream: Dict[str, str], source_url: str = None):
        """If `channel_num_text` is provided and valid, save the stream as a channel.
        Also updates the active player's label to "Ch N: Name" and sets `current_channel`."""
        if not channel_num_text:
            return
        try:
            num = int(channel_num_text.strip())
        except Exception:
            self.status_bar.showMessage("Invalid channel number; skipping channel save")
            return
        title = (channel_title_text or "").strip() or stream.get('title', str(num))
        # Persist only canonical data
        entry = {'title': title}
        if source_url:
            entry['source_url'] = source_url
        # Keep current token URL only in memory
        entry['url'] = stream.get('url', '')
        self.channels[num] = entry
        self._save_channels_to_disk()
        # Update current channel and label
        self.current_channel = num
        if hasattr(self, 'channel_input'):
            self.channel_input.setText(str(num))
        if self.active_player:
            display_title = f"Ch {num}: {title}" if title else f"Ch {num}"
            self.active_player.set_display_text(display_title)
        self.status_bar.showMessage(f"Saved channel {num}: {title}")
    
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
        """Extract streams from URL and show selection dialog.

        Note: Some sites (e.g., LocalNow) only support browser mode. In that case we still
        show the selection dialog so the user can explicitly pick "Browser Mode".
        """
        self.status_bar.showMessage("Extracting video streams...")
        
        # Run extraction in background thread
        future = self.submit_stream_extraction(url)
        
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
                    if not streams:
                        self.load_url_directly(url)
                        return
                    self.show_stream_selection_dialog(streams, url)
                    self.status_bar.showMessage("Stream extraction completed")
                except Exception as e:
                    log_error_with_context("Extraction Error", f"URL: {url}", e)
                    self.load_url_directly(url)

        future.add_done_callback(lambda _: QTimer.singleShot(0, check_completion))
    
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
            future = self.submit_stream_extraction(url)
            
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
                        if not streams:
                            self.load_url_directly(url)
                            return
                        self.show_stream_selection_dialog(streams, url)
                        self.status_bar.showMessage("Stream extraction completed")
                    except Exception as e:
                        log_error_with_context("Extraction Error", f"URL: {url}", e)
                        self.load_url_directly(url)

            future.add_done_callback(lambda _: QTimer.singleShot(0, check_completion))
    
    def show_stream_selection_dialog(self, streams: List[Dict[str, str]], source_url: str = None):
        """Show dialog to select which streams to add to the grid."""
        if not streams:
            if source_url:
                self.handle_no_streams_found(source_url)
            else:
                QMessageBox.information(self, "No Streams Found", "No video streams were found on the page.")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Select Video Stream ({len(streams)} found)")
        dialog.setModal(True)
        dialog.resize(1000, 600)
        
        main_layout = QHBoxLayout()
        dialog.setLayout(main_layout)
        
        # Left side - stream list
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel(f"Found {len(streams)} video stream(s). Select to preview:"))
        
        # Stream table
        stream_table = QTableWidget()
        stream_table.setColumnCount(3)
        stream_table.setHorizontalHeaderLabels(["#", "Title", "Type"])
        stream_table.setRowCount(len(streams))
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
        
        def can_vlc_preview(stream: Dict[str, str]) -> bool:
            st = (stream.get('type') or '').lower()
            u = (stream.get('url') or '').lower()
            if st in {'browser', 'iframe', 'youtube', 'dynamic', 'blob'}:
                return False
            if u.endswith(('.m3u8', '.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv', '.flv')):
                return True
            # Many extractors mark HLS as application/x-mpegURL
            if 'mpegurl' in st or 'hls' in st:
                return True
            # Fall back: avoid trying to preview arbitrary webpages in VLC
            return False

        # Selection changed handler
        def on_selection_changed():
            current_row = stream_table.currentRow()
            if current_row >= 0:
                title_item = stream_table.item(current_row, 1)
                stream = title_item.data(Qt.ItemDataRole.UserRole)
                stream_url = stream.get('url', '')
                
                # Stop current preview
                preview_player.stop()

                # Skip VLC preview for browser-mode / non-direct-media entries
                if not can_vlc_preview(stream):
                    return
                
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
                    self.logger.error("Preview error: %s", e)
        
        stream_table.currentCellChanged.connect(lambda: on_selection_changed())
        
        # Double-click to add single stream
        stream_table.itemDoubleClicked.connect(lambda item: self.add_single_stream_from_table(
            stream_table,
            dialog,
            source_url,
            channel_num_input.text(),
            channel_title_input.text()
        ))
        
        left_layout.addWidget(stream_table)
        
        # Optional channel save inputs
        channel_row = QHBoxLayout()
        channel_num_input = QLineEdit()
        channel_num_input.setPlaceholderText("Channel # (optional)")
        channel_num_input.setFixedWidth(120)
        channel_title_input = QLineEdit()
        channel_title_input.setPlaceholderText("Channel Name (optional)")
        channel_row.addWidget(channel_num_input)
        channel_row.addWidget(channel_title_input)
        left_layout.addLayout(channel_row)
        
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
        add_selected_button.clicked.connect(lambda: self.add_selected_streams_from_table(
            stream_table,
            dialog,
            source_url,
            channel_num_input.text(),
            channel_title_input.text()
        ))
        add_selected_button.setDefault(True)
        button_layout.addWidget(add_selected_button)
        
        add_all_button = QPushButton("Add All")
        add_all_button.clicked.connect(lambda: self.add_all_streams(
            streams,
            dialog,
            source_url,
            channel_num_input.text(),
            channel_title_input.text()
        ))
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
                st = stream.get('type', 'unknown')
                url_text = stream.get('url', 'N/A')
                if (st == 'browser') or (not can_vlc_preview(stream)):
                    preview_info.setText(
                        f"URL: {url_text}\nType: {st}\n\nPreview: not available in VLC (will open in Browser Mode)."
                    )
                else:
                    preview_info.setText(f"URL: {url_text}\nType: {st}")
        
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

    def add_single_stream_from_table(self, table: QTableWidget, dialog: QDialog, source_url: str = None, channel_num_text: str = None, channel_title_text: str = None):
        """Add a single stream when double-clicked from table.
        Optionally save as a channel if `channel_num_text` is provided."""
        current_row = table.currentRow()
        if current_row >= 0:
            title_item = table.item(current_row, 1)
            stream = title_item.data(Qt.ItemDataRole.UserRole)
            
            self.logger.info("Double-click: loading single stream into selected player")
            self.logger.debug("Stream: %s", stream.get('title'))

            # Browser-mode streams must be opened via WebEngine, not VLC
            if (stream.get('type') == 'browser'):
                self.add_url_to_browser_mode(stream.get('url', ''))
                self._maybe_save_channel_mapping(channel_num_text, channel_title_text, stream, source_url)
                dialog.accept()
                return
            
            # Use selected player if available
            if self.active_player:
                player = self.active_player
                self.logger.debug("Using selected player %s", player.player_id)
                # Note: source_url should be passed from show_stream_selection_dialog
                success = player.load_media(stream['url'], stream['title'], source_url=source_url)
                self.logger.info("Load result: %s", "success" if success else "failed")
                # Save channel mapping if provided
                self._maybe_save_channel_mapping(channel_num_text, channel_title_text, stream, source_url)
                dialog.accept()
                return
            
            # Fallback to first available player if none selected
            available_players = [p for p in self.players if not p.current_url]
            if available_players:
                player = available_players[0]
                self.set_active_player(player)  # Auto-select the chosen player
                self.logger.debug("Using first available player %s", player.player_id)
                success = player.load_media(stream['url'], stream['title'], source_url=source_url)
                self.logger.info("Load result: %s", "success" if success else "failed")
                # Save channel mapping if provided
                self._maybe_save_channel_mapping(channel_num_text, channel_title_text, stream, source_url)
                dialog.accept()
            else:
                self.logger.warning("No available players")
                QMessageBox.warning(dialog, "Grid Full", "All grid slots are occupied. Click a player to select it first.")
    
    def add_selected_streams_from_table(self, table: QTableWidget, dialog: QDialog, source_url: str = None, channel_num_text: str = None, channel_title_text: str = None):
        """Add selected streams from table to the grid.
        Optionally save as a channel if `channel_num_text` is provided."""
        selected_rows = sorted(set(item.row() for item in table.selectedItems()))
        
        if not selected_rows:
            QMessageBox.information(dialog, "No Selection", "Please select at least one stream.")
            return
        
        # For single selection, use only the selected player
        if len(selected_rows) == 1:
            row = selected_rows[0]
            title_item = table.item(row, 1)
            stream = title_item.data(Qt.ItemDataRole.UserRole)
            
            if self.active_player:
                player = self.active_player
                self.logger.info("Loading single selected stream into selected player %s", player.player_id)
                if (stream.get('type') == 'browser'):
                    self.add_url_to_browser_mode(stream.get('url', ''))
                    success = True
                else:
                    success = player.load_media(stream['url'], stream['title'], source_url=source_url)
                self.logger.info("Load result: %s", "success" if success else "failed")
                # Save channel mapping if provided
                self._maybe_save_channel_mapping(channel_num_text, channel_title_text, stream, source_url)
            else:
                QMessageBox.warning(dialog, "No Player Selected", "Please click a player box to select it first.")
                return
        else:
            # For multiple selections, warn the user and suggest using single selection
            reply = QMessageBox.question(
                dialog, 
                "Multiple Streams Selected", 
                f"You've selected {len(selected_rows)} streams, but only the first one will load into your selected player.\n\nProceed with loading just the first stream?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
                
            # Load only the first stream into selected player
            row = selected_rows[0]
            title_item = table.item(row, 1)
            stream = title_item.data(Qt.ItemDataRole.UserRole)
            
            if self.active_player:
                player = self.active_player
                self.logger.info(
                    "Loading first of %s streams into selected player %s",
                    len(selected_rows),
                    player.player_id,
                )
                if (stream.get('type') == 'browser'):
                    self.add_url_to_browser_mode(stream.get('url', ''))
                    success = True
                else:
                    success = player.load_media(stream['url'], stream['title'], source_url=source_url)
                self.logger.info("Load result: %s", "success" if success else "failed")
                # Save channel mapping if provided
                self._maybe_save_channel_mapping(channel_num_text, channel_title_text, stream, source_url)
            else:
                QMessageBox.warning(dialog, "No Player Selected", "Please click a player box to select it first.")
                return
        
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
    

    
    def add_all_streams(self, streams: List[Dict[str, str]], dialog: QDialog, source_url: str = None, channel_num_text: str = None, channel_title_text: str = None):
        """Add all streams to the grid.
        If a channel number is provided, save the first stream as a channel."""
        if not streams:
            return
            
        if len(streams) == 1:
            # Single stream - load into selected player
            stream = streams[0]
            if self.active_player:
                player = self.active_player
                success = player.load_media(stream['url'], stream['title'], source_url=source_url)
                # Save channel mapping if provided
                self._maybe_save_channel_mapping(channel_num_text, channel_title_text, stream, source_url)
            else:
                QMessageBox.warning(dialog, "No Player Selected", "Please click a player box to select it first.")
                return
        else:
            # Multiple streams - warn user and load only first into selected player
            reply = QMessageBox.question(
                dialog, 
                "Multiple Streams Found", 
                f"Found {len(streams)} streams, but only the first one will load into your selected player.\n\nProceed with loading just the first stream?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
                
            stream = streams[0]
            if self.active_player:
                player = self.active_player
                success = player.load_media(stream['url'], stream['title'], source_url=source_url)
                # Save channel mapping if provided
                self._maybe_save_channel_mapping(channel_num_text, channel_title_text, stream, source_url)
            else:
                QMessageBox.warning(dialog, "No Player Selected", "Please click a player box to select it first.")
                return
        
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
        """Set volume for all players with smooth transitions."""
        self.current_volume = volume
        self.volume_label.setText(f"{volume}%")
        # Delegate to centralized audio policy so solo/manual mute are respected
        self.enforce_audio_policy()
    
    def mute_all_players(self):
        """Mute or unmute all players."""
        # Check if any players are not manually muted
        any_unmuted = any(not getattr(player, '_manually_muted', False) for player in self.players if player.current_url)
        
        for player in self.players:
            if player.current_url:
                if any_unmuted:
                    if not getattr(player, '_manually_muted', False):
                        player.toggle_mute()
                else:
                    if getattr(player, '_manually_muted', False):
                        player.toggle_mute()
        
        self.mute_all_button.setText("🔊 Unmute All" if any_unmuted else "🔇 Mute All")
        self.status_bar.showMessage("Muted all players" if any_unmuted else "Unmuted all players")
    
    def force_audio_restore_all(self):
        """Emergency function to restore audio to all players - for troubleshooting."""
        for player in self.players:
            if hasattr(player, 'media_player') and player.media_player:
                player._manually_muted = False
                player._solo_silenced = False
                player.is_muted = False
                player._volume_before_mute = getattr(self, 'current_volume', 70)
                if hasattr(player, 'mute_button'):
                    player.mute_button.setText("🔊")
        
        # Turn off solo mode completely
        if hasattr(self, 'solo_mode_active'):
            self.solo_mode_active = False
            if hasattr(self, 'solo_mode_button'):
                self.solo_mode_button.setText("🎵 Solo Mode: OFF")
                # Reset button style to default
                self.solo_mode_button.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #4a9eff, stop:1 #357abd);
                        color: #ffffff;
                        border: none;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #5aafff, stop:1 #4585cd);
                    }
                """)
        
            # Apply normalized audio state after resets
            self.enforce_audio_policy()
        
            self.status_bar.showMessage("🔊 EMERGENCY AUDIO RESTORE - All players should have sound now", 10000)
    
    def toggle_solo_mode(self):
        """Toggle solo mode - completely isolates audio to selected player only."""
        self.solo_mode_active = not self.solo_mode_active
        
        if self.solo_mode_active:
            self.solo_mode_button.setText("🎵 Solo Mode: ON")
            self.solo_mode_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ff6b35, stop:1 #e55a2b);
                    color: #ffffff;
                    border: 1px solid #d14820;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ff7b45, stop:1 #f56a3b);
                }
            """)
            # Ensure we have an active player and apply policy
            if not self.active_player and self.players:
                self.set_active_player(self.players[0])
            self.refresh_audio_states()
            active_id = getattr(self.active_player, 'display_id', 1) if self.active_player else 1
            self.status_bar.showMessage(f"🎵 Solo Mode: ON - ONLY Player #{active_id} has audio")
        else:
            self.solo_mode_button.setText("🎵 Solo Mode: OFF")
            self.solo_mode_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #4a9eff, stop:1 #357abd);
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #5aafff, stop:1 #4585cd);
                }
            """)
            self.refresh_audio_states()
            self.status_bar.showMessage("🎵 Solo Mode: OFF - All players restored")
    
    def handle_solo_activated(self, solo_player):
        """Handle when a player activates solo mode.
        Hides all other players and expands solo_player to fill the grid."""
        # First, turn off solo on all other players
        for player in self.players:
            if player != solo_player and hasattr(player, 'is_solo') and player.is_solo:
                player.is_solo = False
                player.solo_button.setText("🎯")
                # Reset button style
                button_style = """
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #4a4a4a, stop:1 #3a3a3a);
                        color: #ffffff;
                        border: 1px solid #555;
                        border-radius: 6px;
                        font-size: 11pt;
                        font-weight: bold;
                        padding: 2px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #5a5a5a, stop:1 #4a4a4a);
                        border: 1px solid #666;
                    }
                """
                player.solo_button.setStyleSheet(button_style)
                player.solo_button.setToolTip("Solo this player (mute all others & scale)")
        
        # Hide all other players; audio will be handled centrally
        for player in self.players:
            if player != solo_player:
                player.hide()
        
        # Show solo player at full size
        solo_player.show()
        # Force solo player to expand to fill available space
        solo_player.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Process events to update layout
        QApplication.processEvents()
        solo_player.resize(self.central_widget().size())
        
        # Re-apply centralized audio policy for solo state
        self.enforce_audio_policy()
    
    def handle_solo_deactivated(self, solo_player):
        """Handle when a player deactivates solo mode.
        Shows all hidden players and restores the full grid."""
        # Show all players again
        for player in self.players:
            player.show()
        
        # Restore size policies for all players to share grid space
        for player in self.players:
            player.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Restore audio via centralized policy
        self.enforce_audio_policy()
    
    def clear_all_solo(self):
        """Clear solo mode from all players."""
        for player in self.players:
            if hasattr(player, 'is_solo') and player.is_solo:
                player.is_solo = False
                player.solo_button.setText("🎯")
                # Reset button style
                button_style = """
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #4a4a4a, stop:1 #3a3a3a);
                        color: #ffffff;
                        border: 1px solid #555;
                        border-radius: 6px;
                        font-size: 11pt;
                        font-weight: bold;
                        padding: 2px;
                    }
                """
                player.solo_button.setStyleSheet(button_style)
                player.solo_button.setToolTip("Solo this player (mute all others)")
        
        # Restore all players audio
        self.handle_solo_deactivated(None)
    
    def toggle_control_panel(self):
        """Toggle control panel visibility (also called by auto-hide logic)."""
        self.control_panel_visible = not self.control_panel_visible
        self.control_panel.setVisible(self.control_panel_visible)

    def _poll_hover_autohide(self):
        """Poll mouse position every ~80 ms to implement auto-hide taskbar behaviour."""
        if not self.isVisible():
            return
        # Suspend auto-hide while in fullscreen player mode
        if getattr(self, '_player_fullscreen_active', False):
            return

        try:
            from PyQt6.QtGui import QCursor
        except ImportError:
            from PyQt5.QtGui import QCursor

        cursor_global = QCursor.pos()
        pos = self.mapFromGlobal(cursor_global)

        # Reveal zone: top 20px of the window
        TRIGGER_Y = 20
        panel_h = self.control_panel.sizeHint().height() + 8 if self.control_panel else 130

        if not self.control_panel_visible and pos.y() <= TRIGGER_Y and 0 <= pos.x() <= self.width():
            # Mouse entered the top strip → reveal panel, cancel any pending hide
            self.control_panel_visible = True
            self.control_panel.setVisible(True)
            self._autohide_delay_timer.stop()
        elif self.control_panel_visible:
            if pos.y() <= panel_h:
                # Mouse is over the panel — keep it visible
                self._autohide_delay_timer.stop()
            else:
                # Mouse moved below panel — start the countdown if not already set
                if not self._autohide_delay_timer.isActive():
                    self._autohide_delay_timer.start()

    def _run_autohide(self):
        """Called after the delay timer fires; hides the panel if mouse is still away."""
        try:
            from PyQt6.QtGui import QCursor
        except ImportError:
            from PyQt5.QtGui import QCursor

        if not self.control_panel_visible:
            return
        panel_h = self.control_panel.sizeHint().height() + 8 if self.control_panel else 130
        pos = self.mapFromGlobal(QCursor.pos())
        if pos.y() > panel_h:
            self.control_panel_visible = False
            self.control_panel.setVisible(False)
    
    def handle_no_streams_found(self, url: str):
        """Handle case when no streams are found.

        For JavaScript-heavy sites (e.g., LocalNow), the correct behavior is to load the URL
        directly in browser mode rather than showing a dead-end dialog.
        """
        self.load_url_directly(url)

    def load_url_directly(self, url: str):
        """Load a URL directly.

        - Direct media URLs (e.g., .m3u8/.mp4) load in VLC.
        - Web pages load in browser mode when available.
        """
        is_direct_video = any(
            url.lower().endswith(ext)
            for ext in ['.m3u8', '.mp4', '.webm', '.ogg', '.avi', '.mov', '.flv', '.mkv', '.ts']
        )

        if is_direct_video or (not WEBENGINE_AVAILABLE):
            self.add_url_to_grid(url)
            return

        self.add_url_to_browser_mode(url)
    
    def add_url_to_browser_mode(self, url: str):
        """Add URL to grid in browser mode."""
        # Use selected player if available
        target_player = self.active_player
        
        # Fallback to first available player if none selected
        if not target_player:
            for player in self.players:
                if not player.current_url:
                    target_player = player
                    self.set_active_player(player)
                    break
        
        if not target_player:
            QMessageBox.warning(self, "Grid Full", "All grid slots are occupied. Click a player to select it first.")
            return
        
        # Switch player to browser mode and load URL
        target_player.browser_mode = True
        target_player.mode_stack.setCurrentIndex(1)
        target_player.mode_button.setText("📺")
        target_player.mode_button.setToolTip("Switch to VLC mode")
        target_player.fullscreen_button.setVisible(True)
        target_player.status_label.setText("🌐")
        
        # Load URL in browser
        target_player.load_url_in_browser(url)
        
        player_id = getattr(target_player, 'display_id', getattr(target_player, 'player_id', 'unknown'))
        self.status_bar.showMessage(f"Loaded in browser mode on Player #{player_id}: {url}")
        self.logger.info("Added to browser mode on Player %s: %s", player_id, url)
    
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
                    'title': player.get_display_text(),
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
            self._apply_state(state)
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
                        'original_page': getattr(player, 'source_url', None) or getattr(player, 'source_page', None)
                    }
                    continue
                
                # Check if stream needs refresh (refresh every 25 minutes for 30min tokens)
                last_refresh = self.active_streams[url]['last_refresh']
                if current_time - last_refresh > 1500:  # 25 minutes
                    self.logger.info("Refreshing time-sensitive stream: %s", url)
                    self.refresh_stream_token(player, url)
    
    def refresh_stream_token(self, player, old_url):
        """Refresh a stream with expiring token."""
        source_page = self.active_streams.get(old_url, {}).get('original_page') or getattr(player, 'source_url', None)
        if not source_page:
            self.logger.warning("No source page available for token refresh")
            return
            
        self.logger.info("Extracting fresh streams from: %s", source_page)
        
        def refresh_worker():
            try:
                # Re-extract streams from the original page using the process pool
                future = self.submit_stream_extraction(source_page)
                streams = future.result(timeout=90)
                
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
                    self.logger.warning("No fresh stream found for refresh")
                    
            except Exception as e:
                self.logger.error("Error refreshing stream: %s", e)
        
        # Run in background
        self.thread_pool.submit(refresh_worker)
    
    def apply_stream_refresh(self, player, new_stream, source_page):
        """Apply refreshed stream to player."""
        import time
        
        old_url = player.current_url
        new_url = new_stream['url']
        
        self.logger.info("Applying refreshed stream: %s", new_stream.get('title'))
        
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
            player.source_url = source_page
            
            self.logger.info("Stream refresh successful")
    
    def _refresh_idle_channels(self):
        """Refresh cached tokens for idle channels while app is idle (background task).
        Ensures next channel switch is fast even if token expired."""
        import time
        current_time = time.time()
        
        # Only refresh if idle for 5+ seconds (not actively tuning)
        if current_time - self._last_channel_tune_time < 5:
            return  # User is actively changing channels, skip
        
        try:
            # Find channels without cached tokens (need extraction)
            to_refresh = []
            for num, ch in self.channels.items():
                if (not ch.get('url') or not self._is_cached_stream_valid(num)) and ch.get('source_url'):
                    to_refresh.append((num, ch))
            
            if not to_refresh:
                return  # All channels already cached
            
            # Refresh up to 2 channels per cycle (low-priority background task)
            for num, ch in to_refresh[:2]:
                src = ch.get('source_url')
                if src:
                    if num in self._idle_refresh_pending:
                        continue
                    self._idle_refresh_pending.add(num)
                    future = self.submit_stream_extraction(src)
                    
                    def on_idle_refresh_done(n=num, f=future):
                        """Called once on main thread when future completes."""
                        try:
                            candidate = _select_best_stream(f.result(timeout=0))
                            if candidate:
                                url = candidate.get('url')
                                stype = candidate.get('type', '')
                                if url and _is_playable_stream(url, stype):
                                    self._cache_channel_stream(n, url, stype)
                                    self.logger.debug(f"Idle refresh cached token for channel {n}")
                        except Exception as e:
                            self.logger.debug(f"Idle refresh error for channel {n}: {e}")
                        finally:
                            self._idle_refresh_pending.discard(n)

                    # Dispatch to main thread exactly once when future finishes (no busy-wait)
                    future.add_done_callback(
                        lambda f, n=num: QTimer.singleShot(0, lambda: on_idle_refresh_done(n, f))
                    )
        except Exception as e:
            self.logger.debug(f"Idle channel refresh error: {e}")
    
    def closeEvent(self, event):
        """Handle application close event with proper cleanup and logging."""
        self.logger.info("Application shutdown initiated")
        self.action_logger.info("Application closing")
        
        try:
            # Stop all players
            for player in self.players:
                try:
                    player.destroy_vlc()
                except Exception as e:
                    self.logger.error(f"Error destroying player {player.player_id}: {e}")
            
            # Shutdown thread pool
            self.thread_pool.shutdown(wait=False)
            if getattr(self, 'extractor_pool', None):
                self.extractor_pool.shutdown(wait=False)
            
            self.logger.info("Application shutdown completed successfully")
            self.action_logger.info("Application closed")
            
        except Exception as e:
            self.logger.error(f"Error during application shutdown: {e}")
        
        event.accept()


# Backward-compatible name for legacy entrypoints/imports.
WebGridPlayer = ADHDTVPlayer


def main(app_state: Optional[Any] = None, config: Optional[Dict[str, Any]] = None):
    """Main entry point."""
    config = config or {}
    app_name = config.get("app_name", APP_NAME)
    app_version = config.get("version", "0.0.0")
    setup_logging(app_name=app_name, log_level=config.get("logging", {}).get("level", "INFO"))

    # Enable HiDPI-aware auto scaling so the UI resizes smoothly while dragging between displays
    try:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        try:
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName(app_name)
    app.setApplicationVersion(app_version)
    
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
    window = WebGridPlayer(app_state=app_state, config=config)
    if window.display_mode == "fullscreen":
        window.showFullScreen()
    elif window.display_mode == "maximized":
        window.showMaximized()
    else:
        # Prefer a screen-filling start unless user explicitly asks for windowed mode
        if os.environ.get("ADHDTV_WINDOWED") == "1":
            window.show()
        else:
            window.showMaximized()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
