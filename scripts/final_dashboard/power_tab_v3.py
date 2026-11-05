"""Power tab of the 2012 research dashboard, tag 0930 (2026-11-04) -> Analysis/_power_build/power_tab_0930.json (tracked), merged into the page by build_final_dashboard_v3.py, which stops if the file is missing.
STANDALONE: the Power tab is not in fd_config.BUCKETS, so it is not in the All-buckets book, By Style, Cross-Pair or Correlations; it has the same structure as the bucket tabs
(performance by period for the five sleeves, EW PORT and Inverse Vol; cumulative return; by-product table; cumulative return by product).
Series: the ICE monthly real-time power futures with Calendar-2025 L = K / x below 5 days (K = USD 1M): PJM Western Hub peak and off-peak, ERCOT North peak and off-peak, MISO Indiana Hub peak
(MISO off-peak, L = 9.9, is out). Sleeves, parameters, roll rule and costs are the dashboard's (research/configs/power.py, scripts/power/power_pipeline.py -> outputs/power_0930/power_nets.pkl).
Windows: the data start on 2015-01-02 and Value needs two years of F3, so Full = 2017-01-01 to 2026-09-30, P1 (2012-2016) is not available, P2 2017-2021, P3 2022-2026, 2026 YTD.
Run from the repo root after scripts/power/power_pipeline.py and power_liquidity.py:  python scripts/final_dashboard/power_tab_v3.py"""
import json
import os
import pickle
import sys
from pathlib import Path

os.environ.setdefault("RP_PRICES_DIR", "Prices_0930")
sys.path[:0] = ["research", "research/configs", "scripts", "scripts/final_dashboard"]
import pandas as pd
from engine import combine_returns
from cross_asset_engine import combine_cross_asset
from run_regime_table import _metrics
import power as pw
from fd_config import STYLES, out_dir

TAG = "0930"
OUT = out_dir(TAG)
L_MAX = 5.0
START = "2017-01-01"
LAB = {"PJM_Peak": "PJM Peak", "PJM_OffPeak": "PJM OffPeak", "ERCOT_Peak": "ERCOT Peak", "ERCOT_OffPeak": "ERCOT OffPeak", "MISO_Peak": "MISO Peak", "MISO_OffPeak": "MISO OffPeak"}
WINDOWS = [("full", START, None), ("p1", None, None), ("p2", "2017-01-01", "2021-12-31"), ("p3", "2022-01-01", "2026-12-31"), ("y26", "2026-01-01", None)]
COLS = [dict(key="full", label="Full", years="2017-2026"), dict(key="p1", label="P1", years="n/a"), dict(key="p2", label="P2", years="2017-2021"),
        dict(key="p3", label="P3", years="2022-2026"), dict(key="y26", label="2026", years="YTD")]
EMPTY = dict(ret=None, vol=None, mdd=None, ir=None)
f3 = lambda d: {k: (None if pd.isna(v) else round(float(v), 3)) for k, v in d.items()}


def metrics(s, a, b):
    if a is None:
        return dict(EMPTY)
    return f3(_metrics(s.loc[a:b] if b else s.loc[a:]))


win = lambda rows: {w: [dict(name=k, **metrics(v, a, b)) for k, v in rows.items()] for w, a, b in WINDOWS}
pk = lambda p: f"power|{p}"


def equity(rows, step=5):
    """Cumulative LOG return from START, sampled every `step` trading days (the page rebases it and converts to % return)."""
    df = pd.concat(rows, axis=1, keys=list(rows.keys())).loc[START:]
    df = df.fillna(0.0).cumsum().iloc[::step]
    return dict(dates=[d.strftime("%Y-%m-%d") for d in df.index], series={k: [round(float(x), 5) for x in df[k]] for k in df.columns})


liq = pd.read_csv("Analysis/Power_Liquidity_Cal2025_results.csv").set_index("product")
assert (abs(liq["N_contracts_for_K"] * liq["risk_per_contract"] - 1e6) < 1).all(), "L is not on K = USD 1M"
members = [p for p in pw.PRODUCTS if float(liq.loc[p, "L_strip"]) < L_MAX]
assert members == ["PJM_Peak", "PJM_OffPeak", "ERCOT_Peak", "ERCOT_OffPeak", "MISO_Peak"], members
nets = pickle.load(open("outputs/power_0930/power_nets.pkl", "rb"))["nets"]
CUT = pd.Timestamp("2026-09-30")

styles = {}
for st in STYLES:
    ser = [nets[p][st] for p in members]
    styles[st] = combine_cross_asset(ser)
lst = list(styles.values())
ew, iv = combine_returns(lst, "equal_weight"), combine_returns(lst, "inverse_vol", vol_window=63)
rows = dict(styles)
rows["EW PORT"], rows["Inverse Vol"] = ew, iv

firsts, lasts, rolls = {}, {}, {}
for p in members:
    raw = pw.load_f1_series_logret(p).loc[:CUT]
    firsts[p], lasts[p], rolls[p] = str(raw.index.min().date()), str(raw.index.max().date()), int(raw["is_roll_date"].sum())

tab = dict(label="Power", products=[LAB[p] for p in members], pkeys=[pk(p) for p in members], windows=win(rows), cols=COLS,
           data_first=max(firsts.values()), data_last=min(lasts.values()),
           note=("Standalone tab: not part of the All-buckets book, By Style, Cross-Pair or Correlations. ICE monthly real-time power futures (USD/MWh), the five series whose Calendar-2025 "
                 "time to trade 1 sigma risk is under 5 days (MISO OffPeak, 9.9 days, is excluded). The data start in 2015, so Full is 2017-2026 (every sleeve live; Value needs two years of F3) and P1 is not available."),
           pairs={pk(p): ["-".join(x) for x in pw.carry_pairs(p)] for p in members}, rolls={pk(p): rolls[p] for p in members})
products, eq = {}, {"power": equity(rows)}
for p in members:
    d = {st: {w: metrics(nets[p][st], a, b) for w, a, b in WINDOWS} for st in STYLES}
    ew_p = combine_returns([nets[p][st] for st in STYLES], "equal_weight")
    d["EW PORT"] = {w: metrics(ew_p, a, b) for w, a, b in WINDOWS}
    products[pk(p)] = d
    eq[f"prod|power|{p}"] = equity({**{st: nets[p][st] for st in STYLES}, "EW PORT": ew_p})
out = dict(tab=tab, products=products, equity=eq,
           meta=dict(label="Power", liq={pk(p): float(liq.loc[p, "L_strip"]) for p in members}, pairs=tab["pairs"], rolls=tab["rolls"]))
TRACKED = Path("Analysis/_power_build/power_tab_0930.json")   # tracked, read by build_final_dashboard_v3.py (which stops if it is missing)
TRACKED.parent.mkdir(parents=True, exist_ok=True)
json.dump(out, open(TRACKED, "w"))
print("members:", members)
print("windows (IR):", {w: {r["name"]: r["ir"] for r in tab["windows"][w]} for w in ("full", "p2")})
print("saved", TRACKED, TRACKED.stat().st_size // 1024, "KB")
