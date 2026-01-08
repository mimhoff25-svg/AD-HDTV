# Fullscreen Button Implementation - Summary

## Problem Fixed
1. **Fullscreen button not visible** - Button was being hidden at init but layout wasn't refreshing
2. **1×1 grid was same size as 2×2** - Default grid was 2×2 instead of 1×1

## Changes Made

### webgridplayer.py
- **Default grid changed**: From `(2, 2)` to `(1, 1)` for single video display
- **Button visibility logic**: 
  - Button now initialized as visible (not hidden)
  - Uses `show()` and `hide()` methods instead of `setVisible()` for more reliable display updates
  - Visibility update deferred to next event loop using `QTimer.singleShot()`
- **New helper methods on WebGridPlayer**:
  - `is_single_grid()`: Checks if grid is 1×1
  - `update_fullscreen_button_visibility()`: Shows button only in 1×1 grids

### New Files
- `tests/test_fullscreen_button_visibility.py`: Automated test verifying button appears in 1×1 and disappears in multi-grid layouts
- `test_manual_check.py`: Diagnostic script to verify button state and grid sizing
- `test_visual.py`: Visual test launcher with on-screen instructions

## How It Works Now

**1×1 Grid (Default on startup)**
- Single video fills the screen
- Fullscreen button (⛶) visible in the lower-right corner
- Click to enter fullscreen, press ESC/F11 to exit

**Multi-Grid (2×2, etc.)**
- Multiple videos in a grid
- Fullscreen button hidden (not needed)

**Grid Switching**
- Menu → Grid → "1 Screen" shows the button
- Menu → Grid → "4 Screens (2×2)" hides the button
- Button automatically updates when grid size changes

## Testing

Run the visual test:
```bash
cd ~/projects/webgridplayer
source ../.venv/bin/activate
python test_visual.py
```

Run automated tests:
```bash
WGP_DISABLE_WEBENGINE=1 xvfb-run -a pytest -q tests/test_fullscreen_button_visibility.py
```

## Keyboard Shortcuts
- **⛶ Button Click**: Enter/exit fullscreen
- **F11**: Toggle fullscreen
- **ESC**: Exit fullscreen (hides UI chrome)
