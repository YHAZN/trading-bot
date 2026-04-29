# Dual-Mode Trading Bot Architecture

## Design Philosophy

**One codebase, two modes:**
- Paper trading (sandbox) - Learn and optimize
- Live trading (production) - Execute with real money

**Switch with a single flag:** `--mode=paper` or `--mode=live`

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Trading Bot Core                       │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐      ┌──────────────┐                │
│  │   Strategy   │─────▶│   Execution  │                │
│  │   Engine     │      │   Router     │                │
│  └──────────────┘      └──────┬───────┘                │
│                                │                         │
│                    ┌───────────┴───────────┐            │
│                    │                       │            │
│             ┌──────▼──────┐        ┌──────▼──────┐     │
│             │   Paper     │        │    Live     │     │
│             │   Executor  │        │   Executor  │     │
│             │  (Simulated)│        │   (Real $)  │     │
│             └─────────────┘        └─────────────┘     │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## Paper Trading Mode

**What it does:**
- Simulates trades with fake money ($10,000 starting balance)
- Uses real live prices from Kraken
- Tracks P&L, win rate, drawdown
- Logs every trade decision
- No real money at risk

**Data collected:**
- Trade history (entry/exit prices, timing)
- Strategy performance (win rate, profit factor)
- Risk metrics (max drawdown, Sharpe ratio)
- Market conditions when trades happen

**Learning phase:**
- Run for 2-4 weeks minimum
- Test different strategies
- Optimize parameters
- Build confidence

---

## Live Trading Mode

**What it does:**
- Places real orders on Kraken
- Uses real money
- Same strategies as paper mode
- Same risk management rules

**Safety checks before going live:**
1. ✅ Paper trading profitable for 2+ weeks
2. ✅ Win rate >55%
3. ✅ Max drawdown <10%
4. ✅ Sharpe ratio >1.5
5. ✅ Risk management tested

**Start small:**
- Begin with $500-1000
- 1% position sizes
- Scale up gradually

---

## Mode Switching

**Configuration file:** `config/mode.json`

```json
{
  "mode": "paper",
  "paper": {
    "starting_balance": 10000,
    "use_live_prices": true,
    "log_all_trades": true
  },
  "live": {
    "max_position_size": 0.02,
    "daily_loss_limit": 0.05,
    "require_confirmation": true
  }
}
```

**To switch modes:**
```bash
# Paper trading (default)
./run.sh --mode=paper

# Live trading (after testing)
./run.sh --mode=live
```

---

## Shared Components

**Both modes use:**
- Same data pipeline (live Kraken prices)
- Same strategy engine
- Same risk management
- Same logging/monitoring

**Only difference:**
- Paper mode: simulates fills
- Live mode: sends real orders

---

## Safety Features

**Paper mode:**
- Can't lose real money
- Can test aggressive strategies
- Fast iteration

**Live mode:**
- Position size limits
- Daily loss limits
- Stop-losses enforced
- Confirmation required for large trades

---

## Metrics Tracked (Both Modes)

- Total P&L
- Win rate
- Profit factor
- Max drawdown
- Sharpe ratio
- Average trade duration
- Best/worst trades

---

## Next Steps

1. Build paper trading executor
2. Implement first strategy (mean reversion)
3. Run paper trading for 2 weeks
4. Analyze results
5. Optimize strategy
6. Switch to live (if profitable)

---

**Remember:** Paper trading success doesn't guarantee live success, but paper trading failure definitely predicts live failure. Test thoroughly.
