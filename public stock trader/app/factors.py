"""The eight pillars. Each function turns raw connector data into a PillarResult.

Thresholds here are broad-market heuristics (a v1 stand-in for full per-sector
percentile normalisation). They live in one place so they're easy to tune. Every
factor degrades to a neutral 50 when its data is missing, and the pillar tracks how
much real data backed the score (coverage).
"""
from __future__ import annotations

from typing import Any, Optional

from app.models import PillarResult
from app.scoring import (
    NEUTRAL,
    build_pillar,
    clamp,
    make_factor,
    score_higher_better,
    score_lower_better,
)


def _f(d: dict[str, Any], key: str) -> Optional[float]:
    v = d.get(key)
    return float(v) if isinstance(v, (int, float)) else None


# --- 1. Valuation (lower multiples = cheaper = higher score) ------------------
def valuation(metrics: dict[str, Any]) -> PillarResult:
    pe = _f(metrics, "peTTM") or _f(metrics, "peNormalizedAnnual")
    ps = _f(metrics, "psTTM")
    pfcf = _f(metrics, "pfcfShareTTM")
    pb = _f(metrics, "pbAnnual") or _f(metrics, "pbQuarterly")

    def pe_score(x: Optional[float]) -> float:
        if x is None:
            return NEUTRAL
        if x < 0:  # losing money — expensive on earnings
            return 20.0
        return score_lower_better(x, good=10.0, bad=40.0)

    factors = [
        make_factor("P/E (TTM)", pe, pe_score(pe), "Lower is cheaper; negative = unprofitable"),
        make_factor("P/S (TTM)", ps, score_lower_better(ps, 1.0, 12.0), "Price to sales"),
        make_factor("P/FCF", pfcf, score_lower_better(pfcf, 10.0, 40.0), "Price to free cash flow"),
        make_factor("P/B", pb, score_lower_better(pb, 1.0, 8.0), "Price to book"),
    ]
    return build_pillar("valuation", factors)


# --- 2. Growth ----------------------------------------------------------------
def growth(metrics: dict[str, Any]) -> PillarResult:
    rev_yoy = _f(metrics, "revenueGrowthTTMYoy")
    eps_yoy = _f(metrics, "epsGrowthTTMYoy")
    rev_5y = _f(metrics, "revenueGrowth5Y")
    factors = [
        make_factor("Revenue growth YoY %", rev_yoy, score_higher_better(rev_yoy, -5.0, 30.0), "TTM revenue vs prior year"),
        make_factor("EPS growth YoY %", eps_yoy, score_higher_better(eps_yoy, -10.0, 40.0), "TTM EPS vs prior year"),
        make_factor("Revenue 5Y CAGR %", rev_5y, score_higher_better(rev_5y, 0.0, 20.0), "5-year revenue trend"),
    ]
    return build_pillar("growth", factors)


# --- 3. Profitability / Quality ----------------------------------------------
def quality(metrics: dict[str, Any], scores: dict[str, Any] | None = None) -> PillarResult:
    gross = _f(metrics, "grossMarginTTM")
    op = _f(metrics, "operatingMarginTTM")
    net = _f(metrics, "netProfitMarginTTM")
    roe = _f(metrics, "roeTTM")
    roic = _f(metrics, "roiTTM") or _f(metrics, "roaTTM")
    factors = [
        make_factor("Gross margin %", gross, score_higher_better(gross, 10.0, 60.0), "Pricing power"),
        make_factor("Operating margin %", op, score_higher_better(op, 0.0, 30.0), "Core profitability"),
        make_factor("Net margin %", net, score_higher_better(net, 0.0, 25.0), "Bottom-line profitability"),
        make_factor("ROE %", roe, score_higher_better(roe, 0.0, 30.0), "Return on equity"),
        make_factor("ROIC / ROA %", roic, score_higher_better(roic, 0.0, 20.0), "Capital efficiency"),
    ]
    scores = scores or {}
    pio = scores.get("piotroski") or {}
    if pio.get("available"):
        factors.append(make_factor(
            "Piotroski F-Score", float(pio["score"]), pio["score"] / 9.0 * 100.0,
            f"{pio['score']}/9 — fundamental quality ({pio.get('verdict','')})"))
    eq = scores.get("earnings_quality") or {}
    if eq.get("available") and eq.get("fcf_to_ni") is not None:
        factors.append(make_factor(
            "Earnings quality (FCF/NI)", eq["fcf_to_ni"],
            score_higher_better(eq["fcf_to_ni"], 0.5, 1.2), "Cash backing reported profit"))
    return build_pillar("quality", factors)


# --- 4. Financial Health / Solvency ------------------------------------------
def health(metrics: dict[str, Any], scores: dict[str, Any] | None = None) -> PillarResult:
    current = _f(metrics, "currentRatioAnnual") or _f(metrics, "currentRatioQuarterly")
    de = _f(metrics, "totalDebt/totalEquityAnnual") or _f(metrics, "longTermDebt/equityAnnual")
    coverage = _f(metrics, "netInterestCoverageAnnual") or _f(metrics, "netInterestCoverageTTM")
    factors = [
        make_factor("Current ratio", current, score_higher_better(current, 0.8, 2.5), "Short-term liquidity"),
        make_factor("Debt / equity", de, score_lower_better(de, 0.3, 2.0), "Leverage (lower is safer)"),
        make_factor("Interest coverage", coverage, score_higher_better(coverage, 1.5, 10.0), "EBIT / interest expense"),
    ]
    altman = (scores or {}).get("altman") or {}
    if altman.get("available"):
        factors.append(make_factor(
            "Altman Z-Score", altman["z"], score_higher_better(altman["z"], 1.8, 3.0),
            f"Distress risk — {altman.get('zone','')}"))
    return build_pillar("health", factors)


# --- 5. Estimates & Revisions -------------------------------------------------
def _bull_ratio(rec: dict[str, Any]) -> Optional[float]:
    total = sum(_f(rec, k) or 0.0 for k in ("strongBuy", "buy", "hold", "sell", "strongSell"))
    if total <= 0:
        return None
    weighted = (
        (_f(rec, "strongBuy") or 0) * 1.0
        + (_f(rec, "buy") or 0) * 0.75
        + (_f(rec, "hold") or 0) * 0.5
        + (_f(rec, "sell") or 0) * 0.25
        + (_f(rec, "strongSell") or 0) * 0.0
    )
    return weighted / total * 100.0


def estimates(
    recs: list[dict[str, Any]],
    target: dict[str, Any],
    earnings_list: list[dict[str, Any]],
    current_price: Optional[float],
) -> PillarResult:
    # Consensus rating level (latest period).
    bull = _bull_ratio(recs[0]) if recs else None
    consensus_score = bull if bull is not None else NEUTRAL

    # Price-target implied upside.
    tmean = _f(target, "targetMean")
    upside = None
    if tmean and current_price:
        upside = (tmean - current_price) / current_price * 100.0

    # Average recent earnings surprise %.
    surprises = [_f(e, "surprisePercent") for e in earnings_list[:4]]
    surprises = [s for s in surprises if s is not None]
    avg_surprise = sum(surprises) / len(surprises) if surprises else None

    factors = [
        make_factor(
            "Analyst consensus", bull, consensus_score,
            "Buy/hold/sell mix (weighted)", available=bull is not None,
        ),
        make_factor("Price-target upside %", upside, score_higher_better(upside, -20.0, 40.0), "Mean target vs current price"),
        make_factor("Avg earnings surprise %", avg_surprise, score_higher_better(avg_surprise, -10.0, 10.0), "Recent beats/misses"),
    ]
    return build_pillar("estimates", factors)


# --- 6. Momentum / Technicals -------------------------------------------------
def momentum(metrics: dict[str, Any], quote: dict[str, Any]) -> PillarResult:
    price = _f(quote, "c")
    high = _f(metrics, "52WeekHigh")
    low = _f(metrics, "52WeekLow")
    range_pos = None
    if price and high and low and high > low:
        range_pos = (price - low) / (high - low) * 100.0

    rel_sp = _f(metrics, "priceRelativeToS&P50052Week")
    ret_52w = _f(metrics, "52WeekPriceReturnDaily")

    factors = [
        make_factor("52-week range position", range_pos, clamp(range_pos) if range_pos is not None else NEUTRAL, "Where price sits in its yearly range"),
        make_factor("Relative strength vs S&P %", rel_sp, score_higher_better(rel_sp, -30.0, 30.0), "1-year outperformance"),
        make_factor("52-week price return %", ret_52w, score_higher_better(ret_52w, -30.0, 40.0), "Trailing 12-month return"),
    ]
    return build_pillar("momentum", factors)


# --- 7. Sentiment -------------------------------------------------------------
def sentiment(recs: list[dict[str, Any]], news_count: int) -> PillarResult:
    # Recommendation momentum: change in bull ratio vs the prior period.
    delta = None
    if len(recs) >= 2:
        cur, prev = _bull_ratio(recs[0]), _bull_ratio(recs[1])
        if cur is not None and prev is not None:
            delta = cur - prev
    factors = [
        make_factor("Analyst rating momentum", delta, score_higher_better(delta, -15.0, 15.0), "Consensus improving vs deteriorating"),
        make_factor("News flow (30d)", float(news_count), NEUTRAL if news_count else NEUTRAL, "Headline volume (tone scored by AI narrative)", available=news_count > 0),
    ]
    return build_pillar("sentiment", factors)


# --- 8. Ownership / Smart money ----------------------------------------------
def ownership(insiders: list[dict[str, Any]]) -> PillarResult:
    net_shares = 0.0
    for t in insiders:
        change = t.get("change")
        if isinstance(change, (int, float)):
            net_shares += change
    if insiders:
        # Sign-based: net buying bullish, net selling bearish. Magnitude is noisy,
        # so we map direction to a score rather than the raw share count.
        if net_shares > 0:
            insider_score, detail = 70.0, "Net insider buying"
        elif net_shares < 0:
            insider_score, detail = 35.0, "Net insider selling"
        else:
            insider_score, detail = NEUTRAL, "Flat insider activity"
        available = True
    else:
        insider_score, detail, available = NEUTRAL, "No insider data (free-tier gated)", False
    factors = [
        make_factor("Insider net activity", net_shares if insiders else None, insider_score, detail, available=available),
    ]
    return build_pillar("ownership", factors)
