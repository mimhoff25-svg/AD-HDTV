from dataclasses import dataclass, field, asdict
from datetime import UTC, datetime
from threading import Lock
from typing import Optional, Dict, Any, Union

def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Selected:
    channel_id: Union[str, int]
    row: Optional[int] = None
    col: Optional[int] = None
    start_time_iso: Optional[str] = None

@dataclass
class AudioState:
    solo_source_id: Optional[Union[str, int]] = None
    muted: bool = False
    volume: int = 100

@dataclass
class State:
    version: str
    started_at: datetime
    current_channel_id: Union[str, int]
    current_channel_name: str
    playing: bool = True
    guide_visible: bool = False
    selected: Selected = field(default_factory=lambda: Selected(channel_id=None))
    audio: AudioState = field(default_factory=AudioState)
    last_updated_at: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['started_at'] = self.started_at.isoformat()
        d['last_updated_at'] = self.last_updated_at.isoformat()
        return d

# Thread-safe wrapper for State (used by StateManager)
class ThreadSafeState:
    def __init__(self, state: State):
        self._state = state
        self._lock = Lock()

    def get(self) -> State:
        with self._lock:
            return self._state

    def update(self, fn):
        with self._lock:
            fn(self._state)
