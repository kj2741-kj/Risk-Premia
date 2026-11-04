"""Writes Analysis/Power_Bucket_Analysis_2026-11-04.md from outputs/power_0930/power_results.json and the liquidity CSVs (run power_pipeline.py and power_liquidity.py first).
Run from the repo root:  python scripts/power/power_report.py"""
import json
import pandas as pd

r = json.load(open("outputs/power_0930/power_results.json"))
liq = pd.read_csv("Analysis/Power_Liquidity_Cal2025_results.csv")
base = pd.read_csv("Analysis/Liquidity_Cal2025_results.csv")
S = ["Momentum", "Carry", "CarryMom", "Value", "Skewness"]
SN = {"Momentum": "Momentum", "Carry": "Carry", "CarryMom": "Carry-Mom.", "Value": "Value", "Skewness": "Skewness"}
LAB = {"PJM_Peak": "PJM Peak", "PJM_OffPeak": "PJM Off-peak", "ERCOT_Peak": "ERCOT Peak", "ERCOT_OffPeak": "ERCOT Off-peak", "MISO_Peak": "MISO Peak", "MISO_OffPeak": "MISO Off-peak"}
f = lambda v, k=2: "n/a" if v is None else f"{v:.{k}f}"
fx = lambda v: f"{v:,.1f}" if v >= 10 else (f"{v:,.2f}" if v >= 1 else f"{v:.3f}")
mr = r["signal_month_r2"]
rng = lambda k: f"{min(mr[p][k] for p in mr):.2f}-{max(mr[p][k] for p in mr):.2f}"
o = []
A = o.append
A("# US Power bucket: data, expiry and roll alignment, liquidity, risk-premia sleeves (2026-11-04)\n")
A("Files: `data/Emissions_1029/PJM_Power_Futures.xlsx`, `US_Power_Futures.xlsx` (Bloomberg pull 2026-11-03). Code: `research/configs/power.py`, `scripts/make_power_calendars.py`, `scripts/power/` "
  "(`power_validate.py`, `power_pipeline.py`, `power_liquidity.py`, `power_report.py`). Prices cut at 2026-09-30 (the dashboard's tag 0930).\n")
A("## 1. How many series are possible\n")
A("| Family | Series | History | Tenors | Usable for the strategies |\n|---|---|---|---|---|\n"
  "| ICE PJM Western Hub RT, peak and off-peak | 2 | 2015-01-02 to 2026-11-02 | F1-F122 | Yes |\n"
  "| ICE ERCOT North 345KV RT, peak and off-peak | 2 | 2015-01-02 to 2026-11-02 | F1-F48 | Yes |\n"
  "| ICE MISO Indiana Hub RT, peak and off-peak | 2 | 2015-01-02 to 2026-11-02 | F1-F48 | Yes |\n"
  "| CME PJM Western Hub RT, peak and off-peak | 2 | 2026-05-11 (122 days) | F1-F110 / F1-F72 | No: too short, and volume and open interest are empty |\n"
  "| CME ERCOT North RT, peak and off-peak | 2 | 2026-08-31 (45 days) | F1-F48 | No: same |\n"
  "| 'Active contract' series (single continuation, 10 columns) | 10 | from 2017-01-23 | one price | Not used: no curve, so no Carry or Value |\n")
A("**Ten generic families are in the files and six are usable: the ICE series, all from 2015-01-02, every tenor quoted from the first day (no gaps in F1).** About 11.7 years of data to 2026-09-30, "
  "against 14.7 years for the other buckets, so the dashboard's Full window (from 2012) cannot be reproduced; Section 4 uses 2017 onwards.\n")
c = pd.DataFrame(r["corr_returns"])
A("**Independent bets.** Daily log-return correlation of the six roll-adjusted series (2017 onwards):\n")
A("| | " + " | ".join(LAB[p] for p in c.columns) + " |\n|---|" + "---|" * len(c.columns))
for p in c.index:
    A(f"| {LAB[p]} | " + " | ".join(f"{c.loc[p, q]:.2f}" for q in c.columns) + " |")
A("\nPJM and MISO are near duplicates (0.82 to 0.92) and peak and off-peak of one hub are 0.73 to 0.92, so the six series are about two independent bets (PJM/MISO and ERCOT, correlation about 0.4 between the two).\n")
A("## 2. Expiry and roll alignment\n")
A("- **Contract cycle checked (2026-11-04): every series is monthly, not bimonthly.** All ten calendars list every delivery month with no gaps and no duplicates (264 PJM ICE contracts for 2015-2036, 204 ERCOT and MISO ICE for 2015-2031), "
  "each year of 2015-2026 has exactly 12 last trade dates, and in the 2026-11-03 snapshot consecutive generics are exactly one month apart (F1 = Nov-2026, F2 = Dec-2026, F13 = Nov-2027). "
  "So F2 is the next month, F13 is the same month a year later, and the F1-F12 volume strip is twelve consecutive months. (The snapshot carries one extra trailing row per product, a repeat of the front month.)\n"
  "- All ICE contracts are monthly and their **last trade date falls inside the delivery month** (the last business day, at most four days before month end, every contract checked). "
  "The generic F1 is therefore the contract delivering now, partly settled against realised prices.\n"
  "- Calendar: `Power_Expiry_Calendars.xlsx` (one sheet per root) built from the EXPIRY_HISTORY sheets in the format `rolling_continuous` reads. Rule: the repo-wide research rule, "
  "roll on the **5th trading day of the month in which the last trade date falls**, which here is the 5th trading day of the delivery month; bridge on the day after the last trade date.\n"
  "- Result: **every roll on the 5th trading day** of the expiry month (141 of 141 for PJM Peak and ERCOT Peak, 140 of 140 for the others), every bridge on the trading day after the last trade date "
  "(one per series is missing: the 30-Sep-2026 contract, whose bridge is after the cut), **0 roll fallbacks**.\n"
  "- Data test of the Bloomberg generic: F1 moves to the next contract the day after the last trade date in 82 to 87% of contracts (3 to 7% on the last trade date itself); "
  "it is the best-fitting switch day among six candidates in 49 to 63% (chance 17%).\n"
  "- Effect: a position holds the next-month contract from the 5th trading day of the previous month, through the last trade date, and is on F1 (the same contract, now in delivery) "
  "for the first 4 to 5 trading days of its delivery month, so those days are in a partly settled contract. Rolling on the 2nd trading day instead is tested in Section 4 "
  "(the 1st trading day is not usable: the roll lands on the bridge day and the engine then skips it).\n")
A("## 3. Liquidity, Calendar 2025 (K = USD 1M, 2025 data only)\n")
A("Same method as the 26-product table (x = ADV x price x sigma x multiplier, USD millions of one-sigma daily risk traded per day; L = K / x in days). "
  "ADV is volume summed over F1-F12; 'held' uses only the contract the strategy holds.\n")
A("| Series | ADV F1-F12 (lots/day) | Days traded | Price (USD/MWh) | Sigma (daily) | Multiplier (MWh) | x (USD m/day) | L (days) | x held (USD m/day) | L held (days) | Rank among 32 |\n"
  "|---|---|---|---|---|---|---|---|---|---|---|")
allx = pd.concat([base[["product", "x_strip"]], liq[["product", "x_strip"]]]).sort_values("x_strip", ascending=False).reset_index(drop=True)
for _, q in liq.iterrows():
    rk = int(allx.index[allx["product"] == q["product"]][0]) + 1
    A(f"| {LAB[q['product']]} | {q['adv_strip']:,.0f} | {q['share_days_print']*100:.0f}% | {q['price_usd_mwh']:.1f} | {q['sigma']*100:.2f}% | {q['mult_mwh']:.0f} | "
      f"{fx(q['x_strip'])} | {1/q['x_strip']:.3f} | {fx(q['x_held'])} | {1/q['x_held']:.2f} | {rk} |")
A("\nFor reference (same method): Lead x = 19.3, Palladium 23.9, Propane 4.85, Ethane 0.35, Isobutane 0.006. **Only PJM Peak (x = 10.0) is near the least liquid non-energy products; "
  "ERCOT Peak and PJM Off-peak (2.8, 2.1) sit between Butane (1.8) and Propane (4.85); ERCOT Off-peak, MISO Peak and MISO Off-peak (0.21, 0.21, 0.10) are below Ethane (0.35).** "
  "On the held contract the figures are lower still (PJM Peak 2.8, MISO Off-peak 0.02). 33 to 68% of the 2025 volume sits beyond F12 (calendar strips), which the strategies do not trade.\n")
A("Contract size, checked on ice.com on 2026-11-04: all six monthly contracts are 1 MW (1 MW for every hour of the contract period, so 304-368 MWh a lot for peak and 352-417 for off-peak in 2025, as used). "
  "The 800 and 50 in the Bloomberg size field are the daily contracts (800 MWh peak, 50 MWh off-peak), which is why the field is inconsistent; the multipliers and the liquidity above are unchanged.\n")
A("Not measurable: the four CME series. Their VOLUME and OPEN INTEREST sheets contain no values at all (0 non-null cells), although prices are quoted "
  "(118 distinct F1 prices in 122 days for PJM Peak).\n")
A("## 4. Risk-premia sleeves, dashboard parameters\n")
A("Momentum (1,20)/(5,60)/(20,250), shift 1, on the raw F1; Carry V2: sign of the summed z-scores of F1-F2 and F1-F13 (252 days); Carry-Momentum: summed 20-observation slope changes; "
  "Value: F3, 1,260-day average, +-10%, 504 observations minimum; Skewness: 252 days; 5 bps costs, roll days charged; 5th trading day roll; EW across the six series, "
  "then EW PORT and Inverse Vol (63 days). **Window: Full = 2017-01-01 to 2026-09-30**, because the data start 2015-01-02 and Value needs two years of F3 (first Value positions 2016-12); "
  "P2 2017-2021, P3 2022-2026, 2026 YTD. Information ratio on the full span of each window, as in the dashboard.\n")
for w, wl in (("full", "Full 2017-2026"), ("p2", "P2 2017-2021"), ("p3", "P3 2022-2026"), ("y26", "2026 YTD")):
    A(f"**IR, {wl}**\n")
    A("| | " + " | ".join(SN[k] for k in S) + " |\n|---|" + "---|" * len(S))
    for p in r["products"]:
        A(f"| {LAB[p]} | " + " | ".join(f(r["products"][p][k][w]["ir"]) for k in S) + " |")
    A("| **EW bucket** | " + " | ".join("**" + f(r["bucket"][k][w]["ir"]) + "**" for k in S) + " |\n")
A("**Bucket sleeves and portfolios, Full 2017-2026** (annual return %, volatility %, max drawdown %, IR)\n")
A("| | Return | Vol | Max DD | IR | P2 IR | P3 IR | 2026 IR |\n|---|---|---|---|---|---|---|---|")
for k in S + ["EW PORT", "Inverse Vol"]:
    b = r["bucket"][k]
    A(f"| {SN.get(k, k)} | {f(b['full']['ret'], 1)} | {f(b['full']['vol'], 1)} | {f(b['full']['mdd'], 1)} | {f(b['full']['ir'])} | {f(b['p2']['ir'])} | {f(b['p3']['ir'])} | {f(b['y26']['ir'])} |")
import pickle
import numpy as np
B = pickle.load(open("outputs/power_0930/power_bucket_series.pkl", "rb"))
sh = lambda x: float(x.mean() / x.std(ddof=1) * np.sqrt(252))
A("\n**Log-return Sharpe of the bucket sleeves** (mean / standard deviation x sqrt 252 of the daily log returns). The dashboard's IR divides the compounded annual return by volatility, "
  "which exaggerates large up-years when volatility is 50% or more; this is the plain measure.\n")
A("| | Full 2017-2026 | P2 | P3 | 2026 YTD |\n|---|---|---|---|---|")
for k in S + ["EW PORT", "Inverse Vol"]:
    x = B[k]
    A(f"| {SN.get(k, k)} | {sh(x.loc['2017-01-01':]):.2f} | {sh(x.loc['2017-01-01':'2021-12-31']):.2f} | {sh(x.loc['2022-01-01':]):.2f} | {sh(x.loc['2026-01-01':]):.2f} |")
A("\nAverage pairwise correlation of the six products' returns within a sleeve: " + ", ".join(f"{SN[k]} {v:.2f}" for k, v in r["avg_pairwise_corr_of_sleeve_returns"].items()) + ".\n")
A("**Sensitivities (EW bucket IR; Full / P2 / P3 / 2026)**\n")
A("| Variant | Full | P2 | P3 | 2026 |\n|---|---|---|---|---|")
for k in S + ["EW PORT"]:
    A(f"| Roll on the 2nd trading day, {SN.get(k, k)} (5th: {f(r['bucket'][k]['full']['ir'])}) | " + " | ".join(f(r["roll_on_2nd_td"][k][w]["ir"]) for w in ("full", "p2", "p3", "y26")) + " |")
for k, v in r["sens"].items():
    A(f"| {k} | " + " | ".join(f(v[w]["ir"]) for w in ("full", "p2", "p3", "y26")) + " |")
A(f"\nSeasonality of the positions (R-squared of the position on calendar-month dummies, 2017 onwards): Momentum {rng('Momentum')}, Carry {rng('Carry')}, Carry-Momentum {rng('CarryMom')}, "
  f"Value {rng('Value')}, Skewness {rng('Skewness')}. The signals are partly, not mainly, calendar rules.\n")
open("Analysis/Power_Bucket_Analysis_2026-11-04.md", "w", encoding="utf-8", newline="").write("\n".join(o))
print("written", len("\n".join(o)), "chars")
