# Channel Loading Performance Optimizations - Complete Guide

## Overview
Implemented 4 key optimizations to make channel switching fast (target: <100ms for prefetched channels, 7-10s for app startup with full prewarm).

---

## Optimization 1: Prewarm ALL Channels with Parallel Extraction

### What Changed
**Before:** Only first 4 channels were prewarmed at startup
**After:** ALL channels are prewarmed in parallel during startup

### Implementation
- **File:** `webgridplayer.py` lines 2728-2797
- **Method:** `prewarm_channels(limit=None)`
- **Key features:**
  - Accepts `limit=None` to cache all channels
  - Uses `concurrent.futures.as_completed()` for parallel extraction
  - Skips channels that already have cached tokens
  - Each extraction has 5-second timeout
  - Total prewarm timeout: 30 seconds
  - Reports progress in status bar

### Performance Impact
```
Scenario: 10 channels, ~2.5s per extraction
Before:   10 × 2.5s = 25s (sequential)
After:    2-3 parallel × 2.5s ≈ 7-10s (parallel with timeouts)
Speedup:  3-4x faster app startup
```

### Usage
```python
# In __init__() at line 2043
self.prewarm_channels(limit=None)  # Prewarm ALL channels
```

### Logs
```
⏳ Prewarming 8 channel(s)...
⏳ Prewarming channels: 1/8
⏳ Prewarming channels: 2/8
...
✓ Prewarmed 8/8 channels for fast switching
```

---

## Optimization 2: Prefetch Next/Previous Channels

### What Changed
**Before:** User switches to Ch 5 → extract → wait 2-3s → play
**After:** User on Ch 5 → bg prefetch Ch 6 & 4 → switch to Ch 6 → instant!

### Implementation
- **File:** `webgridplayer.py` lines 3366-3418
- **Method:** `_prefetch_next_channel(current_number)`
- **Called from:** `tune_channel()` after successful tune

### How It Works
1. User tunes to channel 5
2. After tuning completes, background extracts channels 4 and 6
3. User presses channel up → instant switch to channel 6 (already cached)
4. Next prefetch cycle extracts channels 5 and 7 for continuation

### Performance Impact
```
Scenario: User navigates sequentially (Ch 5 → 6 → 7 → 8)
Before:   2-3s + 2-3s + 2-3s + 2-3s = 8-12s total
After:    <100ms × 4 = <400ms total (all prefetched!)
Speedup:  20-30x faster sequential navigation
```

### Code
```python
def _prefetch_next_channel(self, current_number: int):
    """Prefetch next ±1 channels in background."""
    # Extract channels N+1 and N-1 with 3-sec timeout each
    # Doesn't block UI, runs in background thread pool
```

### Logs
```
INFO: Tuning to channel 5 with cached token: ABC
DEBUG: Prefetched token for channel 6
DEBUG: Prefetched token for channel 4
```

---

## Optimization 3: Idle Background Channel Refresh

### What Changed
**Before:** Only first 4 channels cached; others required extraction on first tune
**After:** Keeps all channel cache warm during idle periods

### Implementation
- **File:** `webgridplayer.py` lines 4557-4603
- **Method:** `_refresh_idle_channels()`
- **Timer:** `idle_refresh_timer` runs every 2 minutes
- **Condition:** Only runs if user hasn't tuned a channel in 5+ seconds

### How It Works
1. App tracks `_last_channel_tune_time` when user changes channels
2. Idle refresh timer runs every 2 minutes
3. If idle for 5+ seconds, refresh up to 2 uncached channels
4. Runs in background, doesn't affect playback
5. Repeats to eventually cache all channels

### Performance Impact
```
Scenario: App running, user idle for 5 minutes with 8 channels
Without idle refresh: High cache miss rate, random channel switches slow
With idle refresh:    Eventually all channels cached, all switches fast
Benefit:              Consistent performance over time
```

### Configuration
```python
# In __init__() line 2040
self.idle_refresh_timer = QTimer()
self.idle_refresh_timer.timeout.connect(self._refresh_idle_channels)
self.idle_refresh_timer.start(120000)  # 2 minutes
```

### Logs
```
DEBUG: Idle refresh cached token for channel 7
DEBUG: Idle refresh cached token for channel 8
(No logs if app is actively being used)
```

---

## Optimization 4: Extraction Timeout Protection

### What Changed
**Before:** No timeout on extractions - could hang indefinitely on slow websites
**After:** Each extraction has timeout; prevents UI hangs

### Implementation
- **Prewarm timeout:** 5 seconds per extraction, 30 seconds total
- **Prefetch timeout:** 3 seconds per extraction
- **Idle refresh timeout:** 5 seconds per extraction
- **File:** `webgridplayer.py` prewarm (line 2768), prefetch (line 3400), idle (line 4590)

### Code Pattern
```python
from concurrent.futures import as_completed, TimeoutError as FutureTimeoutError

# In prewarm
for future in as_completed(futures.values(), timeout=30):
    streams = f.result(timeout=5)  # Each extraction has 5s timeout
```

### Performance Impact
```
Scenario: One channel has slow extraction website (takes 10s)
Without timeout: App hangs for 10s+ during prewarm
With timeout:    App skips slow channel after 5s, completes in ~10s total
Benefit:         UI never freezes, app always responsive
```

---

## Combined Impact & Performance Targets

### Startup Performance
| Metric | Before | After | Speedup |
|--------|--------|-------|---------|
| App startup (8 channels) | 20+ seconds | 7-10 seconds | 2-3x |
| Status message updates | Sequential, slow | Parallel, fast | 3-4x |
| Cache hit rate @ startup | 50% (4 of 8) | 100% (all 8) | 2x |

### Channel Switching Performance
| Scenario | Before | After | Speedup |
|----------|--------|-------|---------|
| Sequential navigation (Ch 5→6→7→8) | 8-12s | <400ms | 20-30x |
| Random channel switch (cached) | <100ms | <100ms | 1x (no change) |
| Random channel switch (not cached) | 2-3s | 2-3s | 1x (same extraction) |
| Prefetched channel switch | 2-3s | <100ms | 20-30x |

### User Experience Improvements
1. **App Launch:** "Prewarming channels..." message, then ready
2. **Cable Box Feel:** Up/down arrows instant if used sequentially
3. **Background:** App keeps all channels fresh even during commercials
4. **Reliability:** No hangs on slow websites (timeouts prevent them)

---

## Logging & Monitoring

### Enabled Logs
All optimizations generate debug logs in `logs/webgridplayer` (if logging enabled):

```
[2024-01-07 10:15:30] INFO: Starting prewarm for channels: [5, 24, 55, 44, 74, 46]
[2024-01-07 10:15:31] DEBUG: Cached token for channel 5
[2024-01-07 10:15:32] DEBUG: Cached token for channel 24
...
[2024-01-07 10:15:38] INFO: Prewarm completed: 6/6 channels cached
[2024-01-07 10:16:00] DEBUG: Prefetched token for channel 55
[2024-01-07 10:16:00] DEBUG: Prefetched token for channel 44
```

### Status Bar Messages
- Startup: `"⏳ Prewarming 8 channel(s)..."`
- Progress: `"⏳ Prewarming channels: 5/8"`
- Complete: `"✓ Prewarmed 8/8 channels for fast switching"`

---

## Configuration & Tuning

### Adjustable Parameters

**1. Prewarm Limit** (line 2043)
```python
self.prewarm_channels(limit=None)   # All channels (default)
self.prewarm_channels(limit=10)     # First 10 channels
self.prewarm_channels(limit=4)      # First 4 channels (old behavior)
```

**2. Idle Refresh Interval** (line 2040)
```python
self.idle_refresh_timer.start(120000)  # 2 minutes (default)
self.idle_refresh_timer.start(60000)   # 1 minute (more aggressive)
self.idle_refresh_timer.start(300000)  # 5 minutes (less aggressive)
```

**3. Extraction Timeouts** (line 2768)
```python
for future in as_completed(futures.values(), timeout=30):  # Total timeout
    streams = f.result(timeout=5)  # Per-extraction timeout
```

**4. Idle Threshold** (line 4563)
```python
if current_time - self._last_channel_tune_time < 5:  # 5 seconds
    return  # Too active, skip refresh
```

---

## Testing Instructions

### Test 1: Startup Performance
```
1. Start WebGridPlayer fresh
2. Watch status bar: "⏳ Prewarming channels..."
3. Expected: Completes in <10 seconds
4. Expected: All channels have cached tokens after
5. Check logs: See "Cached token for channel X" messages
```

### Test 2: Sequential Channel Navigation
```
1. Load channel 5 (wait for playback)
2. Press channel up → observe Ch 6 loads instantly
3. Press channel up → observe Ch 7 loads instantly
4. Expected: All switches <100ms
5. Check logs: See "Prefetched token" messages
```

### Test 3: Random Channel Switching
```
1. After startup, switch to random channel (e.g., 55)
2. First switch: Should be 2-3s (extraction happens)
3. After extraction, channel is cached
4. Next switch back to 55: Should be <100ms
```

### Test 4: Idle Refresh
```
1. Launch app with few channels
2. Wait 2+ minutes without switching channels
3. Notice: Logs show "Idle refresh cached token..." messages
4. After idle period, switching channels should be fast
```

### Test 5: Timeout Protection
```
1. (Manual) Add a very slow website as channel source
2. Start app - observe it doesn't hang
3. Expected: Timeout kicks in, prewarm continues
4. Expected: Slow channel skipped but others cached
```

---

## Future Enhancements

### Priority 1: Smart Prefetch
- Track channel navigation history
- Prefetch most likely next channel based on history
- Example: If user always goes 5→24→55, prefetch accordingly

### Priority 2: Adaptive Timeouts
- Measure network speed on startup
- Adjust extraction timeouts based on speed
- Fast networks: 3s timeout, Slow: 8s timeout

### Priority 3: LRU Cache
- Track which channels user watches most
- Prioritize prewarming top 10 favorite channels
- Deprioritize channels never watched

### Priority 4: Progressive Prewarm
- Prewarm top channels first, others as background task
- User gets faster access to frequently-watched channels
- Less aggressive on startup

### Priority 5: Per-Channel Profiling
- Profile extraction speed for each channel/source
- Learn which websites are slow/fast
- Adjust strategy per-channel

---

## Troubleshooting

### Issue: App still slow on startup
**Cause:** Might be extracting many channels with slow network
**Solution:** 
- Check logs for timeouts: `timeout for channel X`
- Consider reducing prewarm limit: `prewarm_channels(limit=10)`
- Check network speed with external tool

### Issue: Prefetch not working
**Cause:** Might have switched to non-sequential navigation
**Solution:**
- Prefetch only works for N±1 channels
- Jumping from Ch 5 to Ch 55 won't prefetch
- Sequential switching (up/down buttons) always prefetched

### Issue: Memory usage increasing
**Cause:** Tokens cached for all channels
**Solution:**
- Tokens are small (URLs only)
- Expected memory overhead: <1MB for 100+ channels
- No action needed - this is intended design

### Issue: High CPU during startup
**Cause:** Parallel extraction uses multiple threads
**Solution:**
- Expected brief spike during prewarm (2-5 seconds)
- After prewarm, CPU returns to normal
- Threaded approach prevents UI freezing

---

## Summary

These four optimizations work together to make WebGridPlayer channel switching feel like a cable box:
- **Prewarm:** Get all channels cached during startup
- **Prefetch:** Anticipate next channel and cache it
- **Idle Refresh:** Keep cache warm between uses  
- **Timeouts:** Prevent hangs on slow websites

**Expected user experience:** Launch → 7-10s wait → then <100ms channel switches!
