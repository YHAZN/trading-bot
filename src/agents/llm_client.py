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
MODEL_FAST = "claude-haiku-4-5"
MODEL_SMART = "claude-sonnet-4-6"

# OpenRouter model IDs (fallback)
OR_MODEL_FAST = "anthropic/claude-haiku-4-5"
OR_MODEL_SMART = "anthropic/claude-sonnet-4-6"


def _load_openrouter_config() -> dict:
    with open(_CONFIG_PATH) as f:
        d = json.load(f)
    providers = d.get("models", {}).get("providers", {})
    if not providers:
        providers = d.get("providers", {})
    or_cfg = providers.get("openrouter", {})
    return {
        "base_url": or_cfg.get("baseUrl", "https://openrouter.ai/api/v1"),
        "api_key": or_cfg.get("apiKey", ""),
    }

_or_cfg = _load_openrouter_config()


def call_claude(system_prompt: str, user_message: str, model: str = MODEL_FAST, max_tokens: int = 512) -> str:
    """
    Single-turn LLM call. Tries routeai.cc (Anthropic proxy) first, falls back to OpenRouter.
    Returns the text response. Raises on both failing.
    """
    # Try primary (routeai.cc Anthropic proxy)
    try:
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
    except Exception as primary_err:
        pass  # Fall through to OpenRouter

    # Fallback: OpenRouter (OpenAI-compatible)
    or_model = OR_MODEL_SMART if model == MODEL_SMART else OR_MODEL_FAST
    url = f"{_or_cfg['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {_or_cfg['api_key']}",
        "content-type": "application/json",
    }
    payload = {
        "model": or_model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()
