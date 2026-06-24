"""Shared data structures for the scoring engine.

A FactorScore is one computed metric (e.g. P/E vs peers). A PillarResult bundles
the factors for one pillar into a single 0-100 score. AnalysisResult is the whole
scorecard returned to the API/UI.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class FactorScore:
    name: str
    score: float  # 0-100 (50 = neutral / no data)
    raw: Optional[float] = None  # the underlying metric value, for display
    detail: str = ""
    available: bool = True  # False -> we had no data and used a neutral 50

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PillarResult:
    key: str
    title: str
    score: float
    weight: float
    factors: list[FactorScore] = field(default_factory=list)
    coverage: float = 1.0  # fraction of factors that had real data

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["factors"] = [f.to_dict() for f in self.factors]
        return d


@dataclass
class AnalysisResult:
    ticker: str
    company_name: str
    composite: float
    rating: str
    pillars: list[PillarResult]
    generated_at: str = ""
    data_sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sections: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["pillars"] = [p.to_dict() for p in self.pillars]
        return d
