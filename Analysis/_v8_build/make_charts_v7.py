import sys, os
sys.path.insert(0, ".")
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from rp import *

OUT = os.path.join(S, "img"); os.makedirs(OUT, exist_ok=True)
COL = {"Momentum": "#C58F56", "Carry": "#D6BC74", "CarryMom": "#5FA3A0", "Value": "#7FBF96", "Skewness": "#B898B0"}
EWC, IVC = "#111111", "#2B72B8"
PROD_COL = ["#C58F56", "#D6BC74", "#5FA3A0", "#7FBF96", "#C97B7B", "#B898B0"]
PAIR_COL = ["#E08A1E", "#E8C547", "#1F9E9A", "#6FBF4A", "#D9534F", "#8E44AD", "#7F7F7F", "#8C6D1F", "#2B72B8", "#5B3A29"]
PAIR_LS = ["-", "-", "-", "-", "-", "-", "--", "--", "--", "--"]
PNAME = {"HeatingOil": "Heating Oil", "NatGas": "Natural Gas", "SoybeanOil": "Soybean Oil"}
FINAL = {}   # final cumulative return (%) of every plotted curve, dumped to the file named by env FINAL_JSON for an independent check
NICE = {"Momentum": "Momentum", "Carry": "Carry", "CarryMom": "Carry-Momentum", "Value": "Value", "Skewness": "Skewness"}
START = "2012-01-01"


def cum(r):
    r = r.loc[START:].fillna(0)
    return np.exp(r.cumsum()) * 100


def setup(title):
    fig, ax = plt.subplots(figsize=(9.9, 5.9), dpi=150)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_ylabel("Cumulative Return (start = 100%)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}%"))
    ax.grid(True, color="#e5e5e5", linewidth=0.8); ax.set_axisbelow(True)
    ax.axhline(100, color="#999999", linewidth=1.0, zorder=1)
    return fig, ax


def plot(ax, ser, color, lw, label, fig_name, ls="-", alpha=0.95):
    c = cum(ser); ax.plot(c.index, c.values, color=color, lw=lw, alpha=alpha, label=label, ls=ls)
    FINAL.setdefault(fig_name, {})[label] = float(c.iloc[-1])


def finish(fig, ax, name, loc="upper left", ncol=2):
    ax.legend(loc=loc, ncol=ncol, fontsize=8.5, framealpha=0.95)
    ax.set_xlim(pd.Timestamp("2011-05-01"), pd.Timestamp("2026-12-31"))
    fig.tight_layout(); fig.savefig(os.path.join(OUT, name), dpi=150); plt.close(fig)


made = []
# --- combined strategies per asset class (five sleeves + EW + IV)
for v, nm in (("metals", "Metals"), ("petroleum", "Petroleum"), ("precious", "Precious Metals"), ("agri", "Agriculture")):
    df = class_sleeves(v); ew, iv = class_portfolios(v)
    fig, ax = setup(f"{nm}: Combined Strategies")
    fn = f"fig_{v}_combined.png"
    for k in SLEEVES:
        plot(ax, df[k], COL[k], 1.4, NICE[k], fn)
    plot(ax, ew, EWC, 3.6, "EW Portfolio", fn)
    plot(ax, iv, IVC, 3.6, "Inverse Vol", fn)
    finish(fig, ax, f"fig_{v}_combined.png"); made.append(f"fig_{v}_combined.png")

# --- per-product equity curves for each sleeve
UNIT = {"metals": "Metal", "petroleum": "Product", "precious": "Metal", "agri": "Product"}
for v, nm in (("metals", "Metals"), ("petroleum", "Petroleum"), ("precious", "Precious Metals"), ("agri", "Agriculture")):
    a, prods = VARIANTS[v]; df = class_sleeves(v)
    for k in SLEEVES:
        fig, ax = setup(f"{nm}: {NICE[k]}, Equity by {UNIT[v]}")
        fn = f"figA_{v}_{k}.png"
        for i, p in enumerate(prods):
            plot(ax, nets()[(a, p)][k], PROD_COL[i], 1.4, PNAME.get(p, p), fn)
        plot(ax, df[k], EWC, 3.6, "EW (All Products)", fn)
        finish(fig, ax, f"figA_{v}_{k}.png", loc="best"); made.append(f"figA_{v}_{k}.png")

import json
json.dump(FINAL, open(os.environ.get("FINAL_JSON", os.path.join(OUT, "..", "final_values.json")), "w"), indent=1)
print(len(made), "charts written to", OUT)
