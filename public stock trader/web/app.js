"use strict";

const $ = (id) => document.getElementById(id);
const GAUGE_C = 2 * Math.PI * 52;

/* ---- formatting helpers ---- */
function scoreColor(s) { return `hsl(${Math.max(0, Math.min(100, s)) / 100 * 140}, 70%, 52%)`; }

function fmtMoney(v) {
  if (v == null || isNaN(v)) return "—";
  const a = Math.abs(v), sign = v < 0 ? "-" : "";
  if (a >= 1e12) return `${sign}$${(a / 1e12).toFixed(2)}T`;
  if (a >= 1e9) return `${sign}$${(a / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `${sign}$${(a / 1e6).toFixed(1)}M`;
  return `${sign}$${a.toLocaleString()}`;
}
function fmtMetric(v, fmt) {
  if (v == null || isNaN(v)) return null;
  switch (fmt) {
    case "x": return v.toFixed(2) + "×";
    case "%": return v.toFixed(1) + "%";
    case "money": return fmtMoney(v);
    case "price": return "$" + v.toFixed(2);
    default: return String(v);
  }
}
function signClass(v) { return v > 0 ? "pos" : v < 0 ? "neg" : ""; }
function colorFor(v) { return v > 0 ? "var(--green)" : v < 0 ? "var(--red)" : "var(--muted)"; }

const RATING_STYLE = {
  "Strong Buy": ["rgba(31,209,122,0.20)", "#3ce58e", "rgba(31,209,122,0.5)"],
  "Buy": ["rgba(31,209,122,0.12)", "#1fd17a", "rgba(31,209,122,0.35)"],
  "Hold": ["rgba(230,181,60,0.14)", "#e6b53c", "rgba(230,181,60,0.4)"],
  "Sell": ["rgba(255,77,87,0.12)", "#ff6a72", "rgba(255,77,87,0.35)"],
  "Strong Sell": ["rgba(255,77,87,0.20)", "#ff4d57", "rgba(255,77,87,0.5)"],
};

function setStatus(html, err = false) {
  const el = $("status"); el.className = "status" + (err ? " error" : "");
  el.innerHTML = html; el.classList.remove("hidden");
}
const clearStatus = () => $("status").classList.add("hidden");

/* ---- cursor-tracked glass specular ---- */
function bindGlass() {
  document.querySelectorAll(".panel").forEach((p) => {
    if (p.dataset.glass) return;
    p.dataset.glass = "1";
    p.addEventListener("pointermove", (e) => {
      const r = p.getBoundingClientRect();
      p.style.setProperty("--mx", ((e.clientX - r.left) / r.width * 100) + "%");
      p.style.setProperty("--my", ((e.clientY - r.top) / r.height * 100) + "%");
    });
  });
}

/* ---- renderers ---- */
function renderVerdict(d) {
  const s = d.sections, p = s.profile || {}, px = s.price || {};
  $("company-name").textContent = d.company_name;
  $("ticker-chip").textContent = d.ticker;
  $("industry").textContent = p.industry ? "· " + p.industry : "";
  const logo = $("logo"), logoTile = $("logo-tile");
  logo.onload = () => logoTile.classList.remove("hidden");                       // a successful load always wins
  logo.onerror = () => { if (!logo.naturalWidth) logoTile.classList.add("hidden"); };  // hide only if truly broken
  if (p.logo) { logoTile.classList.remove("hidden"); logo.src = p.logo; } else logoTile.classList.add("hidden");

  $("price").textContent = px.current != null ? "$" + px.current.toFixed(2) : "—";
  const pc = $("price-change");
  if (px.change != null) {
    pc.textContent = `${px.change >= 0 ? "+" : ""}${px.change.toFixed(2)} (${px.change_pct >= 0 ? "+" : ""}${(px.change_pct || 0).toFixed(2)}%)`;
    pc.style.color = colorFor(px.change);
  } else pc.textContent = "";

  const badge = $("rating-badge"); badge.textContent = d.rating;
  const [bg, fg, br] = RATING_STYLE[d.rating] || RATING_STYLE["Hold"];
  badge.style.background = bg; badge.style.color = fg; badge.style.border = "1px solid " + br;

  const arc = $("gauge-arc");
  arc.style.stroke = scoreColor(d.composite);
  arc.style.strokeDashoffset = GAUGE_C;
  requestAnimationFrame(() => { arc.style.strokeDashoffset = GAUGE_C * (1 - d.composite / 100); });
  animateNumber($("composite-score"), d.composite);
}

const REC_COLORS = { strongBuy: "#1fd17a", buy: "#6fe0a6", hold: "#e6b53c", sell: "#ff8a8a", strongSell: "#ff4d57" };
const REC_LABELS = { strongBuy: "Strong Buy", buy: "Buy", hold: "Hold", sell: "Sell", strongSell: "Strong Sell" };

function renderAnalyst(a) {
  const wrap = $("analyst-wrap");
  if (!a || !a.available) { wrap.classList.add("hidden"); return; }
  wrap.classList.remove("hidden");
  const c = a.counts, total = a.total_analysts;
  const segs = Object.keys(REC_COLORS).map((k) =>
    `<span style="width:${(c[k] / total * 100) || 0}%;background:${REC_COLORS[k]}"></span>`).join("");
  const legend = Object.keys(REC_COLORS).map((k) =>
    `<span><i style="background:${REC_COLORS[k]}"></i>${REC_LABELS[k]} ${c[k]}</span>`).join("");
  const pt = a.price_target || {};
  const ptHtml = pt.mean ? `
    <div class="kv"><span class="k">Target (mean)</span><span class="v">$${pt.mean.toFixed(2)}</span></div>
    <div class="kv"><span class="k">Range</span><span class="v">$${(pt.low||0).toFixed(0)}–$${(pt.high||0).toFixed(0)}</span></div>
    <div class="kv"><span class="k">Implied upside</span><span class="v" style="color:${colorFor(pt.upside_pct)}">${pt.upside_pct != null ? (pt.upside_pct>=0?"+":"")+pt.upside_pct+"%" : "—"}</span></div>`
    : `<div class="kv"><span class="k">Price target</span><span class="v muted">n/a (free tier)</span></div>`;

  const srcTag = a.source ? `<span class="src-tag">via ${a.source}</span>` : "";

  // Named top-player ratings (FMP only). Finnhub fallback can't name firms.
  const firms = a.firm_ratings || [];
  const firmsHtml = firms.length ? `
    <div class="firm-ratings">
      <div class="fr-title muted small">Top-firm ratings <span class="muted">— latest call per house</span></div>
      <div class="fr-list">
        ${firms.map((f) => `
          <div class="fr-row">
            <span class="fr-firm">${f.firm}</span>
            <span class="fr-grade" style="color:${REC_COLORS[f.bucket] || "var(--muted)"}">${f.grade || "—"}</span>
            <span class="fr-date muted small">${f.date || ""}</span>
          </div>`).join("")}
      </div>
    </div>`
    : (a.source === "Finnhub"
        ? `<div class="fr-note muted small">Add an FMP key to name the firms — showing Finnhub's anonymized counts.</div>`
        : "");

  $("analyst").innerHTML = `
    <div class="analyst-top">
      <div class="consensus-main">
        <span class="consensus-label" style="color:${scoreColor(a.consensus_score)}">${a.consensus_label}</span>
        <span class="muted small">${total} analysts · ${a.period || ""} ${srcTag}</span>
      </div>
      <div style="flex:1;min-width:260px">
        <div class="dist">${segs}</div>
        <div class="dist-legend">${legend}</div>
      </div>
      <div class="pt">${ptHtml}</div>
    </div>
    ${firmsHtml}`;
}

function renderChart(sec) {
  const host = $("chart-host");
  host.innerHTML = "";
  const note = $("chart-note");
  // Finnhub daily candles need a premium plan; use a TradingView widget for a reliable, live chart.
  const sym = sec.symbol;
  const div = document.createElement("div");
  div.id = "tv_" + sym; div.style.height = "100%";
  host.appendChild(div);
  const make = () => new TradingView.widget({
    autosize: true, symbol: sym, interval: "D", timezone: "Etc/UTC",
    theme: "dark", style: "3", locale: "en", hide_top_toolbar: false,
    hide_legend: false, allow_symbol_change: false, save_image: false,
    backgroundColor: "rgba(8,10,16,1)", container_id: div.id,
  });
  if (window.TradingView) make();
  else {
    const sc = document.createElement("script");
    sc.src = "https://s3.tradingview.com/tv.js"; sc.onload = make;
    sc.onerror = () => { note.textContent = "Chart unavailable (could not load chart widget)."; };
    document.head.appendChild(sc);
  }
  note.textContent = "Live chart via TradingView. (Finnhub daily candles require a premium plan.)";
}

function renderEarnings(e) {
  const wrap = $("earnings-wrap");
  if (!e || (!e.past?.length && !e.next?.date)) { wrap.classList.add("hidden"); return; }
  wrap.classList.remove("hidden");
  const next = e.next || {};
  const nextHtml = next.date ? `
    <div class="next-earn">
      <div class="lbl">Next earnings</div>
      <div class="date">${next.date}</div>
      <div class="muted small">${next.hour ? next.hour.toUpperCase() + " · " : ""}EPS est ${next.eps_estimate != null ? "$" + next.eps_estimate.toFixed(2) : "—"}</div>
    </div>` : `<div class="next-earn"><div class="lbl">Next earnings</div><div class="date muted" style="font-size:16px">Not available</div></div>`;

  const rows = (e.past || []).map((q) => `
    <div class="earn-row">
      <span>${q.period || "—"}</span>
      <span class="r">${q.actual != null ? "$" + q.actual.toFixed(2) : "—"}</span>
      <span class="r muted">${q.estimate != null ? "$" + q.estimate.toFixed(2) : "—"}</span>
      <span class="r" style="color:${colorFor(q.surprise_pct)}">${q.surprise_pct != null ? (q.surprise_pct>=0?"+":"")+q.surprise_pct.toFixed(1)+"%" : "—"}</span>
    </div>`).join("");
  const table = rows ? `
    <div class="earn-table">
      <div class="earn-row head"><span>Quarter</span><span class="r">Actual</span><span class="r">Estimate</span><span class="r">Surprise</span></div>
      ${rows}
    </div>` : "";
  $("earnings").innerHTML = nextHtml + table;
}

function renderValuation(list) {
  const wrap = $("valuation-wrap");
  if (!list || !list.length) { wrap.classList.add("hidden"); return; }
  wrap.classList.remove("hidden");
  const groups = {};
  list.forEach((m) => { (groups[m.group] = groups[m.group] || []).push(m); });
  $("valuation").innerHTML = Object.entries(groups).map(([g, items]) => `
    <div class="metric-group">
      <h4>${g}</h4>
      <div class="metric-grid">
        ${items.map((m) => {
          const val = fmtMetric(m.value, m.fmt);
          return `<div class="metric"><div class="ml">${m.label}</div><div class="mv ${val ? "" : "na"}">${val || "n/a"}</div></div>`;
        }).join("")}
      </div>
    </div>`).join("");
}

function renderFinancials(f) {
  const wrap = $("financials-wrap");
  if (!f || !f.years?.length) { wrap.classList.add("hidden"); return; }
  wrap.classList.remove("hidden");
  const head = `<thead><tr><th>USD</th>${f.years.map((y) => `<th>FY${String(y).slice(2)}</th>`).join("")}</tr></thead>`;
  const body = f.groups.map((g) => {
    const grp = `<tr class="grp"><td colspan="${f.years.length + 1}">${g.name}</td></tr>`;
    const rows = g.rows.map((r) => `<tr class="line"><td>${r.label}</td>${
      r.values.map((v) => `<td>${v == null ? "—" : (r.unit === "pershare" ? "$" + v.toFixed(2) : fmtMoney(v))}</td>`).join("")
    }</tr>`).join("");
    return grp + rows;
  }).join("");
  $("financials").innerHTML = `<table class="fin-table">${head}<tbody>${body}</tbody></table>`;
}

function renderDcf(dcf, ticker) {
  const wrap = $("dcf-wrap");
  if (!dcf) { wrap.classList.add("hidden"); return; }
  wrap.classList.remove("hidden");
  if (!dcf.available) {
    $("dcf").innerHTML = `<div class="muted">DCF unavailable — ${dcf.reason || "insufficient data"}.</div>`;
    return;
  }
  const a = dcf.assumptions, wc = a.wacc_components || {};
  const pct = (v) => v != null ? (v * 100).toFixed(1) + "%" : "—";

  const waccLine = wc.cost_of_equity != null
    ? `WACC <strong>${pct(a.discount)}</strong> = ${pct(wc.equity_weight)} equity @ ${pct(wc.cost_of_equity)}
       (β ${wc.beta ?? "—"}, rf ${pct(wc.risk_free)}) + ${pct(wc.debt_weight)} debt @ ${pct(wc.cost_of_debt_after_tax)} after-tax`
    : `WACC <strong>${pct(a.discount)}</strong> <span class="muted">(default — market cap unavailable)</span>`;

  // Sensitivity grid: WACC down the rows, terminal growth across the columns.
  const sv = dcf.sensitivity;
  let sensHtml = "";
  if (sv && sv.grid) {
    const head = sv.terminal_growth.map((g) => `<th>g ${pct(g)}</th>`).join("");
    const rows = sv.grid.map((row, i) => {
      const cells = row.map((fv) => {
        const up = dcf.current_price ? (fv - dcf.current_price) / dcf.current_price : 0;
        return `<td style="color:${colorFor(up)}">$${fv.toFixed(2)}</td>`;
      }).join("");
      return `<tr><th>WACC ${pct(sv.wacc[i])}</th>${cells}</tr>`;
    }).join("");
    sensHtml = `
      <div class="dcf-sens">
        <div class="dcf-sens-title muted small">Sensitivity — fair value / share</div>
        <table class="sens-table"><thead><tr><th></th>${head}</tr></thead><tbody>${rows}</tbody></table>
      </div>`;
  }

  $("dcf").innerHTML = `
    <div class="dcf-headline">
      <div class="kv"><span class="k">Fair value / share</span><span class="v">$${dcf.fair_value.toFixed(2)}</span></div>
      <div class="kv"><span class="k">Current price</span><span class="v">${dcf.current_price != null ? "$" + dcf.current_price.toFixed(2) : "—"}</span></div>
      <div class="kv"><span class="k">Upside / downside</span><span class="v" style="color:${colorFor(dcf.upside_pct)}">${dcf.upside_pct != null ? (dcf.upside_pct>=0?"+":"")+dcf.upside_pct+"%" : "—"}</span></div>
    </div>
    <div class="dcf-assume">
      Base FCF ${fmtMoney(a.base_fcf)} <span class="muted">(${a.base_fcf_method})</span> ·
      stage-1 growth ${pct(a.stage1_growth)} for ${a.high_growth_years}y, fading to ${pct(a.terminal_growth)} terminal over ${a.years}y
    </div>
    <div class="dcf-assume">${waccLine}</div>
    ${sensHtml}
    <a class="dl-btn" href="/api/dcf/${ticker}.xlsx" download>⬇ Download DCF (.xlsx)</a>`;
}

function renderFilings(sec) {
  const wrap = $("filings-wrap");
  const p = sec.profile || {}, filings = sec.filings || [];
  if (!p.ir_website && !filings.length) { wrap.classList.add("hidden"); return; }
  wrap.classList.remove("hidden");
  const ir = p.ir_website ? `<div class="ir-link">Investor relations: <a href="${p.ir_website}" target="_blank" rel="noopener">${p.ir_website}</a></div>` : "";
  const list = filings.length ? `<div class="filing-list">${
    filings.map((f) => `<div class="filing"><span class="form">${f.form}</span><span class="date">${f.date || ""}</span><span>${f.url ? `<a href="${f.url}" target="_blank" rel="noopener">View filing ↗</a>` : ""}</span></div>`).join("")
  }</div>` : "";
  $("filings").innerHTML = ir + list;
}

function scoreCard(label, value, sub, color) {
  return `<div class="score-card" style="--c:${color}">
    <div class="sc-label">${label}</div>
    <div class="sc-value">${value}</div>
    <div class="sc-sub muted">${sub || ""}</div>
  </div>`;
}

function renderScores(q) {
  const wrap = $("scores-wrap");
  if (!q || !Object.keys(q).length) { wrap.classList.add("hidden"); return; }
  const cards = [];
  const pio = q.piotroski;
  if (pio?.available) {
    const c = pio.score >= 7 ? "var(--green)" : pio.score <= 3 ? "var(--red)" : "var(--amber)";
    const chips = pio.checks.map((k) => `<span class="chk ${k.pass ? "ok" : "no"}" title="${k.name}"></span>`).join("");
    cards.push(`<div class="score-card" style="--c:${c}"><div class="sc-label">Piotroski F-Score</div>
      <div class="sc-value">${pio.score}<small>/9</small></div>
      <div class="sc-chips">${chips}</div><div class="sc-sub muted">${pio.verdict} fundamentals</div></div>`);
  }
  const alt = q.altman;
  if (alt?.available) {
    const c = alt.zone === "Safe" ? "var(--green)" : alt.zone === "Distress" ? "var(--red)" : "var(--amber)";
    cards.push(scoreCard("Altman Z-Score", alt.z, alt.zone + " · bankruptcy risk", c));
  }
  const ben = q.beneish;
  if (ben?.available) {
    const c = ben.m > -1.78 ? "var(--red)" : "var(--green)";
    cards.push(scoreCard("Beneish M-Score", ben.m, ben.flag, c));
  }
  const eq = q.earnings_quality;
  if (eq?.available && eq.fcf_to_ni != null) {
    const c = eq.fcf_to_ni >= 1 ? "var(--green)" : eq.fcf_to_ni < 0.7 ? "var(--red)" : "var(--amber)";
    cards.push(scoreCard("Earnings quality", eq.fcf_to_ni + "×", "Free cash flow ÷ net income", c));
  }
  const sy = q.shareholder_yield;
  if (sy?.available) {
    cards.push(scoreCard("Shareholder yield", sy.yield_pct + "%", "Dividends + buybacks", "var(--green)"));
  }
  const ds = q.dividend_safety;
  if (ds?.available && ds.payout_ratio != null) {
    const c = ds.payout_ratio < 0.6 ? "var(--green)" : ds.payout_ratio > 0.9 ? "var(--red)" : "var(--amber)";
    cards.push(scoreCard("Dividend safety", Math.round(ds.payout_ratio * 100) + "%", `payout · FCF cover ${ds.fcf_coverage ?? "—"}×`, c));
  }
  if (!cards.length) { wrap.classList.add("hidden"); return; }
  wrap.classList.remove("hidden");
  $("scores").innerHTML = cards.join("");
}

async function fetchNews(ticker) {
  const wrap = $("news-wrap"), host = $("news");
  wrap.classList.remove("hidden");
  host.innerHTML = `<div class="muted"><span class="spinner"></span> Searching the web for recent news…</div>`;
  try {
    const r = await fetch(`/api/news/${encodeURIComponent(ticker)}`);
    const d = await r.json();
    if (!d.available) { host.innerHTML = `<div class="muted">${d.note || "No news available."}</div>`; return; }
    host.innerHTML = d.items.map((it) => `
      <div class="news-item">
        <div class="news-head">
          <a href="${it.url}" target="_blank" rel="noopener">${it.title}</a>
          <span class="news-meta muted">${[it.source, it.date].filter(Boolean).join(" · ")}</span>
        </div>
        <ul class="news-bullets">${(it.bullets || []).map((b) => `<li>${b}</li>`).join("")}</ul>
      </div>`).join("");
  } catch (e) {
    host.innerHTML = `<div class="muted">News unavailable: ${e.message}</div>`;
  }
}

function renderPillars(pillars) {
  $("pillars").innerHTML = "";
  pillars.forEach((p) => {
    const card = document.createElement("div"); card.className = "pillar";
    const color = scoreColor(p.score);
    const factors = p.factors.map((f) => `
      <div class="factor ${f.available ? "" : "na"}" title="${f.detail}">
        <span class="fname">${f.name}</span>
        <span class="fbar"><span style="width:${f.score}%;background:${scoreColor(f.score)}"></span></span>
        <span class="fval">${Math.round(f.score)}</span>
      </div>`).join("");
    card.innerHTML = `
      <div class="pillar-head">
        <div><div class="name">${p.title}</div><div class="weight">weight ${Math.round(p.weight*100)}% · coverage ${Math.round(p.coverage*100)}%</div></div>
        <div class="pscore" style="color:${color}">${Math.round(p.score)}</div>
      </div>
      <div class="bar"><div class="bar-fill" style="background:${color}"></div></div>
      <div class="factors">${factors}</div>`;
    $("pillars").appendChild(card);
    requestAnimationFrame(() => { card.querySelector(".bar-fill").style.width = p.score + "%"; });
  });
}

function renderResult(d) {
  const s = d.sections || {};
  renderVerdict(d);
  renderAnalyst(s.recommendations);
  renderChart(s.chart || { symbol: d.ticker });
  renderEarnings(s.earnings);
  renderValuation(s.valuation);
  renderFinancials(s.financials);
  renderDcf(s.dcf, d.ticker);
  renderFilings(s);
  renderScores(s.quant_scores);
  renderPillars(d.pillars);
  fetchNews(d.ticker);

  $("sources").innerHTML = (d.data_sources || []).map((x) => `<span>${x}</span>`).join("") || "<span>—</span>";
  const ww = $("warnings-wrap");
  if (d.warnings?.length) { $("warnings").innerHTML = d.warnings.map((w) => `<li>${w}</li>`).join(""); ww.classList.remove("hidden"); }
  else ww.classList.add("hidden");

  $("result").classList.remove("hidden");
  bindGlass();
}

function animateNumber(el, target) {
  const dur = 900, start = performance.now();
  function step(now) {
    const t = Math.min(1, (now - start) / dur), e = 1 - Math.pow(1 - t, 3);
    el.textContent = (target * e).toFixed(1);
    if (t < 1) requestAnimationFrame(step); else el.textContent = target.toFixed(1);
  }
  requestAnimationFrame(step);
}

async function run(ticker) {
  $("result").classList.add("hidden");
  setStatus(`<span class="spinner"></span> Analyzing <strong>${ticker}</strong> — SEC filings, fundamentals, estimates, DCF…`);
  $("go").disabled = true;
  try {
    const resp = await fetch(`/api/analyze/${encodeURIComponent(ticker)}`);
    const body = await resp.json();
    if (!resp.ok) throw new Error(body.detail || "Request failed");
    clearStatus();
    renderResult(body);
  } catch (err) {
    setStatus(`Could not analyze ${ticker}: ${err.message}`, true);
  } finally { $("go").disabled = false; }
}

$("search").addEventListener("submit", (e) => {
  e.preventDefault();
  const t = $("ticker").value.trim().toUpperCase();
  if (t) run(t);
});
bindGlass();
