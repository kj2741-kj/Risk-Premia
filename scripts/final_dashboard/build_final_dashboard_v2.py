"""Builds Analysis/Final_Research_Dashboard.html (rebuilt: 5 asset classes, EW + Inverse Vol, two-pair Carry for Precious and Agriculture,
new roll rule, data through 2026-09-23, cross-pair, correlations, equity curves). Inputs: final_v2.json, twopair_v2.json. Run from repo root."""
import json
import re
from pathlib import Path

R = Path(".")
# CSS and the shared JS helpers (colour scale, rolling-correlation chart) are reused from an existing dashboard page: the August
# Strategy_Results_Dashboard.html if present (it is not tracked), otherwise the previously committed Final_Research_Dashboard.html.
_aug = R / "Analysis/Strategy_Results_Dashboard.html"
if _aug.exists():
    base = _aug.read_text(encoding="utf8")
    color_js = re.search(r"function irColor.*?(?=function renderTable)", base, re.S).group(0)
    roll_js = re.search(r"function rollingPearson.*?(?=function populateRcPairSelect)", base, re.S).group(0)
else:
    base = (R / "Analysis/Final_Research_Dashboard.html").read_text(encoding="utf8")
    color_js = re.search(r"function irColor.*?(?=function rollingPearson)", base, re.S).group(0)
    roll_js = re.search(r"function rollingPearson.*?(?=const f=\(v,n,s\))", base, re.S).group(0)
css = re.search(r"<style>(.*?)</style>", base, re.S).group(1)
res = json.load(open(R / "outputs/final_dashboard/final_v2.json"))
two = json.load(open(R / "outputs/final_dashboard/twopair_v2.json"))
COLS = [("full", "Full", "2011-2026"), ("r1", "R1", "2011-2016"), ("r2", "R2", "2017-2021"),
        ("r3", "R3", "2022-2026"), ("y26", "2026", "YTD")]
data = dict(res, twopair=two, cols=[dict(key=k, label=l, years=y) for k, l, y in COLS])

BODY = r"""
<div class="wrap">
<h1>Risk Premia: Final Research Dashboard</h1>
<div class="subtitle">Five commodity asset classes, four sleeves each (Momentum, Carry, Carry-Momentum, Value), combined by Equal Weight and Inverse Vol only. Log-return methodology, 5 bps costs, reporting from 2011-01-01. All price data through 2026-09-23. Generated 2026-10-12.</div>
<div class="tabs" id="tabbar"></div>
<div id="panels"></div>
<div class="tab-panel" id="panel-notes"><div class="card"><h2>Method, data and what changed</h2>
<h3>Sleeves (per product)</h3><ul class="steps">
<li><b>Momentum:</b> average of the signs of three moving-average crossovers, (1,20), (5,60), (20,250), on the raw front-month price; 1-day lag.</li>
<li><b>Carry (V2):</b> z-score of the carry slope, (near - far) / near, against its own trailing 252 days. With two tenor pairs, each pair gives a sign and the two signs are averaged then signed again (sign-vote): the position is flat when the pairs disagree. The lag is applied once to the blended signal.</li>
<li><b>Carry-Momentum (V3):</b> sign of the 20-day change in the same slope, blended across the same two tenor pairs by the same sign-vote rule.</li>
<li><b>Value:</b> F3 price against its own 1,260-day average, long below -10%, short above +10%.</li></ul>
<h3>Tenor pairs</h3><ul class="steps">
<li>Metals and Energy: F1-F3 and F1-F13. NGL: F2-F4 and F2-F14.</li>
<li>Precious: F1-F2 plus a long pair about 12 months out: Gold F1-F7, Silver F1-F6, Platinum F1-F5, Palladium F1-F5.</li>
<li>Agriculture: F1-F2 plus a long pair about 12 months out: Corn F1-F6, Wheat F1-F6, Soybean F1-F8, Soybean Oil F1-F8 (10 to 11 months, the deepest column in the file), Coffee F1-F6, Sugar F1-F5.</li></ul>
<h3>Rolling</h3><ul class="steps">
<li><b>New rule:</b> each contract is rolled on the 5th trading day of the month in which its last trade date falls (previously: 5 trading days before the last trade date). The bridge on the day after the last trade date, when the data's F1 switches contract, is unchanged. In practice this rolls about 14 to 16 trading days before expiry for Energy, NGL, Precious and Sugar, about 6 for Metals, and about 5 for Corn, Wheat and Soybeans. On every contract the roll falls before the last trade date, apart from one NGL contract (Isobutane, expiring Nov 2009) that gets no roll because the series has only one price date that month; it is at the start of the history, before the 2011 reporting window.</li>
<li>Contracts whose last trade date is after the last price date no longer produce a spurious roll in the final week (the previous rule snapped them to the last price date).</li></ul>
<h3>How things are combined</h3><ul class="steps">
<li>Products inside a sleeve are equally weighted on common dates (a dropped date's move is carried into the next shared date).</li>
<li>Each asset-class portfolio combines its four sleeves by <b>EW PORT</b> (equal weight) or <b>Inverse Vol</b> (weights from each sleeve's trailing 63-day volatility, recomputed daily).</li>
<li><b>Combined books</b> are two-stage: sleeves into an asset-class portfolio, then the five asset-class portfolios into one book; all four EW / Inverse Vol pairs are shown, with and without NatGas. <b>Cross-pair portfolios</b> blend two asset classes' portfolios the same way. Series are aligned on common dates before weighting.</li></ul>
<h3>Data and calendars</h3><ul class="steps">
<li>Prices: <code>data/Prices_0924</code>, all five asset classes through 2026-09-23 (previously June 30 for four of them). Reporting still starts 2011-01-01, so 2026 year-to-date now covers nearly nine months.</li>
<li><b>NGL labels (verified):</b> the 24-Sep NGL file relabels its Argus sheets, and those sheet names are wrong; the underlying series are identical to the July file, whose labels are right. Checked against EIA's Mont Belvieu propane spot price (daily, via FRED series DPROPANEMBTX): the BAP series is propane (median price ratio 1.00, level correlation 0.995, 5-day change correlation 0.90), while the file calls it "Butane". CAP is ethane, not "Propane Far East": its 2012 average was 47% below 2011 (EIA reported ethane down 48%, propane 32%; BAP is down 31%), 24 cents per gallon on 19 Dec 2012 (reported 25 cents) and 13 cents on 16 Mar 2020 (reported 12.9 cents). DAE is normal butane (about 1.2 times propane; 2012 average down 10% against EIA's 5% for normal butane, allowing for swap versus spot) and IBD is isobutane (about 1.3 times propane). Products are mapped by ticker root: Ethane CAP, Propane BAP, Butane DAE, Isobutane IBD.</li>
<li>Gold and Silver deep columns (Gold F14 to F20, Silver F12 to F16) were revised in the new file from mid 2025; no pair used here goes that deep.</li>
<li>Roll calendars: Precious aligned to Bloomberg's contract months, Agriculture Bloomberg-matched, Metals, Energy and NGL on <code>expiry_calendars_20260701.xlsx</code> (it agrees with the 24-Sep consolidated calendar on every shared contract; those three were not Bloomberg-matched because no monthly files exist for them).</li></ul>
<h3>Regimes</h3><ul class="steps">
<li>Three regimes (set 2026-10-12, replacing the earlier four): <b>R1</b> 1 Jan 2011 to 31 Dec 2016, <b>R2</b> 1 Jan 2017 to 31 Dec 2021, <b>R3</b> 1 Jan 2022 to the last price date, 23 Sep 2026. The windows do not overlap. The 2026 column (year to date) lies inside R3. Every horizon figure is computed on its own window: return and volatility annualised over that window, drawdown measured from the window's start.</li></ul>
<h3>Checks</h3><ul class="steps">
<li>With the old roll rule, the new price files reproduce the old continuous series exactly through May 2026 (Gold, Platinum, WTI, Copper, Corn, Ethane, Propane, Butane).</li>
<li>Earlier versions of this analysis reproduced the August dashboard's Momentum and Value rows to three decimals for Metals, Energy and NGL.</li></ul>
<h3>Cautions</h3><ul class="steps">
<li>NGL tenors are provisional (F2 reintroduces heating-season seasonality). Platinum and Palladium F5 and Gold F7 sit beyond the range the liquidity study found fully liquid; Agriculture has had no liquidity study.</li>
<li>Platinum and Palladium F5 has data only from February 2010 (the monthly files have no earlier prices either), so their long-pair signals warm up during 2010.</li>
<li>All results are in-sample and not tested for statistical significance; the roll-rule change alters every asset class's numbers.</li></ul>
</div></div>
</div>
"""

SCRIPT = r"""
const f=(v,n,s)=>v==null?"n/a":v.toFixed(n)+(s||"");
const ir=v=>v==null?"n/a":`<span class="ir-cell" style="background:${irColor(v)};color:${irTextColor(v)}">${v.toFixed(3)}</span>`;
const BOLD=n=>/^(EW PORT|Inverse Vol)/.test(n)||n.startsWith("EW sleeves")||n.startsWith("Inverse Vol sleeves");
const LABEL={metals:"Metals",energy:"Energy",energy_exng:"Energy ex-NatGas",ngl:"NGL",precious:"Precious",agri:"Agriculture"};
const ASSET={metals:"metals",energy:"energy",energy_exng:"energy",ngl:"ngl",precious:"precious",agri:"agri"};
const CAL={metals:"LME futures. Roll calendar: expiry_calendars_20260701.xlsx (not Bloomberg-matched).",
 energy:"NYMEX/ICE futures. Roll calendar: expiry_calendars_20260701.xlsx (not Bloomberg-matched).",
 energy_exng:"Energy with Natural Gas removed. Roll calendar: expiry_calendars_20260701.xlsx (not Bloomberg-matched).",
 ngl:"Mont Belvieu swaps/futures, mapped by ticker root; labels verified against EIA propane spot (see Notes). Roll calendar: expiry_calendars_20260701.xlsx (not Bloomberg-matched).",
 precious:"COMEX/NYMEX futures. Roll calendar: expiry_calendars_20260701_aligned.xlsx (Bloomberg-matched months).",
 agri:"CBOT/ICE futures. Roll calendar: Agri_Rolling_Calendar_bloomberg_matched.xlsx (Bloomberg-matched months)."};
const ORDER=[["metals","Metals"],["energy","Energy"],["energy_exng","Energy ex-NatGas"],["ngl","NGL"],["precious","Precious"],["agri","Agriculture"],
 ["all5","All 5: with NatGas"],["all5_exng","All 5: ex-NatGas"],["bystyle","By Style"],["crosspair","Cross-Pair"],["corr","Correlations"],["notes","Notes"]];
const bar=document.getElementById("tabbar"),panels=document.getElementById("panels");
ORDER.forEach(([k,l],i)=>{const b=document.createElement("button");b.className="tab-btn";b.setAttribute("role","tab");b.setAttribute("aria-selected",i==0?"true":"false");b.dataset.tab=k;b.textContent=l;bar.appendChild(b);});
function addPanel(key,html,first){const p=document.createElement("div");p.className="tab-panel"+(first?" active":"");p.id="panel-"+key;p.innerHTML=html;panels.appendChild(p);return p;}
const horizonOpts=D.cols.map(c=>`<option value="${c.key}">${c.label} (${c.years})</option>`).join("");
function fullTable(rows,lab){return "<thead><tr><th>"+(lab||"Strategy")+"</th><th>Return (annualized)</th><th>Vol (annualized)</th><th>Max Drawdown</th><th>IR</th></tr></thead><tbody>"+rows.map(r=>`<tr style="${BOLD(r.name)?"font-weight:700":""}"><td>${r.name}</td><td>${f(r.ret,2,"%")}</td><td>${f(r.vol,2,"%")}</td><td>${f(r.mdd,2,"%")}</td><td>${ir(r.ir)}</td></tr>`).join("")+"</tbody>";}
function irTable(W,lab){const names=W.full.map(r=>r.name);return "<thead><tr><th>"+(lab||"Strategy")+"</th>"+D.cols.map(c=>`<th>${c.label}<br><span style="font-weight:400;color:var(--text-muted);font-size:10.5px">${c.years}</span></th>`).join("")+"</tr></thead><tbody>"+names.map((n,i)=>`<tr style="${BOLD(n)?"font-weight:700":""}"><td>${n}</td>`+D.cols.map(c=>`<td>${ir(W[c.key][i].ir)}</td>`).join("")+"</tr>").join("")+"</tbody>";}
function wireTable(p,selId,tblId,getRows){const sel=p.querySelector(selId),tb=p.querySelector(tblId);const draw=()=>tb.innerHTML=fullTable(getRows(sel.value));sel.addEventListener("change",draw);draw();}

/* ---------- equity (cumulative return) chart ---------- */
const PALETTE=["#3987e5","#e34948","#0ca30c","#a06c00","#7a4fd1","#0e8c8c","#c2185b","#6b6b6b","#d97706"];
const EQ_STARTS=[["2011-01-01","From 2011"],["2016-01-01","From 2016"],["2020-01-01","From 2020"],["2022-01-01","From 2022"],["2026-01-01","From 2026"]];
function renderEquity(host,key){
  const E=D.equity[key],names=Object.keys(E.series);
  host.innerHTML=`<div class="rc-window-row"><label>Period: <select class="window-select" data-eq="start">${EQ_STARTS.map(s=>`<option value="${s[0]}">${s[1]}</option>`).join("")}</select></label><span class="note" style="margin:0">Cumulative return, rebased to 0 at the start of the period.</span></div>
  <div data-eq="legend" class="legend-row"></div><div class="rc-card" style="position:relative"><div data-eq="chart"></div></div>`;
  const startSel=host.querySelector("[data-eq=start]"),legend=host.querySelector("[data-eq=legend]"),chart=host.querySelector("[data-eq=chart]");
  const on={};names.forEach((n,i)=>on[n]=!n.startsWith("Reference")||false);
  names.forEach(n=>{on[n]=!n.startsWith("Reference");});
  legend.innerHTML=names.map((n,i)=>`<label style="cursor:pointer"><input type="checkbox" data-n="${i}" ${on[n]?"checked":""}> <span class="legend-swatch" style="background:${PALETTE[i%PALETTE.length]}"></span>${n}</label>`).join("");
  function draw(){
    const start=startSel.value;let s0=E.dates.findIndex(d=>d>=start);if(s0<0)s0=0;
    const sel=names.filter(n=>on[n]);
    const W=920,H=340,padL=56,padR=16,padT=14,padB=30,plotW=W-padL-padR,plotH=H-padT-padB;
    const idx=[];for(let i=s0;i<E.dates.length;i++)idx.push(i);const n=idx.length;
    const vals={};let lo=0,hi=0;
    sel.forEach(nm=>{const c=E.series[nm];vals[nm]=idx.map(i=>(Math.exp(c[i]-c[s0])-1)*100);vals[nm].forEach(v=>{if(v<lo)lo=v;if(v>hi)hi=v;});});
    if(hi-lo<1){hi=lo+1;}
    const pad=(hi-lo)*0.06;lo-=pad;hi+=pad;
    const xS=i=>padL+(i/Math.max(1,n-1))*plotW,yS=v=>padT+(1-(v-lo)/(hi-lo))*plotH;
    const rawStep=(hi-lo)/6,mag=Math.pow(10,Math.floor(Math.log10(rawStep))),stepV=[1,2,5,10].map(m=>m*mag).find(m=>m>=rawStep)||mag*10;
    let grid="";for(let v=Math.ceil(lo/stepV)*stepV;v<=hi;v+=stepV){const y=yS(v);grid+=`<line x1="${padL}" y1="${y.toFixed(1)}" x2="${W-padR}" y2="${y.toFixed(1)}" class="${Math.abs(v)<1e-9?"rc-zero-line":"rc-grid-line"}"/><text x="${padL-6}" y="${(y+3).toFixed(1)}" text-anchor="end" class="rc-axis-label">${v.toFixed(0)}%</text>`;}
    let xt="",lastY=null;idx.forEach((gi,k)=>{const y=E.dates[gi].slice(0,4);if(y!==lastY){lastY=y;const x=xS(k);xt+=`<line x1="${x.toFixed(1)}" y1="${padT}" x2="${x.toFixed(1)}" y2="${H-padB}" class="rc-grid-line"/><text x="${x.toFixed(1)}" y="${H-padB+14}" text-anchor="middle" class="rc-axis-label">${y}</text>`;}});
    const lines=sel.map(nm=>{const col=PALETTE[names.indexOf(nm)%PALETTE.length];return `<polyline fill="none" stroke="${col}" stroke-width="1.8" points="${vals[nm].map((v,k)=>xS(k).toFixed(1)+","+yS(v).toFixed(1)).join(" ")}"/>`;}).join("");
    chart.innerHTML=`<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="width:100%;height:auto"><g>${grid}</g><g>${xt}</g>${lines}<line x1="0" y1="${padT}" x2="0" y2="${H-padB}" class="rc-crosshair" data-ch="1"/></svg><div class="rc-tooltip" style="white-space:pre"></div>`;
    const svg=chart.querySelector("svg"),ch=chart.querySelector("[data-ch]"),tip=chart.querySelector(".rc-tooltip");
    svg.addEventListener("pointermove",e=>{const r=svg.getBoundingClientRect(),rx=(e.clientX-r.left)/r.width*W;let k=Math.round(((rx-padL)/plotW)*(n-1));k=Math.max(0,Math.min(n-1,k));
      ch.setAttribute("x1",xS(k).toFixed(1));ch.setAttribute("x2",xS(k).toFixed(1));ch.style.display="block";tip.style.display="block";
      tip.textContent=E.dates[idx[k]]+"\n"+sel.map(nm=>nm+": "+vals[nm][k].toFixed(1)+"%").join("\n");
      tip.style.left=(e.clientX-chart.getBoundingClientRect().left+12)+"px";tip.style.top=(e.clientY-chart.getBoundingClientRect().top-10)+"px";});
    svg.addEventListener("pointerleave",()=>{ch.style.display="none";tip.style.display="none";});
  }
  legend.querySelectorAll("input").forEach(cb=>cb.addEventListener("change",()=>{on[names[+cb.dataset.n]]=cb.checked;draw();}));
  startSel.addEventListener("change",draw);draw();
}

/* ---------- asset-class tabs ---------- */
function productSection(p,key){
  const asset=ASSET[key],t=D.tabs[key];
  const sleeves=["Momentum","Carry","CarryMom","Value"];
  p.querySelector("[data-prod]").innerHTML=`<div class="window-row"><h3>By product</h3><label>Horizon: <select class="window-select" data-ph>${horizonOpts}</select> Metric: <select class="window-select" data-pm><option value="ir">IR</option><option value="ret">Return (%)</option><option value="vol">Vol (%)</option><option value="mdd">Max drawdown (%)</option></select></label></div><div class="table-scroll"><table data-pt></table></div>`;
  const ph=p.querySelector("[data-ph]"),pm=p.querySelector("[data-pm]"),pt=p.querySelector("[data-pt]");
  const draw=()=>{const m=pm.value;pt.innerHTML="<thead><tr><th>Product</th>"+sleeves.map(s=>`<th>${s==="Carry"?"Carry (V2)":s==="CarryMom"?"CarryMom (V3)":s}</th>`).join("")+"<th>Tenor pairs</th><th>Roll events</th></tr></thead><tbody>"+t.products.map(pr=>{const d=D.products[asset+"|"+pr];return `<tr><td>${pr}</td>`+sleeves.map(s=>{const v=d[s][ph.value][m];return m==="ir"?`<td>${ir(v)}</td>`:`<td>${f(v,2)}</td>`;}).join("")+`<td style="text-align:left">${D.meta.pairs[asset+"|"+pr].join(", ")}</td><td>${D.meta.rolls[asset+"|"+pr]}</td></tr>`;}).join("")+"</tbody>";};
  ph.addEventListener("change",draw);pm.addEventListener("change",draw);draw();
}
function twoPairSection(p,key){
  const T=D.twopair[key],card=p.querySelector("[data-two]");
  card.innerHTML=`<div class="window-row"><h3>Single pair (previous setup) vs two pairs</h3><label>Horizon: <select class="window-select" data-th>${horizonOpts}</select></label></div>
  <p class="note">Previous setup: ${key==="precious"?"F1-F3":"F1-F2"} single pair. Two pairs: short F1-F2 plus the long pair per product, blended by the sign-vote rule. Same data, roll rule and costs in both. IR shown (return / vol in the table below).</p>
  <div class="table-scroll"><table data-t1></table></div><h3>Per product, full sample IR</h3><div class="table-scroll"><table data-t2></table></div>`;
  const th=card.querySelector("[data-th]"),t1=card.querySelector("[data-t1]"),t2=card.querySelector("[data-t2]");
  const draw=()=>{const W=T[th.value];const rowS=(lab,a,b,c,d)=>`<tr><td>${lab}</td><td>${ir(W[a].ir)}</td><td>${ir(W[b].ir)}</td><td>${ir(W[c].ir)}</td><td>${ir(W[d].ir)}</td><td>${f(W[d].ret,2,"%")} / ${f(W[d].vol,1,"%")}</td></tr>`;
    t1.innerHTML="<thead><tr><th>Sleeve</th><th>Previous single pair</th><th>Short F1-F2 only</th><th>Long pair only</th><th>Two pairs (sign-vote)</th><th>Two pairs: return / vol</th></tr></thead><tbody>"+
      rowS("Carry (V2)","Carry single (previous)","Carry short F1-F2","Carry long","Carry two-pair")+rowS("CarryMom (V3)","CarryMom single (previous)","CarryMom short F1-F2","CarryMom long","CarryMom two-pair")+
      `<tr style="font-weight:700"><td>EW PORT</td><td>${ir(W["EW PORT single"].ir)}</td><td></td><td></td><td>${ir(W["EW PORT two"].ir)}</td><td>${f(W["EW PORT two"].ret,2,"%")} / ${f(W["EW PORT two"].vol,1,"%")}</td></tr><tr style="font-weight:700"><td>Inverse Vol</td><td>${ir(W["Inverse Vol single"].ir)}</td><td></td><td></td><td>${ir(W["Inverse Vol two"].ir)}</td><td>${f(W["Inverse Vol two"].ret,2,"%")} / ${f(W["Inverse Vol two"].vol,1,"%")}</td></tr></tbody>`;};
  th.addEventListener("change",draw);draw();
  t2.innerHTML="<thead><tr><th>Product</th><th>Long pair</th><th>Carry: previous</th><th>short</th><th>long</th><th>two-pair</th><th>CarryMom: previous</th><th>short</th><th>long</th><th>two-pair</th></tr></thead><tbody>"+D.tabs[key].products.map(pr=>{const d=D.products[key+"|"+pr],g=k=>ir(d[k].full.ir);return `<tr><td>${pr}</td><td>${D.meta.pairs[key+"|"+pr][1]}</td><td>${g("carry_single_prev")}</td><td>${g("carry_short")}</td><td>${g("carry_long")}</td><td>${g("Carry")}</td><td>${g("cm_single_prev")}</td><td>${g("cm_short")}</td><td>${g("cm_long")}</td><td>${g("CarryMom")}</td></tr>`;}).join("")+"</tbody>";
}
Object.keys(D.tabs).forEach((key,i)=>{const t=D.tabs[key];
  const p=addPanel(key,`<div class="card"><h2>${LABEL[key]}</h2><p class="note"><b>Products:</b> ${t.products.join(", ")}. <b>Data:</b> ${t.data_first} to ${t.data_last}.</p><p class="note">${CAL[key]}</p>
  <div class="window-row"><h3>Performance by horizon</h3><label>Horizon: <select class="window-select" data-hs>${horizonOpts}</select></label></div><div class="table-scroll"><table data-full></table></div>
  <h3>IR by horizon</h3><div class="table-scroll"><table data-ir></table></div><h3>Cumulative return</h3><div data-eq></div><div data-prod></div>${(key==="precious"||key==="agri")?'<div data-two></div>':""}</div>`,i===0);
  wireTable(p,"[data-hs]","[data-full]",w=>t.windows[w]);p.querySelector("[data-ir]").innerHTML=irTable(t.windows);
  renderEquity(p.querySelector("[data-eq]"),key);productSection(p,key);if(key==="precious"||key==="agri")twoPairSection(p,key);
});

/* ---------- combined books ---------- */
[["all5","All 5 asset classes (Energy with NatGas)"],["all5_exng","All 5 asset classes (Energy ex-NatGas)"]].forEach(([key,label])=>{const c=D.combined[key];
  const p=addPanel(key,`<div class="card"><h2>${label}</h2><p class="note">Two-stage book: four sleeves into an asset-class portfolio, then the five asset-class portfolios into one book, by Equal Weight or Inverse Vol at each stage (first word = sleeves, second = across asset classes). Common window: ${c.common_first} to ${c.common_last}. "Reference" rows are each asset class's own EW PORT on that window.</p>
  <div class="window-row"><h3>Performance by horizon</h3><label>Horizon: <select class="window-select" data-hs>${horizonOpts}</select></label></div><div class="table-scroll"><table data-full></table></div><h3>IR by horizon</h3><div class="table-scroll"><table data-ir></table></div><h3>Cumulative return</h3><div data-eq></div></div>`,false);
  wireTable(p,"[data-hs]","[data-full]",w=>c.windows[w]);p.querySelector("[data-ir]").innerHTML=irTable(c.windows);renderEquity(p.querySelector("[data-eq]"),key);});

/* ---------- by style ---------- */
(function(){const p=addPanel("bystyle",`<div class="card"><h2>By-Style Portfolio</h2><p class="note">Each style (Momentum, Carry, Carry-Momentum, Value) is first equal-weighted across the five asset classes' own sleeves on their common dates, giving one cross-asset-class series per style. The four style series are then combined into one Equal Weight portfolio (EW PORT) and one Inverse Vol portfolio (trailing 63-day volatility, lagged one day). This is the reverse order to the "All 5" tabs, which combine sleeves within each asset class first.</p>
  <div class="window-row"><label>Energy: <select class="window-select" data-bv><option value="with NatGas">with NatGas</option><option value="ex-NatGas">ex-NatGas</option></select></label><span class="note" style="margin:0" data-bn></span></div>
  <div class="window-row"><h3>Performance by horizon</h3><label>Horizon: <select class="window-select" data-hs>${horizonOpts}</select></label></div><div class="table-scroll"><table data-full></table></div><h3>IR by horizon</h3><div class="table-scroll"><table data-ir></table></div><h3>Cumulative return</h3><div data-eq></div></div>`,false);
  const bv=p.querySelector("[data-bv]"),hs=p.querySelector("[data-hs]"),tb=p.querySelector("[data-full]");
  const draw=()=>{const c=D.bystyle[bv.value];p.querySelector("[data-bn]").textContent="Common window: "+c.common_first+" to "+c.common_last+".";tb.innerHTML=fullTable(c.windows[hs.value]);p.querySelector("[data-ir]").innerHTML=irTable(c.windows);renderEquity(p.querySelector("[data-eq]"),"bystyle "+bv.value);};
  bv.addEventListener("change",draw);hs.addEventListener("change",draw);draw();})();

/* ---------- cross-pair ---------- */
(function(){const p=addPanel("crosspair",`<div class="card"><h2>Cross-Pair Portfolios</h2><p class="note">Each row blends two asset classes' own portfolios, 50/50 (Equal Weight) or by trailing 63-day inverse volatility (Inverse Vol); each asset-class portfolio is built with the same method. Series are aligned on the pair's common dates. Pairs involving Energy are shown with NatGas and ex-NatGas.</p>
  <div class="window-row"><h3>Performance by horizon</h3><label>Energy: <select class="window-select" data-cv><option value="with NatGas">with NatGas</option><option value="ex-NatGas">ex-NatGas</option></select> Construction: <select class="window-select" data-cc><option value="EW">Equal Weight</option><option value="Inverse Vol">Inverse Vol</option></select> Horizon: <select class="window-select" data-hs>${horizonOpts}</select></label></div>
  <div class="table-scroll"><table data-full></table></div><h3>IR by horizon</h3><div class="table-scroll"><table data-ir></table></div></div>`,false);
  const cv=p.querySelector("[data-cv]"),cc=p.querySelector("[data-cc]"),hs=p.querySelector("[data-hs]"),tf=p.querySelector("[data-full]"),ti=p.querySelector("[data-ir]");
  const draw=()=>{const W=D.crosspair[cv.value][cc.value];tf.innerHTML=fullTable(W[hs.value],"Pair");ti.innerHTML=irTable(W,"Pair");};
  [cv,cc,hs].forEach(e=>e.addEventListener("change",draw));draw();})();

/* ---------- correlations ---------- */
const CAC=["metals","energy","precious","ngl","agri"],CLAB=["Metals","Energy","Precious","NGL","Agriculture"];
function corrCol(v){const a=Math.min(Math.abs(v),1);if(a<0.15)return "var(--neutral)";return v>=0?(a<0.5?"var(--pos-weak)":"var(--pos-strong)"):(a<0.5?"var(--neg-weak)":"var(--neg-strong)");}
function corrTxt(v){return Math.min(Math.abs(v),1)<0.5?"var(--text-primary)":"#ffffff";}
function corrMatrix(el,labels,m){el.innerHTML="<thead><tr><th></th>"+labels.map(l=>`<th>${l}</th>`).join("")+"</tr></thead><tbody>"+m.map((row,i)=>`<tr><td>${labels[i]}</td>`+row.map(v=>`<td><span class="corr-cell" style="background:${corrCol(v)};color:${corrTxt(v)}">${v.toFixed(2)}</span></td>`).join("")+"</tr>").join("")+"</tbody>";}
(function(){
  const PAIRS=[];for(let i=0;i<CAC.length;i++)for(let j=i+1;j<CAC.length;j++)PAIRS.push([CAC[i],CAC[j],CLAB[i]+" - "+CLAB[j]]);
  const p=addPanel("corr",`<div class="card"><p class="note"><strong>Methodology:</strong> Pearson correlations on daily net log-return series (Momentum, Carry, Carry-Momentum, Value, EW PORT, Inverse Vol), 2011-2026. Within-asset-class matrices use each asset class's own calendar; cross-asset-class and rolling figures use the intersection of trading dates across the five asset classes (days per strategy: ${D.corr.rows.map(r=>r+" "+D.corr.cross._n[r]).join(", ")}; the Inverse Vol rows start later because NGL's Inverse Vol series is undefined before 23 Feb 2012).</p></div>
  <div class="card"><h2>Section 1: Within-Asset-Class Correlation</h2><div class="window-row"><h3>Select asset class</h3><label>Asset class: <select class="window-select" data-w>${Object.keys(LABEL).map(k=>`<option value="${k}">${LABEL[k]}</option>`).join("")}</select></label></div><div class="table-scroll"><table class="corr" data-wt></table></div></div>
  <div class="card"><h2>Section 2: Cross-Asset-Class Correlation</h2><div class="window-row"><h3>Select strategy</h3><label>Strategy: <select class="window-select" data-c>${D.corr.rows.map(r=>`<option value="${r}">${r}</option>`).join("")}</select></label></div><div class="table-scroll"><table class="corr" data-ct></table></div>
   <div class="legend-row"><span><span class="legend-swatch" style="background:var(--pos-strong)"></span>strong positive (&ge;0.5)</span><span><span class="legend-swatch" style="background:var(--pos-weak)"></span>weak positive (0.15-0.5)</span><span><span class="legend-swatch" style="background:var(--neutral)"></span>near zero (&lt;0.15)</span><span><span class="legend-swatch" style="background:var(--neg-weak)"></span>weak negative</span><span><span class="legend-swatch" style="background:var(--neg-strong)"></span>strong negative</span></div></div>
  <div class="card"><h2>Section 3: Rolling Correlation Over Time</h2><p class="note">Trailing correlation between two asset classes' own portfolios, 2011 onward. Blue is positive, red negative; hairlines at &plusmn;0.15 and &plusmn;0.5.</p>
  <div class="rc-window-row"><label>Pair: <select class="window-select" data-rp>${PAIRS.map((x,i)=>`<option value="${i}">${x[2]}</option>`).join("")}</select></label><label>Portfolio: <select class="window-select" data-rc><option value="ew">Equal Weight</option><option value="iv">Inverse Vol</option></select></label><label>Rolling window: <select class="window-select" data-rw><option value="60">60 trading days</option><option value="126" selected>126 trading days</option><option value="252">252 trading days</option></select></label></div><div class="rc-single" data-rcs></div></div>`,false);
  const ws=p.querySelector("[data-w]"),wt=p.querySelector("[data-wt]");const dw=()=>corrMatrix(wt,D.corr.rows,D.corr.within[ws.value]);ws.addEventListener("change",dw);dw();
  const cs=p.querySelector("[data-c]"),ct=p.querySelector("[data-ct]");const dc=()=>corrMatrix(ct,CLAB,D.corr.cross[cs.value]);cs.addEventListener("change",dc);dc();
  const rp=p.querySelector("[data-rp]"),rcn=p.querySelector("[data-rc]"),rw=p.querySelector("[data-rw]"),host=p.querySelector("[data-rcs]");
  const dr=()=>{const [a,b,title]=PAIRS[+rp.value];const R=D.corr.rolling[rcn.value],S=R.series;const vals=rollingPearson(S[a],S[b],+rw.value);host.innerHTML="";const card=document.createElement("div");card.className="rc-card";host.appendChild(card);renderRollingCorrChart(card,title,vals,R.dates);};
  [rp,rcn,rw].forEach(e=>e.addEventListener("change",dr));dr();})();

document.querySelectorAll(".tab-btn").forEach(btn=>btn.addEventListener("click",()=>{document.querySelectorAll(".tab-btn").forEach(b=>b.setAttribute("aria-selected","false"));document.querySelectorAll(".tab-panel").forEach(p=>p.classList.remove("active"));btn.setAttribute("aria-selected","true");document.getElementById("panel-"+btn.dataset.tab).classList.add("active");}));
"""

EXTRA = (" ul.steps li{margin:4px 0;font-size:13px} .legend-row label{display:inline-flex;align-items:center;gap:4px;font-size:12px}"
         " .rc-tooltip{white-space:pre}")
html = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Risk Premia: Final Research Dashboard</title>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"><style>' + css + EXTRA + "</style></head><body>" + BODY +
        "<script>\nconst D=" + json.dumps(data) + ";\n" + color_js + roll_js + SCRIPT + "</script></body></html>")
out = R / "Analysis/Final_Research_Dashboard.html"
out.write_text(html, encoding="utf8")
print("written", out, len(html) // 1024, "KB")
