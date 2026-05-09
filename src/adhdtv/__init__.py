"""Public API surface for the AD-HDTV package."""

from __future__ import annotations

__all__ = ["VideoPlayer", "VideoStreamExtractor", "ADHDTVPlayer"]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module 'adhdtv' has no attribute {name!r}")
    try:
        from webgridplayer import ADHDTVPlayer, VideoPlayer, VideoStreamExtractor
    except Exception as exc:  # pragma: no cover - import guard for diagnostics
        raise ImportError("Unable to import AD-HDTV core classes from webgridplayer") from exc
    exports = {
        "VideoPlayer": VideoPlayer,
        "VideoStreamExtractor": VideoStreamExtractor,
        "ADHDTVPlayer": ADHDTVPlayer,
    }
    return exports[name]
