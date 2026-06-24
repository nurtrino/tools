"""LLM news desk: Claude searches the web for recent material news, ranks it by
importance, and returns concise bullet summaries linking the source article.
Requires ANTHROPIC_API_KEY (uses Claude's server-side web_search tool);
degrades to a clear note otherwise.
"""
from __future__ import annotations

import json
import re
from typing import Any

from app import cache
from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

_SYSTEM = (
    "You are a buy-side news analyst. Use web_search to find the most important, "
    "potentially market-moving news about the company from roughly the last 30 days "
    "(earnings, guidance, M&A, regulatory/legal, products, management, analyst moves). "
    "Rank by importance and keep only what actually matters. Be concise and concrete — "
    "no filler, no hype. Return ONLY a JSON object, no prose around it:\n"
    '{"items":[{"title":"...","source":"...","date":"YYYY-MM-DD","url":"https://...",'
    '"bullets":["short point","short point"]}]}\n'
    "Max 6 items. Each bullet under ~15 words. Use the real article URL in 'url'."
)


def _extract_json(text: str) -> dict[str, Any]:
    # Find the outermost JSON object in the model's final text.
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        # Strip code fences / stray text and retry on the largest {...} match.
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return {}
    return {}


def fetch(company: str, ticker: str) -> dict[str, Any]:
    if not ANTHROPIC_API_KEY:
        return {"available": False,
                "note": "Add ANTHROPIC_API_KEY to .env to enable AI news (uses Claude web search)."}
    try:
        import anthropic
    except ImportError:
        return {"available": False, "note": "anthropic SDK not installed."}

    cache_key = f"news:{ticker}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"Find and summarize the most important recent news for {company} (ticker {ticker})."
    try:
        resp = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2500,
            system=_SYSTEM,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        return {"available": False, "note": f"News fetch failed: {exc}"}

    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    data = _extract_json(text)
    items = data.get("items", []) if isinstance(data, dict) else []

    result = {"available": bool(items), "items": items[:6]}
    if not items:
        result["note"] = "No material news found, or the response could not be parsed."
    cache.set(cache_key, result)
    return result
