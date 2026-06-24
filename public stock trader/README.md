# Public Company Analyser

Feed it a ticker, get a **Strong Buy → Strong Sell** rating.

The headline verdict is the **average of Wall Street analyst ratings** (the consensus
score, sourced from FMP's named-firm ratings). The eight-pillar scorecard is still
computed and shown for reference — and remains the fallback rating for tickers with no
analyst coverage — but it no longer sets the headline number. Claude is used **only** to
find and summarize recent news; it does **not** set the score.

## Pillars & weights

| Pillar | Weight | Signals |
|---|---|---|
| Valuation | 18% | P/E, P/S, P/FCF, P/B |
| Growth | 15% | Revenue & EPS growth, 5Y CAGR |
| Profitability / Quality | 15% | Margins, ROE, ROIC |
| Financial Health | 12% | Current ratio, debt/equity, interest coverage |
| Estimates & Revisions | 15% | Analyst consensus, price-target upside, earnings surprise |
| Momentum / Technicals | 10% | 52-week range position, relative strength, 12-month return |
| Sentiment | 8% | Analyst rating momentum, news flow (tone via AI) |
| Ownership | 7% | Insider net buying/selling |

Tune the weights in [`config.py`](config.py) — they must sum to 1.0.

## What you get per ticker

- **Verdict** — average of Wall Street analyst ratings (0–100 gauge) + live price
- **Wall Street consensus** — named ratings from the major research houses (Goldman, Morgan Stanley, JPMorgan, BofA, …) with the latest call per firm, the distribution, and a price target — via **Financial Modeling Prep**, falling back to Finnhub's anonymized counts if FMP is unavailable. *Not* from the LLM
- **News & catalysts** — Claude searches the web for the most important recent news, summarizes it in concise bullets, and links the source article *(needs `ANTHROPIC_API_KEY`)*
- **Forensic & quality scores** — Piotroski F, Altman Z, Beneish M, earnings quality, shareholder yield, dividend safety (computed from EDGAR; the F-score and Z-score also feed the rating)
- **Price chart** — live (TradingView; Finnhub daily candles need a premium plan)
- **Earnings** — past surprises + next earnings date
- **Valuation & quality** — 20+ metrics incl. EV/EBITDA & EV/Sales (derived from EDGAR + market cap)
- **SEC financial statements** — multi-year income / balance / cash-flow from EDGAR XBRL
- **DCF** — a real two-stage model: normalised base FCF (3-year average), company-specific WACC (CAPM cost of equity + after-tax cost of debt, market-weighted), high-growth plateau fading to a terminal rate over a 10-year horizon, plus a WACC × terminal-growth sensitivity grid. Downloadable `.xlsx` keeps the projection live (formulas)
- **Filings & IR** — company IR site link + recent 10-K/10-Q/8-K with EDGAR links
- **Scorecard** — the eight pillars driving the rating

## Data sources

- **Finnhub** — prices, fundamentals, estimates, earnings, news, insiders *(required; free key)*
- **Financial Modeling Prep** — named analyst ratings + price targets for the consensus panel *(optional; falls back to Finnhub's anonymized recommendation counts)*
- **SEC EDGAR** — filings & XBRL financial statements *(free, no key; needs a User-Agent)*
- **FRED** — macro context *(optional; free key)*
- **Claude** — AI news desk only *(optional; never sets the rating)*

> Seeking Alpha transcripts and the Massive unblocker were dropped — SA's bot protection made it unreliable. The IR/filings section uses public EDGAR + the company IR link instead.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # then paste in your keys (Finnhub is the only required one)
```

## Run

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 and type a ticker.

Endpoints:
- `GET /api/analyze/{ticker}` — full scorecard + sections
- `GET /api/news/{ticker}` — AI news desk (loads separately so the page renders instantly)
- `GET /api/dcf/{ticker}.xlsx` — download the DCF model as Excel
- `GET /api/candles/{ticker}` — Finnhub daily candles (empty on the free tier)

## Notes

- Responses are cached in `cache.db` (12h) to respect free-tier rate limits and keep runs reproducible.
- Some Finnhub endpoints (price targets, insider transactions) are gated on the free tier; those factors fall back to a neutral score and the pillar's **coverage** drops to show it.
- v2 ideas: per-sector percentile normalisation, Altman-Z / Piotroski-F / Beneish-M from EDGAR XBRL, 13F institutional flows, alternative data.
