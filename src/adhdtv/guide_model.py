from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Channel:
    id: str
    number: str
    name: str
    logo_key: Optional[str] = None

@dataclass
class Program:
    channel_id: str
    title: str
    start_time_iso: str
    duration_minutes: int

@dataclass
class GuideResponse:
    start_time_iso: str
    minutes_per_slot: int
    slot_count: int
    channels: List[Channel] = field(default_factory=list)
    programs: List[Program] = field(default_factory=list)
