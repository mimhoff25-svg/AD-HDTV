"""
Guide data model, adapters, and rendering utilities for AD-HDTV.

This module is intentionally self-contained: the UI renderer consumes the
normalized GuideData structure and does not depend on the TVMaze API shape.
"""

from __future__ import annotations

import logging
import math
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

logger = logging.getLogger("adhdtv.guide")


# ------------------------- Data model ------------------------- #


@dataclass(frozen=True)
class ChannelInfo:
    id: str
    name: str
    number: int
    logo_path: Optional[Path] = None


@dataclass(frozen=True)
class ProgramEntry:
    channel_id: str
    title: str
    start_time: datetime
    duration_minutes: int


@dataclass
class GuideData:
    channels: List[ChannelInfo]
    programs: List[ProgramEntry]


# ------------------------- Logo resolver ------------------------- #


class LogoResolver:
    """Resolve channel logos from a local LyngSat-style pack."""

    def __init__(self, logos_dir: Path):
        self.logos_dir = logos_dir
        self.cache: Dict[str, Optional[Path]] = {}

    @staticmethod
    def _normalize(name: str) -> str:
        return "".join(ch for ch in name.lower() if ch.isalnum() or ch in ("-", "_"))

    def resolve(self, channel_name: str) -> Optional[Path]:
        key = self._normalize(channel_name)
        if key in self.cache:
            return self.cache[key]

        candidates = [
            self.logos_dir / f"{key}.png",
            self.logos_dir / f"{key}.jpg",
            self.logos_dir / f"{key}.jpeg",
        ]
        for path in candidates:
            if path.exists():
                self.cache[key] = path
                return path

        self.cache[key] = None
        return None


# ------------------------- TVMaze adapter ------------------------- #


class TVMazeAdapter:
    """Fetch schedule data from TVMaze and normalize it into the GuideData model."""

    API_URL = "https://api.tvmaze.com/schedule"

    def __init__(self, logo_resolver: LogoResolver | None = None):
        self.logo_resolver = logo_resolver

    @staticmethod
    def _normalize_channel_name(value: str) -> str:
        return "".join(ch for ch in value.lower() if ch.isalnum())

    def fetch(
        self,
        date: Optional[datetime] = None,
        country: str = "US",
        max_channels: int = 150,
        known_channels: List[Tuple[int, str]] | None = None,
    ) -> GuideData:
        target_date = (date or datetime.utcnow()).strftime("%Y-%m-%d")
        params = {"country": country, "date": target_date}

        resp = requests.get(self.API_URL, params=params, timeout=12)
        resp.raise_for_status()
        items = resp.json() or []

        # Build known channel lookup to reuse existing numbers where names match.
        known_lookup: Dict[str, Tuple[int, str]] = {}
        for number, title in known_channels or []:
            key = self._normalize_channel_name(title)
            if key:
                known_lookup[key] = (number, title)

        channels: Dict[str, ChannelInfo] = {}
        programs: List[ProgramEntry] = []
        next_virtual_number = 900  # Assign unmatched networks to high numbers.

        for entry in items:
            show = entry.get("show") or {}
            network = show.get("network") or show.get("webChannel") or {}
            network_name = network.get("name") or show.get("name") or "Unknown"
            key = self._normalize_channel_name(network_name)
            if not key:
                continue

            if key in known_lookup:
                ch_number, ch_name = known_lookup[key]
            else:
                ch_number, ch_name = next_virtual_number, network_name
                next_virtual_number += 1

            if key not in channels and len(channels) < max_channels:
                logo_path = self.logo_resolver.resolve(network_name) if self.logo_resolver else None
                channels[key] = ChannelInfo(
                    id=key,
                    name=network_name,
                    number=ch_number,
                    logo_path=logo_path,
                )

            # Skip programs if channel cap reached
            if key not in channels:
                continue

            start_iso = entry.get("airstamp") or entry.get("airdate")
            runtime = entry.get("runtime") or show.get("runtime") or 30
            try:
                start_time = datetime.fromisoformat(start_iso.replace("Z", "+00:00")).astimezone(None).replace(
                    tzinfo=None
                )
            except Exception:
                continue

            programs.append(
                ProgramEntry(
                    channel_id=key,
                    title=show.get("name") or "Unknown",
                    start_time=start_time,
                    duration_minutes=int(runtime),
                )
            )

        return GuideData(list(channels.values()), programs)


# ------------------------- Sample data for offline dev ------------------------- #


def build_sample_data(start: Optional[datetime] = None) -> GuideData:
    base = start or datetime.now().replace(minute=0, second=0, microsecond=0)
    channels = [
        ChannelInfo(id="news", name="NewsNet", number=2, logo_path=None),
        ChannelInfo(id="sports", name="SportsOne", number=5, logo_path=None),
        ChannelInfo(id="kids", name="KidsWorld", number=7, logo_path=None),
        ChannelInfo(id="movies", name="MovieMax", number=10, logo_path=None),
    ]
    programs: List[ProgramEntry] = []
    titles = {
        "news": ["Morning Update", "Local Live", "World Desk", "Evening Report"],
        "sports": ["Top Plays", "Live: City FC", "Halftime Desk", "Post Match"],
        "kids": ["Cartoon Hour", "Adventure Squad", "Learning Time", "Bedtime Tales"],
        "movies": ["Classic Cinema", "Indie Picks", "Blockbuster", "Late Night Noir"],
    }
    for ch in channels:
        start_time = base
        for title in titles[ch.id]:
            programs.append(
                ProgramEntry(
                    channel_id=ch.id,
                    title=title,
                    start_time=start_time,
                    duration_minutes=30,
                )
            )
            start_time += timedelta(minutes=30)
    return GuideData(channels=channels, programs=programs)


# ------------------------- Renderer ------------------------- #


class GuideCanvas(QGraphicsView):
    """Fixed-size TV Guide grid renderer (1280x720 canvas)."""

    CANVAS_W = 1280
    CANVAS_H = 720
    LEFT_W = 240
    HEADER_H = 70
    ROW_H = 70
    SLOT_MINUTES = 30
    SLOT_COUNT = 8  # 4 hours view by default

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedSize(self.CANVAS_W, self.CANVAS_H)
        self.scene = QGraphicsScene(0, 0, self.CANVAS_W, self.CANVAS_H)
        self.setScene(self.scene)
        self.logo_cache: Dict[str, QPixmap] = {}
        self.fallback_logo = self._build_fallback_logo()

    def _build_fallback_logo(self) -> QPixmap:
        pix = QPixmap(120, 60)
        pix.fill(QColor("#222"))
        painter = QPainter(pix)
        painter.setPen(QColor("#ccc"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(12)
        painter.setFont(font)
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "AD-HDTV")
        painter.end()
        return pix

    def _snap_start(self, start: datetime) -> datetime:
        minute = start.minute
        snapped = start.replace(minute=(0 if minute < 30 else 30), second=0, microsecond=0)
        return snapped

    def _slot_width(self) -> float:
        timeline_w = self.CANVAS_W - self.LEFT_W - 10
        return timeline_w / self.SLOT_COUNT

    def _load_logo(self, channel: ChannelInfo) -> QPixmap:
        key = channel.id
        if key in self.logo_cache:
            return self.logo_cache[key]
        if channel.logo_path and channel.logo_path.exists():
            pix = QPixmap(str(channel.logo_path))
            if not pix.isNull():
                scaled = pix.scaled(120, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.logo_cache[key] = scaled
                return scaled
        self.logo_cache[key] = self.fallback_logo
        return self.fallback_logo

    def render_guide(self, data: GuideData, start_time: datetime, selected_index: Optional[int] = None):
        self.scene.clear()
        slot_w = self._slot_width()
        start_time = self._snap_start(start_time)
        end_time = start_time + timedelta(minutes=self.SLOT_MINUTES * self.SLOT_COUNT)

        # Background
        self.scene.addRect(
            QRectF(0, 0, self.CANVAS_W, self.CANVAS_H),
            pen=QPen(Qt.PenStyle.NoPen),
            brush=QColor("#0d0d0d"),
        )

        # Header row: times
        header_y = 0
        header_bg = self.scene.addRect(
            QRectF(self.LEFT_W, header_y, self.CANVAS_W - self.LEFT_W, self.HEADER_H),
            pen=QPen(Qt.PenStyle.NoPen),
            brush=QColor("#1a1a1a"),
        )
        header_bg.setZValue(1)
        font = QFont("Helvetica", 10, QFont.Weight.Bold)
        for idx in range(self.SLOT_COUNT + 1):
            t = start_time + timedelta(minutes=idx * self.SLOT_MINUTES)
            x = self.LEFT_W + idx * slot_w
            line = self.scene.addLine(x, header_y, x, self.CANVAS_H, QPen(QColor("#333"), 1))
            line.setZValue(0.5)
            label = self.scene.addSimpleText(t.strftime("%I:%M %p").lstrip("0"), font)
            label.setBrush(QColor("#ccc"))
            label.setPos(x + 6, header_y + 10)

        # Channels column and program rows
        row_y = self.HEADER_H
        alt = [QColor("#101010"), QColor("#151515")]
        name_font = QFont("Helvetica", 10, QFont.Weight.Bold)
        prog_font = QFont("Helvetica", 9)

        # Index programs by channel
        progs_by_channel: Dict[str, List[ProgramEntry]] = {}
        for p in data.programs:
            progs_by_channel.setdefault(p.channel_id, []).append(p)
        for plist in progs_by_channel.values():
            plist.sort(key=lambda p: p.start_time)

        sorted_channels = sorted(data.channels, key=lambda c: c.number)
        for row_idx, channel in enumerate(sorted_channels):
            bg = self.scene.addRect(
                QRectF(0, row_y, self.CANVAS_W, self.ROW_H),
                pen=QPen(Qt.PenStyle.NoPen),
                brush=alt[row_idx % 2],
            )
            bg.setZValue(0)

            # Channel cell
            logo = self._load_logo(channel)
            logo_item = self.scene.addPixmap(logo)
            logo_item.setPos(10, row_y + (self.ROW_H - logo.height()) / 2)
            num_text = self.scene.addSimpleText(f"{channel.number}", name_font)
            num_text.setBrush(QColor("#5ac8fa"))
            num_text.setPos(self.LEFT_W - 90, row_y + 10)
            name_text = self.scene.addSimpleText(channel.name, prog_font)
            name_text.setBrush(QColor("#eee"))
            name_text.setPos(self.LEFT_W - 90, row_y + 32)

            # Program blocks
            for prog in progs_by_channel.get(channel.id, []):
                if prog.start_time >= end_time or prog.start_time + timedelta(minutes=prog.duration_minutes) <= start_time:
                    continue  # outside window
                offset_min_raw = (max(prog.start_time, start_time) - start_time).total_seconds() / 60.0
                offset_blocks = max(0, math.floor(offset_min_raw / self.SLOT_MINUTES))
                offset_min = offset_blocks * self.SLOT_MINUTES
                span_min = max(self.SLOT_MINUTES, prog.duration_minutes)
                span_slots = math.ceil(span_min / self.SLOT_MINUTES)
                x = self.LEFT_W + (offset_min / self.SLOT_MINUTES) * slot_w
                width = min(span_slots, self.SLOT_COUNT - offset_blocks) * slot_w
                if width <= 0:
                    continue
                rect = self.scene.addRect(QRectF(x, row_y + 8, width - 6, self.ROW_H - 16),
                                          pen=QPen(QColor("#333")), brush=QColor("#1f3b4d"))
                rect.setZValue(0.4)
                title = self.scene.addSimpleText(prog.title, prog_font)
                title.setBrush(QColor("#fefefe"))
                title.setPos(x + 8, row_y + 14)
                time_label = self.scene.addSimpleText(
                    f"{prog.start_time.strftime('%I:%M %p').lstrip('0')} • {prog.duration_minutes}m", prog_font
                )
                time_label.setBrush(QColor("#b0b0b0"))
                time_label.setPos(x + 8, row_y + 36)

            if selected_index is not None and row_idx == selected_index:
                highlight = self.scene.addRect(
                    QRectF(0, row_y, self.CANVAS_W, self.ROW_H),
                    pen=QPen(QColor("#4da3ff"), 2),
                    brush=QColor(0, 0, 0, 0),
                )
                highlight.setZValue(0.9)

            row_y += self.ROW_H

        # Footer hint
        footer = self.scene.addSimpleText("Use ◀ ▶ to move in time blocks • ▲ ▼ to move channels • Reload to fetch TVMaze",
                                          QFont("Helvetica", 9))
        footer.setBrush(QColor("#888"))
        footer.setPos(20, self.CANVAS_H - 24)


# ------------------------- Dialog wrapper ------------------------- #


class GuideDialog(QDialog):
    """Encapsulates fetching and rendering the guide in a fixed-size dialog."""

    def __init__(
        self,
        guide_data: GuideData,
        logo_resolver: LogoResolver,
        known_channels: List[Tuple[int, str]] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("AD-HDTV Guide")
        self.setFixedSize(1280, 780)  # A little extra for footer/actions
        self.canvas = GuideCanvas(self)
        self.logo_resolver = logo_resolver
        self.known_channels = known_channels or []
        self.current_data = guide_data
        self.current_start = datetime.now()
        self.status_label = QLabel("Loaded sample guide")
        self.selected_index = 0
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._build_layout()
        self._render()

    def _build_layout(self):
        main = QVBoxLayout(self)
        header = QHBoxLayout()

        self.prev_btn = QPushButton("◀ Earlier")
        self.prev_btn.clicked.connect(lambda: self._shift_time(-30))
        self.next_btn = QPushButton("Later ▶")
        self.next_btn.clicked.connect(lambda: self._shift_time(30))
        self.reload_btn = QPushButton("Reload from TVMaze")
        self.reload_btn.clicked.connect(self._reload_tvmaze)

        header.addWidget(self.prev_btn)
        header.addWidget(self.next_btn)
        header.addStretch()
        header.addWidget(self.reload_btn)

        main.addLayout(header)
        main.addWidget(self.canvas)
        main.addWidget(self.status_label)

    def _render(self):
        total = max(0, len(self.current_data.channels) - 1)
        if self.selected_index > total:
            self.selected_index = total
        self.canvas.render_guide(self.current_data, self.current_start, self.selected_index if total >= 0 else None)

    def _shift_time(self, minutes: int):
        self.current_start += timedelta(minutes=minutes)
        self._render()

    def _reload_tvmaze(self):
        self.status_label.setText("Fetching TVMaze schedule…")
        self.setEnabled(False)

        def work():
            try:
                adapter = TVMazeAdapter(self.logo_resolver)
                data = adapter.fetch(date=self.current_start, known_channels=self.known_channels)
                return data, ""
            except Exception as e:
                logger.error("TVMaze fetch failed: %s", e)
                return None, str(e)

        def done(result):
            data, err = result
            self.setEnabled(True)
            if data:
                self.update_data(data)
            else:
                self.status_label.setText(f"TVMaze failed: {err or 'Unknown error'} (using existing data)")

        thread_result: Dict[str, any] = {}

        def runner():
            thread_result["value"] = work()

        t = threading.Thread(target=runner, daemon=True)
        t.start()

        def poll():
            if "value" in thread_result:
                done(thread_result["value"])
            else:
                self.status_label.setText("Fetching TVMaze schedule…")
                QTimer.singleShot(150, poll)

        from PyQt6.QtCore import QTimer

        QTimer.singleShot(150, poll)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Left:
            self._shift_time(-30)
        elif key == Qt.Key.Key_Right:
            self._shift_time(30)
        elif key == Qt.Key.Key_PageUp:
            self._shift_time(-120)
        elif key == Qt.Key.Key_PageDown:
            self._shift_time(120)
        elif key == Qt.Key.Key_Up:
            if self.selected_index > 0:
                self.selected_index -= 1
                self._render()
        elif key == Qt.Key.Key_Down:
            if self.selected_index < max(0, len(self.current_data.channels) - 1):
                self.selected_index += 1
                self._render()
        else:
            super().keyPressEvent(event)

    def update_data(self, guide_data: GuideData):
        """Replace guide data and rerender."""
        self.current_data = guide_data
        self.status_label.setText(f"Guide loaded ({len(guide_data.channels)} channels)")
        self._render()


__all__ = [
    "ChannelInfo",
    "ProgramEntry",
    "GuideData",
    "LogoResolver",
    "TVMazeAdapter",
    "GuideDialog",
    "build_sample_data",
]
