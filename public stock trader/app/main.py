"""FastAPI app: JSON analysis endpoint + serves the dark-glass web UI."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app import dcf as dcf_model
from app import news as news_mod
from app import statements
from app.analyzer import analyze
from app.connectors import edgar, finnhub, fred

_WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Public Company Analyser", version="1.0")


def _clean_ticker(ticker: str) -> str:
    ticker = ticker.strip().upper()
    if not ticker.isalnum() or len(ticker) > 8:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol.")
    return ticker


@app.get("/api/analyze/{ticker}")
def api_analyze(ticker: str) -> JSONResponse:
    ticker = _clean_ticker(ticker)
    try:
        result = analyze(ticker)
    except Exception as exc:  # surface failures as JSON, not a 500 page
        raise HTTPException(status_code=502, detail=str(exc))
    return JSONResponse(result.to_dict())


@app.get("/api/news/{ticker}")
def api_news(ticker: str) -> JSONResponse:
    """LLM news desk (Claude web search). Separate endpoint so the main analysis
    renders instantly while news loads in the background."""
    ticker = _clean_ticker(ticker)
    name = finnhub.profile(ticker).get("name") or ticker
    return JSONResponse(news_mod.fetch(name, ticker))


@app.get("/api/candles/{ticker}")
def api_candles(ticker: str, days: int = 365) -> JSONResponse:
    """Daily OHLC from Finnhub (empty on free tier -> UI uses a chart widget)."""
    ticker = _clean_ticker(ticker)
    return JSONResponse(finnhub.candles(ticker, days=days))


@app.get("/api/dcf/{ticker}.xlsx")
def api_dcf_download(ticker: str) -> Response:
    """Build the DCF model from EDGAR fundamentals and return a downloadable .xlsx."""
    ticker = _clean_ticker(ticker)
    cik = edgar.cik_for(ticker)
    if not cik:
        raise HTTPException(status_code=404, detail="No SEC filings found for this ticker.")
    stmt = statements.build(edgar.company_facts(cik))
    price = finnhub.quote(ticker).get("c")
    dcf = dcf_model.compute(
        stmt,
        price,
        **dcf_model.inputs_from_market_data(
            finnhub.profile(ticker), finnhub.metrics(ticker), fred.snapshot()),
    )
    if not dcf.get("available"):
        raise HTTPException(status_code=422, detail=dcf.get("reason", "DCF unavailable."))
    blob = dcf_model.to_xlsx(ticker, dcf)
    return Response(
        content=blob,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{ticker}_DCF.xlsx"'},
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_WEB_DIR / "index.html")


# Static assets (style.css, app.js).
app.mount("/static", StaticFiles(directory=_WEB_DIR), name="static")
