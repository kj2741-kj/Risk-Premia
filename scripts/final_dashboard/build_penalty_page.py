"""Liquidity-penalty version of the research dashboard (2026-11-15) -> Analysis/Final_Research_Dashboard_2012_0930_penalty.html + Analysis/penalty_0930/pen_<model>_<capital>.js
The committed page Analysis/Final_Research_Dashboard_2012_0930.html (the one on the Vercel app) is NOT touched: this script reads it as its template and adds
  * a control bar (penalty model: none / square-root impact / convex past a threshold; book capital: USD 100M, 500M, 1B, 5B) that reloads the page with ?pen=<model>_<capital>;
  * a loader that, for that choice, pulls pen/pen_<model>_<capital>.js (scenario data) before the page script runs, and a merge that replaces the tabs' performance windows, the by-product tables,
    the equity curves, the All-buckets / By-Style / Cross-Pair results with the penalised ones (correlations stay on the unpenalised returns and say so);
  * a methodology block with the parameters and a participation table (share of one day's strip volume that one full sleeve position trades, per product, at the chosen capital).
With no ?pen the page equals the committed one apart from the control bar. Scenario data: analyze_v3.py with FD_PENALTY=<model>:<capital in USD millions> (outputs/final_dashboard_0930/).
Run from the repo root after those runs:  python scripts/final_dashboard/build_penalty_page.py"""
import json
import re
import sys
from pathlib import Path

sys.path[:0] = ["scripts/final_dashboard"]
import numpy as np
import liquidity_penalty as L
from fd_config import BUCKETS

TAG = "0930"
OUT = Path(f"outputs/final_dashboard_{TAG}")
SRC = Path(f"Analysis/Final_Research_Dashboard_2012_{TAG}.html")
DST = Path(f"Analysis/Final_Research_Dashboard_2012_{TAG}_penalty.html")
PEN_DIR = Path(f"Analysis/penalty_{TAG}")
PEN_DIR.mkdir(exist_ok=True)
MODEL_LABEL = {"sqrt": "Square-root above threshold", "linear": "Linear above threshold"}
PRODUCT_LABEL = {"SingaporeGasoil": "Gas Oil", "HeatingOil": "Heating Oil", "NatGas": "Henry Hub", "UKGas": "UK Gas", "NatGasoline": "Natural Gasoline", "LiveCattle": "Live Cattle"}

vol = L.daily_notional_volume()
w = L.book_weights(BUCKETS)     # the 30 bucket products only: US Power is not in the book and is not penalised (user, 2026-11-15)

SCEN = [(m, c, "b") for m in L.MODELS for c in L.CAPITALS_M] + [("none", 0, "b")]     # variant b only (user, 2026-11-15): penalty and 5 bps netted over a product's sleeves; none_0_b = the 5 bps netted, no penalty
CPEN = json.load(open(OUT / "classical_ng_pen_b_page.json")); CPEN1 = json.load(open(OUT / "classical_pen_b_page.json"))     # classical_penalty.py: Classical + New gen Energy tab under each scenario (14 products, 1/14 of the capital each)
for model, cap, var in SCEN:
    suf = "_b"
    r = json.load(open(OUT / f"final_v3_pen_{model}_{cap}{suf}.json"))
    part = {}
    if model != "none":
        for (a, p), wt in w.items():
            part[PRODUCT_LABEL.get(p, p)] = round(float(min(L.per_unit_participation(cap, wt, vol[p]), 99.0)), 5)
    tabs = {k: dict(windows=v["windows"]) for k, v in r["tabs"].items()}
    scen = dict(tabs=tabs, products=r["products"], equity=r["equity"],
                combined=dict(windows=r["combined"]["windows"]), bystyle=dict(windows=r["bystyle"]["windows"]), crosspair=r["crosspair"],
                classical_ng=CPEN["none_0" if model == "none" else f"{model}_{cap}"], classical=CPEN1["none_0" if model == "none" else f"{model}_{cap}"], part=part, model=model, variant=var, capital_m=cap, notional=round(cap * 1e6 * L.LEVERAGE), lev=L.LEVERAGE)
    js = "window.__PEN=" + json.dumps(scen, separators=(",", ":")) + ";"
    (PEN_DIR / f"pen_{model}_{cap}{suf}.js").write_text(js, encoding="utf8")
    print("wrote", model, cap, var, len(js) // 1024, "KB")

h = SRC.read_text(encoding="utf8")


def once(old, new):
    global h
    assert h.count(old) == 1, (old[:60], h.count(old))
    h = h.replace(old, new)


once("<title>Risk Premia: Final Research Dashboard (2012 start, three periods, data to 2026-09-30)</title>",
     "<title>Risk Premia: Final Research Dashboard with liquidity penalty (2012 start, data to 2026-09-30)</title>")
# loader: scenario data must be in place before the page script runs
once("</head><body>", '<script>(function(){var q=new URLSearchParams(location.search).get("pen");if(q&&/^(sqrt|linear)_\\d+_b$|^none_0_b$/.test(q))document.write(\'<script src="penalty_' + TAG + '/pen_\'+q+\'.js"><\\/script>\');})();</script></head><body>')
# merge right after const D=...;
m = re.search(r"<script>\nconst D=(.*?);\n", h, re.S)
merge = ("if(window.__PEN){const P=window.__PEN;for(const k in P.tabs)D.tabs[k].windows=P.tabs[k].windows;Object.assign(D.products,P.products);Object.assign(D.equity,P.equity);"
         "D.combined.windows=P.combined.windows;D.bystyle.windows=P.bystyle.windows;D.crosspair=P.crosspair;D.classical.classical_ng.windows=P.classical_ng.windows;D.equity.classical_ng=P.classical_ng.equity;D.classical.classical.windows=P.classical.windows;D.equity.classical=P.classical.equity;}\n")
h = h[:m.end()] + merge + h[m.end():]

CSS = ("<style>.penbar{background:rgba(224,140,40,.10);border:1px solid rgba(224,140,40,.55);border-left:4px solid #e08c28;border-radius:8px;padding:10px 14px;margin:10px 0;font-size:13px}"
       ".penbar select{border:2px solid #e08c28;font-weight:600;cursor:pointer;background:rgba(224,140,40,.12);border-radius:6px;padding:2px 6px}"
       ".penbar label{margin-right:14px}.penbar details{margin-top:8px}.penbar table{border-collapse:collapse;font-size:12px;margin:6px 0}.penbar th,.penbar td{border:1px solid rgba(128,128,128,.35);padding:2px 8px;text-align:right}"
       ".penbar td:first-child,.penbar th:first-child{text-align:left}.penbar .warn{color:#b3261e;font-weight:600}</style>")
once("</head><body>", CSS + "</head><body>")

BAR = f"""<div class="penbar" id="penbar"><b>Liquidity penalty</b> (extra market-impact cost on top of the flat 5 bps, all products) &nbsp;
<label>Model: <select id="pen-model"><option value="none">None (committed results, 5 bps per sleeve)</option><option value="flat">None (5 bps netted across sleeves)</option><option value="sqrt">{MODEL_LABEL['sqrt']}</option><option value="linear">{MODEL_LABEL['linear']}</option></select></label>
<label>Book capital: <select id="pen-cap">{''.join(f'<option value="{c}">USD {c/1000:g}B</option>' if c >= 1000 else f'<option value="{c}">USD {c}M</option>' for c in L.CAPITALS_M)}</select></label>
<span id="pen-status"></span>
<details><summary>How the penalty works</summary>
<p>Capital C is the whole book, fully invested at {L.LEVERAGE:g}x leverage: C of position notional, the same "+-1 unit of notional" the dashboard's returns already assume. A product takes its book weight
(1 / (7 x products in its bucket)) and splits it over its five sleeves, so one full unit of a sleeve's position is N = C x weight / 5 dollars.
The market's size is the 12-month strip's daily traded notional V (the Calendar-2025 risk turnover x of the liquidity note, CME plus ICE for NGL, divided by the product's 2025 daily vol; held fixed for every year, so 2012 is not thinner than 2025).
A day that trades <i>u</i> units (a change of position, plus a unit for a position held through a roll, the trades the 5 bps is charged on) has participation P = u x N / V, capped at 1 (one full day of volume), and pays, as a share of notional, nothing extra while P is below the threshold P0 = {int(L.P0*100)}% of daily volume and, above it, with E = P - P0:</p>
<ul><li><b>{MODEL_LABEL['sqrt']}:</b> u x Y x sigma x sqrt(E), with Y = {L.Y:g}</li>
<li><b>{MODEL_LABEL['linear']}:</b> u x sigma x a x E, with a = Y / sqrt(P0) = {L.Y/L.P0**0.5:.2f}</li></ul>
<p><b>Netting.</b> A product's five sleeves are added first: the product trades |change in the sum of its five sleeve positions| (plus a roll unit when the net position is rolled). The penalty and the flat 5 bps are charged once on that combined trade (offsetting sleeves pay nothing, stacked sleeves pay for the combined size), and the cost is split back to the sleeves in proportion to their own trades.
"None (5 bps netted)" is the same netting with no penalty, the fair comparison for the penalised views; "None (committed)" is the dashboard as published, 5 bps per sleeve.
The Classical (10 products, 1/10 of the capital each) and Classical + New gen Energy (14 products, 1/14 each) tabs are penalised too, with a larger share of capital per product than in the 30-product book.</p>
<p>sigma is the trailing 63-day volatility of the product's daily log return, lagged one day. The penalty is subtracted from each sleeve's net return before anything is combined. Correlations are computed on the unpenalised returns.
Bloomberg volume misses OTC-cleared swap volume, so the NGL and Naphtha penalties are upper bounds. Share of a day's volume traded by one full sleeve position at the chosen capital:</p>
<div id="pen-part"></div></details></div>
"""
once('<div class="tabs" id="tabbar"></div>', BAR + '<div class="tabs" id="tabbar"></div>')
JS = """<script>(function(){var q=new URLSearchParams(location.search).get("pen")||"none_0",pr=q.split("_"),M=document.getElementById("pen-model"),C=document.getElementById("pen-cap");
M.value=(pr[0]==="none"&&pr[2]==="b")?"flat":pr[0];if(pr[1]&&pr[0]!=="none")C.value=pr[1];
function go(){var u=location.pathname;if(M.value==="flat")u+="?pen=none_0_b";else if(M.value!=="none")u+="?pen="+M.value+"_"+C.value+"_b";location.href=u+location.hash;}
[M,C].forEach(function(e){e.addEventListener("change",go);});
var st=document.getElementById("pen-status");
if(window.__PEN){var P=window.__PEN,rows=Object.keys(P.part).map(function(k){return [k,P.part[k]];}).sort(function(a,b){return b[1]-a[1];});
 st.innerHTML=P.model==="none"?"<b>Active:</b> the flat 5 bps netted across each product's sleeves, no liquidity penalty. Every table and chart except Correlations uses it.":"<b>Active:</b> "+(P.model==="sqrt"?"square-root above the threshold":"linear above the threshold")+", penalty and 5 bps netted across a product's sleeves, book capital USD "+(P.capital_m>=1000?P.capital_m/1000+"B":P.capital_m+"M")+" (position notional USD "+(P.notional/1e6).toFixed(0)+"M at "+P.lev+"x leverage). Every table and chart on this page except Correlations is net of the penalty.";
 document.getElementById("pen-part").innerHTML=rows.length?"<table><thead><tr><th>Product</th><th>% of a day's volume per full unit</th></tr></thead><tbody>"+rows.map(function(r){return "<tr><td>"+r[0]+"</td><td"+(r[1]>=0.1?' class="warn"':"")+">"+(r[1]*100).toFixed(r[1]<0.01?3:1)+"%</td></tr>";}).join("")+"</tbody></table>":"";}
else{st.innerHTML="Showing the committed results (flat 5 bps per sleeve). Pick a model and capital to see the same dashboard net of the liquidity penalty.";document.getElementById("pen-part").innerHTML="";}
})();</script>"""
once('const HIDDEN_TABS=["all6"];', 'const HIDDEN_TABS=["all6"].concat(["power"]);')
once('<div id="panels"></div>', '<div id="panels"></div>' + JS)
DST.write_text(h, encoding="utf8")
print("wrote", DST, len(h) // 1024, "KB")
