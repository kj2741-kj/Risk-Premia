"""Skewness style (Fernandez-Perez, Fuertes and Miffre 2021, Table 1), time-series version, as a fifth sleeve -> Analysis/Skewness_Research.html
Separate research page, kept apart from the Final dashboard and its 2012 variant (neither is changed).

Signal (per product, daily): minus the skewness of the product's daily log returns over the past 252 observations (full window required).
    +1 if the skewness is negative (paper: negative skewness is expected to outperform), -1 if positive. Same rules as the other sleeves:
    execution lag 2 days (exec_shift, shift_n = 1), 5 bps round trip with the roll-day charge, returns on the roll-adjusted continuous series.
    The returns are the continuous series' daily log returns (log_price.diff()), so roll jumps are not in the skewness. pandas' rolling skew is the
    bias-adjusted sample skewness, which has the same sign as the paper's third-moment form, and only the sign is used.
Basis: the 2012 variant (outputs/final_dashboard_2012/products_2012_nets.pkl: Value needs 504 observations), reported from 2012-01-01 in three periods.
Aggregation exactly as the Final dashboard: products equal-weighted on common dates, sleeves combined by EW and Inverse Vol (63 days, lagged one day).
Run from the repo root after scripts/final_dashboard/run_2012_variant.py."""
import sys, pickle, importlib
from itertools import combinations
from pathlib import Path

sys.path.insert(0, "research"); sys.path.insert(0, "research/configs"); sys.path.insert(0, "scripts")
import numpy as np
import pandas as pd
from engine import exec_shift, log_return_daily, combine_returns
from cross_asset_engine import combine_cross_asset
from run_regime_table import _metrics

SKEW_WINDOW = 252
START = "2012-01-01"
WINS = [("Full", START, None), ("P1 2012-16", "2012-01-01", "2016-12-31"), ("P2 2017-21", "2017-01-01", "2021-12-31"), ("P3 2022-26", "2022-01-01", None)]
nets, meta = pickle.load(open("outputs/final_dashboard_2012/products_2012_nets.pkl", "rb"))
PRODUCTS = {"metals": ["Copper", "Aluminium", "Lead", "Zinc"], "energy": ["WTI", "Brent", "RBOB", "HeatingOil", "NatGas"],
            "ngl": ["Ethane", "Propane", "Butane", "Isobutane"], "precious": ["Gold", "Silver", "Platinum", "Palladium"],
            "agri": ["Corn", "Wheat", "Soybean", "SoybeanOil", "Coffee", "Sugar"]}
LABEL = {"metals": "Metals", "energy": "Energy", "energy_exng": "Energy ex-NatGas", "ngl": "NGL", "precious": "Precious", "agri": "Agriculture"}
OLD = ("Momentum", "Carry", "CarryMom", "Value")

# ---- 1. Skewness sleeve per product ----
for a, prods in PRODUCTS.items():
    cfg = importlib.import_module(a)
    for p in prods:
        raw = cfg.load_f1_series_logret(p)
        lp, ph = raw["log_price"], raw["Phase"]
        sk = lp.diff().rolling(SKEW_WINDOW).skew()
        sig = np.sign(-sk)
        nets[(a, p)]["Skewness"] = log_return_daily(exec_shift(sig, 1).fillna(0), lp, 5, ph)[1]
        print("skew", a, p, flush=True)


def align(lst):
    cum = [x.cumsum() for x in lst]
    idx = cum[0].index
    for c in cum[1:]:
        idx = idx.intersection(c.index)
    idx = idx.sort_values()
    return [c.reindex(idx).diff() for c in cum]


def met(s):
    return {w: _metrics(s.loc[st:e] if e else s.loc[st:]) for w, st, e in WINS}


VARIANTS = [("metals", "metals", PRODUCTS["metals"]), ("energy", "energy", PRODUCTS["energy"]),
            ("energy_exng", "energy", [p for p in PRODUCTS["energy"] if p != "NatGas"]), ("ngl", "ngl", PRODUCTS["ngl"]),
            ("precious", "precious", PRODUCTS["precious"]), ("agri", "agri", PRODUCTS["agri"])]
acs = {}
for key, a, prods in VARIANTS:
    st = {s: combine_cross_asset([nets[(a, p)][s] for p in prods]) for s in OLD + ("Skewness",)}
    l4, l5 = [st[s] for s in OLD], [st[s] for s in OLD + ("Skewness",)]
    acs[key] = dict(styles=st, ew4=combine_returns(l4, "equal_weight"), iv4=combine_returns(l4, "inverse_vol", vol_window=63),
                    ew5=combine_returns(l5, "equal_weight"), iv5=combine_returns(l5, "inverse_vol", vol_window=63))
# cross-asset by-style books
books = {}
for lab, keys in (("with NatGas", ["metals", "energy", "ngl", "precious", "agri"]), ("ex-NatGas", ["metals", "energy_exng", "ngl", "precious", "agri"])):
    sty = {s: combine_returns(align([acs[k]["styles"][s] for k in keys]), "equal_weight") for s in OLD + ("Skewness",)}
    l4, l5 = [sty[s] for s in OLD], [sty[s] for s in OLD + ("Skewness",)]
    books[lab] = dict(sty=sty, ew4=combine_returns(l4, "equal_weight"), iv4=combine_returns(l4, "inverse_vol", vol_window=63),
                      ew5=combine_returns(l5, "equal_weight"), iv5=combine_returns(l5, "inverse_vol", vol_window=63))

# ---- 2. HTML ----
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
sec.append("<h2>Skewness sleeve by asset class</h2><p class='note'>Equal-weighted across the asset class's products; Return, Vol and MDD are full-sample (2012 to 23 Sep 2026), IR by period.</p>"
           + table(H, perf_rows({LABEL[k]: acs[k]["styles"]["Skewness"] for k in LABEL}
                                | {"Cross-asset EW (with NatGas)": books["with NatGas"]["sty"]["Skewness"],
                                   "Cross-asset EW (ex-NatGas)": books["ex-NatGas"]["sty"]["Skewness"]})))
rows = []
for key, a, prods in VARIANTS:
    if key == "energy_exng":
        continue
    for p in prods:
        m = met(nets[(a, p)]["Skewness"])
        rows.append([f"{LABEL[a]}: {p}", f(m["Full"]["ret"]), f(m["Full"]["vol"]), f(m["Full"]["mdd"])] + [ir(m[w]["ir"]) for w in W4])
sec.append("<h2>Skewness sleeve by product</h2>" + table(["Product", "Return %", "Vol %", "MDD %"] + [f"IR {w}" for w in W4], rows))
cmp_rows = {}
for k in LABEL:
    cmp_rows[f"{LABEL[k]}: EW 4 sleeves"] = acs[k]["ew4"]; cmp_rows[f"{LABEL[k]}: EW 5 sleeves (+ Skewness)"] = acs[k]["ew5"]
    cmp_rows[f"{LABEL[k]}: Inverse Vol 4 sleeves"] = acs[k]["iv4"]; cmp_rows[f"{LABEL[k]}: Inverse Vol 5 sleeves"] = acs[k]["iv5"]
sec.append("<h2>Does a fifth sleeve help? Asset-class portfolios</h2><p class='note'>EW PORT and Inverse Vol of the four existing sleeves against the same with Skewness added.</p>" + table(H, perf_rows(cmp_rows)))
bk = {}
for lab in books:
    for nm, key in (("EW 4 styles", "ew4"), ("EW 5 styles (+ Skewness)", "ew5"), ("Inverse Vol 4 styles", "iv4"), ("Inverse Vol 5 styles", "iv5")):
        bk[f"By Style {lab}: {nm}"] = books[lab][key]
sec.append("<h2>Does a fifth style help? By-Style books</h2><p class='note'>Each style equal-weighted across the five asset classes, then combined by EW or Inverse Vol (as the By Style tab of the dashboard).</p>" + table(H, perf_rows(bk)))
# correlations of Skewness with the other sleeves, within asset class and across-asset-class books
names = list(OLD)
crow = []
for k in LABEL:
    df = pd.concat({s: acs[k]["styles"][s] for s in OLD + ("Skewness",)}, axis=1).loc[START:].dropna()
    crow.append([LABEL[k]] + [f"{df['Skewness'].corr(df[s]):.2f}" for s in names])
for lab in books:
    df = pd.concat(books[lab]["sty"], axis=1).loc[START:].dropna()
    crow.append([f"Cross-asset {lab}"] + [f"{df['Skewness'].corr(df[s]):.2f}" for s in names])
sec.append("<h2>Correlation of Skewness with the other sleeves</h2><p class='note'>Pearson, daily net log returns from 2012-01-01.</p>" + table(["Asset class"] + names, crow))

method = ("<p>Per product, each day: signal = minus the skewness of the continuous series' daily log returns over the past 252 observations. Position +1 when skewness "
          "is negative, -1 when positive (Fernandez-Perez, Fuertes and Miffre 2021, Table 1: the Skewness style is long negatively skewed contracts). Same engine as the "
          "other sleeves: two-day execution lag, 5 bps round-trip costs plus the roll-day charge, roll-adjusted continuous series, 5th-trading-day-of-expiry-month roll. "
          "Products equal-weighted within the asset class; portfolios by Equal Weight or Inverse Vol (trailing 63 days, lagged one day). Basis: the 2012 variant "
          "(Value needs 504 observations), reported from 1 Jan 2012 to 23 Sep 2026 in three periods. The paper's own version is cross-sectional (long/short sort across "
          "contracts, held a month); this is the time-series version used by all our sleeves, so numbers are not comparable with the paper's.</p>")
CSS = """body{font-family:Calibri,Arial,sans-serif;margin:0;background:#fff;color:#1f2d3d}@media(prefers-color-scheme:dark){body{background:#12171d;color:#dfe5ec}th{background:#222b35!important}td,th{border-color:#333d49!important}}
.wrap{max-width:1100px;margin:0 auto;padding:20px 16px}h1{font-size:24px;margin:0 0 4px}h2{font-size:17px;margin:26px 0 4px}.note{color:#667;font-size:13px;margin:2px 0 8px}
.ts{overflow-x:auto}table{border-collapse:collapse;font-size:12.5px;width:100%}th,td{border:1px solid #d5dbe2;padding:4px 8px;text-align:right;white-space:nowrap}th{background:#e8ecf0}
td:first-child,th:first-child{text-align:left}.pos{color:#0a7d3c;font-weight:600}.neg{color:#b3261e;font-weight:600}"""
html = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Skewness Research</title>"
        f"<style>{CSS}</style></head><body><div class='wrap'><h1>Skewness style: research page</h1><p class='note'>Separate from the Final dashboard. Generated 2026-10-12.</p>"
        f"<h2>Method</h2>{method}{''.join(sec)}</div></body></html>")
Path("Analysis/Skewness_Research.html").write_text(html, encoding="utf8")
print("written Analysis/Skewness_Research.html", len(html) // 1024, "KB")
