
import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from adhdtv.state import State
from adhdtv.state_manager import StateManager
from datetime import datetime

class TestStateManager(unittest.TestCase):
    def test_revision_increments(self):
        s = State(version="1.0", started_at=datetime.utcnow(), current_channel_id=1, current_channel_name="Test")
        mgr = StateManager(s)
        rev0 = mgr.revision
        mgr.update(lambda st: setattr(st, 'current_channel_id', 2))
        rev1 = mgr.revision
        self.assertEqual(rev1, rev0 + 1)
        mgr.touch()
        self.assertEqual(mgr.revision, rev1 + 1)

if __name__ == '__main__':
    unittest.main()
