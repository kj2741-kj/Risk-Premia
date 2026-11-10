"""Commodity and bucket rankings by Sharpe ratio (return / volatility, no risk-free rate) -> Analysis/Commodity_Rankings_<tag>.html (2026-10-31; new buckets)
Derived from rankings_page.py: reads outputs/final_dashboard_<tag>/final_v3.json and products_nets.pkl (tag 0930 or 1029, env FD_TAG) (analyze_v3.py, compute_products_v3.py); sectors = the seven buckets (the six research buckets and US Power).
Per commodity: each risk-premium sleeve (Momentum, Carry V2, Carry-Momentum V3, Value, Skewness) and two mini-portfolios of the five sleeves (Equal Weight, Inverse Vol 63d, lagged).
Per asset class: the same sleeves plus EW PORT and Inverse Vol, from the dashboards' own series. Coloured by sector (= asset class). Basis: the 2012-start variant (P1-P3). Reads outputs/final_dashboard*/final_v2.json and the products pickles. Run from the repo root."""
import sys, json, pickle
from pathlib import Path

sys.path.insert(0, "scripts/final_dashboard")
from fd_config import TAGS, current_tag, out_dir, check_run
TAG = current_tag()
check_run(TAG)

sys.path.insert(0, "research"); sys.path.insert(0, "research/configs"); sys.path.insert(0, "scripts")
import pandas as pd
from engine import combine_returns
from run_regime_table import _metrics

SLEEVES = ["Momentum", "Carry", "CarryMom", "Value", "Skewness"]
BUCKETS = {"metals": "Metals", "petroleum": "Petroleum", "pen": "Gas and Emissions", "ngl": "NGL", "precious": "Precious", "agri": "Agriculture", "power": "US Power"}
PRODUCTS = [("metals", "metals", p) for p in ["Copper", "Aluminium", "Lead", "Zinc"]] + [("petroleum", "energy", p) for p in ["WTI", "Brent", "RBOB", "HeatingOil"]] \
    + [("pen", "energy", "NatGas"), ("pen", "emissions", "TTF"), ("pen", "emissions", "UKGas"), ("pen", "emissions", "EUA")] + [("ngl", "ngl", p) for p in ["Ethane", "Propane", "Butane"]] + [("ngl", "naphtha", "Naphtha")] \
    + [("precious", "precious", p) for p in ["Gold", "Silver", "Platinum", "Palladium"]] + [("agri", "agri", p) for p in ["Corn", "Wheat", "Soybean", "SoybeanOil", "Coffee", "Sugar"]] \
    + [("power", "power", p) for p in ["PJM_Peak", "PJM_OffPeak", "ERCOT_Peak", "ERCOT_OffPeak", "MISO_Peak"]]
CLASSES = list(BUCKETS.items())
import os
BASES = [(f"2012 start, data to {TAGS[TAG]['cutoff']}", str(out_dir(TAG)), "products_nets.pkl",
          [("full", "Full 2012-2026", "2012-01-01", None), ("p1", "P1 2012-2016", "2012-01-01", "2016-12-31"), ("p2", "P2 2017-2021", "2017-01-01", "2021-12-31"),
           ("p3", "P3 2022-2026", "2022-01-01", None), ("y26", "2026 YTD", "2026-01-01", None)])]
import csv
LIQ = {r["product"]: r for r in csv.DictReader(open("Analysis/Liquidity_Cal2025_results.csv", encoding="utf8"))}
LIQ.update({r["product"]: r for r in csv.DictReader(open("Analysis/Power_Liquidity_Cal2025_results.csv", encoding="utf8"))})     # the five US Power series   # Calendar-2025 snapshot, K = USD 1M: L_strip = K / x (days), x_strip = x (USD m of one-sigma risk traded per day)
pack = lambda m: [None if pd.isna(m[k]) else round(float(m[k]), 3) for k in ("ir", "ret", "vol", "mdd")]
PJ = json.load(open(f"Analysis/_power_build/power_tab_{TAG}.json"))      # US Power: its own tab, products and windows (Full from 2017, no P1)
PDISP = {"PJM_Peak": "PJM Peak", "PJM_OffPeak": "PJM OffPeak", "ERCOT_Peak": "ERCOT Peak", "ERCOT_OffPeak": "ERCOT OffPeak", "MISO_Peak": "MISO Peak"}
DATA = {}
for name, d, pkl, wins in BASES:
    res = json.load(open(f"{d}/final_v3.json"))
    nets, _ = pickle.load(open(f"{d}/{pkl}", "rb"))
    prods = []
    for bk, a, p in PRODUCTS:
        src = PJ["products"] if bk == "power" else res["products"]
        vals = {s: {w: pack(src[f"{a}|{p}"][s][w]) for w, *_ in wins} for s in SLEEVES}
        lst = [nets[(a, p)][s] for s in SLEEVES]
        for col, ser in (("EW-5", combine_returns(lst, "equal_weight")), ("IV-5", combine_returns(lst, "inverse_vol", vol_window=63))):
            if bk == "power":      # Full from 2017-01-01 (every sleeve live), P1 not available
                vals[col] = {w: ([None] * 4 if w == "p1" else pack(_metrics(ser.loc["2017-01-01" if w == "full" else st:e] if e else ser.loc["2017-01-01" if w == "full" else st:]))) for w, _, st, e in wins}
            else:
                vals[col] = {w: pack(_metrics(ser.loc[st:e] if e else ser.loc[st:])) for w, _, st, e in wins}
        prods.append(dict(name=PDISP.get(p, p), asset=BUCKETS[bk], vals=vals, L=float(LIQ[p]["L_strip"]), X=float(LIQ[p]["x_strip"])))
    classes = []
    for key, label in CLASSES:
        vals = {}
        tab = PJ["tab"] if key == "power" else res["tabs"][key]
        for r_i, row in enumerate(tab["windows"][wins[0][0]]):
            vals[row["name"]] = {w: pack(tab["windows"][w][r_i]) for w, *_ in wins}
        classes.append(dict(name=label, vals=vals))
    DATA[name] = dict(windows=[dict(key=w, label=l) for w, l, *_ in wins], products=prods, classes=classes)

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Commodity Rankings (2012 start)</title>
<style>
:root{--bg:#fff;--fg:#1f2d3d;--muted:#667;--line:#d5dbe2;--card:#f6f8fa;--c0:#2f6fb5;--c1:#d9792b;--c2:#c9a227;--c3:#8a5fb0;--c4:#3f9b5a;--c5:#c2185b;--c6:#00897b}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#12171d;--fg:#dfe5ec;--muted:#98a4b3;--line:#333d49;--card:#1b222b;--c0:#5b97dd;--c1:#f0954a;--c2:#e0bd4a;--c3:#b48cd8;--c4:#5cbf7b;--c5:#e0608f;--c6:#36b3a6}}
body{margin:0;background:var(--bg);color:var(--fg);font-family:Calibri,Arial,sans-serif}.wrap{max-width:1180px;margin:0 auto;padding:18px 16px}
h1{font-size:23px;margin:0 0 4px}h2{font-size:17px;margin:26px 0 6px}.note{color:var(--muted);font-size:13px;margin:2px 0 8px}
.ctl{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:8px 0}button{font:inherit;padding:2px 8px;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:4px;cursor:pointer}select{font:inherit;padding:3px 6px;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:4px}
.leg span{display:inline-flex;align-items:center;margin-right:14px;font-size:13px}.leg i{width:12px;height:12px;border-radius:3px;margin-right:5px;display:inline-block}
.ts{overflow-x:auto}table{border-collapse:collapse;font-size:12.5px}th,td{border:1px solid var(--line);padding:3px 7px;text-align:right;white-space:nowrap}
th{background:var(--card)}th.srt{cursor:pointer;user-select:none}th.srt:hover{text-decoration:underline}td:first-child,th:first-child{text-align:left}td.nm i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
svg{width:100%;height:auto;display:block}svg text{fill:var(--fg);font-size:11px}.axis{stroke:var(--line)}.dl{margin:2px 0 6px}.dl button{margin-right:6px;font-size:12px}
</style></head><body><div class="wrap"><h1>Commodity and asset-class rankings by Sharpe ratio</h1>
<p class="note">Sharpe ratio here is annualised return divided by annualised volatility (no risk-free rate), net of costs, as in the dashboards. Colour = sector (bucket: Metals, Petroleum, Gas and Emissions, NGL, Precious, Agriculture, US Power). Basis: the 2012-start dashboard (see its Notes tab for the data end date); US Power reports from 2017 (its data start in 2015 and Value needs two years of F3), so its Full column starts in 2017 and its P1 cells are empty. Ranks are 1 = best. Mini-portfolios blend a commodity's five sleeves by Equal Weight (EW-5) or Inverse Vol (IV-5, 63-day, lagged one day).</p>
<div class="ctl"><label>Period <select id="period"></select></label></div>
<div class="leg" id="leg"></div>
<h2>1. Buckets (sector portfolios)</h2><p class="note">Equal-weighted across each bucket's commodities, from the dashboard tabs. Click any column heading to sort (click again to reverse); the table starts sorted by the EW PORT. The small number is the rank among the seven rows for that column (six in P1, where US Power has no value).</p><div class="ts" id="cheat"></div>
<h2>2. Commodities</h2><p class="note">Click any column heading to sort by it (click again to reverse); the table starts sorted by the EW mini-portfolio. Cell colour: green positive, red negative; the small number is the rank among the __NPROD__ commodities for that column (27 in P1, where the five US Power series have no value). The last two columns are the Calendar-2025 liquidity snapshot and do not depend on the Period: Time to trade 1 sigma risk (in Days) = K / x with K = USD 1M of one-sigma daily risk, and Risk Millions per day = x, the USD millions of one-sigma risk the market trades per day (average daily volume x price x volatility x contract multiplier). For both, rank 1 = most liquid (fewest days, most risk per day), and the cells are not coloured.</p><div class="ts" id="heat"></div>
<h2>3. Bar charts by risk premium</h2><div class="ctl"><label>Risk premium <select id="prem"></select></label></div><h3>Buckets</h3><div id="cbars"></div><h3>Commodities</h3><div id="bars"></div>
<h2>4. Liquidity (Calendar 2025)</h2><p class="note">Calendar-2025 snapshot, the same figures as the last two columns of the Commodities table; it does not depend on the Period or Risk premium selections. Both charts use a log scale (each gridline is ten times the previous one) because the commodities span more than five orders of magnitude. Time to trade 1 sigma risk (in Days) = K / x with K = USD 1M of one-sigma daily risk; sorted from the fewest days (most liquid, shortest bar). Risk Millions per day = x, the USD millions of one-sigma risk the market trades per day; sorted from the most (most liquid, longest bar).</p>
<h3>Time to trade 1 sigma risk (in Days)</h3><div id="lbars"></div><h3>Risk Millions per day</h3><div id="xbars"></div>
</div><script>
const DATA=__DATA__;
const SECT=["Metals","Petroleum","Gas and Emissions","NGL","Precious","Agriculture","US Power"],COL={"Metals":"var(--c0)","Petroleum":"var(--c1)","Gas and Emissions":"var(--c5)","NGL":"var(--c3)","Precious":"var(--c2)","Agriculture":"var(--c4)","US Power":"var(--c6)"};
const PREM=[["Momentum","Momentum"],["Carry","Carry (V2)"],["CarryMom","Carry-Momentum (V3)"],["Value","Value"],["Skewness","Skewness"],["EW-5","Mini-portfolio EW (5 sleeves)"],["IV-5","Mini-portfolio Inverse Vol (5 sleeves)"]];
const CPREM=[["Momentum","Momentum"],["Carry","Carry (V2)"],["CarryMom","Carry-Momentum (V3)"],["Value","Value"],["Skewness","Skewness"],["EW PORT","EW PORT (5 sleeves)"],["Inverse Vol","Inverse Vol (5 sleeves)"]];
const $=id=>document.getElementById(id),f2=v=>v==null?"":v.toFixed(2);
let SORT=null,SORTC=null;const CH={};
const fL=v=>v==null?"n/a":String(Number(v.toPrecision(3))),fX=v=>v==null?"n/a":(v>=100?Math.round(v).toLocaleString("en-US"):(v>=10?v.toFixed(1):(v>=1?v.toFixed(2):String(Number(v.toPrecision(2))))));
const LCOLS=[["__L","Time to trade 1 sigma risk (in Days)",1],["__X","Risk Millions per day",-1]];   // [key, heading, default sort direction]
$("leg").innerHTML=SECT.map(s=>`<span><i style="background:${COL[s]}"></i>${s}</span>`).join("");
const BASIS=Object.keys(DATA)[0];
$("prem").innerHTML=PREM.map(p=>`<option value="${p[0]}">${p[1]}</option>`).join("");
function setPeriods(){const w=DATA[BASIS].windows;$("period").innerHTML=w.map(x=>`<option value="${x.key}">${x.label}</option>`).join("");}
function tint(v){if(v==null)return"transparent";const a=Math.min(Math.abs(v)/1.2,1)*0.55;return v>=0?`rgba(63,155,90,${a})`:`rgba(200,60,50,${a})`;}
function bars(host,rows,title,vname){CH[host.id]={title,vname,rows}; // rows: [{name,sector,v}] already sorted
  const W=900,rh=19,L=150,H=rows.length*rh+30,vals=rows.map(r=>r.v||0),mx=Math.max(0.2,...vals.map(Math.abs)),x0=L+(W-L-60)/2,sc=(W-L-60)/2/mx;
  let s=`<svg viewBox="0 0 ${W} ${H}"><line class="axis" x1="${x0}" y1="8" x2="${x0}" y2="${H-18}"/>`;
  rows.forEach((r,i)=>{const y=12+i*rh,w=(r.v||0)*sc,x=w>=0?x0:x0+w;
    s+=`<text x="${L-8}" y="${y+11}" text-anchor="end">${i+1}. ${r.name}</text><rect x="${x}" y="${y}" width="${Math.abs(w)}" height="${rh-5}" rx="2" fill="${COL[r.sector]||'var(--c0)'}"><title>${r.name}: ${f2(r.v)}</title></rect>
    <text x="${w>=0?x0+w+5:x0+w-5}" y="${y+11}" text-anchor="${w>=0?'start':'end'}">${f2(r.v)}</text>`;});
  host.innerHTML=s+"</svg>";}
function logbars(host,rows,fmt,title,vname){CH[host.id]={title,vname,rows}; // rows: [{name,sector,v}] already sorted; log10 axis with a gridline at every power of ten
  const W=900,rh=19,L=150,R=70,H=rows.length*rh+44,pw=W-L-R,lv=rows.map(r=>Math.log10(r.v)),lo=Math.floor(Math.min(...lv)),hi=Math.ceil(Math.max(...lv)),xs=v=>L+(Math.log10(v)-lo)/(hi-lo)*pw;
  let s=`<svg viewBox="0 0 ${W} ${H}">`;
  for(let d=lo;d<=hi;d++){const x=L+(d-lo)/(hi-lo)*pw;s+=`<line class="axis" x1="${x}" y1="8" x2="${x}" y2="${H-26}"/><text x="${x}" y="${H-10}" text-anchor="middle">${String(Number("1e"+d))}</text>`;}
  rows.forEach((r,i)=>{const y=12+i*rh,w=xs(r.v)-L;
    s+=`<text x="${L-8}" y="${y+11}" text-anchor="end">${i+1}. ${r.name}</text><rect x="${L}" y="${y}" width="${w}" height="${rh-5}" rx="2" fill="${COL[r.sector]||'var(--c0)'}"><title>${r.name}: ${fmt(r.v)}</title></rect><text x="${xs(r.v)+5}" y="${y+11}">${fmt(r.v)}</text>`;});
  host.innerHTML=s+"</svg>";}
function liqbars(){
  const P=DATA[BASIS].products.map(x=>({name:x.name,sector:x.asset,L:x.L,X:x.X}));
  logbars($("lbars"),[...P].sort((a,b)=>a.L-b.L).map(x=>({name:x.name,sector:x.sector,v:x.L})),fL,"Time to trade 1 sigma risk (days), Calendar 2025","Time to trade 1 sigma risk (days)");
  logbars($("xbars"),[...P].sort((a,b)=>b.X-a.X).map(x=>({name:x.name,sector:x.sector,v:x.X})),fX,"Risk turnover (USD million per day), Calendar 2025","Risk turnover (USD million per day)");}
function render(){
  const D=DATA[BASIS],w=$("period").value,p=$("prem").value;
  const P=D.products.map(x=>({name:x.name,sector:x.asset,vals:x.vals,L:x.L,X:x.X}));
  const sorted=[...P].sort((a,b)=>(b.vals[p][w][0]??-9)-(a.vals[p][w][0]??-9));
  bars($("bars"),sorted.map(x=>({name:x.name,sector:x.sector,v:x.vals[p][w][0]})).filter(x=>x.v!=null),"Commodities: "+$("prem").selectedOptions[0].text+", Sharpe ratio, "+$("period").selectedOptions[0].text,"Sharpe ratio");
  // heat table with ranks
  const rank={};PREM.forEach(([k])=>{const o=[...P].sort((a,b)=>(b.vals[k][w][0]??-9)-(a.vals[k][w][0]??-9));rank[k]={};o.forEach((x,i)=>rank[k][x.name]=i+1);});
  const rankL={},rankX={};[...P].sort((a,b)=>a.L-b.L).forEach((x,i)=>rankL[x.name]=i+1);[...P].sort((a,b)=>b.X-a.X).forEach((x,i)=>rankX[x.name]=i+1);
  const sk=SORT?SORT.k:"EW-5",dir=SORT?SORT.d:-1,isStr=sk==="__name"||sk==="__sector";
  const val=x=>sk==="__name"?x.name:(sk==="__sector"?x.sector:(sk==="__L"?x.L:(sk==="__X"?x.X:x.vals[sk][w][0])));
  const rows=[...P].sort((a,b)=>isStr?dir*String(val(a)).localeCompare(String(val(b))):dir*((val(a)??-9)-(val(b)??-9)));
  const arrow=k=>sk===k?(dir<0?" &#9660;":" &#9650;"):"";
  $("heat").innerHTML="<table><tr><th class='srt' data-k='__name'>Commodity"+arrow("__name")+"</th><th class='srt' data-k='__sector'>Sector"+arrow("__sector")+"</th>"+PREM.map(q=>`<th class="srt" data-k="${q[0]}">${q[1]}${arrow(q[0])}</th>`).join("")+LCOLS.map(q=>`<th class="srt" data-k="${q[0]}">${q[1]}${arrow(q[0])}</th>`).join("")+"</tr>"+rows.map(x=>`<tr><td class="nm"><i style="background:${COL[x.sector]}"></i>${x.name}</td><td>${x.sector}</td>`+PREM.map(([k])=>{const v=x.vals[k][w][0];return `<td style="background:${tint(v)}">${v==null?"":f2(v)+" <sup>"+rank[k][x.name]+"</sup>"}</td>`;}).join("")+`<td>${fL(x.L)} <sup>${rankL[x.name]}</sup></td><td>${fX(x.X)} <sup>${rankX[x.name]}</sup></td></tr>`).join("")+"</table>";
  document.querySelectorAll("#heat th.srt").forEach(th=>th.onclick=()=>{const k=th.dataset.k,st=k==="__name"||k==="__sector";SORT=(SORT&&SORT.k===k)?{k,d:-SORT.d}:(!SORT&&"EW-5"===k?{k,d:1}:{k,d:(st||k==="__L")?1:-1});render();});
  // asset classes
  const cp=CPREM.map(x=>x[0]).includes(p)?p:(p==="EW-5"?"EW PORT":(p==="IV-5"?"Inverse Vol":"Momentum"));
  const C=D.classes,csorted=[...C].sort((a,b)=>(b.vals[cp][w][0]??-9)-(a.vals[cp][w][0]??-9));
  bars($("cbars"),csorted.map(c=>({name:c.name,sector:c.name,v:c.vals[cp][w][0]})).filter(x=>x.v!=null),"Buckets: "+CPREM.find(q=>q[0]===cp)[1]+", Sharpe ratio, "+$("period").selectedOptions[0].text,"Sharpe ratio");
  const crank={};CPREM.forEach(([k])=>{const o=[...C].sort((a,b)=>(b.vals[k][w][0]??-9)-(a.vals[k][w][0]??-9));crank[k]={};o.forEach((x,i)=>crank[k][x.name]=i+1);});
  const ck=SORTC?SORTC.k:"EW PORT",cd=SORTC?SORTC.d:-1,cs_=ck==="__name";
  const cv=c=>cs_?c.name:c.vals[ck][w][0];
  const cs=[...C].sort((a,b)=>cs_?cd*String(cv(a)).localeCompare(String(cv(b))):cd*((cv(a)??-9)-(cv(b)??-9)));
  const carrow=k=>ck===k?(cd<0?" &#9660;":" &#9650;"):"";
  $("cheat").innerHTML="<table><tr><th class='srt' data-k='__name'>Bucket"+carrow("__name")+"</th>"+CPREM.map(q=>`<th class="srt" data-k="${q[0]}">${q[1]}${carrow(q[0])}</th>`).join("")+"</tr>"+cs.map(c=>`<tr><td class="nm"><i style="background:${COL[c.name]}"></i>${c.name}</td>`+CPREM.map(([k])=>{const v=c.vals[k][w][0];return `<td style="background:${tint(v)}">${v==null?"":f2(v)+" <sup>"+crank[k][c.name]+"</sup>"}</td>`;}).join("")+"</tr>").join("")+"</table>";
  document.querySelectorAll("#cheat th.srt").forEach(th=>th.onclick=()=>{const k=th.dataset.k,st=k==="__name";SORTC=(SORTC&&SORTC.k===k)?{k,d:-SORTC.d}:(!SORTC&&"EW PORT"===k?{k,d:1}:{k,d:st?1:-1});render();});
}
$("period").onchange=render;$("prem").onchange=render;
setPeriods();render();liqbars();
// ---- downloads: every bar chart can be saved as a PNG image or as the CSV behind it (rank, name, sector, value, in the order shown)
function saveBlob(blob,name){const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),4000);}
function dlName(id,ext){return ("Commodity_Rankings___TAG___"+CH[id].title).replace(/[^A-Za-z0-9]+/g,"_").replace(/^_+|_+$/g,"")+"."+ext;}
function dlCSV(id){const m=CH[id],q=x=>'"'+String(x).replace(/"/g,'""')+'"';
  const lines=[["Rank","Name","Sector",m.vname].map(q).join(",")].concat(m.rows.map((x,i)=>[i+1,q(x.name),q(x.sector),x.v==null?"":x.v].join(",")));
  saveBlob(new Blob(["\ufeff"+lines.join("\r\n")],{type:"text/csv;charset=utf-8"}),dlName(id,"csv"));}
function dlPNG(id){const m=CH[id],svg=$(id).querySelector("svg"),cs=getComputedStyle(document.documentElement),g=n=>cs.getPropertyValue(n).trim(),NS="http://www.w3.org/2000/svg";
  const vb=svg.viewBox.baseVal,W=vb.width,H=vb.height,T=32,c=svg.cloneNode(true);
  c.setAttribute("xmlns",NS);c.setAttribute("viewBox","0 0 "+W+" "+(H+T));c.setAttribute("width",W);c.setAttribute("height",H+T);
  c.querySelectorAll("[fill]").forEach(e=>{const k=/var\((--[a-z0-9]+)\)/.exec(e.getAttribute("fill"));if(k)e.setAttribute("fill",g(k[1]));});
  c.querySelectorAll("text").forEach(e=>{e.setAttribute("fill",g("--fg"));e.setAttribute("font-size","11");e.setAttribute("font-family","Calibri,Arial,sans-serif");});
  c.querySelectorAll(".axis").forEach(e=>e.setAttribute("stroke",g("--line")));
  const inner=document.createElementNS(NS,"g");inner.setAttribute("transform","translate(0,"+T+")");while(c.firstChild)inner.appendChild(c.firstChild);c.appendChild(inner);
  const bg=document.createElementNS(NS,"rect");bg.setAttribute("width",W);bg.setAttribute("height",H+T);bg.setAttribute("fill",g("--bg"));c.insertBefore(bg,inner);
  const t=document.createElementNS(NS,"text");t.setAttribute("x",10);t.setAttribute("y",21);t.setAttribute("fill",g("--fg"));t.setAttribute("font-size","15");t.setAttribute("font-weight","bold");t.setAttribute("font-family","Calibri,Arial,sans-serif");t.textContent=m.title;c.appendChild(t);
  const url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(c)],{type:"image/svg+xml;charset=utf-8"})),img=new Image();
  img.onload=()=>{const k=2,cv=document.createElement("canvas");cv.width=W*k;cv.height=(H+T)*k;const x=cv.getContext("2d");x.scale(k,k);x.drawImage(img,0,0,W,H+T);URL.revokeObjectURL(url);cv.toBlob(b=>saveBlob(b,dlName(id,"png")),"image/png");};
  img.src=url;}
["cbars","bars","lbars","xbars"].forEach(id=>{const h=$(id),d=document.createElement("div");d.className="dl";d.innerHTML="<button onclick=\"dlPNG('"+id+"')\">Download PNG</button><button onclick=\"dlCSV('"+id+"')\">Download CSV</button>";h.parentNode.insertBefore(d,h);});

</script></body></html>"""
_out = f"Analysis/Commodity_Rankings_{TAG}.html"
Path(_out).write_text(PAGE.replace("__DATA__", json.dumps(DATA)).replace("__NPROD__", str(len(PRODUCTS))).replace("__TAG__", TAG), encoding="utf8")
print("written", _out)
