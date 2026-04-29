#!/usr/bin/env python3
"""
Strategy optimizer — downloads historical BTC prices, backtests param grid,
writes best params to Supabase strategy_params table.

No AI, no cost. Pure math backtest.
"""

import sys
import json
import time
import requests
import numpy as np
from itertools import product
from datetime import datetime, timezone

SUPABASE_URL = "https://uakuqcxhjqlqxduiuzvd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVha3VxY3hoanFscXhkdWl1enZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzczMjY2OTQsImV4cCI6MjA5MjkwMjY5NH0.7hpzkUNNR3qwdYUPDnpFsAZpfx1Q57Shl8sTVDRJkEI"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

# ── Param grid to search ────────────────────────────────────────────────────
PARAM_GRID = {
    "z_entry":      [-1.0, -1.5, -2.0, -2.5, -3.0],
    "rsi_entry":    [25, 35, 45, 55],
    "z_exit":       [0.0, 0.5, 1.0],
    "z_stop":       [-3.5, -3.0, -2.5],
    "lookback":     [20, 30, 50],
    "position_size":[0.01],
}

STARTING_BALANCE = 10_000.0
SLIPPAGE_BPS     = 5
COMMISSION_BPS   = 10

# ── 1. Fetch historical prices ───────────────────────────────────────────────
def fetch_prices(days=90):
    """Fetch BTC/USD OHLC from Kraken (1h candles, up to 720 per call)."""
    since = int(time.time()) - days * 86400
    prices = []
    url = "https://api.kraken.com/0/public/OHLC"
    # Kraken returns max 720 candles; page backward
    end = int(time.time())
    seen = set()
    while True:
        try:
            r = requests.get(url, params={"pair": "XBTUSD", "interval": 60, "since": since}, timeout=10)
            data = r.json()
            if data.get("error"):
                print(f"Kraken error: {data['error']}")
                break
            candles = data["result"]["XXBTZUSD"]
            new = [(int(c[0]), float(c[4])) for c in candles if int(c[0]) not in seen]  # (ts, close)
            if not new:
                break
            for ts, p in new:
                seen.add(ts)
                prices.append((ts, p))
            last_ts = candles[-1][0]
            if int(last_ts) >= end - 3600:
                break
            since = int(last_ts)
            time.sleep(0.3)
        except Exception as e:
            print(f"Fetch error: {e}")
            break
    prices.sort(key=lambda x: x[0])
    closes = [p for _, p in prices]
    print(f"  Fetched {len(closes)} hourly candles")
    return closes

# ── 2. Single backtest ───────────────────────────────────────────────────────
def backtest(prices, z_entry, rsi_entry, z_exit, z_stop, lookback, position_size):
    balance  = STARTING_BALANCE
    position = None  # {"entry": price, "qty": qty, "commission": fee}
    trades   = []
    equity   = []

    slip  = SLIPPAGE_BPS  / 10000
    comm  = COMMISSION_BPS / 10000

    for i in range(lookback, len(prices)):
        window = np.array(prices[i - lookback: i + 1])
        price  = window[-1]

        # Indicators
        mean  = np.mean(window)
        std   = np.std(window)
        z     = (price - mean) / std if std > 0 else 0

        deltas    = np.diff(window)
        gains     = np.where(deltas > 0, deltas, 0)
        losses    = np.where(deltas < 0, -deltas, 0)
        ag        = np.mean(gains[-14:])  if len(gains)  >= 14 else np.mean(gains)
        al        = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses)
        rs        = ag / al if al > 0 else 0
        rsi       = 100 - (100 / (1 + rs)) if rs > 0 else 0

        # Entry
        if position is None and z < z_entry and rsi < rsi_entry:
            fill    = price * (1 + slip)
            fee     = fill * position_size * comm
            cost    = fill * position_size + fee
            if cost <= balance:
                balance  -= cost
                position  = {"entry": fill, "qty": position_size, "fee": fee}

        # Exit
        elif position is not None:
            if z > z_exit or z < z_stop:
                fill     = price * (1 - slip)
                fee      = fill * position["qty"] * comm
                proceeds = fill * position["qty"] - fee
                pnl      = proceeds - position["entry"] * position["qty"] - position["fee"]
                balance += proceeds
                trades.append(pnl)
                position = None

        equity.append(balance + (price * position["qty"] if position else 0))

    # Force-close any open position at last price
    if position is not None:
        last = prices[-1]
        fill = last * (1 - slip)
        fee  = fill * position["qty"] * comm
        proceeds = fill * position["qty"] - fee
        pnl = proceeds - position["entry"] * position["qty"] - position["fee"]
        balance += proceeds
        trades.append(pnl)

    # Metrics
    n      = len(trades)
    wins   = sum(1 for t in trades if t > 0)
    wr     = wins / n if n else 0
    total_pnl = sum(trades)

    # Sharpe (annualised, hourly equity)
    if len(equity) > 1:
        rets   = np.diff(equity) / np.array(equity[:-1])
        sharpe = (np.mean(rets) / np.std(rets) * np.sqrt(8760)) if np.std(rets) > 0 else 0.0
    else:
        sharpe = 0.0

    # Max drawdown
    peak = STARTING_BALANCE
    max_dd = 0.0
    for e in equity:
        if e > peak: peak = e
        dd = (peak - e) / peak
        if dd > max_dd: max_dd = dd

    score = (wr * 0.4) + (total_pnl / STARTING_BALANCE * 0.4) + (sharpe * 0.2)

    return {
        "total_trades": n, "winning_trades": wins, "win_rate": wr,
        "total_pnl": round(total_pnl, 4), "max_drawdown": round(max_dd, 4),
        "sharpe": round(sharpe, 4), "score": round(score, 6),
        "final_balance": round(balance, 2),
    }

# ── 3. Write best params to Supabase ────────────────────────────────────────
def push_params(params):
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/strategy_params?id=eq.1",
        headers={**HEADERS, "Prefer": "return=minimal"},
        json={**params, "updated_at": datetime.now(timezone.utc).isoformat()},
        timeout=5,
    )
    return r.status_code in (200, 204)

def push_run(params, result):
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/strategy_runs",
        headers={**HEADERS, "Prefer": "return=minimal"},
        json={
            **params,
            "ended_at":       datetime.now(timezone.utc).isoformat(),
            "total_trades":   result["total_trades"],
            "winning_trades": result["winning_trades"],
            "win_rate":       result["win_rate"],
            "total_pnl":      result["total_pnl"],
            "max_drawdown":   result["max_drawdown"],
            "sharpe":         result["sharpe"],
        },
        timeout=5,
    )

# ── 4. Main ──────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  STRATEGY OPTIMIZER")
    print("=" * 60)

    print("\n[1/3] Fetching historical BTC prices (90 days, 1h candles)...")
    prices = fetch_prices(days=90)
    if len(prices) < 100:
        print("Not enough price data. Abort.")
        sys.exit(1)

    # Build grid
    keys   = list(PARAM_GRID.keys())
    combos = list(product(*PARAM_GRID.values()))
    total  = len(combos)
    print(f"\n[2/3] Backtesting {total} param combos on {len(prices)} candles...")

    best_score  = -999
    best_params = None
    best_result = None
    results     = []

    for i, vals in enumerate(combos):
        p = dict(zip(keys, vals))
        r = backtest(prices, **p)
        results.append((p, r))

        if r["score"] > best_score:
            best_score  = r["score"]
            best_params = p
            best_result = r

        if (i + 1) % 50 == 0 or (i + 1) == total:
            print(f"  {i+1}/{total} — best so far: score={best_score:.4f} "
                  f"pnl=${best_result['total_pnl']:+.2f} "
                  f"trades={best_result['total_trades']} "
                  f"wr={best_result['win_rate']*100:.0f}%")

    print(f"\n[3/3] Best params found:")
    for k, v in best_params.items():
        print(f"  {k:15s} = {v}")
    print(f"\n  Score:        {best_result['score']:.4f}")
    print(f"  Total PnL:    ${best_result['total_pnl']:+.2f}")
    print(f"  Trades:       {best_result['total_trades']}")
    print(f"  Win rate:     {best_result['win_rate']*100:.1f}%")
    print(f"  Sharpe:       {best_result['sharpe']:.3f}")
    print(f"  Max drawdown: {best_result['max_drawdown']*100:.1f}%")
    print(f"  Final balance: ${best_result['final_balance']:,.2f}")

    # Save full results locally
    import os
    os.makedirs("data", exist_ok=True)
    with open("data/optimizer_results.json", "w") as f:
        json.dump({
            "run_at": datetime.now(timezone.utc).isoformat(),
            "prices_used": len(prices),
            "combos_tested": total,
            "best_params": best_params,
            "best_result": best_result,
            "top10": sorted(results, key=lambda x: -x[1]["score"])[:10],
        }, f, indent=2, default=str)
    print("\n  Full results → data/optimizer_results.json")

    # Push to Supabase
    if push_params(best_params):
        print("  ✅ strategy_params updated in Supabase — bot picks up on next restart")
    else:
        print("  ⚠️  Supabase update failed — check manually")

    push_run(best_params, best_result)
    print("\nDone.")

if __name__ == "__main__":
    main()
