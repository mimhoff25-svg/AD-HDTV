from datetime import datetime

from src.adhdtv.api import build_state_manager, run_api

if __name__ == '__main__':
    state_manager = build_state_manager(
        version="1.0",
        current_channel_id=1,
        current_channel_name=f"Channel {datetime.utcnow().year}",
    )
    run_api(state_manager)
