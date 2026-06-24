"""SEC EDGAR connector — CIK lookup, XBRL company facts, recent filings.

Used for: structured fundamentals (cross-check + solvency scores), insider Form 4
activity, and pulling 10-K risk-factor text for the LLM. EDGAR is free but requires
a descriptive User-Agent (SEC policy) — set SEC_USER_AGENT in your .env.
"""
from __future__ import annotations

from typing import Any, Optional

import httpx

from app import cache
from config import SEC_USER_AGENT

_HEADERS = {"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"}
_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"


def _get_json(url: str) -> Optional[Any]:
    cache_key = f"edgar:{url}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        resp = httpx.get(url, headers=_HEADERS, timeout=25.0)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None
    cache.set(cache_key, data)
    return data


def cik_for(ticker: str) -> Optional[str]:
    """Resolve a ticker to a zero-padded 10-digit CIK."""
    data = _get_json(_TICKER_MAP_URL)
    if not isinstance(data, dict):
        return None
    target = ticker.upper()
    for row in data.values():
        if row.get("ticker", "").upper() == target:
            return str(row["cik_str"]).zfill(10)
    return None


def company_facts(cik: str) -> dict[str, Any]:
    """Full XBRL company-facts payload (all reported us-gaap concepts)."""
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    data = _get_json(url)
    return data if isinstance(data, dict) else {}


def latest_annual(facts: dict[str, Any], concept: str) -> Optional[float]:
    """Most recent annual (FY) value for a us-gaap concept, e.g. 'NetIncomeLoss'."""
    try:
        units = facts["facts"]["us-gaap"][concept]["units"]
    except (KeyError, TypeError):
        return None
    # Pick the USD (or first available) unit series.
    series = units.get("USD") or next(iter(units.values()), [])
    annual = [r for r in series if r.get("form") in ("10-K", "20-F") and r.get("fp") == "FY"]
    pool = annual or series
    if not pool:
        return None
    latest = max(pool, key=lambda r: r.get("end", ""))
    val = latest.get("val")
    return float(val) if isinstance(val, (int, float)) else None


def recent_filings(cik: str, forms: tuple[str, ...] = ("10-K", "10-Q", "8-K")) -> list[dict[str, Any]]:
    """Recent filings of the given form types, newest first."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = _get_json(url)
    if not isinstance(data, dict):
        return []
    recent = data.get("filings", {}).get("recent", {})
    out: list[dict[str, Any]] = []
    form_list = recent.get("form", [])
    for i, form in enumerate(form_list):
        if form in forms:
            out.append({
                "form": form,
                "filingDate": recent.get("filingDate", [None] * len(form_list))[i],
                "primaryDocument": recent.get("primaryDocument", [None] * len(form_list))[i],
                "accessionNumber": recent.get("accessionNumber", [None] * len(form_list))[i],
            })
    return out[:20]
