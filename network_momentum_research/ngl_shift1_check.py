"""
network_momentum_research/ngl_shift1_check.py
================================================
Robustness check on the sub-class ablation's one standout, statistically
significant result: NGL-only LinReg (Sharpe 5.08, block-bootstrap
p=0.0000 vs long-only under shift0). Every other headline result in this
project has been put through the shift0-vs-shift1 (one extra day of
execution delay) test, which has consistently been the toughest, most
revealing robustness check -- the full-22 LinReg/GMOM edge, which looked
strong under shift0, completely flipped negative under shift1. NGL was
never tested this way. This script does that, cheaply: NGL's alpha*/beta*
per block are already selected (from the sub-class ablation checkpoints)
and don't need re-selecting -- shift_n doesn't affect what the model is
FIT to predict (target_y is a fixed forward-1-day return, independent of
execution delay), only how a prediction gets scored against future returns
downstream. So this only needs to reconstruct NGL's 3 blocks' test signals
ONCE (single process, no parallel grid-search workers -- also means this
carries none of the Windows-spawn RAM-pressure risk that caused the
earlier ablation kills), then score portfolio_returns_with_tc at both
shift_n=0 (self-check: must reproduce the known 0.379/0.759/5.083/1.801
Sharpe numbers exactly) and shift_n=1 (the actual new question), plus a
block-bootstrap significance test on the shift1 result.
"""
from __future__ import annotations

import os

os.environ.setdefault("WALKFORWARD_VARIANT", "expanding")
os.environ.setdefault("SHIFT_N", "0")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from block_bootstrap import block_bootstrap_mean_diff  # noqa: E402
from network_momentum_paper_replication import (  # noqa: E402
    BLOCK_SCHEMES, CFG, PRODUCTS, TC_BPS, _THIS_DIR, _flat, compute_network_features_range,
    fit_pooled_ols, load_panel, macd_signal, portfolio_returns_with_tc, table1_metrics,
)

EXPANDING_BLOCKS = BLOCK_SCHEMES["expanding"]
_NGL_CKPT_DIR = os.path.join(_THIS_DIR, "outputs", "network_momentum_subclass_ablation_v1", "ngl")

_KNOWN_SHIFT0_SHARPE = dict(longonly=0.379, macd=0.759, linreg=5.083, gmom=1.801)


def _idx(dates: pd.DatetimeIndex, start: str, end: str) -> tuple[int, int]:
    start_idx = int(dates.searchsorted(pd.Timestamp(start)))
    end_idx = int(dates.searchsorted(pd.Timestamp(end), side="right")) - 1
    return start_idx, end_idx


def _subset_indices(subclass: str) -> list[int]:
    members = set(CFG[subclass].PRODUCTS)
    return [i for i, p in enumerate(PRODUCTS) if p in members]


def reconstruct_block_signals(dates, U_sub, target_y_sub, block, alpha_star, beta_star, log=print, label=""):
    train_start, train_end, test_start, test_end = block
    train_start_idx, train_end_idx = _idx(dates, train_start, train_end)
    test_start_idx, test_end_idx = _idx(dates, test_start, test_end)

    train_feats = compute_network_features_range(U_sub, train_start_idx, train_end_idx, alpha_star, beta_star,
                                                  step=1, log=log, label=f"{label}-train", use_cache=False)
    X_train = _flat(train_feats)
    y_train = target_y_sub[train_start_idx:train_end_idx + 1].reshape(-1)
    gmom_beta, gmom_intercept = fit_pooled_ols(X_train, y_train)

    U_train_flat = _flat(U_sub[train_start_idx:train_end_idx + 1])
    linreg_beta, linreg_intercept = fit_pooled_ols(U_train_flat, y_train)

    test_feats = compute_network_features_range(U_sub, test_start_idx, test_end_idx, alpha_star, beta_star,
                                                 step=1, log=log, label=f"{label}-test", use_cache=False)
    n_test = test_end_idx - test_start_idx + 1
    U_test = U_sub[test_start_idx:test_end_idx + 1]
    X_gmom = np.stack([test_feats[k] @ gmom_beta + gmom_intercept for k in range(n_test)])
    X_linreg = np.stack([U_test[k] @ linreg_beta + linreg_intercept for k in range(n_test)])

    return dict(
        test_start_idx=test_start_idx, n_test=n_test, test_dates=dates[test_start_idx:test_end_idx + 1],
        x_gmom=np.sign(X_gmom), x_linreg=np.sign(X_linreg),
        x_macd=np.stack([macd_signal(U_test[k]) for k in range(n_test)]),
        x_long=np.ones((n_test, U_sub.shape[1])),
    )


def score_all_blocks(dates, fwd_ret_sub, sigma_ann_sub, is_roll_day_sub, per_block_signals, shift_n: int) -> dict:
    combined = {name: [] for name in ("gmom", "linreg", "macd", "longonly")}
    for sig in per_block_signals:
        for name, x in (("gmom", sig["x_gmom"]), ("linreg", sig["x_linreg"]),
                         ("macd", sig["x_macd"]), ("longonly", sig["x_long"])):
            r = portfolio_returns_with_tc(x, fwd_ret_sub, sigma_ann_sub, is_roll_day_sub, sig["test_start_idx"],
                                           sig["n_test"], shift_n=shift_n, tc_bps=TC_BPS)
            combined[name].append(pd.Series(r["returns"], index=sig["test_dates"]))
    return {name: pd.concat(parts).sort_index() for name, parts in combined.items()}


if __name__ == "__main__":
    print("Loading panel...")
    panel = load_panel()
    dates = panel["dates"]
    U = panel["U"]
    target_y = panel["target_y"].to_numpy()
    fwd_ret = panel["fwd_simple_ret"].to_numpy()
    sigma_ann = panel["sigma_annualized"].to_numpy()
    is_roll_day = panel["is_roll_day"]

    idx = _subset_indices("ngl")
    print(f"NGL products: {[PRODUCTS[i] for i in idx]}")
    U_sub = U[:, idx, :]
    target_y_sub = target_y[:, idx]
    fwd_ret_sub = fwd_ret[:, idx]
    sigma_ann_sub = sigma_ann[:, idx]
    is_roll_day_sub = is_roll_day[:, idx]

    per_block_signals = []
    for i, block in enumerate(EXPANDING_BLOCKS):
        ckpt = pd.read_pickle(os.path.join(_NGL_CKPT_DIR, f"block_{i}.pkl"))
        print(f"Block {i}: alpha*={ckpt['alpha']} beta*={ckpt['beta']}")
        sig = reconstruct_block_signals(dates, U_sub, target_y_sub, block, ckpt["alpha"], ckpt["beta"],
                                         label=f"ngl-b{i}")
        per_block_signals.append(sig)
        print(f"  Block {i} signals reconstructed.")

    print("\nSelf-check: shift0 must reproduce known Sharpe numbers exactly...")
    shift0 = score_all_blocks(dates, fwd_ret_sub, sigma_ann_sub, is_roll_day_sub, per_block_signals, shift_n=0)
    for name, expected in _KNOWN_SHIFT0_SHARPE.items():
        got = table1_metrics(shift0[name])["sharpe"]
        status = "OK" if abs(got - expected) < 5e-3 else "MISMATCH"
        print(f"  {name}: got={got:.4f} expected={expected:.4f}  [{status}]")
        assert abs(got - expected) < 5e-3, f"{name} shift0 Sharpe mismatch -- signal reconstruction bug"
    print("Self-check PASSED.")

    print("\nScoring at shift_n=1 (one extra day of execution delay)...")
    shift1 = score_all_blocks(dates, fwd_ret_sub, sigma_ann_sub, is_roll_day_sub, per_block_signals, shift_n=1)
    print(f"\n{'strategy':<12}{'shift0 sharpe':>15}{'shift1 sharpe':>15}")
    for name in ("longonly", "macd", "linreg", "gmom"):
        s0 = table1_metrics(shift0[name])["sharpe"]
        s1 = table1_metrics(shift1[name])["sharpe"]
        print(f"{name:<12}{s0:>15.3f}{s1:>15.3f}")

    print("\nBlock bootstrap significance (shift1) -- linreg/gmom vs longonly:")
    for name in ("linreg", "gmom"):
        res = block_bootstrap_mean_diff(shift1[name], shift1["longonly"], block=20, n_boot=5000, seed=0)
        print(f"  {name} vs longonly (shift1): n={res['n']} point={res['point_bps']:.2f}bp/day "
              f"CI=[{res['ci_lo_bps']:.2f},{res['ci_hi_bps']:.2f}]bp/day p={res['p_value']:.4f}")

    out_dir = os.path.join(_THIS_DIR, "outputs")
    pd.DataFrame(shift1).to_csv(os.path.join(out_dir, "ngl_shift1_returns.csv"))
    print(f"\nSaved: {os.path.join(out_dir, 'ngl_shift1_returns.csv')}")
