# Risk Management

**Last Updated:** April 27, 2026

The most important part of trading. Strategies make money, risk management keeps it.

---

## Core Principles

1. **Never risk more than you can afford to lose**
2. **Position sizing matters more than entry price**
3. **Stop losses are mandatory, not optional**
4. **Diversify across strategies, not just assets**
5. **When in doubt, reduce size or exit**

---

## Position Sizing

### Kelly Criterion (Base Formula)

```python
def kelly_criterion(win_rate, avg_win, avg_loss):
    """
    Calculate optimal position size using Kelly Criterion
    
    Args:
        win_rate: Historical win rate (0-1)
        avg_win: Average winning trade (as decimal, e.g., 0.025 = 2.5%)
        avg_loss: Average losing trade (as decimal, e.g., 0.015 = 1.5%)
    
    Returns:
        Optimal position size (capped at 2%)
    """
    kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    
    # Cap at 2% (full Kelly is too aggressive)
    return min(kelly, 0.02)
```

**Example:**
```
Win rate: 55%
Avg win: 2.5%
Avg loss: 1.5%

Kelly = (0.55 * 0.025 - 0.45 * 0.015) / 0.025
      = (0.01375 - 0.00675) / 0.025
      = 0.28 (28%)

Capped at 2% → Use 2% position size
```

### Volatility-Adjusted Sizing

```python
def volatility_adjusted_size(base_size, current_atr, avg_atr):
    """
    Adjust position size based on current volatility
    
    Higher volatility → smaller position
    Lower volatility → larger position
    """
    volatility_ratio = avg_atr / current_atr
    adjusted_size = base_size * volatility_ratio
    
    # Don't exceed 3% even in low volatility
    return min(adjusted_size, 0.03)
```

**Example:**
```
Base size: 2%
Current ATR: $1,500 (high volatility)
Avg ATR: $1,000

Ratio = 1000 / 1500 = 0.67
Adjusted size = 2% * 0.67 = 1.34%

Use 1.34% position size (smaller due to high volatility)
```

### Confidence-Based Sizing (News Trades)

```python
def confidence_based_size(base_size, confidence):
    """
    Adjust position size based on signal confidence
    
    Args:
        base_size: Base position size (e.g., 0.015 = 1.5%)
        confidence: Signal confidence (0-1)
    
    Returns:
        Adjusted position size
    """
    return base_size * confidence
```

**Example:**
```
Base size: 1.5%
Claude sentiment confidence: 85%

Position size = 1.5% * 0.85 = 1.275%
```

---

## Stop Losses

### ATR-Based Stop Loss

```python
def calculate_stop_loss(entry_price, atr, direction, multiplier=2):
    """
    Calculate stop loss based on ATR
    
    Args:
        entry_price: Entry price
        atr: Current ATR value
        direction: 'long' or 'short'
        multiplier: ATR multiplier (default 2)
    
    Returns:
        Stop loss price
    """
    if direction == 'long':
        return entry_price - (multiplier * atr)
    else:  # short
        return entry_price + (multiplier * atr)
```

**Example (Long BTC):**
```
Entry: $60,000
ATR: $1,000
Multiplier: 2

Stop loss = $60,000 - (2 * $1,000) = $58,000
Risk per trade = $2,000 / $60,000 = 3.33%
```

### Trailing Stop (Momentum Trades)

```python
def update_trailing_stop(current_price, highest_price, atr, direction):
    """
    Update trailing stop based on Supertrend
    
    For long positions, stop moves up as price rises
    Never moves down (lock in profits)
    """
    if direction == 'long':
        new_stop = current_price - (3 * atr)
        # Only update if new stop is higher
        return max(new_stop, previous_stop)
    else:  # short
        new_stop = current_price + (3 * atr)
        return min(new_stop, previous_stop)
```

### Time-Based Stop (News Trades)

```python
def check_time_stop(entry_time, current_time, max_duration_minutes=30):
    """
    Exit news trades after max duration
    
    News impact fades quickly, don't hold too long
    """
    elapsed = (current_time - entry_time).total_seconds() / 60
    return elapsed > max_duration_minutes
```

---

## Portfolio Risk Limits

### Maximum Concurrent Risk

```python
def calculate_portfolio_heat(positions):
    """
    Calculate total portfolio risk (heat)
    
    Portfolio heat = sum of all position risks
    Max allowed: 5%
    """
    total_heat = 0
    
    for position in positions:
        entry_price = position['entry_price']
        stop_loss = position['stop_loss']
        position_size = position['size']
        
        # Risk per position
        risk_per_unit = abs(entry_price - stop_loss) / entry_price
        position_risk = position_size * risk_per_unit
        
        total_heat += position_risk
    
    return total_heat
```

**Example:**
```
Position 1: 2% size, 3% risk = 0.06% portfolio risk
Position 2: 1.5% size, 2% risk = 0.03% portfolio risk
Position 3: 2% size, 4% risk = 0.08% portfolio risk

Total heat = 0.06% + 0.03% + 0.08% = 0.17%
Status: OK (under 5% limit)
```

### Daily Loss Limit

```python
def check_daily_loss_limit(daily_pnl, portfolio_value, limit=0.03):
    """
    Stop trading if daily loss exceeds limit
    
    Args:
        daily_pnl: Today's profit/loss
        portfolio_value: Total portfolio value
        limit: Max daily loss (default 3%)
    
    Returns:
        True if should stop trading
    """
    daily_loss_pct = abs(daily_pnl) / portfolio_value
    
    if daily_pnl < 0 and daily_loss_pct > limit:
        return True  # Stop trading
    
    return False
```

### Weekly/Monthly Drawdown Limits

```python
def check_drawdown_limits(current_value, peak_value):
    """
    Monitor drawdown from peak
    
    Weekly limit: 10%
    Monthly limit: 20%
    """
    drawdown = (peak_value - current_value) / peak_value
    
    if drawdown > 0.20:
        return "SHUTDOWN"  # Stop all trading, review strategy
    elif drawdown > 0.10:
        return "REDUCE"  # Cut position sizes by 50%
    else:
        return "OK"
```

---

## Risk Per Strategy

### Strategy-Specific Limits

```python
STRATEGY_LIMITS = {
    "mean_reversion": {
        "max_position_size": 0.02,  # 2%
        "max_positions": 3,
        "daily_loss_limit": 0.03,   # 3%
        "stop_loss_multiplier": 2   # 2x ATR
    },
    "momentum": {
        "max_position_size": 0.02,  # 2% (2.4% in strong trends)
        "max_positions": 2,
        "daily_loss_limit": 0.03,
        "stop_loss_multiplier": 3   # Wider stops for trends
    },
    "news_sentiment": {
        "max_position_size": 0.015, # 1.5%
        "max_positions": 1,
        "daily_loss_limit": 0.02,   # 2% (riskier)
        "stop_loss_multiplier": 1.5 # Tight stops
    }
}
```

### Correlation Risk

```python
def check_correlation_risk(positions):
    """
    Don't open correlated positions
    
    Example: Don't go long BTC and ETH simultaneously
    (they move together, doubles risk)
    """
    assets = [p['asset'] for p in positions]
    
    # BTC and ETH are highly correlated
    if 'BTC' in assets and 'ETH' in assets:
        # Check if both are same direction
        btc_direction = [p['direction'] for p in positions if p['asset'] == 'BTC'][0]
        eth_direction = [p['direction'] for p in positions if p['asset'] == 'ETH'][0]
        
        if btc_direction == eth_direction:
            return False  # Don't open, too correlated
    
    return True  # OK to open
```

---

## Emergency Stops

### Circuit Breakers

```python
def check_circuit_breakers(market_data):
    """
    Pause trading during extreme conditions
    
    1. Flash crash (>10% move in 5 minutes)
    2. Exchange issues (API errors, delays)
    3. Extreme volatility (ATR > 2x average)
    """
    # Flash crash detection
    price_change_5min = (market_data['close'] - market_data['close_5min_ago']) / market_data['close_5min_ago']
    if abs(price_change_5min) > 0.10:
        return "PAUSE", "Flash crash detected"
    
    # Volatility check
    if market_data['atr'] > 2 * market_data['avg_atr']:
        return "PAUSE", "Extreme volatility"
    
    # API health check
    if market_data['api_latency'] > 1000:  # >1 second
        return "PAUSE", "Exchange API issues"
    
    return "OK", None
```

### Manual Override

```python
def manual_override_check():
    """
    Check for manual stop file
    
    Create ~/Workspace/trading-bot/STOP to pause trading
    """
    stop_file = Path("~/Workspace/trading-bot/STOP").expanduser()
    
    if stop_file.exists():
        return True  # Stop trading immediately
    
    return False
```

---

## Risk Monitoring

### Real-Time Alerts (Discord)

```python
def send_risk_alert(alert_type, message):
    """
    Send Discord alerts for risk events
    
    Alert types:
    - STOP_LOSS_HIT
    - DAILY_LIMIT_REACHED
    - DRAWDOWN_WARNING
    - CIRCUIT_BREAKER
    - POSITION_OPENED
    - POSITION_CLOSED
    """
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
    
    payload = {
        "content": f"🚨 **{alert_type}**\n{message}",
        "username": "Trading Bot Risk Manager"
    }
    
    requests.post(discord_webhook, json=payload)
```

### Daily Risk Report

```python
def generate_daily_risk_report(trades, positions):
    """
    Generate end-of-day risk report
    
    Includes:
    - Total P&L
    - Win rate
    - Largest loss
    - Current portfolio heat
    - Drawdown from peak
    """
    report = f"""
    📊 **Daily Risk Report - {datetime.now().strftime('%Y-%m-%d')}**
    
    **Performance:**
    - Total P&L: ${sum(t['pnl'] for t in trades):.2f}
    - Win Rate: {len([t for t in trades if t['pnl'] > 0]) / len(trades) * 100:.1f}%
    - Largest Win: ${max(t['pnl'] for t in trades):.2f}
    - Largest Loss: ${min(t['pnl'] for t in trades):.2f}
    
    **Risk Metrics:**
    - Portfolio Heat: {calculate_portfolio_heat(positions):.2f}%
    - Open Positions: {len(positions)}
    - Drawdown: {calculate_drawdown():.2f}%
    
    **Status:** {'⚠️ WARNING' if check_daily_loss_limit() else '✅ OK'}
    """
    
    send_risk_alert("DAILY_REPORT", report)
```

---

## Risk Checklist (Before Every Trade)

```
[ ] Position size calculated using Kelly Criterion?
[ ] Stop loss set (ATR-based)?
[ ] Portfolio heat under 5%?
[ ] Daily loss limit not exceeded?
[ ] No correlated positions?
[ ] Market conditions normal (no circuit breakers)?
[ ] Strategy limits not exceeded?
[ ] Manual override not active?
```

**If ANY checkbox is unchecked, DO NOT OPEN POSITION.**

---

## Risk Parameters (Configurable)

**File:** `config/risk.json`

```json
{
  "position_sizing": {
    "max_position_size": 0.02,
    "kelly_cap": 0.02,
    "volatility_adjustment": true
  },
  "stop_losses": {
    "atr_multiplier": 2,
    "trailing_stop": true,
    "time_stop_minutes": 30
  },
  "portfolio_limits": {
    "max_portfolio_heat": 0.05,
    "max_positions": 3,
    "max_correlated_positions": 1
  },
  "loss_limits": {
    "daily_loss_limit": 0.03,
    "weekly_loss_limit": 0.10,
    "monthly_loss_limit": 0.20
  },
  "circuit_breakers": {
    "flash_crash_threshold": 0.10,
    "volatility_multiplier": 2.0,
    "api_latency_ms": 1000
  }
}
```

---

## Notes

- **Risk management is not optional**
- **When in doubt, reduce size or exit**
- **Losses are part of trading, but they must be controlled**
- **Review risk parameters monthly**
- **Never override risk limits "just this once"**

**Remember:** You can always re-enter a trade. You can't recover a blown account.
