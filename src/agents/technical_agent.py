"""
Technical Agent — sees OHLCV price data ONLY.
No macro, no news, no sentiment.
Returns: signal (BUY/SELL/WAIT), confidence (0.0-1.0), reasoning.
"""

import json
from .llm_client import call_claude, MODEL_FAST

SYSTEM_PROMPT = """You are a quantitative technical analyst for BTC/USD.
You receive recent OHLCV candles and computed indicators.
Your job: assess the technical setup quality and output a structured JSON decision.

Rules:
- Only use the data provided. No assumptions about news or macro.
- Be strict. A mediocre setup gets low confidence, not medium.
- If regime is TRENDING and we are looking for mean reversion, confidence must be low (<0.3).
- A strong Z-score + RSI convergence in RANGING regime can be high confidence (>0.7).
- Output ONLY valid JSON. No prose before or after.

Output format:
{
  "signal": "BUY" | "SELL" | "WAIT",
  "confidence": 0.0-1.0,
  "reasoning": "one sentence max"
}"""


def run(candles: list[dict], indicators: dict, has_position: bool, entry_price: float | None) -> dict:
    """
    candles: last 20 OHLCV dicts {t, o, h, l, c, v}
    indicators: {z_score, rsi, atr, mean, std, bb_width, regime}
    has_position: bool
    entry_price: float or None
    Returns: {signal, confidence, reasoning}
    """
    # Build compact candle summary (last 10 only to save tokens)
    recent = candles[-10:] if len(candles) >= 10 else candles
    candle_lines = []
    for c in recent:
        candle_lines.append(
            f"o={c['o']:.0f} h={c['h']:.0f} l={c['l']:.0f} c={c['c']:.0f} v={c.get('v', 0):.2f}"
        )

    msg = f"""Indicators:
Z-score: {indicators['z_score']}
RSI: {indicators['rsi']}
ATR: {indicators['atr']}
BB Width: {indicators['bb_width']}
Regime: {indicators['regime']}
Mean: {indicators['mean']}
Std: {indicators['std']}

Position: {"OPEN @ $" + str(entry_price) if has_position and entry_price else "NONE"}

Last {len(recent)} candles (OHLCV):
{chr(10).join(candle_lines)}

Should I BUY, SELL, or WAIT? Output JSON only."""

    try:
        raw = call_claude(SYSTEM_PROMPT, msg, model=MODEL_FAST, max_tokens=200)
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        return {
            "signal": result.get("signal", "WAIT"),
            "confidence": float(result.get("confidence", 0.0)),
            "reasoning": result.get("reasoning", ""),
            "agent": "technical",
        }
    except Exception as e:
        return {"signal": "WAIT", "confidence": 0.0, "reasoning": f"Technical agent error: {e}", "agent": "technical"}
