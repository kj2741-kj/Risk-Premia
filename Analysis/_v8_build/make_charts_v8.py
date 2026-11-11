"""All charts of Risk Premia Analysis v8: seven buckets on the 30 September 2026 data (return index, start = 100%)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from itertools import combinations
from rp import *
from facts3 import bystyle, PAIR_ORDER, pair_series, SHORT

OUT = os.path.join(S, "img8"); os.makedirs(OUT, exist_ok=True)
COL = {"Momentum": "#C58F56", "Carry": "#D6BC74", "CarryMom": "#5FA3A0", "Value": "#7FBF96", "Skewness": "#B898B0"}
EWC, IVC = "#111111", "#2B72B8"
PROD_COL = ["#C58F56", "#D6BC74", "#5FA3A0", "#7FBF96", "#C97B7B", "#B898B0"]
PAIR_COL = ["#E08A1E", "#E8C547", "#1F9E9A", "#6FBF4A", "#D9534F", "#8E44AD", "#7F7F7F", "#8C6D1F", "#2B72B8", "#5B3A29", "#C2185B", "#00897B", "#3949AB", "#F4511E", "#546E7A", "#0B6E4F", "#A23B72", "#F18F01", "#3B1F2B", "#6C91BF", "#B5838D"]
PAIR_LS = ["-"] * 7 + ["--"] * 7 + [":"] * 7
PNAME = {"SingaporeGasoil": "Gas Oil", "HeatingOil": "Heating Oil", "NatGas": "Henry Hub", "SoybeanOil": "Soybean Oil", "UKGas": "UK Gas", "EUA": "EUA", "LiveCattle": "Live Cattle", "NatGasoline": "Natural Gasoline"}
NICE = {"Momentum": "Momentum", "Carry": "Carry", "CarryMom": "Carry-Momentum", "Value": "Value", "Skewness": "Skewness"}
FINAL = {}
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


def finish(fig, ax, name, loc="upper left", ncol=2, fs=8.5):
    ax.legend(loc=loc, ncol=ncol, fontsize=fs, framealpha=0.95)
    ax.set_xlim(pd.Timestamp("2011-05-01"), pd.Timestamp("2026-12-31"))
    fig.tight_layout(); fig.savefig(os.path.join(OUT, name), dpi=150); plt.close(fig)


made = []
TITLE = {"metals": "Metals", "petroleum": "Petroleum", "pen": "Gas and Emissions", "ngl": "NGL", "precious": "Precious Metals", "agri": "Agriculture", "softs": "Softs"}
UNIT = {"metals": "Metal", "petroleum": "Product", "pen": "Product", "ngl": "Product", "precious": "Metal", "agri": "Product", "softs": "Product"}
for v in BUCKETS:
    df = class_sleeves(v); ew, iv = class_portfolios(v)
    fn = f"fig_{v}_combined.png"
    fig, ax = setup(f"{TITLE[v]}: Combined Strategies")
    for k in SLEEVES:
        plot(ax, df[k], COL[k], 1.4, NICE[k], fn)
    plot(ax, ew, EWC, 3.6, "EW Portfolio", fn)
    plot(ax, iv, IVC, 3.6, "Inverse Vol", fn)
    finish(fig, ax, fn); made.append(fn)
    for k in SLEEVES:
        fn = f"figA_{v}_{k}.png"
        fig, ax = setup(f"{TITLE[v]}: {NICE[k]}, Equity by {UNIT[v]}")
        for i, (a, p) in enumerate(MEMBERS[v]):
            plot(ax, nets()[(a, p)][k], PROD_COL[i], 1.4, PNAME.get(p, p), fn)
        plot(ax, df[k], EWC, 3.6, "EW (All Products)", fn)
        finish(fig, ax, fn, loc="best"); made.append(fn)

# cross-commodity book: by style across the seven buckets, with the two portfolio constructions
style = bystyle()
ewp = style["EW PORT"]; ivp = style["Inverse Vol"]
fig, ax = setup("Cross-Commodity Portfolio: Combined Strategies")
for k in SLEEVES:
    plot(ax, style[k], COL[k], 1.4, NICE[k], "fig_cross_combined.png")
plot(ax, ewp, EWC, 3.6, "EW Portfolio", "fig_cross_combined.png")
plot(ax, ivp, IVC, 3.6, "Inverse Vol", "fig_cross_combined.png")
finish(fig, ax, "fig_cross_combined.png"); made.append("fig_cross_combined.png")

# the twenty-one bucket pairs
for meth, ttl in (("EW", "Equal Weight"), ("IV", "Inverse Vol")):
    fig, ax = setup(f"Cross-Pair Portfolios: {ttl}")
    for i, (a, b) in enumerate(PAIR_ORDER):
        plot(ax, pair_series(a, b, meth), PAIR_COL[i], 1.6, f"{SHORT[a]}-{SHORT[b]}", f"figA_pairs_{meth}.png", ls=PAIR_LS[i])
    finish(fig, ax, f"figA_pairs_{meth}.png", ncol=2, fs=7.5); made.append(f"figA_pairs_{meth}.png")
import json
json.dump(FINAL, open(os.path.join(S, "final_values8.json"), "w"), indent=1)
print(len(made), "charts written to", OUT)
