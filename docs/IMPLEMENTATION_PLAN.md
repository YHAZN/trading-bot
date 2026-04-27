# Implementation Plan - Week 1

**Goal:** Working trading bot on Binance testnet by end of week

**Approach:** Build fast, test continuously, iterate based on failures

---

## Day 1-2: Foundation (Data + Database)

### Tasks

**1. Environment Setup**
```bash
# Install dependencies
pip install websockets pandas numpy ta-lib psycopg2-binary redis python-binance

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Start Docker services
docker-compose up -d timescaledb redis
```

**2. Binance Testnet Setup**
- Create account: https://testnet.binance.vision/
- Generate API keys (trade permissions, no withdrawal)
- Save to `~/.openclaw/credentials/binance-testnet-api-key.txt`
- Save secret to `~/.openclaw/credentials/binance-testnet-secret.txt`

**3. TimescaleDB Schema**
```bash
# Run schema creation
psql -h localhost -U postgres -d trading_bot -f config/schema.sql
```

**4. Data Pipeline (Minimal)**
```python
# src/data/websocket_client.py
# Connect to Binance WebSocket
# Stream BTC/ETH 1-minute candles
# Save to TimescaleDB
# Calculate basic indicators (RSI, ATR, SMA)
```

**Success Criteria:**
- [ ] Binance testnet API keys working
- [ ] TimescaleDB running and accessible
- [ ] Data pipeline streaming live prices
- [ ] At least 1 hour of historical data stored
- [ ] Basic indicators calculated

---

## Day 3-4: Strategy Engine (Mean Reversion)

### Tasks

**1. Base Strategy Class**
```python
# src/strategy/base_strategy.py
# Abstract class for all strategies
# Methods: analyze(), generate_signal(), update_state()
```

**2. Mean Reversion Strategy**
```python
# src/strategy/mean_reversion.py
# Implement Z-score calculation
# Entry: Z-score < -2, RSI < 30, volume > 1.5x avg
# Exit: Z-score > 0 or stop loss hit
# Position sizing: Kelly Criterion (capped at 2%)
```

**3. Regime Detector**
```python
# src/strategy/regime_detector.py
# Calculate ADX
# Classify: RANGING (ADX < 25) or TRENDING (ADX > 25)
# Only run mean reversion in RANGING regime
```

**4. Backtesting Framework**
```python
# src/backtest/backtest_engine.py
# Load historical data from TimescaleDB
# Simulate trades
# Calculate metrics: win rate, Sharpe, max drawdown
```

**Success Criteria:**
- [ ] Mean reversion strategy implemented
- [ ] Regime detector working
- [ ] Backtest on 3+ months of data
- [ ] Win rate > 50%, Sharpe > 1.0
- [ ] Strategy generates signals on live data

---

## Day 5-6: Risk Management + Execution

### Tasks

**1. Risk Manager**
```python
# src/risk/position_sizer.py
# Kelly Criterion implementation
# Volatility adjustment (ATR-based)

# src/risk/portfolio_monitor.py
# Portfolio heat calculation
# Daily loss limit check
# Circuit breaker logic
```

**2. Execution Engine (Rust - Minimal)**
```rust
// src/engine/main.rs
// Connect to Binance testnet API
// Place market orders
// Track positions
// Monitor stop losses

// Paper trading mode (no real orders)
// Just log what would be executed
```

**3. Discord Alerts**
```python
# src/alerts/discord_notifier.py
# Send alerts for:
# - Position opened
# - Position closed
# - Stop loss hit
# - Daily loss limit reached
```

**Success Criteria:**
- [ ] Risk manager validates all signals
- [ ] Execution engine can place testnet orders
- [ ] Stop losses monitored in real-time
- [ ] Discord alerts working
- [ ] Paper trading mode functional

---

## Day 7: Integration + Testing

### Tasks

**1. Full Pipeline Integration**
```bash
# Start all components
./scripts/start_all.sh

# Components:
# - Data pipeline (WebSocket)
# - Strategy engine (mean reversion)
# - Risk manager
# - Execution engine (paper mode)
# - Discord alerts
```

**2. End-to-End Testing**
- [ ] Data flows from Binance → TimescaleDB
- [ ] Strategy generates signals
- [ ] Risk manager approves/rejects signals
- [ ] Execution engine logs trades
- [ ] Discord receives alerts
- [ ] System runs for 24 hours without crashes

**3. Performance Validation**
- [ ] Backtest results match expectations
- [ ] Live signals make sense (not random)
- [ ] Risk limits enforced correctly
- [ ] No memory leaks or crashes

**4. Documentation**
```bash
# Update README with:
# - How to run the system
# - How to check if it's working
# - How to stop it
# - Common issues and fixes
```

**Success Criteria:**
- [ ] System runs end-to-end
- [ ] At least 5 paper trades executed
- [ ] All components communicate correctly
- [ ] No critical bugs
- [ ] Ready for 24/7 paper trading

---

## Week 2 Plan (If Week 1 Succeeds)

### Goals
1. Run paper trading for 7 days
2. Monitor performance daily
3. Fix bugs as they appear
4. Tune strategy parameters
5. Add momentum strategy (if mean reversion works)

### Decision Point (End of Week 2)
- **If profitable in paper trading:** Go live with $200-300
- **If break-even:** Continue paper trading, tune parameters
- **If losing:** Debug strategy, review assumptions

---

## Delegation Strategy

### What I'll Build Directly
- Architecture and design
- Core strategy logic
- Risk management rules
- Integration and testing

### What I Can Delegate (If Needed)
- Rust execution engine (can use coding agent)
- Data pipeline boilerplate (straightforward)
- Database schema setup (standard SQL)
- Discord bot integration (simple API)

### When to Delegate
- Only after I've designed the interface
- Only for well-defined tasks
- Only if it saves significant time
- Never for critical logic (strategies, risk)

---

## Risk Mitigation

### Technical Risks
| Risk | Mitigation |
|------|------------|
| Binance API rate limits | Cache data, batch requests |
| WebSocket disconnects | Auto-reconnect logic |
| Database crashes | Redis cache, auto-restart |
| Execution engine bugs | Paper trading first, extensive testing |
| Strategy overfitting | Walk-forward validation, out-of-sample testing |

### Trading Risks
| Risk | Mitigation |
|------|------------|
| Strategy loses money | Paper trade first, strict stop losses |
| Flash crash | Circuit breakers, pause trading |
| API delays | Monitor latency, pause if >1s |
| Slippage | Use limit orders, monitor execution quality |
| Correlation risk | Max 1 position per asset direction |

---

## Success Metrics (Week 1)

### Technical
- [ ] System uptime > 95%
- [ ] Data pipeline latency < 100ms
- [ ] Order execution latency < 500ms
- [ ] Zero crashes or data loss

### Strategy
- [ ] Backtest Sharpe ratio > 1.0
- [ ] Backtest win rate > 50%
- [ ] Backtest max drawdown < 15%
- [ ] Live signals align with backtest

### Process
- [ ] All code documented
- [ ] All strategies in STRATEGIES.md
- [ ] All risks in RISK_MANAGEMENT.md
- [ ] System can run unattended

---

## Daily Checklist

### Every Morning
- [ ] Check system health (all components running?)
- [ ] Review overnight trades (if any)
- [ ] Check Discord alerts
- [ ] Verify data pipeline (no gaps?)
- [ ] Update progress in README

### Every Evening
- [ ] Review day's performance
- [ ] Check for errors in logs
- [ ] Commit code changes
- [ ] Update documentation
- [ ] Plan next day's tasks

---

## Emergency Procedures

### If System Crashes
1. Check logs: `tail -f logs/*.log`
2. Restart crashed component: `./scripts/restart.sh <component>`
3. Verify data integrity: `./scripts/check_data.sh`
4. Alert Boss if can't fix in 30 minutes

### If Strategy Loses >3% in One Day
1. Pause trading immediately: `touch STOP`
2. Review all trades: `./scripts/review_trades.sh`
3. Check for bugs or market anomalies
4. Don't resume until root cause found

### If Binance API Issues
1. Check status: https://www.binance.com/en/support/announcement
2. Pause trading: `touch STOP`
3. Wait for API to recover
4. Backfill any missing data

---

## Tools and Resources

### Development
- **IDE:** VS Code with Python + Rust extensions
- **Database client:** DBeaver or psql
- **API testing:** Postman or curl
- **Monitoring:** htop, docker stats

### Learning
- **Binance API docs:** https://binance-docs.github.io/apidocs/spot/en/
- **TA-Lib docs:** https://ta-lib.org/
- **TimescaleDB docs:** https://docs.timescale.com/
- **Rust async:** https://tokio.rs/

### Debugging
- **Python debugger:** pdb or ipdb
- **Rust debugger:** rust-gdb or lldb
- **Network:** Wireshark (if needed)
- **Logs:** journalctl, docker logs

---

## Notes

- **Speed matters, but correctness matters more**
- **Test every component before integration**
- **Document as you build (not after)**
- **Ask for help if stuck >1 hour**
- **Commit code daily (even if incomplete)**

**Remember:** Week 1 is about building the foundation. It doesn't need to be profitable yet, just functional.
