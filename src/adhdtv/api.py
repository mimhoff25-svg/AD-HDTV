from flask import Flask, request, jsonify, Response
import threading
import time
import json
from .state_manager import StateManager
from .state import State
from .guide_generator import generate_fake_guide
from datetime import datetime

app = Flask(__name__)

# Global state manager instance (should be initialized in runner)
state_manager: StateManager = None
sse_subscribers = set()

@app.route('/status', methods=['GET'])
def status():
    return jsonify(state_manager.get_snapshot())

@app.route('/events', methods=['GET'])
def events():
    def event_stream():
        last_rev = state_manager.revision
        while True:
            time.sleep(0.5)
            rev = state_manager.revision
            if rev != last_rev:
                data = json.dumps(state_manager.get_snapshot())
                yield f"data: {data}\n\n"
                last_rev = rev
    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/control/channel/next', methods=['POST'])
def channel_next():
    def mut(state):
        state.current_channel_id = int(state.current_channel_id) + 1
        state.current_channel_name = f"Channel {state.current_channel_id}"
    state_manager.update(mut)
    return jsonify(state_manager.get_snapshot())

@app.route('/control/channel/prev', methods=['POST'])
def channel_prev():
    def mut(state):
        state.current_channel_id = max(1, int(state.current_channel_id) - 1)
        state.current_channel_name = f"Channel {state.current_channel_id}"
    state_manager.update(mut)
    return jsonify(state_manager.get_snapshot())

@app.route('/control/channel/set', methods=['POST'])
def channel_set():
    cid = request.args.get('id')
    if not cid:
        return jsonify({'error': 'Missing id'}), 400
    def mut(state):
        state.current_channel_id = cid
        state.current_channel_name = f"Channel {cid}"
    state_manager.update(mut)
    return jsonify(state_manager.get_snapshot())

@app.route('/control/select', methods=['POST'])
def select():
    row = request.args.get('row')
    col = request.args.get('col')
    channel_id = request.args.get('channel_id')
    def mut(state):
        if row: state.selected.row = int(row)
        if col: state.selected.col = int(col)
        if channel_id: state.selected.channel_id = channel_id
    state_manager.update(mut)
    return jsonify(state_manager.get_snapshot())

@app.route('/control/guide/show', methods=['POST'])
def guide_show():
    def mut(state):
        state.guide_visible = True
    state_manager.update(mut)
    return jsonify(state_manager.get_snapshot())

@app.route('/control/guide/hide', methods=['POST'])
def guide_hide():
    def mut(state):
        state.guide_visible = False
    state_manager.update(mut)
    return jsonify(state_manager.get_snapshot())

@app.route('/control/audio/solo', methods=['POST'])
def audio_solo():
    source_id = request.args.get('id')
    if not source_id:
        return jsonify({'error': 'Missing id'}), 400
    def mut(state):
        state.audio.solo_source_id = source_id
    state_manager.update(mut)
    return jsonify(state_manager.get_snapshot())

@app.route('/control/audio/mute', methods=['POST'])
def audio_mute():
    value = request.args.get('value')
    if value not in ('0', '1'):
        return jsonify({'error': 'Missing or invalid value'}), 400
    def mut(state):
        state.audio.muted = (value == '1')
    state_manager.update(mut)
    return jsonify(state_manager.get_snapshot())

@app.route('/guide', methods=['GET'])
def guide():
    hours = int(request.args.get('hours', 2))
    start = request.args.get('start')
    if start:
        try:
            start_dt = datetime.fromisoformat(start)
        except Exception:
            return jsonify({'error': 'Invalid start'}), 400
    else:
        start_dt = None
    guide = generate_fake_guide(hours=hours, start=start_dt)
    return jsonify(guide.__dict__)

def run_api(state_mgr: StateManager):
    global state_manager
    state_manager = state_mgr
    app.run(host='0.0.0.0', port=5005, debug=False, threaded=True)
