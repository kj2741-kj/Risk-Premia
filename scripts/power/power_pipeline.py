"""US Power bucket: the five risk-premia sleeves with the research dashboard's parameters (2026-11-04) -> outputs/power_0930/power_nets.pkl and power_results.json.
Same definitions as scripts/final_dashboard/compute_products_v3.py: Momentum (1,20)/(5,60)/(20,250) shift 1 on the raw F1; Carry V2 = sign of the summed z-scores of F1-F2 and F1-F13
(252-day window); Carry-Momentum = sign of the summed 20-observation slope changes; Value F3, 1260-day average, +-10%, 504 observations minimum; Skewness = -sign of the 252-day skewness of the
daily log returns; 5 bps costs, roll days charged; roll on the 5th trading day of the expiry month. Prices cut at 2026-09-30 (the dashboard's tag 0930).
Windows: the data start on 2015-01-02 and Value needs two years of F3 before its first signal, so the full window starts 2017-01-01 (every sleeve live); P2 2017-2021, P3 2022-2026, 2026 YTD.
Run from the repo root:  python scripts/power/power_pipeline.py"""
import json, os, pickle, sys
os.environ.setdefault("RP_PRICES_DIR", "Prices_0930")
sys.path[:0] = ["research", "research/configs", "scripts"]
import numpy as np, pandas as pd
import power as pw
from engine import combine_returns, exec_shift, log_return_daily, momentum_composite_position, value_v1_position
from carry_zsum import carry_slope_change, carry_z, summed_signal
from run_regime_table import _metrics
import rolling_continuous as rc

CUT = pd.Timestamp("2026-09-30")
TC, SKEW_W, VALUE_MIN = 5, 252, 504
OUT = "outputs/power_0930"
os.makedirs(OUT, exist_ok=True)
WINDOWS = [("full", "2017-01-01", None), ("p2", "2017-01-01", "2021-12-31"), ("p3", "2022-01-01", None), ("y26", "2026-01-01", None)]
SLEEVES = ["Momentum", "Carry", "CarryMom", "Value", "Skewness"]

nets, sens, pos_all, first_live, lret = {}, {}, {}, {}, {}
nets1, rolls1 = {}, {}
for p in pw.PRODUCTS:
    curve = pw.load_curve(p).loc[:CUT]
    raw = pw.load_f1_series_logret(p).loc[:CUT]
    lp, ph, f1r = raw["log_price"], raw["Phase"], raw["F1_raw"]
    assert f1r.index.max() <= CUT
    W, H, pr = pw.CARRY_ZSCORE_WINDOW, pw.CARRY_MOMENTUM_HORIZON, pw.carry_pairs(p)
    run = lambda pos: log_return_daily(pos, lp, TC, ph)[1]
    P = {}
    P["Momentum"] = momentum_composite_position(f1r, pw.MOMENTUM_PAIRS, shift_n=pw.MOMENTUM_SHIFT_N)
    P["Carry"] = exec_shift(summed_signal([carry_z(curve, n, f, W) for n, f in pr], lp.index), pw.CARRY_SHIFT_N).fillna(0)
    P["CarryMom"] = exec_shift(summed_signal([carry_slope_change(curve, n, f, H) for n, f in pr], lp.index), pw.CARRY_MOMENTUM_SHIFT_N).fillna(0)
    P["Value"] = value_v1_position(curve, pw.VALUE_CONTRACT, pw.VALUE_LOOKBACK_DAYS, pw.VALUE_THRESHOLD, shift_n=pw.VALUE_SHIFT_N, min_periods=VALUE_MIN)
    P["Skewness"] = exec_shift(np.sign(-lp.diff().rolling(SKEW_W).skew()), 1).fillna(0)
    nets[p] = {k: run(v) for k, v in P.items()}
    pos_all[p] = P
    first_live[p] = {k: (str(v.reindex(lp.index).fillna(0).ne(0).idxmax().date()) if v.reindex(lp.index).fillna(0).ne(0).any() else None) for k, v in P.items()}
    # sensitivities: Momentum on the roll-adjusted (continuous) series; Carry on the short pair only / the long pair only
    cont = np.exp(lp)
    S = {"Momentum (continuous series)": momentum_composite_position(cont, pw.MOMENTUM_PAIRS, shift_n=1),
         "Carry F1-F2 only": exec_shift(summed_signal([carry_z(curve, "F1", "F2", W)], lp.index), 1).fillna(0),
         "Carry F1-F13 only": exec_shift(summed_signal([carry_z(curve, "F1", "F13", W)], lp.index), 1).fillna(0)}
    sens[p] = {k: run(v) for k, v in S.items()}
    lret[p] = lp.diff()
    # sensitivity: roll on the 2nd trading day of the delivery month (one trading day in the partly settled contract; N=1 collides with the bridge day and the engine then skips the roll, so it is not usable); the signals are unchanged, only the held contract and costs
    raw1 = pw.load_f1_series_logret(p, roll_n=2).loc[:CUT]
    run1 = lambda pos: log_return_daily(pos, raw1["log_price"], TC, raw1["Phase"])[1]
    nets1[p] = {k: run1(v) for k, v in P.items()}
    rolls1[p] = int(raw1["is_roll_date"].sum())
    print("done", p, first_live[p], flush=True)

pickle.dump(dict(nets=nets, nets_roll2=nets1, sens=sens, first_live=first_live, lret=lret, pos=pos_all), open(f"{OUT}/power_nets.pkl", "wb"))


def met(s, a, b=None):
    m = _metrics(s.loc[a:b] if b else s.loc[a:])
    return {k: (None if (v is None or (isinstance(v, float) and np.isnan(v))) else round(float(v), 3)) for k, v in m.items()}


res = {"products": {}, "bucket": {}, "sens": {}, "first_live": first_live, "roll_fallbacks": rc.ROLL_FALLBACK_COUNT["n"]}
for p in pw.PRODUCTS:
    res["products"][p] = {k: {w: met(nets[p][k], a, b) for w, a, b in WINDOWS} for k in SLEEVES}
idx = nets[pw.PRODUCTS[0]]["Momentum"].index
ew = {k: sum(nets[p][k].reindex(idx).fillna(0) for p in pw.PRODUCTS) / len(pw.PRODUCTS) for k in SLEEVES}
ew_port = sum(ew.values()) / len(SLEEVES)
iv = combine_returns([ew[k] for k in SLEEVES], "inverse_vol", vol_window=63)
bucket = {**ew, "EW PORT": ew_port, "Inverse Vol": iv}
res["bucket"] = {k: {w: met(v, a, b) for w, a, b in WINDOWS} for k, v in bucket.items()}
res["sens"] = {k: {w: met(sum(sens[p][k].reindex(idx).fillna(0) for p in pw.PRODUCTS) / len(pw.PRODUCTS), a, b) for w, a, b in WINDOWS} for k in next(iter(sens.values()))}
ew1 = {k: sum(nets1[p][k].reindex(idx).fillna(0) for p in pw.PRODUCTS) / len(pw.PRODUCTS) for k in SLEEVES}
res["roll_on_2nd_td"] = {k: {w: met(v, a_, b_) for w, a_, b_ in WINDOWS} for k, v in {**ew1, "EW PORT": sum(ew1.values()) / len(SLEEVES)}.items()}
res["roll_on_2nd_td_rolls"] = rolls1
# 2015-2016 warm-up window and the full data window, for reference
res["bucket_from_2015"] = {k: met(v, "2015-01-01") for k, v in bucket.items()}
# redundancy: correlation of the daily log returns of the six roll-adjusted series (2017 onwards)
L = pd.concat(lret, axis=1).loc["2017-01-01":].dropna()
res["corr_returns"] = L.corr().round(2).to_dict()
# correlation of the sleeve returns across products, average pairwise (how many independent bets)
avgc = {k: round(float(np.nanmean(np.triu(pd.concat({p: nets[p][k] for p in pw.PRODUCTS}, axis=1).loc["2017-01-01":].corr().values, 1)[np.triu_indices(6, 1)])), 2) for k in SLEEVES}
res["avg_pairwise_corr_of_sleeve_returns"] = avgc
# seasonality of the signals: share of the variance of each position explained by the calendar month (R-squared of a 12-month-dummy regression, 2017 onwards); 1 = the position is a pure calendar rule
def month_r2(pos):
    s = pos.loc["2017-01-01":].dropna()
    return float(1 - ((s - s.groupby(s.index.month).transform("mean")) ** 2).sum() / ((s - s.mean()) ** 2).sum()) if s.var() > 0 else None
res["signal_month_r2"] = {p: {k: (None if month_r2(pos_all[p][k]) is None else round(month_r2(pos_all[p][k]), 3)) for k in SLEEVES} for p in pw.PRODUCTS}
json.dump(res, open(f"{OUT}/power_results.json", "w"), indent=1)
pickle.dump(bucket, open(f"{OUT}/power_bucket_series.pkl", "wb"))
print("saved", OUT)
