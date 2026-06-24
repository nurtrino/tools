"""Comprehensive valuation & quality metrics for the display grid.

Combines Finnhub's precomputed ratios with figures derived from EDGAR (so we can
show EV/EBITDA and EV/Sales, which Finnhub's free tier doesn't expose directly).
"""
from __future__ import annotations

from typing import Any, Optional


def _f(d: dict[str, Any], key: str) -> Optional[float]:
    v = d.get(key)
    return float(v) if isinstance(v, (int, float)) else None


def build(metrics: dict[str, Any], statements: dict[str, Any], profile: dict[str, Any],
          price: Optional[float]) -> list[dict[str, Any]]:
    """Ordered list of {label, value, fmt, group} for the metrics grid."""
    derived = statements.get("derived", {}) if statements else {}
    latest = statements.get("latest", {}) if statements else {}

    # Market cap (Finnhub profile reports it in millions).
    mcap_m = _f(profile, "marketCapitalization")
    market_cap = mcap_m * 1_000_000 if mcap_m is not None else None

    # Enterprise value = market cap + total debt - cash.
    ev = None
    if market_cap is not None and derived.get("total_debt") is not None and latest.get("cash") is not None:
        ev = market_cap + derived["total_debt"] - latest["cash"]

    ebitda = derived.get("ebitda")
    revenue = latest.get("revenue")
    ev_ebitda = (ev / ebitda) if (ev and ebitda and ebitda != 0) else None
    ev_sales = (ev / revenue) if (ev and revenue and revenue != 0) else None

    fcf = derived.get("free_cash_flow")
    fcf_yield = (fcf / market_cap * 100.0) if (fcf and market_cap) else None

    rows = [
        # group, label, value, format
        ("Valuation", "P/E (TTM)", _f(metrics, "peTTM") or _f(metrics, "peNormalizedAnnual"), "x"),
        ("Valuation", "P/S (TTM)", _f(metrics, "psTTM"), "x"),
        ("Valuation", "P/B", _f(metrics, "pbAnnual") or _f(metrics, "pbQuarterly"), "x"),
        ("Valuation", "P/FCF", _f(metrics, "pfcfShareTTM"), "x"),
        ("Valuation", "EV/EBITDA", ev_ebitda, "x"),
        ("Valuation", "EV/Sales", ev_sales, "x"),
        ("Valuation", "PEG", _f(metrics, "pegTTM") or _f(metrics, "pegRatio"), "x"),
        ("Valuation", "FCF yield", fcf_yield, "%"),
        ("Valuation", "Dividend yield", _f(metrics, "dividendYieldIndicatedAnnual") or _f(metrics, "currentDividendYieldTTM"), "%"),
        ("Profitability", "Gross margin", _f(metrics, "grossMarginTTM"), "%"),
        ("Profitability", "Operating margin", _f(metrics, "operatingMarginTTM"), "%"),
        ("Profitability", "Net margin", _f(metrics, "netProfitMarginTTM"), "%"),
        ("Profitability", "ROE", _f(metrics, "roeTTM"), "%"),
        ("Profitability", "ROIC / ROA", _f(metrics, "roiTTM") or _f(metrics, "roaTTM"), "%"),
        ("Health", "Debt / equity", _f(metrics, "totalDebt/totalEquityAnnual") or _f(metrics, "longTermDebt/equityAnnual"), "x"),
        ("Health", "Current ratio", _f(metrics, "currentRatioAnnual") or _f(metrics, "currentRatioQuarterly"), "x"),
        ("Health", "Interest coverage", _f(metrics, "netInterestCoverageAnnual") or _f(metrics, "netInterestCoverageTTM"), "x"),
        ("Market", "Market cap", market_cap, "money"),
        ("Market", "Enterprise value", ev, "money"),
        ("Market", "Beta", _f(metrics, "beta"), "x"),
        ("Market", "52-week high", _f(metrics, "52WeekHigh"), "price"),
        ("Market", "52-week low", _f(metrics, "52WeekLow"), "price"),
    ]
    return [{"group": g, "label": l, "value": v, "fmt": f} for (g, l, v, f) in rows]
