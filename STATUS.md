# Project Status

**Last Updated:** April 29, 2026

---

## Current Phase: Active Development

**Status:** Agent running (paper mode), ORB + mean-reversion strategies live

---

## Completed

### Documentation
- [x] README.md — project overview
- [x] docs/STRATEGIES.md — strategies 1-3 (mean reversion, momentum, news) + **ORB (Strategy 4)**
- [x] docs/RISK_MANAGEMENT.md — risk rules and position sizing
- [x] docs/ARCHITECTURE.md — system design
- [x] docs/MULTI_AGENT_ARCHITECTURE.md — **asymmetric agent upgrade plan (new)**
- [x] VISION.md — target architecture

### Agent (agent.py)
- [x] BTC mean reversion (24/7, Kraken data)
- [x] ORB scalping (NYSE session, 9:14-11:30 AM ET)
- [x] Supabase logging (trades, bot_logs, bot_state)
- [x] Aggressive trailing stop (10 pts, ORB-specific)
- [x] Paper trading mode
- [x] TradingRouter (paper/live switcher)

### Exchange
- [x] Migrated from Binance to Kraken (US-compliant)
- [x] Paper trader implementation
- [x] Live trader stub

### Dashboard
- [x] Next.js Bloomberg-style terminal (trading-dashboard repo)
- [x] Supabase real-time data feed
- [x] P&L chart, candle chart, trade log
- [x] Bot state panel (balance, win rate, open positions)

---

## In Progress

### ORB Trailing Stop Refinement
- [ ] Validate trailing stop activates correctly tick-by-tick
- [ ] Backtest on Kraken XBTUSD 15-min data

### Multi-Agent Architecture (Phase 1)
- [ ] Extract technical logic → `src/agents/technical_agent.py`
- [ ] Add FRED economic data fetcher (macro agent feed)
- [ ] Add NewsAPI integration (sentiment agent feed)
- [ ] Quality gate (composite score ≥ 0.35)

---

## Next Steps

**Immediate:**
1. Validate ORB trailing stop behavior in paper mode
2. Start Phase 1 of multi-agent refactor (extract agent modules)
3. Add FRED API key to credentials

**This Week:**
- Run ORB strategy during NYSE open, monitor logs in dashboard
- Begin asymmetric data feed implementation
- Add per-agent confidence panel to dashboard

**Next Week:**
- Full multi-agent pipeline test (all 3 specialist agents + synthesis)
- Dashboard upgrade: Agent Decision Panel
- Consider: quantitative finance courses (Haze mentioned interest)

---

## Key Decisions Made

1. **Spot trading first** (not futures) — lower risk
2. **BTC/ETH + NASDAQ ORB** — diversified signal sources
3. **Paper trading minimum 2 weeks** — no real money until proven
4. **ORB trailing stop = 10 pts** — from 5-year backtest (88% win rate)
5. **Asymmetric data feeds** — fix for symmetric-agent failure mode
6. **Quality gate at 0.35** — filter marginal setups before execution

---

## Architecture Reference

```
agent.py (orchestrator)
├── src/executor/trading_router.py  → paper/live switcher
├── src/executor/paper_trader.py    → paper trading logic
├── src/executor/live_trader.py     → Kraken live execution (stub)
└── [planned] src/agents/
    ├── technical_agent.py          → OHLCV only
    ├── macro_agent.py              → FRED + economic data
    ├── sentiment_agent.py          → news + Fear & Greed
    └── synthesis_agent.py          → composite scoring + quality gate
```

---

## Risks and Mitigation

| Risk | Mitigation |
|---|---|
| ORB strategy doesn't hold on crypto | Primary target is NASDAQ (US 100); BTC is secondary |
| Agent disagreement causes paralysis | Synthesis agent makes final call; HOLD is valid output |
| API rate limits | Exponential backoff, tiered polling |
| System crash during ORB window | PM2 auto-restart; ORB state resets cleanly each day |
| Overfitting | Walk-forward validation before any live capital |

---

## Team

**Owner:** Haze (TODO FUN)
**Builder:** Kō (Chief of Staff)
**Started:** April 27, 2026
