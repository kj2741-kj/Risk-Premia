"""Builds Analysis/Final_Research_Dashboard_2012_<tag>.html (2026-10-31): the 2012-start, three-period research dashboard with the new buckets
(Metals, Petroleum, Power / Emissions / Nat Gas, NGL, Precious, Agriculture). Tag 0930 = data cut at 2026-09-30, tag 1029 = latest data (to 2026-10-29), chosen with the env
var FD_TAG (default 0930; see fd_config.py). Input: outputs/final_dashboard_<tag>/final_v3.json (analyze_v3.py).

TEMPLATE: the committed Analysis/Final_Research_Dashboard_2012.html (the page as last published, 2026-10-18). That page was edited by hand after build_final_dashboard_v2.py
produced it (heading, hidden "All 5" tabs, no roll-calendar notes), and build_final_dashboard_v2.py no longer compiles, so the layout, CSS, KaTeX and JavaScript are taken from the
published page and only the pieces that depend on the buckets, the dates or the data are replaced here (every replacement is asserted to match exactly once).
Run from the repo root:  FD_TAG=1029 python scripts/final_dashboard/build_final_dashboard_v3.py"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "scripts/final_dashboard")
from fd_config import TAGS, current_tag, out_dir, check_run

TAG = current_tag()
check_run(TAG)
CFG = TAGS[TAG]
BR = chr(10)     # newline between two <li> items (cosmetic, as in the template)
R = Path(".")
TEMPLATE = R / "Analysis/Final_Research_Dashboard_2012.html"
res = json.load(open(R / out_dir(TAG) / "final_v3.json"))
COLS = [("full", "Full", "2012-2026"), ("p1", "P1", "2012-2016"), ("p2", "P2", "2017-2021"), ("p3", "P3", "2022-2026"), ("y26", "2026", "YTD")]
data = dict(res, cols=[dict(key=k, label=l, years=y) for k, l, y in COLS])

# Liquidity metric, Calendar 2025 (Analysis/Liquidity_Cal2025_results.csv, scripts/liquidity_cal2025.py): L = K / x with K = USD 1M of one-sigma daily risk, shown in the By-product tables
import csv
_liq = {r["product"]: r for r in csv.DictReader(open(R / "Analysis/Liquidity_Cal2025_results.csv", encoding="utf8"))}
for _r in _liq.values():
    assert abs(float(_r["N_contracts_for_K"]) * float(_r["risk_per_contract"]) - 1e6) < 1, ("L is not on K = USD 1M", _r["product"])
_pk = list(res["meta"]["rolls"].keys())
assert all(k.split("|")[1] in _liq for k in _pk), [k for k in _pk if k.split("|")[1] not in _liq]
data["meta"] = dict(res["meta"], liq={k: float(_liq[k.split("|")[1]]["L_strip"]) for k in _pk})

h = TEMPLATE.read_text(encoding="utf8")
m = re.search(r"<script>\nconst D=(.*?);\n", h, re.S)
assert m, "template layout changed: const D= not found"
head_body, tail = h[:m.start()], h[m.end():]          # tail = shared JS helpers + page script (starts at color_js)


def rep(s, old, new):
    assert s.count(old) == 1, (s.count(old), old[:100])
    return s.replace(old, new)


# ---------------- head and body (heading, how-to, Notes tab) ----------------
b = head_body
b = rep(b, "<title>Risk Premia: Final Research Dashboard (2012 start, three periods)</title>", "<title>Risk Premia: Final Research Dashboard (2012 start, three periods, data to " + CFG["cutoff"] + ")</title>")
b = rep(b, "<h1>Risk Premia Analysis Dashbaord</h1>", "<h1>Risk Premia Analysis Dashboard</h1>")
b = rep(b, "Five commodity asset classes, five sleeves each (Momentum, Carry, Carry-Momentum, Value, Skewness), combined by Equal Weight and Inverse Vol only. Log-return methodology, 5 bps costs, reporting from 2012-01-01 in three periods (P1 2012-2016, P2 2017-2021, P3 2022 onwards) plus a 2026 year-to-date column. All price data through 2026-09-23.",
        "Six commodity buckets (Metals, Petroleum, Power / Emissions / Nat Gas, NGL, Precious, Agriculture), five sleeves each (Momentum, Carry, Carry-Momentum, Value, Skewness), combined by Equal Weight and Inverse Vol only. Log-return methodology, 5 bps costs, reporting from 2012-01-01 in three periods (P1 2012-2016, P2 2017-2021, P3 2022 onwards) plus a 2026 year-to-date column. All price data through " + CFG["cutoff"] + ".")
b = rep(b, "one per asset class, plus By Style, Cross-Pair, Correlations and Notes (methods and data).", "one per bucket, plus By Style, Cross-Pair, Correlations and Notes (methods and data).")
b = rep(b, "every control you can change: period, commodity, metric, Energy with or without NatGas.", "every control you can change: period, commodity, metric.")
b = rep(b, "<b>Each asset-class tab</b>", "<b>Each bucket tab</b>")
b = rep(b, "<li>Metals and Energy: F1-F3 and F1-F13. NGL: F2-F4 and F2-F14.</li>",
        "<li>Metals, Petroleum and Nat Gas: F1-F3 and F1-F13. NGL: F2-F4 and F2-F14. TTF: F1-F2 and F1-F13. EUA: F1-F2 and F1-F5 (EUA is quarterly, so F5 is 12 months out; TTF is monthly, so F13 is). TTF F13 is not quoted before 2013-10-04. A pair joins the sum from its own first value, so until then TTF runs on the short pair F1-F2 alone, and the long pair F1-F13 is added when its value first exists: for Carry from 2014-09-25 (the 252-day z-score needs a year of the long slope), for Carry-Momentum from 2013-11-01 (the 20-observation slope change).</li>")
b = rep(b, "This rolls roughly 14 to 16 trading days before expiry for Energy, NGL, Precious and Sugar, about 6 for Metals and about 5 for Corn, Wheat and Soybeans.</li>",
        "Counted from the roll day to the last trade date, this rolls about 5 trading days before expiry for Corn, Wheat, Soybean and Soybean Oil, 6 for Metals, 8 for Coffee, 9 for WTI, 11 for Brent and EUA, 14 for Nat Gas and Precious, 15 for TTF and Sugar, and 16 for RBOB, Heating Oil and NGL.</li>")
b = rep(b, "<li>Products inside a sleeve are equally weighted on common dates",
        "<li>Buckets: Petroleum = WTI, Brent, RBOB, Heating Oil. Power / Emissions / Nat Gas = Henry Hub natural gas (US), TTF natural gas (European, ICE Endex) and EUA carbon (the other power products are not in yet). Metals, NGL, Precious and Agriculture are unchanged.</li>\n<li>Products inside a sleeve are equally weighted on common dates")
b = rep(b, "<li>Each asset-class portfolio combines its five sleeves", "<li>Each bucket portfolio combines its five sleeves")
b = rep(b, "sleeves into an asset-class portfolio, then the five asset-class portfolios into one book; all four EW / Inverse Vol pairs are shown, with and without NatGas. <b>Cross-pair portfolios</b> blend two asset classes' portfolios",
        "sleeves into a bucket portfolio, then the six bucket portfolios into one book; all four EW / Inverse Vol pairs are shown. <b>Cross-pair portfolios</b> blend two buckets' portfolios")
b = rep(b, "<li>Prices run through 2026-09-23 for all five asset classes. Reporting starts 2012-01-01; the 2026 year-to-date column covers 1 January to 23 September. Value requires two years of F3 price history before its first signal.</li>",
        "<li>" + CFG["data_line"].replace(" (the 29-Oct Bloomberg pull extends the 24-Sep file; every sheet is cut at 30 September)", "") + " Reporting starts 2012-01-01; the 2026 year-to-date column covers 1 January to " + CFG["short"] + ". Value requires two years of price history of its contract (F3; F2 for Precious and Agriculture) before its first signal.</li>")
b = rep(b, "Metals, Energy and NGL use expiry dates published by the exchange.</li>",
        "Metals, Energy (including Henry Hub) and NGL use expiry dates published by the exchange. EUA and TTF use ICE Endex last trade dates from Bloomberg's expiry history (EUA: third Monday of the delivery month; TTF: two business days before the delivery month).</li>")
b = rep(b, "and P3 covers 1 January 2022 to 23 September 2026 (the last price date).", "and P3 covers 1 January 2022 to " + CFG["last_txt"] + ".")
# Notes tab: what changed, carry wording for one-pair products, costs
b = rep(b, "<h2>Method, data and what changed</h2>", "<h2>Methodology and data</h2>")   # the Notes tab starts with the Timing convention (the 'What changed in this version' block was removed on 2026-11-01)
# Value contract: stated where the sleeve is defined (F2 for Precious and Agriculture)
b = rep(b, "<li><b>Value:</b> F3 price against its own 1,260-day average, long below -10%, short above +10%.", "<li><b>Value:</b> price of the Value contract (F3; F2 for Precious and Agriculture, whose contract cycles are sparse, so F3 can sit 4 to 6 months from the front) against its own 1,260-day average, long below -10%, short above +10%.")
b = rep(b, "d_t=\\frac{P^{F3}_t}{\\frac1{1260}\\sum_{i=0}^{1259}P^{F3}_{t-i}}-1", "d_t=\\frac{P^{V}_t}{\\frac1{1260}\\sum_{i=0}^{1259}P^{V}_{t-i}}-1")
# Liquidity metric pointer (equations as in the v7 document, Appendix liquidity section)
b = rep(b, "<h3>Data and calendars</h3>",
        "<h3>Liquidity metric</h3><ul class=\"steps\">"
        "<li><b>Dollar risk turnover:</b> the amount of one-standard-deviation daily price risk a market trades per day, which puts contracts of different size, price and volatility on one scale."
        "<div class=\"formula\">$$c_i=m_i\\,\\bar P_i\\,\\sigma_i,\\qquad \\mathrm{ADV}_i=\\frac1{T_i}\\sum_{t=1}^{T_i}\\sum_{j\\in S_i}V_{i,j,t},\\qquad x_i=\\mathrm{ADV}_i\\,c_i,\\qquad L_i=\\frac{K}{x_i}$$</div></li>"
        "<li><b>Terms:</b> <i>m<sub>i</sub></i> contract multiplier (units per lot); <i>P&#772;<sub>i</sub></i> mean price of the contract held over the window (USD per unit); <i>&sigma;<sub>i</sub></i> standard deviation of the daily log returns of the roll-adjusted series over the window; "
        "<i>S<sub>i</sub></i> the strip of tenors spanning twelve months (F1-F12 for monthly chains; Gold F1-F6, Silver F1-F5, Platinum and Palladium F1-F4, Corn, Wheat and Coffee F1-F5, Soybean F1-F7, Soybean Oil F1-F8, Sugar F1-F4, EUA F1-F4); "
        "<i>V<sub>i,j,t</sub></i> volume in lots of tenor <i>j</i> on day <i>t</i> (a day without a print counts as zero, open interest is never used); <i>T<sub>i</sub></i> the trading days of the window on the product's own calendar.</li>"
        "<li><b>L (days):</b> <i>K</i> is a reference position of USD 1 million of one-sigma daily risk, and <i>L</i> is its size as a multiple of one day of the market's risk turnover, i.e. the time in days to trade it at full market participation (0.05 is five per cent of a day, 3 is three days of the entire market's flow). "
        "It is shown as <i>Time to trade 1 sigma risk (in Days)</i> in each By-product table. The ranking of products does not depend on <i>K</i>.</li>"
        "<li>For research purposes the metric has been evaluated on 2025 volumes for each product (a one-time snapshot); NGL volume is the CME half only.</li></ul>"
        "<h3>Data and calendars</h3>")
b = rep(b, "Transaction costs are charged when the position changes.</li></ul>", "Transaction costs of 5 bps per unit of turnover are charged when the position changes, and on every roll day.</li></ul>")
b = rep(b, "The two z-scores are summed and the sign of the sum is the signal.", "The z-scores of a product's tenor pairs are summed (two pairs for every product) and the sign of the sum is the signal.")
b = rep(b, "summed across the tenor pairs (raw changes, not standardised) and signed; if a pair is missing the last signal is kept.", "summed across the tenor pairs (raw changes, not standardised) and signed; if a pair is missing the last signal is kept.")

# ---------------- page script ----------------
t = tail
i0 = t.index('const LABEL={metals:"Metals"')
i1 = t.index('const bar=document.getElementById("tabbar")')
t = t[:i0] + ('const LABEL=D.meta.labels;\n'
              'const ORDER=D.meta.keys.map(k=>[k,LABEL[k]]).concat([["all6","All 6 buckets"],["bystyle","By Style"],["crosspair","Cross-Pair"],["corr","Correlations"],["notes","Notes"]]);\n') + t[i1:]
t = rep(t, 'const HIDDEN_TABS=["all5","all5_exng"];', 'const HIDDEN_TABS=["all6"];')
t = rep(t, 'const asset=ASSET[key],t=D.tabs[key];\n  const sleeves', 'const t=D.tabs[key];\n  const sleeves')
t = rep(t, 't.products.map(pr=>{const d=D.products[asset+"|"+pr];return `<tr><td>${pr}</td>`', 't.pkeys.map((pk,ix)=>{const pr=t.products[ix];const d=D.products[pk];return `<tr><td>${pr}</td>`')
t = rep(t, '${D.meta.pairs[asset+"|"+pr].join(", ")}</td><td>${D.meta.rolls[asset+"|"+pr]}</td>', '${D.meta.pairs[pk].join(", ")}</td><td>${(v=>v==null?"n/a":String(Number(v.toPrecision(3))))(D.meta.liq[pk])}</td>')
t = rep(t, '<th>Tenor pairs</th><th>Roll events</th>', '<th>Tenor pairs</th><th>Time to trade 1 sigma risk (in Days)</th>')
t = rep(t, 'const asset=ASSET[key],t=D.tabs[key],host=p.querySelector("[data-peq]");', 'const t=D.tabs[key],host=p.querySelector("[data-peq]");')
t = rep(t, '${t.products.map(x=>`<option>${x}</option>`).join("")}', '${t.pkeys.map((k,ix)=>`<option value="${k}">${t.products[ix]}</option>`).join("")}')
t = rep(t, 'renderEquity(inner,"prod|"+asset+"|"+sel.value)', 'renderEquity(inner,"prod|"+sel.value)')
# combined book (tab stays hidden, as in the published 2012 page)
t = rep(t, '[["all5","All 5 asset classes (Energy with NatGas)"],["all5_exng","All 5 asset classes (Energy ex-NatGas)"]].forEach(([key,label])=>{const c=D.combined[key];', '[["all6","All 6 buckets"]].forEach(([key,label])=>{const c=D.combined;')
t = rep(t, "Two-stage book: five sleeves into an asset-class portfolio, then the five asset-class portfolios into one book, by Equal Weight or Inverse Vol at each stage (first word = sleeves, second = across asset classes).",
        "Two-stage book: five sleeves into a bucket portfolio, then the six bucket portfolios into one book, by Equal Weight or Inverse Vol at each stage (first word = sleeves, second = across buckets).")
t = rep(t, '"Reference" rows are each asset class\'s own EW PORT on that window.', '"Reference" rows are each bucket\'s own EW PORT on that window.')
# by style
j0 = t.index('/* ---------- by style ---------- */')
j1 = t.index('/* ---------- cross-pair ---------- */')
t = t[:j0] + '''/* ---------- by style ---------- */
(function(){const p=addPanel("bystyle",`<div class="card"><h2>By-Style Portfolio</h2><p class="note">Each style (Momentum, Carry, Carry-Momentum, Value, Skewness) is first equal-weighted across the six buckets' own sleeves on their common dates, giving one cross-bucket series per style. The five style series are then combined into one Equal Weight portfolio (EW PORT) and one Inverse Vol portfolio (trailing 63-day volatility, lagged one day).</p>
  <div class="window-row"><span class="note" style="margin:0" data-bn></span></div>
  <div class="window-row"><h3>Performance by period</h3><label>Show details for period: <select class="window-select" data-hs>${horizonOpts}</select></label></div><div class="table-scroll"><table data-full></table></div><h3>Cumulative return</h3><div data-eq></div></div>`,false);
  const hs=p.querySelector("[data-hs]"),tb=p.querySelector("[data-full]");
  const draw=()=>{const c=D.bystyle;p.querySelector("[data-bn]").textContent="Common window: "+c.common_first+" to "+c.common_last+".";tb.innerHTML=mergedTable(c.windows,hs.value);wireHeads(tb,hs);renderEquity(p.querySelector("[data-eq]"),"bystyle");};
  hs.addEventListener("change",draw);draw();})();

''' + t[j1:]
# cross pair
t = rep(t, "Each row blends two asset classes' own portfolios, 50/50 (Equal Weight) or by trailing 63-day inverse volatility (Inverse Vol); each asset-class portfolio is built with the same method. Series are aligned on the pair's common dates. Pairs involving Energy are shown with NatGas and ex-NatGas.",
        "Each row blends two buckets' own portfolios, 50/50 (Equal Weight) or by trailing 63-day inverse volatility (Inverse Vol); each bucket portfolio is built with the same method. Series are aligned on the pair's common dates (15 pairs).")
t = rep(t, '<label>Energy: <select class="window-select" data-cv><option value="with NatGas">with NatGas</option><option value="ex-NatGas">ex-NatGas</option></select> Construction:', '<label>Construction:')
t = rep(t, 'const cv=p.querySelector("[data-cv]"),cc=p.querySelector("[data-cc]")', 'const cc=p.querySelector("[data-cc]")')
t = rep(t, 'const W=D.crosspair[cv.value][cc.value];', 'const W=D.crosspair[cc.value];')
t = rep(t, '[cv,cc,hs].forEach(e=>e.addEventListener("change",draw));draw();})();', '[cc,hs].forEach(e=>e.addEventListener("change",draw));draw();})();')
# correlations
t = rep(t, 'const CAC=["metals","energy","precious","ngl","agri"],CLAB=["Metals","Energy","Precious","NGL","Agriculture"];', 'const CAC=D.meta.keys,CLAB=D.meta.keys.map(k=>LABEL[k]);')
t = rep(t, "Within-asset-class matrices use each asset class's own calendar; cross-asset-class and rolling figures use the intersection of trading dates across the five asset classes (days per strategy: ${D.corr.rows.map(r=>r+\" \"+D.corr.cross._n[r]).join(\", \")}; the Inverse Vol rows start later because NGL's Inverse Vol series is undefined before 23 Feb 2012).",
        "Within-bucket matrices use each bucket's own calendar; cross-bucket and rolling figures use the intersection of trading dates across the six buckets (days per strategy: ${D.corr.rows.map(r=>r+\" \"+D.corr.cross._n[r]).join(\", \")}).")
t = rep(t, "Section 1: Within-Asset-Class Correlation", "Section 1: Within-Bucket Correlation")
t = rep(t, "Select asset class</h3><label>Asset class: <select", "Select bucket</h3><label>Bucket: <select")
t = rep(t, "Section 2: Cross-Asset-Class Correlation", "Section 2: Cross-Bucket Correlation")
t = rep(t, "Trailing correlation between two asset classes' own portfolios, 2012 onward.", "Trailing correlation between two buckets' own portfolios, 2012 onward.")

out = R / f"Analysis/Final_Research_Dashboard_2012_{TAG}.html"
out.write_text(b + "<script>\nconst D=" + json.dumps(data) + ";\n" + t, encoding="utf8")
print("written", out, out.stat().st_size // 1024, "KB")
