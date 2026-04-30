# Multi-Agent Architecture Upgrade

**Source:** GreymatterAI (Claude Code AI Hedge Fund) + OpenClaw $10k Trading Bot (Nate Herk / Salmon)
**Status:** Planned — upgrade from current single-agent design

---

## The Core Problem: Symmetric Data Feeds

Most AI trading agents fail because **all agents see the same data** — you just get N flavors of the same answer.

```
❌ Current single-agent approach:
   [Price + Indicators + News + Macro] → One Agent → Decision

❌ Naive multi-agent (same failure):
   [Same Data] → Agent 1 (Buffett persona)  → Vote
   [Same Data] → Agent 2 (Dalio persona)   → Vote
   [Same Data] → Agent 3 (Ackman persona)  → Vote
   = 3 agents with identical information, just different prompts
```

## The Fix: Asymmetric Data Feeds

Each agent receives **only** the data relevant to its specialty. This forces genuine disagreement and diverse signals.

```
✅ Asymmetric architecture:
   [Price bars only]          → Technical Agent   → Technical score
   [Economic data only]       → Macro Agent       → Macro score
   [News/social only]         → Sentiment Agent   → Sentiment score
   [Fundamentals only]        → Value Agent       → Value score
   [All composite scores]     → Synthesis Agent   → Final decision
```

---

## Agent Roster (Planned)

### 1. Technical Agent
**Data feed:** OHLCV price bars (5-min), volume, no other inputs
**Job:** Pure price-action analysis — trends, breakouts, mean reversion signals
**Persona:** Modeled on systematic trader (Simons / Renaissance Technologies style)
**Output:** `{ signal: BUY|SELL|HOLD, confidence: 0-1, reasoning: "..." }`

### 2. Macro Agent
**Data feed:** Economic calendar, Fed announcements, DXY, bond yields, CPI/PCE
**Job:** Macro regime detection — risk-on vs risk-off, inflation signals
**Persona:** Modeled on macro trader (Dalio / Druckenmiller style)
**Output:** `{ regime: RISK_ON|RISK_OFF|NEUTRAL, strength: 0-1, reasoning: "..." }`

### 3. Sentiment Agent
**Data feed:** News headlines (15-min intervals), crypto social (optional), Fear & Greed index
**Job:** Short-term sentiment direction, news-driven volatility prediction
**Persona:** Modeled on news trader (SAC Capital style)
**Output:** `{ sentiment: BULLISH|BEARISH|NEUTRAL, confidence: 0-1, news_events: [] }`

### 4. Synthesis Agent (The Decider)
**Data feed:** Outputs from all 3 specialist agents + current portfolio state
**Job:** Combine signals, apply quality gate, make final trade decision
**Rules:**
- Composite score = weighted average of agent outputs
- **Quality gate: composite score must exceed 0.35 to proceed**
- Positions below gate score are NEVER executed
- Must specify position size, entry, SL, TP

---

## Quality Gate

Inspired by the GreymatterAI implementation — filters out marginal setups before they reach execution.

```python
QUALITY_GATE_THRESHOLD = 0.35  # composite score 0-1

def composite_score(tech, macro, sentiment) -> float:
    # Weights reflect strategy allocations
    return (
        tech.confidence * 0.45 +
        macro.strength * 0.30 +
        sentiment.confidence * 0.25
    )

def should_trade(score: float) -> bool:
    return score >= QUALITY_GATE_THRESHOLD
```

Only setups where ALL three agents agree (weighted) at ≥35% confidence get executed.

---

## Data Ingestion Schedule

| Data Type | Source | Frequency |
|---|---|---|
| Price bars (OHLCV) | Kraken WebSocket | Every 5 min |
| Economic calendar | FRED / ForexFactory | Daily at 6 AM ET |
| News headlines | NewsAPI / Kraken news feed | Every 15 min |
| Fear & Greed | Alternative.me API | Hourly |
| Fundamentals (crypto) | CoinGecko | Daily |

---

## OpenClaw Multi-Agent Pattern (from $10k experiment)

The Nate Herk / Salmon OpenClaw experiment validated this architecture works:

**Salmon's bot:**
- Trained on JP Morgan methodology + hedge fund signals
- Cron job every 30 min during market hours
- Rebalances based on: signals + news + portfolio state

**Nate's bot:**
- Spawned "team of wealth adviser sub-agents" with minimal prompting
- Strategy mix: 60-70% momentum swings, 15-25% options, 10%+ cash reserve
- Hard limits: max 20% per stock, max $1k per options trade

**Key takeaway:** The multi-agent team approach with role specialization outperformed single-agent approaches. Our implementation will follow the asymmetric-data pattern from GreymatterAI + the position-sizing discipline from Nate's bot.

---

## Implementation Plan

### Phase 1: Extract current agent logic into modules
- Move mean-reversion logic → `src/agents/technical_agent.py`
- Move ORB logic → `src/agents/orb_agent.py`
- Add new `src/agents/macro_agent.py`
- Add new `src/agents/sentiment_agent.py`
- Add `src/agents/synthesis_agent.py`

### Phase 2: Add asymmetric data feeds
- Technical: receives only OHLCV from Kraken WS
- Macro: add FRED economic data fetcher
- Sentiment: add NewsAPI integration

### Phase 3: Quality gate + synthesis
- Implement composite scoring
- Add threshold enforcement
- Add decision logging per agent (transparency)

### Phase 4: Dashboard upgrades
- Per-agent confidence panel
- Show which agents agreed/disagreed on last trade
- Quality gate hit rate visualization

---

## Dashboard Upgrade: Agent Decision Panel

```
┌─────────────────────────────────────────────────────────┐
│  AGENT PANEL                          [Last: 15:34:22]  │
├──────────────┬──────────────┬──────────────┬────────────┤
│  TECHNICAL   │    MACRO     │  SENTIMENT   │ COMPOSITE  │
│  BUY 0.72 ✅ │  NEUTRAL 0.4 │  BULLISH 0.6 │   0.62 ✅  │
│  ORB break   │  Risk-on     │  Positive    │  EXECUTE   │
│  confirmed   │  regime      │  news flow   │            │
└──────────────┴──────────────┴──────────────┴────────────┘
```

---

## Notes

- Phase 1 can start immediately (refactoring only)
- Macro data requires FRED API key (free)
- Sentiment requires NewsAPI key (free tier: 100 req/day)
- Quality gate threshold (0.35) is the default; tune via backtest
- This upgrade does NOT change the ORB or mean-reversion strategies — it adds a layer above them

**Reference implementations:**
- GreymatterAI hedge fund: Python + FastAPI + Celery + TimescaleDB + React
- Nate Herk OpenClaw bot: OpenClaw cron + multi-agent sessions
