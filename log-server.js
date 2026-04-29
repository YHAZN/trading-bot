const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const os = require('os');

const app = express();
app.use(cors());

app.get('/api/bot-logs', (req, res) => {
  try {
    const logPath = path.join(os.homedir(), '.pm2/logs/trading-bot-out.log');
    const content = fs.readFileSync(logPath, 'utf-8');
    const lines = content.split('\n').filter(l => l.trim()).slice(-100);
    res.json({ logs: lines });
  } catch (error) {
    res.json({ logs: ['Bot not started yet'], error: error.message });
  }
});

const PORT = 3001;
app.listen(PORT, () => {
  console.log(`Log server running on http://localhost:${PORT}`);
});
