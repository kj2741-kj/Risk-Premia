"""
network_momentum_research/table4_coefficient_significance.py
==============================================================
Replicates the paper's Table 4 (Section 5.4): standardized-feature OLS
coefficients with standard errors and p<0.05 significance marking, for
Panel A (LinReg / Eq.11, individual momentum on raw features) and Panel B
(GMOM / Eq.8, network momentum on graph-diffused features), across multiple
expanding in-sample windows.

Deliberately kept SEPARATE from network_momentum_paper_replication.py (the
main, already-validated walk-forward driver) rather than modifying it in
place -- this is new analysis code with its own new math (standard errors,
t-stats, p-values were never computed anywhere in this project before), and
isolating it means it cannot accidentally change anything about the already
-verified trading/backtest pipeline. It REUSES that module's panel loading,
feature caching and per-block alpha*/beta* choices (via the existing
checkpoints) rather than recomputing any of that -- refitting the regression
on an already-cached (start,end,step=1,alpha,beta) key is a fast cache hit,
not a new expensive graph-learning solve.

Key correctness point (verified below in `_self_test`, cross-checked against
statsmodels.OLS on synthetic data before this was ever run on real data):
OLS is invariant to affine reparametrisation of the predictors in terms of
FITTED VALUES -- standardizing X before fitting changes the COEFFICIENTS'
scale (now "effect of a 1-std-dev move in feature i") and lets them be
compared to each other, but does NOT change any predicted y-hat, and
therefore does NOT change the trading signal (sign(y-hat)) at all. This is
why this script is safe to treat as pure add-on reporting: it cannot,
even in principle, change what the main pipeline's backtests already found.

Windows used: the paper's own Table 4 uses 5 EXPANDING in-sample windows,
each starting at the same fixed date and growing (1990-1999 through
1990-2019). Our "annual" walk-forward variant is the closest analogue on
our compressed calendar -- also expanding from the same fixed TRAIN_START
(2017-10-09), just recalibrated every year instead of every ~5 years -- and
gives 6 windows instead of the paper's 5, a slightly richer analogue of the
same idea. (The "rolling" variant does NOT expand -- fixed-length sliding
window -- so it is not a valid analogue for an expanding-window coefficient-
stability table and is deliberately not used here.)

Coefficients only depend on (train_start, train_end, alpha*, beta*) -- NOT
on SHIFT_N (target_y is built from the fixed forward-1-day return regardless
of the module's execution-delay setting; shift_n only affects how a
PREDICTION is later scored against returns, not what the model is trained
to predict). So this only needs to run once (shift0's checkpoints), not
once per shift -- confirmed by inspecting load_panel()/target_y construction
in network_momentum_paper_replication.py before writing this script.
"""
from __future__ import annotations

import os

os.environ["WALKFORWARD_VARIANT"] = "annual"
os.environ["SHIFT_N"] = "0"

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats as sstats  # noqa: E402

from network_momentum_paper_replication import (  # noqa: E402
    BLOCKS, PRODUCTS, N_ASSETS, _CKPT_DIR_NAME, _THIS_DIR,
    compute_network_features_range, load_panel, _flat,
)

FEATURE_NAMES = [
    "vscaled_ret_1d", "vscaled_ret_21d", "vscaled_ret_63d", "vscaled_ret_126d", "vscaled_ret_252d",
    "macd_8_24", "macd_16_48", "macd_32_96",
]

_ANNUAL_SHIFT0_CKPT_DIR = os.path.join(_THIS_DIR, "outputs", "network_momentum_checkpoints_v3_annual_shift0")


# ═══════════════════════════════════════════════════════════════
# Standardized-OLS with standard errors / t-stats / p-values
# ═══════════════════════════════════════════════════════════════

def ols_with_inference(X: np.ndarray, y: np.ndarray, feature_names: list[str]) -> pd.DataFrame:
    """Standardizes X columns (subtract mean, divide by std -- paper's own
    stated preprocessing for Table 4), fits OLS with intercept, returns one
    row per feature (+ intercept) with coef/se/t/p. Uses the pseudo-inverse
    (not a plain inverse) for (X'X)^-1 so a near-singular design (the 8
    features are correlated by construction -- overlapping-horizon vol-scaled
    returns) can't crash this; NaN/inf rows are dropped first, same masking
    convention as fit_pooled_ols in the main module."""
    mask = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    Xm, ym = X[mask], y[mask]
    n = Xm.shape[0]

    mu = Xm.mean(axis=0)
    sd = Xm.std(axis=0, ddof=0)
    sd_safe = np.where(sd > 0, sd, 1.0)
    Xs = (Xm - mu) / sd_safe

    Xd = np.column_stack([Xs, np.ones(n)])
    k = Xd.shape[1]
    dof = n - k

    coef, *_ = np.linalg.lstsq(Xd, ym, rcond=None)
    resid = ym - Xd @ coef
    sigma2 = float(resid @ resid) / dof
    XtX_inv = np.linalg.pinv(Xd.T @ Xd)
    se = np.sqrt(np.clip(np.diag(sigma2 * XtX_inv), 0, None))
    with np.errstate(divide="ignore", invalid="ignore"):
        tstat = np.where(se > 0, coef / se, np.nan)
    pval = 2 * (1 - sstats.t.cdf(np.abs(tstat), df=dof))

    return pd.DataFrame(dict(
        feature=feature_names + ["intercept"], coef=coef, se=se, t=tstat, p=pval,
    )).assign(n=n, dof=dof)


def _self_test() -> None:
    """Cross-validates ols_with_inference against statsmodels.OLS on
    synthetic data with a KNOWN generating process, before this is ever
    trusted on real data -- per the explicit "make sure no errors" ask.
    Raises AssertionError (loud failure, not a silent print) if anything
    disagrees beyond float tolerance."""
    import statsmodels.api as sm

    rng = np.random.default_rng(42)
    n, p = 4000, 8
    true_beta = rng.normal(0, 1.5, size=p)
    true_intercept = 0.3
    X = rng.normal(0, 1, size=(n, p))
    # Correlate a couple of columns, matching the real features' overlapping-horizon
    # correlation structure -- also exercises the pinv path under near-collinearity.
    X[:, 1] = 0.8 * X[:, 0] + 0.2 * rng.normal(0, 1, size=n)
    noise = rng.normal(0, 2.0, size=n)
    y = X @ true_beta + true_intercept + noise

    # Inject some NaNs to test the masking path too.
    X_nan = X.copy()
    y_nan = y.copy()
    nan_rows = rng.choice(n, size=15, replace=False)
    X_nan[nan_rows[:8], 0] = np.nan
    y_nan[nan_rows[8:]] = np.nan

    ours = ols_with_inference(X_nan, y_nan, [f"x{i}" for i in range(p)])

    mask = np.isfinite(y_nan) & np.all(np.isfinite(X_nan), axis=1)
    Xm, ym = X_nan[mask], y_nan[mask]
    mu, sd = Xm.mean(axis=0), Xm.std(axis=0, ddof=0)
    Xs = (Xm - mu) / sd
    sm_model = sm.OLS(ym, sm.add_constant(Xs)).fit()

    sm_coef = np.concatenate([sm_model.params[1:], sm_model.params[:1]])  # reorder: features..., intercept
    sm_se = np.concatenate([sm_model.bse[1:], sm_model.bse[:1]])
    sm_p = np.concatenate([sm_model.pvalues[1:], sm_model.pvalues[:1]])

    assert np.allclose(ours["coef"].to_numpy(), sm_coef, atol=1e-8), "coef mismatch vs statsmodels"
    assert np.allclose(ours["se"].to_numpy(), sm_se, atol=1e-8), "SE mismatch vs statsmodels"
    assert np.allclose(ours["p"].to_numpy(), sm_p, atol=1e-6), "p-value mismatch vs statsmodels"
    assert int(ours["n"].iloc[0]) == mask.sum(), "n mismatch"
    assert int(ours["dof"].iloc[0]) == mask.sum() - (p + 1), "dof mismatch"

    # Also sanity-check the "coefficients don't affect fitted signs" invariance claim in the
    # module docstring: refit on RAW (unstandardized) X and confirm sign(y_hat) is identical.
    Xd_raw = np.column_stack([Xm, np.ones(len(Xm))])
    coef_raw, *_ = np.linalg.lstsq(Xd_raw, ym, rcond=None)
    yhat_raw = Xd_raw @ coef_raw
    Xd_std = np.column_stack([Xs, np.ones(len(Xm))])
    yhat_std = Xd_std @ ours["coef"].to_numpy()
    assert np.allclose(np.sign(yhat_raw), np.sign(yhat_std), atol=0), \
        "standardization changed predicted signs -- should be impossible for OLS"

    print("Self-test PASSED: matches statsmodels.OLS exactly (coef/SE/p), "
          "and standardization provably does not change predicted signs.")


# ═══════════════════════════════════════════════════════════════
# Real-data Table 4
# ═══════════════════════════════════════════════════════════════

def _block_indices(dates: pd.DatetimeIndex, train_start: str, train_end: str) -> tuple[int, int]:
    train_start_idx = int(dates.searchsorted(pd.Timestamp(train_start)))
    train_end_idx = int(dates.searchsorted(pd.Timestamp(train_end), side="right")) - 1
    return train_start_idx, train_end_idx


def build_table4(panel: dict, log=print) -> dict[str, pd.DataFrame]:
    dates = panel["dates"]
    U = panel["U"]
    target_y = panel["target_y"].to_numpy()

    panel_a_rows, panel_b_rows = [], []
    for i, (train_start, train_end, _test_start, _test_end) in enumerate(BLOCKS):
        ckpt_path = os.path.join(_ANNUAL_SHIFT0_CKPT_DIR, f"block_{i}.pkl")
        if not os.path.exists(ckpt_path):
            log(f"  block {i}: no checkpoint at {ckpt_path}, skipping")
            continue
        res = pd.read_pickle(ckpt_path)
        alpha_star, beta_star = res["alpha"], res["beta"]

        train_start_idx, train_end_idx = _block_indices(dates, train_start, train_end)
        y_train = target_y[train_start_idx:train_end_idx + 1].reshape(-1)
        period_label = f"{train_start}->{train_end}"

        # Panel A: LinReg on raw features (Eq.11) -- no graph, cheap.
        U_train_flat = _flat(U[train_start_idx:train_end_idx + 1])
        row_a = ols_with_inference(U_train_flat, y_train, FEATURE_NAMES)
        row_a.insert(0, "period", period_label)
        panel_a_rows.append(row_a)

        # Panel B: GMOM on network-diffused features (Eq.8) -- reuses the cached
        # graph computation from this exact block's own "final train-fit" step in
        # run_walk_forward_block (same start/end/step=1/alpha/beta cache key), so
        # this is a disk read, not a re-solve.
        train_feats = compute_network_features_range(U, train_start_idx, train_end_idx, alpha_star, beta_star,
                                                       step=1, log=log, label=f"block{i}-table4")
        X_train = _flat(train_feats)
        row_b = ols_with_inference(X_train, y_train, FEATURE_NAMES)
        row_b.insert(0, "period", period_label)
        row_b.insert(1, "alpha_star", alpha_star)
        row_b.insert(2, "beta_star", beta_star)
        panel_b_rows.append(row_b)

        log(f"  block {i} ({period_label}, alpha*={alpha_star} beta*={beta_star}): "
            f"n={int(row_a['n'].iloc[0])} obs, Panel A/B coefficients computed")

    panel_a = pd.concat(panel_a_rows, ignore_index=True)
    panel_b = pd.concat(panel_b_rows, ignore_index=True)
    return dict(panel_a_linreg=panel_a, panel_b_gmom=panel_b)


def _fmt_cell(coef: float, se: float, p: float) -> str:
    star = "*" if p < 0.05 else ""
    return f"{coef:.4f}{star} ({se:.4f})"


def print_table4(tables: dict[str, pd.DataFrame], log=print) -> None:
    for panel_name, df in (("Panel A: LinReg (individual momentum, Eq.11)", tables["panel_a_linreg"]),
                            ("Panel B: GMOM (network momentum, Eq.8)", tables["panel_b_gmom"])):
        log(f"\n=== {panel_name} ===")
        feats = [f for f in FEATURE_NAMES + ["intercept"]]
        periods = df["period"].unique().tolist()
        header = f"{'period':<24}" + "".join(f"{f:>18}" for f in feats)
        log(header)
        for period in periods:
            sub = df[df["period"] == period].set_index("feature")
            cells = "".join(f"{_fmt_cell(sub.loc[f,'coef'], sub.loc[f,'se'], sub.loc[f,'p']):>18}" for f in feats)
            log(f"{period:<24}{cells}")
        log("(* = p<0.05; entries are coef (SE) on standardized features)")


if __name__ == "__main__":
    print("Running self-test (cross-checked against statsmodels.OLS on synthetic data)...")
    _self_test()

    print("\nLoading panel (annual/shift0 checkpoints must already exist)...")
    panel = load_panel()
    print(f"Panel: {len(panel['dates'])} days, {panel['dates'][0].date()} -> {panel['dates'][-1].date()}")

    tables = build_table4(panel)
    print_table4(tables)

    out_dir = os.path.join(_THIS_DIR, "outputs")
    os.makedirs(out_dir, exist_ok=True)
    tables["panel_a_linreg"].to_csv(os.path.join(out_dir, "table4_panel_a_linreg.csv"), index=False)
    tables["panel_b_gmom"].to_csv(os.path.join(out_dir, "table4_panel_b_gmom.csv"), index=False)
    print(f"\nSaved: {os.path.join(out_dir, 'table4_panel_a_linreg.csv')}")
    print(f"Saved: {os.path.join(out_dir, 'table4_panel_b_gmom.csv')}")
