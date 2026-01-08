#!/usr/bin/env python3
"""Test to verify startup grid size."""
import os
import sys

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
    app = QApplication([])
    window = WebGridPlayer()
    
    print(f"Grid size: {window.grid_size}")
    print(f"Number of players: {len(window.players)}")
    print(f"Expected: (1, 1) with 1 player")
    print(f"Match: {window.grid_size == (1, 1) and len(window.players) == 1}")
