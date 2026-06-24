"""Forensic & quality scores computed from EDGAR financials (all free).

  * Piotroski F-Score (0-9)  — fundamental momentum / quality
  * Altman Z-Score           — bankruptcy / distress risk
  * Beneish M-Score          — earnings-manipulation flag
  * Earnings quality         — FCF/NI + accruals ratio
  * Shareholder yield        — dividends + buybacks vs market cap
  * Dividend safety          — payout ratio + FCF coverage

Each returns an {"available": bool, ...} dict; missing line items degrade to
available=False rather than producing a misleading number.
"""
from __future__ import annotations

from typing import Any, Optional


def _g(lines: dict, field: str, fy: Optional[int]) -> Optional[float]:
    if fy is None:
        return None
    v = lines.get(field, {}).get(fy)
    return float(v) if isinstance(v, (int, float)) else None


def compute(stmt: dict[str, Any], market_cap: Optional[float]) -> dict[str, Any]:
    if not stmt or not stmt.get("years"):
        return {}
    years, L, derived = stmt["years"], stmt["lines"], stmt.get("derived", {})
    cy = years[-1]
    py = years[-2] if len(years) >= 2 else None
    return {
        "piotroski": _piotroski(L, cy, py),
        "altman": _altman(L, cy, market_cap),
        "beneish": _beneish(L, cy, py),
        "earnings_quality": _earnings_quality(L, cy, derived),
        "shareholder_yield": _shareholder_yield(L, cy, market_cap),
        "dividend_safety": _dividend_safety(L, cy, derived),
    }


def _piotroski(L: dict, cy: int, py: Optional[int]) -> dict[str, Any]:
    if py is None:
        return {"available": False, "note": "Needs two fiscal years."}
    ni, ni_p = _g(L, "net_income", cy), _g(L, "net_income", py)
    a, a_p = _g(L, "assets", cy), _g(L, "assets", py)
    ocf = _g(L, "operating_cash_flow", cy)
    roa = ni / a if (ni is not None and a) else None
    roa_p = ni_p / a_p if (ni_p is not None and a_p) else None
    ltd, ltd_p = _g(L, "long_term_debt", cy), _g(L, "long_term_debt", py)
    lev = ltd / a if (ltd is not None and a) else None
    lev_p = ltd_p / a_p if (ltd_p is not None and a_p) else None
    ca, cl = _g(L, "current_assets", cy), _g(L, "current_liabilities", cy)
    ca_p, cl_p = _g(L, "current_assets", py), _g(L, "current_liabilities", py)
    cr = ca / cl if (ca is not None and cl) else None
    cr_p = ca_p / cl_p if (ca_p is not None and cl_p) else None
    sh = _g(L, "shares_outstanding", cy) or _g(L, "shares_diluted", cy)
    sh_p = _g(L, "shares_outstanding", py) or _g(L, "shares_diluted", py)
    gp, rev = _g(L, "gross_profit", cy), _g(L, "revenue", cy)
    gp_p, rev_p = _g(L, "gross_profit", py), _g(L, "revenue", py)
    gm = gp / rev if (gp is not None and rev) else None
    gm_p = gp_p / rev_p if (gp_p is not None and rev_p) else None
    at = rev / a if (rev is not None and a) else None
    at_p = rev_p / a_p if (rev_p is not None and a_p) else None

    checks = [
        ("ROA positive", roa is not None and roa > 0),
        ("Operating cash flow positive", ocf is not None and ocf > 0),
        ("ROA improving", roa is not None and roa_p is not None and roa > roa_p),
        ("Cash flow exceeds net income", ocf is not None and ni is not None and ocf > ni),
        ("Leverage decreasing", lev is not None and lev_p is not None and lev < lev_p),
        ("Current ratio improving", cr is not None and cr_p is not None and cr > cr_p),
        ("No share dilution", sh is not None and sh_p is not None and sh <= sh_p * 1.01),
        ("Gross margin improving", gm is not None and gm_p is not None and gm > gm_p),
        ("Asset turnover improving", at is not None and at_p is not None and at > at_p),
    ]
    score = sum(1 for _, ok in checks if ok)
    return {
        "available": True,
        "score": score,
        "max": 9,
        "verdict": "Strong" if score >= 7 else ("Weak" if score <= 3 else "Average"),
        "checks": [{"name": n, "pass": bool(ok)} for n, ok in checks],
    }


def _altman(L: dict, cy: int, market_cap: Optional[float]) -> dict[str, Any]:
    a = _g(L, "assets", cy)
    ca, cl = _g(L, "current_assets", cy), _g(L, "current_liabilities", cy)
    re = _g(L, "retained_earnings", cy)
    ebit = _g(L, "operating_income", cy)
    tl = _g(L, "liabilities", cy)
    rev = _g(L, "revenue", cy)
    wc = (ca - cl) if (ca is not None and cl is not None) else None
    parts = {
        "x1": wc / a if (wc is not None and a) else None,
        "x2": re / a if (re is not None and a) else None,
        "x3": ebit / a if (ebit is not None and a) else None,
        "x4": market_cap / tl if (market_cap and tl) else None,
        "x5": rev / a if (rev is not None and a) else None,
    }
    if any(v is None for v in parts.values()):
        return {"available": False, "note": "Incomplete balance sheet data."}
    z = 1.2 * parts["x1"] + 1.4 * parts["x2"] + 3.3 * parts["x3"] + 0.6 * parts["x4"] + 1.0 * parts["x5"]
    zone = "Safe" if z > 2.99 else ("Grey zone" if z >= 1.81 else "Distress")
    return {"available": True, "z": round(z, 2), "zone": zone}


def _beneish(L: dict, cy: int, py: Optional[int]) -> dict[str, Any]:
    if py is None:
        return {"available": False}
    try:
        recv, recv_p = _g(L, "receivables", cy), _g(L, "receivables", py)
        sales, sales_p = _g(L, "revenue", cy), _g(L, "revenue", py)
        cogs, cogs_p = _g(L, "cogs", cy), _g(L, "cogs", py)
        ca, ca_p = _g(L, "current_assets", cy), _g(L, "current_assets", py)
        ppe, ppe_p = _g(L, "ppe_net", cy), _g(L, "ppe_net", py)
        a, a_p = _g(L, "assets", cy), _g(L, "assets", py)
        dep, dep_p = _g(L, "dep_amort", cy), _g(L, "dep_amort", py)
        sga, sga_p = _g(L, "sga", cy), _g(L, "sga", py)
        ltd, ltd_p = _g(L, "long_term_debt", cy) or 0, _g(L, "long_term_debt", py) or 0
        cl, cl_p = _g(L, "current_liabilities", cy), _g(L, "current_liabilities", py)
        ni, ocf = _g(L, "net_income", cy), _g(L, "operating_cash_flow", cy)
        required = [recv, recv_p, sales, sales_p, cogs, cogs_p, ca, ca_p, ppe, ppe_p,
                    a, a_p, dep, dep_p, sga, sga_p, cl, cl_p, ni, ocf]
        if any(v is None for v in required):
            return {"available": False}
        dsri = (recv / sales) / (recv_p / sales_p)
        gmi = ((sales_p - cogs_p) / sales_p) / ((sales - cogs) / sales)
        aqi = (1 - (ca + ppe) / a) / (1 - (ca_p + ppe_p) / a_p)
        sgi = sales / sales_p
        depi = (dep_p / (dep_p + ppe_p)) / (dep / (dep + ppe))
        sgai = (sga / sales) / (sga_p / sales_p)
        lvgi = ((ltd + cl) / a) / ((ltd_p + cl_p) / a_p)
        tata = (ni - ocf) / a
        m = (-4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi
             + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi)
        return {
            "available": True,
            "m": round(m, 2),
            "flag": "Possible manipulation" if m > -1.78 else "Unlikely manipulation",
        }
    except (ZeroDivisionError, TypeError):
        return {"available": False}


def _earnings_quality(L: dict, cy: int, derived: dict) -> dict[str, Any]:
    ni, ocf, a = _g(L, "net_income", cy), _g(L, "operating_cash_flow", cy), _g(L, "assets", cy)
    fcf = derived.get("free_cash_flow")
    fcf_ni = fcf / ni if (fcf is not None and ni) else None
    accruals = (ni - ocf) / a if (ni is not None and ocf is not None and a) else None
    if fcf_ni is None and accruals is None:
        return {"available": False}
    return {
        "available": True,
        "fcf_to_ni": round(fcf_ni, 2) if fcf_ni is not None else None,
        "accruals_ratio": round(accruals, 3) if accruals is not None else None,
    }


def _shareholder_yield(L: dict, cy: int, market_cap: Optional[float]) -> dict[str, Any]:
    if not market_cap:
        return {"available": False}
    div = _g(L, "dividends_paid", cy) or 0.0
    buy = _g(L, "buybacks", cy) or 0.0
    if div == 0 and buy == 0:
        return {"available": False}
    return {
        "available": True,
        "yield_pct": round((div + buy) / market_cap * 100, 2),
        "dividend": div,
        "buyback": buy,
    }


def _dividend_safety(L: dict, cy: int, derived: dict) -> dict[str, Any]:
    div = _g(L, "dividends_paid", cy)
    if not div:
        return {"available": False, "note": "No dividend paid."}
    ni = _g(L, "net_income", cy)
    fcf = derived.get("free_cash_flow")
    return {
        "available": True,
        "payout_ratio": round(div / ni, 2) if ni else None,
        "fcf_coverage": round(fcf / div, 2) if (fcf and div) else None,
    }
