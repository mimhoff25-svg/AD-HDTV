from src.adhdtv.state import State
from src.adhdtv.state_manager import StateManager
from src.adhdtv.api import run_api
from datetime import datetime
import threading

if __name__ == '__main__':
    # Initialize State and StateManager
    state = State(
        version="1.0",
        started_at=datetime.utcnow(),
        current_channel_id=1,
        current_channel_name="Channel 1"
    )
    state_manager = StateManager(state)

    # Start API server (blocking)
    run_api(state_manager)
