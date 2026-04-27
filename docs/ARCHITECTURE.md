# System Architecture

**Last Updated:** April 27, 2026

Technical design of the trading bot system.

---

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Trading Bot System                        │
└─────────────────────────────────────────────────────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │     Data     │  │   Strategy   │  │     Risk     │
        │   Pipeline   │  │    Engine    │  │   Manager    │
        └──────────────┘  └──────────────┘  └──────────────┘
                │                │                │
                └────────────────┼────────────────┘
                                 │
                                 ▼
                        ┌──────────────┐
                        │  Execution   │
                        │    Engine    │
                        └──────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │   Binance    │  │ TimescaleDB  │  │   Discord    │
        │     API      │  │   Storage    │  │    Alerts    │
        └──────────────┘  └──────────────┘  └──────────────┘
```

---

## Components

### 1. Data Pipeline (Python)

**Purpose:** Ingest, normalize, and store market data

**Responsibilities:**
- WebSocket connection to Binance
- Real-time price/volume data
- Historical data backfill
- Feature engineering (indicators)
- Data validation and cleaning

**Tech Stack:**
- Python 3.11+
- `websockets` library
- `pandas` for data manipulation
- `ta-lib` for technical indicators
- TimescaleDB for storage

**Key Files:**
```
src/data/
├── websocket_client.py    # Binance WebSocket connection
├── data_processor.py      # Clean and normalize data
├── indicators.py          # Calculate technical indicators
├── storage.py             # TimescaleDB interface
└── backfill.py            # Historical data download
```

**Data Flow:**
```
Binance WebSocket → Raw Data → Validation → Normalization → 
Indicator Calculation → TimescaleDB → Strategy Engine
```

---

### 2. Strategy Engine (Python + OpenClaw)

**Purpose:** Analyze market data and generate trading signals

**Responsibilities:**
- Implement trading strategies
- Regime detection (trend vs range)
- News sentiment analysis (Claude)
- Signal generation
- Strategy performance tracking

**Tech Stack:**
- Python 3.11+
- OpenClaw for AI integration
- Claude for NLP/sentiment
- NumPy/Pandas for calculations

**Key Files:**
```
src/strategy/
├── base_strategy.py       # Abstract strategy class
├── mean_reversion.py      # Mean reversion strategy
├── momentum.py            # Momentum breakout strategy
├── news_sentiment.py      # News-based strategy
├── regime_detector.py     # Market regime detection
└── portfolio_manager.py   # Multi-strategy coordination
```

**Signal Format:**
```python
{
    "strategy": "mean_reversion",
    "asset": "BTCUSDT",
    "action": "BUY",
    "confidence": 0.85,
    "entry_price": 60000,
    "stop_loss": 58000,
    "take_profit": 61500,
    "position_size": 0.02,  # 2% of portfolio
    "reason": "Z-score < -2, RSI oversold, volume spike"
}
```

---

### 3. Risk Manager (Python)

**Purpose:** Enforce risk limits and position sizing

**Responsibilities:**
- Position size calculation (Kelly Criterion)
- Stop loss validation
- Portfolio heat monitoring
- Daily/weekly loss limits
- Circuit breaker checks
- Correlation risk management

**Tech Stack:**
- Python 3.11+
- NumPy for calculations

**Key Files:**
```
src/risk/
├── position_sizer.py      # Kelly Criterion, volatility adjustment
├── stop_loss.py           # ATR-based stops, trailing stops
├── portfolio_monitor.py   # Portfolio heat, drawdown tracking
├── circuit_breaker.py     # Emergency stop conditions
└── risk_alerts.py         # Discord notifications
```

**Risk Check Flow:**
```
Signal → Position Size Check → Stop Loss Validation → 
Portfolio Heat Check → Daily Limit Check → Correlation Check → 
Approve/Reject
```

---

### 4. Execution Engine (Rust)

**Purpose:** Execute trades with minimal latency

**Responsibilities:**
- Order placement (market/limit)
- Order status tracking
- Position management
- Slippage monitoring
- Exchange API health checks

**Tech Stack:**
- Rust 1.75+
- `tokio` for async runtime
- `reqwest` for HTTP
- `tungstenite` for WebSocket

**Key Files:**
```
src/engine/
├── main.rs                # Entry point
├── exchange.rs            # Binance API client
├── order_manager.rs       # Order lifecycle management
├── position_tracker.rs    # Track open positions
└── health_monitor.rs      # API latency, errors
```

**Why Rust:**
- Sub-millisecond latency
- Memory safety (no crashes)
- Concurrency (handle multiple orders)
- Production-grade reliability

---

### 5. TimescaleDB (Storage)

**Purpose:** Store time-series market data

**Schema:**
```sql
-- Price data (1-minute candles)
CREATE TABLE price_data (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume NUMERIC,
    PRIMARY KEY (time, symbol)
);

SELECT create_hypertable('price_data', 'time');

-- Indicators (calculated features)
CREATE TABLE indicators (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    rsi NUMERIC,
    macd NUMERIC,
    macd_signal NUMERIC,
    atr NUMERIC,
    adx NUMERIC,
    z_score NUMERIC,
    PRIMARY KEY (time, symbol)
);

SELECT create_hypertable('indicators', 'time');

-- Trades (executed trades)
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,  -- BUY/SELL
    entry_price NUMERIC,
    exit_price NUMERIC,
    quantity NUMERIC,
    pnl NUMERIC,
    pnl_pct NUMERIC,
    stop_loss NUMERIC,
    take_profit NUMERIC,
    exit_reason TEXT  -- STOP_LOSS/TAKE_PROFIT/MANUAL
);

-- Positions (currently open)
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    opened_at TIMESTAMPTZ NOT NULL,
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    entry_price NUMERIC,
    quantity NUMERIC,
    stop_loss NUMERIC,
    take_profit NUMERIC,
    current_pnl NUMERIC
);
```

---

### 6. OpenClaw Integration (Agent Layer)

**Purpose:** AI-powered analysis and decision support

**Responsibilities:**
- News sentiment analysis (Claude)
- Market regime classification
- Strategy parameter tuning
- Performance analysis
- Anomaly detection

**Integration Points:**
```python
# Example: News sentiment analysis
from openclaw import Agent

agent = Agent("trading_analyst")

def analyze_news(headline):
    prompt = f"""
    Analyze this crypto news for trading impact:
    "{headline}"
    
    Return JSON:
    {{
        "sentiment": "BULLISH/BEARISH/NEUTRAL",
        "confidence": 0-100,
        "impact": "HIGH/MEDIUM/LOW",
        "reason": "..."
    }}
    """
    
    response = agent.query(prompt)
    return response
```

---

## Data Flow (End-to-End)

### 1. Market Data Ingestion
```
Binance WebSocket → Data Pipeline → TimescaleDB
(Real-time)         (Validation)    (Storage)
```

### 2. Signal Generation
```
TimescaleDB → Strategy Engine → Signal
(Historical)   (Analysis)       (BUY/SELL)
```

### 3. Risk Validation
```
Signal → Risk Manager → Approved Signal
         (Checks)       (or Rejected)
```

### 4. Order Execution
```
Approved Signal → Execution Engine → Binance API → Order Filled
                  (Rust)             (Exchange)     (Position Open)
```

### 5. Position Monitoring
```
Open Position → Price Updates → Stop Loss Check → Exit Signal
                (Real-time)     (Risk Manager)    (Close Position)
```

---

## Communication Between Components

### Message Queue (Redis)

**Purpose:** Decouple components, enable async processing

**Channels:**
```
market_data     → Raw price/volume updates
signals         → Trading signals from strategies
orders          → Order execution requests
positions       → Position updates
alerts          → Risk alerts, errors
```

**Example:**
```python
# Strategy Engine publishes signal
redis.publish('signals', json.dumps({
    "strategy": "mean_reversion",
    "action": "BUY",
    "asset": "BTCUSDT",
    ...
}))

# Risk Manager subscribes to signals
def on_signal(message):
    signal = json.loads(message)
    if validate_risk(signal):
        redis.publish('orders', json.dumps(signal))
```

---

## Deployment Architecture

### Development (Local)
```
┌─────────────────────────────────────┐
│         Local Machine (WSL2)        │
├─────────────────────────────────────┤
│  Data Pipeline (Python)             │
│  Strategy Engine (Python)           │
│  Risk Manager (Python)              │
│  Execution Engine (Rust)            │
│  TimescaleDB (Docker)               │
│  Redis (Docker)                     │
└─────────────────────────────────────┘
         │
         ▼
   Binance Testnet
```

### Production (AWS)
```
┌─────────────────────────────────────┐
│    AWS EC2 (Tokyo Region)           │
│    (Near Binance servers)           │
├─────────────────────────────────────┤
│  Data Pipeline (systemd service)    │
│  Strategy Engine (systemd service)  │
│  Risk Manager (systemd service)     │
│  Execution Engine (systemd service) │
│  TimescaleDB (RDS)                  │
│  Redis (ElastiCache)                │
└─────────────────────────────────────┘
         │
         ▼
   Binance Production
```

---

## Monitoring & Observability

### Metrics (Prometheus)
- Order latency (p50, p95, p99)
- API error rate
- Position count
- Portfolio value
- Daily P&L
- Strategy win rates

### Logs (Structured JSON)
```json
{
  "timestamp": "2026-04-27T02:00:00Z",
  "level": "INFO",
  "component": "execution_engine",
  "event": "order_filled",
  "order_id": "12345",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "price": 60000,
  "quantity": 0.01,
  "latency_ms": 45
}
```

### Alerts (Discord)
- Position opened/closed
- Stop loss hit
- Daily loss limit reached
- Circuit breaker triggered
- API errors
- System health issues

---

## Security

### API Keys
- Stored in environment variables (never in code)
- Read-only keys for data access
- Trade-only keys (no withdrawal permissions)
- Separate keys for testnet and production

### Network
- Binance API over HTTPS only
- WebSocket over WSS (encrypted)
- Database access restricted to localhost
- No public-facing endpoints

### Code
- Input validation on all external data
- Rate limiting on API calls
- Error handling (no crashes)
- Audit logs for all trades

---

## Scalability

### Current (Phase 1)
- 2 assets (BTC, ETH)
- 3 strategies
- 1-minute candles
- ~100 trades/day

### Future (Phase 2+)
- 10+ assets
- 5+ strategies
- Tick data (sub-second)
- 1000+ trades/day

**Bottlenecks to watch:**
- TimescaleDB query performance
- Redis message throughput
- Binance API rate limits (1200 req/min)

---

## Disaster Recovery

### Backups
- TimescaleDB: Daily snapshots to S3
- Config files: Git repository
- Logs: Retained for 30 days

### Failover
- If Execution Engine crashes → Auto-restart (systemd)
- If Binance API down → Pause trading, alert operator
- If database down → Cache in Redis, backfill later

### Manual Override
- Create `~/Workspace/trading-bot/STOP` file → Pause all trading
- Discord command: `/stop` → Emergency shutdown
- SSH access for manual intervention

---

## Development Workflow

### 1. Local Development
```bash
# Start services
docker-compose up -d

# Run data pipeline
python src/data/websocket_client.py

# Run strategy engine
python src/strategy/portfolio_manager.py

# Run execution engine (paper trading)
cargo run --release -- --mode paper
```

### 2. Testing
```bash
# Unit tests
pytest tests/

# Backtesting
python src/backtest/run_backtest.py --strategy mean_reversion --start 2023-01-01 --end 2024-01-01

# Integration tests
python tests/integration/test_full_pipeline.py
```

### 3. Deployment
```bash
# Build Rust binary
cargo build --release

# Deploy to AWS
./scripts/deploy.sh production

# Monitor
./scripts/monitor.sh
```

---

## Tech Stack Summary

| Component | Language | Framework | Purpose |
|-----------|----------|-----------|---------|
| Data Pipeline | Python | asyncio, websockets | Real-time data ingestion |
| Strategy Engine | Python | pandas, numpy | Signal generation |
| Risk Manager | Python | - | Risk validation |
| Execution Engine | Rust | tokio, reqwest | Order execution |
| Database | SQL | TimescaleDB | Time-series storage |
| Cache | - | Redis | Message queue |
| AI Agent | Python | OpenClaw, Claude | Sentiment analysis |
| Monitoring | - | Prometheus, Grafana | Metrics & dashboards |
| Alerts | Python | Discord API | Notifications |

---

## Next Steps (Week 1)

1. **Day 1-2:** Data pipeline + TimescaleDB setup
2. **Day 3-4:** Strategy engine (mean reversion)
3. **Day 5-6:** Risk manager + execution engine skeleton
4. **Day 7:** Integration testing, paper trading deployment

---

## Notes

- Architecture is modular (easy to swap components)
- Python for rapid iteration, Rust for performance
- All components can run independently (loose coupling)
- Designed for 24/7 operation (no manual intervention)

**Remember:** Start simple, add complexity as needed. Don't over-engineer.
