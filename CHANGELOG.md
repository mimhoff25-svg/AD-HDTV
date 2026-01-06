# Changelog

All notable changes to WebGridPlayer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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