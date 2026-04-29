#!/usr/bin/env python3
"""Simple dashboard server - serves logs via HTTP"""

import http.server
import socketserver
import json
import subprocess
from pathlib import Path

PORT = 8888

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.get_dashboard_html().encode())
        
        elif self.path == '/api/logs':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Read PM2 logs
            log_file = Path.home() / '.pm2/logs/trading-bot-out.log'
            if log_file.exists():
                with open(log_file) as f:
                    lines = f.readlines()[-100:]  # Last 100 lines
                self.wfile.write(json.dumps({'logs': lines}).encode())
            else:
                self.wfile.write(json.dumps({'logs': ['Bot not started yet']}).encode())
        
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Check PM2 status
            try:
                result = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True)
                processes = json.loads(result.stdout)
                bot = next((p for p in processes if p['name'] == 'trading-bot'), None)
                
                if bot:
                    status = {
                        'running': bot['pm2_env']['status'] == 'online',
                        'uptime': bot['pm2_env']['pm_uptime'],
                        'restarts': bot['pm2_env']['restart_time']
                    }
                else:
                    status = {'running': False}
                
                self.wfile.write(json.dumps(status).encode())
            except:
                self.wfile.write(json.dumps({'running': False}).encode())
        
        else:
            super().do_GET()
    
    def get_dashboard_html(self):
        return '''<!DOCTYPE html>
<html>
<head>
    <title>Trading Bot Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Monaco', 'Courier New', monospace;
            background: #0a0e27;
            color: #00ff41;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 2em;
            text-shadow: 0 0 10px #00ff41;
        }
        .status {
            text-align: center;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 1.2em;
        }
        .status.running { background: rgba(0, 255, 65, 0.2); color: #00ff41; }
        .status.stopped { background: rgba(255, 65, 54, 0.2); color: #ff4136; }
        .panel {
            background: #1a1f3a;
            border: 2px solid #00ff41;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 0 20px rgba(0, 255, 65, 0.3);
            margin-bottom: 20px;
        }
        .panel h2 {
            margin-bottom: 15px;
            color: #00ff41;
            font-size: 1.3em;
        }
        .logs {
            background: #0a0e27;
            padding: 15px;
            border-radius: 5px;
            height: 500px;
            overflow-y: auto;
            font-size: 0.9em;
            line-height: 1.6;
        }
        .log-line {
            padding: 5px 0;
            border-bottom: 1px solid #1a1f3a;
        }
        .log-trade { color: #ffd700; font-weight: bold; }
        .log-error { color: #ff4136; }
        .controls {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-top: 20px;
        }
        button {
            background: #00ff41;
            color: #0a0e27;
            border: none;
            padding: 15px 30px;
            font-size: 1em;
            font-weight: bold;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }
        button:hover {
            background: #00cc33;
            box-shadow: 0 0 20px rgba(0, 255, 65, 0.5);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 TRADING BOT DASHBOARD</h1>
        
        <div class="status running" id="status">
            ● RUNNING - Paper Trading Mode
        </div>
        
        <div class="panel">
            <h2>🧠 Bot Thoughts (Live)</h2>
            <div class="logs" id="logs">
                Loading...
            </div>
        </div>
        
        <div class="controls">
            <button onclick="location.reload()">🔄 Refresh</button>
            <button onclick="window.open('http://localhost:8888/api/logs')">📋 Raw Logs</button>
        </div>
    </div>
    
    <script>
        async function fetchLogs() {
            try {
                const response = await fetch('/api/logs');
                const data = await response.json();
                
                const logsDiv = document.getElementById('logs');
                logsDiv.innerHTML = data.logs.map(line => {
                    let className = 'log-line';
                    if (line.includes('BUY') || line.includes('SELL') || line.includes('💰') || line.includes('💸')) {
                        className += ' log-trade';
                    }
                    if (line.includes('⚠️') || line.includes('❌')) {
                        className += ' log-error';
                    }
                    return `<div class="${className}">${line}</div>`;
                }).join('');
                
                // Scroll to bottom
                logsDiv.scrollTop = logsDiv.scrollHeight;
            } catch (error) {
                console.error('Failed to fetch logs:', error);
            }
        }
        
        async function checkStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                const statusDiv = document.getElementById('status');
                if (data.running) {
                    statusDiv.className = 'status running';
                    statusDiv.textContent = '● RUNNING - Paper Trading Mode';
                } else {
                    statusDiv.className = 'status stopped';
                    statusDiv.textContent = '● STOPPED';
                }
            } catch (error) {
                console.error('Failed to check status:', error);
            }
        }
        
        // Auto-refresh every 2 seconds
        setInterval(() => {
            fetchLogs();
            checkStatus();
        }, 2000);
        
        fetchLogs();
        checkStatus();
    </script>
</body>
</html>'''

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"\n{'='*60}")
        print(f"🌐 Dashboard running at: http://localhost:{PORT}")
        print(f"{'='*60}\n")
        httpd.serve_forever()
