"""Charts of the US Power (standalone) section of v8: return index, start = 100% on 2017-01-01 (the Full window of the Power bucket)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from power_facts import *

OUT = os.path.join(S, "img8"); os.makedirs(OUT, exist_ok=True)
COL = {"Momentum": "#C58F56", "Carry": "#D6BC74", "CarryMom": "#5FA3A0", "Value": "#7FBF96", "Skewness": "#B898B0"}
EWC, IVC = "#111111", "#2B72B8"
PROD_COL = ["#C58F56", "#D6BC74", "#5FA3A0", "#7FBF96", "#C97B7B"]
NICE = {"Momentum": "Momentum", "Carry": "Carry", "CarryMom": "Carry-Momentum", "Value": "Value", "Skewness": "Skewness"}
START = "2017-01-01"; FINAL = {}


def cum(r):
    return np.exp(r.loc[START:].fillna(0).cumsum()) * 100


def setup(title):
    fig, ax = plt.subplots(figsize=(9.9, 5.9), dpi=150)
    ax.set_title(title, fontsize=13, fontweight="bold"); ax.set_ylabel("Cumulative Return (start = 100%)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}%")); ax.grid(True, color="#e5e5e5", linewidth=0.8); ax.set_axisbelow(True)
    ax.axhline(100, color="#999999", linewidth=1.0, zorder=1)
    return fig, ax


def plot(ax, ser, color, lw, label, fig_name):
    c = cum(ser); ax.plot(c.index, c.values, color=color, lw=lw, alpha=0.95, label=label); FINAL.setdefault(fig_name, {})[label] = float(c.iloc[-1])


def finish(fig, ax, name, loc="upper left"):
    ax.legend(loc=loc, ncol=2, fontsize=8.5, framealpha=0.95); ax.set_xlim(pd.Timestamp("2016-09-01"), pd.Timestamp("2026-12-31"))
    fig.tight_layout(); fig.savefig(os.path.join(OUT, name), dpi=150); plt.close(fig)


fn = "fig_power_combined.png"; fig, ax = setup("US Power: Combined Strategies")
for k in SLEEVES: plot(ax, STY_P[k], COL[k], 1.4, NICE[k], fn)
plot(ax, EW_P, EWC, 3.6, "EW Portfolio", fn); plot(ax, IV_P, IVC, 3.6, "Inverse Vol", fn); finish(fig, ax, fn)
for k in SLEEVES:
    fn = f"figA_power_{k}.png"; fig, ax = setup(f"US Power: {NICE[k]}, Equity by Product")
    for i, p in enumerate(MEMBERS_P): plot(ax, NETS_P[p][k], PROD_COL[i], 1.4, LABEL_P[p], fn)
    plot(ax, STY_P[k], EWC, 3.6, "EW (All Products)", fn); finish(fig, ax, fn, loc="best")
json.dump(FINAL, open(os.path.join(S, "final_values_power.json"), "w"), indent=1)
print("6 power charts written to", OUT)
