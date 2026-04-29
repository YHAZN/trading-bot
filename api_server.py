#!/usr/bin/env python3
"""Simple API server to expose bot stats to dashboard"""

from flask import Flask, jsonify, make_response
import json
from pathlib import Path

app = Flask(__name__)

STATS_FILE = Path(__file__).parent / "data" / "stats.json"

def add_cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return resp

@app.route('/api/stats')
def get_stats():
    try:
        if STATS_FILE.exists():
            with open(STATS_FILE) as f:
                data = json.load(f)
        else:
            data = {"balance": 10000, "total_pnl": 0, "total_trades": 0, "win_rate": 0, "open_positions": 0}
        return add_cors(make_response(jsonify(data)))
    except Exception as e:
        return add_cors(make_response(jsonify({"error": str(e)}), 500))

@app.route('/api/health')
def health():
    return add_cors(make_response(jsonify({"status": "ok"})))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3002, debug=False)
