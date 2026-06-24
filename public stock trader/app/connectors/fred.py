"""FRED connector — macro context (rates, inflation, yield curve).

Used to lightly tilt the rating for the macro regime. Free key from
https://fredaccount.stlouisfed.org/apikeys. Degrades to {} without a key.
"""
from __future__ import annotations

from typing import Optional

import httpx

from app import cache
from config import FRED_API_KEY

_BASE = "https://api.stlouisfed.org/fred/series/observations"

# A small, useful set of series.
SERIES = {
    "fed_funds": "FEDFUNDS",        # effective federal funds rate
    "cpi_yoy": "CPIAUCSL",          # CPI (level; we compute YoY)
    "yield_10y": "DGS10",           # 10-year Treasury
    "yield_2y": "DGS2",             # 2-year Treasury
    "unemployment": "UNRATE",
}


def latest(series_id: str) -> Optional[float]:
    """Most recent non-missing observation for a FRED series."""
    if not FRED_API_KEY:
        return None
    cache_key = f"fred:{series_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 13,  # enough to compute a YoY change on monthly data
    }
    try:
        resp = httpx.get(_BASE, params=params, timeout=20.0)
        if resp.status_code != 200:
            return None
        obs = resp.json().get("observations", [])
    except (httpx.HTTPError, ValueError):
        return None
    values = [float(o["value"]) for o in obs if o.get("value") not in (".", "", None)]
    if not values:
        return None
    cache.set(cache_key, values)
    return values[0]


def snapshot() -> dict[str, Optional[float]]:
    """A dict of current macro readings (or Nones if no FRED key)."""
    return {name: latest(sid) for name, sid in SERIES.items()}
