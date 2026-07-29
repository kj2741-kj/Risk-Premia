"""
network_momentum_research/regcombo_signcombo.py
==================================================
Paper's Section 4.3 diversification check: blend LinReg (individual
momentum, Eq.11) and GMOM (network momentum, Eq.8) into one combined
strategy, two ways:
  - RegCombo: average the two RAW regression outputs (predicted next-day
    vol-scaled return) BEFORE taking the sign -- x = sign((X_linreg+X_gmom)/2).
  - SignCombo: average the two SIGNS after each is taken independently --
    x = (sign(X_linreg)+sign(X_gmom))/2, so a value in {-1,-0.5,0,0.5,1}: a
    softer "vote" that only takes a full-size bet when both signals agree.

Full-22 universe, expanding/shift0 (matches the paper's own walk-forward
convention, same as everywhere else in this project's "headline" table).
Cheap: reuses the existing checkpointed alpha*/beta* and the FULL feature
cache (unlike the sub-class ablations, which had use_cache=False -- the
full-22 universe's cache is intact and was built during the original v3
run), so reconstructing X_linreg/X_gmom test signals is a cache hit, not a
new graph-learning solve.
"""
from __future__ import annotations

import os

os.environ.setdefault("WALKFORWARD_VARIANT", "expanding")
os.environ.setdefault("SHIFT_N", "0")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from network_momentum_paper_replication import (  # noqa: E402
    BLOCK_SCHEMES, N_ASSETS, TC_BPS, _THIS_DIR, _flat, compute_network_features_range,
    fit_pooled_ols, load_panel, macd_signal, portfolio_returns_with_tc, table1_metrics,
)

EXPANDING_BLOCKS = BLOCK_SCHEMES["expanding"]
_FULL_CKPT_DIR = os.path.join(_THIS_DIR, "outputs", "network_momentum_checkpoints_v3_expanding_shift0")
_KNOWN_SHARPE = dict(longonly=0.562, macd=0.276, linreg=0.898, gmom=0.773)


def _idx(dates: pd.DatetimeIndex, start: str, end: str) -> tuple[int, int]:
    start_idx = int(dates.searchsorted(pd.Timestamp(start)))
    end_idx = int(dates.searchsorted(pd.Timestamp(end), side="right")) - 1
    return start_idx, end_idx


def reconstruct_block_raw_signals(dates, U, target_y, block, alpha_star, beta_star, log=print, label=""):
    """Same as cost_sweep.py's block_test_signals, but ALSO returns the raw
    (pre-sign) X_linreg/X_gmom regression outputs, needed to build
    RegCombo (which blends before taking the sign)."""
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
    X_gmom_raw = np.stack([test_feats[k] @ gmom_beta + gmom_intercept for k in range(n_test)])
    X_linreg_raw = np.stack([U_test[k] @ linreg_beta + linreg_intercept for k in range(n_test)])

    return dict(
        test_start_idx=test_start_idx, n_test=n_test, test_dates=dates[test_start_idx:test_end_idx + 1],
        X_gmom_raw=X_gmom_raw, X_linreg_raw=X_linreg_raw,
        x_macd=np.stack([macd_signal(U_test[k]) for k in range(n_test)]),
        x_long=np.ones((n_test, N_ASSETS)),
    )


def score(x, fwd_ret, sigma_ann, is_roll_day, start_idx, n_test):
    r = portfolio_returns_with_tc(x, fwd_ret, sigma_ann, is_roll_day, start_idx, n_test, shift_n=0, tc_bps=TC_BPS)
    return r["returns"]


if __name__ == "__main__":
    print("Loading panel...")
    panel = load_panel()
    dates = panel["dates"]
    U = panel["U"]
    target_y = panel["target_y"].to_numpy()
    fwd_ret = panel["fwd_simple_ret"].to_numpy()
    sigma_ann = panel["sigma_annualized"].to_numpy()
    is_roll_day = panel["is_roll_day"]

    per_block = []
    for i, block in enumerate(EXPANDING_BLOCKS):
        ckpt = pd.read_pickle(os.path.join(_FULL_CKPT_DIR, f"block_{i}.pkl"))
        print(f"Block {i}: alpha*={ckpt['alpha']} beta*={ckpt['beta']}")
        sig = reconstruct_block_raw_signals(dates, U, target_y, block, ckpt["alpha"], ckpt["beta"], label=f"b{i}")
        per_block.append(sig)

    strategies = {name: [] for name in ("longonly", "macd", "linreg", "gmom", "regcombo", "signcombo")}
    for sig in per_block:
        x_linreg = np.sign(sig["X_linreg_raw"])
        x_gmom = np.sign(sig["X_gmom_raw"])
        x_regcombo = np.sign((sig["X_linreg_raw"] + sig["X_gmom_raw"]) / 2.0)
        x_signcombo = (x_linreg + x_gmom) / 2.0

        for name, x in (("longonly", sig["x_long"]), ("macd", sig["x_macd"]), ("linreg", x_linreg),
                         ("gmom", x_gmom), ("regcombo", x_regcombo), ("signcombo", x_signcombo)):
            r = score(x, fwd_ret, sigma_ann, is_roll_day, sig["test_start_idx"], sig["n_test"])
            strategies[name].append(pd.Series(r, index=sig["test_dates"]))

    combined = {name: pd.concat(parts).sort_index() for name, parts in strategies.items()}

    print("\nSelf-check: longonly/macd/linreg/gmom must reproduce known Sharpe numbers...")
    for name, expected in _KNOWN_SHARPE.items():
        got = table1_metrics(combined[name])["sharpe"]
        status = "OK" if abs(got - expected) < 5e-3 else "MISMATCH"
        print(f"  {name}: got={got:.4f} expected={expected:.4f}  [{status}]")
        assert abs(got - expected) < 5e-3, f"{name} Sharpe mismatch -- signal reconstruction bug"
    print("Self-check PASSED.")

    print(f"\n{'strategy':<12}{'ret':>9}{'vol':>8}{'sharpe':>9}{'mdd':>9}{'sortino':>9}")
    rows = []
    for name, series in combined.items():
        m = table1_metrics(series)
        rows.append(dict(strategy=name, **m))
        print(f"{name:<12}{m['ret']:>9.3f}{m['vol']:>8.3f}{m['sharpe']:>9.3f}{m['mdd']:>9.3f}{m['sortino']:>9.3f}")

    out_dir = os.path.join(_THIS_DIR, "outputs")
    pd.DataFrame(rows).to_csv(os.path.join(out_dir, "regcombo_signcombo_results.csv"), index=False)
    pd.DataFrame(combined).to_csv(os.path.join(out_dir, "regcombo_signcombo_returns.csv"))
    print(f"\nSaved: {os.path.join(out_dir, 'regcombo_signcombo_results.csv')}")
