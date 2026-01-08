import os
import sys
import pytest

# Ensure the package path includes project root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Import Qt auto-selection from app
from webgridplayer import WebGridPlayer

try:
    # The module itself creates QApplication in main(), but we create our own for tests
    from PyQt6.QtWidgets import QApplication
except Exception:
    try:
        from PyQt5.QtWidgets import QApplication
    except Exception as e:
        QApplication = None

pytestmark = pytest.mark.skipif(
    os.environ.get('DISPLAY') in (None, ''),
    reason='Qt tests require X display; run with X or xvfb.'
)

@pytest.fixture(scope='module')
def app():
    app = QApplication.instance() or QApplication([])
    yield app


def get_fullscreen_buttons(window):
    return [p.fullscreen_button for p in window.players if hasattr(p, 'fullscreen_button')]


def test_fullscreen_button_visible_only_in_1x1(app):
    window = WebGridPlayer()

    # 1x1 grid
    window.change_grid_size(1, 1)
    buttons = get_fullscreen_buttons(window)
    assert buttons, 'No players/buttons found in 1x1 grid'
    assert all(not b.isHidden() for b in buttons), 'Fullscreen button should be visible in 1x1 grid'

    # 2x2 grid
    window.change_grid_size(2, 2)
    buttons = get_fullscreen_buttons(window)
    assert buttons, 'No players/buttons found in 2x2 grid'
    assert all(b.isHidden() for b in buttons), 'Fullscreen button should be hidden in multi-tile grid'

    # return to 1x1
    window.change_grid_size(1, 1)
    buttons = get_fullscreen_buttons(window)
    assert all(not b.isHidden() for b in buttons), 'Fullscreen button should reappear in 1x1 grid'
