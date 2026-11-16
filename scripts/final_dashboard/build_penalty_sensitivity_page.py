"""Penalty sensitivity page in the style of Commodity_Rankings (2026-11-15) -> Analysis/Penalty_Sensitivity_0930.html (standalone, data embedded).
Input: outputs/final_dashboard_0930/penalty_sensitivity.json from penalty_sensitivity.py. Run from the repo root:  python scripts/final_dashboard/build_penalty_sensitivity_page.py"""
import json
from pathlib import Path

D = json.load(open("outputs/final_dashboard_0930/penalty_sensitivity.json"))
LABEL = {"petroleum": "Petroleum", "metals": "Metals", "precious": "Precious", "agri": "Agriculture", "softs": "Softs", "pen": "Gas and Emissions", "ngl": "NGL"}
D["buckets"] = {k: dict(v, label=LABEL.get(k, v["label"])) for k, v in D["buckets"].items()}
html = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Liquidity penalty sensitivity (Sharpe ratios)</title>
<style>
:root{--bg:#fff;--fg:#1f2d3d;--muted:#667;--line:#d5dbe2;--card:#f6f8fa;--c0:#2f6fb5;--c1:#d9792b;--c2:#c9a227;--c3:#8a5fb0;--c4:#3f9b5a;--c5:#c2185b;--c6:#00897b}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#12171d;--fg:#dfe5ec;--muted:#98a4b3;--line:#333d49;--card:#1b222b;--c0:#5b97dd;--c1:#f0954a;--c2:#e0bd4a;--c3:#b48cd8;--c4:#5cbf7b;--c5:#e0608f;--c6:#36b3a6}}
body{margin:0;background:var(--bg);color:var(--fg);font-family:Calibri,Arial,sans-serif}.wrap{max-width:1250px;margin:0 auto;padding:18px 16px}
h1{font-size:23px;margin:0 0 4px}h2{font-size:17px;margin:22px 0 6px}.note{color:var(--muted);font-size:13px;margin:2px 0 8px;line-height:1.45}
.ctl{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:10px 0}button,select{font:inherit;padding:3px 9px;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:4px;cursor:pointer}
button.on{background:var(--c0);color:#fff;border-color:var(--c0)}
.ts{overflow-x:auto}table{border-collapse:collapse;font-size:12.5px}th,td{border:1px solid var(--line);padding:3px 7px;text-align:right;white-space:nowrap}th{background:var(--card)}
th.srt{cursor:pointer;user-select:none}th.srt:hover{text-decoration:underline}td:first-child,th:first-child,td.sc,th.sc{text-align:left}td.nm i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
th.grp{text-align:center}td.base,th.base{border-right:3px solid var(--line)}sup{color:var(--muted);font-size:10px}
</style></head><body><div class="wrap"><h1>Liquidity penalty sensitivity: Sharpe ratios by portfolio level</h1>
<p class="note" id="intro"></p>
<div class="ctl"><span id="lv"></span><label>Weighting: <select id="wt"><option value="ew">Equal Weight</option><option value="iv">Inverse Vol</option></select></label>
<label>Period: <select id="win"></select></label></div>
<p class="note" id="desc"></p><div class="ts" id="tbl"></div>
<h2>How to read and how it is built</h2><div class="note" id="method"></div></div>
<script>
const D=__DATA__;
const $=id=>document.getElementById(id);
const LV=[["commodity","Individual commodities"],["bucket","Asset classes"],["pair","Commodity pairs"],["book","Cross-commodity portfolio"]];
const WL={full:"Full 2012-",p1:"P1 2012-16",p2:"P2 2017-21",p3:"P3 2022-",y26:"2026 YTD"};
const COL=["var(--c0)","var(--c1)","var(--c2)","var(--c3)","var(--c4)","var(--c5)","var(--c6)"];
const BK=Object.keys(D.buckets),f2=v=>v==null?"":v.toFixed(2);
const cap=c=>c>=1000?"$"+(c/1000)+"B":"$"+c+"M";
let level="commodity",SORT=null;
function tint(v){if(v==null)return"transparent";const a=Math.min(Math.abs(v)/1.2,1)*0.55;return v>=0?`rgba(63,155,90,${a})`:`rgba(200,60,50,${a})`;}
$("win").innerHTML=D.windows.map(w=>`<option value="${w}">${WL[w]}</option>`).join("");
$("lv").innerHTML=LV.map(([k,l])=>`<button data-k="${k}">${l}</button>`).join(" ");
const gl=BK.map(k=>D.buckets[k].label);
function rowsFor(lv,wt){ // [{name,sector,key,method}]
  if(lv==="commodity"){const r=[];BK.forEach((k,i)=>{Object.keys(D.res["commodity|0|none"]).filter(x=>x.startsWith(k+"|")).forEach(x=>r.push({name:x.split("|")[1],sector:D.buckets[k].label,col:COL[i],key:x,m:wt}));});return r;}
  if(lv==="bucket")return BK.map((k,i)=>({name:D.buckets[k].label,col:COL[i],key:k,m:wt}));
  if(lv==="book")return [["ew","ew","EW sleeves, EW across"],["ew","iv","EW sleeves, Inverse Vol across"],["iv","ew","Inverse Vol sleeves, EW across"],["iv","iv","Inverse Vol sleeves, Inverse Vol across"]].map(([s,a,n])=>({name:n,key:"book",m:s+"_"+a}));
  const r=[];for(let i=0;i<BK.length;i++)for(let j=i+1;j<BK.length;j++)r.push({name:D.buckets[BK[i]].label+" - "+D.buckets[BK[j]].label,key:BK[i]+"|"+BK[j],m:wt});return r;}
function cols(lv){const c=[{k:"b",h:"Base",res:`${lv}|0|none`}];D.models.forEach(m=>D.grid[lv].forEach(x=>c.push({k:m+x,h:cap(x),m,res:`${lv}|${x}|${m}`})));return c;}
function render(){
  const lv=level,wt=$("wt").value,w=$("win").value,C=cols(lv),R=rowsFor(lv,wt);
  R.forEach(r=>{r.v=C.map(c=>{const x=D.res[c.res][r.key];return x&&x[r.m]?x[r.m][w]:null;});});
  const rank=C.map((c,j)=>{const s=R.map(r=>r.v[j]).filter(v=>v!=null).sort((a,b)=>b-a);return v=>v==null?"":s.indexOf(v)+1;});
  if(!SORT)SORT={j:0,d:-1};
  const rows=R.slice().sort((a,b)=>SORT.j===-1?SORT.d*a.name.localeCompare(b.name):SORT.d*((a.v[SORT.j]??-99)-(b.v[SORT.j]??-99)));
  const arrow=j=>SORT.j===j?(SORT.d<0?" &#9660;":" &#9650;"):"";
  const sec=lv==="commodity";
  let h=`<table><tr><th rowspan="2" class="srt" data-j="-1">${LV.find(x=>x[0]===lv)[1]}${arrow(-1)}</th>${sec?'<th rowspan="2" class="sc">Sector</th>':""}<th rowspan="2" class="srt base" data-j="0">Base${arrow(0)}</th><th class="grp" colspan="${D.grid[lv].length}">Square-root above threshold</th><th class="grp" colspan="${D.grid[lv].length}">Linear above threshold</th></tr><tr>`;
  C.slice(1).forEach((c,i)=>{h+=`<th class="srt" data-j="${i+1}">${c.h}${arrow(i+1)}</th>`;});
  h+="</tr>";
  rows.forEach(r=>{h+=`<tr><td class="nm">${r.col?`<i style="background:${r.col}"></i>`:""}${r.name}</td>${sec?`<td class="sc">${r.sector}</td>`:""}`+r.v.map((v,j)=>`<td class="${j===0?"base":""}" style="background:${tint(v)}">${f2(v)}${v==null?"":" <sup>"+rank[j](v)+"</sup>"}</td>`).join("")+"</tr>";});
  $("tbl").innerHTML=h+"</table>";
  document.querySelectorAll("#tbl th.srt").forEach(th=>th.onclick=()=>{const j=+th.dataset.j;SORT=SORT.j===j?{j,d:-SORT.d}:{j,d:j===-1?1:-1};render();});
  document.querySelectorAll("#lv button").forEach(b=>b.classList.toggle("on",b.dataset.k===lv));
  const d={commodity:"Each row is one commodity's own five-premia portfolio, holding the whole capital of the column in that one product.",bucket:"Each row is an asset class (bucket) portfolio; its capital is split equally over its products.",pair:"Each row blends two asset classes 50/50; the capital is split equally between the two, then over each one's products.",book:"The seven asset classes together (30 products); the capital is split equally over the seven, then over each one's products."}[lv];
  $("desc").innerHTML="<b>Capital of the portfolio in each column ("+LV.find(x=>x[0]===lv)[1].toLowerCase()+"):</b> "+D.grid[lv].map(cap).join(", ")+". "+d+" Cells: Sharpe ratio, "+WL[w]+"; superscript = rank within the column (1 = best); colour = sign and size.";
}
$("lv").onclick=e=>{const k=e.target.dataset&&e.target.dataset.k;if(k){level=k;SORT=null;render();}};$("wt").onchange=render;$("win").onchange=render;
$("intro").innerHTML="Sharpe ratio (annualised return over annualised volatility, no risk-free rate, from 2012; data to 2026-09-30) of each portfolio when a liquidity penalty is charged on top of the 5 bps trading cost, at several capital sizes. <b>Base</b> = the 5 bps cost netted across each product's five premia, no penalty. US Power is not included (seven buckets, 30 products, 21 pairs).";
$("method").innerHTML=`<p><b>Penalty.</b> A product's five premia positions are added, so the product trades only the change in the sum (plus a roll unit when the net position is rolled); the 5 bps and the penalty are charged once on that net trade and split back to the premia by their own trades. A day that trades u units has participation P = u x N / V, where N = the dollars one unit of one premia position holds that day (the product's capital times the day's weights) and V = the product's daily traded notional on the 12-month strip (Calendar-2025 liquidity file; held fixed for all years). The penalty is zero while P is below 10% of a day's volume; above it, with E = P - 10% (P capped at 100%), the extra cost as a share of notional is u x sigma x sqrt(E) (square-root, Y = 1) or u x sigma x 3.16 x E (linear; 3.16 = Y / sqrt(10%)), sigma = trailing 63-day daily vol. Capital is notional at 1x leverage.</p>
<p><b>Weighting toggle.</b> Equal Weight / Inverse Vol is the way the five premia are combined (products and asset classes), and for pairs the way the two buckets are blended (each bucket built with the same method).</p>
<p><b>Weights.</b> The dollars a position holds follow the weights the portfolio actually uses each day: constant under Equal Weight, and under Inverse Vol the daily weights (1 / trailing 63-day volatility, lagged one day, normalised), for the premia inside a product or asset class, for the buckets in a pair or the book, and for the two stages of the book. The weights are taken from the series without the penalty, so the penalty does not change its own weights. A change of weights alone is not charged as a trade, as in the dashboard. Before the first weights exist (63-day burn-in) the Equal Weight split is used.</p>
<p><b>Caveats.</b> Y, the 10% threshold and the linear coefficient are assumptions, not calibrated. Volumes are the 2025 snapshot for every year. Bloomberg volume misses OTC-cleared swaps, so thin NGL penalties are upper bounds. Commodities are not selected for liquidity here: all 30 are shown.</p>`;
render();
</script></body></html>"""
out = Path("Analysis/Penalty_Sensitivity_0930.html")
out.write_text(html.replace("__DATA__", json.dumps(D, separators=(",", ":"))), encoding="utf8")
print("wrote", out, out.stat().st_size // 1024, "KB")
