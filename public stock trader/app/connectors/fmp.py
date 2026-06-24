"""Financial Modeling Prep connector — named analyst ratings + price targets.

FMP's `stable/` API exposes the *grading firm's name* on every rating (unlike
Finnhub's anonymized counts), which is what powers the "top players" consensus.
Every call is cached and degrades to empty on any error or paywall — FMP signals
plan-gated / legacy / bad-key endpoints with a JSON `{"Error Message": ...}` object
rather than a list — so callers fall back to Finnhub seamlessly.
"""
from __future__ import annotations

from typing import Any

import httpx

from app import cache
from config import FMP_API_KEY

_BASE = "https://financialmodelingprep.com/stable"


def _get(path: str, symbol: str) -> list[dict[str, Any]] | None:
    """GET an FMP stable endpoint. Returns the JSON list, or None on any failure
    (no key, non-200, paywall/legacy error object, or malformed body)."""
    if not FMP_API_KEY:
        return None
    cache_key = f"fmp:{path}:{symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        resp = httpx.get(
            f"{_BASE}/{path}",
            params={"symbol": symbol, "apikey": FMP_API_KEY},
            timeout=20.0,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None
    # Success is always a JSON array; an {"Error Message": ...} dict means
    # paywalled / legacy / invalid key -> treat as unavailable.
    if not isinstance(data, list):
        return None
    cache.set(cache_key, data)
    return data


def grades(symbol: str) -> list[dict[str, Any]]:
    """Recent rating actions, each with the grading firm's name."""
    return _get("grades", symbol) or []


def grades_consensus(symbol: str) -> dict[str, Any]:
    """Aggregate {strongBuy, buy, hold, sell, strongSell, consensus}."""
    data = _get("grades-consensus", symbol) or []
    return data[0] if data else {}


def grades_historical(symbol: str) -> list[dict[str, Any]]:
    """Monthly rating distribution over time (for the consensus trend)."""
    return _get("grades-historical", symbol) or []


def price_target_consensus(symbol: str) -> dict[str, Any]:
    """{targetHigh, targetLow, targetConsensus, targetMedian}."""
    data = _get("price-target-consensus", symbol) or []
    return data[0] if data else {}
