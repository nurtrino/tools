"""Finnhub connector — prices, fundamentals metrics, estimates, news, peers, insiders.

All calls are cached and degrade gracefully: a missing key or a premium-gated
endpoint returns an empty dict rather than raising, so the engine can fall back to
neutral scores instead of crashing.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

import httpx

from app import cache
from config import FINNHUB_API_KEY

_BASE = "https://finnhub.io/api/v1"
_TODAY = _dt.date.today().isoformat()


def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET a Finnhub endpoint with caching. Returns {} on any failure."""
    if not FINNHUB_API_KEY:
        return {}
    cache_key = f"finnhub:{path}:{sorted(params.items())}:{_TODAY}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    params = {**params, "token": FINNHUB_API_KEY}
    try:
        resp = httpx.get(f"{_BASE}{path}", params=params, timeout=20.0)
        if resp.status_code != 200:
            return {}
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        return {}
    result = data if isinstance(data, dict) else {"_list": data}
    cache.set(cache_key, result)
    return result


def profile(symbol: str) -> dict[str, Any]:
    return _get("/stock/profile2", {"symbol": symbol})


def metrics(symbol: str) -> dict[str, Any]:
    """Basic financials: valuation ratios, margins, growth, balance-sheet health."""
    data = _get("/stock/metric", {"symbol": symbol, "metric": "all"})
    return data.get("metric", {}) if isinstance(data, dict) else {}


def quote(symbol: str) -> dict[str, Any]:
    return _get("/quote", {"symbol": symbol})


def recommendations(symbol: str) -> list[dict[str, Any]]:
    data = _get("/stock/recommendation", {"symbol": symbol})
    return data.get("_list", []) if isinstance(data, dict) else []


def price_target(symbol: str) -> dict[str, Any]:
    return _get("/stock/price-target", {"symbol": symbol})


def earnings(symbol: str) -> list[dict[str, Any]]:
    data = _get("/stock/earnings", {"symbol": symbol})
    return data.get("_list", []) if isinstance(data, dict) else []


def peers(symbol: str) -> list[str]:
    data = _get("/stock/peers", {"symbol": symbol})
    return data.get("_list", []) if isinstance(data, dict) else []


def insider_transactions(symbol: str) -> list[dict[str, Any]]:
    data = _get("/stock/insider-transactions", {"symbol": symbol})
    return data.get("data", []) if isinstance(data, dict) else []


def company_news(symbol: str, days: int = 30) -> list[dict[str, Any]]:
    today = _dt.date.today()
    frm = (today - _dt.timedelta(days=days)).isoformat()
    data = _get("/company-news", {"symbol": symbol, "from": frm, "to": today.isoformat()})
    items = data.get("_list", []) if isinstance(data, dict) else []
    return items[:25]


def candles(symbol: str, days: int = 365, resolution: str = "D") -> dict[str, Any]:
    """Daily OHLC candles. Gated on Finnhub's free tier (often 403/no_data);
    callers fall back to a chart widget when this is empty."""
    today = _dt.datetime.now()
    frm = int((today - _dt.timedelta(days=days)).timestamp())
    to = int(today.timestamp())
    data = _get("/stock/candle", {"symbol": symbol, "resolution": resolution, "from": frm, "to": to})
    if isinstance(data, dict) and data.get("s") == "ok":
        return data
    return {}


def earnings_calendar(symbol: str) -> dict[str, Any]:
    """Upcoming earnings (next reporting date). Free-tier availability varies."""
    today = _dt.date.today()
    to = (today + _dt.timedelta(days=120)).isoformat()
    data = _get("/calendar/earnings", {"symbol": symbol, "from": today.isoformat(), "to": to})
    rows = data.get("earningsCalendar", []) if isinstance(data, dict) else []
    return rows[0] if rows else {}
