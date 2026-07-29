"""
network_momentum_research/lookback_sensitivity.py
====================================================
Paper's Section 5.3: test each graph-learning lookback window
(delta in {252,504,756,1008,1260}) ALONE instead of the 5-window ensemble
Eq.5 uses everywhere else in this project. RIGOROUS version (user's
explicit choice 2026-07-28, not the cheaper disclosed-compromise
alternative that was offered): each (delta, block) pair gets its OWN
independent 121-combo alpha/beta grid search and regression refit -- NOT
reusing the ensemble's already-selected alpha*/beta*. Full-22 universe,
expanding/shift0 (matches the paper's own walk-forward convention, same
"headline" convention as everywhere else in this project).

Mirrors network_momentum_paper_replication.py's run_walk_forward_block
structure closely, but with a single-delta graph (`rolling_ensemble_graph`
generalized to accept a `deltas` override instead of always using the
module-level 5-tuple DELTAS constant) in place of the 5-window ensemble.
Kept as a separate script (not modifying the main module) for the same
reason as every other analysis script in this folder: isolates new code
from the already-validated pipeline.

Calibrated cost (measured 2026-07-28, single-delta N=22 solve): ~245ms
(delta=252) to ~340ms (delta=1260) per solve -- NOT the same as the ensemble
cost/5, timed directly rather than extrapolated. Own checkpoint dir per
(delta, block), grid-score checkpoint within each (same resilience pattern
as subclass_ablation.py), since this is a multi-hour run exposed to the
same external-kill risk documented elsewhere in this project's memory.
"""
from __future__ import annotations

import itertools
import json
import os
import time

os.environ.setdefault("WALKFORWARD_VARIANT", "expanding")
os.environ.setdefault("SHIFT_N", "0")

from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from kalofolias_graph_learning import learn_graph  # noqa: E402
from network_momentum_paper_replication import (  # noqa: E402
    ALPHA_BETA_GRID, GRID_SEARCH_STEP_DAYS, N_ASSETS, N_WORKERS, TC_BPS, _THIS_DIR, _flat,
    fit_pooled_ols, load_panel, macd_signal, portfolio_returns_with_tc, table1_metrics,
)
from network_momentum_paper_replication import BLOCK_SCHEMES  # noqa: E402

EXPANDING_BLOCKS = BLOCK_SCHEMES["expanding"]
LOOKBACK_DELTAS = (252, 504, 756, 1008, 1260)
_OUT_DIR = os.path.join(_THIS_DIR, "outputs", "network_momentum_lookback_sensitivity_v1")


def _idx(dates: pd.DatetimeIndex, start: str, end: str) -> tuple[int, int]:
    start_idx = int(dates.searchsorted(pd.Timestamp(start)))
    end_idx = int(dates.searchsorted(pd.Timestamp(end), side="right")) - 1
    return start_idx, end_idx


def _build_V_t(U: np.ndarray, t_idx: int, delta: int) -> np.ndarray:
    window = U[t_idx - delta + 1: t_idx + 1]
    return window.transpose(1, 0, 2).reshape(U.shape[1], -1)


def single_delta_graph(U: np.ndarray, t_idx: int, delta: int, alpha: float, beta: float,
                        warm_start: np.ndarray | None) -> tuple[np.ndarray, np.ndarray]:
    """Single-window analogue of rolling_ensemble_graph -- Eq.4-6 with K=1
    (no ensemble averaging across multiple deltas, just this one window's
    own graph, degree-normalized the same way)."""
    V_t = _build_V_t(U, t_idx, delta)
    A, w = learn_graph(V_t, alpha, beta, w_init=warm_start)
    d = A.sum(axis=1)
    with np.errstate(divide="ignore"):
        d_inv_sqrt = np.where(d > 0, 1.0 / np.sqrt(d), 0.0)
    A_norm = (A * d_inv_sqrt[:, None]) * d_inv_sqrt[None, :]
    return A_norm, w


def compute_single_delta_features(U: np.ndarray, delta: int, start_idx: int, end_idx: int, alpha: float,
                                   beta: float, step: int = 1, log=None, log_every: int = 100,
                                   label: str = "") -> np.ndarray:
    n_days = end_idx - start_idx + 1
    out = np.empty((n_days, U.shape[1], U.shape[2]))
    warm = None
    A_norm = None
    next_reestimate = start_idx
    t0 = time.time()
    for t_idx in range(start_idx, end_idx + 1):
        if t_idx >= next_reestimate or A_norm is None:
            A_norm, warm = single_delta_graph(U, t_idx, delta, alpha, beta, warm)
            next_reestimate = t_idx + step
        out[t_idx - start_idx] = A_norm @ U[t_idx]
        done = t_idx - start_idx + 1
        if log is not None and (done % log_every == 0 or done == n_days):
            log(f"    {label} {done}/{n_days} days ({time.time()-t0:.0f}s elapsed)")
    return out


_WORKER_CTX: dict = {}


def _init_grid_worker(U, delta, target_y, fwd_ret, sigma_ann, is_roll_day, train_start_idx, fit_end_idx,
                       val_start_idx, train_end_idx):
    global _WORKER_CTX
    _WORKER_CTX = dict(U=U, delta=delta, target_y=target_y, fwd_ret=fwd_ret, sigma_ann=sigma_ann,
                        is_roll_day=is_roll_day, train_start_idx=train_start_idx, fit_end_idx=fit_end_idx,
                        val_start_idx=val_start_idx, train_end_idx=train_end_idx)


def _score_combo(ab: tuple[float, float]) -> tuple[float, float, float]:
    alpha, beta = ab
    ctx = _WORKER_CTX
    feats = compute_single_delta_features(ctx["U"], ctx["delta"], ctx["train_start_idx"], ctx["train_end_idx"],
                                           alpha, beta, step=GRID_SEARCH_STEP_DAYS)
    fit_slice = slice(0, ctx["fit_end_idx"] - ctx["train_start_idx"] + 1)
    val_slice = slice(ctx["val_start_idx"] - ctx["train_start_idx"], ctx["train_end_idx"] - ctx["train_start_idx"] + 1)

    X_fit = _flat(feats[fit_slice])
    y_fit = ctx["target_y"][ctx["train_start_idx"]:ctx["fit_end_idx"] + 1].reshape(-1)
    beta_coef, intercept = fit_pooled_ols(X_fit, y_fit)

    val_feats = feats[val_slice]
    n_val = val_feats.shape[0]
    X_val = np.stack([val_feats[k] @ beta_coef + intercept for k in range(n_val)])
    x_val = np.sign(X_val)
    res = portfolio_returns_with_tc(x_val, ctx["fwd_ret"], ctx["sigma_ann"], ctx["is_roll_day"],
                                     ctx["val_start_idx"], n_val, shift_n=0, tc_bps=TC_BPS)
    m = table1_metrics(pd.Series(res["returns"]))
    score = m["sharpe"] if np.isfinite(m["sharpe"]) else -np.inf
    return alpha, beta, score


def run_single_delta_block(delta: int, block_idx: int, dates, U, target_y, fwd_ret, sigma_ann, is_roll_day,
                            train_start, train_end, test_start, test_end, log=print) -> dict:
    train_start_idx, train_end_idx = _idx(dates, train_start, train_end)
    test_start_idx, test_end_idx = _idx(dates, test_start, test_end)
    n_train = train_end_idx - train_start_idx + 1
    n_val = max(round(0.10 * n_train), 60)
    val_start_idx = train_end_idx - n_val + 1
    fit_end_idx = val_start_idx - 1

    log(f"[delta={delta}] Block {block_idx}: fit={dates[train_start_idx].date()}->{dates[fit_end_idx].date()} "
        f"valid={dates[val_start_idx].date()}->{dates[train_end_idx].date()} "
        f"test={dates[test_start_idx].date()}->{dates[test_end_idx].date()}")

    delta_dir = os.path.join(_OUT_DIR, f"delta_{delta}")
    os.makedirs(delta_dir, exist_ok=True)
    grid_ckpt_path = os.path.join(
        delta_dir, f"gridscore_{train_start_idx}_{fit_end_idx}_{val_start_idx}_{train_end_idx}_shift0_tc{TC_BPS}.json")
    scored: dict[str, float] = {}
    if os.path.exists(grid_ckpt_path):
        with open(grid_ckpt_path) as f:
            scored = json.load(f)
        log(f"  [delta={delta}] grid-score checkpoint: {len(scored)}/121 combos already scored, resuming")

    def _ab_key(a, b):
        return f"{a},{b}"

    combos = list(itertools.product(ALPHA_BETA_GRID, ALPHA_BETA_GRID))
    best_score, best_ab = -np.inf, (ALPHA_BETA_GRID[0], ALPHA_BETA_GRID[0])
    for alpha, beta in combos:
        k = _ab_key(alpha, beta)
        if k in scored and scored[k] > best_score:
            best_score, best_ab = scored[k], (alpha, beta)

    remaining = [(a, b) for a, b in combos if _ab_key(a, b) not in scored]
    t_grid0 = time.time()
    ctx_args = (U, delta, target_y, fwd_ret, sigma_ann, is_roll_day, train_start_idx, fit_end_idx,
                val_start_idx, train_end_idx)
    if remaining:
        log(f"  [delta={delta}] grid search: {len(remaining)}/{len(combos)} combos remaining, {N_WORKERS} workers...")
        with ProcessPoolExecutor(max_workers=N_WORKERS, initializer=_init_grid_worker, initargs=ctx_args) as ex:
            done = 0
            for alpha, beta, score in ex.map(_score_combo, remaining):
                done += 1
                scored[_ab_key(alpha, beta)] = score
                if score > best_score:
                    best_score, best_ab = score, (alpha, beta)
                if done % 20 == 0 or done == len(remaining):
                    tmp_path = grid_ckpt_path + f".tmp{os.getpid()}"
                    with open(tmp_path, "w") as f:
                        json.dump(scored, f)
                    os.replace(tmp_path, grid_ckpt_path)
                    log(f"  [delta={delta}] grid search {done}/{len(remaining)} done "
                        f"({time.time()-t_grid0:.0f}s elapsed, best alpha={best_ab[0]} beta={best_ab[1]} "
                        f"sharpe={best_score:.3f})")
    else:
        log(f"  [delta={delta}] grid search: all combos already scored, skipping")
    alpha_star, beta_star = best_ab
    log(f"  [delta={delta}] SELECTED alpha={alpha_star} beta={beta_star} (val Sharpe={best_score:.3f}, "
        f"{time.time()-t_grid0:.0f}s)")

    t_final0 = time.time()
    train_feats = compute_single_delta_features(U, delta, train_start_idx, train_end_idx, alpha_star, beta_star,
                                                 step=1, log=log, label=f"delta{delta}-b{block_idx}-train")
    X_train = _flat(train_feats)
    y_train = target_y[train_start_idx:train_end_idx + 1].reshape(-1)
    gmom_beta, gmom_intercept = fit_pooled_ols(X_train, y_train)

    test_feats = compute_single_delta_features(U, delta, test_start_idx, test_end_idx, alpha_star, beta_star,
                                                step=1, log=log, label=f"delta{delta}-b{block_idx}-test")
    log(f"  [delta={delta}] final train+test graph took {time.time()-t_final0:.0f}s")

    n_test = test_end_idx - test_start_idx + 1
    U_test = U[test_start_idx:test_end_idx + 1]
    X_gmom = np.stack([test_feats[k] @ gmom_beta + gmom_intercept for k in range(n_test)])
    x_gmom = np.sign(X_gmom)
    x_macd = np.stack([macd_signal(U_test[k]) for k in range(n_test)])
    x_long = np.ones((n_test, N_ASSETS))

    gmom_res = portfolio_returns_with_tc(x_gmom, fwd_ret, sigma_ann, is_roll_day, test_start_idx, n_test,
                                          shift_n=0, tc_bps=TC_BPS)
    macd_res = portfolio_returns_with_tc(x_macd, fwd_ret, sigma_ann, is_roll_day, test_start_idx, n_test,
                                          shift_n=0, tc_bps=TC_BPS)
    longonly_res = portfolio_returns_with_tc(x_long, fwd_ret, sigma_ann, is_roll_day, test_start_idx, n_test,
                                              shift_n=0, tc_bps=TC_BPS)

    test_dates = dates[test_start_idx:test_end_idx + 1]
    return dict(
        delta=delta, alpha=alpha_star, beta=beta_star, validation_sharpe=best_score,
        gmom_turnover=gmom_res["avg_turnover"],
        gmom=pd.Series(gmom_res["returns"], index=test_dates),
        macd=pd.Series(macd_res["returns"], index=test_dates),
        longonly=pd.Series(longonly_res["returns"], index=test_dates),
    )


def run_all_deltas(deltas: list[int] | None = None, log=print) -> dict[int, dict]:
    deltas = deltas or list(LOOKBACK_DELTAS)
    log("Loading panel...")
    panel = load_panel()
    dates = panel["dates"]
    U = panel["U"]
    target_y = panel["target_y"].to_numpy()
    fwd_ret = panel["fwd_simple_ret"].to_numpy()
    sigma_ann = panel["sigma_annualized"].to_numpy()
    is_roll_day = panel["is_roll_day"]

    all_results = {}
    for delta in deltas:
        log(f"\n########## delta={delta} ##########")
        delta_dir = os.path.join(_OUT_DIR, f"delta_{delta}")
        os.makedirs(delta_dir, exist_ok=True)
        block_results = []
        for i, (tr_start, tr_end, te_start, te_end) in enumerate(EXPANDING_BLOCKS):
            ckpt_path = os.path.join(delta_dir, f"block_{i}.pkl")
            if os.path.exists(ckpt_path):
                res = pd.read_pickle(ckpt_path)
                log(f"[delta={delta}] Block {i}: loaded from checkpoint (alpha*={res['alpha']} beta*={res['beta']})")
                block_results.append(res)
                continue
            res = run_single_delta_block(delta, i, dates, U, target_y, fwd_ret, sigma_ann, is_roll_day,
                                          tr_start, tr_end, te_start, te_end, log=log)
            pd.to_pickle(res, ckpt_path)
            block_results.append(res)

        combined = {name: pd.concat([r[name] for r in block_results]).sort_index() for name in ("gmom", "macd", "longonly")}
        metrics = {name: table1_metrics(combined[name]) for name in combined}
        all_results[delta] = dict(blocks=block_results, combined=combined, metrics=metrics)
        log(f"[delta={delta}] aggregated OOS Sharpe: longonly={metrics['longonly']['sharpe']:.3f}  "
            f"macd={metrics['macd']['sharpe']:.3f}  gmom={metrics['gmom']['sharpe']:.3f}  "
            f"turnover={np.mean([b['gmom_turnover'] for b in block_results]):.4f}")

    return all_results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--delta", type=int, default=None, choices=list(LOOKBACK_DELTAS))
    args = parser.parse_args()
    deltas = [args.delta] if args.delta else None
    print(f"N_WORKERS = {N_WORKERS}  TC_BPS = {TC_BPS}  shift_n=0  expanding blocks only  full-22 universe")
    run_all_deltas(deltas)
