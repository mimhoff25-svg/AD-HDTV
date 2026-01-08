# WebGridPlayer - Known Errors & Solutions

This document tracks known issues, their causes, and proven solutions to prevent recurring problems.

## 📋 **Error Categories**

### 🎥 **VLC/Player Initialization Errors**

#### **Error: "Player error" on all windows**
- **Symptoms**: All video boxes show "Player error #X" instead of working players
- **Cause**: VLC initialization failure due to complex/invalid arguments
- **Solution**: 
  - Use basic VLC arguments: `--quiet`, `--no-video-title-show`, `--network-caching=1000`
  - Avoid: `--intf=dummy`, `--no-embedded-video`, complex audio arguments
  - Ensure proper widget ID assignment before VLC attachment
- **Code Fix**: Use minimal VLC instance creation
- **Status**: ✅ Fixed (Jan 6, 2026)

#### **Error: Random VLC window appearing in top-left corner**
- **Symptoms**: Extra VLC player window opens separately from the application
- **Cause**: VLC creating separate interface window due to improper arguments
- **Solution**: 
  - Remove `--intf=dummy` and `--no-embedded-video` arguments
  - Ensure proper widget embedding with `set_xwindow`/`set_hwnd`/`set_nsobject`
- **Status**: ✅ Fixed (Jan 6, 2026)

#### **Error: Application crashes on startup**
- **Symptoms**: Python application exits with errors during initialization
- **Cause**: Complex widget initialization timing, premature VLC setup
- **Solution**:
  - Remove `self.show()` calls from VideoPlayer constructor
  - Eliminate `QTimer.singleShot` delays in widget initialization
  - Initialize VLC immediately after widget creation, not delayed
- **Status**: ✅ Fixed (Jan 6, 2026)

### 🔊 **Audio Issues**

#### **Error: Audio glitches and crackling**
- **Symptoms**: Choppy, distorted, or crackling audio from video players
- **Cause**: Inadequate audio buffering, conflicting audio time-stretch settings
- **Solution**:
  - Increase VLC caching: `--network-caching=3000`, `--live-caching=3000`
  - Remove conflicting arguments: `--audio-time-stretch` + `--no-audio-time-stretch`
  - Use platform-appropriate audio output: `pulse,alsa` (Linux), `directsound` (Windows)
- **Prevention**: Test audio settings on target platform
- **Status**: ✅ Fixed (Jan 6, 2026)

#### **Error: Volume control causing audio pops/clicks**
- **Symptoms**: Audio artifacts when changing volume or muting
- **Cause**: Abrupt volume changes, complex fade algorithms with timing issues
- **Solution**:
  - Use direct VLC volume control: `audio_set_volume(volume)`
  - Remove `time.sleep()` loops in volume transitions
  - Use simple boolean mute: `audio_set_mute(True/False)`
- **Code Fix**: Simplified volume/mute methods without fade effects
- **Status**: ✅ Fixed (Jan 6, 2026)

### 🖥️ **UI/Widget Issues**

#### **Error: CSS warnings "Unknown property box-shadow"**
- **Symptoms**: Console spam with CSS property warnings
- **Cause**: Qt StyleSheet doesn't support CSS box-shadow property
- **Solution**: Use Qt-native border styling instead of box-shadow
- **Impact**: Cosmetic only - doesn't affect functionality
- **Status**: ⚠️ Known (Non-critical)

#### **Error: VideoPlayer selection not working**
- **Symptoms**: Clicking video boxes doesn't highlight/select them
- **Cause**: Incorrect parent widget traversal in mousePressEvent
- **Solution**: Proper parent chain walking to find WebGridPlayer instance
- **Code Fix**: Enhanced `mousePressEvent` with parent type checking
- **Status**: ✅ Fixed (Jan 6, 2026)

### 🌐 **Network/Streaming Issues**

#### **Error: Stream extraction fails silently**
- **Symptoms**: No streams found from valid video websites
- **Cause**: Missing User-Agent headers, insufficient timeout values
- **Solution**:
  - Use realistic browser User-Agent string
  - Increase request timeout to 10+ seconds
  - Add proper error handling for network failures
- **Prevention**: Test with various streaming sites regularly

#### **Error: HLS streams won't play**
- **Symptoms**: .m3u8 URLs load but no video appears
- **Cause**: Insufficient buffering for live streams
- **Solution**:
  - Increase live-caching: `--live-caching=3000`
  - Add HTTP reconnection: `--http-reconnect`
  - Use adaptive streaming: `--adaptive-logic=highest`

### 📁 **File System Issues**

#### **Error: State files not saving**
- **Symptoms**: Favorites, playlists, or channels don't persist between sessions
- **Cause**: Missing directory permissions or path issues
- **Solution**:
  - Ensure `state/` directory exists with write permissions
  - Use `Path.mkdir(parents=True, exist_ok=True)` for directory creation
  - Add try-catch around all JSON file operations
- **Prevention**: Validate file paths on startup

## 🔧 **Error Prevention Best Practices**

### **VLC Integration**
1. **Always use minimal VLC arguments** - Only add what's absolutely necessary
2. **Test on target platform** - VLC behavior varies between OS
3. **Proper error handling** - Check if VLC instance/player creation succeeded
4. **Widget timing** - Ensure widgets are fully initialized before VLC attachment

### **Audio Management**
1. **Simple volume control** - Avoid complex fade/transition algorithms
2. **Platform-specific audio** - Use appropriate audio output for each OS
3. **Adequate buffering** - Higher caching for network streams
4. **Test multiple streams** - Different audio codecs may behave differently

### **UI Development**
1. **Qt-native styling** - Use supported CSS properties only
2. **Proper event handling** - Ensure parent-child relationships are correct
3. **Thread safety** - Keep UI updates on main thread
4. **Resource cleanup** - Properly destroy VLC objects on exit

### **Network Operations**
1. **Robust error handling** - Handle timeouts, connection failures
2. **User-Agent spoofing** - Some sites block default Python requests
3. **Rate limiting** - Avoid overwhelming target servers
4. **Input validation** - Sanitize URLs and user input

## 📊 **Error Tracking System**

The application now logs errors to:
- `logs/webgridplayer_YYYYMMDD.log` - All application events
- `logs/errors_YYYYMMDD.log` - Error events only
- `logs/user_actions_YYYYMMDD.log` - User interactions

### **Adding New Known Errors**

When encountering a new error:

1. **Document the symptoms** clearly
2. **Identify the root cause** through debugging
3. **Test the solution** thoroughly
4. **Update this file** with the fix
5. **Add error detection** to prevent recurrence

### **Error Severity Levels**

- 🔴 **Critical**: Application won't start/function
- 🟡 **Major**: Feature doesn't work as expected
- 🟠 **Minor**: Degraded user experience
- ⚠️ **Cosmetic**: Visual issues, no functional impact

## 🔄 **Version History**

- **v1.0 (Jan 6, 2026)**: Initial error tracking system
  - Fixed VLC initialization crashes
  - Resolved audio glitching issues
  - Added comprehensive logging
  - Implemented modern UI theme
  - Added solo audio functionality
  - Created channel saving feature

---

**Note**: This document should be updated whenever new errors are discovered and resolved. Regular review helps maintain application stability.