"""
Synthesis Agent — receives outputs from Technical + Sentiment agents.
Applies quality gate: composite score must be >= QUALITY_GATE_THRESHOLD.
Returns: final decision {signal, composite_score, approved, reasoning}.
"""

import json
from .llm_client import call_claude, MODEL_SMART

QUALITY_GATE_THRESHOLD = 0.35

# Weights per agent (must sum to 1.0)
WEIGHT_TECHNICAL = 0.60
WEIGHT_SENTIMENT = 0.40

SYSTEM_PROMPT = """You are the synthesis agent for a BTC trading system.
You receive structured outputs from two specialized agents and must make the final trade decision.

Your job:
1. Review technical and sentiment agent outputs
2. Check if the composite score meets the quality gate (>= 0.35)
3. Make the final BUY/SELL/WAIT decision
4. Be conservative — when in doubt, WAIT

Important:
- A weak technical setup CANNOT be saved by strong sentiment
- SELL signals bypass the quality gate if we have an open position at a loss
- Output ONLY valid JSON. No prose.

Output format:
{
  "signal": "BUY" | "SELL" | "WAIT",
  "approved": true | false,
  "reasoning": "one sentence synthesis"
}"""


def run(technical: dict, sentiment: dict) -> dict:
    """
    technical: output from technical_agent.run()
    sentiment: output from sentiment_agent.run()
    Returns: {signal, composite_score, approved, reasoning, agent}
    """
    # Compute composite score
    tech_score = technical.get("confidence", 0.0)
    sent_score = sentiment.get("score", 0.5)

    # Only weight sentiment for BUY signals — for SELL/exits, trust technical
    if technical.get("signal") == "SELL":
        composite = tech_score
    else:
        composite = (WEIGHT_TECHNICAL * tech_score) + (WEIGHT_SENTIMENT * sent_score)

    composite = round(composite, 4)
    gate_passed = composite >= QUALITY_GATE_THRESHOLD

    msg = f"""Technical Agent:
Signal: {technical.get('signal')}
Confidence: {technical.get('confidence')}
Reasoning: {technical.get('reasoning')}

Sentiment Agent:
Sentiment: {sentiment.get('sentiment')}
Score: {sentiment.get('score')}
Fear & Greed: {sentiment.get('fg_value')}/100 ({sentiment.get('fg_label')})
Reasoning: {sentiment.get('reasoning')}

Composite Score: {composite} (gate threshold: {QUALITY_GATE_THRESHOLD})
Gate Passed: {gate_passed}

Make the final trading decision. Output JSON only."""

    try:
        raw = call_claude(SYSTEM_PROMPT, msg, model=MODEL_SMART, max_tokens=200)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)

        # Hard enforce quality gate — LLM can't override it
        signal = result.get("signal", "WAIT")
        if not gate_passed and signal == "BUY":
            signal = "WAIT"
            approved = False
            reasoning = f"Quality gate blocked (score={composite} < {QUALITY_GATE_THRESHOLD}): {result.get('reasoning', '')}"
        else:
            approved = gate_passed or signal == "SELL"
            reasoning = result.get("reasoning", "")

        return {
            "signal": signal,
            "composite_score": composite,
            "approved": approved,
            "reasoning": reasoning,
            "agent": "synthesis",
            "technical": technical,
            "sentiment": sentiment,
        }
    except Exception as e:
        return {
            "signal": "WAIT",
            "composite_score": composite,
            "approved": False,
            "reasoning": f"Synthesis agent error: {e}",
            "agent": "synthesis",
            "technical": technical,
            "sentiment": sentiment,
        }
