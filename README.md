# AI Trading Bot - Dual Mode (Paper + Live)

**Status:** ✅ Paper trading ready | 🔒 Live trading locked until proven

---

## Quick Start

### Paper Trading (Safe - No Real Money)
```bash
cd ~/Workspace/trading-bot
python3 run.py --mode=paper --duration=60
```

### Live Trading (Real Money - Use After Testing)
```bash
python3 run.py --mode=live --duration=60
```

---

## What's Built

✅ **Dual-mode architecture**
- Paper trading executor (simulated fills)
- Live trading executor (real Kraken orders)
- Smart router that switches between them

✅ **Kraken API connected**
- Real-time price feeds
- Account balance checks
- Order placement ready

✅ **Risk management**
- Position size limits (2% per trade)
- Stop-losses (2%)
- Daily loss limits (5%)
- Slippage simulation (5 bps)
- Commission simulation (16 bps = Kraken fees)

✅ **Safety features**
- Confirmation required for live trades
- Paper mode can't touch real money
- All trades logged

---

## Architecture

```
run.py (main bot)
    ↓
trading_router.py (mode switcher)
    ↓
    ├─→ paper_trader.py (simulated)
    └─→ live_trader.py (real Kraken API)
```

---

## Configuration

**File:** `config/mode.json`

```json
{
  "mode": "paper",  ← Change to "live" when ready
  "paper": {
    "starting_balance": 10000,
    "slippage_bps": 5,
    "commission_bps": 16
  },
  "live": {
    "max_position_size": 0.02,
    "daily_loss_limit": 0.05,
    "require_confirmation": true
  }
}
```

---

## Testing

**Test paper trading:**
```bash
cd ~/Workspace/trading-bot
python3 run.py --mode=paper --duration=60
```

**Test Kraken connection:**
```bash
python3 scripts/test-kraken-connection.py
```

---

## Next Steps

### Week 1 (Current)
- [x] Kraken API connected
- [x] Paper trading executor
- [x] Live trading executor
- [x] Trading router
- [ ] Implement mean reversion strategy
- [ ] Add data pipeline (WebSocket)
- [ ] Add backtesting

### Week 2-3
- [ ] Run paper trading 24/7
- [ ] Collect performance data
- [ ] Optimize strategy parameters
- [ ] Add more strategies

### Week 4+
- [ ] Review paper trading results
- [ ] If profitable (>55% win rate, Sharpe >1.5):
  - Switch to live mode
  - Start with $500-1000
  - Scale gradually

---

## Safety Rules

**NEVER go live until:**
1. ✅ Paper trading profitable for 2+ weeks
2. ✅ Win rate >55%
3. ✅ Max drawdown <10%
4. ✅ Sharpe ratio >1.5
5. ✅ You understand every trade the bot makes

**When live:**
- Start small ($500-1000)
- 1-2% position sizes
- Monitor daily
- Stop if daily loss >5%

---

## Files

```
trading-bot/
├── run.py                    # Main bot runner
├── config/
│   ├── mode.json             # Paper/live mode config
│   └── kraken.json           # Kraken API config
├── src/
│   └── executor/
│       ├── paper_trader.py   # Paper trading engine
│       ├── live_trader.py    # Live trading engine
│       └── trading_router.py # Mode switcher
├── scripts/
│   └── test-kraken-connection.py
├── data/
│   └── paper_trading_state.json  # Paper trading logs
└── docs/
    ├── DUAL_MODE_ARCHITECTURE.md
    └── KRAKEN_SETUP.md
```

---

## Current Status

**Paper trading:** ✅ Working
**Live trading:** ✅ Working (but locked behind confirmation)
**Strategy:** ⏳ Simple buy/sell (needs improvement)
**Data pipeline:** ⏳ Not built yet
**Backtesting:** ⏳ Not built yet

---

**Remember:** Paper trading success doesn't guarantee live success. Test thoroughly.
