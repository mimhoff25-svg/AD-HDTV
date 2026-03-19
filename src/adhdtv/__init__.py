"""Public API surface for the AD-HDTV package.

This module re-exports the most commonly used classes so that callers can simply::

    from adhdtv import VideoPlayer, VideoStreamExtractor, ADHDTVPlayer

The actual implementations live in :mod:`webgridplayer`, but exposing them here keeps
backwards compatibility with earlier release documentation and the automated tests.
"""

from __future__ import annotations

try:
    from webgridplayer import ADHDTVPlayer, VideoPlayer, VideoStreamExtractor
except Exception as exc:  # pragma: no cover - import guard for diagnostics
    # Re-raise with clearer context so import errors surface during diagnostics.
    raise ImportError("Unable to import AD-HDTV core classes from webgridplayer") from exc

__all__ = [
    "VideoPlayer",
    "VideoStreamExtractor",
    "ADHDTVPlayer",
]
