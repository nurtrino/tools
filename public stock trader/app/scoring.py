"""Scoring primitives: map raw metrics to 0-100 sub-scores, then pillars to a composite.

The verdict is fully deterministic — no LLM in this path — so the same inputs always
produce the same rating, and every number is auditable back to a metric.
"""
from __future__ import annotations

from typing import Optional

from app.models import AnalysisResult, FactorScore, PillarResult
from config import PILLAR_TITLES, PILLAR_WEIGHTS, rating_for

NEUTRAL = 50.0


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def score_higher_better(value: Optional[float], bad: float, good: float) -> float:
    """Linear map where `good` -> 100 and `bad` -> 0. Returns NEUTRAL if value is None."""
    if value is None:
        return NEUTRAL
    if good == bad:
        return NEUTRAL
    return clamp((value - bad) / (good - bad) * 100.0)


def score_lower_better(value: Optional[float], good: float, bad: float) -> float:
    """Linear map where `good` -> 100 and `bad` -> 0 (lower raw value is better)."""
    if value is None:
        return NEUTRAL
    if good == bad:
        return NEUTRAL
    return clamp((bad - value) / (bad - good) * 100.0)


def make_factor(
    name: str,
    value: Optional[float],
    score: float,
    detail: str,
    available: Optional[bool] = None,
) -> FactorScore:
    avail = (value is not None) if available is None else available
    return FactorScore(
        name=name,
        score=round(score, 1),
        raw=round(value, 4) if isinstance(value, (int, float)) else None,
        detail=detail,
        available=avail,
    )


def build_pillar(key: str, factors: list[FactorScore]) -> PillarResult:
    """Average the factor scores into a pillar score and track data coverage."""
    if factors:
        pillar_score = sum(f.score for f in factors) / len(factors)
        coverage = sum(1 for f in factors if f.available) / len(factors)
    else:
        pillar_score, coverage = NEUTRAL, 0.0
    return PillarResult(
        key=key,
        title=PILLAR_TITLES.get(key, key.title()),
        score=round(pillar_score, 1),
        weight=PILLAR_WEIGHTS.get(key, 0.0),
        factors=factors,
        coverage=round(coverage, 2),
    )


def composite(pillars: list[PillarResult]) -> float:
    """Weighted sum of pillar scores -> 0-100 composite."""
    total = sum(p.score * p.weight for p in pillars)
    return round(total, 1)


def assemble(
    ticker: str,
    company_name: str,
    pillars: list[PillarResult],
    generated_at: str,
    data_sources: list[str],
    warnings: list[str],
) -> AnalysisResult:
    comp = composite(pillars)
    return AnalysisResult(
        ticker=ticker.upper(),
        company_name=company_name,
        composite=comp,
        rating=rating_for(comp),
        pillars=pillars,
        generated_at=generated_at,
        data_sources=data_sources,
        warnings=warnings,
    )
