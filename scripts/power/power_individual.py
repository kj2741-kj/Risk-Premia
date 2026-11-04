"""Individual (per-product) risk-premia results for the US Power series whose Calendar-2025 liquidity L = K/x is below 5 days (K = USD 1M) -> Analysis/Power_Individual_Results_2026-11-04.md.
Reads outputs/power_0930/power_nets.pkl (power_pipeline.py) and Analysis/Power_Liquidity_Cal2025_results.csv (power_liquidity.py). Same parameters and windows as power_pipeline.py;
per product: the five sleeves, plus the product's own EW PORT (equal weight of its five sleeves) and Inverse Vol (63 days). No cross-product combination.
Run from the repo root:  python scripts/power/power_individual.py"""
import os, pickle, sys
sys.path[:0] = ["research", "research/configs", "scripts"]
import numpy as np, pandas as pd
from engine import combine_returns
from run_regime_table import _metrics

L_MAX = 5.0
LAB = {"PJM_Peak": "PJM Western Hub, peak", "PJM_OffPeak": "PJM Western Hub, off-peak", "ERCOT_Peak": "ERCOT North, peak", "ERCOT_OffPeak": "ERCOT North, off-peak",
       "MISO_Peak": "MISO Indiana Hub, peak", "MISO_OffPeak": "MISO Indiana Hub, off-peak"}
SN = {"Momentum": "Momentum", "Carry": "Carry", "CarryMom": "Carry-Momentum", "Value": "Value", "Skewness": "Skewness", "EW PORT": "EW PORT (5 sleeves)", "Inverse Vol": "Inverse Vol (5 sleeves)"}
S = ["Momentum", "Carry", "CarryMom", "Value", "Skewness"]
WIN = [("Full 2017-2026", "2017-01-01", None), ("P2 2017-2021", "2017-01-01", "2021-12-31"), ("P3 2022-2026", "2022-01-01", None), ("2026 YTD", "2026-01-01", None)]

liq = pd.read_csv("Analysis/Power_Liquidity_Cal2025_results.csv")
liq["L_strip"] = 1e6 / (liq["x_strip"] * 1e6)
liq["L_held"] = 1e6 / (liq["x_held"] * 1e6)
sel = liq[liq["L_strip"] < L_MAX].sort_values("L_strip")["product"].tolist()
N = pickle.load(open("outputs/power_0930/power_nets.pkl", "rb"))["nets"]
f = lambda v, k=2: "n/a" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.{k}f}"
sh = lambda x: float(x.mean() / x.std(ddof=1) * np.sqrt(252))
o = []
A = o.append
A("# US Power: individual results for the series with L < 5 days (2026-11-04)\n")
A(f"Selection: Calendar-2025 L = K / x below {L_MAX:g} days with K = USD 1M, F1-F12 ADV (the table in `Power_Bucket_Analysis_2026-11-04.md`). Contract size confirmed on ice.com: all six monthly contracts are 1 MW "
  "(1 MW for every hour of the contract period), so the multipliers, and the liquidity, are unchanged. MISO Off-peak (L = 9.9) is out. No cross-product combination: each table is one product.\n")
A("| Product | L (days, F1-F12) | L held contract (days) | x (USD m/day) |\n|---|---|---|---|")
for p in sel:
    q = liq[liq["product"] == p].iloc[0]
    A(f"| {LAB[p]} | {q['L_strip']:.2f} | {q['L_held']:.1f} | {q['x_strip']:.2f} |")
A("\nOn the held contract (the one the strategy trades) only PJM Peak, ERCOT Peak and PJM Off-peak stay under 5 days; ERCOT Off-peak (31.7) and MISO Peak (15.3) do not.\n")
A("Window: Full = 2017-01-01 to 2026-09-30 (the data start 2015-01-02 and Value needs two years of F3). Return = compounded annual return %, Vol = annualised volatility of simple returns %, "
  "Max DD = value-based maximum drawdown %, IR = Return / Vol (the dashboard's convention), Sharpe = mean / std x sqrt 252 of the daily log returns.\n")
for p in sel:
    idx = N[p]["Momentum"].index
    ser = {k: N[p][k].reindex(idx).fillna(0) for k in S}
    ser["EW PORT"] = sum(ser[k] for k in S) / 5
    ser["Inverse Vol"] = combine_returns([ser[k] for k in S], "inverse_vol", vol_window=63)
    A(f"## {LAB[p]}\n")
    A("| | Ret % | Vol % | Max DD % | IR Full | Sharpe Full | IR P2 | IR P3 | IR 2026 |\n|---|---|---|---|---|---|---|---|---|")
    for k in S + ["EW PORT", "Inverse Vol"]:
        x = ser[k]; m = {w: _metrics(x.loc[a:b] if b else x.loc[a:]) for w, a, b in WIN}
        A(f"| {SN[k]} | {f(m['Full 2017-2026']['ret'], 1)} | {f(m['Full 2017-2026']['vol'], 1)} | {f(m['Full 2017-2026']['mdd'], 1)} | {f(m['Full 2017-2026']['ir'])} | {sh(x.loc['2017-01-01':]):.2f} | "
          f"{f(m['P2 2017-2021']['ir'])} | {f(m['P3 2022-2026']['ir'])} | {f(m['2026 YTD']['ir'])} |")
    A("")
open("Analysis/Power_Individual_Results_2026-11-04.md", "w", encoding="utf-8", newline="").write("\n".join(o))
print("\n".join(o))
