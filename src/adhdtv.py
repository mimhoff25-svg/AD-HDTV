
# Main AD-HDTV module: exports ADHDTVPlayer, VideoPlayer, VideoStreamExtractor
import sys
import os
import logging
from pathlib import Path

APP_NAME = "AD-HDTV"
LOGGER_NAME = "adhdtv"
ACTION_LOGGER_NAME = "adhdtv.actions"

try:
    from PyQt6.QtWidgets import QMainWindow, QFrame
except ImportError:
    from PyQt5.QtWidgets import QMainWindow, QFrame

class VideoStreamExtractor:
    """Extracts video streams from web pages."""
    def __init__(self):
        self.logger = logging.getLogger(f"{LOGGER_NAME}.extractor")

class VideoPlayer(QFrame):
    """Individual video player widget with VLC integration."""
    def __init__(self, player_id: int, parent=None):
        super().__init__(parent)
        self.player_id = player_id

class ADHDTVPlayer(QMainWindow):
    """Main application window."""
    def __init__(self, app_state=None, config=None):
        super().__init__()
        self.app_state = app_state
        self.config = config or {}


__all__ = ["ADHDTVPlayer", "VideoPlayer", "VideoStreamExtractor"]

# Entrypoint: launch the app if run as a script
if __name__ == "__main__":
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        from PyQt5.QtWidgets import QApplication

    import sys
    app = QApplication(sys.argv)
    window = ADHDTVPlayer()
    window.show()
    sys.exit(app.exec())
