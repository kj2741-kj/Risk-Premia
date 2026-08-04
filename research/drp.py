"""
research/drp.py
=================
Dynamic Risk Parity (DRP), per Mark Bogorad's "Risk Premia in Diversified
Energy Portfolios" (Dec 2025), Section 6.2.2-6.2.3: EWMA vol/covariance with
Ledoit-Wolf-style diagonal shrinkage, inverse-vol weighting, and a portfolio-
level volatility target with leverage.

DELIBERATELY a separate module from risk_parity.py, not a replacement for
it. risk_parity.py's rolling_erc_combine() solves for true Equal Risk
Contribution (every constituent contributes equal risk to total portfolio
variance, via a convex optimizer over the full covariance matrix) -- a
different, more general algorithm than what the paper specifies. DRP here
is a direct, literal implementation of the paper's own simpler recipe
(inverse-vol only, correlation used solely to measure resulting portfolio
vol for the leverage step, not to influence relative weights) so its
behavior can be compared against ERC and plain equal-weight side by side,
not silently blended with either.

Paper's formulas (Section 6.2.2, p.28-30):
    sigma_i,t^2 = (1-lambda_vol) * sum_{l=1}^inf lambda_vol^(l-1) * r_{i,t-l}^2,
        lambda_vol = 2^(-1/20)                                    (20-day half-life)
    Sigma_i,j,t = (1-lambda_cov) * sum_{l=1}^inf lambda_cov^(l-1) * r_{i,t-l} r_{j,t-l},
        lambda_cov = 2^(-1/60)                                    (60-day half-life)
    Sigma_bar_t = (1-alpha)*Sigma_t + alpha*diag(Sigma_t), alpha = 0.5
    omega_0,i,t = X_i,t / sigma_i,t              (inverse-vol raw weight)
    sigma_p,t = sqrt(omega_0,t' Sigma_bar_t omega_0,t)
    gamma_t = sigma_target / sigma_p,t
    omega_t = gamma_t * omega_0,t

Both EWMA recursions are written by the paper as sums over l=1..inf of
LAGGED returns (r_{t-l}, l>=1) -- i.e. the estimate at t uses no
information from day t itself, matching this project's no-lookahead
discipline elsewhere (rolling_erc_combine's own window is also strictly
prior data). Implemented here via pandas' .ewm(adjust=False) (which
reproduces the same recursive exponential-smoothing formula) applied to
the RETURNS SHIFTED BY ONE DAY, so the value stored for date t is exactly
the paper's sigma_t / Sigma_t, computed from r_{t-1}, r_{t-2}, ...

"Ledoit-Wolf" in the paper's own Section 6.2.2 is this fixed-alpha=0.5
diagonal blend, not the data-driven optimal-shrinkage-intensity estimator
from Ledoit & Wolf's original paper (which the paper also cites in its
references) -- replicated here as the paper actually specifies it, not the
more famous namesake estimator.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_VOL_HALFLIFE = 20   # trading days, Section 6.2.2
DEFAULT_COV_HALFLIFE = 60   # trading days, Section 6.2.2
DEFAULT_SHRINK_ALPHA = 0.5  # Section 6.2.2
DEFAULT_REBALANCE_FREQ = 21  # not specified numerically by the paper; matches
                              # risk_parity.py's rebalance cadence so EW/ERC/DRP
                              # are compared on the same rebalance schedule
_VOL_FLOOR = 1e-12  # numerical floor to avoid divide-by-zero on a near-dead series


def ewma_vol(returns: pd.DataFrame, halflife: int = DEFAULT_VOL_HALFLIFE) -> pd.DataFrame:
    """Per-column EWMA volatility, lagged by one day so the value at row t
    uses only r_{t-1}, r_{t-2}, ... (Section 6.2.2's sigma_i,t). Returns a
    DataFrame of the same shape/index/columns as `returns`; the first row
    is NaN (nothing to lag from) and early rows are noisy until the decay
    has had a chance to accumulate history -- callers should not treat
    rows before some burn-in as reliable (see rolling_drp_combine's
    `min_periods`)."""
    lagged_sq = returns.shift(1) ** 2
    var = lagged_sq.ewm(halflife=halflife, adjust=False, min_periods=1).mean()
    return np.sqrt(var)


def ewma_cov(returns: pd.DataFrame, halflife: int = DEFAULT_COV_HALFLIFE) -> pd.DataFrame:
    """EWMA covariance panel, lagged by one day (Section 6.2.2's Sigma_i,j,t).
    Returns a long-form DataFrame with a (date, column) MultiIndex, same
    shape as pandas' own `.ewm().cov()` output -- index a single date's
    covariance matrix via `.loc[date]`.

    Built from pairwise products run through `.ewm(adjust=False).mean()`
    directly (Sigma_i,j,t = EWMA of r_i,t-l * r_j,t-l), NOT pandas' own
    `.ewm().cov()` method: that method uses a different internal recursion
    (confirmed empirically -- even with bias=True and min_periods=1, its
    diagonal disagrees with ewma_vol()'s plain EWMA-of-squares by up to
    ~0.0012 on a 50-row toy series, traced to `.cov()` requiring 2
    observations before returning a nonzero value regardless of
    min_periods, which then propagates through the whole recursion since
    each step depends on the last). Computing every entry -- diagonal
    included -- via the same `.ewm().mean()` primitive as ewma_vol()
    guarantees exact mutual consistency (a diagonal entry here is
    identically ewma_vol(t)**2) by construction, and matches the paper's
    own formula, which is a plain weighted sum with no such correction."""
    lagged = returns.shift(1)
    cols = list(returns.columns)

    pairwise = {}
    for i, ci in enumerate(cols):
        for cj in cols[i:]:
            prod = lagged[ci] * lagged[cj]
            pairwise[(ci, cj)] = prod.ewm(halflife=halflife, adjust=False, min_periods=1).mean()

    frames = []
    for ci in cols:
        row = {cj: pairwise[(ci, cj) if (ci, cj) in pairwise else (cj, ci)] for cj in cols}
        block = pd.DataFrame(row, index=lagged.index)
        block.index = pd.MultiIndex.from_product([block.index, [ci]])
        frames.append(block)
    out = pd.concat(frames).sort_index(level=0)
    out.index.names = [None, None]
    return out[cols]


def shrink_covariance(cov: np.ndarray, alpha: float = DEFAULT_SHRINK_ALPHA) -> np.ndarray:
    """Sigma_bar = (1-alpha)*Sigma + alpha*diag(Sigma) -- pulls off-diagonal
    covariances toward zero without touching the diagonal (variances), per
    Section 6.2.2. alpha=0 is the raw covariance matrix unchanged; alpha=1
    is fully diagonal (a plain inverse-vol portfolio with zero assumed
    correlation)."""
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be in [0, 1], got {alpha}")
    cov = np.asarray(cov, dtype=float)
    diag_only = np.diag(np.diag(cov))
    return (1.0 - alpha) * cov + alpha * diag_only


def inverse_vol_weights(vols: np.ndarray) -> np.ndarray:
    """omega_0 = 1 / sigma, elementwise (Section 6.2.3) -- unnormalized,
    raw exposure assumed to be unit (+-1) per constituent, matching how
    every net-return series entering this module is already a fully
    signal-and-position-determined PnL stream (same convention
    rolling_erc_combine's inputs use)."""
    vols = np.asarray(vols, dtype=float)
    safe = np.where(vols > _VOL_FLOOR, vols, _VOL_FLOOR)
    return 1.0 / safe


def portfolio_vol(weights: np.ndarray, cov: np.ndarray) -> float:
    """sqrt(w' Sigma w) -- the realized portfolio vol implied by `weights`
    under `cov`. Used both internally (to size the leverage scalar) and as
    a standalone diagnostic: portfolio_vol(final_weights, shrunk_cov)
    should equal `target_vol` at every rebalance date, by construction."""
    weights = np.asarray(weights, dtype=float)
    cov = np.asarray(cov, dtype=float)
    variance = weights @ cov @ weights
    return float(np.sqrt(max(variance, 0.0)))


def vol_target_scale(raw_weights: np.ndarray, shrunk_cov: np.ndarray, target_vol: float) -> np.ndarray:
    """gamma_t = sigma_target / sigma_p,t; returns gamma_t * raw_weights
    (Section 6.2.3's final omega_t). If the raw-weight portfolio vol is
    ~zero (e.g. every constituent flat that period), returns raw_weights
    unscaled rather than dividing by ~zero."""
    sigma_p = portfolio_vol(raw_weights, shrunk_cov)
    if sigma_p <= _VOL_FLOOR:
        return raw_weights
    gamma = target_vol / sigma_p
    return gamma * raw_weights


def rolling_drp_combine(net_returns: dict[str, pd.Series],
                         vol_halflife: int = DEFAULT_VOL_HALFLIFE,
                         cov_halflife: int = DEFAULT_COV_HALFLIFE,
                         shrink_alpha: float = DEFAULT_SHRINK_ALPHA,
                         target_vol: float | None = None,
                         rebalance_freq: int = DEFAULT_REBALANCE_FREQ,
                         min_periods: int | None = None,
                         ) -> tuple[pd.Series, pd.DataFrame]:
    """Combine several daily net return series using rolling DRP weights.

    Mirrors risk_parity.py's rolling_erc_combine() contract exactly (same
    dict-in, (combined_series, weights_over_time)-out shape; same
    dropna(how="any")-then-intersect approach to aligning inputs to one
    common date index -- the same pre-existing path-dependent-drift caveat
    documented on rolling_erc_combine applies here too, unchanged by this
    module) so callers can swap "risk_parity" <-> "dynamic_risk_parity" as
    interchangeable combine_method values without touching anything else.

    Weights are recomputed every `rebalance_freq` trading days and held
    constant between rebalances, same cadence as ERC, even though the
    paper's own EWMA formulas are continuous (no fixed window) -- periodic
    rebalancing keeps EW/ERC/DRP comparisons on equal footing rather than
    DRP re-weighting every single day while ERC only re-weights monthly.

    `target_vol`: if None (default), calibrated ONCE from the trailing-
    complete plain equal-weight combination's own full-sample daily return
    std -- i.e. DRP is volatility-MATCHED to equal-weight over the whole
    sample, exactly the comparison the paper itself makes ("Volatility is
    matched... for equal comparison", Figure 8 caption). This default is
    NOT causally blind: it looks at the full sample once to pick a single
    scalar target, a deliberate experimental-design choice for a fair
    side-by-side comparison, not a claim that a live, non-lookahead
    strategy could know its own full-sample vol in advance. Pass an
    explicit `target_vol` (e.g. a fixed annual-vol-derived daily figure)
    for a genuinely lookahead-free live sizing rule.

    `min_periods`: minimum trailing days of history before the first
    rebalance is trusted; before this, and before the first rebalance
    passes it, falls back to equal weight (same "undefined portfolio is
    never returned" discipline as rolling_erc_combine). Defaults to
    4 * max(vol_halflife, cov_halflife) -- roughly the point at which EWMA
    decay has reduced the influence of the very first observations to
    under ~6% of a fresh one, a reasonable "the estimate has actually
    converged" threshold for a half-life-based (unbounded-lookback, no
    hard window) estimator.
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

    if min_periods is None:
        min_periods = 4 * max(vol_halflife, cov_halflife)

    if target_vol is None:
        target_vol = float(df.mean(axis=1).std())

    vol_frame = ewma_vol(df, halflife=vol_halflife)
    cov_panel = ewma_cov(df, halflife=cov_halflife)

    dates = df.index
    weights_over_time = pd.DataFrame(index=dates, columns=names, dtype=float)
    current_weights = np.full(n, 1.0 / n)

    values = df.values
    for i in range(len(dates)):
        if i >= min_periods and (i - min_periods) % rebalance_freq == 0:
            date_i = dates[i]
            vols_i = vol_frame.loc[date_i].values
            if np.all(np.isfinite(vols_i)) and np.all(vols_i > _VOL_FLOOR):
                cov_i = cov_panel.loc[date_i].reindex(index=names, columns=names).values
                shrunk = shrink_covariance(cov_i, shrink_alpha)
                raw = inverse_vol_weights(vols_i)
                current_weights = vol_target_scale(raw, shrunk, target_vol)
        weights_over_time.iloc[i] = current_weights

    combined = pd.Series((values * weights_over_time.values).sum(axis=1), index=dates)
    return combined, weights_over_time
