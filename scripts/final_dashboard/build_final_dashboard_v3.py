"""Builds Analysis/Final_Research_Dashboard_2012_<tag>.html (2026-10-31): the 2012-start, three-period research dashboard with the new buckets
(Metals, Petroleum, Gas and Emissions, NGL, Precious, Agriculture). Tag 0930 = data cut at 2026-09-30, tag 1029 = latest data (to 2026-10-29), chosen with the env
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
_by = res["bystyle"]["common_first"][:4]       # the seven-bucket book (By Style, All buckets, cross-bucket correlations) starts with the US Power data
BOOKCOLS = [("full", "Full", f"{_by}-2026"), ("p1", "P1", f"{_by}-2016"), ("p2", "P2", "2017-2021"), ("p3", "P3", "2022-2026"), ("y26", "2026", "YTD")]
data = dict(res, cols=[dict(key=k, label=l, years=y) for k, l, y in COLS], bookcols=[dict(key=k, label=l, years=y) for k, l, y in BOOKCOLS])

# Liquidity metric, Calendar 2025 (Analysis/Liquidity_Cal2025_results.csv, scripts/liquidity_cal2025.py): L = K / x with K = USD 1M of one-sigma daily risk, shown in the By-product tables
import csv
_liq = {r["product"]: r for r in csv.DictReader(open(R / "Analysis/Liquidity_Cal2025_results.csv", encoding="utf8"))}
for _r in _liq.values():
    assert abs(float(_r["N_contracts_for_K"]) * float(_r["risk_per_contract"]) - 1e6) < 1, ("L is not on K = USD 1M", _r["product"])
_pk = list(res["meta"]["rolls"].keys())
_liq.update({r["product"]: r for r in csv.DictReader(open(R / "Analysis/Power_Liquidity_Cal2025_results.csv", encoding="utf8"))})     # the five US Power series of the book
for _r in list(_liq.values())[-6:]:
    assert abs(float(_r["N_contracts_for_K"]) * float(_r["risk_per_contract"]) - 1e6) < 1, ("L is not on K = USD 1M", _r["product"])
assert all(k.split("|")[1] in _liq for k in _pk), [k for k in _pk if k.split("|")[1] not in _liq]
data["meta"] = dict(res["meta"], liq={k: float(_liq[k.split("|")[1]]["L_strip"]) for k in _pk})

# Power tab (2026-11-04), standalone: scripts/final_dashboard/power_tab_v3.py -> Analysis/_power_build/power_tab_0930.json (TRACKED, so a rebuild on any machine has it). It is added as its own tab
# entry (data["tabs"]["power"]) and is NOT in meta.keys, which drives the All-buckets book, By Style, Cross-Pair and Correlations, so none of those sees it. Tags 0930 and 1029 (the power data are cut
# at 2026-09-30 and 2026-10-29). If the file is missing the build STOPS: a page without the Power tab must never be published by accident (it happened once, when the input sat in the untracked outputs/ folder).
POWER = None
_pt = R / f"Analysis/_power_build/power_tab_{TAG}.json"
if TAG in ("0930", "1029"):
    if not _pt.exists():
        sys.exit(f"{_pt} is missing: the {TAG} page has a Power tab. Regenerate it with  FD_TAG={TAG} python scripts/power/power_pipeline.py  and  FD_TAG={TAG} python scripts/final_dashboard/power_tab_v3.py "
                 "(after python scripts/power/power_liquidity.py), or restore it from git.")
    POWER = json.load(open(_pt))
    assert "power" in res["meta"]["keys"] and "power" not in res["tabs"]       # Power is a book member in the analysis stage; its tab comes from power_tab_v3.py
    for _c in POWER["tab"]["cols"]:
        if _c["key"] == "p1":
            _c["years"] = ""          # P1 (2012-2016) does not exist for power: show nothing, not "n/a"
    data["tabs"] = dict(res["tabs"], power=POWER["tab"])
    data["products"] = dict(res["products"], **POWER["products"])
    data["equity"] = dict(res["equity"], **POWER["equity"])
    data["meta"] = dict(data["meta"], liq=dict(data["meta"]["liq"], **POWER["meta"]["liq"]),
                        pairs=dict(res["meta"]["pairs"], **POWER["meta"]["pairs"]), rolls=dict(res["meta"]["rolls"], **POWER["meta"]["rolls"]))

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
        "Seven buckets (Metals, Petroleum, Gas and Emissions, NGL, Precious, Agriculture and US Power), five sleeves each (Momentum, Carry, Carry-Momentum, Value, Skewness), combined by Equal Weight and Inverse Vol only. Log-return methodology, 5 bps costs, reporting from 2012-01-01 in three periods (P1 2012-2016, P2 2017-2021, P3 2022 onwards) plus a 2026 year-to-date column. All price data through " + CFG["cutoff"] + "." + (" US Power (ICE real-time power futures, data from 2015) is part of the combined book, By Style, Cross-Pair and Correlations on common dates from January 2015; its own tab reports from 2017, when all its sleeves are live." if POWER else ""))
b = rep(b, "one per asset class, plus By Style, Cross-Pair, Correlations and Notes (methods and data).", "one per bucket, plus By Style, Cross-Pair, Correlations and Notes (methods and data).")
b = rep(b, "every control you can change: period, commodity, metric, Energy with or without NatGas.", "every control you can change: period, commodity, metric.")
b = rep(b, "<b>Each asset-class tab</b>", "<b>Each bucket tab</b>")
b = rep(b, "<li>Metals and Energy: F1-F3 and F1-F13. NGL: F2-F4 and F2-F14.</li>",
        "<li>Metals, Petroleum and Nat Gas: F1-F3 and F1-F13. NGL: F2-F4 and F2-F14, except Naphtha F2-F4 only. TTF and UK Gas: F1-F2 and F1-F13. EUA: F1-F2 and F1-F5 (EUA is quarterly, so F5 is 12 months out; TTF is monthly, so F13 is).</li>")
b = rep(b, " (10 to 11 months, the deepest column in the file)", "")
b = rep(b, "This rolls roughly 14 to 16 trading days before expiry for Energy, NGL, Precious and Sugar, about 6 for Metals and about 5 for Corn, Wheat and Soybeans.</li>",
        "Counted from the roll day to the last trade date, this rolls about 5 trading days before expiry for Corn, Wheat, Soybean and Soybean Oil, 6 for Metals, 8 for Coffee, 9 for WTI, 11 for Brent and EUA, 14 for Nat Gas and Precious, 15 for TTF, UK Gas and Sugar, and 16 for RBOB, Heating Oil, NGL and Naphtha.</li>")
b = rep(b, "<li>Products inside a sleeve are equally weighted on common dates",
        "<li>Buckets: Petroleum = WTI, Brent, RBOB, Heating Oil. Gas and Emissions = Henry Hub natural gas (US), TTF natural gas (European, ICE Endex), UK Gas (NBP, ICE Futures Europe) and EUA carbon. NGL = Ethane, Propane, Butane, Isobutane and Naphtha (CIF NWE average-price swap). Metals, Precious and Agriculture are unchanged.</li>\n<li>Products inside a sleeve are equally weighted on common dates")
b = rep(b, "<li>Each asset-class portfolio combines its five sleeves", "<li>Each bucket portfolio combines its five sleeves")
b = rep(b, "sleeves into an asset-class portfolio, then the five asset-class portfolios into one book; all four EW / Inverse Vol pairs are shown, with and without NatGas. <b>Cross-pair portfolios</b> blend two asset classes' portfolios",
        "sleeves into a bucket portfolio, then the seven bucket portfolios into one book; all four EW / Inverse Vol pairs are shown. <b>Cross-pair portfolios</b> blend two buckets' portfolios")
b = rep(b, "<li>Prices run through 2026-09-23 for all five asset classes. Reporting starts 2012-01-01; the 2026 year-to-date column covers 1 January to 23 September. Value requires two years of F3 price history before its first signal.</li>",
        "<li>" + CFG["data_line"].replace(" (the 29-Oct Bloomberg pull extends the 24-Sep file; every sheet is cut at 30 September)", "") + " Reporting starts 2012-01-01; the 2026 year-to-date column covers 1 January to " + CFG["short"] + ". Value requires two years of price history of its contract (F3; F2 for Precious and Agriculture) before its first signal. The All-buckets book, By Style and the cross-bucket correlations include US Power and therefore start on " + res["bystyle"]["common_first"] + " (the first common trading day once the Power data begin in January 2015), so their Full window is " + _by + "-2026 and their P1 is " + _by + "-2016; the pairs with US Power start the same day, the other pairs in 2012. Inverse Vol series that include US Power (its own Inverse Vol portfolio, the six pairs with Power under the Inverse Vol construction, the Inverse Vol-sleeves rows of the combined book and the Inverse Vol rows of the correlations) start in " + res["meta"]["iv_start_power"][:7] + " at the earliest (Power's own Inverse Vol portfolio on " + res["meta"]["iv_start_power"] + ", the Inverse Vol pairs with Power 63 trading days later), because Power's Value sleeve is flat until December 2016 and a flat sleeve has no trailing volatility to weight by; their P1 is empty.</li>")
b = rep(b, "Metals, Energy and NGL use expiry dates published by the exchange.</li>",
        "Metals, Energy (including Henry Hub) and the Mont Belvieu NGL swaps use expiry dates published by the exchange.</li>")
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
if POWER:
    b = rep(b, "<h3>Data and calendars</h3>",
            "<h3>Power tab (standalone)</h3><ul class=\"steps\">"
            "<li><b>What it is:</b> US power with the same layout as the bucket tabs. It is part of the All-buckets book, By Style, Cross-Pair and Correlations (seven buckets) on common dates, which start in January 2015 with the Power data; until its signals exist (Carry-Momentum from February 2015, Momentum from November 2015, Carry and Skewness from December 2015, Value from December 2016) the Power sleeves are flat and add a return of zero. The tab itself reports from 2017, when every sleeve is live.</li>"
            "<li><b>Series:</b> ICE monthly real-time power futures (USD/MWh), peak and off-peak, on the PJM Western Hub, ERCOT North 345KV and MISO Indiana Hub. The data files hold ten series: the four CME ones start in 2026 and carry no volume or open interest, so six are usable, "
            "and the five whose Calendar-2025 time to trade 1 sigma risk is under 5 days are shown (PJM Peak 0.10, ERCOT Peak 0.36, PJM OffPeak 0.47, ERCOT OffPeak 4.7, MISO Peak 4.7; MISO OffPeak, 9.9 days, is excluded). One lot is 1 MW for every hour of the contract (ICE), i.e. 304 to 417 MWh.</li>"
            "<li><b>Contracts and roll:</b> every delivery month is listed (12 last trade dates a year) and the last trade date falls in the delivery month, so the generic F1 is the contract delivering now. The same roll rule applies (5th trading day of the expiry month), "
            "which here rolls into the next month on the 5th trading day of the delivery month: every roll of every series falls on that day. The position is therefore in the partly settled delivery-month contract for its first four or five trading days. F2 is the next month and F13 the same month a year later.</li>"
            "<li><b>Parameters:</b> the same as every other bucket (Momentum, Carry V2 on F1-F2 and F1-F13, Carry-Momentum, Value on F3, Skewness; 5 bps costs; EW and Inverse Vol).</li>"
            "<li><b>Windows:</b> the data start on 2015-01-02 and Value needs two years of F3, so on this tab Full is 2017-2026 and P1 (2012-2016) is not available; P2, P3 and 2026 are as elsewhere (the All-buckets book and the correlations use the common dates from 2015). "
            "Power prices are far more volatile than the other buckets (about 60% to 125% a year per sleeve), so read the IRs together with the drawdowns.</li></ul>"
            "<h3>Data and calendars</h3>")
b = rep(b, "Transaction costs are charged when the position changes.</li></ul>", "Transaction costs of 5 bps per unit of turnover are charged when the position changes, and on every roll day.</li></ul>")
b = rep(b, "The two z-scores are summed and the sign of the sum is the signal.", "The z-scores of a product's tenor pairs are summed (two pairs for every product) and the sign of the sum is the signal.")
b = rep(b, "summed across the tenor pairs (raw changes, not standardised) and signed; if a pair is missing the last signal is kept.", "summed across the tenor pairs (raw changes, not standardised) and signed; if a pair is missing the last signal is kept.")

# ---------------- page script ----------------
t = tail
i0 = t.index('const LABEL={metals:"Metals"')
i1 = t.index('const bar=document.getElementById("tabbar")')
t = t[:i0] + ('const LABEL=D.meta.labels;\n'
              'const ORDER=D.meta.keys.map(k=>[k,LABEL[k]]).concat([["all6","All 7 buckets"],["bystyle","By Style"],["crosspair","Cross-Pair"],["corr","Correlations"],["notes","Notes"]]);\n') + t[i1:]
t = rep(t, 'const HIDDEN_TABS=["all5","all5_exng"];', 'const HIDDEN_TABS=["all6"];')
t = rep(t, 'const f=(v,n,s)=>v==null?"n/a":v.toFixed(n)+(s||"");', 'const f=(v,n,s)=>v==null?"":v.toFixed(n)+(s||"");')     # a missing value (Power's P1, the Inverse Vol pairs with Power in P1) is left empty
t = rep(t, 'const ir=v=>v==null?"n/a":`<span class="ir-cell"', 'const ir=v=>v==null?"":`<span class="ir-cell"')
t = rep(t, 'const asset=ASSET[key],t=D.tabs[key];\n  const sleeves', 'const t=D.tabs[key];\n  const sleeves')
t = rep(t, 't.products.map(pr=>{const d=D.products[asset+"|"+pr];return `<tr><td>${pr}</td>`', 't.pkeys.map((pk,ix)=>{const pr=t.products[ix];const d=D.products[pk];return `<tr><td>${pr}</td>`')
t = rep(t, '${D.meta.pairs[asset+"|"+pr].join(", ")}</td><td>${D.meta.rolls[asset+"|"+pr]}</td>', '${D.meta.pairs[pk].join(", ")}</td><td>${(v=>v==null?"n/a":String(Number(v.toPrecision(3))))(D.meta.liq[pk])}</td>')
t = rep(t, '<th>Tenor pairs</th><th>Roll events</th>', '<th>Tenor pairs</th><th>Time to trade 1 sigma risk (in Days)</th>')
t = rep(t, 'const asset=ASSET[key],t=D.tabs[key],host=p.querySelector("[data-peq]");', 'const t=D.tabs[key],host=p.querySelector("[data-peq]");')
t = rep(t, '${t.products.map(x=>`<option>${x}</option>`).join("")}', '${t.pkeys.map((k,ix)=>`<option value="${k}">${t.products[ix]}</option>`).join("")}')
t = rep(t, 'renderEquity(inner,"prod|"+asset+"|"+sel.value)', 'renderEquity(inner,"prod|"+sel.value)')
if POWER:
    # tab-specific period columns (Full 2017-2026, P1 not available): mergedTable / wireMerged / the horizon selectors take the tab's own `cols`; every other tab passes none and keeps D.cols
    a0, a1 = t.index("function mergedTable(W,per,lab){"), t.index("function wireHeads(")
    mt = t[a0:a1].replace("D.cols", "CC")
    mt = rep(mt, "function mergedTable(W,per,lab){\n  const names=", "function mergedTable(W,per,lab,cols){\n  const CC=cols||D.cols;const names=")
    t = t[:a0] + mt + t[a1:]
    t = rep(t, 'function wireMerged(p,getW,lab){', 'function wireMerged(p,getW,lab,cols){')
    t = rep(t, 'tb.innerHTML=mergedTable(getW(),sel.value,lab);wireHeads(tb,sel);', 'tb.innerHTML=mergedTable(getW(),sel.value,lab,cols);wireHeads(tb,sel);')
    t = rep(t, 'const horizonOpts=D.cols.map(c=>`<option value="${c.key}">${c.label} (${c.years})</option>`).join("");',
            'const hOpts=cols=>(cols||D.cols).map(c=>`<option value="${c.key}">${c.label} (${c.years})</option>`).join("");const horizonOpts=hOpts();')
    t = rep(t, '<select class="window-select" data-ph>${horizonOpts}</select>', '<select class="window-select" data-ph>${hOpts(t.cols)}</select>')
    t = rep(t, '<select class="window-select" data-hs>${horizonOpts}</select></label></div><div class="table-scroll"><table data-full></table></div><h3>Cumulative return</h3><div data-eq></div><div data-prod></div>',
            '<select class="window-select" data-hs>${hOpts(t.cols)}</select></label></div><div class="table-scroll"><table data-full></table></div><h3>Cumulative return</h3><div data-eq></div><div data-prod></div>')
    t = rep(t, 'wireMerged(p,()=>t.windows);', 'wireMerged(p,()=>t.windows,undefined,t.cols);')
    # the tab title comes from the tab's own data, not from D.meta.labels (which lists the six buckets only and drives the correlation selector)
    t = rep(t, '<div class="card"><h2>${LABEL[key]}</h2><p class="note"><b>Products:</b>', '<div class="card"><h2>${t.label}</h2><p class="note"><b>Products:</b>')
    t = rep(t, '<b>Data:</b> ${t.data_first} to ${t.data_last}.</p>', '<b>Data:</b> ${t.data_first} to ${t.data_last}.${t.note?" "+t.note:""}</p>')
# combined book (tab stays hidden, as in the published 2012 page)
t = rep(t, '[["all5","All 5 asset classes (Energy with NatGas)"],["all5_exng","All 5 asset classes (Energy ex-NatGas)"]].forEach(([key,label])=>{const c=D.combined[key];', '[["all6","All 7 buckets"]].forEach(([key,label])=>{const c=D.combined;')
t = rep(t, "Two-stage book: five sleeves into an asset-class portfolio, then the five asset-class portfolios into one book, by Equal Weight or Inverse Vol at each stage (first word = sleeves, second = across asset classes).",
        "Two-stage book: five sleeves into a bucket portfolio, then the seven bucket portfolios into one book, by Equal Weight or Inverse Vol at each stage (first word = sleeves, second = across buckets).")
t = rep(t, '"Reference" rows are each asset class\'s own EW PORT on that window.', '"Reference" rows are each bucket\'s own EW PORT on that window.')
# by style
j0 = t.index('/* ---------- by style ---------- */')
j1 = t.index('/* ---------- cross-pair ---------- */')
t = t[:j0] + '''/* ---------- by style ---------- */
(function(){const p=addPanel("bystyle",`<div class="card"><h2>By-Style Portfolio</h2><p class="note">Each style (Momentum, Carry, Carry-Momentum, Value, Skewness) is first equal-weighted across the seven buckets' own sleeves on their common dates, giving one cross-bucket series per style. The five style series are then combined into one Equal Weight portfolio (EW PORT) and one Inverse Vol portfolio (trailing 63-day volatility, lagged one day).</p>
  <div class="window-row"><span class="note" style="margin:0" data-bn></span></div>
  <div class="window-row"><h3>Performance by period</h3><label>Show details for period: <select class="window-select" data-hs>${hOpts(D.bookcols)}</select></label></div><div class="table-scroll"><table data-full></table></div><h3>Cumulative return</h3><div data-eq></div></div>`,false);
  const hs=p.querySelector("[data-hs]"),tb=p.querySelector("[data-full]");
  const draw=()=>{const c=D.bystyle;p.querySelector("[data-bn]").textContent="Common window: "+c.common_first+" to "+c.common_last+" (the first common trading day once the US Power data begin in January 2015, to the last price date).";tb.innerHTML=mergedTable(c.windows,hs.value,undefined,D.bookcols);wireHeads(tb,hs);renderEquity(p.querySelector("[data-eq]"),"bystyle");};
  hs.addEventListener("change",draw);draw();})();

''' + t[j1:]
# cross pair
t = rep(t, "Each row blends two asset classes' own portfolios, 50/50 (Equal Weight) or by trailing 63-day inverse volatility (Inverse Vol); each asset-class portfolio is built with the same method. Series are aligned on the pair's common dates. Pairs involving Energy are shown with NatGas and ex-NatGas.",
        "Each row blends two buckets' own portfolios, 50/50 (Equal Weight) or by trailing 63-day inverse volatility (Inverse Vol); each bucket portfolio is built with the same method. Series are aligned on the pair's common dates (21 pairs; the six pairs with US Power start in January 2015, so their P1 is 2015-2016, and the other fifteen start in 2012).")
t = rep(t, '<label>Energy: <select class="window-select" data-cv><option value="with NatGas">with NatGas</option><option value="ex-NatGas">ex-NatGas</option></select> Construction:', '<label>Construction:')
t = rep(t, 'const cv=p.querySelector("[data-cv]"),cc=p.querySelector("[data-cc]")', 'const cc=p.querySelector("[data-cc]")')
t = rep(t, 'const W=D.crosspair[cv.value][cc.value];', 'const W=D.crosspair[cc.value];')
t = rep(t, '[cv,cc,hs].forEach(e=>e.addEventListener("change",draw));draw();})();', '[cc,hs].forEach(e=>e.addEventListener("change",draw));draw();})();')
# correlations
t = rep(t, 'const CAC=["metals","energy","precious","ngl","agri"],CLAB=["Metals","Energy","Precious","NGL","Agriculture"];', 'const CAC=D.meta.keys,CLAB=D.meta.keys.map(k=>LABEL[k]);')
t = rep(t, "Within-asset-class matrices use each asset class's own calendar; cross-asset-class and rolling figures use the intersection of trading dates across the five asset classes (days per strategy: ${D.corr.rows.map(r=>r+\" \"+D.corr.cross._n[r]).join(\", \")}; the Inverse Vol rows start later because NGL's Inverse Vol series is undefined before 23 Feb 2012).",
        "Within-bucket matrices use each bucket's own calendar; cross-bucket and rolling figures use the intersection of trading dates across the seven buckets, which starts in January 2015 with the US Power data (days per strategy: ${D.corr.rows.map(r=>r+\" \"+D.corr.cross._n[r]).join(\", \")}).")
# Cumulative-return charts (both tags): value of $100 invested at the chosen period start = exp(cumulative log return since the start) x 100, baseline at $100, PNG and CSV download buttons.
if TAG in ("0930", "1029"):
    t = rep(t, "Cumulative return, rebased to 0 at the start of the period.</span></div>",
            "Value of $100 invested at the start of the period.</span><span style=\"margin-left:auto\"><button type=\"button\" class=\"window-select\" data-eq=\"png\">Download PNG</button> <button type=\"button\" class=\"window-select\" data-eq=\"csv\">Download CSV</button></span></div>")
    t = rep(t, "const vals={};let lo=0,hi=0;", "const vals={};let lo=100,hi=100;")
    t = rep(t, "vals[nm]=idx.map(i=>(Math.exp(c[i]-c[s0])-1)*100);", "vals[nm]=idx.map(i=>Math.exp(c[i]-c[s0])*100);")
    t = rep(t, "const W=920,H=340,padL=56,", "const W=920,H=340,padL=64,")
    t = rep(t, "const pad=(hi-lo)*0.06;lo-=pad;hi+=pad;", "const pad=(hi-lo)*0.06;lo=Math.max(0,lo-pad);hi+=pad;")
    t = rep(t, "function renderEquity(host,key){", "const D$=(v,d)=>\"$\"+(Math.abs(v)<0.5*Math.pow(10,-d)?0:v).toLocaleString(\"en-US\",{minimumFractionDigits:d,maximumFractionDigits:d});\nfunction renderEquity(host,key){")
    t = rep(t, "const on={};names.forEach", "let cur=null;const on={};names.forEach")
    t = rep(t, "for(let v=Math.ceil(lo/stepV)*stepV;v<=hi;v+=stepV){const y=yS(v);grid+=`<line x1=\"${padL}\" y1=\"${y.toFixed(1)}\" x2=\"${W-padR}\" y2=\"${y.toFixed(1)}\" class=\"${Math.abs(v)<1e-9?\"rc-zero-line\":\"rc-grid-line\"}\"/><text x=\"${padL-6}\" y=\"${(y+3).toFixed(1)}\" text-anchor=\"end\" class=\"rc-axis-label\">${v.toFixed(0)}%</text>`;}",
             "const dp=stepV<1?2:0;for(let v=Math.ceil(lo/stepV)*stepV;v<=hi;v+=stepV){if(Math.abs(v-100)<1e-9)continue;const y=yS(v);grid+=`<line x1=\"${padL}\" y1=\"${y.toFixed(1)}\" x2=\"${W-padR}\" y2=\"${y.toFixed(1)}\" class=\"rc-grid-line\"/><text x=\"${padL-6}\" y=\"${(y+3).toFixed(1)}\" text-anchor=\"end\" class=\"rc-axis-label\">${D$(v,dp)}</text>`;}{const y=yS(100);grid+=`<line x1=\"${padL}\" y1=\"${y.toFixed(1)}\" x2=\"${W-padR}\" y2=\"${y.toFixed(1)}\" class=\"rc-zero-line\"/><text x=\"${padL-6}\" y=\"${(y+3).toFixed(1)}\" text-anchor=\"end\" class=\"rc-axis-label\">$100</text>`;}")
    t = rep(t, "chart.innerHTML=`<svg viewBox", "cur={sel,idx,vals,lo,hi,stepV,start};chart.innerHTML=`<svg viewBox")
    t = rep(t, "vals[nm][k].toFixed(1)+\"%\"", "D$(vals[nm][k],2)")
    EXPORT = r"""startSel.addEventListener("change",draw);draw();
  const esc=x=>String(x).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  const ttl=()=>{const card=host.closest(".card");let x=card&&card.querySelector("h2")?card.querySelector("h2").textContent:"Cumulative return";if(key.indexOf("prod|")===0){const sl=card&&card.querySelector("[data-pc]");if(sl)x+=" - "+sl.options[sl.selectedIndex].text;}return x;};
  const fname=()=>(ttl()+" from "+cur.start).replace(/[^A-Za-z0-9._-]+/g,"_");
  const save=(blob,name)=>{const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=name;document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},1000);};
  host.querySelector("[data-eq=csv]").addEventListener("click",()=>{if(!cur)return;const q=x=>'"'+String(x).replace(/"/g,'""')+'"';const rows=[["Date"].concat(cur.sel.map(nm=>nm+" ($)")).map(q).join(",")];cur.idx.forEach((gi,k)=>rows.push([E.dates[gi]].concat(cur.sel.map(nm=>cur.vals[nm][k].toFixed(4))).join(",")));save(new Blob(["\ufeff"+rows.join("\r\n")],{type:"text/csv;charset=utf-8"}),fname()+".csv");});
  host.querySelector("[data-eq=png]").addEventListener("click",()=>{if(!cur)return;const {sel,idx,vals,lo,hi,stepV}=cur,n=idx.length,dp=stepV<1?2:0;
    const W=920,H=340,padL=64,padR=16,padT=14,padB=30,plotW=W-padL-padR,plotH=H-padT-padB,F='font-family="Arial,Helvetica,sans-serif"';
    let lx=16,ly=44,lg="";sel.forEach(nm=>{const w=nm.length*6.3+34;if(lx+w>W-16){lx=16;ly+=18;}lg+=`<rect x="${lx}" y="${ly-8}" width="14" height="4" fill="${PALETTE[names.indexOf(nm)%PALETTE.length]}"/><text x="${lx+19}" y="${ly}" font-size="11" fill="#222" ${F}>${esc(nm)}</text>`;lx+=w;});
    const OFF=ly+14,TH=OFF+H,xS=i=>padL+(i/Math.max(1,n-1))*plotW,yS=v=>padT+(1-(v-lo)/(hi-lo))*plotH;
    let g="";for(let v=Math.ceil(lo/stepV)*stepV;v<=hi;v+=stepV){if(Math.abs(v-100)<1e-9)continue;const y=yS(v);g+=`<line x1="${padL}" y1="${y.toFixed(1)}" x2="${W-padR}" y2="${y.toFixed(1)}" stroke="#e1e4e8" stroke-width="1"/><text x="${padL-6}" y="${(y+3).toFixed(1)}" text-anchor="end" font-size="11" fill="#444" ${F}>${D$(v,dp)}</text>`;}
    {const y=yS(100);g+=`<line x1="${padL}" y1="${y.toFixed(1)}" x2="${W-padR}" y2="${y.toFixed(1)}" stroke="#666" stroke-width="1.2" stroke-dasharray="4 3"/><text x="${padL-6}" y="${(y+3).toFixed(1)}" text-anchor="end" font-size="11" font-weight="700" fill="#222" ${F}>$100</text>`;}
    let ly0=null;idx.forEach((gi,k)=>{const yy=E.dates[gi].slice(0,4);if(yy!==ly0){ly0=yy;const x=xS(k);g+=`<line x1="${x.toFixed(1)}" y1="${padT}" x2="${x.toFixed(1)}" y2="${H-padB}" stroke="#e1e4e8" stroke-width="1"/><text x="${x.toFixed(1)}" y="${H-padB+14}" text-anchor="middle" font-size="11" fill="#444" ${F}>${yy}</text>`;}});
    const pl=sel.map(nm=>`<polyline fill="none" stroke="${PALETTE[names.indexOf(nm)%PALETTE.length]}" stroke-width="1.8" stroke-linejoin="round" points="${vals[nm].map((v,k)=>xS(k).toFixed(1)+","+yS(v).toFixed(1)).join(" ")}"/>`).join("");
    const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${TH}" viewBox="0 0 ${W} ${TH}"><rect width="${W}" height="${TH}" fill="#fff"/><text x="16" y="20" font-size="15" font-weight="700" fill="#111" ${F}>${esc(ttl())}</text><text x="${W-16}" y="20" text-anchor="end" font-size="11" fill="#444" ${F}>Value of $100 invested on ${cur.start}</text>${lg}<g transform="translate(0,${OFF})">${g}${pl}</g></svg>`;
    const url=URL.createObjectURL(new Blob([svg],{type:"image/svg+xml;charset=utf-8"})),img=new Image();
    img.onload=()=>{const c=document.createElement("canvas");c.width=W*2;c.height=TH*2;const cx=c.getContext("2d");cx.fillStyle="#fff";cx.fillRect(0,0,c.width,c.height);cx.drawImage(img,0,0,c.width,c.height);URL.revokeObjectURL(url);c.toBlob(b=>save(b,fname()+".png"),"image/png");};img.src=url;});"""
    t = rep(t, 'startSel.addEventListener("change",draw);draw();', EXPORT)
    # Power tab: P1 does not exist, so its heading year range and its cells stay empty instead of "n/a"
    t = rep(t, "const hOpts=cols=>(cols||D.cols).map(c=>`<option value=\"${c.key}\">${c.label} (${c.years})</option>`).join(\"\");",
            "const hOpts=cols=>(cols||D.cols).map(c=>`<option value=\"${c.key}\">${c.label}${c.years?` (${c.years})`:\"\"}</option>`).join(\"\");")
    t = rep(t, "Details for \"+pc.label+\" (\"+pc.years+\")</th>", "Details for \"+pc.label+(pc.years?\" (\"+pc.years+\")\":\"\")+\"</th>")
    t = rep(t, "CC.map(c=>`<td${c.key===per?' class=\"on\"':\"\"}>${ir(W[c.key][i].ir)}</td>`).join(\"\")+`<td class=\"sel\">${f(r.ret,2,\"%\")}</td><td class=\"sel\">${f(r.vol,2,\"%\")}</td><td class=\"sel\">${f(r.mdd,2,\"%\")}</td></tr>`",
            "CC.map(c=>`<td${c.key===per?' class=\"on\"':\"\"}>${c.years===\"\"?\"\":ir(W[c.key][i].ir)}</td>`).join(\"\")+(pc.years===\"\"?`<td class=\"sel\"></td><td class=\"sel\"></td><td class=\"sel\"></td></tr>`:`<td class=\"sel\">${f(r.ret,2,\"%\")}</td><td class=\"sel\">${f(r.vol,2,\"%\")}</td><td class=\"sel\">${f(r.mdd,2,\"%\")}</td></tr>`)")
    t = rep(t, "const v=d[s][ph.value][m];const b=s===\"EW PORT\"?' style=\"font-weight:700\"':\"\";return m===\"ir\"?",
            "const v=d[s][ph.value][m];const b=s===\"EW PORT\"?' style=\"font-weight:700\"':\"\";if((t.cols||D.cols).find(c=>c.key===ph.value).years===\"\")return `<td${b}></td>`;return m===\"ir\"?")
t = rep(t, "Section 1: Within-Asset-Class Correlation", "Section 1: Within-Bucket Correlation")
t = rep(t, "Select asset class</h3><label>Asset class: <select", "Select bucket</h3><label>Bucket: <select")
t = rep(t, "Section 2: Cross-Asset-Class Correlation", "Section 2: Cross-Bucket Correlation")
t = rep(t, "Trailing correlation between two asset classes' own portfolios, 2012 onward.", "Trailing correlation between two buckets' own portfolios, 2012 onward.")

out = R / f"Analysis/Final_Research_Dashboard_2012_{TAG}.html"
out.write_text(b + "<script>\nconst D=" + json.dumps(data) + ";\n" + t, encoding="utf8")
print("written", out, out.stat().st_size // 1024, "KB")
