"""
Sentiment Agent — sees Fear & Greed index + recent BTC news headlines ONLY.
No price data, no indicators.
Returns: sentiment (BULLISH/BEARISH/NEUTRAL), score (0.0-1.0), reasoning.
"""

import json
import requests
from .llm_client import call_claude, MODEL_FAST

SYSTEM_PROMPT = """You are a crypto market sentiment analyst.
You receive the current Fear & Greed index value and recent BTC news headlines.
Your job: assess whether current sentiment supports a BUY trade.

Rules:
- EXTREME FEAR (0-25): market panic, could mean good BUY but also falling knife — score 0.4
- FEAR (26-45): cautiously bullish for mean reversion entries — score 0.6
- NEUTRAL (46-55): no strong sentiment edge — score 0.5
- GREED (56-75): market complacent, be careful — score 0.45
- EXTREME GREED (76-100): overheated, avoid new longs — score 0.2
- Adjust based on headlines — negative breaking news lowers score significantly
- Output ONLY valid JSON. No prose.

Output format:
{
  "sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
  "score": 0.0-1.0,
  "reasoning": "one sentence max"
}"""


def _fetch_fear_greed() -> dict:
    """Fetch current Fear & Greed index. Returns {value, label}."""
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
        data = r.json()["data"][0]
        return {"value": int(data["value"]), "label": data["value_classification"]}
    except Exception:
        return {"value": 50, "label": "Neutral (API error)"}


def _fetch_headlines() -> list[str]:
    """
    Fetch recent BTC news headlines.
    Uses NewsAPI if key available, otherwise returns empty list.
    """
    from pathlib import Path
    key_file = Path.home() / ".openclaw" / "credentials" / "newsapi-key.txt"
    if not key_file.exists():
        return []
    try:
        api_key = key_file.read_text().strip()
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": "bitcoin BTC crypto",
                "sortBy": "publishedAt",
                "pageSize": 5,
                "language": "en",
                "apiKey": api_key,
            },
            timeout=5,
        )
        articles = r.json().get("articles", [])
        return [a["title"] for a in articles[:5]]
    except Exception:
        return []


def run() -> dict:
    """
    Fetches sentiment data and returns agent decision.
    Returns: {sentiment, score, reasoning, agent, fg_value, fg_label}
    """
    fg = _fetch_fear_greed()
    headlines = _fetch_headlines()

    headline_text = "\n".join(f"- {h}" for h in headlines) if headlines else "No headlines available."

    msg = f"""Fear & Greed Index: {fg['value']}/100 — {fg['label']}

Recent BTC headlines:
{headline_text}

Is sentiment currently BULLISH, BEARISH, or NEUTRAL for a BTC long entry? Output JSON only."""

    try:
        raw = call_claude(SYSTEM_PROMPT, msg, model=MODEL_FAST, max_tokens=200)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        return {
            "sentiment": result.get("sentiment", "NEUTRAL"),
            "score": float(result.get("score", 0.5)),
            "reasoning": result.get("reasoning", ""),
            "agent": "sentiment",
            "fg_value": fg["value"],
            "fg_label": fg["label"],
        }
    except Exception as e:
        return {
            "sentiment": "NEUTRAL",
            "score": 0.5,
            "reasoning": f"Sentiment agent error: {e}",
            "agent": "sentiment",
            "fg_value": fg["value"],
            "fg_label": fg["label"],
        }
