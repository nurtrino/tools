"""Central configuration: API keys, model, and the pillar weights that drive the rating.

Weights live here (not in code) so you can re-tilt the engine — value investor vs.
momentum vs. quality — without touching the scoring logic. They must sum to 1.0.
"""
from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

# --- Credentials --------------------------------------------------------------
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "").strip()
FMP_API_KEY = os.getenv("FMP_API_KEY", "").strip()
FRED_API_KEY = os.getenv("FRED_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5").strip()
SEC_USER_AGENT = os.getenv(
    "SEC_USER_AGENT", "PublicCompanyAnalyser/1.0 (contact@example.com)"
).strip()

# --- Pillar weights (must sum to 1.0) -----------------------------------------
PILLAR_WEIGHTS: dict[str, float] = {
    "valuation": 0.18,
    "growth": 0.15,
    "quality": 0.15,
    "health": 0.12,
    "estimates": 0.15,
    "momentum": 0.10,
    "sentiment": 0.08,
    "ownership": 0.07,
}

# Human-readable pillar titles for the UI.
PILLAR_TITLES: dict[str, str] = {
    "valuation": "Valuation",
    "growth": "Growth",
    "quality": "Profitability / Quality",
    "health": "Financial Health",
    "estimates": "Estimates & Revisions",
    "momentum": "Momentum / Technicals",
    "sentiment": "Sentiment",
    "ownership": "Ownership",
}

# --- Rating buckets: (inclusive lower bound, label) ---------------------------
RATING_BUCKETS: list[tuple[float, str]] = [
    (85.0, "Strong Buy"),
    (65.0, "Buy"),
    (40.0, "Hold"),
    (20.0, "Sell"),
    (0.0, "Strong Sell"),
]

# --- "Top players" allowlist for the named-ratings panel ----------------------
# When ratings come from FMP (which names the grading firm), the consensus panel
# highlights only these heavyweight houses. Matched case-insensitively as
# substrings of the firm name (so "B of A Securities" matches "b of a"). Tune freely.
TOP_RATING_FIRMS: list[str] = [
    "goldman", "morgan stanley", "jpmorgan", "jp morgan", "j.p. morgan",
    "bank of america", "b of a", "bofa", "citigroup", "citi", "wells fargo",
    "barclays", "ubs", "deutsche", "jefferies", "evercore", "bernstein",
    "rbc", "td cowen", "cowen", "wedbush", "morningstar", "hsbc", "mizuho",
    "baird", "piper sandler", "oppenheimer", "raymond james", "truist",
    "guggenheim", "needham", "bmo", "stifel", "scotiabank", "daiwa", "redburn",
]

# Cache TTL for API responses (seconds). Same ticker on the same day -> same result.
CACHE_TTL_SECONDS = 60 * 60 * 12  # 12 hours


def rating_for(score: float) -> str:
    """Map a 0-100 composite score to a rating label."""
    for lower, label in RATING_BUCKETS:
        if score >= lower:
            return label
    return "Strong Sell"


def validate_weights() -> None:
    total = sum(PILLAR_WEIGHTS.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"PILLAR_WEIGHTS must sum to 1.0, got {total:.4f}")


validate_weights()
