# Channel Loading Performance Analysis

## Current Bottlenecks

### 1. **Prewarm Limited to 4 Channels**
- Only the first 4 channels are prewarmed on startup
- All other channels require extraction on first tune
- Each extraction takes 2-3 seconds (network + BeautifulSoup parsing)

### 2. **No Parallel Extraction**
- Prewarm extracts channels sequentially in callbacks
- Should extract multiple channels in parallel for faster startup

### 3. **Extraction Timeout**
- No timeout handling for slow source websites
- If a website is slow/unresponsive, extraction blocks for indefinite time

### 4. **Missing Token Cache Invalidation**
- Old/expired tokens aren't detected until playback fails
- Could validate tokens before playback and refresh preemptively

### 5. **No Background Preloading After Startup**
- Only first 4 channels prewarmed at startup
- Other channels could be extracted in background while user is watching

## Performance Targets

**Current:** 2-3 seconds per channel switch (waiting for extraction)  
**Target:** <500ms by using cached tokens

## Optimization Strategy

### Priority 1: Expand Prewarm Cache (Quick Win)
- Prewarm ALL channels (not just 4) in background at startup
- Use concurrent.futures with larger thread pool for parallel extraction
- Expected impact: 2-3 seconds → <1ms for most common channel switches

### Priority 2: Parallel Extraction (Medium)
- Extract multiple channels in parallel instead of sequential callbacks
- Use ThreadPoolExecutor with wait=ALL to coordinate
- Expected impact: Startup time 10+ seconds → 5-7 seconds

### Priority 3: Token Validation (Advanced)
- Check token expiry before playback
- Refresh expired tokens in background
- Expected impact: Reduces "token expired" errors mid-stream

### Priority 4: Extraction Timeout (Safety)
- Add configurable timeout to extract_streams()
- Skip slow/unresponsive channels after timeout
- Expected impact: Prevents UI hangs

## Implementation Plan

1. **Modify prewarm_channels():**
   - Cache ALL channels, not just first 4
   - Use concurrent.futures.wait() for parallel extraction
   - Add progress bar in status bar during prewarming

2. **Optimize tune_channel():**
   - Add metrics to log cache hit rate
   - Measure extraction time for each channel
   - Consider prefetching next channel during playback

3. **Add extraction timeout:**
   - Pass timeout parameter to extract_streams()
   - Add fallback mechanism if extraction fails

4. **Add background refresh:**
   - Periodically check/refresh channel tokens while idle
   - Re-extract channels with no tokens when app is idle

## Expected Results

| Operation | Before | After | Speedup |
|-----------|--------|-------|---------|
| App startup (8 channels) | 30+ sec | 7-10 sec | 3-4x |
| Channel switch (cached) | 2-3 sec | <100ms | 20-30x |
| Channel switch (cold) | 2-3 sec | 2-3 sec | 1x (same) |

## Implementation Complexity

- **Priority 1:** Low complexity, high impact
- **Priority 2:** Medium complexity, medium impact
- **Priority 3:** Medium complexity, safety improvement
- **Priority 4:** Low complexity, high reliability
