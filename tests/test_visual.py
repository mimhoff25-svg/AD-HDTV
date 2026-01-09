#!/usr/bin/env python3
"""Manual visual test - run this to see the fullscreen button and test grid sizes."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'src')
for p in (ROOT, SRC):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ['WGP_DISABLE_WEBENGINE'] = '1'

try:
    from PyQt6.QtWidgets import QApplication
except Exception:
    try:
        from PyQt5.QtWidgets import QApplication
    except Exception as e:
        print(f"Error: PyQt not available: {e}")
        sys.exit(1)

from webgridplayer import WebGridPlayer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WebGridPlayer()
    window.setWindowTitle("WebGridPlayer - Fullscreen Test (1×1 Default)")
    window.show()
    
    print("=" * 60)
    print("FULLSCREEN BUTTON TEST")
    print("=" * 60)
    print(f"\n✓ App started with 1×1 grid (single video)")
    print(f"✓ Look for the ⛶ (fullscreen) button in the lower-right of the video box")
    print(f"\nControls:")
    print(f"  • Click ⛶ button to enter fullscreen")
    print(f"  • Press ESC or F11 to exit fullscreen")
    print(f"  • Use Grid menu to change to 2×2 (button should disappear)")
    print(f"  • Change back to 1 Screen (button should reappear)")
    print("\n" + "=" * 60)
    
    sys.exit(app.exec())
