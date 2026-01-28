import logging
from typing import Optional, Callable, Any

class AudioDirector:
    def __init__(self,
                 mute_all_except: Optional[Callable[[Optional[str]], None]] = None,
                 stop_source: Optional[Callable[[str], None]] = None,
                 set_source_volume: Optional[Callable[[str, int], None]] = None):
        self._solo_source_id: Optional[str] = None
        self._muted: bool = False
        self._volume: int = 100
        self._mute_all_except = mute_all_except or self._default_mute_all_except
        self._stop_source = stop_source or self._default_stop_source
        self._set_source_volume = set_source_volume or self._default_set_source_volume

    def set_solo(self, source_id: str):
        logging.info(f"AudioDirector: Soloing source {source_id}")
        self._solo_source_id = source_id
        self._mute_all_except(source_id)

    def clear_solo(self):
        logging.info("AudioDirector: Clearing solo source")
        self._solo_source_id = None
        self._mute_all_except(None)

    def set_muted(self, value: bool):
        logging.info(f"AudioDirector: Muted set to {value}")
        self._muted = value
        if value:
            self._mute_all_except(None)
        else:
            if self._solo_source_id:
                self._mute_all_except(self._solo_source_id)

    def set_volume(self, value: int):
        logging.info(f"AudioDirector: Volume set to {value}")
        self._volume = max(0, min(100, value))
        if self._solo_source_id:
            self._set_source_volume(self._solo_source_id, self._volume)

    @staticmethod
    def _default_mute_all_except(source_id: Optional[str]):
        logging.info(f"[AudioDirector] Would mute all except: {source_id}")

    @staticmethod
    def _default_stop_source(source_id: str):
        logging.info(f"[AudioDirector] Would stop source: {source_id}")

    @staticmethod
    def _default_set_source_volume(source_id: str, vol: int):
        logging.info(f"[AudioDirector] Would set volume for {source_id} to {vol}")
