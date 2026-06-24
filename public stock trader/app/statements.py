"""Turn raw EDGAR XBRL company-facts into a standardized, analyst-friendly view.

Output is a multi-year financial summary (income statement, balance sheet, cash
flow highlights) plus the derived figures the rest of the engine needs: free cash
flow, EBITDA, total debt, net debt, shares outstanding. Different filers tag the
same line under different us-gaap concepts, so each field tries several tags.
"""
from __future__ import annotations

from typing import Any, Optional

# Candidate us-gaap concepts per line item, in priority order.
CONCEPTS: dict[str, list[str]] = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "eps_diluted": ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"],
    "rd_expense": ["ResearchAndDevelopmentExpense"],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ],
    "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "short_term_debt": ["LongTermDebtCurrent", "DebtCurrent", "ShortTermBorrowings"],
    "dep_amort": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "DepreciationAndAmortization",
    ],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],
    "shares_diluted": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    "shares_outstanding": ["CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding"],
    # Extra lines used by the forensic / quality scores (not shown in the table).
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "retained_earnings": ["RetainedEarningsAccumulatedDeficit"],
    "dividends_paid": ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"],
    "buybacks": ["PaymentsForRepurchaseOfCommonStock", "PaymentsForRepurchaseOfCommonStockAndPreferredStock"],
    "cogs": ["CostOfGoodsAndServicesSold", "CostOfRevenue"],
    "receivables": ["AccountsReceivableNetCurrent", "AccountsReceivableNet"],
    "ppe_net": ["PropertyPlantAndEquipmentNet"],
    "sga": ["SellingGeneralAndAdministrativeExpense", "GeneralAndAdministrativeExpense"],
}


def _annual_map(facts: dict[str, Any], tags: list[str]) -> dict[int, float]:
    """{fiscal_year: value} for the first matching concept, annual (FY) figures."""
    try:
        gaap = facts["facts"]["us-gaap"]
    except (KeyError, TypeError):
        gaap = {}
    dei = facts.get("facts", {}).get("dei", {})
    for tag in tags:
        node = gaap.get(tag) or dei.get(tag)
        if not node:
            continue
        units = node.get("units", {})
        series = units.get("USD") or units.get("USD/shares") or units.get("shares") \
            or next(iter(units.values()), [])
        out: dict[int, float] = {}
        for row in series:
            if row.get("form") not in ("10-K", "20-F"):
                continue
            fy = row.get("fy")
            val = row.get("val")
            if isinstance(fy, int) and isinstance(val, (int, float)):
                # Prefer full-year frames; keep the latest filed value per FY.
                out[fy] = float(val)
        if out:
            return out
    return {}


def build(facts: dict[str, Any], max_years: int = 5) -> dict[str, Any]:
    """Return {'years': [...], 'lines': {field: {fy: val}}, 'latest': {field: val}, 'derived': {...}}."""
    if not facts:
        return {}
    lines = {field: _annual_map(facts, tags) for field, tags in CONCEPTS.items()}

    # Most recent `max_years` fiscal years that have a revenue figure.
    rev_years = sorted(lines.get("revenue", {}).keys())
    years = rev_years[-max_years:] if rev_years else \
        sorted({fy for m in lines.values() for fy in m})[-max_years:]
    if not years:
        return {}

    def latest(field: str) -> Optional[float]:
        m = lines.get(field, {})
        return m.get(years[-1]) if m else None

    op_cf = latest("operating_cash_flow")
    capex = latest("capex")
    free_cash_flow = (op_cf - capex) if (op_cf is not None and capex is not None) else None

    op_inc = latest("operating_income")
    da = latest("dep_amort")
    ebitda = (op_inc + da) if (op_inc is not None and da is not None) else None

    ltd = latest("long_term_debt") or 0.0
    std = latest("short_term_debt") or 0.0
    total_debt = ltd + std if (latest("long_term_debt") or latest("short_term_debt")) else None
    cash = latest("cash")
    net_debt = (total_debt - cash) if (total_debt is not None and cash is not None) else None

    shares = latest("shares_outstanding") or latest("shares_diluted")

    return {
        "years": years,
        "lines": lines,
        "latest": {field: latest(field) for field in CONCEPTS},
        "derived": {
            "free_cash_flow": free_cash_flow,
            "ebitda": ebitda,
            "total_debt": total_debt,
            "net_debt": net_debt,
            "shares": shares,
        },
    }


# Which lines to render in the UI statement table, grouped by statement.
STATEMENT_LAYOUT = [
    ("Income statement", [
        ("Revenue", "revenue"),
        ("Gross profit", "gross_profit"),
        ("Operating income", "operating_income"),
        ("Net income", "net_income"),
        ("Diluted EPS", "eps_diluted"),
        ("R&D expense", "rd_expense"),
    ]),
    ("Balance sheet", [
        ("Total assets", "assets"),
        ("Total liabilities", "liabilities"),
        ("Shareholders' equity", "equity"),
        ("Cash & equivalents", "cash"),
    ]),
    ("Cash flow", [
        ("Operating cash flow", "operating_cash_flow"),
        ("Capital expenditure", "capex"),
    ]),
]
