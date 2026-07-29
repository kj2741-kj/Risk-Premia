"""
network_momentum_research/block_bootstrap.py
===============================================
Block bootstrap significance test for a strategy-vs-benchmark daily-return
DIFFERENCE, on autocorrelated daily return series (block size preserves
short-horizon autocorrelation/turnover-induced serial dependence that an
IID bootstrap would destroy). Same methodology used earlier in this project
for the main v3 walk-forward results (block=20 trading days, 5000
resamples) -- that test was run ad-hoc and never saved as a reusable module;
written here as one now since it's needed again for the NGL sub-class
ablation's suspiciously high Sharpe (5.08) and should exist as a checkable,
reusable piece of this project's infra rather than being re-derived from
scratch each time.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def block_bootstrap_mean_diff(a: pd.Series, b: pd.Series, block: int = 20, n_boot: int = 5000,
                               seed: int = 0) -> dict:
    """Tests whether mean(a - b) (daily) is distinguishable from zero, via a
    moving-block bootstrap on the (a-b) difference series. Returns the point
    estimate (in bps/day), a 95% CI, and a two-sided p-value (fraction of
    bootstrap resamples with the opposite sign from the point estimate, x2)."""
    diff = (a - b).dropna()
    diff = diff[np.isfinite(diff)]
    n = len(diff)
    point = float(diff.mean())

    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    starts_pool = np.arange(0, n - block + 1) if n > block else np.array([0])
    boot_means = np.empty(n_boot)
    vals = diff.to_numpy()
    for i in range(n_boot):
        starts = rng.choice(starts_pool, size=n_blocks, replace=True)
        sample = np.concatenate([vals[s:s + block] for s in starts])[:n]
        boot_means[i] = sample.mean()

    lo, hi = np.percentile(boot_means, [2.5, 97.5])
    if point >= 0:
        p = 2 * (boot_means < 0).mean()
    else:
        p = 2 * (boot_means > 0).mean()
    p = min(p, 1.0)

    return dict(n=n, point_bps=point * 1e4, ci_lo_bps=lo * 1e4, ci_hi_bps=hi * 1e4, p_value=float(p))
