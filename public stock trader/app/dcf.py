"""Discounted-cash-flow model + Excel export.

A real two-stage unlevered FCF DCF:
  * Base FCF is normalised (3-year average of operating cash flow minus capex) so a
    single noisy year doesn't drive the valuation.
  * Growth is two-stage: a high-growth plateau that then fades linearly to the
    terminal rate over an explicit 10-year horizon — not one flat rate forever.
  * The discount rate is a company-specific WACC (CAPM cost of equity blended with
    after-tax cost of debt at market-value weights), not a hard-coded number.
  * A Gordon-growth terminal value, less net debt, over shares -> fair value.
  * A WACC x terminal-growth sensitivity grid shows how soft the answer is.

Every assumption is explicit and overridable, and the downloaded workbook keeps the
projection live (per-year growth + discounting as formulas).
"""
from __future__ import annotations

import io
from typing import Any, Optional

# --- WACC building blocks (sane defaults; overridden by live data when available) --
DEFAULT_ERP = 0.05          # equity risk premium over the risk-free rate
DEFAULT_RISK_FREE = 0.042   # fallback 10-year Treasury if FRED is unavailable
DEFAULT_BETA = 1.0
DEFAULT_TAX_RATE = 0.21     # US federal statutory corporate rate
CREDIT_SPREAD = 0.02        # pre-tax cost-of-debt proxy = risk-free + spread
WACC_FLOOR, WACC_CEIL = 0.06, 0.15
DEFAULT_DISCOUNT = 0.10     # used only when market cap is unknown (can't weight WACC)


def _normalized_base_fcf(statements: dict[str, Any]) -> tuple[Optional[float], str]:
    """Average of the last up-to-3 years of (operating cash flow - capex).

    Smooths one-off working-capital or capex swings. Falls back to the single
    latest year, then to the pre-derived FCF, returning the method used for display.
    """
    lines = statements.get("lines", {}) if statements else {}
    years = statements.get("years", []) if statements else []
    ocf = lines.get("operating_cash_flow", {})
    capex = lines.get("capex", {})
    series = []
    for fy in years:
        o, c = ocf.get(fy), capex.get(fy)
        if isinstance(o, (int, float)) and isinstance(c, (int, float)):
            series.append(o - c)
    if len(series) >= 2:
        recent = series[-3:]
        return sum(recent) / len(recent), f"{len(recent)}-year average"
    if series:
        return series[-1], "latest year"
    derived = statements.get("derived", {}) if statements else {}
    base = derived.get("free_cash_flow")
    return (base, "latest year") if base else (None, "")


def _compute_wacc(
    market_cap: Optional[float],
    total_debt: Optional[float],
    beta: Optional[float],
    risk_free: Optional[float],
    erp: float,
    tax_rate: float,
) -> tuple[float, dict[str, Any]]:
    """CAPM cost of equity blended with after-tax cost of debt at market-value weights.

    Falls back to DEFAULT_DISCOUNT when market cap is unknown (can't form weights).
    """
    rf = risk_free if isinstance(risk_free, (int, float)) and risk_free > 0 else DEFAULT_RISK_FREE
    b = beta if isinstance(beta, (int, float)) and beta > 0 else DEFAULT_BETA
    cost_equity = rf + b * erp
    cost_debt_pretax = rf + CREDIT_SPREAD
    cost_debt_at = cost_debt_pretax * (1 - tax_rate)

    e = market_cap if isinstance(market_cap, (int, float)) and market_cap > 0 else None
    d = total_debt if isinstance(total_debt, (int, float)) and total_debt > 0 else 0.0
    if e is None:
        return DEFAULT_DISCOUNT, {
            "method": "default (market cap unavailable)",
            "cost_of_equity": round(cost_equity, 4),
            "risk_free": round(rf, 4), "beta": round(b, 3), "erp": erp,
        }
    v = e + d
    we, wd = e / v, d / v
    wacc = we * cost_equity + wd * cost_debt_at
    wacc = max(WACC_FLOOR, min(WACC_CEIL, wacc))
    return wacc, {
        "method": "CAPM + after-tax debt, market-weighted",
        "cost_of_equity": round(cost_equity, 4),
        "cost_of_debt_after_tax": round(cost_debt_at, 4),
        "risk_free": round(rf, 4), "beta": round(b, 3), "erp": erp,
        "tax_rate": tax_rate,
        "equity_weight": round(we, 3), "debt_weight": round(wd, 3),
        "raw_wacc": round(we * cost_equity + wd * cost_debt_at, 4),
        "clamped": not (WACC_FLOOR <= we * cost_equity + wd * cost_debt_at <= WACC_CEIL),
    }


def _growth_for_year(t: int, stage1: float, terminal: float, high_years: int, years: int) -> float:
    """Two-stage path: flat `stage1` through `high_years`, then a linear fade to `terminal`."""
    if t <= high_years:
        return stage1
    span = years - high_years
    if span <= 0:
        return terminal
    frac = (t - high_years) / span  # 0 -> just after plateau, 1 -> final year
    return stage1 + (terminal - stage1) * frac


def _value(base_fcf: float, stage1: float, terminal: float, discount: float,
           high_years: int, years: int, net_debt: float, shares: float) -> dict[str, Any]:
    """Run the projection + terminal value for one (discount, terminal) pair."""
    projection, pv_sum, fcf = [], 0.0, base_fcf
    for t in range(1, years + 1):
        g = _growth_for_year(t, stage1, terminal, high_years, years)
        fcf = fcf * (1 + g)
        df = (1 + discount) ** t
        pv = fcf / df
        pv_sum += pv
        projection.append({"year": t, "growth": round(g, 4), "fcf": fcf,
                           "discount_factor": round(df, 4), "pv": pv})

    if discount <= terminal:  # Gordon growth undefined; nudge to keep it finite
        terminal = discount - 0.005
    terminal_fcf = fcf * (1 + terminal)
    terminal_value = terminal_fcf / (discount - terminal)
    pv_terminal = terminal_value / ((1 + discount) ** years)

    enterprise_value = pv_sum + pv_terminal
    equity_value = enterprise_value - (net_debt or 0.0)
    fair_value = equity_value / shares
    return {
        "projection": projection,
        "terminal_value": terminal_value,
        "pv_terminal": pv_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "fair_value": fair_value,
    }


def _stage1_growth(metrics: dict[str, Any]) -> float:
    """Stage-1 FCF growth from observed revenue growth, clamped to a sane band."""
    for key in ("revenueGrowth5Y", "revenueGrowthTTMYoy"):
        v = (metrics or {}).get(key)
        if isinstance(v, (int, float)):
            return max(0.02, min(0.20, v / 100.0))
    return 0.08


def inputs_from_market_data(
    profile: dict[str, Any],
    metrics: dict[str, Any],
    macro: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the company-specific compute() kwargs from connector data, so the
    on-page model and the downloadable workbook are always built identically."""
    mcap_m = (profile or {}).get("marketCapitalization")
    market_cap = mcap_m * 1_000_000 if isinstance(mcap_m, (int, float)) else None
    yield_10y = macro.get("yield_10y") if macro else None
    risk_free = yield_10y / 100.0 if isinstance(yield_10y, (int, float)) else None
    return {
        "market_cap": market_cap,
        "beta": (metrics or {}).get("beta"),
        "risk_free": risk_free,
        "stage1_growth": _stage1_growth(metrics),
    }


def compute(
    statements: dict[str, Any],
    price: Optional[float],
    *,
    market_cap: Optional[float] = None,
    beta: Optional[float] = None,
    risk_free: Optional[float] = None,
    stage1_growth: float = 0.08,
    terminal_growth: float = 0.025,
    high_growth_years: int = 5,
    years: int = 10,
    erp: float = DEFAULT_ERP,
    tax_rate: float = DEFAULT_TAX_RATE,
) -> dict[str, Any]:
    derived = statements.get("derived", {}) if statements else {}
    shares = derived.get("shares")
    net_debt = derived.get("net_debt") or 0.0
    total_debt = derived.get("total_debt")

    base_fcf, base_method = _normalized_base_fcf(statements)
    if not base_fcf or base_fcf <= 0 or not shares or shares <= 0:
        return {"available": False,
                "reason": "Insufficient EDGAR data (need positive normalised FCF + shares)."}

    # Clamp the high-growth rate to a defensible band.
    stage1 = max(0.0, min(0.25, stage1_growth))
    terminal = max(0.0, min(0.04, terminal_growth))

    discount, wacc_components = _compute_wacc(
        market_cap, total_debt, beta, risk_free, erp, tax_rate)

    base = _value(base_fcf, stage1, terminal, discount, high_growth_years, years, net_debt, shares)
    fair_value = base["fair_value"]
    upside = ((fair_value - price) / price * 100.0) if price else None

    # Sensitivity: fair value across +/- WACC and +/- terminal growth.
    wacc_axis = [round(discount + d, 4) for d in (-0.01, 0.0, 0.01)]
    tg_axis = [round(terminal + d, 4) for d in (-0.005, 0.0, 0.005)]
    grid = [[round(_value(base_fcf, stage1, tg, w, high_growth_years, years,
                          net_debt, shares)["fair_value"], 2)
             for tg in tg_axis] for w in wacc_axis]

    return {
        "available": True,
        "assumptions": {
            "base_fcf": base_fcf,
            "base_fcf_method": base_method,
            "stage1_growth": stage1,
            "terminal_growth": terminal,
            "discount": round(discount, 4),
            "wacc_components": wacc_components,
            "high_growth_years": high_growth_years,
            "years": years,
            "shares": shares,
            "net_debt": net_debt,
        },
        "projection": base["projection"],
        "terminal_value": base["terminal_value"],
        "pv_terminal": base["pv_terminal"],
        "enterprise_value": base["enterprise_value"],
        "equity_value": base["equity_value"],
        "fair_value": round(fair_value, 2),
        "current_price": price,
        "upside_pct": round(upside, 1) if upside is not None else None,
        "sensitivity": {"wacc": wacc_axis, "terminal_growth": tg_axis, "grid": grid},
    }


def to_xlsx(ticker: str, dcf: dict[str, Any]) -> bytes:
    """Render the DCF as a downloadable .xlsx with a live (formula-driven) projection."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = Workbook()
    ws = wb.active
    ws.title = "DCF"
    a = dcf["assumptions"]
    wc = a.get("wacc_components", {})
    yrs = a["years"]

    bold = Font(bold=True)
    header_fill = PatternFill("solid", fgColor="1F2937")
    white_bold = Font(bold=True, color="FFFFFF")

    ws["A1"] = f"{ticker} — Discounted Cash Flow (two-stage)"
    ws["A1"].font = Font(bold=True, size=14)

    # --- Assumptions block (B-cells are the live inputs the projection references) --
    ws["A3"] = "Assumptions"; ws["A3"].font = bold
    assumptions = [
        ("Base free cash flow", a["base_fcf"]),              # B4
        ("  (basis)", a.get("base_fcf_method", "")),         # B5
        ("Stage-1 FCF growth", a["stage1_growth"]),          # B6
        ("High-growth years", a["high_growth_years"]),       # B7
        ("Terminal growth", a["terminal_growth"]),           # B8
        ("Discount rate (WACC)", a["discount"]),             # B9
        ("Projection years", yrs),                           # B10
        ("Shares outstanding", a["shares"]),                 # B11
        ("Net debt", a["net_debt"]),                         # B12
    ]
    for i, (label, val) in enumerate(assumptions, start=4):
        ws[f"A{i}"] = label
        ws[f"B{i}"] = val
    g1_ref, hy_ref, tg_ref, disc_ref = "$B$6", "$B$7", "$B$8", "$B$9"
    shares_ref, netdebt_ref = "$B$11", "$B$12"

    # --- WACC derivation (transparency) -----------------------------------------
    ws["A14"] = "WACC build-up"; ws["A14"].font = bold
    wacc_rows = [
        ("Method", wc.get("method", "")),
        ("Risk-free (10Y)", wc.get("risk_free")),
        ("Beta", wc.get("beta")),
        ("Equity risk premium", wc.get("erp")),
        ("Cost of equity", wc.get("cost_of_equity")),
        ("Cost of debt (after tax)", wc.get("cost_of_debt_after_tax")),
        ("Equity / Debt weight", f"{wc.get('equity_weight','—')} / {wc.get('debt_weight','—')}"),
    ]
    for i, (label, val) in enumerate(wacc_rows, start=15):
        ws[f"A{i}"] = label
        ws[f"B{i}"] = val

    # --- Projection table (live formulas) ---------------------------------------
    start = 24
    ws[f"A{start}"] = "Year"; ws[f"B{start}"] = "Growth"
    ws[f"C{start}"] = "Projected FCF"; ws[f"D{start}"] = "PV of FCF"
    for c in ("A", "B", "C", "D"):
        ws[f"{c}{start}"].font = white_bold
        ws[f"{c}{start}"].fill = header_fill
        ws[f"{c}{start}"].alignment = Alignment(horizontal="center")

    prev_fcf_cell = "$B$4"  # base FCF
    for n in range(1, yrs + 1):
        r = start + n
        ws[f"A{r}"] = n
        # Two-stage growth: stage-1 through high-growth years, then linear fade to terminal.
        ws[f"B{r}"] = (
            f"=IF(A{r}<={hy_ref},{g1_ref},"
            f"{g1_ref}+({tg_ref}-{g1_ref})*(A{r}-{hy_ref})/({yrs}-{hy_ref}))"
        )
        ws[f"C{r}"] = f"={prev_fcf_cell}*(1+B{r})"
        ws[f"D{r}"] = f"=C{r}/((1+{disc_ref})^A{r})"
        prev_fcf_cell = f"$C${r}"

    last = start + yrs
    tv = last + 2
    ws[f"A{tv}"] = "Terminal value"
    ws[f"B{tv}"] = f"=C{last}*(1+{tg_ref})/({disc_ref}-{tg_ref})"
    ws[f"A{tv+1}"] = "PV of terminal value"
    ws[f"B{tv+1}"] = f"=B{tv}/((1+{disc_ref})^{yrs})"
    ws[f"A{tv+2}"] = "Enterprise value"
    ws[f"B{tv+2}"] = f"=SUM(D{start+1}:D{last})+B{tv+1}"
    ws[f"A{tv+3}"] = "Equity value"
    ws[f"B{tv+3}"] = f"=B{tv+2}-{netdebt_ref}"
    ws[f"A{tv+4}"] = "Fair value / share"
    ws[f"B{tv+4}"] = f"=B{tv+3}/{shares_ref}"
    ws[f"A{tv+4}"].font = bold; ws[f"B{tv+4}"].font = bold
    ws[f"A{tv+5}"] = "Current price"
    ws[f"B{tv+5}"] = dcf.get("current_price")
    ws[f"A{tv+6}"] = "Upside / downside"
    ws[f"B{tv+6}"] = f"=B{tv+4}/B{tv+5}-1"
    ws[f"B{tv+6}"].number_format = "0.0%"

    # --- Sensitivity grid (computed values; WACC down rows x terminal growth cols) --
    sens = dcf.get("sensitivity") or {}
    if sens.get("grid"):
        s = tv + 8
        ws[f"A{s}"] = "Sensitivity — fair value / share"; ws[f"A{s}"].font = bold
        ws[f"A{s+1}"] = "WACC \\ term. g"
        for j, tgv in enumerate(sens["terminal_growth"]):
            cell = ws.cell(row=s + 1, column=2 + j, value=tgv)
            cell.number_format = "0.0%"; cell.font = white_bold; cell.fill = header_fill
        for i, wv in enumerate(sens["wacc"]):
            wcell = ws.cell(row=s + 2 + i, column=1, value=wv)
            wcell.number_format = "0.0%"; wcell.font = white_bold; wcell.fill = header_fill
            for j, fv in enumerate(sens["grid"][i]):
                ws.cell(row=s + 2 + i, column=2 + j, value=fv).number_format = "$#,##0.00"

    ws.column_dimensions["A"].width = 28
    for col in ("B", "C", "D"):
        ws.column_dimensions[col].width = 20

    note_row = (tv + 8) + (len(sens.get("wacc", [])) + 3 if sens.get("grid") else 1)
    ws[f"A{note_row}"] = ("Two-stage DCF — generated by Public Company Analyser. "
                          "Research only, not financial advice.")

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
