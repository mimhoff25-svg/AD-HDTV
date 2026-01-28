@app.route('/api_options', methods=['GET'])
def api_options():
    options = [
        {
            'endpoint': '/play',
            'method': 'POST',
            'description': 'Start playback.'
        },
        {
            'endpoint': '/pause',
            'method': 'POST',
            'description': 'Pause playback.'
        },
        {
            'endpoint': '/channel_up',
            'method': 'POST',
            'description': 'Increase channel number.'
        },
        {
            'endpoint': '/channel_down',
            'method': 'POST',
            'description': 'Decrease channel number.'
        },
        {
            'endpoint': '/status',
            'method': 'GET',
            'description': 'Get current player status.'
        }
    ]
    return jsonify({'api_options': options})
# Remote control API for AD_HDTV
# Simple Flask server to receive remote commands

from flask import Flask, request, jsonify
import threading

app = Flask(__name__)

# Example: You should connect these to your real player logic
player_state = {
    'playing': False,
    'channel': 1
}

@app.route('/play', methods=['POST'])
def play():
    player_state['playing'] = True
    # TODO: Call your play logic here
    return jsonify({'status': 'playing'})

@app.route('/pause', methods=['POST'])
def pause():
    player_state['playing'] = False
    # TODO: Call your pause logic here
    return jsonify({'status': 'paused'})

@app.route('/channel_up', methods=['POST'])
def channel_up():
    player_state['channel'] += 1
    # TODO: Call your channel up logic here
    return jsonify({'channel': player_state['channel']})

@app.route('/channel_down', methods=['POST'])
def channel_down():
    player_state['channel'] = max(1, player_state['channel'] - 1)
    # TODO: Call your channel down logic here
    return jsonify({'channel': player_state['channel']})

@app.route('/status', methods=['GET'])
def status():
    return jsonify(player_state)


def run_api():
    app.run(host='0.0.0.0', port=5005, debug=False)

# To run in a thread from your main app:
# threading.Thread(target=run_api, daemon=True).start()

if __name__ == '__main__':
    run_api()
