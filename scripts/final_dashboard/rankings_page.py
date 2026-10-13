"""Commodity and asset-class rankings by Sharpe ratio (return / volatility, no risk-free rate) -> Analysis/Commodity_Rankings.html (2026-10-12)
Per commodity: each risk-premium sleeve (Momentum, Carry V2, Carry-Momentum V3, Value, Skewness) and two mini-portfolios of the five sleeves (Equal Weight, Inverse Vol 63d, lagged).
Per asset class: the same sleeves plus EW PORT and Inverse Vol, from the dashboards' own series. Coloured by sector (= asset class). Basis: the 2012-start variant (P1-P3). Reads outputs/final_dashboard*/final_v2.json and the products pickles. Run from the repo root."""
import sys, json, pickle
from pathlib import Path

sys.path.insert(0, "research"); sys.path.insert(0, "research/configs"); sys.path.insert(0, "scripts")
import pandas as pd
from engine import combine_returns
from run_regime_table import _metrics

SLEEVES = ["Momentum", "Carry", "CarryMom", "Value", "Skewness"]
ASSETS = {"metals": "Metals", "energy": "Energy", "ngl": "NGL", "precious": "Precious", "agri": "Agriculture"}
PRODUCTS = {"metals": ["Copper", "Aluminium", "Lead", "Zinc"], "energy": ["WTI", "Brent", "RBOB", "HeatingOil", "NatGas"],
            "ngl": ["Ethane", "Propane", "Butane", "Isobutane"], "precious": ["Gold", "Silver", "Platinum", "Palladium"],
            "agri": ["Corn", "Wheat", "Soybean", "SoybeanOil", "Coffee", "Sugar"]}
CLASSES = [("metals", "Metals"), ("energy", "Energy"), ("energy_exng", "Energy ex-NatGas"), ("ngl", "NGL"), ("precious", "Precious"), ("agri", "Agriculture")]
BASES = [("2012 start", "outputs/final_dashboard_2012", "products_2012_nets.pkl",
          [("full", "Full 2012-2026", "2012-01-01", None), ("p1", "P1 2012-2016", "2012-01-01", "2016-12-31"), ("p2", "P2 2017-2021", "2017-01-01", "2021-12-31"),
           ("p3", "P3 2022-2026", "2022-01-01", None)])]
pack = lambda m: [None if pd.isna(m[k]) else round(float(m[k]), 3) for k in ("ir", "ret", "vol", "mdd")]
DATA = {}
for name, d, pkl, wins in BASES:
    res = json.load(open(f"{d}/final_v2.json"))
    nets, _ = pickle.load(open(f"{d}/{pkl}", "rb"))
    prods = []
    for a, plist in PRODUCTS.items():
        for p in plist:
            vals = {s: {w: pack(res["products"][f"{a}|{p}"][s][w]) for w, *_ in wins} for s in SLEEVES}
            lst = [nets[(a, p)][s] for s in SLEEVES]
            for col, ser in (("EW-5", combine_returns(lst, "equal_weight")), ("IV-5", combine_returns(lst, "inverse_vol", vol_window=63))):
                vals[col] = {w: pack(_metrics(ser.loc[st:e] if e else ser.loc[st:])) for w, _, st, e in wins}
            prods.append(dict(name=p, asset=ASSETS[a], vals=vals))
    classes = []
    for key, label in CLASSES:
        vals = {}
        for r_i, row in enumerate(res["tabs"][key]["windows"][wins[0][0]]):
            vals[row["name"]] = {w: pack(res["tabs"][key]["windows"][w][r_i]) for w, *_ in wins}
        classes.append(dict(name=label, vals=vals))
    DATA[name] = dict(windows=[dict(key=w, label=l) for w, l, *_ in wins], products=prods, classes=classes)

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Commodity Rankings</title>
<style>
:root{--bg:#fff;--fg:#1f2d3d;--muted:#667;--line:#d5dbe2;--card:#f6f8fa;--c0:#2f6fb5;--c1:#d9792b;--c2:#c9a227;--c3:#8a5fb0;--c4:#3f9b5a}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#12171d;--fg:#dfe5ec;--muted:#98a4b3;--line:#333d49;--card:#1b222b;--c0:#5b97dd;--c1:#f0954a;--c2:#e0bd4a;--c3:#b48cd8;--c4:#5cbf7b}}
body{margin:0;background:var(--bg);color:var(--fg);font-family:Calibri,Arial,sans-serif}.wrap{max-width:1180px;margin:0 auto;padding:18px 16px}
h1{font-size:23px;margin:0 0 4px}h2{font-size:17px;margin:26px 0 6px}.note{color:var(--muted);font-size:13px;margin:2px 0 8px}
.ctl{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:8px 0}button{font:inherit;padding:2px 8px;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:4px;cursor:pointer}select{font:inherit;padding:3px 6px;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:4px}
.leg span{display:inline-flex;align-items:center;margin-right:14px;font-size:13px}.leg i{width:12px;height:12px;border-radius:3px;margin-right:5px;display:inline-block}
.ts{overflow-x:auto}table{border-collapse:collapse;font-size:12.5px}th,td{border:1px solid var(--line);padding:3px 7px;text-align:right;white-space:nowrap}
th{background:var(--card)}th.srt{cursor:pointer;user-select:none}th.srt:hover{text-decoration:underline}td:first-child,th:first-child{text-align:left}td.nm i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
svg{width:100%;height:auto;display:block}svg text{fill:var(--fg);font-size:11px}.axis{stroke:var(--line)}
</style></head><body><div class="wrap"><h1>Commodity and asset-class rankings by Sharpe ratio</h1>
<p class="note">Sharpe ratio here is annualised return divided by annualised volatility (no risk-free rate), net of costs, as in the dashboards. Colour = sector (asset class). Ranks are 1 = best. Mini-portfolios blend a commodity's five sleeves by Equal Weight (EW-5) or Inverse Vol (IV-5, 63-day, lagged one day).</p>
<div class="ctl"><label>Period <select id="period"></select></label></div>
<div class="leg" id="leg"></div>
<h2>1. Asset classes (sector portfolios)</h2><p class="note">Equal-weighted across each sector's commodities, from the dashboard tabs; Energy is shown with and without NatGas. Click any column heading to sort (click again to reverse); the table starts sorted by the EW PORT. The small number is the rank among the six rows for that column.</p><div class="ts" id="cheat"></div>
<h2>2. Commodities</h2><p class="note">Click any column heading to sort by it (click again to reverse); the table starts sorted by the EW mini-portfolio. Cell colour: green positive, red negative; the small number is the rank among the 23 commodities for that column.</p><div class="ts" id="heat"></div>
<h2>3. Bar charts by risk premium</h2><div class="ctl"><label>Risk premium <select id="prem"></select></label></div><h3>Asset classes</h3><div id="cbars"></div><h3>Commodities</h3><div id="bars"></div>
</div><script>
const DATA=__DATA__;
const SECT=["Metals","Energy","Precious","NGL","Agriculture"],COL={Metals:"var(--c0)",Energy:"var(--c1)",Precious:"var(--c2)",NGL:"var(--c3)",Agriculture:"var(--c4)"};
const PREM=[["Momentum","Momentum"],["Carry","Carry (V2)"],["CarryMom","Carry-Momentum (V3)"],["Value","Value"],["Skewness","Skewness"],["EW-5","Mini-portfolio EW (5 sleeves)"],["IV-5","Mini-portfolio Inverse Vol (5 sleeves)"]];
const CPREM=[["Momentum","Momentum"],["Carry","Carry (V2)"],["CarryMom","Carry-Momentum (V3)"],["Value","Value"],["Skewness","Skewness"],["EW PORT","EW PORT (5 sleeves)"],["Inverse Vol","Inverse Vol (5 sleeves)"]];
const $=id=>document.getElementById(id),f2=v=>v==null?"n/a":v.toFixed(2);
let SORT=null,SORTC=null;
$("leg").innerHTML=SECT.map(s=>`<span><i style="background:${COL[s]}"></i>${s}</span>`).join("");
const BASIS=Object.keys(DATA)[0];
$("prem").innerHTML=PREM.map(p=>`<option value="${p[0]}">${p[1]}</option>`).join("");
function setPeriods(){const w=DATA[BASIS].windows;$("period").innerHTML=w.map(x=>`<option value="${x.key}">${x.label}</option>`).join("");}
function tint(v){if(v==null)return"transparent";const a=Math.min(Math.abs(v)/1.2,1)*0.55;return v>=0?`rgba(63,155,90,${a})`:`rgba(200,60,50,${a})`;}
function bars(host,rows){ // rows: [{name,sector,v}] already sorted
  const W=900,rh=19,L=150,H=rows.length*rh+30,vals=rows.map(r=>r.v||0),mx=Math.max(0.2,...vals.map(Math.abs)),x0=L+(W-L-60)/2,sc=(W-L-60)/2/mx;
  let s=`<svg viewBox="0 0 ${W} ${H}"><line class="axis" x1="${x0}" y1="8" x2="${x0}" y2="${H-18}"/>`;
  rows.forEach((r,i)=>{const y=12+i*rh,w=(r.v||0)*sc,x=w>=0?x0:x0+w;
    s+=`<text x="${L-8}" y="${y+11}" text-anchor="end">${i+1}. ${r.name}</text><rect x="${x}" y="${y}" width="${Math.abs(w)}" height="${rh-5}" rx="2" fill="${COL[r.sector]||'var(--c0)'}"><title>${r.name}: ${f2(r.v)}</title></rect>
    <text x="${w>=0?x0+w+5:x0+w-5}" y="${y+11}" text-anchor="${w>=0?'start':'end'}">${f2(r.v)}</text>`;});
  host.innerHTML=s+"</svg>";}
function render(){
  const D=DATA[BASIS],w=$("period").value,p=$("prem").value;
  const P=D.products.map(x=>({name:x.name,sector:x.asset,vals:x.vals}));
  const sorted=[...P].sort((a,b)=>(b.vals[p][w][0]??-9)-(a.vals[p][w][0]??-9));
  bars($("bars"),sorted.map(x=>({name:x.name,sector:x.sector,v:x.vals[p][w][0]})));
  // heat table with ranks
  const rank={};PREM.forEach(([k])=>{const o=[...P].sort((a,b)=>(b.vals[k][w][0]??-9)-(a.vals[k][w][0]??-9));rank[k]={};o.forEach((x,i)=>rank[k][x.name]=i+1);});
  const sk=SORT?SORT.k:"EW-5",dir=SORT?SORT.d:-1,isStr=sk==="__name"||sk==="__sector";
  const val=x=>sk==="__name"?x.name:(sk==="__sector"?x.sector:x.vals[sk][w][0]);
  const rows=[...P].sort((a,b)=>isStr?dir*String(val(a)).localeCompare(String(val(b))):dir*((val(a)??-9)-(val(b)??-9)));
  const arrow=k=>sk===k?(dir<0?" &#9660;":" &#9650;"):"";
  $("heat").innerHTML="<table><tr><th class='srt' data-k='__name'>Commodity"+arrow("__name")+"</th><th class='srt' data-k='__sector'>Sector"+arrow("__sector")+"</th>"+PREM.map(q=>`<th class="srt" data-k="${q[0]}">${q[1]}${arrow(q[0])}</th>`).join("")+"</tr>"+rows.map(x=>`<tr><td class="nm"><i style="background:${COL[x.sector]}"></i>${x.name}</td><td>${x.sector}</td>`+PREM.map(([k])=>{const v=x.vals[k][w][0];return `<td style="background:${tint(v)}">${f2(v)} <sup>${rank[k][x.name]}</sup></td>`;}).join("")+"</tr>").join("")+"</table>";
  document.querySelectorAll("#heat th.srt").forEach(th=>th.onclick=()=>{const k=th.dataset.k,st=k==="__name"||k==="__sector";SORT=(SORT&&SORT.k===k)?{k,d:-SORT.d}:(!SORT&&"EW-5"===k?{k,d:1}:{k,d:st?1:-1});render();});
  // asset classes
  const cp=CPREM.map(x=>x[0]).includes(p)?p:(p==="EW-5"?"EW PORT":(p==="IV-5"?"Inverse Vol":"Momentum"));
  const C=D.classes,csorted=[...C].sort((a,b)=>(b.vals[cp][w][0]??-9)-(a.vals[cp][w][0]??-9));
  bars($("cbars"),csorted.map(c=>({name:c.name,sector:c.name==="Energy ex-NatGas"?"Energy":c.name,v:c.vals[cp][w][0]})));
  const crank={};CPREM.forEach(([k])=>{const o=[...C].sort((a,b)=>(b.vals[k][w][0]??-9)-(a.vals[k][w][0]??-9));crank[k]={};o.forEach((x,i)=>crank[k][x.name]=i+1);});
  const ck=SORTC?SORTC.k:"EW PORT",cd=SORTC?SORTC.d:-1,cs_=ck==="__name";
  const cv=c=>cs_?c.name:c.vals[ck][w][0];
  const cs=[...C].sort((a,b)=>cs_?cd*String(cv(a)).localeCompare(String(cv(b))):cd*((cv(a)??-9)-(cv(b)??-9)));
  const carrow=k=>ck===k?(cd<0?" &#9660;":" &#9650;"):"";
  $("cheat").innerHTML="<table><tr><th class='srt' data-k='__name'>Asset class"+carrow("__name")+"</th>"+CPREM.map(q=>`<th class="srt" data-k="${q[0]}">${q[1]}${carrow(q[0])}</th>`).join("")+"</tr>"+cs.map(c=>`<tr><td class="nm"><i style="background:${COL[c.name==="Energy ex-NatGas"?"Energy":c.name]}"></i>${c.name}</td>`+CPREM.map(([k])=>{const v=c.vals[k][w][0];return `<td style="background:${tint(v)}">${f2(v)} <sup>${crank[k][c.name]}</sup></td>`;}).join("")+"</tr>").join("")+"</table>";
  document.querySelectorAll("#cheat th.srt").forEach(th=>th.onclick=()=>{const k=th.dataset.k,st=k==="__name";SORTC=(SORTC&&SORTC.k===k)?{k,d:-SORTC.d}:(!SORTC&&"EW PORT"===k?{k,d:1}:{k,d:st?1:-1});render();});
}
$("period").onchange=render;$("prem").onchange=render;
setPeriods();render();
</script></body></html>"""
Path("Analysis/Commodity_Rankings.html").write_text(PAGE.replace("__DATA__", json.dumps(DATA)), encoding="utf8")
print("written Analysis/Commodity_Rankings.html")
