"""Channel interface for AD-HDTV."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Channel(ABC):
    """Base interface for channel modules."""

    @abstractmethod
    def init(self, state: Any) -> None:
        """Initialize channel resources."""
        raise NotImplementedError

    @abstractmethod
    def update(self, state: Any, dt: float) -> None:
        """Update channel state."""
        raise NotImplementedError

    @abstractmethod
    def render(self, context: Any) -> None:
        """Render channel output into the UI context."""
        raise NotImplementedError
