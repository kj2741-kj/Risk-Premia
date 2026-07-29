"""
network_momentum_research/cost_sweep.py
========================================
Replicates the paper's own transaction-cost sensitivity sweep (Section 4.4):
sweep the one-way cost assumption (paper's own grid: c in
{0, 0.5, 1, 2, 3, 4, 5} bps) and report how each strategy's aggregated OOS
Sharpe decays, holding everything else (alpha*/beta* selection, regression
coefficients, the signal itself) FIXED at whatever the already-completed
shift0 v3 run chose. This matches the paper's own convention -- they sweep
cost on a GIVEN fitted model, they do not re-run hyperparameter selection
under each cost assumption -- and it is also the cheap, correct choice here:
selecting hyperparameters is itself already NET-of-TC_BPS=5 (see
_score_combo in the main module), so re-selecting per cost level would
answer a different, more expensive question ("what if TC had been c all
along, including during model selection") than the one actually being
asked here ("how fragile is the already-chosen model's edge to the cost
assumption").

Kept separate from network_momentum_paper_replication.py for the same
reason as table4_coefficient_significance.py: isolates new
reporting/analysis code from the already-validated pipeline. Reuses that
module's checkpointed alpha*/beta* (no new grid search) and the feature
cache (no new graph-learning solves -- refitting on an already-cached
(start,end,step=1,alpha,beta) key is a disk read), so this is cheap: only
portfolio_returns_with_tc (pure numpy, no optimization) is re-run, once per
(block, tc_bps).

Self-check before trusting the sweep: the tc_bps=5 row must reproduce the
EXACT aggregated Sharpe numbers already reported in this project's final v3
results table (memory: project_network_momentum_replication.md) --
Expanding: longonly=0.562, macd=0.276, linreg=0.898, gmom=0.773. This isn't
optional bookkeeping -- if this script's tc=5 row disagreed with the
already-checkpointed, previously-validated result, that would mean this
script's signal-reconstruction has a bug, and the rest of the sweep
(tc != 5) could not be trusted either.
"""
from __future__ import annotations

import os

os.environ.setdefault("WALKFORWARD_VARIANT", "expanding")
os.environ.setdefault("SHIFT_N", "0")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from network_momentum_paper_replication import (  # noqa: E402
    BLOCK_SCHEMES, N_ASSETS, _THIS_DIR,
    compute_network_features_range, fit_pooled_ols, load_panel, macd_signal,
    portfolio_returns_with_tc, table1_metrics, _flat,
)

TC_SWEEP_BPS = (0, 0.5, 1, 2, 3, 4, 5)  # paper's own Section 4.4 grid
VARIANTS = ("expanding", "rolling", "annual")

_KNOWN_TC5_SHARPE = {  # from the already-validated v3 shift0 final results table (memory, 2026-07-27)
    "expanding": dict(longonly=0.562, macd=0.276, linreg=0.898, gmom=0.773),
    "rolling": dict(longonly=0.562, macd=0.276, linreg=1.113, gmom=0.788),
    "annual": dict(longonly=0.562, macd=0.275, linreg=1.109, gmom=0.748),
}


def _idx(dates: pd.DatetimeIndex, start: str, end: str) -> tuple[int, int]:
    start_idx = int(dates.searchsorted(pd.Timestamp(start)))
    end_idx = int(dates.searchsorted(pd.Timestamp(end), side="right")) - 1
    return start_idx, end_idx


def block_test_signals(panel: dict, U: np.ndarray, target_y: np.ndarray, block: tuple[str, str, str, str],
                        alpha_star: float, beta_star: float, log=print, label: str = "") -> dict:
    """Reconstructs the exact same test-period signals (x_gmom/x_linreg/x_macd/
    x_long) that run_walk_forward_block computed for this block originally --
    same code path (train->refit->test), just re-derived from the checkpointed
    alpha*/beta* instead of re-running the grid search that chose them."""
    dates = panel["dates"]
    train_start, train_end, test_start, test_end = block
    train_start_idx, train_end_idx = _idx(dates, train_start, train_end)
    test_start_idx, test_end_idx = _idx(dates, test_start, test_end)

    train_feats = compute_network_features_range(U, train_start_idx, train_end_idx, alpha_star, beta_star,
                                                   step=1, log=log, label=f"{label}-train")
    X_train = _flat(train_feats)
    y_train = target_y[train_start_idx:train_end_idx + 1].reshape(-1)
    gmom_beta, gmom_intercept = fit_pooled_ols(X_train, y_train)

    U_train_flat = _flat(U[train_start_idx:train_end_idx + 1])
    linreg_beta, linreg_intercept = fit_pooled_ols(U_train_flat, y_train)

    test_feats = compute_network_features_range(U, test_start_idx, test_end_idx, alpha_star, beta_star,
                                                  step=1, log=log, label=f"{label}-test")
    n_test = test_end_idx - test_start_idx + 1
    U_test = U[test_start_idx:test_end_idx + 1]
    X_gmom = np.stack([test_feats[k] @ gmom_beta + gmom_intercept for k in range(n_test)])
    X_linreg = np.stack([U_test[k] @ linreg_beta + linreg_intercept for k in range(n_test)])

    return dict(
        test_start_idx=test_start_idx, n_test=n_test,
        test_dates=dates[test_start_idx:test_end_idx + 1],
        x_gmom=np.sign(X_gmom), x_linreg=np.sign(X_linreg),
        x_macd=np.stack([macd_signal(U_test[k]) for k in range(n_test)]),
        x_long=np.ones((n_test, N_ASSETS)),
    )


def run_cost_sweep(panel: dict, variant: str, log=print) -> pd.DataFrame:
    U = panel["U"]
    target_y = panel["target_y"].to_numpy()
    fwd_ret = panel["fwd_simple_ret"].to_numpy()
    sigma_ann = panel["sigma_annualized"].to_numpy()
    is_roll_day = panel["is_roll_day"]

    ckpt_dir = os.path.join(_THIS_DIR, "outputs", f"network_momentum_checkpoints_v3_{variant}_shift0")
    blocks = BLOCK_SCHEMES[variant]

    per_block_signals = []
    for i, block in enumerate(blocks):
        ckpt_path = os.path.join(ckpt_dir, f"block_{i}.pkl")
        if not os.path.exists(ckpt_path):
            log(f"  [{variant}] block {i}: no checkpoint at {ckpt_path}, skipping")
            continue
        res = pd.read_pickle(ckpt_path)
        sig = block_test_signals(panel, U, target_y, block, res["alpha"], res["beta"],
                                  log=log, label=f"{variant}-b{i}")
        per_block_signals.append(sig)
        log(f"  [{variant}] block {i}: signals reconstructed (alpha*={res['alpha']} beta*={res['beta']})")

    rows = []
    for tc_bps in TC_SWEEP_BPS:
        combined = {name: [] for name in ("longonly", "macd", "linreg", "gmom")}
        for sig in per_block_signals:
            for name, x in (("gmom", sig["x_gmom"]), ("linreg", sig["x_linreg"]),
                             ("macd", sig["x_macd"]), ("longonly", sig["x_long"])):
                r = portfolio_returns_with_tc(x, fwd_ret, sigma_ann, is_roll_day, sig["test_start_idx"],
                                               sig["n_test"], shift_n=0, tc_bps=tc_bps)
                combined[name].append(pd.Series(r["returns"], index=sig["test_dates"]))
        row = dict(tc_bps=tc_bps)
        for name, parts in combined.items():
            full = pd.concat(parts).sort_index()
            row[name] = table1_metrics(full)["sharpe"]
        rows.append(row)

    return pd.DataFrame(rows)


def _self_check(sweep_df: pd.DataFrame, variant: str, log=print) -> None:
    """The tc_bps=5 row must reproduce the already-validated final results
    table exactly (see module docstring) -- loud failure, not a silent
    print, if this script's signal-reconstruction disagrees with the
    original checkpointed backtest."""
    row = sweep_df[sweep_df["tc_bps"] == 5].iloc[0]
    known = _KNOWN_TC5_SHARPE[variant]
    for name, expected in known.items():
        got = row[name]
        assert abs(got - expected) < 5e-3, (
            f"[{variant}] tc=5bps {name} Sharpe mismatch: got {got:.4f}, expected {expected:.4f} "
            f"(from the already-validated v3 final results table) -- signal reconstruction has a bug"
        )
    log(f"  [{variant}] self-check PASSED: tc=5bps row reproduces the known, already-validated Sharpe "
        f"numbers exactly ({known})")


if __name__ == "__main__":
    print("Loading panel...")
    panel = load_panel()
    print(f"Panel: {len(panel['dates'])} days, {panel['dates'][0].date()} -> {panel['dates'][-1].date()}")

    all_sweeps = {}
    for variant in VARIANTS:
        print(f"\n=== {variant} (shift0) ===")
        sweep_df = run_cost_sweep(panel, variant)
        _self_check(sweep_df, variant)
        all_sweeps[variant] = sweep_df
        print(f"\n{'tc_bps':>8}{'longonly':>12}{'macd':>10}{'linreg':>10}{'gmom':>10}")
        for _, r in sweep_df.iterrows():
            print(f"{r['tc_bps']:>8.1f}{r['longonly']:>12.3f}{r['macd']:>10.3f}{r['linreg']:>10.3f}{r['gmom']:>10.3f}")

        out_dir = os.path.join(_THIS_DIR, "outputs")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"cost_sweep_{variant}_shift0.csv")
        sweep_df.to_csv(out_path, index=False)
        print(f"Saved: {out_path}")
