"""Cross-check of our data and Skewness implementation against Fernandez-Perez, Fuertes and Miffre (2021), Tables 3 and 4 (2026-10-12).
The paper's single-style portfolios are CROSS-SECTIONAL: every month-end, standardise the signal across the energy contracts, long the positive and short the negative,
weights = z / sum|z| (gross 1, fully collateralised), held one month, gross of costs. We rebuild that for Term structure (TS), Momentum (Mom) and Skewness on OUR five
energy products (WTI, Brent, RBOB, Heating Oil, Natural Gas) from our continuous series, and compare with the paper's reported Sharpe ratios.
Signals (Table 1): TS = mean over the past year of ln F1 - ln F2; Mom = mean daily log return over the past year; Skewness = minus the third standardised moment of the
daily log returns over the past year. Differences from the paper that we cannot remove: its universe has up to ~10 contracts (ethanol, unleaded, electricity, coal, ...)
against our 5, Datastream against Bloomberg, its roll is the end of the month before maturity, and its sample is Jul 2001 - Mar 2019 (ours starts Jan 2006)."""
import sys
sys.path.insert(0, "research"); sys.path.insert(0, "research/configs"); sys.path.insert(0, "scripts")
import numpy as np
import pandas as pd
import energy

PRODUCTS = ["WTI", "Brent", "RBOB", "HeatingOil", "NatGas"]
ret, f1f2 = {}, {}
for p in PRODUCTS:
    raw = energy.load_f1_series_logret(p)
    ret[p] = raw["log_price"].diff()
    c = energy.load_curve(p)
    f1f2[p] = np.log(c["F1"].where(c["F1"] > 0)) - np.log(c["F2"].where(c["F2"] > 0))
R = pd.concat(ret, axis=1)
TS = pd.concat(f1f2, axis=1).reindex(R.index)
D = 252
sig = {
    "TS": TS.rolling(D, min_periods=D // 2).mean(),
    "Mom": R.rolling(D, min_periods=D // 2).mean(),
    "Skewness": -((R - R.rolling(D, min_periods=D // 2).mean()) ** 3).rolling(D, min_periods=D // 2).mean() / R.rolling(D, min_periods=D // 2).std(ddof=0) ** 3,
}
m_end = R.groupby(R.index.to_period("M")).tail(1).index
mret = R.groupby(R.index.to_period("M")).sum(min_count=1)
out = {}
for name, s in sig.items():
    sm = s.loc[m_end]; sm.index = sm.index.to_period("M")
    z = sm.sub(sm.mean(axis=1), axis=0).div(sm.std(axis=1, ddof=0), axis=0)
    w = z.div(z.abs().sum(axis=1), axis=0)
    out[name] = (w.shift(1) * mret).sum(axis=1, min_count=1).where(w.shift(1).notna().all(axis=1))
M = pd.DataFrame(out).dropna()
M.index = M.index.to_timestamp("M")
PAPER = {"TS": (0.0758, 0.5676), "Mom": (0.1328, 0.7524), "Skewness": (-0.0029, -0.0165)}   # (mean, Sharpe) July 2001 - Mar 2019; paper Table 3
PAPER_SUB = {"Dec-05 to Apr-10": ("2005-12", "2010-04", {"TS": 1.0838, "Mom": 0.9685, "Skewness": -0.5271}),
             "May-10 to Sep-14": ("2010-05", "2014-09", {"TS": 0.9793, "Mom": 0.7780, "Skewness": 0.2234}),
             "Oct-14 to Mar-19": ("2014-10", "2019-03", {"TS": 0.5995, "Mom": 0.1770, "Skewness": -0.6210})}
sh = lambda x: x.mean() * 12 / (x.std(ddof=1) * np.sqrt(12))
print(f"Our sample: {M.index.min().date()} to {M.index.max().date()} ({len(M)} months), 5 energy products\n")
print(f"{'Style':10}{'ours mean':>11}{'ours Sharpe':>13}{'paper mean':>12}{'paper Sharpe':>14}")
sub = M.loc[:"2019-03"]
for k in M:
    print(f"{k:10}{sub[k].mean()*12:>11.3f}{sh(sub[k]):>13.2f}{PAPER[k][0]:>12.3f}{PAPER[k][1]:>14.2f}")
print("\nSharpe by sub-period (ours / paper)")
print(f"{'':20}" + "".join(f"{k:>16}" for k in M))
for lab, (a, b, pp) in PAPER_SUB.items():
    s = M.loc[a:b]
    print(f"{lab:20}" + "".join(f"{sh(s[k]):>8.2f} /{pp[k]:>6.2f}" for k in M) + f"   (n={len(s)})")
print("\nCorrelation of monthly returns, ours (paper): Skewness vs TS, Skewness vs Mom, TS vs Mom")
print(f"{sub['Skewness'].corr(sub['TS']):.2f} (0.28)   {sub['Skewness'].corr(sub['Mom']):.2f} (0.13)   {sub['TS'].corr(sub['Mom']):.2f} (0.66)")
