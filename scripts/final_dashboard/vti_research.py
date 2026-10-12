"""Volatility-timing integration (VTI) of Fernandez-Perez, Fuertes and Miffre (2021), eq. (3), applied to our sleeves -> Analysis/VTI_Research.html
Separate research page; the Final dashboard, its 2012 variant and the Skewness page are not changed.

VTI weight of style k at month-end t:  w_k = (1 / var_k) / sum_j (1 / var_j), var = variance (n-1 divisor) of the style's MONTHLY returns over the last
60 months (paper's window). Our adaptation of the window (user's decision 2026-10-12): expanding until 60 months are available, at least 36 months
needed; a style's months count from its first non-zero daily return (before that it was not trading). In any month in which some style has fewer than
36 months, or zero variance, all styles get equal weights. Weights set at month-end t are applied to every day of month t+1 (no look-ahead).
Monthly returns = sum of the daily net log returns of the month. Compared with the existing Inverse Vol (1/volatility, 63 days, daily).
Applied at two levels, each on the four existing sleeves and on five (with Skewness): across sleeves inside each asset class, and across the five
cross-asset-class style series of the By-Style books. Basis: the 2012 variant, reported from 2012-01-01. Run after skewness_research.py."""
import sys, pickle
from pathlib import Path

sys.path.insert(0, "research"); sys.path.insert(0, "research/configs"); sys.path.insert(0, "scripts")
import numpy as np
import pandas as pd
from engine import combine_returns
from cross_asset_engine import combine_cross_asset
from run_regime_table import _metrics

WINDOW, MIN_M = 60, 36
START = "2012-01-01"
WINS = [("Full", START, None), ("P1 2012-16", "2012-01-01", "2016-12-31"), ("P2 2017-21", "2017-01-01", "2021-12-31"), ("P3 2022-26", "2022-01-01", None)]
nets, meta = pickle.load(open("outputs/final_dashboard_2012/products_2012_skew_nets.pkl", "rb"))
PRODUCTS = {"metals": ["Copper", "Aluminium", "Lead", "Zinc"], "energy": ["WTI", "Brent", "RBOB", "HeatingOil", "NatGas"],
            "ngl": ["Ethane", "Propane", "Butane", "Isobutane"], "precious": ["Gold", "Silver", "Platinum", "Palladium"],
            "agri": ["Corn", "Wheat", "Soybean", "SoybeanOil", "Coffee", "Sugar"]}
LABEL = {"metals": "Metals", "energy": "Energy", "energy_exng": "Energy ex-NatGas", "ngl": "NGL", "precious": "Precious", "agri": "Agriculture"}
OLD = ("Momentum", "Carry", "CarryMom", "Value")


def vti(rets: dict):
    """Returns (daily VTI portfolio return, daily weight frame, share of months on equal-weight fallback after START)."""
    df = pd.concat(rets, axis=1)
    started = (df.fillna(0) != 0).cummax()
    month = df.index.to_period("M")
    monthly = df.where(started).groupby(month).sum(min_count=1)
    var = monthly.rolling(WINDOW, min_periods=MIN_M).var(ddof=1).replace(0.0, np.nan)
    inv = 1.0 / var
    w = inv.div(inv.sum(axis=1, skipna=False), axis=0)
    k = df.shape[1]
    fallback = w.isna().any(axis=1)
    w = w.where(~fallback, 1.0 / k).shift(1)               # month-end t weights apply to month t+1
    w.iloc[0] = 1.0 / k
    w = w.fillna(1.0 / k)
    wd = w.reindex(month).set_axis(df.index)
    ret = (wd * df).sum(axis=1, skipna=False)
    fb = fallback.shift(1).reindex(month).set_axis(df.index).fillna(True)
    return ret, wd, float(fb.loc[START:].mean())


def align(lst):
    cum = [x.cumsum() for x in lst]
    idx = cum[0].index
    for c in cum[1:]:
        idx = idx.intersection(c.index)
    idx = idx.sort_values()
    return [c.reindex(idx).diff() for c in cum]


VARIANTS = [("metals", "metals", PRODUCTS["metals"]), ("energy", "energy", PRODUCTS["energy"]),
            ("energy_exng", "energy", [p for p in PRODUCTS["energy"] if p != "NatGas"]), ("ngl", "ngl", PRODUCTS["ngl"]),
            ("precious", "precious", PRODUCTS["precious"]), ("agri", "agri", PRODUCTS["agri"])]
groups = {}   # name -> dict(styles={name: series})
for key, a, prods in VARIANTS:
    groups[LABEL[key]] = {s: combine_cross_asset([nets[(a, p)][s] for p in prods]) for s in OLD + ("Skewness",)}
for lab, keys in (("By Style, with NatGas", ["metals", "energy", "ngl", "precious", "agri"]), ("By Style, ex-NatGas", ["metals", "energy_exng", "ngl", "precious", "agri"])):
    ac = {k: {s: combine_cross_asset([nets[(a, p)][s] for p in prods]) for s in OLD + ("Skewness",)} for k, a, prods in VARIANTS if k in keys}
    groups[lab] = {s: combine_returns(align([ac[k][s] for k in keys]), "equal_weight") for s in OLD + ("Skewness",)}

f = lambda v, n=2: "" if v is None or pd.isna(v) else f"{v:.{n}f}"
cls = lambda v: "" if v is None or pd.isna(v) else (" pos" if v > 0.3 else (" neg" if v < -0.1 else ""))
ir = lambda v: f"<td class='n{cls(v)}'>{f(v)}</td>"
W4 = [w for w, _, _ in WINS]


def met(s):
    return {w: _metrics(s.loc[st:e] if e else s.loc[st:]) for w, st, e in WINS}


def table(head, rows):
    h = "<tr>" + "".join(f"<th>{x}</th>" for x in head) + "</tr>"
    b = "".join("<tr>" + "".join(c if c.startswith("<td") else f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<div class='ts'><table>{h}{b}</table></div>"


perf, wrows = [], []
for g, sty in groups.items():
    for nstyle, names in (("4 sleeves" if not g.startswith("By Style") else "4 styles", OLD),
                          ("5 sleeves" if not g.startswith("By Style") else "5 styles", OLD + ("Skewness",))):
        lst = [sty[s] for s in names]
        series = {"EW": combine_returns(lst, "equal_weight"), "Inverse Vol (63d)": combine_returns(lst, "inverse_vol", vol_window=63)}
        v, wd, fbshare = vti({s: sty[s] for s in names})
        series["VTI (60m, 1/variance)"] = v
        for nm, s in series.items():
            m = met(s)
            perf.append([f"{g}, {nstyle}: {nm}", f(m["Full"]["ret"]), f(m["Full"]["vol"]), f(m["Full"]["mdd"])] + [ir(m[w]["ir"]) for w in W4])
        mw = wd.loc[START:].mean()
        wrows.append([f"{g}, {nstyle}"] + [f"{mw[s]:.2f}" for s in names] + ([""] if len(names) == 4 else []) + [f"{fbshare:.0%}"])
H = ["Series", "Return %", "Vol %", "MDD %"] + [f"IR {w}" for w in W4]
WH = ["Group", "Momentum", "Carry", "CarryMom", "Value", "Skewness", "Equal-weight months"]
CSS = open("scripts/final_dashboard/skewness_research.py", encoding="utf8").read().split('CSS = """')[1].split('"""')[0]
method = ("<p>VTI (Kirby and Ostdiek 2012; Fernandez-Perez, Fuertes and Miffre 2021, eq. 3) weights each style by the inverse of its return <b>variance</b>, normalised to sum to "
          "1, with variance measured over the last 60 monthly observations and weights reset at month-end for the next month. The existing Inverse Vol uses the inverse of "
          "<b>volatility</b> over 63 days, updated daily, so VTI concentrates more on the least volatile style. Window adaptation: expanding until 60 months, at least 36 months; "
          "a style's months count from its first non-zero return; in any month where a style has fewer than 36 months, or zero variance, all styles get equal weights "
          "(share of such months in the last column below). Monthly returns are the sum of the daily net log returns. Basis: the 2012 variant, reported from 1 Jan 2012 "
          "to 23 Sep 2026 in three periods; the sleeves are the Final dashboard's, with Skewness as a possible fifth.</p>")
html = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>VTI Research</title>"
        f"<style>{CSS}</style></head><body><div class='wrap'><h1>Volatility-timing integration (VTI): research page</h1><p class='note'>Separate from the Final dashboard. "
        f"Generated 2026-10-12.</p><h2>Method</h2>{method}<h2>Performance: EW, Inverse Vol and VTI</h2>{table(H, perf)}"
        f"<h2>Average VTI weights since 2012</h2><p class='note'>Mean weight on each style over all days from 1 Jan 2012; the last column is the share of days on the equal-weight fallback.</p>{table(WH, wrows)}"
        f"</div></body></html>")
Path("Analysis/VTI_Research.html").write_text(html, encoding="utf8")
print("written Analysis/VTI_Research.html", len(html) // 1024, "KB")
