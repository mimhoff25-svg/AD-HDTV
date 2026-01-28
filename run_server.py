
from src.adhdtv.state import State
from src.adhdtv.state_manager import StateManager
from src.adhdtv.api import run_api
from datetime import datetime
import threading
import remote_api

if __name__ == '__main__':
    # Initialize State and StateManager
    state = State(
        version="1.0",
        started_at=datetime.utcnow(),
        current_channel_id=1,
        current_channel_name="Channel 1"
    )
    state_manager = StateManager(state)

    # Start remote_api Flask server in a thread
    threading.Thread(target=remote_api.run_api, daemon=True).start()

    # Start main API server (blocking)
    run_api(state_manager)
