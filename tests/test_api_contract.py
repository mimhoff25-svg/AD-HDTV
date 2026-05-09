import os
import sys
import unittest
from datetime import UTC, datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from adhdtv.api import API_PREFIX, build_state_manager, create_app
from adhdtv.state import State
from adhdtv.state_manager import StateManager


class TestApiContract(unittest.TestCase):
    def setUp(self):
        self.state_manager = build_state_manager(version="test", current_channel_id=7)
        self.app = create_app(
            state_mgr=self.state_manager,
            config={"hub": {"auth_token": "secret", "allow_origins": ["http://roku.local"]}},
        )
        self.client = self.app.test_client()
        self.headers = {
            "Authorization": "Bearer secret",
            "Origin": "http://roku.local",
        }

    def test_status_requires_auth(self):
        response = self.client.get(f"{API_PREFIX}/status")
        self.assertEqual(response.status_code, 401)

    def test_status_returns_snapshot_and_cors(self):
        response = self.client.get(f"{API_PREFIX}/status", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["version"], "test")
        self.assertEqual(payload["current_channel_id"], 7)
        self.assertTrue(payload["playing"])
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "http://roku.local")

    def test_channel_and_selection_controls_accept_json(self):
        channel_response = self.client.post(
            f"{API_PREFIX}/control/channel/set",
            json={"id": 42},
            headers=self.headers,
        )
        self.assertEqual(channel_response.status_code, 200)
        self.assertEqual(channel_response.get_json()["current_channel_id"], 42)

        select_response = self.client.post(
            f"{API_PREFIX}/control/select",
            json={"row": 1, "col": 2, "channel_id": "42", "start_time_iso": "2026-01-27T18:00:00"},
            headers=self.headers,
        )
        self.assertEqual(select_response.status_code, 200)
        selected = select_response.get_json()["selected"]
        self.assertEqual(selected["row"], 1)
        self.assertEqual(selected["col"], 2)
        self.assertEqual(selected["channel_id"], "42")
        self.assertEqual(selected["start_time_iso"], "2026-01-27T18:00:00")

    def test_guide_and_audio_controls_work(self):
        guide_show = self.client.post(f"{API_PREFIX}/control/guide/show", headers=self.headers)
        self.assertEqual(guide_show.status_code, 200)
        self.assertTrue(guide_show.get_json()["guide_visible"])

        solo = self.client.post(
            f"{API_PREFIX}/control/audio/solo",
            json={"id": "tile-2"},
            headers=self.headers,
        )
        self.assertEqual(solo.status_code, 200)
        self.assertEqual(solo.get_json()["audio"]["solo_source_id"], "tile-2")

        mute = self.client.post(
            f"{API_PREFIX}/control/audio/mute",
            json={"value": True},
            headers=self.headers,
        )
        self.assertEqual(mute.status_code, 200)
        self.assertTrue(mute.get_json()["audio"]["muted"])

    def test_guide_and_discovery_endpoints_exist(self):
        discovery = self.client.get(f"{API_PREFIX}", headers=self.headers)
        self.assertEqual(discovery.status_code, 200)
        self.assertEqual(discovery.get_json()["status"], f"{API_PREFIX}/status")

        guide = self.client.get(f"{API_PREFIX}/guide?hours=2", headers=self.headers)
        self.assertEqual(guide.status_code, 200)
        payload = guide.get_json()
        self.assertIn("channels", payload)
        self.assertIn("programs", payload)

    def test_ip_allowlist_blocks_disallowed_clients(self):
        app = create_app(
            state_mgr=build_state_manager(),
            config={"hub": {"allowed_ips": ["127.0.0.2"]}},
        )
        client = app.test_client()
        response = client.get(f"{API_PREFIX}/status", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
        self.assertEqual(response.status_code, 403)

    def test_legacy_aliases_still_work(self):
        play = self.client.post("/play", headers=self.headers)
        self.assertEqual(play.status_code, 200)
        self.assertTrue(play.get_json()["playing"])

        status = self.client.get("/status", headers=self.headers)
        self.assertEqual(status.status_code, 200)
        self.assertIn("revision", status.get_json())


class TestStatePlayingField(unittest.TestCase):
    def test_state_snapshot_includes_playing(self):
        state = State(
            version="1.0",
            started_at=datetime.now(UTC),
            current_channel_id=1,
            current_channel_name="Test",
            playing=False,
        )
        manager = StateManager(state)
        snapshot = manager.get_snapshot()
        self.assertFalse(snapshot["playing"])


if __name__ == "__main__":
    unittest.main()
