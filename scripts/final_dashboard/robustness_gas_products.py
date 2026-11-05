"""Robustness of the TTF and UK Gas edge over Henry Hub (2026-11-04). Run from the repo root:
   RP_PRICES_DIR=Prices_1029_merged python scripts/final_dashboard/robustness_gas_products.py
Same sleeves, signals, roll rule and costs as compute_products_v3.py (baseline reproduces products_nets.pkl). Tests, all applied identically to the three products:
 1 year-by-year Sharpe of the equal-weight portfolio of the five sleeves (EW PORT) and how often TTF / UK Gas beat Henry Hub
 2 paired stationary block bootstrap (mean block 20 days, 4000 resamples) of the Sharpe DIFFERENCE vs Henry Hub, on common dates
 3 exclusion of the 2021-07 to 2023-06 gas crisis
 4 parameter variations: costs 5/10/20 bps, Carry tenor pairs, Momentum pairs
 5 correlations of the three EW PORT series
Sharpe here = mean/std of daily log net returns x sqrt(252) (no risk-free rate); the dashboard IR (compounded return / volatility) differs slightly in level, not in ordering."""
import os, sys, pickle, warnings
warnings.filterwarnings("ignore")
os.environ.setdefault("RP_PRICES_DIR", "Prices_1029_merged")
sys.path[:0] = ["scripts/final_dashboard", "research", "research/configs", "scripts", "."]
import importlib
import numpy as np, pandas as pd
from engine import exec_shift, log_return_daily, momentum_composite_position, value_v1_position
from carry_zsum import carry_z, carry_slope_change, summed_signal
START, TC0, VALUE_MIN, SKEW_W = "2012-01-01", 5, 504, 252
PROD = {"Henry Hub": ("energy", "NatGas"), "TTF": ("emissions", "TTF"), "UK Gas": ("emissions", "UKGas")}
cfgs = {a: importlib.import_module(a) for a in ("energy", "emissions")}
DATA = {}
for name, (a, p) in PROD.items():
    cfg = cfgs[a]; DATA[name] = (cfg, cfg.load_curve(p), cfg.load_f1_series_logret(p), p)
STY = ("Momentum", "Carry", "CarryMom", "Value", "Skewness")


def sleeves(name, tc=TC0, carry_pairs=None, mom_pairs=None):
    cfg, curve, raw, p = DATA[name]
    lp, ph, f1r = raw["log_price"], raw["Phase"], raw["F1_raw"]
    pr = carry_pairs or cfg.carry_pairs(p)
    W, H = cfg.CARRY_ZSCORE_WINDOW, cfg.CARRY_MOMENTUM_HORIZON
    run = lambda pos: log_return_daily(pos, lp, tc, ph)[1]
    out = {"Momentum": run(momentum_composite_position(f1r, mom_pairs or cfg.MOMENTUM_PAIRS, shift_n=cfg.MOMENTUM_SHIFT_N)),
           "Carry": run(exec_shift(summed_signal([carry_z(curve, n, f, W) for n, f in pr], lp.index), cfg.CARRY_SHIFT_N).fillna(0)),
           "CarryMom": run(exec_shift(summed_signal([carry_slope_change(curve, n, f, H) for n, f in pr], lp.index), cfg.CARRY_MOMENTUM_SHIFT_N).fillna(0)),
           "Value": run(value_v1_position(curve, cfg.VALUE_CONTRACT, cfg.VALUE_LOOKBACK_DAYS, cfg.VALUE_THRESHOLD, shift_n=cfg.VALUE_SHIFT_N, min_periods=VALUE_MIN)),
           "Skewness": run(exec_shift(np.sign(-lp.diff().rolling(SKEW_W).skew()), 1).fillna(0))}
    return out


def ew(s):
    return sum(s[k].reindex(s["Momentum"].index).fillna(0) for k in STY) / len(STY)


sharpe = lambda x: float(x.mean() / x.std(ddof=1) * np.sqrt(252)) if len(x.dropna()) > 20 and x.std(ddof=1) > 0 else np.nan
lines = []
def out(s=""):
    print(s, flush=True); lines.append(s)

# baseline check against the pipeline's pickle
nets, _ = pickle.load(open("outputs/final_dashboard_1029/products_nets.pkl", "rb"))
base = {n: sleeves(n) for n in PROD}
worst = max(float((base[n][s].reindex(nets[PROD[n]][s].index).fillna(0) - nets[PROD[n]][s]).abs().max()) for n in PROD for s in STY)
out(f"Baseline reproduces products_nets.pkl: worst abs difference {worst:.1e}\n")
EW = {n: ew(base[n]).loc[START:] for n in PROD}

# common dates (cumsum-intersection, as everywhere in the repo)
def align(lst):
    cum = [x.cumsum() for x in lst]; idx = cum[0].index
    for c in cum[1:]:
        idx = idx.intersection(c.index)
    idx = idx.sort_values(); return [c.reindex(idx).diff().dropna() for c in cum]
al = align([EW[n] for n in PROD]); CM = dict(zip(PROD, al))
out(f"Common dates for paired tests: {len(al[0])} days, {al[0].index[0].date()} to {al[0].index[-1].date()}\n")

# 1 year by year
out("1. Sharpe by calendar year, equal-weight portfolio of the five sleeves")
yr = pd.DataFrame({n: CM[n].groupby(CM[n].index.year).apply(sharpe) for n in PROD}).round(2)
out(yr.to_string())
for n in ("TTF", "UK Gas"):
    k = int((yr[n] > yr["Henry Hub"]).sum()); out(f"   {n} beats Henry Hub in {k} of {len(yr)} years")
out()

# 2 paired block bootstrap
rng = np.random.default_rng(20261104)
def stat_boot(a, b, n_boot=4000, mean_block=20):
    T = len(a); x = a.values; y = b.values; p = 1.0 / mean_block
    d = np.empty(n_boot); sa = np.empty(n_boot); sb = np.empty(n_boot)
    for i in range(n_boot):
        idx = np.empty(T, dtype=int); t = 0
        while t < T:
            start = rng.integers(T); L = min(rng.geometric(p), T - t)
            idx[t:t + L] = (start + np.arange(L)) % T; t += L
        xa, xb = x[idx], y[idx]
        sa[i] = xa.mean() / xa.std(ddof=1) * np.sqrt(252); sb[i] = xb.mean() / xb.std(ddof=1) * np.sqrt(252); d[i] = sa[i] - sb[i]
    return d, sa, sb
out("2. Paired stationary block bootstrap (mean block 20 days, 4000 resamples), Sharpe of EW PORT")
hh = CM["Henry Hub"]
out(f"   Henry Hub Sharpe {sharpe(hh):.2f}")
for n in ("TTF", "UK Gas"):
    d, sa, sb = stat_boot(CM[n], hh)
    lo, hi = np.percentile(d, [2.5, 97.5]); p_ge = float((d <= 0).mean())
    se = sa.std(); out(f"   {n}: Sharpe {sharpe(CM[n]):.2f} (bootstrap 95% CI {np.percentile(sa,2.5):.2f} to {np.percentile(sa,97.5):.2f}); difference vs Henry Hub {sharpe(CM[n]) - sharpe(hh):+.2f}, 95% CI {lo:+.2f} to {hi:+.2f}, share of resamples with difference <= 0: {p_ge:.3f}")
out()

# 3 crisis exclusion
out("3. Excluding the 2021-07-01 to 2023-06-30 gas crisis (Sharpe of EW PORT on common dates)")
mask = ~((al[0].index >= "2021-07-01") & (al[0].index <= "2023-06-30"))
for n in PROD:
    out(f"   {n:10s} all dates {sharpe(CM[n]):5.2f} | without crisis {sharpe(CM[n][mask]):5.2f} | crisis only {sharpe(CM[n][~mask]):5.2f}")
out()

# 4 parameter variations (same change applied to all three products)
out("4. Parameter variations, Sharpe of EW PORT from 2012 (each product's own series, same settings for all three)")
VAR = [("baseline", {}),
       ("costs 10 bps", dict(tc=10)), ("costs 20 bps", dict(tc=20)),
       ("Carry F1-F2 only", dict(carry_pairs=[("F1", "F2")])), ("Carry F1-F3 only", dict(carry_pairs=[("F1", "F3")])),
       ("Carry F1-F2 + F1-F6", dict(carry_pairs=[("F1", "F2"), ("F1", "F6")])), ("Carry F1-F3 + F1-F13", dict(carry_pairs=[("F1", "F3"), ("F1", "F13")])),
       ("Momentum (5,60),(20,250)", dict(mom_pairs=((5, 60), (20, 250)))), ("Momentum (1,20) only", dict(mom_pairs=((1, 20),)))]
rows = []
for lab, kw in VAR:
    r = {"variant": lab}
    for n in PROD:
        r[n] = sharpe(ew(sleeves(n, **kw)).loc[START:])
    r["TTF>HH"] = r["TTF"] > r["Henry Hub"]; r["UK>HH"] = r["UK Gas"] > r["Henry Hub"]; rows.append(r)
vt = pd.DataFrame(rows).set_index("variant"); out(vt.round(2).to_string())
out(f"   TTF beats Henry Hub in {int(vt['TTF>HH'].sum())} of {len(vt)} variants; UK Gas in {int(vt['UK>HH'].sum())} of {len(vt)}\n")

# sleeve level, baseline
out("5. Sleeve Sharpe from 2012 (baseline)")
sl = pd.DataFrame({n: {s: sharpe(base[n][s].loc[START:]) for s in STY} for n in PROD}).round(2); out(sl.to_string())
out()
out("6. Correlation of daily EW PORT returns (common dates)")
out(pd.concat(CM, axis=1).corr().round(2).to_string())
open("Analysis/Gas_Products_Robustness.md", "w", encoding="utf8").write("```\n" + "\n".join(lines) + "\n```\n")
