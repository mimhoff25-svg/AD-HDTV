# AD-HDTV Quick Start Guide 🚀

## 30-Second Setup

```bash
# 1. Download and run the installer
curl -sSL https://raw.githubusercontent.com/yourusername/adhdtv/main/install_adhdtv.sh | bash

# 2. Start AD-HDTV
./run_adhdtv.sh
```

## 2-Minute Demo

### Try the KIII Tower Cam Example:
1. **Launch AD-HDTV**: `python app.py`
2. **Fetch Web Stream**: `Web → Fetch from Web Page...`
3. **Enter URL**: `https://www.kiiitv.com/tower-cam`
4. **Select Stream**: Choose from extracted streams
5. **Play**: Click "Play All" button

### Try Local Videos:
1. **Drag & Drop**: Drop video files onto the window
2. **Grid Layout**: Change to `Grid → 2×2` for 4 videos
3. **Sync Play**: Use "Play All" for synchronized playback

## Key Features in 5 Minutes

| Feature | How To Use | Example |
|---------|------------|---------|
| **Multi-Grid** | `Grid` menu → Select layout | 2×2 for 4 videos |
| **Web Extract** | `Web` → `Fetch from Web Page` | News sites, cams |
| **Local Files** | Drag & drop or `Ctrl+O` | MP4, AVI, MKV |
| **Stream URLs** | `File` → `Add URL` | .m3u8, direct links |
| **Video Clip** | Set start/end times | 00:30 to 02:00 |
| **Volume** | Master volume slider | Controls all players |

## Troubleshooting in 1 Minute

| Problem | Quick Fix |
|---------|-----------|
| VLC Error | Install VLC: `sudo apt install vlc` |
| No Streams | Try different websites or direct URLs |
| High CPU | Use smaller grid (2×2 instead of 4×4) |
| PyQt Error | `pip install PyQt6` or `pip install PyQt5` |

## What Works Best

✅ **Great Sources**: Weather cams, HTML5 videos, HLS streams  
✅ **Perfect Grid**: 2×2 layout for balanced performance  
✅ **Ideal Use**: Security monitoring, sports analysis, content comparison  
✅ **Best Performance**: SSD storage, 8GB+ RAM, modern CPU

## Get Help

- **Examples**: Run `python examples.py`
- **Test**: Run `python test_stream_extraction.py`  
- **Issues**: https://github.com/yourusername/adhdtv/issues

---
**Ready to explore multi-video streaming? Launch AD-HDTV and start creating your perfect grid setup!** 🎬
