"""Skewness style (Fernandez-Perez, Fuertes and Miffre 2021, Table 1), time-series version, as a fifth sleeve -> Analysis/Skewness_Research_<tag>.html (2026-10-31 rebuild).
Rebuilt for the new buckets (Metals, Petroleum, Power / Emissions / Nat Gas, NGL, Precious, Agriculture) and the tag's data (0930: cut at 2026-09-30, 1029: latest data), from
outputs/final_dashboard_<tag>/products_nets.pkl, which already holds the Skewness sleeve of every product (compute_products_v3.py: minus the sign of the 252-observation rolling
skewness of the continuous series' daily log returns, +1 if negative, -1 if positive, the same two-day execution lag, 5 bps costs with the roll-day charge, 504-observation Value).
Aggregation exactly as the Final dashboard: products equal-weighted on common dates inside a bucket, sleeves combined by EW and Inverse Vol (63 days, lagged one day).
The older page (Analysis/Skewness_Research.html, old buckets, data to 23 Sep) is left as it was. Run from the repo root: FD_TAG=1029 python scripts/final_dashboard/skewness_research_v3.py"""
import sys, pickle
from pathlib import Path

sys.path.insert(0, "research"); sys.path.insert(0, "research/configs"); sys.path.insert(0, "scripts"); sys.path.insert(0, "scripts/final_dashboard")
import numpy as np
import pandas as pd
from engine import combine_returns
from cross_asset_engine import combine_cross_asset
from run_regime_table import _metrics
from fd_config import TAGS, BUCKETS, PAGE_CSS, current_tag, out_dir, check_run

TAG = current_tag(); check_run(TAG); CFG = TAGS[TAG]
START = "2012-01-01"
WINS = [("Full", START, None), ("P1 2012-16", "2012-01-01", "2016-12-31"), ("P2 2017-21", "2017-01-01", "2021-12-31"), ("P3 2022-26", "2022-01-01", None)]
nets, meta = pickle.load(open(out_dir(TAG) / "products_nets.pkl", "rb"))
OLD = ("Momentum", "Carry", "CarryMom", "Value")
KEYS = list(BUCKETS)


def align(lst):
    cum = [x.cumsum() for x in lst]
    idx = cum[0].index
    for c in cum[1:]:
        idx = idx.intersection(c.index)
    idx = idx.sort_values()
    return [c.reindex(idx).diff() for c in cum]


def met(s):
    return {w: _metrics(s.loc[st:e] if e else s.loc[st:]) for w, st, e in WINS}


acs = {}
for k, (label, members) in BUCKETS.items():
    st = {s: (combine_cross_asset([nets[m][s] for m in members]) if len(members) > 1 else nets[members[0]][s]) for s in OLD + ("Skewness",)}
    l4, l5 = [st[s] for s in OLD], [st[s] for s in OLD + ("Skewness",)]
    acs[k] = dict(styles=st, ew4=combine_returns(l4, "equal_weight"), iv4=combine_returns(l4, "inverse_vol", vol_window=63),
                  ew5=combine_returns(l5, "equal_weight"), iv5=combine_returns(l5, "inverse_vol", vol_window=63))
sty = {s: combine_returns(align([acs[k]["styles"][s] for k in KEYS]), "equal_weight") for s in OLD + ("Skewness",)}
l4, l5 = [sty[s] for s in OLD], [sty[s] for s in OLD + ("Skewness",)]
book = dict(sty=sty, ew4=combine_returns(l4, "equal_weight"), iv4=combine_returns(l4, "inverse_vol", vol_window=63),
            ew5=combine_returns(l5, "equal_weight"), iv5=combine_returns(l5, "inverse_vol", vol_window=63))

f = lambda v, n=2: "" if v is None or pd.isna(v) else f"{v:.{n}f}"
cls = lambda v: "" if v is None or pd.isna(v) else (" pos" if v > 0.3 else (" neg" if v < -0.1 else ""))


def table(head, rows):
    h = "<tr>" + "".join(f"<th>{x}</th>" for x in head) + "</tr>"
    b = "".join("<tr>" + "".join(c if c.startswith("<td") else f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<div class='ts'><table>{h}{b}</table></div>"


ir = lambda v: f"<td class='n{cls(v)}'>{f(v)}</td>"
W4 = [w for w, _, _ in WINS]


def perf_rows(series_dict):
    rows = []
    for name, s in series_dict.items():
        m = met(s)
        rows.append([name, f(m["Full"]["ret"]), f(m["Full"]["vol"]), f(m["Full"]["mdd"])] + [ir(m[w]["ir"]) for w in W4])
    return rows


H = ["Series", "Return %", "Vol %", "MDD %"] + [f"IR {w}" for w in W4]
sec = []
sec.append(f"<h2>Skewness sleeve by bucket</h2><p class='note'>Equal-weighted across the bucket's products; Return, Vol and MDD are full-sample (2012 to {CFG['long']}), IR by period.</p>"
           + table(H, perf_rows({BUCKETS[k][0]: acs[k]["styles"]["Skewness"] for k in KEYS} | {"Cross-bucket EW (six buckets)": book["sty"]["Skewness"]})))
rows = []
for k, (label, members) in BUCKETS.items():
    for a, p in members:
        m = met(nets[(a, p)]["Skewness"])
        rows.append([f"{label}: {p}", f(m["Full"]["ret"]), f(m["Full"]["vol"]), f(m["Full"]["mdd"])] + [ir(m[w]["ir"]) for w in W4])
sec.append("<h2>Skewness sleeve by product</h2>" + table(["Product", "Return %", "Vol %", "MDD %"] + [f"IR {w}" for w in W4], rows))
cmp_rows = {}
for k in KEYS:
    lab = BUCKETS[k][0]
    cmp_rows[f"{lab}: EW 4 sleeves"] = acs[k]["ew4"]; cmp_rows[f"{lab}: EW 5 sleeves (+ Skewness)"] = acs[k]["ew5"]
    cmp_rows[f"{lab}: Inverse Vol 4 sleeves"] = acs[k]["iv4"]; cmp_rows[f"{lab}: Inverse Vol 5 sleeves"] = acs[k]["iv5"]
sec.append("<h2>Does a fifth sleeve help? Bucket portfolios</h2><p class='note'>EW PORT and Inverse Vol of the four existing sleeves against the same with Skewness added.</p>" + table(H, perf_rows(cmp_rows)))
bk = {}
for nm, key in (("EW 4 styles", "ew4"), ("EW 5 styles (+ Skewness)", "ew5"), ("Inverse Vol 4 styles", "iv4"), ("Inverse Vol 5 styles", "iv5")):
    bk[f"By Style, six buckets: {nm}"] = book[key]
sec.append("<h2>Does a fifth style help? By-Style book</h2><p class='note'>Each style equal-weighted across the six buckets, then combined by EW or Inverse Vol (as the By Style tab of the dashboard).</p>" + table(H, perf_rows(bk)))
names = list(OLD)
crow = []
for k in KEYS:
    df = pd.concat({s: acs[k]["styles"][s] for s in OLD + ("Skewness",)}, axis=1).loc[START:].dropna()
    crow.append([BUCKETS[k][0]] + [f"{df['Skewness'].corr(df[s]):.2f}" for s in names])
df = pd.concat(book["sty"], axis=1).loc[START:].dropna()
crow.append(["Cross-bucket (six buckets)"] + [f"{df['Skewness'].corr(df[s]):.2f}" for s in names])
sec.append("<h2>Correlation of Skewness with the other sleeves</h2><p class='note'>Pearson, daily net log returns from 2012-01-01.</p>" + table(["Bucket"] + names, crow))

method = ("<p>Per product, each day: signal = minus the skewness of the continuous series' daily log returns over the past 252 observations. Position +1 when skewness "
          "is negative, -1 when positive (Fernandez-Perez, Fuertes and Miffre 2021, Table 1: the Skewness style is long negatively skewed contracts). Same engine as the "
          "other sleeves: two-day execution lag, 5 bps round-trip costs plus the roll-day charge, roll-adjusted continuous series, 5th-trading-day-of-expiry-month roll. "
          f"Products equal-weighted within the bucket; portfolios by Equal Weight or Inverse Vol (trailing 63 days, lagged one day). Basis: the 2012-start dashboard "
          f"(Value needs 504 observations), reported from 1 Jan 2012 to {CFG['long']} in three periods. Buckets: Metals, Petroleum, Power / Emissions / Nat Gas (Henry Hub, TTF, EUA), "
          "NGL, Precious, Agriculture. The paper's own version is cross-sectional (long/short sort across "
          "contracts, held a month); this is the time-series version used by all our sleeves, so numbers are not comparable with the paper's.</p>")
html = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Skewness Research</title>"
        f"<style>{PAGE_CSS}</style></head><body><div class='wrap'><h1>Skewness style: research page</h1><p class='note'>Separate from the Final dashboard. Six buckets, data to {CFG['cutoff']}. Generated 2026-10-31.</p>"
        f"<h2>Method</h2>{method}{''.join(sec)}</div></body></html>")
out = Path(f"Analysis/Skewness_Research_{TAG}.html")
out.write_text(html, encoding="utf8")
print("written", out, len(html) // 1024, "KB")
