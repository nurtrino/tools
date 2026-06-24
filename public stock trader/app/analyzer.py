"""Orchestrator: ticker in, full analysis (rating + all display sections) out.

The headline rating is the average of Wall Street analyst ratings (the consensus
score), not an LLM opinion. The eight-pillar scorecard is still computed and shown
for reference, but it no longer sets the rating (it's only the fallback when a
ticker has no analyst coverage). Every data source is optional; missing data
degrades gracefully rather than failing the run.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Optional

from app import dcf as dcf_model
from app import factors, recommendations, scores as scores_mod, statements, valuation
from app.connectors import edgar, finnhub, fmp, fred
from app.models import AnalysisResult
from app.scoring import assemble


def _filing_url(cik: str, accession: Optional[str], doc: Optional[str]) -> Optional[str]:
    if not accession or not doc:
        return None
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{doc}"


def _statement_table(stmt: dict[str, Any]) -> dict[str, Any]:
    """Shape the standardized statements for the UI table."""
    if not stmt:
        return {}
    years = stmt["years"]
    lines = stmt["lines"]
    groups = []
    for group_name, rows in statements.STATEMENT_LAYOUT:
        out_rows = []
        for label, field in rows:
            m = lines.get(field, {})
            out_rows.append({
                "label": label,
                "unit": "pershare" if field == "eps_diluted" else "money",
                "values": [m.get(fy) for fy in years],
            })
        groups.append({"name": group_name, "rows": out_rows})
    return {"years": years, "groups": groups}


def analyze(ticker: str) -> AnalysisResult:
    ticker = ticker.strip().upper()
    warnings: list[str] = []
    sources: list[str] = []

    # --- Finnhub: quantitative backbone --------------------------------------
    profile = finnhub.profile(ticker)
    metrics = finnhub.metrics(ticker)
    quote = finnhub.quote(ticker)
    recs = finnhub.recommendations(ticker)
    target = finnhub.price_target(ticker)
    # Named analyst ratings via FMP (falls back to the Finnhub data above if paywalled).
    fmp_consensus = fmp.grades_consensus(ticker)
    fmp_grades = fmp.grades(ticker)
    fmp_grades_hist = fmp.grades_historical(ticker)
    fmp_target = fmp.price_target_consensus(ticker)
    earnings = finnhub.earnings(ticker)
    insiders = finnhub.insider_transactions(ticker)
    news = finnhub.company_news(ticker)
    next_earnings = finnhub.earnings_calendar(ticker)

    if metrics or quote:
        sources.append("Finnhub")
    else:
        warnings.append("No Finnhub data — check FINNHUB_API_KEY.")

    company_name = profile.get("name") or ticker
    current_price = quote.get("c") if isinstance(quote.get("c"), (int, float)) else None

    # --- SEC EDGAR: filings + standardized financial statements ---------------
    cik = edgar.cik_for(ticker)
    stmt = {}
    filings_section: list[dict[str, Any]] = []
    if cik:
        sources.append("SEC EDGAR")
        facts = edgar.company_facts(cik)
        stmt = statements.build(facts)
        for f in edgar.recent_filings(cik):
            filings_section.append({
                "form": f["form"],
                "date": f["filingDate"],
                "url": _filing_url(cik, f.get("accessionNumber"), f.get("primaryDocument")),
            })
    else:
        warnings.append(f"No SEC CIK found for {ticker} (foreign/ADR or non-filer?).")

    # --- Forensic / quality scores (from EDGAR) -------------------------------
    mcap_m = profile.get("marketCapitalization")
    market_cap = mcap_m * 1_000_000 if isinstance(mcap_m, (int, float)) else None
    quant_scores = scores_mod.compute(stmt, market_cap) if stmt else {}

    # --- Pillars / deterministic rating ---------------------------------------
    pillars = [
        factors.valuation(metrics),
        factors.growth(metrics),
        factors.quality(metrics, quant_scores),
        factors.health(metrics, quant_scores),
        factors.estimates(recs, target, earnings, current_price),
        factors.momentum(metrics, quote),
        factors.sentiment(recs, len(news)),
        factors.ownership(insiders),
    ]

    # --- Macro (FRED) ---------------------------------------------------------
    macro = fred.snapshot()
    if any(v is not None for v in macro.values()):
        sources.append("FRED (macro)")

    result = assemble(
        ticker=ticker,
        company_name=company_name,
        pillars=pillars,
        generated_at=_dt.datetime.now().isoformat(timespec="seconds"),
        data_sources=sources,
        warnings=warnings,
    )

    # --- Display sections -----------------------------------------------------
    dcf_summary = dcf_model.compute(
        stmt,
        current_price,
        **dcf_model.inputs_from_market_data(profile, metrics, macro),
    )

    consensus = recommendations.build(
        current_price,
        fmp_consensus=fmp_consensus, fmp_grades=fmp_grades,
        fmp_grades_hist=fmp_grades_hist, fmp_target=fmp_target,
        finnhub_recs=recs, finnhub_target=target,
    )
    if consensus.get("source") == "Financial Modeling Prep" and "Financial Modeling Prep" not in result.data_sources:
        result.data_sources.append("Financial Modeling Prep")

    # --- Headline verdict = average of Wall Street analyst ratings -------------
    # The pillar scorecard is kept for reference but no longer sets the rating.
    # If a ticker has no analyst ratings at all, fall back to the pillar composite
    # so the gauge still shows something.
    if consensus.get("available"):
        result.composite = consensus["consensus_score"]
        result.rating = consensus["consensus_label"]
    else:
        warnings.append("No analyst ratings found — falling back to the pillar scorecard for the rating.")

    result.sections = {
        "profile": {
            "name": company_name,
            "industry": profile.get("finnhubIndustry"),
            "exchange": profile.get("exchange"),
            "currency": profile.get("currency"),
            "logo": profile.get("logo"),
            "ir_website": profile.get("weburl"),
            "market_cap_m": profile.get("marketCapitalization"),
        },
        "price": {
            "current": current_price,
            "change": quote.get("d"),
            "change_pct": quote.get("dp"),
            "prev_close": quote.get("pc"),
            "high": quote.get("h"),
            "low": quote.get("l"),
        },
        "chart": {"symbol": ticker, "exchange": profile.get("exchange")},
        "financials": _statement_table(stmt),
        "valuation": valuation.build(metrics, stmt, profile, current_price),
        "recommendations": consensus,
        "earnings": {
            "past": [
                {
                    "period": e.get("period"),
                    "actual": e.get("actual"),
                    "estimate": e.get("estimate"),
                    "surprise_pct": e.get("surprisePercent"),
                }
                for e in earnings[:8]
            ],
            "next": {
                "date": next_earnings.get("date"),
                "hour": next_earnings.get("hour"),
                "eps_estimate": next_earnings.get("epsEstimate"),
                "revenue_estimate": next_earnings.get("revenueEstimate"),
            } if next_earnings else {},
        },
        "filings": filings_section,
        "dcf": dcf_summary,
        "quant_scores": quant_scores,
    }

    return result
