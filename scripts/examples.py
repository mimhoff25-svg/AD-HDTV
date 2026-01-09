#!/usr/bin/env python3
"""
AD-HDTV Usage Examples
Demonstrates how to use AD-HDTV for various video sources
"""

import sys
import os

def print_examples():
    """Print usage examples for AD-HDTV."""
    
    print("""
🎥 AD-HDTV Usage Examples
================================

AD-HDTV is a powerful multi-video player that can play multiple videos
simultaneously in a grid layout, with advanced web stream extraction capabilities.

📋 Basic Commands:
   python app.py                              # Start the application
   ./run_adhdtv.sh                            # Alternative startup script

🔧 Installation:
   ./install_adhdtv.sh                        # Automated installation
   pip install -r requirements.txt          # Manual dependency installation

📺 Example 1: Playing Local Videos
   1. Launch AD-HDTV
   2. Drag and drop video files onto the window, or
   3. File → Open Files... (Ctrl+O)
   4. Select multiple video files
   5. Use "Play All" to start synchronized playback

🌐 Example 2: Web Stream Extraction (KIII Tower Cam)
   1. Launch AD-HDTV
   2. Web → Fetch from Web Page... (Ctrl+F)
   3. Enter: https://www.kiiitv.com/tower-cam
   4. Wait for stream extraction
   5. Select streams from the dialog
   6. Videos are added to the grid automatically

🔗 Example 3: Direct Streaming URLs
   1. Launch AD-HDTV
   2. File → Add URL... (Ctrl+U)
   3. Enter streaming URLs like:
      - HLS streams: http://example.com/stream.m3u8
      - Direct video: http://example.com/video.mp4
      - RTMP streams: rtmp://example.com/stream

✂️ Example 4: Video Clipping
   1. Load videos into the grid
   2. Set start time (e.g., 00:30 for 30 seconds)
   3. Set end time (e.g., 02:00 for 2 minutes)
   4. Click "Apply Clip"
   5. Videos will play only the specified segment and loop

🔧 Grid Layout Examples:
   Grid → 1x1    # Single fullscreen video
   Grid → 2x2    # Four videos in a square
   Grid → 3x3    # Nine videos
   Grid → 4x4    # Sixteen videos (requires powerful hardware)

🎮 Control Features:
   ▶ Play All     # Start all videos simultaneously
   ⏸ Pause All   # Pause all videos
   ⏹ Stop All    # Stop all videos
   🔊 Volume      # Control volume for all videos (0-100%)

🌍 Web Sources That Work Well:
   • Weather cameras and traffic cams
   • News websites with embedded videos  
   • Live streaming sites
   • HTML5 video pages
   • Sites with HLS (.m3u8) streams

🔍 Supported Video Formats:
   Local Files: MP4, AVI, MKV, MOV, FLV, WMV, WebM, M4V, 3GP
   Streams: HLS (.m3u8), RTMP, RTSP, HTTP streams
   Web: HTML5 videos, embedded players, direct links

⚙️ System Requirements:
   • Python 3.8+
   • VLC Media Player installed
   • PyQt6 or PyQt5
   • Internet connection (for web extraction)

🛠️ Troubleshooting:

   Problem: "VLC Error" in player
   Solution: Install VLC media player system-wide
            sudo apt install vlc libvlc-dev  # Linux
            brew install vlc                 # macOS

   Problem: "No streams found" for web pages
   Solution: Some sites block automated requests or use complex JavaScript
            Try different URLs or use direct stream links

   Problem: High CPU usage
   Solution: Reduce grid size (use 2x2 instead of 4x4)
            Lower video resolution/quality
            Close other applications

   Problem: PyQt import errors
   Solution: Install PyQt6: pip install PyQt6
            Or PyQt5: pip install PyQt5

🚀 Advanced Usage:

   Custom Stream Sources:
   • YouTube live streams (paste YouTube URLs)
   • Webcam streams (use device URLs)
   • Security camera feeds
   • Online radio with video

   Performance Optimization:
   • Use 2x2 grid for balanced performance
   • Reduce volume to prevent audio conflicts
   • Monitor CPU/memory usage
   • Use SSD storage for better performance

📝 Developer Notes:

   The application is built with:
   • PyQt6/PyQt5 for the GUI framework
   • VLC (libvlc) for media playback
   • BeautifulSoup + requests for web scraping
   • Threading for non-blocking operations

   To extend functionality:
   • Modify VideoStreamExtractor for new site support
   • Add new video player features in VideoPlayer class
   • Enhance UI in AD-HDTV main class

🎯 Real-World Use Cases:

   1. Security Monitoring: Multiple camera feeds in one view
   2. Sports Analysis: Compare multiple game angles
   3. Weather Monitoring: Multiple weather cam locations
   4. Live Events: Different stream sources simultaneously
   5. Content Creation: Multi-source video comparison

📞 Support:
   If you encounter issues:
   1. Check the troubleshooting section above
   2. Verify all dependencies are installed
   3. Test with simple video files first
   4. Check network connectivity for web extraction

🎉 Enjoy using AD-HDTV for your multi-video needs!
""")

if __name__ == "__main__":
    print_examples()
