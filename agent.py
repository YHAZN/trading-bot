#!/usr/bin/env python3
import sys; sys.stdout = sys.stderr = open(sys.stdout.fileno(), "w", buffering=1)
"""
Trading agent — BTC mean reversion (24/7) + ORB breakout (NYSE hours)
Fixes: real ATR from OHLC highs/lows, removed broken vol filter, ORB strategy
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "src" / "executor"))
from trading_router import TradingRouter
sys.path.insert(0, str(Path(__file__).parent / "src"))
from agents import technical_agent, sentiment_agent, synthesis_agent

SUPABASE_URL = "https://uakuqcxhjqlqxduiuzvd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVha3VxY3hoanFscXhkdWl1enZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzczMjY2OTQsImV4cCI6MjA5MjkwMjY5NH0.7hpzkUNNR3qwdYUPDnpFsAZpfx1Q57Shl8sTVDRJkEI"
SB_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


def sb_get(path, params=""):
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{path}{params}", headers=SB_HEADERS, timeout=3)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def sb_post(path, payload):
    try:
        r = requests.post(f"{SUPABASE_URL}/rest/v1/{path}", headers=SB_HEADERS, json=payload, timeout=3)
        return r
    except Exception:
        return None


def sb_patch(path, payload):
    try:
        r = requests.patch(f"{SUPABASE_URL}/rest/v1/{path}", headers=SB_HEADERS, json=payload, timeout=3)
        return r
    except Exception:
        return None


def sb_upsert(path, payload):
    h = {**SB_HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"}
    try:
        r = requests.post(f"{SUPABASE_URL}/rest/v1/{path}", headers=h, json=payload, timeout=3)
        return r
    except Exception:
        return None


def now_et() -> datetime:
    """Current time in US/Eastern."""
    et = timezone(timedelta(hours=-4))  # EDT; adjust to -5 for EST if needed
    return datetime.now(tz=et)


def is_orb_session() -> bool:
    """True during NYSE session ORB window: 9:14 AM – 11:30 AM ET, Mon-Fri."""
    dt = now_et()
    if dt.weekday() >= 5:  # weekend
        return False
    t = dt.time()
    from datetime import time as dtime
    return dtime(9, 14) <= t <= dtime(11, 30)


def is_market_hours() -> bool:
    """True during NYSE regular hours: 9:30 AM – 4:00 PM ET, Mon-Fri."""
    dt = now_et()
    if dt.weekday() >= 5:
        return False
    t = dt.time()
    from datetime import time as dtime
    return dtime(9, 30) <= t <= dtime(16, 0)


class TradingAgent:
    def __init__(self, mode="paper"):
        self.mode = mode
        self.router = TradingRouter()
        self.running = False

        # Candle data: list of dicts {t, o, h, l, c, v}
        self.candles: list[dict] = []

        # ORB state (resets each trading day)
        self.orb_high: float | None = None
        self.orb_low: float | None = None
        self.orb_set_date: str | None = None   # "YYYY-MM-DD"
        self.orb_trade_taken: bool = False      # one trade per day

        # Open trade tracking
        self.entry_price: float | None = None
        self.entry_strategy: str = ""
        self.open_trade_id: str | None = None

        # Run tracking
        self.run_id = None
        self.price_history: list[float] = []

        # Stats file
        self.stats_file = Path(__file__).parent / "data" / "stats.json"
        self.stats_file.parent.mkdir(exist_ok=True)

        print(f"\n{'='*60}")
        print(f"🤖 TRADING AGENT — BTC Mean Reversion + ORB")
        print(f"Mode: {mode.upper()} | Balance: ${self.router.get_balance():,.2f}")
        print(f"{'='*60}\n")

        self.params = self._load_params()
        self._restore_state()

    # ─── Supabase helpers ────────────────────────────────────────────────

    def _load_params(self) -> dict:
        defaults = {
            "z_entry": -1.8,
            "rsi_entry": 35.0,
            "atr_stop_mult": 1.5,
            "atr_target_mult": 2.0,
            "lookback": 20,
            "position_size": 0.01,
            "max_positions": 1,
        }
        data = sb_get("strategy_params?id=eq.1&select=*")
        if data:
            p = data[0]
            merged = {k: p[k] for k in defaults if k in p}
            defaults.update(merged)
            print(f"📐 Params loaded from DB: {merged}")
        return defaults

    def _restore_state(self):
        data = sb_get("bot_state?id=eq.1&select=balance,open_positions,current_price")
        if data and data[0].get("balance"):
            self.router.executor.balance = float(data[0]["balance"])
            print(f"💾 Restored balance: ${self.router.executor.balance:,.2f}")

        history_file = Path(__file__).parent / "data" / "price_history.json"
        try:
            if history_file.exists():
                with open(history_file) as f:
                    self.price_history = json.load(f)[-100:]
                print(f"💾 Restored {len(self.price_history)} price points")
        except Exception:
            pass

    def _save_price_history(self):
        try:
            with open(Path(__file__).parent / "data" / "price_history.json", "w") as f:
                json.dump(self.price_history[-200:], f)
        except Exception:
            pass

    def log(self, message, level="INFO", data=None):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {message}")
        sb_post("bot_logs", {
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def _write_trade(self, side, price, qty, pnl=None, status="OPEN", reason="", strategy="mean_rev"):
        s = side.lower()
        payload = {
            "symbol": "BTC-USD",
            "side": s,
            "price": price,
            "entry_price": price if s == "buy" else self.entry_price,
            "exit_price": price if s == "sell" else None,
            "quantity": qty,
            "pnl": pnl,
            "status": status,
            "reason": reason,
        }
        if s == "sell" and self.open_trade_id:
            # Close the open BUY row
            sb_patch(
                f"trades?id=eq.{self.open_trade_id}",
                {"status": "CLOSED", "exit_price": price, "pnl": pnl}
            )
            self.open_trade_id = None
        else:
            h = {**SB_HEADERS, "Prefer": "return=representation", "Content-Type": "application/json"}
            try:
                import requests as _req
                r = _req.post(f"{SUPABASE_URL}/rest/v1/trades", headers=h, json=payload, timeout=3)
                if r.status_code in [200, 201]:
                    rows = r.json()
                    if rows and isinstance(rows, list):
                        self.open_trade_id = rows[0].get("id")
                else:
                    print(f"⚠️ trades insert: {r.status_code} {r.text[:200]}")
            except Exception as e:
                print(f"⚠️ trades insert error: {e}")

    def _update_bot_state(self, price, indicators=None, analysis=None):
        stats = self.router.get_stats()
        payload = {
            "id": 1,
            "balance": stats.get("balance", self.router.executor.balance),
            "total_pnl": stats.get("total_pnl", 0),
            "total_trades": stats.get("total_trades", 0),
            "winning_trades": stats.get("winning_trades", 0),
            "win_rate": stats.get("win_rate", 0),
            "open_positions": stats.get("open_positions", 0),
            "current_price": price,
            "updated_at": datetime.utcnow().isoformat(),
        }
        if indicators:
            payload["current_z"] = round(indicators.get("z_score", 0), 4)
            payload["current_rsi"] = round(indicators.get("rsi", 0), 4)
            payload["current_regime"] = indicators.get("regime", "RANGING")
        if analysis:
            payload["last_signal"] = analysis.get("signal", "WAIT")
        sb_patch("bot_state?id=eq.1", payload)

    def _push_market_data(self, price, indicators=None):
        """Update market_data table with current BTC price."""
        candle = self.candles[-1] if self.candles else {}
        payload = {
            "symbol": "BTC-USD",
            "price": price,
            "change24h": 0,
            "volume": candle.get("v", 0),
            "high24h": max((c["h"] for c in self.candles[-288:]), default=price),
            "low24h": min((c["l"] for c in self.candles[-288:]), default=price),
            "updated_at": datetime.utcnow().isoformat(),
        }
        sb_upsert("market_data", payload)

    def _push_candle(self, candle: dict):
        """Write one candle row to candles table."""
        payload = {
            "time": int(candle["t"]),
            "open": candle["o"],
            "high": candle["h"],
            "low": candle["l"],
            "close": candle["c"],
            "volume": candle["v"],
            "symbol": "BTC-USD",
            "timeframe": "5m",
        }
        sb_upsert("candles", payload)

    # ─── Price + candle fetching ─────────────────────────────────────────

    def get_price(self) -> float | None:
        """Fetch BTC tick price + refresh 5-min OHLC candle history."""
        try:
            resp = requests.get(
                "https://api.kraken.com/0/public/Ticker?pair=XBTUSD", timeout=5
            )
            data = resp.json()
            if data.get("error"):
                self.log(f"⚠️ Kraken Ticker error: {data['error']}", "ERROR")
                return None
            price = float(data["result"]["XXBTZUSD"]["c"][0])

            ohlc = requests.get(
                "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=5",
                timeout=8,
            ).json()
            if not ohlc.get("error") and "result" in ohlc:
                raw = ohlc["result"]["XXBTZUSD"]
                # raw: [time, open, high, low, close, vwap, volume, count]
                new_candles = [
                    {"t": int(c[0]), "o": float(c[1]), "h": float(c[2]),
                     "l": float(c[3]), "c": float(c[4]), "v": float(c[6])}
                    for c in raw
                ]
                # Exclude current incomplete candle (last one, still forming)
                self.candles = new_candles[:-1][-288:]  # up to 24h of 5-min candles

                # Push latest completed candle to Supabase
                if self.candles:
                    self._push_candle(self.candles[-1])

            return price
        except Exception as e:
            self.log(f"⚠️ get_price error: {e}", "ERROR")
            return None

    # ─── Indicators ──────────────────────────────────────────────────────

    def _calc_indicators(self) -> dict | None:
        """Calculate indicators from completed 5-min candles."""
        n = self.params.get("lookback", 20)
        if len(self.candles) < n:
            return None

        recent = self.candles[-n:]
        closes = np.array([c["c"] for c in recent])
        highs  = np.array([c["h"] for c in recent])
        lows   = np.array([c["l"] for c in recent])

        # Z-score
        mean = np.mean(closes)
        std  = np.std(closes)
        z    = (closes[-1] - mean) / std if std > 0 else 0

        # RSI
        deltas   = np.diff(closes)
        gains    = np.where(deltas > 0, deltas, 0)
        losses   = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else (np.mean(gains) if len(gains) else 0)
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else (np.mean(losses) if len(losses) else 1e-9)
        rs  = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        # True ATR (average of true ranges)
        prev_closes = closes[:-1]
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(np.abs(highs[1:] - prev_closes), np.abs(lows[1:] - prev_closes))
        )
        atr = np.mean(tr[-14:]) if len(tr) >= 14 else np.mean(tr) if len(tr) else closes[-1] * 0.002

        # Regime: BB width
        bb_width = (2 * std) / mean if mean > 0 else 0
        regime = "TRENDING" if bb_width > 0.025 else "RANGING"

        return {
            "z_score": round(z, 4),
            "rsi": round(rsi, 2),
            "atr": round(atr, 2),
            "mean": round(mean, 2),
            "std": round(std, 2),
            "bb_width": round(bb_width, 5),
            "regime": regime,
        }

    # ─── ORB setup ───────────────────────────────────────────────────────

    def _update_orb(self):
        """
        Build the Opening Range (9:14–9:30 AM ET) from 5-min candles.
        Uses the 9:14 candle (the one that opens 1 min before the NYSE open,
        capturing the pre-open spike) through 9:30.
        """
        today = now_et().strftime("%Y-%m-%d")
        if self.orb_set_date == today:
            return  # already built today

        # Find candles that fall in 9:14–9:30 ET range today
        # Kraken timestamps are UTC; ET is UTC-4 (EDT)
        import calendar
        et_offset = timedelta(hours=4)  # EDT = UTC-4
        opening_candles = []
        for c in self.candles:
            dt_utc = datetime.utcfromtimestamp(c["t"])
            dt_et  = dt_utc - et_offset  # crude conversion (no DST edge)
            if dt_et.strftime("%Y-%m-%d") == today:
                t = dt_et.time()
                from datetime import time as dtime
                if dtime(9, 14) <= t <= dtime(9, 30):
                    opening_candles.append(c)

        if opening_candles:
            self.orb_high = max(c["h"] for c in opening_candles)
            self.orb_low  = min(c["l"] for c in opening_candles)
            self.orb_set_date = today
            self.orb_trade_taken = False
            self.log(
                f"📐 ORB set for {today}: High=${self.orb_high:,.2f} Low=${self.orb_low:,.2f} "
                f"({len(opening_candles)} candles)",
                "INFO"
            )

    # ─── Strategy logic ──────────────────────────────────────────────────

    def _analyze_orb(self, price: float) -> dict:
        """ORB breakout signal. One trade per day, market hours only."""
        if not is_orb_session():
            return {"signal": "WAIT", "strategy": "orb", "reason": "Outside ORB session"}

        self._update_orb()

        if self.orb_high is None:
            return {"signal": "WAIT", "strategy": "orb", "reason": "ORB range not set yet"}

        if self.orb_trade_taken:
            return {"signal": "WAIT", "strategy": "orb", "reason": "ORB trade already taken today"}

        stats = self.router.get_stats()
        has_position = stats.get("open_positions", 0) > 0

        # Exit logic for open ORB position
        if has_position and self.entry_strategy == "orb" and self.entry_price:
            indicators = self._calc_indicators()
            atr = indicators["atr"] if indicators else price * 0.002
            stop  = self.entry_price - 1.5 * atr
            target = self.entry_price + 2.0 * atr
            if price >= target:
                return {"signal": "SELL", "strategy": "orb",
                        "reason": f"ORB target hit: ${price:,.2f} >= ${target:,.2f}"}
            if price <= stop:
                return {"signal": "SELL", "strategy": "orb",
                        "reason": f"ORB stop hit: ${price:,.2f} <= ${stop:,.2f}"}
            return {"signal": "WAIT", "strategy": "orb",
                    "reason": f"ORB in trade: entry=${self.entry_price:,.2f} stop=${stop:,.2f} target=${target:,.2f}"}

        # Entry logic
        if not has_position:
            if price > self.orb_high:
                return {"signal": "BUY", "strategy": "orb",
                        "reason": f"ORB breakout UP: ${price:,.2f} > ${self.orb_high:,.2f}"}
            # (Short selling not implemented for paper trader — skip downside)

        return {"signal": "WAIT", "strategy": "orb",
                "reason": f"ORB waiting: price=${price:,.2f} range=[{self.orb_low:,.2f},{self.orb_high:,.2f}]"}

    def _analyze_mean_rev(self, price: float, indicators: dict) -> dict:
        """Mean reversion signal using real ATR stops/targets."""
        p = self.params
        z         = indicators["z_score"]
        rsi       = indicators["rsi"]
        atr       = indicators["atr"]
        regime    = indicators["regime"]
        z_entry   = p.get("z_entry", -1.8)
        rsi_entry = p.get("rsi_entry", 35.0)
        atr_stop  = p.get("atr_stop_mult", 1.5)
        atr_tgt   = p.get("atr_target_mult", 2.0)

        stats = self.router.get_stats()
        has_position = stats.get("open_positions", 0) > 0

        # Exit
        if has_position and self.entry_strategy == "mean_rev" and self.entry_price:
            stop   = self.entry_price - atr_stop * atr
            target = self.entry_price + atr_tgt * atr
            if price >= target:
                return {"signal": "SELL", "strategy": "mean_rev",
                        "reason": f"MR target: ${price:,.2f} >= ${target:,.2f} (+{atr_tgt}×ATR={atr:.2f})"}
            if price <= stop:
                return {"signal": "SELL", "strategy": "mean_rev",
                        "reason": f"MR stop: ${price:,.2f} <= ${stop:,.2f} (-{atr_stop}×ATR={atr:.2f})"}
            # Regime flip to trending — exit to protect capital
            if regime == "TRENDING":
                return {"signal": "SELL", "strategy": "mean_rev",
                        "reason": f"Regime flipped TRENDING — exit mean reversion trade"}

        # Entry: only in ranging regime
        if not has_position and regime == "RANGING":
            if z < z_entry and rsi < rsi_entry:
                return {"signal": "BUY", "strategy": "mean_rev",
                        "reason": f"MR entry: Z={z:.2f}, RSI={rsi:.1f}, ATR={atr:.2f}, Regime={regime}"}

        return {"signal": "WAIT", "strategy": "mean_rev",
                "reason": f"MR no setup: Z={z:.2f}, RSI={rsi:.1f}, Regime={regime}"}

    # ─── AI quality gate ─────────────────────────────────────────────────

    def _run_ai_gate(self, indicators: dict) -> dict:
        """
        Run technical + sentiment + synthesis agents.
        Returns synthesis result with composite_score and approved flag.
        Only called when a rule-based BUY signal triggers — gates the final execution.
        """
        try:
            stats = self.router.get_stats()
            has_pos = stats.get("open_positions", 0) > 0
            tech = technical_agent.run(self.candles, indicators, has_pos, self.entry_price)
            sent = sentiment_agent.run()
            result = synthesis_agent.run(tech, sent)
            self.log(
                f"🤖 AI Gate | Tech:{tech['signal']}({tech['confidence']:.2f}) "
                f"Sent:{sent['sentiment']}({sent['score']:.2f}) "
                f"Composite:{result['composite_score']:.2f} "
                f"→ {result['signal']} {'✅' if result['approved'] else '🚫'}",
                data=result,
            )
            return result
        except Exception as e:
            self.log(f"⚠️ AI gate failed, passing trade through: {e}", "ERROR")
            # Fail open — if AI gate crashes, don't block trading entirely
            return {"signal": "PASS", "composite_score": 0.0, "approved": True, "reasoning": f"Gate error: {e}"}

    def _analyze(self, price: float, indicators: dict | None) -> dict:
        """
        Strategy router:
        - NYSE hours (9:14–11:30): prefer ORB
        - All hours: mean reversion as fallback
        """
        stats = self.router.get_stats()
        has_position = stats.get("open_positions", 0) > 0

        # If we have an open ORB position, always check ORB exit first
        if has_position and self.entry_strategy == "orb":
            orb = self._analyze_orb(price)
            if orb["signal"] in ["SELL", "BUY"]:
                return orb

        # During ORB window, try ORB entry
        if is_orb_session() and not has_position:
            orb = self._analyze_orb(price)
            if orb["signal"] == "BUY":
                return orb

        # Mean reversion (requires indicators)
        if indicators:
            return self._analyze_mean_rev(price, indicators)

        return {"signal": "WAIT", "strategy": "none",
                "reason": "Collecting candle data..."}

    # ─── Remote control ──────────────────────────────────────────────────

    async def _check_remote_command(self):
        data = sb_get("bot_state?id=eq.1&select=command")
        if not data:
            return
        cmd = data[0].get("command")
        if cmd == "STOP":
            self.log("⏹️ Remote STOP received", "INFO")
            self.running = False
            sb_patch("bot_state?id=eq.1", {"command": None})

    # ─── Main loop ───────────────────────────────────────────────────────

    async def run(self):
        self.running = True
        self.params = self._load_params()
        self.log("🚀 Agent started — BTC Mean Reversion + ORB")

        while self.running:
            try:
                price = self.get_price()
                if not price:
                    await asyncio.sleep(5)
                    continue

                self.price_history.append(price)
                if len(self.price_history) > 200:
                    self.price_history = self.price_history[-200:]

                indicators = self._calc_indicators()
                analysis   = self._analyze(price, indicators)

                # Status log
                if indicators:
                    self.log(
                        f"📊 BTC ${price:,.2f} | Z:{indicators['z_score']:+.2f} "
                        f"RSI:{indicators['rsi']:.0f} ATR:{indicators['atr']:.0f} "
                        f"Regime:{indicators['regime']} | {analysis['reason']}",
                        data={"price": price, "indicators": indicators, "signal": analysis["signal"]},
                    )
                else:
                    self.log(f"📊 BTC ${price:,.2f} | Collecting candles ({len(self.candles)}/20)...",
                             data={"price": price})

                # Execute
                qty = self.params.get("position_size", 0.01)
                if analysis["signal"] == "BUY":
                    # AI quality gate — must approve before execution
                    if indicators:
                        ai = self._run_ai_gate(indicators)
                        if not ai.get("approved", False):
                            analysis["signal"] = "WAIT"
                            analysis["reason"] = f"AI gate blocked: {ai.get('reasoning', '')} (score={ai.get('composite_score', 0):.2f})"
                if analysis["signal"] == "BUY":
                    result = self.router.buy("BTC", price, qty)
                    if result["success"]:
                        self.entry_price    = price
                        self.entry_strategy = analysis.get("strategy", "mean_rev")
                        if self.entry_strategy == "orb":
                            self.orb_trade_taken = True
                        self.log(f"✅ BUY {qty} BTC @ ${price:,.2f} [{self.entry_strategy}]",
                                 "TRADE", result)
                        self._write_trade("BUY", price, qty, status="OPEN",
                                          reason=analysis["reason"], strategy=self.entry_strategy)
                    else:
                        self.log(f"❌ Buy failed: {result.get('error')}", "ERROR")

                elif analysis["signal"] == "SELL":
                    result = self.router.sell("BTC", price)
                    if result["success"]:
                        pnl = result.get("pnl", 0)
                        emoji = "🟢" if pnl > 0 else "🔴"
                        self.log(f"{emoji} SELL BTC @ ${price:,.2f} P&L:${pnl:+,.2f} [{self.entry_strategy}]",
                                 "TRADE", result)
                        self._write_trade("SELL", price, qty, pnl=pnl, status="CLOSED",
                                          reason=analysis["reason"], strategy=self.entry_strategy)
                        self.entry_price    = None
                        self.entry_strategy = ""
                    else:
                        self.log(f"❌ Sell failed: {result.get('error')}", "ERROR")

                # Push state to Supabase
                self._update_bot_state(price, indicators, analysis)
                self._push_market_data(price, indicators)
                self._save_price_history()

                await self._check_remote_command()

                # Sleep: 5s if in position, 30s otherwise
                has_pos = self.router.get_stats().get("open_positions", 0) > 0
                await asyncio.sleep(5 if has_pos else 30)

            except KeyboardInterrupt:
                self.log("⏹️ Stopped by user", "INFO")
                self.running = False
                break
            except Exception as e:
                self.log(f"⚠️ Loop error: {e}", "ERROR")
                await asyncio.sleep(5)

        stats = self.router.get_stats()
        self.log(
            f"📊 FINAL — Trades:{stats.get('total_trades',0)} "
            f"WinRate:{stats.get('win_rate',0)*100:.1f}% "
            f"P&L:${stats.get('total_pnl',0):+,.2f}",
            data=stats,
        )


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["paper", "live"], default="paper")
    args = p.parse_args()
    agent = TradingAgent(mode=args.mode)
    asyncio.run(agent.run())
