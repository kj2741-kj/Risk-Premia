"""Standalone verification of research/drp.py, before any wiring into the
live engine: (1) ewma_vol/ewma_cov mutual consistency, (2) shrink_covariance
correctness, (3) inverse-vol weighting direction, (4) vol-target scaling
actually hits target_vol at rebalance dates, (5) no-lookahead (truncation
invariance), (6) runtime sanity at realistic scale."""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drp import (ewma_cov, ewma_vol, inverse_vol_weights, portfolio_vol,
                  rolling_drp_combine, shrink_covariance, vol_target_scale)

np.random.seed(42)
n = 2000
dates = pd.bdate_range("2015-01-01", periods=n)

# 3 synthetic series: A low-vol, B mid-vol, C high-vol, with real correlation
cov_true = np.array([[0.01**2, 0.3 * 0.01 * 0.02, 0.1 * 0.01 * 0.03],
                      [0.3 * 0.01 * 0.02, 0.02**2, 0.5 * 0.02 * 0.03],
                      [0.1 * 0.01 * 0.03, 0.5 * 0.02 * 0.03, 0.03**2]])
raw = np.random.multivariate_normal([0.0002, 0.0002, 0.0002], cov_true, size=n)
df = pd.DataFrame(raw, index=dates, columns=["A_low", "B_mid", "C_high"])

print("=== 1. ewma_vol vs ewma_cov diagonal consistency (same halflife) ===")
hl = 30
v = ewma_vol(df, halflife=hl)
c = ewma_cov(df, halflife=hl)
check_date = dates[500]
diag_from_cov = np.sqrt(np.diag(c.loc[check_date].reindex(index=df.columns, columns=df.columns).values))
diag_from_vol = v.loc[check_date].values
print("from ewma_vol:", diag_from_vol)
print("from ewma_cov diag:", diag_from_cov)
print("max abs diff:", np.max(np.abs(diag_from_vol - diag_from_cov)))
assert np.allclose(diag_from_vol, diag_from_cov, atol=1e-10), "MISMATCH"
print("PASS\n")

print("=== 2. shrink_covariance ===")
cov_i = c.loc[check_date].reindex(index=df.columns, columns=df.columns).values
shrunk_full = shrink_covariance(cov_i, alpha=0.0)
shrunk_diag = shrink_covariance(cov_i, alpha=1.0)
assert np.allclose(shrunk_full, cov_i), "alpha=0 should be a no-op"
assert np.allclose(shrunk_diag, np.diag(np.diag(cov_i))), "alpha=1 should be fully diagonal"
print("alpha=0 no-op: PASS, alpha=1 fully-diagonal: PASS\n")

print("=== 3. inverse_vol_weights direction ===")
vols = np.array([0.01, 0.02, 0.04])
w = inverse_vol_weights(vols)
print("vols:", vols, "-> raw weights:", w)
assert w[0] > w[1] > w[2], "lower vol should get higher raw weight"
print("PASS (lower vol -> higher weight)\n")

print("=== 4. vol_target_scale hits target ===")
target = 0.008
raw_w = inverse_vol_weights(v.loc[check_date].values)
shrunk = shrink_covariance(cov_i, alpha=0.5)
scaled = vol_target_scale(raw_w, shrunk, target)
realized = portfolio_vol(scaled, shrunk)
print(f"target_vol={target}, realized portfolio_vol(scaled weights)={realized:.6f}")
assert abs(realized - target) < 1e-9, "vol targeting failed to hit target exactly"
print("PASS\n")

print("=== 5. no-lookahead (truncation invariance) ===")
print("(using an EXPLICIT target_vol -- the default target_vol=None mode is")
print(" documented as intentionally full-sample-calibrated, not lookahead-safe)")
net_returns = {c_: df[c_] for c_ in df.columns}
FIXED_TARGET = 0.008
combined_full, weights_full = rolling_drp_combine(net_returns, vol_halflife=20, cov_halflife=60,
                                                    rebalance_freq=21, min_periods=240,
                                                    target_vol=FIXED_TARGET)
cutoff = dates[1500]
net_returns_trunc = {c_: df[c_].loc[:cutoff] for c_ in df.columns}
combined_trunc, weights_trunc = rolling_drp_combine(net_returns_trunc, vol_halflife=20, cov_halflife=60,
                                                      rebalance_freq=21, min_periods=240,
                                                      target_vol=FIXED_TARGET)
common_idx = weights_trunc.index[weights_trunc.index <= dates[1400]]  # well before cutoff
diff = (weights_full.loc[common_idx] - weights_trunc.loc[common_idx]).abs().max().max()
print(f"max abs weight diff on dates well before truncation: {diff}")
assert diff < 1e-10, "FAIL: truncating the future changed a past weight -- lookahead bug"
print("PASS (weights before the truncation point are unaffected by future data)\n")

print("=== 5b. confirm target_vol=None IS full-sample dependent (documented, expected) ===")
_, weights_full_default = rolling_drp_combine(net_returns, vol_halflife=20, cov_halflife=60,
                                                rebalance_freq=21, min_periods=240)
_, weights_trunc_default = rolling_drp_combine(net_returns_trunc, vol_halflife=20, cov_halflife=60,
                                                 rebalance_freq=21, min_periods=240)
diff_default = (weights_full_default.loc[common_idx] - weights_trunc_default.loc[common_idx]).abs().max().max()
print(f"max abs weight diff (default target_vol) on same early dates: {diff_default}")
assert diff_default > 1e-6, "expected the default full-sample target_vol to differ between full/truncated runs"
print("CONFIRMED: default mode is full-sample-calibrated as documented, not lookahead-safe\n")

print("=== 6. runtime sanity at realistic scale (8 series x 5200 days) ===")
n2 = 5200
dates2 = pd.bdate_range("2006-01-01", periods=n2)
raw2 = np.random.normal(0.0002, 0.015, size=(n2, 8))
df2 = pd.DataFrame(raw2, index=dates2, columns=[f"S{i}" for i in range(8)])
net_returns2 = {c_: df2[c_] for c_ in df2.columns}
t0 = time.time()
combined2, weights2 = rolling_drp_combine(net_returns2)
t1 = time.time()
print(f"8 series x {n2} days: {t1 - t0:.2f}s, combined series len={len(combined2)}, "
      f"weights shape={weights2.shape}")
assert t1 - t0 < 30, "unexpectedly slow"
print("PASS\n")

print("=== 7. equal-weight fallback before min_periods ===")
early_dates = weights_full.index[weights_full.index < dates[240]]
if len(early_dates) > 0:
    early_w = weights_full.loc[early_dates[-1]].values
    print("weights just before min_periods burn-in:", early_w)
    assert np.allclose(early_w, np.full(3, 1.0 / 3)), "should still be equal-weight fallback"
    print("PASS\n")

print("ALL CHECKS PASSED")
