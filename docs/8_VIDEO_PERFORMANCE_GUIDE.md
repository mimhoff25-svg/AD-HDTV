# WebGridPlayer 8-Video Performance Optimization Guide

## Overview
This guide covers optimizations implemented to handle 8 simultaneous video streams smoothly, reducing glitchiness and slowdowns.

## Key Performance Optimizations

### 1. VLC Instance Optimizations

**Reduced Caching for Faster Startup:**
- Network caching: 1000ms → 500ms
- Live caching: 1000ms → 300ms
- Per-stream HLS caching: 800ms → 200ms for network, 100ms for live

**Hardware Acceleration:**
- Enabled for all platforms: `--avcodec-hw=any`
- Platform-specific acceleration:
  - Linux: VAAPI (`--avcodec-hw=vaapi`)
  - Windows: DirectX (`--avcodec-hw=dxva2`) 
  - macOS: VideoToolbox (`--avcodec-hw=videotoolbox`)

**Threading Optimizations:**
- Limited decoder threads per stream: `--avcodec-threads=2` (instance) + `:avcodec-threads=1` (per-stream)
- Prevents thread contention with 8 concurrent streams

**Memory Optimizations:**
- Disabled statistics: `--no-stats`
- Disabled on-screen display: `--no-osd`
- Disabled video events: `--vout-event=0`
- Minimal interface: `--intf=dummy`

### 2. Audio Management

**Volume Optimization:**
- 8 streams: Default volume 40% (prevents audio conflicts)
- 6+ streams: Default volume 50%
- <6 streams: Default volume 70%

**Platform-specific Audio:**
- Linux: ALSA (`--aout=alsa`)
- Windows: DirectSound (`--aout=directsound`)
- macOS: Audio HAL (`--aout=auhal`)

### 3. Thread Pool Expansion

**Increased Worker Threads:**
- Before: 4 workers
- After: 8 workers (matches max video count)
- Named threads: `webgrid-*` for easier debugging

### 4. Performance Monitoring

**Real-time Metrics:**
- Active stream count tracking
- Failed stream detection
- Memory usage monitoring (2GB+ warnings)
- CPU usage alerts (80%+ warnings)

**Status Bar Updates:**
- Shows active stream count for 6+ videos
- Memory warnings for 3GB+ usage with 8 videos
- Performance logging every 2 minutes for 8-video setups

### 5. Stream-specific Optimizations

**HLS/M3U8 Streams (most common):**
- Ultra-low network caching (200ms)
- Minimal live caching (100ms)
- Single thread per stream
- 5-second network timeouts
- Disabled statistics per stream

**Connection Handling:**
- HTTP reconnection enabled
- 2-second network timeout
- Reduced clock jitter

## Performance Targets

| Video Count | Target Performance | Memory Usage | CPU Usage |
|-------------|-------------------|--------------|-----------|
| 1-4 videos  | Smooth, no issues | <1GB         | <30%      |
| 6 videos    | Occasional stutters| <2GB         | <50%      |
| 8 videos    | Playable with optimizations | <3GB | <80%      |

## System Requirements for 8 Videos

### Minimum:
- **CPU:** Quad-core 2.0GHz with hardware video acceleration
- **RAM:** 4GB system RAM
- **GPU:** Integrated graphics with hardware decoding support
- **Network:** 50Mbps for 8 concurrent streams

### Recommended:
- **CPU:** 8-core 2.5GHz+ or 6-core 3.0GHz+
- **RAM:** 8GB system RAM  
- **GPU:** Dedicated graphics with H.264/H.265 hardware decoding
- **Network:** 100Mbps+ with low latency

## Troubleshooting 8-Video Issues

### High Memory Usage (>3GB)
1. Check if hardware acceleration is working: Look for `avcodec-hw` in logs
2. Close other applications using video acceleration
3. Consider reducing from 8 to 6 videos
4. Restart WebGridPlayer to clear accumulated memory

### High CPU Usage (>80%)
1. Verify hardware decoding is enabled in your system
2. Check if multiple players are using software decoding
3. Reduce video quality/bitrate in source streams
4. Close CPU-intensive background applications

### Audio Glitches with 8 Videos
1. Volume automatically reduced to 40% - increase if needed
2. Use mute/audio focus features to reduce conflicts
3. Check if system audio is overloaded

### Video Stuttering/Freezing
1. Monitor network bandwidth - each stream needs 5-10Mbps
2. Check if streams are expired/need token refresh
3. Verify hardware acceleration is working
4. Consider using grid sizes: 2×3 (6 videos) vs 2×4 (8 videos)

## Best Practices for 8-Video Setup

### Grid Layout:
- **2×4 (8 videos):** Maximum density, requires good hardware
- **2×3 (6 videos):** Better performance balance
- **3×3 (9 videos):** Only for high-end systems

### Stream Selection:
- Prefer hardware-accelerated formats (H.264, H.265)
- Use lower bitrate streams when possible
- Avoid mixing drastically different stream qualities

### System Optimization:
- Close other video applications
- Ensure adequate cooling (hardware decoding generates heat)
- Use wired network connection for stability
- Keep WebGridPlayer updated for latest optimizations

## Performance Monitoring Commands

Check if optimizations are working:

```bash
# Check hardware acceleration support
vlc --intf dummy --list --advanced 2>/dev/null | grep -i accel

# Monitor system resources while running
htop
# or
top -p $(pgrep -f webgridplayer)

# Check network usage
iftop
# or  
nethogs
```

## Known Limitations

1. **8-video performance is system-dependent** - older hardware may struggle
2. **Network bandwidth requirements scale linearly** - 8 streams = 8× bandwidth
3. **Some streams may not support hardware acceleration** - impacts CPU usage
4. **Memory usage accumulates over time** - periodic restarts may be needed

## Future Optimizations

Potential improvements being considered:
- Adaptive quality switching based on system load
- Stream prioritization (focus player gets higher quality)
- More aggressive memory management
- GPU-based video processing pipeline
- Dynamic thread allocation based on system capabilities

---

*Last updated: January 2026*
*For support: Check logs in `logs/` directory for performance warnings*