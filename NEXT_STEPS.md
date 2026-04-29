# Next Steps - Trading Bot Setup

## ✅ Done
- [x] Switched from Binance to Kraken (US-compliant)
- [x] Created Kraken config file
- [x] Created setup guide
- [x] Created connection test script
- [x] Updated README

## 📋 TODO (In Order)

### 1. Get Kraken Demo Account (5 min)
```bash
# Go to: https://demo.kraken.com
# Sign up, get demo API keys
# Save to: ~/.openclaw/credentials/kraken-demo.json
```

### 2. Test Connection (2 min)
```bash
cd ~/Workspace/trading-bot
python3 scripts/test-kraken-connection.py
```

### 3. Build Data Pipeline (Week 1)
- WebSocket connection to Kraken
- Store tick data in TimescaleDB
- Real-time price feeds for BTC/ETH

### 4. Implement First Strategy (Week 1)
- Mean reversion strategy
- Regime detection (trending vs ranging)
- Backtesting framework

### 5. Add Risk Management (Week 1)
- Position sizing (2% per trade)
- Stop-losses (automatic)
- Daily loss limits (5% max)

### 6. Paper Trading (Week 2-3)
- Run on demo account
- Monitor performance
- Refine strategies

### 7. Go Live (Week 4+)
- Only after 2+ weeks profitable paper trading
- Start with small capital ($500-1000)
- Scale gradually

---

## Quick Commands

**Test connection:**
```bash
python3 ~/Workspace/trading-bot/scripts/test-kraken-connection.py
```

**View config:**
```bash
cat ~/Workspace/trading-bot/config/kraken.json
```

**Read setup guide:**
```bash
cat ~/Workspace/trading-bot/docs/KRAKEN_SETUP.md
```

---

## Files Created

- `config/kraken.json` - Exchange config
- `docs/KRAKEN_SETUP.md` - Setup guide
- `scripts/test-kraken-connection.py` - Connection test
- `NEXT_STEPS.md` - This file

---

**First action:** Go to https://demo.kraken.com and create demo account.
