import threading
from typing import Callable, Dict, Any
from .state import State
from datetime import datetime

class StateManager:
    def __init__(self, state: State):
        self._state = state
        self._lock = threading.Lock()
        self._revision = 0

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            snap = self._state.to_dict()
            snap['revision'] = self._revision
            return snap

    def update(self, fn: Callable[[State], None]):
        with self._lock:
            fn(self._state)
            self._state.last_updated_at = datetime.utcnow()
            self._revision += 1

    def touch(self):
        with self._lock:
            self._state.last_updated_at = datetime.utcnow()
            self._revision += 1

    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision
