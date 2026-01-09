

# Main AD-HDTV module: exports ADHDTVPlayer, VideoPlayer, VideoStreamExtractor
import sys
import os
import logging
from pathlib import Path

APP_NAME = "AD-HDTV"
LOGGER_NAME = "adhdtv"
ACTION_LOGGER_NAME = "adhdtv.actions"

try:
    from PyQt6.QtWidgets import QMainWindow, QFrame, QLabel
    from PyQt6.QtCore import Qt
except ImportError:
    from PyQt5.QtWidgets import QMainWindow, QFrame, QLabel
    from PyQt5.QtCore import Qt

from audio_manager import AUDIO_MANAGER

class VideoStreamExtractor:
    """Extracts video streams from web pages."""
    def __init__(self):
        self.logger = logging.getLogger(f"{LOGGER_NAME}.extractor")

class VideoPlayer(QFrame):
    """Individual video player widget with VLC integration."""
    def __init__(self, player_id: int, parent=None):
        super().__init__(parent)
        self.player_id = player_id
        self.audio_channel_id = f"player_{player_id}"
        self.is_active = False

    def request_audio(self, source):
        AUDIO_MANAGER.play(self.audio_channel_id, source)

    def stop_audio(self):
        AUDIO_MANAGER.stop(self.audio_channel_id)

    def fade_out_audio(self):
        AUDIO_MANAGER.fade_out(self.audio_channel_id)

    def release_audio(self):
        AUDIO_MANAGER.stop(self.audio_channel_id)

class SilentChannel(QFrame):
    """A fallback silent channel for guaranteed silence."""
    def __init__(self, parent=None):
        super().__init__(parent)
        label = QLabel("STANDBY / LOADING", self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter)

class ADHDTVPlayer(QMainWindow):
    """Main application window."""
    def __init__(self, app_state=None, config=None):
        super().__init__()
        self.app_state = app_state
        self.config = config or {}
        self.audio_manager = AUDIO_MANAGER
        self.silent_channel = SilentChannel(self)
        self.debug_audio_overlay = None
        self._init_audio_overlay()

    def _init_audio_overlay(self):
        if os.environ.get("ADHDTV_DEV_MODE") == "1":
            self.debug_audio_overlay = QLabel(self)
            self.debug_audio_overlay.setStyleSheet("background: #222; color: #fff; padding: 4px; font-size: 12px;")
            self.debug_audio_overlay.move(10, 10)
            self.debug_audio_overlay.resize(300, 40)
            self.debug_audio_overlay.show()
            self.update_audio_overlay()

    def update_audio_overlay(self):
        if self.debug_audio_overlay:
            info = self.audio_manager.debug_overlay_info()
            self.debug_audio_overlay.setText(f"Audio: {info['audio_state']} | Channel: {info['active_channel']} | Vol: {info['volume']}")

    def closeEvent(self, event):
        self.audio_manager.stop_all()
        event.accept()
