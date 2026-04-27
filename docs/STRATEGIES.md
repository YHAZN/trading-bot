# Trading Strategies

**Last Updated:** April 27, 2026

All strategies implemented in this bot, with mathematical formulas and logic.

---

## Strategy 1: Mean Reversion with Z-Score

**Type:** Range-bound markets
**Timeframe:** 5-15 minutes
**Assets:** BTC/ETH (high liquidity)

### Logic

Markets oscillate around a mean. When price deviates significantly, it tends to revert.

### Entry Conditions

**Long (Buy):**
```
Z-Score < -2 AND
RSI < 30 AND
Volume > 1.5x average AND
ADX < 25 (ranging market)
```

**Short (Sell - Futures only):**
```
Z-Score > 2 AND
RSI > 70 AND
Volume > 1.5x average AND
ADX < 25 (ranging market)
```

### Exit Conditions

**Take Profit:**
```
Z-Score crosses 0 (returned to mean)
```

**Stop Loss:**
```
Price moves 2 * ATR against position
```

### Formulas

**Z-Score:**
```
Z = (Current Price - Moving Average) / Standard Deviation

Where:
- Moving Average = 20-period SMA
- Standard Deviation = 20-period StdDev
```

**RSI (Relative Strength Index):**
```
RSI = 100 - (100 / (1 + RS))
RS = Average Gain / Average Loss (14 periods)
```

**ATR (Average True Range):**
```
ATR = Moving Average of True Range (14 periods)
True Range = max(High - Low, |High - Close_prev|, |Low - Close_prev|)
```

**ADX (Average Directional Index):**
```
ADX = Moving Average of DX (14 periods)
DX = 100 * |+DI - -DI| / (+DI + -DI)
```

### Position Sizing

```python
# Kelly Criterion (capped at 2%)
win_rate = 0.55  # Historical win rate
avg_win = 0.025  # 2.5% average win
avg_loss = 0.015  # 1.5% average loss

kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
position_size = min(kelly, 0.02)  # Cap at 2%

# Adjust for volatility
current_atr = calculate_atr()
avg_atr = historical_avg_atr()
volatility_multiplier = avg_atr / current_atr

final_position_size = position_size * volatility_multiplier
```

### Risk Management

- **Max position size:** 2% of portfolio
- **Stop loss:** 2 * ATR from entry
- **Max open positions:** 3
- **Daily loss limit:** 3% of portfolio

### Backtesting Results (Expected)

- **Win rate:** 55-60%
- **Profit factor:** 1.5-2.0
- **Sharpe ratio:** 1.2-1.8
- **Max drawdown:** 10-15%

---

## Strategy 2: Momentum Breakout

**Type:** Trending markets
**Timeframe:** 15-60 minutes
**Assets:** BTC/ETH

### Logic

Strong trends continue. Enter when price breaks resistance with volume confirmation.

### Entry Conditions

**Long (Buy):**
```
Price > Supertrend AND
MACD crosses above signal line AND
Volume > 2x average AND
ADX > 25 (trending market) AND
Price breaks 20-period high
```

**Short (Sell - Futures only):**
```
Price < Supertrend AND
MACD crosses below signal line AND
Volume > 2x average AND
ADX > 25 (trending market) AND
Price breaks 20-period low
```

### Exit Conditions

**Take Profit:**
```
Price crosses below Supertrend (long) OR
Price crosses above Supertrend (short)
```

**Stop Loss:**
```
Supertrend line (dynamic trailing stop)
```

### Formulas

**Supertrend:**
```
Basic Upper Band = (High + Low) / 2 + (Multiplier * ATR)
Basic Lower Band = (High + Low) / 2 - (Multiplier * ATR)

Where:
- Multiplier = 3 (adjustable)
- ATR = 10-period ATR
```

**MACD (Moving Average Convergence Divergence):**
```
MACD Line = 12-period EMA - 26-period EMA
Signal Line = 9-period EMA of MACD Line
Histogram = MACD Line - Signal Line
```

### Position Sizing

```python
# Trend-adjusted Kelly
win_rate = 0.50  # Momentum has lower win rate
avg_win = 0.04   # But bigger wins (4%)
avg_loss = 0.02  # 2% average loss

kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
position_size = min(kelly, 0.02)

# Increase size in strong trends
adx = calculate_adx()
if adx > 40:  # Very strong trend
    position_size *= 1.2
```

### Risk Management

- **Max position size:** 2% (2.4% in strong trends)
- **Stop loss:** Supertrend line
- **Max open positions:** 2 (momentum is riskier)
- **Daily loss limit:** 3% of portfolio

### Backtesting Results (Expected)

- **Win rate:** 45-50%
- **Profit factor:** 2.0-3.0
- **Sharpe ratio:** 1.5-2.2
- **Max drawdown:** 15-20%

---

## Strategy 3: News Sentiment + Technical

**Type:** Event-driven
**Timeframe:** 1-5 minutes (fast reaction)
**Assets:** BTC/ETH

### Logic

Major news moves markets. Combine sentiment analysis with technical confirmation.

### Entry Conditions

**Long (Buy):**
```
News sentiment = BULLISH (Claude NLP) AND
Price > 5-minute EMA AND
Volume spike > 3x average AND
RSI < 70 (not overbought)
```

**Short (Sell - Futures only):**
```
News sentiment = BEARISH (Claude NLP) AND
Price < 5-minute EMA AND
Volume spike > 3x average AND
RSI > 30 (not oversold)
```

### Exit Conditions

**Take Profit:**
```
3% gain OR
Sentiment changes OR
30 minutes elapsed (news impact fades)
```

**Stop Loss:**
```
1.5% loss (tight stop for news trades)
```

### News Sources

1. **Tavily API** - Real-time news aggregation
2. **Binance announcements** - Exchange-specific news
3. **Twitter/X** - Crypto influencers (optional)

### Sentiment Analysis

```python
# Claude prompt for sentiment
prompt = f"""
Analyze this crypto news headline for trading impact:
"{headline}"

Classify as:
- BULLISH (likely price increase)
- BEARISH (likely price decrease)
- NEUTRAL (no clear direction)

Consider:
- Regulatory news (SEC, CFTC)
- Adoption news (institutions, companies)
- Technical news (upgrades, hacks)
- Macro news (Fed, inflation)

Return JSON: {{"sentiment": "BULLISH/BEARISH/NEUTRAL", "confidence": 0-100, "reason": "..."}}
"""
```

### Position Sizing

```python
# Confidence-based sizing
sentiment_confidence = 0.85  # From Claude analysis
base_size = 0.015  # 1.5% base

position_size = base_size * sentiment_confidence
# 85% confidence = 1.275% position
```

### Risk Management

- **Max position size:** 1.5% (news is unpredictable)
- **Stop loss:** 1.5% (tight)
- **Max open positions:** 1 (one news trade at a time)
- **Daily loss limit:** 2% (news trades are risky)

### Backtesting Results (Expected)

- **Win rate:** 50-55%
- **Profit factor:** 1.8-2.5
- **Sharpe ratio:** 1.0-1.5
- **Max drawdown:** 8-12%

---

## Meta-Strategy: Regime Detection

**Purpose:** Switch between strategies based on market conditions

### Market Regimes

**1. Ranging (Low Volatility)**
```
ADX < 25 AND
ATR < 20-day average
→ Use Mean Reversion
```

**2. Trending (High Momentum)**
```
ADX > 25 AND
Price consistently above/below moving averages
→ Use Momentum Breakout
```

**3. Volatile (High Uncertainty)**
```
ATR > 1.5x 20-day average OR
VIX equivalent > 30
→ Reduce position sizes by 50% OR pause trading
```

**4. News-Driven (Event Impact)**
```
Major news detected AND
Volume spike > 3x average
→ Use News Sentiment strategy
```

### Implementation

```python
def select_strategy(market_data):
    adx = calculate_adx(market_data)
    atr = calculate_atr(market_data)
    avg_atr = historical_avg_atr(market_data, periods=20)
    news_detected = check_news_feed()
    
    # Check for extreme volatility first
    if atr > 1.5 * avg_atr:
        return "PAUSE"  # Too volatile
    
    # Check for news events
    if news_detected and news_detected['confidence'] > 0.7:
        return "NEWS_SENTIMENT"
    
    # Check for trending vs ranging
    if adx > 25:
        return "MOMENTUM"
    else:
        return "MEAN_REVERSION"
```

---

## Strategy Performance Tracking

### Metrics to Monitor

**Per Strategy:**
- Win rate
- Profit factor
- Average win/loss
- Max drawdown
- Sharpe ratio
- Number of trades

**Overall Portfolio:**
- Total return
- Risk-adjusted return (Sharpe)
- Max drawdown
- Calmar ratio (return / max drawdown)
- Correlation between strategies

### When to Disable a Strategy

```
IF (
    Win rate < 45% for 30+ trades OR
    Profit factor < 1.2 for 30+ trades OR
    Max drawdown > 25% OR
    Sharpe ratio < 0.5 for 60+ days
) THEN
    Disable strategy
    Alert operator
    Review and retune
```

---

## Future Strategies (Phase 2+)

### 1. Statistical Arbitrage (Pairs Trading)
- Trade BTC/ETH spread
- Market-neutral
- Lower risk

### 2. Order Book Imbalance
- Analyze bid/ask depth
- Predict short-term moves
- Requires low latency

### 3. Funding Rate Arbitrage (Futures)
- Exploit funding rate differences
- Long spot, short futures (or vice versa)
- Market-neutral income

### 4. Volatility Trading
- Trade based on implied vs realized volatility
- Options-like strategies using perpetuals
- Advanced risk management

---

## Strategy Optimization

### Walk-Forward Analysis

```
Train Period: 2022-01-01 to 2023-12-31
Test Period: 2024-01-01 to 2024-03-31

Repeat:
- Train on 12 months
- Test on 3 months
- Roll forward 3 months
```

### Parameter Optimization

**Don't over-optimize:**
- Test parameter ranges (e.g., RSI 25-35 instead of exact 30)
- Use Monte Carlo simulation (randomize trade order)
- Require 100+ trades for statistical significance

**Parameters to tune:**
- Moving average periods
- RSI thresholds
- ATR multipliers
- Position size limits

---

## Risk-Adjusted Strategy Selection

### Sharpe Ratio Comparison

```
Strategy A: 20% return, 15% volatility → Sharpe = 1.33
Strategy B: 15% return, 8% volatility → Sharpe = 1.88

Choose Strategy B (better risk-adjusted return)
```

### Portfolio Allocation

```python
# Allocate capital based on Sharpe ratios
strategies = {
    "mean_reversion": {"sharpe": 1.5, "allocation": 0},
    "momentum": {"sharpe": 1.8, "allocation": 0},
    "news_sentiment": {"sharpe": 1.2, "allocation": 0}
}

total_sharpe = sum(s["sharpe"] for s in strategies.values())

for name, data in strategies.items():
    data["allocation"] = data["sharpe"] / total_sharpe

# Result:
# Mean Reversion: 33%
# Momentum: 40%
# News Sentiment: 27%
```

---

## Notes

- All strategies are documented here BEFORE implementation
- Update this file when strategies are modified
- Track performance in `data/backtest/` directory
- Review strategies monthly, disable underperformers

**Remember:** No strategy works forever. Markets change. Adapt or die.
