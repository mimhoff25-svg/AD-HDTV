
---
# AD-HDTV 🎥

**AD-HDTV** is a server-hosted broadcast and TV guide system. The backend (ServerX) runs on Python and VLC, with planned clients for Roku and Android remote control. A TV guide grid renderer is a core feature.

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![VLC Powered](https://img.shields.io/badge/powered%20by-VLC-orange.svg)](https://www.videolan.org/vlc/)
[![Cross Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](PLATFORM_COMPATIBILITY.md)

---

## What is AD-HDTV?

- Multiple video grid playback (1x1 to 4x4)
- Intelligent web stream extraction
- Synchronized controls and advanced video features
- Extensible API for remote control (Roku, Android, web)

**Architecture:**
- **Backend:** Python (ServerX) with VLC/libvlc, PyQt, and web extraction
- **Clients:**
  - Roku (planned)
  - Android remote app (planned)
  - Web/desktop (current)

---

## Current Status

- Core backend (Python, VLC) is runnable: grid video playback, stream extraction, basic controls
- Legacy scripts and desktop integration available (see legacy/)
- Remote API (planned/in progress)
- TV guide grid renderer (planned)
- Roku and Android clients (planned)

---

## Repo Layout

- `src/` — Main backend code (grid engine, extraction, etc.)
- `config/` — Configuration and profiles
- `docs/` — Documentation, API contract
- `scripts/` — Install and dev scripts
- `tests/` — Unit/integration tests
- `clients/` — Thin frontends (android, roku)
- `legacy/` — Old scripts and files (not used in AD-HDTV)

---

## How to Run the Backend

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Launch the backend (single entrypoint):
   ```bash
   python run_server.py
   ```


> **Note:** All legacy scripts are now in `legacy/` and not referenced by AD-HDTV. Use only `install_adhdtv.sh` and `run_adhdtv.sh` for setup and running.

---


## Remote API Endpoints

- `POST /play` — Start playback (**Implemented**)
- `POST /pause` — Pause playback (**Implemented**)
- `POST /channel_up` — Increase channel number (**Implemented**)
- `POST /channel_down` — Decrease channel number (**Implemented**)
- `GET /status` — Get current player status (**Implemented**)

See `docs/API.md` for the evolving contract.

---

## Roadmap

- [ ] Guide renderer (EPG)
- [ ] Roku client
- [ ] Android remote app
- [ ] REST API for remote control
- [ ] Improved web extraction
- [ ] Multi-user support

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch strategy, commit style, and rules.

---

## License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE).

---

## Support & Community

- Documentation: [docs/](docs/)
- Issues: [GitHub Issues](https://github.com/yourusername/adhdtv/issues)
- Feature requests: [Discussions](https://github.com/yourusername/adhdtv/discussions)

---


**AD-HDTV: The open video grid engine for everyone.**

## ✨ Key Features

### 🎬 Multi-Video Grid System
- **Dynamic Grid Layouts**: 1×1 up to 4×4 (16 simultaneous videos)
- **VLC Integration**: Universal support for all video formats
- **Synchronized Controls**: Play/pause/stop all videos simultaneously
- **Unified Volume Control**: Single slider for all players
- **Drag & Drop Support**: Easy local file loading

### 🌐 Intelligent Web Stream Extraction
- **Auto-Detection**: Finds video streams from any web page
- **Multiple Formats**: HTML5, HLS (.m3u8), MP4, WebM, YouTube embeds
- **Smart Parsing**: BeautifulSoup + regex for robust extraction  
- **Non-Blocking**: Threaded operations keep UI responsive
- **Stream Selection**: Choose from multiple found streams

### 🎮 Advanced Video Controls
- **Video Clipping**: Set precise start/end times with looping
- **Grid Resizing**: Switch layouts on-the-fly
- **Cross-Platform**: Windows, macOS, Linux support
- **Professional UI**: Modern PyQt6/PyQt5 interface

## 🚀 Quick Start

### One-Line Installation
```bash
curl -sSL https://raw.githubusercontent.com/yourusername/adhdtv/main/install_adhdtv.sh | bash
```

### Manual Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/adhdtv.git
cd adhdtv

# Run the installation script
./install_adhdtv.sh

# Launch AD-HDTV
./run_adhdtv.sh
```

### Desktop Integration
After installation, you can add AD-HDTV to your system's application menu:

```bash
# Install desktop integration (application menu entry and icon)
./install_desktop.sh
```

This will:
- Add AD-HDTV to your application menu (Audio & Video category)
- Create a desktop shortcut (optional)
- Associate AD-HDTV with video file types
- Install the application icon

### Profiles
Use `python app.py --profile dev|demo|live` or set `ADHDTV_PROFILE` to load config overrides from `config/profiles/`.

## 📋 System Requirements

### Required Software
- **Python 3.8+** ([Download](https://python.org))
- **VLC Media Player** ([Download](https://www.videolan.org/vlc/))

### Automatic Dependencies
The installer handles these automatically:
- PyQt6 or PyQt5 (GUI framework)
- python-vlc (VLC bindings)
- requests + BeautifulSoup4 (web extraction)

### Platform-Specific Notes

**📋 For detailed platform setup and compatibility information, see [PLATFORM_COMPATIBILITY.md](PLATFORM_COMPATIBILITY.md)**

#### 🐧 Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install vlc libvlc-dev python3-pip
```

#### 🍎 macOS
```bash
brew install vlc python3
# Or download VLC from videolan.org
```

#### 🪟 Windows
1. Download and install VLC from [videolan.org](https://www.videolan.org/vlc/)
2. Download and install Python 3.8+ from [python.org](https://python.org)
3. Install dependencies: `pip install PyQt6 python-vlc requests beautifulsoup4`
4. Run: `python app.py`

## 🎯 Usage Examples

### Example 1: Web Stream Extraction
```bash
# Launch AD-HDTV
python app.py

# In the app:
# 1. Web → Fetch from Web Page...
# 2. Enter: https://www.kiiitv.com/tower-cam
# 3. Select extracted streams
# 4. Click "Play All"
```

### Example 2: Local Video Files
```bash
# Drag & drop video files onto the window, or:
# File → Open Files... (Ctrl+O)
# Select multiple video files
# Use synchronized playback controls
```

### Example 3: Video Clipping
```bash
# Load videos into grid
# Set start time: 00:30
# Set end time: 02:00  
# Click "Apply Clip"
# Videos now play only that segment and loop
```

## 🌍 Supported Video Sources

### Local Formats
- **Standard**: MP4, AVI, MKV, MOV, FLV, WMV, WebM
- **Advanced**: M4V, 3GP, OGG, and all VLC-supported formats

### Streaming Protocols
- **HLS**: .m3u8 streams (live and VOD)
- **RTMP/RTSP**: Network streaming protocols
- **HTTP**: Direct video file URLs
- **WebRTC**: Modern streaming standards

### Web Sources
- **HTML5 Videos**: `<video>` tags with `<source>` elements
- **YouTube**: Embedded video extraction
- **Weather Cams**: Traffic and weather monitoring streams
- **News Sites**: Embedded video content
- **Live Streams**: Various streaming platforms

## 🔧 Advanced Configuration

### Grid Layout Options
| Layout | Videos | Best For |
|--------|--------|----------|
| 1×1 | 1 | Single fullscreen playback |
| 2×1 | 2 | Side-by-side comparison |
| 2×2 | 4 | Balanced multi-view |
| 3×3 | 9 | Comprehensive monitoring |
| 4×4 | 16 | Maximum coverage (requires powerful hardware) |

### Performance Optimization
- **Recommended**: 2×2 grid for balanced performance
- **CPU Usage**: Monitor with `htop` or Task Manager
- **Memory**: 8GB+ recommended for 4×4 grids
- **Storage**: SSD recommended for local files

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open local files |
| `Ctrl+U` | Add streaming URL |
| `Ctrl+F` | Fetch from web page |
| `Ctrl+Q` | Quit application |
| `Space` | Play/Pause toggle |

## 🛠️ Troubleshooting

### Common Issues

#### "VLC Error" in players
```bash
# Linux
sudo apt install vlc libvlc-dev

# macOS  
brew install vlc

# Windows
# Download VLC from videolan.org
```

#### "No streams found" from web pages
- Some sites block automated requests
- Try direct stream URLs instead
- Check site's robots.txt policy
- Use browser developer tools to find direct links

#### PyQt import errors
```bash
# Try PyQt6 first
pip install PyQt6

# Fallback to PyQt5
pip install PyQt5
```

#### High CPU usage
- Reduce grid size (2×2 instead of 4×4)
- Lower video resolution/quality
- Close other resource-intensive apps
- Use hardware acceleration if available

### Debug Mode
```bash
# Run with verbose output (dev profile)
python app.py --profile dev

# Test stream extraction only
python test_stream_extraction.py
```

## 🏗️ Development

### Architecture and Flow
See `docs/ARCHITECTURE.md` for the lifecycle, state flow, and channel layout.

### Architecture Overview
```
AD-HDTV/
├── GUI Layer (PyQt6/5)
├── Media Engine (VLC/libvlc) 
├── Web Extraction (BeautifulSoup + requests)
├── Threading (ThreadPoolExecutor)
└── Video Processing (Individual VLC instances)
```

### Contributing
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes with tests
4. Submit a pull request

### Building from Source
```bash
git clone https://github.com/yourusername/adhdtv.git
cd adhdtv
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
pip install -r requirements.txt
python app.py
```

## 🎪 Use Cases

### Professional Applications
- **Security Monitoring**: Multiple camera feeds
- **Sports Analysis**: Multi-angle game footage  
- **Weather Monitoring**: Regional weather station feeds
- **Live Event Coverage**: Multiple stream sources
- **Content Creation**: Video comparison and analysis

### Personal Use
- **Home Security**: Multiple IP camera streams
- **Entertainment**: Watch multiple streams simultaneously
- **Education**: Compare different video sources
- **Research**: Analyze multiple video datasets

## 📊 Performance Benchmarks

### Tested Configurations
| Grid Size | CPU Usage* | RAM Usage* | Recommended Hardware |
|-----------|------------|------------|---------------------|
| 1×1 | 5-15% | 200MB | Any modern system |
| 2×2 | 15-30% | 800MB | Dual-core, 4GB RAM |
| 3×3 | 30-50% | 1.5GB | Quad-core, 8GB RAM |
| 4×4 | 50-80% | 3GB+ | 8+ cores, 16GB RAM |

*Approximate values with 1080p video content

## 🔐 Security & Privacy

### Data Handling
- **No Data Collection**: AD-HDTV doesn't collect or transmit user data
- **Local Processing**: All video processing happens locally
- **Network Requests**: Only made when explicitly fetching web streams
- **Privacy First**: No analytics, tracking, or telemetry

### Web Scraping Ethics
- **Respectful**: Follows robots.txt guidelines
- **Rate Limited**: Reasonable request delays
- **User Agent**: Identifies as AD-HDTV
- **Legal Compliance**: Users responsible for content access rights

## 📄 License

This project is licensed under the **GNU General Public License v3.0** - see the [LICENSE](LICENSE) file for details.

### Key Points:
- ✅ **Free to use** for personal and commercial purposes
- ✅ **Modify and distribute** with same license
- ✅ **Source code** must remain available
- ❌ **No warranty** provided

## 🙏 Acknowledgments

- **[VLC Media Player](https://www.videolan.org/vlc/)** - Powerful media framework
- **[Qt Project](https://www.qt.io/)** - Cross-platform GUI toolkit
- **[Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/)** - HTML parsing library
- **[GridPlayer](https://github.com/vzhd1701/gridplayer)** - Original inspiration
- **Community Contributors** - Bug reports and feature suggestions

## 📞 Support

### Getting Help
- **📖 Documentation**: Check the [examples.py](examples.py) file
- **🐛 Bug Reports**: [Open an issue](https://github.com/yourusername/adhdtv/issues)
- **💡 Feature Requests**: [Discussion forum](https://github.com/yourusername/adhdtv/discussions)
- **❓ Questions**: Stack Overflow with `adhdtv` tag

### Sponsor This Project
If AD-HDTV saves you time or enhances your workflow:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow.svg)](https://buymeacoffee.com/adhdtv)
[![GitHub Sponsors](https://img.shields.io/badge/GitHub-sponsor-red.svg)](https://github.com/sponsors/yourusername)

---

<div align="center">

**[⬆ Back to Top](#ad-hdtv-)**

Made with ❤️ for the video streaming community

[![Star this repo](https://img.shields.io/github/stars/yourusername/adhdtv?style=social)](https://github.com/yourusername/adhdtv/stargazers)
[![Follow @yourusername](https://img.shields.io/twitter/follow/yourusername?style=social)](https://twitter.com/yourusername)

</div>
