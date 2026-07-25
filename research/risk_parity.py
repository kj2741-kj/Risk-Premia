"""
research/risk_parity.py
=========================
Equal Risk Contribution (ERC) portfolio weights.

Pure and stateless: given a covariance matrix, returns the weight vector
under which every constituent contributes equal risk to total portfolio
variance. No closed-form solution exists in general (only for the
uncorrelated or equal-correlation special cases), so this solves the
convex reformulation of Maillard, Roncalli & Teiletche (2010) / Spinu
(2013):

    minimize   0.5 * y' Sigma y - sum_i b_i * log(y_i)     subject to y > 0
    w = y / sum(y)

with equal risk budgets b_i = 1/N. The objective is convex (Sigma is
positive semi-definite by construction as a covariance matrix, and -log is
convex), so the solution is unique and reliably found by a general-purpose
convex solver -- no need for a bespoke iterative algorithm at the scale
this project needs (at most 4 constituents per portfolio).

References: Maillard, Roncalli & Teiletche, "The Properties of Equally
Weighted Risk Contribution Portfolios" (2010); Spinu, "An Algorithm for
Computing Risk Parity Weights" (2013); Roncalli, "Introduction to Risk
Parity and Budgeting" (2013).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

_Y_FLOOR = 1e-8  # numerical floor for the log-barrier term, not a portfolio constraint

DEFAULT_WINDOW = 252  # trailing trading days for the covariance estimate, matching the
                       # 252-day window already used elsewhere in this project (Carry's Z-score)
DEFAULT_REBALANCE_FREQ = 21  # roughly monthly (21 trading days)


def erc_weights(cov: np.ndarray) -> np.ndarray:
    """Equal Risk Contribution weights for the given covariance matrix.

    `cov` must be a square, positive semi-definite matrix (n_assets x
    n_assets). Returns a weight vector summing to 1, all entries
    non-negative. Verify a solve with risk_contributions(): the returned
    contributions should come out equal across all constituents.
    """
    cov = np.asarray(cov, dtype=float)
    n = cov.shape[0]
    if cov.ndim != 2 or cov.shape != (n, n):
        raise ValueError(f"cov must be a square matrix, got shape {cov.shape}")
    if n == 1:
        return np.array([1.0])

    budget = np.full(n, 1.0 / n)

    def objective(y):
        return 0.5 * y @ cov @ y - np.sum(budget * np.log(y))

    def objective_grad(y):
        return cov @ y - budget / y

    y0 = np.full(n, 1.0 / n)
    bounds = [(_Y_FLOOR, None)] * n
    result = minimize(objective, y0, jac=objective_grad, method="L-BFGS-B", bounds=bounds,
                       options={"maxiter": 2000, "ftol": 1e-16, "gtol": 1e-14})
    if not result.success:
        raise RuntimeError(f"ERC solver failed to converge: {result.message}")
    y = result.x
    return y / y.sum()


def risk_contributions(weights: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """Each constituent's actual contribution to total portfolio variance.

    For verifying an ERC solve: risk_contributions(erc_weights(cov), cov)
    should come out equal across all entries, within numerical tolerance.
    Contributions sum to the total portfolio variance w'Sigma w, not to 1.
    """
    weights = np.asarray(weights, dtype=float)
    cov = np.asarray(cov, dtype=float)
    marginal = cov @ weights
    return weights * marginal


def rolling_erc_combine(net_returns: dict[str, pd.Series], window: int = DEFAULT_WINDOW,
                         rebalance_freq: int = DEFAULT_REBALANCE_FREQ) -> tuple[pd.Series, pd.DataFrame]:
    """Combine several daily net return series using rolling Equal Risk Contribution weights.

    Weights are recomputed every `rebalance_freq` trading days, from the trailing `window` days
    of history STRICTLY BEFORE the rebalance date -- the covariance estimate at position i uses
    rows [i-window, i), never row i itself or anything later, so a weight decided for a given
    date cannot depend on anything not yet known on that date. Before the first full window of
    history is available, falls back to equal weight rather than leaving the portfolio
    undefined. Deliberately a single day of lag (decide using data through yesterday's close,
    apply from today), not the extra day exec_shift() adds elsewhere in this project for raw
    price signals -- these inputs are already fully lagged, tradeable position returns by the
    time they reach this function, so a second lag would be redundant, not extra safety.

    Returns (combined_return_series, weights_over_time_dataframe). The weights frame is not
    just a diagnostic -- it is what the no-look-ahead property is verified against (truncating
    the input after some date must leave every weight decided at or before that date unchanged).
    """
    names = list(net_returns.keys())
    n = len(names)
    if n == 0:
        return pd.Series(dtype=float), pd.DataFrame()
    df = pd.concat([net_returns[k] for k in names], axis=1, keys=names).dropna(how="any")
    if df.empty or n < 2:
        from engine import combine_returns  # local import: avoid a hard dependency for the n<2 fallback
        combined = combine_returns([net_returns[k] for k in names], "equal_weight")
        return combined, pd.DataFrame()

    dates = df.index
    weights_over_time = pd.DataFrame(index=dates, columns=names, dtype=float)
    current_weights = np.full(n, 1.0 / n)

    values = df.values
    for i in range(len(dates)):
        if i >= window and (i - window) % rebalance_freq == 0:
            trailing_cov = np.cov(values[i - window:i], rowvar=False)
            try:
                current_weights = erc_weights(trailing_cov)
            except RuntimeError:
                pass  # keep the previous weights if this period's solve fails to converge
        weights_over_time.iloc[i] = current_weights

    combined = pd.Series((values * weights_over_time.values).sum(axis=1), index=dates)
    return combined, weights_over_time
