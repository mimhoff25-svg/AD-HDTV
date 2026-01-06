# WebGridPlayer - Chrome Remote Desktop Setup

## ✅ **WebGridPlayer is Now Running!**

You should see the WebGridPlayer window open in your Chrome Remote Desktop session.

## 🚀 **Quick Launch Commands**

### Option 1: Using the run script (recommended)
```bash
cd /home/mike/projects/webgridplayer
./run_webgridplayer.sh
```

### Option 2: Direct launch
```bash
cd /home/mike/projects/gridplayer
source venv/bin/activate
export DISPLAY=:20
python /home/mike/projects/webgridplayer/webgridplayer.py
```

### Option 3: From desktop icon
- Look for "WebGridPlayer" in your application menu
- Or double-click the desktop shortcut if you created one

## 🎮 **Getting Started**

### Test with a sample video:
1. **Drag & Drop**: Find a video file and drag it onto WebGridPlayer
2. **Or use Web Fetch**: 
   - Go to `Web → Fetch from Web Page...`
   - Enter: `https://www.w3schools.com/html/html5_video.asp`
   - Select the video streams found
   - Click "Add Selected to Grid"
3. **Play**: Click the "▶ Play All" button

### Try the grid layouts:
- `Grid → 2×2` for 4 videos
- `Grid → 3×3` for 9 videos

## 🔧 **Troubleshooting**

### If the window doesn't appear:
```bash
# Check if it's running:
ps aux | grep webgridplayer

# Kill any stuck processes:
pkill -f webgridplayer

# Check display:
echo $DISPLAY  # Should show :20 for Chrome Remote Desktop

# Re-launch:
./run_webgridplayer.sh
```

### If you get import errors:
```bash
# Make sure you're using the gridplayer venv:
cd /home/mike/projects/gridplayer
source venv/bin/activate
python /home/mike/projects/webgridplayer/webgridplayer.py
```

## 📝 **Notes for Chrome Remote Desktop**

- **Display**: Chrome Remote Desktop uses display `:20`
- **The run script auto-detects this**, but you can manually set it:
  ```bash
  export DISPLAY=:20
  ```
- **Performance**: Chrome Remote Desktop may add some video latency
- **Best grid size**: Use 2×2 for optimal performance over remote desktop

## 🎬 **Example Workflows**

### 1. Local Videos:
```bash
# Navigate to your videos
cd ~/Videos
# Drag them onto WebGridPlayer window
```

### 2. Streaming URLs:
```bash
# In WebGridPlayer:
# File → Add URL...
# Paste: http://example.com/stream.m3u8
```

### 3. Web Extraction:
```bash
# In WebGridPlayer:
# Web → Fetch from Web Page...
# Try: https://www.kiiitv.com/tower-cam
# or: https://www.w3schools.com/html/html5_video.asp
```

## 💡 **Tips**

- Use `Ctrl+O` to quickly open files
- Use `Ctrl+F` to fetch from web pages
- Start with 2×2 grid for better performance
- Volume control affects all players simultaneously
- Video clipping works great for looping segments

---

**Enjoy multi-video streaming with WebGridPlayer!** 🎥