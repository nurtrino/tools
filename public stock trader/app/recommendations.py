"""Aggregate Wall Street analyst recommendations into a single data-driven readout.

This is the "analyst consensus" the user sees — derived purely from published
ratings and price targets, not from any model opinion. Preferred source is FMP,
which *names the grading firm* (so we can surface the top-player houses); if FMP is
absent or paywalled we fall back to Finnhub's anonymized buy/hold/sell counts.
"""
from __future__ import annotations

from typing import Any, Optional

from config import TOP_RATING_FIRMS

_BUCKETS = ("strongBuy", "buy", "hold", "sell", "strongSell")
_BUCKET_WEIGHT = {"strongBuy": 1.0, "buy": 0.75, "hold": 0.5, "sell": 0.25, "strongSell": 0.0}


def _f(d: dict[str, Any], key: str) -> Optional[float]:
    v = d.get(key)
    return float(v) if isinstance(v, (int, float)) else None


def _consensus_label(score: float) -> str:
    if score >= 85:
        return "Strong Buy"
    if score >= 65:
        return "Buy"
    if score >= 40:
        return "Hold"
    if score >= 20:
        return "Sell"
    return "Strong Sell"


def _score_from_counts(counts: dict[str, int]) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    weighted = sum(counts[b] * _BUCKET_WEIGHT[b] for b in _BUCKETS)
    return weighted / total * 100.0


def _is_top_firm(name: str) -> bool:
    n = (name or "").lower()
    return any(k in n for k in TOP_RATING_FIRMS)


def _bucket_for_grade(grade: str) -> Optional[str]:
    """Map a free-text grade (e.g. 'Overweight', 'Market Perform') to a bucket."""
    g = (grade or "").lower().strip()
    if not g:
        return None
    if "strong buy" in g:
        return "strongBuy"
    if "strong sell" in g:
        return "strongSell"
    if any(k in g for k in ("buy", "outperform", "overweight", "accumulate", "positive", "add")):
        return "buy"
    if any(k in g for k in ("sell", "underperform", "underweight", "reduce", "negative")):
        return "sell"
    if any(k in g for k in ("hold", "neutral", "equal", "market perform", "sector perform", "in-line", "peer perform")):
        return "hold"
    return None


# --- FMP path (named firms) ---------------------------------------------------
def _top_firm_ratings(grades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Latest rating per top-player firm, most recent first."""
    seen: dict[str, dict[str, Any]] = {}
    for g in sorted(grades, key=lambda x: x.get("date") or "", reverse=True):
        firm = g.get("gradingCompany") or ""
        if not _is_top_firm(firm) or firm in seen:
            continue
        grade = g.get("newGrade") or ""
        seen[firm] = {
            "firm": firm,
            "grade": grade,
            "bucket": _bucket_for_grade(grade),
            "action": g.get("action"),
            "date": g.get("date"),
        }
    return list(seen.values())[:12]


def build_from_fmp(
    consensus: dict[str, Any],
    grades: list[dict[str, Any]],
    grades_hist: list[dict[str, Any]],
    target: dict[str, Any],
    current_price: Optional[float],
) -> Optional[dict[str, Any]]:
    counts = {b: int(_f(consensus, b) or 0) for b in _BUCKETS}
    total = sum(counts.values())
    if total == 0:
        return None  # signal the caller to fall back to Finnhub

    score = _score_from_counts(counts)
    tmean = _f(target, "targetConsensus")
    upside = (tmean - current_price) / current_price * 100.0 if (tmean and current_price) else None

    hist = sorted(grades_hist, key=lambda x: x.get("date") or "")[-6:]
    trend = [{
        "period": r.get("date"),
        "strongBuy": int(_f(r, "analystRatingsStrongBuy") or 0),
        "buy": int(_f(r, "analystRatingsBuy") or 0),
        "hold": int(_f(r, "analystRatingsHold") or 0),
        "sell": int(_f(r, "analystRatingsSell") or 0),
        "strongSell": int(_f(r, "analystRatingsStrongSell") or 0),
    } for r in hist]

    return {
        "available": True,
        "source": "Financial Modeling Prep",
        "period": hist[-1]["date"] if hist else None,
        "counts": counts,
        "total_analysts": total,
        "consensus_score": round(score, 1),
        "consensus_label": _consensus_label(score),
        "firm_ratings": _top_firm_ratings(grades),
        "price_target": {
            "mean": tmean,
            "high": _f(target, "targetHigh"),
            "low": _f(target, "targetLow"),
            "median": _f(target, "targetMedian"),
            "current": current_price,
            "upside_pct": round(upside, 1) if upside is not None else None,
        },
        "trend": trend,
    }


# --- Finnhub fallback (anonymized counts) -------------------------------------
def build_from_finnhub(
    recs: list[dict[str, Any]], target: dict[str, Any], current_price: Optional[float],
) -> Optional[dict[str, Any]]:
    if not recs:
        return None
    latest = recs[0]
    counts = {b: int(_f(latest, b) or 0) for b in _BUCKETS}
    total = sum(counts.values())
    if total == 0:
        return None

    score = _score_from_counts(counts)
    tmean = _f(target, "targetMean")
    upside = (tmean - current_price) / current_price * 100.0 if (tmean and current_price) else None

    return {
        "available": True,
        "source": "Finnhub",
        "period": latest.get("period"),
        "counts": counts,
        "total_analysts": total,
        "consensus_score": round(score, 1),
        "consensus_label": _consensus_label(score),
        "firm_ratings": [],  # Finnhub doesn't name the firms
        "price_target": {
            "mean": tmean,
            "high": _f(target, "targetHigh"),
            "low": _f(target, "targetLow"),
            "median": None,
            "current": current_price,
            "upside_pct": round(upside, 1) if upside is not None else None,
        },
        "trend": [{
            "period": r.get("period"),
            "strongBuy": int(_f(r, "strongBuy") or 0),
            "buy": int(_f(r, "buy") or 0),
            "hold": int(_f(r, "hold") or 0),
            "sell": int(_f(r, "sell") or 0),
            "strongSell": int(_f(r, "strongSell") or 0),
        } for r in reversed(recs[:6])],
    }


def build(
    current_price: Optional[float],
    *,
    fmp_consensus: dict[str, Any] | None = None,
    fmp_grades: list[dict[str, Any]] | None = None,
    fmp_grades_hist: list[dict[str, Any]] | None = None,
    fmp_target: dict[str, Any] | None = None,
    finnhub_recs: list[dict[str, Any]] | None = None,
    finnhub_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Prefer FMP (named firms); fall back to Finnhub if FMP is empty/paywalled."""
    fmp = build_from_fmp(
        fmp_consensus or {}, fmp_grades or [], fmp_grades_hist or [],
        fmp_target or {}, current_price,
    )
    if fmp:
        return fmp
    finnhub = build_from_finnhub(finnhub_recs or [], finnhub_target or {}, current_price)
    return finnhub or {"available": False}
