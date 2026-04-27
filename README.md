# AI Trading Bot - TODO FUN

**Status:** Week 1 - Building Spot Trading Engine
**Started:** April 27, 2026
**Goal:** Institutional-grade trading bot with smart strategies

---

## Project Overview

**Phase 1 (Week 1):** Spot trading (BTC/ETH)
- Paper trading on Binance testnet
- Mean reversion + regime detection
- Institutional risk management

**Phase 2 (Week 2-3):** Add futures (2-3x leverage)
- Only after spot is profitable
- Strict liquidation protection
- Shorting capabilities

**Phase 3 (Month 2+):** Scale and optimize
- Multi-strategy portfolio
- News-based trading
- Advanced indicators

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Trading Bot System                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │   Data       │─────▶│   Strategy   │─────▶│   Risk    │ │
│  │   Pipeline   │      │   Engine     │      │  Manager  │ │
│  └──────────────┘      └──────────────┘      └───────────┘ │
│         │                      │                     │       │
│         │                      │                     │       │
│         ▼                      ▼                     ▼       │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │  TimescaleDB │      │   OpenClaw   │      │ Execution │ │
│  │  (Storage)   │      │   (Agent)    │      │  Engine   │ │
│  └──────────────┘      └──────────────┘      └───────────┘ │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

**Execution Engine:** Rust
- Sub-millisecond latency
- Memory safe
- Production-grade

**Strategy Layer:** Python + OpenClaw
- Rapid iteration
- AI-powered analysis
- Easy to modify

**Database:** TimescaleDB
- Time-series optimized
- Stores tick data
- Fast queries

**Exchange:** Binance
- Best API
- High liquidity
- Testnet available

---

## Directory Structure

```
trading-bot/
├── README.md                 # This file
├── docs/
│   ├── STRATEGIES.md         # All trading strategies
│   ├── RISK_MANAGEMENT.md    # Risk rules and formulas
│   ├── ARCHITECTURE.md       # System design
│   ├── BACKTESTING.md        # Testing methodology
│   └── DEPLOYMENT.md         # How to run
├── src/
│   ├── engine/               # Rust execution engine
│   ├── strategy/             # Python strategies
│   ├── data/                 # Data pipeline
│   └── agent/                # OpenClaw integration
├── data/
│   ├── historical/           # Historical price data
│   ├── backtest/             # Backtest results
│   └── live/                 # Live trading logs
├── config/
│   ├── binance.json          # Exchange config
│   ├── strategies.json       # Strategy parameters
│   └── risk.json             # Risk limits
└── logs/                     # System logs
```

---

## Quick Start

**1. Setup (First Time)**
```bash
cd ~/Workspace/trading-bot
./scripts/setup.sh
```

**2. Paper Trading**
```bash
./scripts/run-paper.sh
```

**3. Live Trading (After Testing)**
```bash
./scripts/run-live.sh
```

---

## Documentation

- **[STRATEGIES.md](docs/STRATEGIES.md)** - Trading strategies and logic
- **[RISK_MANAGEMENT.md](docs/RISK_MANAGEMENT.md)** - Risk rules and position sizing
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and components
- **[BACKTESTING.md](docs/BACKTESTING.md)** - How to backtest strategies
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Deployment guide

---

## Current Status

**Week 1 Progress:**
- [x] Project structure created
- [ ] Data pipeline (Binance WebSocket)
- [ ] TimescaleDB setup
- [ ] Strategy engine (mean reversion)
- [ ] Risk management layer
- [ ] Backtesting framework
- [ ] Paper trading deployment

**Next Steps:**
1. Set up Binance testnet API keys
2. Build data pipeline
3. Implement first strategy
4. Run backtests
5. Deploy to paper trading

---

## Safety Rules

**NEVER:**
- Trade without stop-losses
- Use more than 2% per trade
- Exceed 5% total portfolio risk
- Trade during extreme volatility
- Ignore daily loss limits

**ALWAYS:**
- Paper trade first (minimum 2 weeks)
- Review trades daily
- Update risk limits
- Monitor system health
- Keep logs of everything

---

## Contact

**Owner:** Haze (TODO FUN)
**Agent:** Kō (Chief of Staff)
**Started:** April 27, 2026

---

**Remember:** This is a learning project. Expect losses. Never trade money you can't afford to lose.
