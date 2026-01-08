# Changelog

All notable changes to WebGridPlayer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Unified Channel/URL Display** 📺🎛️
  - URL label replaced with combo box showing current channel or URL
  - Dropdown shows all saved channels for quick selection
  - Displays "Ch N: Name" when channel is loaded (no more long URLs)
  - Click dropdown to instantly switch between saved channels
  - Cleaner UI with channel names instead of URLs

- **Audio Focus Mode Enhanced** 🔇🎯
  - Focus Mode now mutes non-selected players (solo style)
  - When ON: Only highlighted player has sound, others are muted
  - When OFF: All players unmuted
  - Cleaner than volume reduction - truly solo the selected player

- **Right-Click Channel Selection** 📺🖱️
  - Right-click on any player box to access a "Load Channel" submenu
  - Shows all saved channels with their numbers and names
  - Load any channel directly into the clicked player
  - Available when player is empty or already has content loaded
  - Streamlined workflow: right-click → select channel → instant load

- **Channel Inputs in Stream Selection Dialog** 📺✏️
  - Stream selection dialog now includes optional channel number and name fields
  - Enter channel metadata while selecting a stream
  - Channel is automatically saved when adding the stream
  - Player label updates to show "Ch N: Name" immediately
  - Eliminates need to manually assign channels via Manage Channels

- **Dual-URL Saving System** 🔗📌
  - Saves **both** webpage URL and embedded video URL when adding to favorites/channels
  - Video URL: Used for instant playback
  - Webpage URL: Used for automatic re-extraction when video dies
  - Automatically prefers video link on load
  - Falls back to webpage for fresh stream extraction when needed
  - Works with channels, favorites, and playlists
  - Backward compatible with old saved entries (missing source_url)

- **Automatic Stream Recovery** 🔄🤖
  - Players now automatically detect when streams die and recover without manual intervention
  - Perfect for news playlists where links expire frequently
  - Monitors playback state every 5 seconds
  - Detects when a playing stream suddenly stops or errors
  - Automatically re-extracts fresh stream from source webpage
  - Attempts up to 3 automatic recoveries per stream
  - Shows status during recovery: `🔄 Auto-recovering...` → `✅ Recovered`
  - Resets recovery counter when stream successfully plays
  - Displays notifications when recovery succeeds or fails

- **Smart Refresh with Auto-Re-Extraction** 🔄
  - Refresh button now intelligently detects failed streams and auto-recovers
  - First attempt: Simple refresh (reloads same URL)
  - If stream fails to start after 3 seconds: Automatically re-extracts from source webpage
  - Finds fresh embedded stream links when originals expire or die
  - Tracks original source URL for each loaded stream
  - Shows status updates during re-extraction process
  - Auto-loads first working stream from re-extraction
  - Prevents stale stream URLs from requiring manual re-fetch

### Technical
- **Enhanced Data Structures** 💾
  - Channels: `{'url': video_url, 'source_url': webpage_url, 'title': name}`
  - Favorites: `{'url': video_url, 'source_url': webpage_url, 'title': name}`
  - Playlists: Player state includes `source_url` field
  - All loading functions accept and use `source_url` parameter
- **Playback Monitoring System** 🔍
  - QTimer-based monitoring (5-second intervals)
  - VLC state tracking: Playing, Stopped, Error, Ended
  - Consecutive error counting to avoid false positives
  - Automatic recovery attempt limiting (max 3 per stream)
  - Background thread extraction for non-blocking recovery
- **Source URL Tracking** 📍
  - `VideoPlayer.source_url` stores original webpage for smart recovery
  - `load_media()` accepts optional `source_url` parameter
  - Stream selection dialog passes source URL to enable smart refresh
- **Recovery State Management** 🎬
  - Tracks `was_playing`, `consecutive_error_count`, `auto_recovery_count`
  - Resets counters on successful playback or new media load
  - 30-second manual refresh counter reset window

## [1.1.1] - 2026-01-05

## [1.1.2] - 2026-01-05

### Added
- **Active Player Targeting** 🎯
  - Clicking a player now selects it and highlights with a blue border
  - URLs/files load into the selected player first, then empty slots
  - Auto-selects the first player after grid changes for predictability
- **6-Screen Preset Update** 🖥️
  - Grid menu preset now uses 2×3 (three across) for 16:9 efficiency

### Fixed
- **Grid Switching Blank Screen** 🧱
  - Reuse a single grid layout instead of reassigning to the container
  - Cleans up old widgets safely, preventing layout reassignment crashes/blanking
- **Layout Warnings & Crashes** 🛠️
  - Removed repeated `setLayout` calls that produced Qt warnings and blank grids
- **Selection State Reset** 🔄
  - Resets and reapplies selection when rebuilding grids to avoid stale targets

### Technical
- **Player Lifecycle** ♻️
  - Light cleanup retained; selection-aware loading for files/URLs
  - Safe recovery path maintained for minimal 1×1 grid on critical errors


### Fixed
- **Critical VLC Initialization Issue** 🔧
  - Removed invalid `--hls-fakeua` VLC option causing instance creation failure
  - VLC media players now initialize properly in all environments
  - Fixed "No Player" error preventing video loading

- **Video Loading in Grid Slots** 📺
  - Videos now correctly load into assigned grid slots after stream selection
  - Enhanced stream assignment with comprehensive debugging output
  - Improved player state management and availability detection
  - Added automatic VLC mode switching when loading video streams

- **Syntax Errors Resolution** 🐛
  - Fixed escaped quote syntax errors in docstrings and print statements
  - Resolved broken print statement line continuations
  - Corrected f-string formatting issues throughout codebase

### Enhanced
- **Status Feedback and Debugging** 📊
  - Added detailed logging for stream extraction and assignment process
  - Enhanced player status indicators with emojis (⏳ Loading, ▶️ Playing, ❌ Error)
  - Improved error messages and user feedback throughout application
  - Better tracking of which streams load into which players

- **Stream Loading Reliability** 🌐
  - Increased auto-play delay for better media initialization (200ms → 500ms)
  - Enhanced HLS stream handling with proper VLC media options
  - Improved URL truncation in UI for better readability
  - Better handling of headless/display-less environments

### Added
- **Comprehensive Test Suite** 🧪
  - Added headless functionality test verifying all core components
  - Created stream loading test for VLC integration validation
  - Added full workflow test simulating extraction → selection → loading
  - Browser mode functionality test for QtWebEngine validation
  - Fox7 Austin specific stream extraction and accessibility testing

### Technical
- **Dependencies Management** 📦
  - Ensured proper installation of python-vlc, requests, beautifulsoup4
  - Added PyQt6-WebEngine for browser mode functionality
  - Improved dependency error handling and user guidance

- **Cross-Platform Compatibility** 💻
  - Better VLC options for different operating systems
  - Enhanced headless mode support for server environments
  - Improved Qt platform plugin handling

**Result**: Videos now successfully load from preview dialog into assigned grid slots with proper playback functionality.

## [1.1.0] - 2026-01-05

### Added
- **Browser Mode Functionality** 🌐
- Embedded web browser in each player slot using QtWebEngine
- Smart fallback system when video stream extraction fails
- Fullscreen support for browser-embedded videos
- Individual player mode toggle buttons (VLC ↔ Browser)
- "Browse Web Page" option in context menu
- Enhanced stream extraction with token refresh system
- Automatic authentication token renewal for time-sensitive streams
- Source page tracking for stream refresh capability

### Enhanced
- **Stream Extraction Engine**:
  - Better iframe detection and filtering
  - Improved HLS stream pattern matching
  - Enhanced VLC options for streaming (network caching, reconnection)
  - Time-limited authentication token handling
  - wetmet.net iframe stream extraction (Fox7 Austin compatible)

- **User Interface**:
  - Mode toggle button (🎬/📺) for VLC/Browser switching
  - Fullscreen button (⛶) for browser mode
  - Updated status indicators (🌐 for browser, 📺 for VLC)
  - Enhanced context menu with browser options
  - Smart fallback dialogs when streams not found

- **Player Controls**:
  - Stacked widget architecture for dual-mode support
  - Browser fullscreen functionality
  - URL processing with automatic protocol detection
  - Grid slot browser mode assignment

### Fixed
- Stream extraction failure handling
- Time-sensitive stream token expiry issues
- VLC HLS streaming reliability
- QtWebEngine integration compatibility

### Technical
- Added QtWebEngine dependency management
- Enhanced error handling for missing WebEngine
- Backward compatibility with VLC-only mode
- Cross-platform browser mode support
- Memory management for dual-mode players

## [1.0.0] - 2026-01-05

### Added
- **Initial Release** 🎉
- Multi-video grid system (1×1 to 4×4 layouts)
- VLC-based media player integration for universal format support
- Intelligent web stream extraction from HTML pages
- Support for HTML5 videos, HLS streams (.m3u8), and direct video URLs
- YouTube embed detection and extraction
- Synchronized playback controls (play/pause/stop all)
- Unified volume control across all players
- Video clipping functionality with start/end time controls
- Drag-and-drop support for local video files
- URL input dialog for streaming sources
- Non-blocking web extraction using threading
- Stream selection dialog for multiple found streams
- Cross-platform compatibility (Windows, macOS, Linux)
- Comprehensive error handling and graceful fallbacks
- Professional PyQt6/PyQt5 GUI interface
- Automated installation scripts
- Extensive documentation and examples

### Features
- **Web Stream Extraction**:
  - HTML5 `<video>` tag parsing
  - HLS manifest (.m3u8) detection
  - Direct video file URL extraction (MP4, WebM, OGG, etc.)
  - YouTube embed video ID extraction
  - Blob URL identification
  - Regular expression-based URL discovery

- **Video Player Grid**:
  - Dynamic grid resizing
  - Individual VLC player instances per grid cell
  - Synchronized control operations
  - Grid layouts: 1×1, 1×2, 2×1, 2×2, 2×3, 3×2, 3×3, 4×4
  - Player status indicators

- **Advanced Controls**:
  - Master play/pause/stop controls
  - Volume slider with percentage display
  - Video clipping with MM:SS time format
  - Grid layout switching menu
  - Keyboard shortcuts (Ctrl+O, Ctrl+U, Ctrl+F, Ctrl+Q)

- **User Interface**:
  - Modern Qt-based interface
  - Menu bar with organized functions
  - Status bar with operation feedback
  - Progress dialogs for long operations
  - Error message dialogs
  - Stream selection dialog with preview

### Technical Implementation
- **Architecture**: Modular design with separate classes for extraction, player, and UI
- **Threading**: ThreadPoolExecutor for non-blocking web operations
- **Error Handling**: Comprehensive exception handling throughout
- **Platform Support**: Native VLC integration for Windows, macOS, and Linux
- **Dependencies**: Minimal external dependencies with automatic installation
- **Performance**: Optimized for multiple simultaneous video streams

### Documentation
- Complete README with installation instructions
- Usage examples and troubleshooting guide
- Performance benchmarks and recommendations
- Developer documentation for contributing
- Automated testing scripts

### Testing
- Stream extraction testing with real-world URLs
- VLC integration verification
- Cross-platform compatibility testing
- Error condition handling verification
- Performance testing with multiple video streams

## [Unreleased]

### Planned Features
- Fullscreen mode for individual players
- Audio synchronization controls
- Video aspect ratio adjustment
- Playlist management and saving
- Stream quality selection
- Recording capabilities
- Plugin system for custom extractors
- Configuration file support
- Multi-language support
- Dark/light theme selection

---

For more information about changes and development, see the [project repository](https://github.com/yourusername/webgridplayer).