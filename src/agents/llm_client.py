"""
Shared LLM client for trading agents.
Uses the Claude API via routeai.cc proxy (same as OpenClaw).
Each agent gets its own session context — they do NOT share state.
"""

import json
import os
import requests
from pathlib import Path

# Load from OpenClaw config (same key OpenClaw uses)
_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"

def _load_claude_config() -> dict:
    with open(_CONFIG_PATH) as f:
        d = json.load(f)
    # Config structure: d["models"]["providers"]["claude"]
    providers = d.get("models", {}).get("providers", {})
    if not providers:
        # Fallback: d["providers"]
        providers = d.get("providers", {})
    claude = providers.get("claude", {})
    return {
        "base_url": claude.get("baseUrl", "https://api.routeai.cc"),
        "api_key": claude.get("apiKey", ""),
    }

_cfg = _load_claude_config()

# Haiku = cheap, fast — for technical + sentiment agents
# Sonnet = better reasoning — for synthesis agent
MODEL_FAST = "claude-haiku-4-5-20251001"
MODEL_SMART = "claude-sonnet-4-6"

# OpenRouter model IDs (fallback)
OR_MODEL_FAST = "anthropic/claude-haiku-4-5"
OR_MODEL_SMART = "anthropic/claude-sonnet-4-6"


def _load_openrouter_config() -> dict:
    # Prefer credentials file (full key) over config (may be truncated)
    key_file = Path.home() / ".openclaw" / "credentials" / "openrouter-api-key.txt"
    if key_file.exists():
        api_key = key_file.read_text().strip()
    else:
        with open(_CONFIG_PATH) as f:
            d = json.load(f)
        providers = d.get("models", {}).get("providers", {})
        if not providers:
            providers = d.get("providers", {})
        api_key = providers.get("openrouter", {}).get("apiKey", "")
    return {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": api_key,
    }

_or_cfg = _load_openrouter_config()


def call_claude(system_prompt: str, user_message: str, model: str = MODEL_FAST, max_tokens: int = 512) -> str:
    """
    Single-turn Claude call via routeai.cc proxy.
    Returns the text response. Raises on HTTP error or empty response.
    """
    url = f"{_cfg['base_url']}/v1/messages"
    headers = {
        "x-api-key": _cfg["api_key"],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data["content"][0]["text"].strip()
