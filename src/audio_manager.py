import logging
from enum import Enum, auto

class AudioState(Enum):
    IDLE = auto()
    PLAYING = auto()
    FADING = auto()
    STOPPED = auto()
    ERROR = auto()

class AudioManager:
    def __init__(self):
        self.logger = logging.getLogger("adhdtv.audio")
        self.active_channel = None
        self.active_source = None
        self.state = AudioState.IDLE
        self.volume = 100
        self._log_state()

    def play(self, channel_id, source):
        self.logger.info(f"Request to play audio: channel={channel_id}, source={source}")
        self.stop_all()
        # TODO: Integrate with VLC/Qt audio backend
        self.active_channel = channel_id
        self.active_source = source
        self.state = AudioState.PLAYING
        self._log_state()

    def stop(self, channel_id):
        if self.active_channel == channel_id:
            self.logger.info(f"Stopping audio for channel {channel_id}")
            self._hard_stop()

    def fade_out(self, channel_id):
        if self.active_channel == channel_id:
            self.logger.info(f"Fading out audio for channel {channel_id}")
            self.state = AudioState.FADING
            self._log_state()
            # TODO: Implement fade-out logic
            self._hard_stop()

    def stop_all(self):
        if self.state in (AudioState.PLAYING, AudioState.FADING):
            self.logger.info("Stopping all audio")
            self._hard_stop()

    def _hard_stop(self):
        # TODO: Integrate with VLC/Qt audio backend to stop and release resources
        self.state = AudioState.STOPPED
        self.active_channel = None
        self.active_source = None
        self._log_state()

    def set_volume(self, volume):
        self.volume = max(0, min(100, volume))
        self.logger.info(f"Set audio volume: {self.volume}")
        # TODO: Integrate with backend

    def _log_state(self):
        self.logger.info(f"Audio state: {self.state.name}, channel: {self.active_channel}, source: {self.active_source}, volume: {self.volume}")

    def get_state(self):
        return self.state

    def get_active_channel(self):
        return self.active_channel

    def get_volume(self):
        return self.volume

    def debug_overlay_info(self):
        return {
            "active_channel": self.active_channel,
            "audio_state": self.state.name,
            "volume": self.volume
        }

# Singleton instance for app-wide use
AUDIO_MANAGER = AudioManager()
