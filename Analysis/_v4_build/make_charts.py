import sys, os
sys.path.insert(0, ".")
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from rp import *

OUT = os.path.join(S, "v4img"); os.makedirs(OUT, exist_ok=True)
COL = {"Momentum": "#C58F56", "Carry": "#D6BC74", "CarryMom": "#5FA3A0", "Value": "#7FBF96", "Skewness": "#B898B0"}
EWC, IVC = "#111111", "#2B72B8"
PROD_COL = ["#C58F56", "#D6BC74", "#5FA3A0", "#7FBF96", "#C97B7B", "#B898B0"]
PAIR_COL = ["#C58F56", "#D6BC74", "#5FA3A0", "#7FBF96", "#C97B7B", "#B898B0", "#8C8C8C", "#BBAA55", "#4A7FB5", "#A5602F"]
NICE = {"Momentum": "Momentum", "Carry": "Carry", "CarryMom": "Carry-Momentum", "Value": "Value", "Skewness": "Skewness"}
START = "2012-01-01"


def cum(r):
    r = r.loc[START:].fillna(0)
    return (np.exp(r.cumsum()) - 1) * 100


def setup(title):
    fig, ax = plt.subplots(figsize=(9.9, 5.9), dpi=150)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_ylabel("Cumulative Return (%)")
    ax.grid(True, color="#e5e5e5", linewidth=0.8); ax.set_axisbelow(True)
    ax.axhline(0, color="#999999", linewidth=1.0, zorder=1)
    return fig, ax


def finish(fig, ax, name, loc="upper left", ncol=2):
    ax.legend(loc=loc, ncol=ncol, fontsize=8.5, framealpha=0.95)
    ax.set_xlim(pd.Timestamp("2011-05-01"), pd.Timestamp("2026-12-31"))
    fig.tight_layout(); fig.savefig(os.path.join(OUT, name), dpi=150); plt.close(fig)


made = []
# --- combined strategies per asset class (five sleeves + EW + IV)
for v, nm in (("metals", "Metals"), ("energy", "Energy"), ("precious", "Precious Metals"), ("ngl", "NGL"), ("agri", "Agriculture")):
    df = class_sleeves(v); ew, iv = class_portfolios(v)
    fig, ax = setup(f"{nm}: Combined Strategies")
    for k in SLEEVES:
        c = cum(df[k]); ax.plot(c.index, c.values, color=COL[k], lw=1.4, alpha=0.95, label=NICE[k] if k != "CarryMom" else "CarryMom")
    c = cum(ew); ax.plot(c.index, c.values, color=EWC, lw=3.6, label="EW Portfolio")
    c = cum(iv); ax.plot(c.index, c.values, color=IVC, lw=3.6, label="Inverse Vol")
    finish(fig, ax, f"fig_{v}_combined.png"); made.append(f"fig_{v}_combined.png")

# --- cross-commodity (By Style, with NatGas)
keys = ["metals", "energy", "ngl", "precious", "agri"]
tabs = {t: class_sleeves(t) for t in keys}
style = pd.DataFrame({k: ew_intersection([tabs[t][k].dropna() for t in keys]) for k in SLEEVES}).dropna()
ewp = style.mean(axis=1, skipna=False); ivp = inverse_vol(style)
fig, ax = setup("Cross-Commodity Portfolio: Combined Strategies")
for k in SLEEVES:
    c = cum(style[k]); ax.plot(c.index, c.values, color=COL[k], lw=1.4, alpha=0.95, label=k)
c = cum(ewp); ax.plot(c.index, c.values, color=EWC, lw=3.6, label="EW Portfolio")
c = cum(ivp); ax.plot(c.index, c.values, color=IVC, lw=3.6, label="Inverse Vol")
finish(fig, ax, "fig_cross_combined.png"); made.append("fig_cross_combined.png")

# --- per-product equity curves for each sleeve
UNIT = {"metals": "Metal", "precious": "Metal", "energy": "Product", "ngl": "Product", "agri": "Product"}
for v, nm in (("metals", "Metals"), ("energy", "Energy"), ("precious", "Precious Metals"), ("ngl", "NGL"), ("agri", "Agriculture")):
    a, prods = VARIANTS[v]; df = class_sleeves(v)
    for k in SLEEVES:
        fig, ax = setup(f"{nm}: {NICE[k]}, Equity by {UNIT[v]}")
        for i, p in enumerate(prods):
            c = cum(nets()[(a, p)][k]); ax.plot(c.index, c.values, color=PROD_COL[i], lw=1.4, alpha=0.95, label=p)
        c = cum(df[k]); ax.plot(c.index, c.values, color=EWC, lw=3.6, label="EW (All Products)")
        finish(fig, ax, f"figA_{v}_{k}.png", loc="best"); made.append(f"figA_{v}_{k}.png")

# --- cross-pair portfolios (Energy including NatGas)
from itertools import combinations
labels = {"metals": "Metals", "energy": "Energy", "ngl": "NGL", "precious": "Precious", "agri": "Agriculture"}
order = [("metals", "energy"), ("metals", "precious"), ("metals", "ngl"), ("metals", "agri"), ("energy", "precious"),
         ("energy", "ngl"), ("energy", "agri"), ("precious", "ngl"), ("precious", "agri"), ("ngl", "agri")]
for meth, ix, ttl in (("EW", 0, "Equal Weight"), ("IV", 1, "Inverse Vol")):
    port = {t: class_portfolios(t)[ix] for t in keys}
    fig, ax = setup(f"Cross-Pair Portfolios: {ttl}")
    for i, (a, b) in enumerate(order):
        cl = [port[a].dropna().cumsum(), port[b].dropna().cumsum()]
        idx = cl[0].index.intersection(cl[1].index).sort_values()
        al = pd.DataFrame({a: cl[0].reindex(idx).diff(), b: cl[1].reindex(idx).diff()})
        ser = al.mean(axis=1, skipna=False) if meth == "EW" else inverse_vol(al)
        c = cum(ser); ax.plot(c.index, c.values, color=PAIR_COL[i], lw=1.5, label=f"{labels[a]}-{labels[b]}")
    finish(fig, ax, f"figA_pairs_{meth}.png"); made.append(f"figA_pairs_{meth}.png")
print(len(made), "charts written to", OUT)
