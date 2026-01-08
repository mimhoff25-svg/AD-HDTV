#!/usr/bin/env python3
"""Quick test to verify fullscreen button visibility and grid sizing."""
import os
import sys

# Disable WebEngine for headless testing
os.environ['WGP_DISABLE_WEBENGINE'] = '1'

from webgridplayer import WebGridPlayer

try:
    from PyQt6.QtWidgets import QApplication
except Exception:
    try:
        from PyQt5.QtWidgets import QApplication
    except Exception as e:
        print(f"Error: PyQt not available: {e}")
        sys.exit(1)

if __name__ == "__main__":
    app = QApplication([])
    window = WebGridPlayer()
    window.show()  # Show the window so widgets are properly rendered
    
    print("\n=== Initial State (should be 1×1) ===")
    print(f"Grid size: {window.grid_size}")
    print(f"Is single grid: {window.is_single_grid()}")
    print(f"Number of players: {len(window.players)}")
    if window.players:
        btn = window.players[0].fullscreen_button
        print(f"Fullscreen button exists: {btn is not None}")
        print(f"Fullscreen button visible: {btn.isVisible()}")
        print(f"Fullscreen button hidden: {btn.isHidden()}")
        print(f"Button parent: {btn.parent()}")
        print(f"Button parent visible: {btn.parent().isVisible() if btn.parent() else 'N/A'}")
    
    print("\n=== After changing to 2×2 ===")
    window.change_grid_size(2, 2)
    print(f"Grid size: {window.grid_size}")
    print(f"Is single grid: {window.is_single_grid()}")
    print(f"Number of players: {len(window.players)}")
    visible_count = sum(1 for p in window.players if not p.fullscreen_button.isHidden())
    print(f"Visible fullscreen buttons: {visible_count}/4 (expected 0)")
    
    print("\n=== After changing back to 1×1 ===")
    window.change_grid_size(1, 1)
    print(f"Grid size: {window.grid_size}")
    print(f"Is single grid: {window.is_single_grid()}")
    print(f"Number of players: {len(window.players)}")
    if window.players:
        btn = window.players[0].fullscreen_button
        print(f"Fullscreen button visible: {btn.isVisible()}")
        print(f"Fullscreen button hidden: {btn.isHidden()}")
    
    print("\n=== Grid Layout State ===")
    print(f"Window geometry: {window.geometry()}")
    print(f"Grid container size: {window.grid_container.size()}")
    for i, p in enumerate(window.players):
        print(f"  Player {i} size: {p.size()}")
