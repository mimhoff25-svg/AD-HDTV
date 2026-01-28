
import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from adhdtv.guide_generator import generate_fake_guide
from datetime import datetime

class TestGuideGenerator(unittest.TestCase):
    def test_guide_structure(self):
        guide = generate_fake_guide(hours=2)
        self.assertEqual(guide.minutes_per_slot, 30)
        self.assertEqual(guide.slot_count, 4)
        for prog in guide.programs:
            dt = datetime.fromisoformat(prog.start_time_iso)
            self.assertIn(dt.minute, (0, 30))

if __name__ == '__main__':
    unittest.main()
