from datetime import UTC, datetime, timedelta
from .guide_model import Channel, Program, GuideResponse
from typing import List
import random

def round_down_to_30(dt):
    return dt.replace(minute=(dt.minute // 30) * 30, second=0, microsecond=0)

def generate_fake_guide(hours=2, start=None):
    now = datetime.now(UTC) if start is None else start
    start_time = round_down_to_30(now)
    minutes_per_slot = 30
    slot_count = int((hours * 60) // minutes_per_slot)
    channels = [
        Channel(id=f"ch{i+1}", number=str(100+i), name=f"Channel {i+1}", logo_key=f"logo_{i+1}")
        for i in range(8)
    ]
    programs = []
    for ch in channels:
        for slot in range(slot_count):
            prog_start = start_time + timedelta(minutes=slot * minutes_per_slot)
            prog = Program(
                channel_id=ch.id,
                title=f"Show {random.randint(1, 99)}",
                start_time_iso=prog_start.isoformat(),
                duration_minutes=minutes_per_slot
            )
            programs.append(prog)
    return GuideResponse(
        start_time_iso=start_time.isoformat(),
        minutes_per_slot=minutes_per_slot,
        slot_count=slot_count,
        channels=channels,
        programs=programs
    )
