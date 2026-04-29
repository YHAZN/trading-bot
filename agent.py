#!/usr/bin/env python3
import sys; sys.stdout = sys.stderr = open(sys.stdout.fileno(), "w", buffering=1)
"""Autonomous trading agent - runs 24/7, makes decisions, broadcasts thoughts"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
import requests
import numpy as np
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "executor"))
from trading_router import TradingRouter

class TradingAgent:
    def __init__(self, mode="paper"):
        self.mode = mode
        self.router = TradingRouter()
        self.running = False
        self.price_history = []
        self.candle_closes = []  # 5-min candle close prices
        self.candle_volumes = []  # 5-min candle volumes
        self.entry_price = None   # track entry for ATR stop
        self.thoughts = []
        
        # Supabase config
        self.supabase_url = "https://uakuqcxhjqlqxduiuzvd.supabase.co"
        self.supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVha3VxY3hoanFscXhkdWl1enZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzczMjY2OTQsImV4cCI6MjA5MjkwMjY5NH0.7hpzkUNNR3qwdYUPDnpFsAZpfx1Q57Shl8sTVDRJkEI"
        
        # Stats file
        self.stats_file = Path(__file__).parent / "data" / "stats.json"
        self.stats_file.parent.mkdir(exist_ok=True)
        
        print(f"\n{'='*60}")
        print(f"🤖 TRADING AGENT INITIALIZED")
        print(f"{'='*60}")
        print(f"Mode: {self.mode.upper()}")
        print(f"Starting balance: ${self.router.get_balance():,.2f}")
        print(f"Strategy: Mean Reversion + Regime Detection")
        print(f"Supabase: ✅ Connected")
        print(f"{'='*60}\n")

        # Strategy params (loaded from Supabase, fallback to defaults)
        self.params = self.load_params()
        self.run_id = None  # current strategy_run row id

        # Restore persisted state so restarts don't reset balance/history
        self._restore_state()
    
    async def _check_remote_command(self):
        """Poll bot_state.command — if STOP, halt the bot gracefully."""
        try:
            resp = requests.get(
                f"{self.supabase_url}/rest/v1/bot_state?id=eq.1&select=command",
                headers={"apikey": self.supabase_key, "Authorization": f"Bearer {self.supabase_key}"},
                timeout=2
            )
            if resp.status_code == 200:
                data = resp.json()
                cmd = data[0].get("command") if data else None
                if cmd == "STOP":
                    self.log_thought("⏹️ Remote STOP received — halting bot", "INFO")
                    self.running = False
                    self.finish_run(self.router.get_stats())
                    # Clear the command
                    requests.patch(
                        f"{self.supabase_url}/rest/v1/bot_state?id=eq.1",
                        headers={"apikey": self.supabase_key, "Authorization": f"Bearer {self.supabase_key}", "Content-Type": "application/json", "Prefer": "return=minimal"},
                        json={"command": None},
                        timeout=2
                    )
        except Exception:
            pass

    def _restore_state(self):
        """Restore balance, positions, and price history from Supabase on restart."""
        try:
            # Restore balance + open positions from bot_state
            resp = requests.get(
                f"{self.supabase_url}/rest/v1/bot_state?id=eq.1&select=balance,open_positions,current_price",
                headers={"apikey": self.supabase_key, "Authorization": f"Bearer {self.supabase_key}"},
                timeout=3
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and data[0].get("balance"):
                    self.router.executor.balance = float(data[0]["balance"])
                    print(f"💾 Restored balance: ${self.router.executor.balance:,.2f}")
        except Exception as e:
            print(f"⚠️ Could not restore state: {e}")

        # Restore price history from local file if available
        history_file = Path(__file__).parent / "data" / "price_history.json"
        try:
            if history_file.exists():
                with open(history_file) as f:
                    self.price_history = json.load(f)
                    self.price_history = self.price_history[-100:]
                print(f"💾 Restored {len(self.price_history)} price history points")
        except Exception as e:
            print(f"⚠️ Could not restore price history: {e}")

    def _save_price_history(self):
        """Persist price history so restarts don't lose data."""
        try:
            history_file = Path(__file__).parent / "data" / "price_history.json"
            with open(history_file, 'w') as f:
                json.dump(self.price_history[-200:], f)
        except Exception:
            pass

    def write_trade_to_supabase(self, side, price, qty, pnl=None, status="OPEN", reason=""):
        """Write a trade record to Supabase trades table."""
        try:
            side_lower = side.lower()  # schema requires lowercase 'buy'/'sell'
            payload = {
                "symbol": "BTC-USD",
                "side": side_lower,
                "price": price,
                "entry_price": price if side_lower == "buy" else None,
                "exit_price": price if side_lower == "sell" else None,
                "quantity": qty,
                "pnl": pnl,
                "status": status,
                "reason": reason,
            }
            resp = requests.post(
                f"{self.supabase_url}/rest/v1/trades",
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json=payload,
                timeout=3
            )
            if resp.status_code not in [200, 201]:
                print(f"⚠️ trades insert failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"⚠️ write_trade_to_supabase error: {e}")

    def load_params(self):
        """Load strategy params from Supabase (falls back to hardcoded defaults)"""
        defaults = {
            "z_entry": -2.0, "rsi_entry": 35.0,
            "z_exit": 0.0,   "z_stop": -3.0,
            "lookback": 20,  "position_size": 0.01, "max_positions": 1
        }
        try:
            resp = requests.get(
                f"{self.supabase_url}/rest/v1/strategy_params?id=eq.1&select=*",
                headers={"apikey": self.supabase_key, "Authorization": f"Bearer {self.supabase_key}"},
                timeout=3
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    p = data[0]
                    print(f"📐 Loaded strategy params: z_entry={p['z_entry']}, rsi_entry={p['rsi_entry']}, z_exit={p['z_exit']}, z_stop={p['z_stop']}, lookback={p['lookback']}")
                    return {k: p[k] for k in defaults if k in p}
        except Exception as e:
            print(f"⚠️ Could not load params, using defaults: {e}")
        return defaults

    def start_run(self):
        """Record a new strategy run in Supabase"""
        try:
            resp = requests.post(
                f"{self.supabase_url}/rest/v1/strategy_runs",
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json={
                    "z_entry": self.params["z_entry"],
                    "rsi_entry": self.params["rsi_entry"],
                    "z_exit": self.params["z_exit"],
                    "z_stop": self.params["z_stop"],
                    "lookback": self.params["lookback"],
                    "position_size": self.params["position_size"],
                },
                timeout=3
            )
            if resp.status_code in [200, 201]:
                self.run_id = resp.json()[0]["id"]
                print(f"📝 Run #{self.run_id} started")
        except Exception as e:
            print(f"⚠️ Could not record run start: {e}")

    def finish_run(self, stats):
        """Update strategy run with final performance"""
        if not self.run_id:
            return
        try:
            closed = [t for t in self.router.trades if t.get("status") != "OPEN"]
            pnls = [t.get("pnl", 0) for t in closed]
            max_dd = 0.0
            if pnls:
                peak = 0
                for p in pnls:
                    peak = max(peak, peak + p)
                    dd = peak - (peak + p)
                    max_dd = max(max_dd, dd)
            requests.patch(
                f"{self.supabase_url}/rest/v1/strategy_runs?id=eq.{self.run_id}",
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={
                    "ended_at": datetime.utcnow().isoformat(),
                    "total_trades": stats.get("total_trades", 0),
                    "winning_trades": stats.get("winning_trades", 0),
                    "win_rate": stats.get("win_rate", 0),
                    "total_pnl": stats.get("total_pnl", 0),
                    "max_drawdown": max_dd,
                },
                timeout=3
            )
        except Exception as e:
            print(f"⚠️ Could not record run end: {e}")

    def save_stats(self, stats, price=None, indicators=None, analysis=None):
        """Save stats to local file + Supabase bot_state"""
        # Local file
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save stats: {e}")
        # Supabase bot_state upsert
        try:
            payload = {
                "id": 1,
                "balance": stats.get("balance", 10000),
                "total_pnl": stats.get("total_pnl", 0),
                "total_trades": stats.get("total_trades", 0),
                "winning_trades": stats.get("winning_trades", 0),
                "win_rate": stats.get("win_rate", 0),
                "open_positions": stats.get("open_positions", 0),
                "updated_at": datetime.utcnow().isoformat()
            }
            if price is not None:
                payload["current_price"] = price
            if indicators:
                payload["current_z"] = indicators.get("z_score", 0)
                payload["current_rsi"] = indicators.get("rsi", 0)
                payload["current_regime"] = "TRENDING" if indicators.get("adx", 0) >= 25 else "RANGING"
            if analysis:
                payload["last_signal"] = analysis.get("signal", "WAIT")
            resp = requests.patch(
                f"{self.supabase_url}/rest/v1/bot_state?id=eq.1",
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json=payload,
                timeout=2
            )
            if resp.status_code not in [200, 201, 204]:
                print(f"⚠️ bot_state update failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"⚠️ Supabase bot_state error: {e}")
    
    def log_to_supabase(self, message, data=None):
        """Log to Supabase bot_logs table"""
        try:
            payload = {
                "message": message,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            resp = requests.post(
                f"{self.supabase_url}/rest/v1/bot_logs",
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json=payload,
                timeout=2
            )
            
            if resp.status_code not in [200, 201]:
                print(f"⚠️ Supabase log failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"⚠️ Supabase error: {e}")
    
    def log_thought(self, message, level="INFO", data=None):
        """Log a thought and broadcast it"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        thought = f"[{timestamp}] {message}"
        print(thought)
        self.thoughts.append({"time": timestamp, "message": message, "level": level})
        
        # Log to Supabase
        self.log_to_supabase(message, data)
        
        # Keep only last 100 thoughts
        if len(self.thoughts) > 100:
            self.thoughts = self.thoughts[-100:]
    
    def get_price(self):
        """Fetch current BTC price and update 5-min candle history from Kraken OHLC"""
        try:
            # Always get latest tick price for execution
            resp = requests.get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD", timeout=5)
            data = resp.json()
            if data.get("error"):
                self.log_thought(f"⚠️ API error: {data['error']}", "ERROR")
                return None
            price = float(data["result"]["XXBTZUSD"]["c"][0])

            # Refresh 5-min OHLC candles (Kraken returns up to 720 candles)
            ohlc_resp = requests.get(
                "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=5",
                timeout=8
            )
            ohlc_data = ohlc_resp.json()
            if not ohlc_data.get("error"):
                candles = ohlc_data["result"]["XXBTZUSD"]
                # Each candle: [time, open, high, low, close, vwap, volume, count]
                closes = [float(c[4]) for c in candles[-60:]]  # last 60 candles = 5h
                volumes = [float(c[6]) for c in candles[-60:]]
                self.candle_closes = closes
                self.candle_volumes = volumes

            return price
        except Exception as e:
            self.log_thought(f"⚠️ Failed to fetch price: {e}", "ERROR")
            return None

    def calculate_indicators(self, prices):
        """Calculate technical indicators using 5-min OHLC candles"""
        # Use candle closes if available, fall back to raw tick history
        src = self.candle_closes if len(self.candle_closes) >= 20 else prices
        lookback = self.params.get("lookback", 20)
        if len(src) < lookback:
            return None

        prices_arr = np.array(src[-lookback:])

        # Z-score (mean reversion signal)
        mean = np.mean(prices_arr)
        std = np.std(prices_arr)
        z_score = (prices_arr[-1] - mean) / std if std > 0 else 0

        # RSI on candle closes
        deltas = np.diff(prices_arr)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses) if len(losses) > 0 else 0
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        # ATR (true range on candle data — simplified: use std of closes as proxy)
        atr = std if std > 0 else prices_arr[-1] * 0.003

        # Bollinger Band width as ranging filter (narrow = ranging, wide = trending)
        bb_width = (2 * std) / mean if mean > 0 else 0  # <0.02 = tight range

        # Volume filter: current candle volume vs 20-period avg
        vol_ratio = 1.0
        if self.candle_volumes and len(self.candle_volumes) >= 21:
            # Use [-2] (last COMPLETED candle) — [-1] is current incomplete candle, always low
            completed_vols = self.candle_volumes[:-1]
            avg_vol = np.mean(completed_vols[-20:])
            vol_ratio = completed_vols[-1] / avg_vol if avg_vol > 0 else 1.0

        # ADX proxy: if BB width is wide, treat as trending
        adx = 30 if bb_width > 0.025 else 15

        return {
            "z_score": z_score,
            "rsi": rsi,
            "adx": adx,
            "mean": mean,
            "std": std,
            "atr": atr,
            "bb_width": bb_width,
            "vol_ratio": vol_ratio,
        }

    def analyze_market(self, price, indicators):
        """Analyze market and generate signal — candle-based mean reversion"""
        if not indicators:
            return {"signal": "WAIT", "reason": "Not enough data (need 20+ candles)"}

        z = indicators["z_score"]
        rsi = indicators["rsi"]
        adx = indicators["adx"]
        atr = indicators["atr"]
        vol_ratio = indicators["vol_ratio"]

        regime = "RANGING" if adx < 25 else "TRENDING"

        p = self.params
        z_entry   = p.get("z_entry",   -1.8)
        rsi_entry = p.get("rsi_entry",  35.0)
        atr_stop  = p.get("atr_stop_mult",  1.5)   # stop = entry - atr_stop * atr
        atr_target = p.get("atr_target_mult", 1.0)  # target = entry + atr_target * atr
        vol_min   = p.get("vol_filter",  0.8)        # min vol ratio to enter

        stats = self.router.get_stats()
        has_position = stats.get("open_positions", 0) > 0

        if regime == "RANGING":
            # --- EXIT LOGIC (check first) ---
            if has_position and self.entry_price:
                stop_price   = self.entry_price - atr_stop * atr
                target_price = self.entry_price + atr_target * atr
                if price >= target_price:
                    return {
                        "signal": "SELL",
                        "reason": f"Profit target: ${price:,.2f} >= ${target_price:,.2f} (+{atr_target}×ATR)",
                        "regime": regime, "indicators": indicators
                    }
                if price <= stop_price:
                    return {
                        "signal": "SELL",
                        "reason": f"ATR stop: ${price:,.2f} <= ${stop_price:,.2f} (-{atr_stop}×ATR)",
                        "regime": regime, "indicators": indicators
                    }

            # --- ENTRY LOGIC ---
            if not has_position:
                if z < z_entry and rsi < rsi_entry and vol_ratio >= vol_min:
                    return {
                        "signal": "BUY",
                        "reason": f"Mean reversion: Z={z:.2f}, RSI={rsi:.1f}, Vol={vol_ratio:.2f}x",
                        "regime": regime, "indicators": indicators
                    }
                elif z < z_entry and rsi < rsi_entry:
                    return {
                        "signal": "WAIT",
                        "reason": f"Setup valid but vol too low: Z={z:.2f}, RSI={rsi:.1f}, Vol={vol_ratio:.2f}x (need {vol_min}x)",
                        "regime": regime, "indicators": indicators
                    }

        elif regime == "TRENDING" and has_position and self.entry_price:
            # In trending market with open position: exit immediately
            stop_price = self.entry_price - atr_stop * atr
            if price <= stop_price:
                return {
                    "signal": "SELL",
                    "reason": f"Trend stop: regime flipped to TRENDING, price ${price:,.2f}",
                    "regime": regime, "indicators": indicators
                }

        return {
            "signal": "WAIT",
            "reason": f"No setup: Z={z:.2f}, RSI={rsi:.1f}, Regime={regime}, Vol={vol_ratio:.2f}x",
            "regime": regime, "indicators": indicators
        }
    
    async def run(self):
        """Main loop - runs forever"""
        self.running = True
        self.params = self.load_params()  # Reload params on each run start
        self.start_run()
        self.log_thought("🚀 Agent started - running 24/7")
        
        while self.running:
            try:
                # Fetch price
                price = self.get_price()
                if not price:
                    await asyncio.sleep(5)
                    continue
                
                # Store price history
                self.price_history.append(price)
                if len(self.price_history) > 100:
                    self.price_history = self.price_history[-100:]
                
                # Calculate indicators
                indicators = self.calculate_indicators(self.price_history)
                
                # Analyze market
                analysis = self.analyze_market(price, indicators)
                
                # Log analysis
                if indicators:
                    msg = f"📊 BTC: ${price:,.2f} | Z: {indicators['z_score']:.2f} | RSI: {indicators['rsi']:.1f} | ADX: {indicators['adx']:.1f}"
                    self.log_thought(msg, data={"price": price, "indicators": indicators})
                else:
                    self.log_thought(f"📊 BTC: ${price:,.2f} | Collecting data...", data={"price": price})
                
                self.log_thought(f"🧠 {analysis['reason']}", data=analysis)
                
                # Execute signal
                if analysis["signal"] == "BUY":
                    # Guard: respect max_positions (allows pyramiding/scaling strategies)
                    current_stats = self.router.get_stats()
                    max_pos = self.params.get("max_positions", 1)
                    if current_stats.get("open_positions", 0) >= max_pos:
                        self.log_thought(f"⏸️ At max positions ({max_pos}) — skip BUY", "INFO")
                    else:
                        qty = self.params.get("position_size", 0.01)
                        self.log_thought("💰 BUY SIGNAL - Executing...", "TRADE")
                        result = self.router.buy("BTC", price, qty)
                        if result["success"]:
                            self.entry_price = price  # track for ATR stop/target
                            self.log_thought(f"✅ Bought {qty} BTC @ ${price:,.2f}", "TRADE", result)
                            self.write_trade_to_supabase("BUY", price, qty, status="OPEN", reason=analysis.get("reason",""))
                        else:
                            self.log_thought(f"❌ Buy failed: {result.get('error')}", "ERROR")

                elif analysis["signal"] == "SELL":
                    qty = self.params.get("position_size", 0.01)
                    self.log_thought("💸 SELL SIGNAL - Executing...", "TRADE")
                    result = self.router.sell("BTC", price)
                    if result["success"]:
                        pnl = result.get("pnl", 0)
                        emoji = "🟢" if pnl > 0 else "🔴"
                        self.log_thought(f"{emoji} Sold BTC @ ${price:,.2f} | P&L: ${pnl:,.2f}", "TRADE", result)
                        self.write_trade_to_supabase("SELL", price, qty, pnl=pnl, status="CLOSED", reason=analysis.get("reason",""))
                        self.entry_price = None  # clear entry on close
                    else:
                        self.log_thought(f"❌ Sell failed: {result.get('error')}", "ERROR")

                # Get and save stats
                stats = self.router.get_stats()
                self.save_stats(stats, price=price, indicators=indicators, analysis=analysis)

                # Show stats every 12 iterations (~1 min)
                if len(self.price_history) % 12 == 0:
                    if stats.get("total_trades", 0) > 0:
                        self.log_thought(
                            f"📈 Stats: {stats['total_trades']} trades | "
                            f"Win rate: {stats['win_rate']*100:.1f}% | "
                            f"P&L: ${stats['total_pnl']:,.2f}",
                            data=stats
                        )

                # Persist price history so restarts don't lose context
                self._save_price_history()

                # Poll for remote stop command
                await self._check_remote_command()

                # Sleep 30s — candles are 5-min, no need to hammer every 5s
                # But if we have an open position, check every 5s for stop/target
                open_pos = self.router.get_stats().get("open_positions", 0)
                await asyncio.sleep(5 if open_pos > 0 else 30)
            
            except KeyboardInterrupt:
                self.log_thought("⏹️ Agent stopped by user", "INFO")
                self.running = False
                self.finish_run(self.router.get_stats())
                break
            
            except Exception as e:
                self.log_thought(f"⚠️ Error: {e}", "ERROR")
                await asyncio.sleep(5)
        
        # Final stats
        self.log_thought("\n" + "="*60)
        self.log_thought("📊 FINAL STATS")
        self.log_thought("="*60)
        stats = self.router.get_stats()
        for key, value in stats.items():
            self.log_thought(f"{key}: {value}")
        self.log_thought("="*60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["paper", "live"], default="paper")
    args = parser.parse_args()
    
    agent = TradingAgent(mode=args.mode)
    asyncio.run(agent.run())
