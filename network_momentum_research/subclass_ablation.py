"""
network_momentum_research/subclass_ablation.py
=================================================
Sub-class ablation, our commodities-only analogue of the paper's Section 5.2
(GMOM-Intra vs GMOM-Inter vs full graph): restrict the universe to just ONE
of the 4 sub-asset-classes (Metals N=4, Precious N=5, Energy N=7, NGL N=6),
re-run the SAME expanding/shift0 walk-forward (3 blocks, matching the
paper's own walk-forward convention, TC_BPS=5) with its OWN independently
re-optimized graph (own 121-combo alpha/beta grid search, own regression
fit), and compare the resulting aggregated OOS Sharpe against the already-
known full-22-product result. Answers: does restricting network momentum to
edges WITHIN one sub-class change anything vs the full cross-class graph --
our data's answer to the paper's own "does the network structure matter, and
which edges are doing the work" question.

DELIBERATE DESIGN CHOICE -- use_cache=False everywhere (found via a Windows-
specific correctness check before writing this): the existing feature cache
(FEATURE_CACHE_DIR in the main module) keys purely on
(start_idx, end_idx, step, alpha, beta) -- NOT on which subset of assets was
used to build U. A different-universe call with the SAME date-index range
and (alpha,beta) would silently return the WRONG (full-22-asset) cached
array. A per-subclass cache-directory monkeypatch was considered and
rejected: ProcessPoolExecutor on Windows uses `spawn`, not `fork`, so each
worker process re-imports network_momentum_paper_replication fresh at
startup -- any parent-process monkeypatch of its FEATURE_CACHE_DIR global
would NOT propagate into the grid-search worker processes, silently putting
them right back onto the shared full-universe cache. Given this Windows
multiprocessing subtlety, `use_cache=False` (recompute every call, no
caching at all for this script) is the only provably-safe option -- accepted
because each sub-universe is much smaller (N=4-7 vs 22), making the
per-combo graph-learning solve considerably cheaper than the full run's.

Kept separate from network_momentum_paper_replication.py (same reasoning as
table4_coefficient_significance.py / cost_sweep.py): new code, isolated from
the already-validated main pipeline, cannot affect its results.
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import time

os.environ.setdefault("WALKFORWARD_VARIANT", "expanding")
os.environ.setdefault("SHIFT_N", "0")

from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from network_momentum_paper_replication import (  # noqa: E402
    ALPHA_BETA_GRID, CFG, GRID_SEARCH_STEP_DAYS, N_WORKERS, PRODUCTS, SIGMA_TGT,  # noqa: F401
    TC_BPS, _THIS_DIR, _flat, compute_network_features_range, fit_pooled_ols, load_panel,
    macd_signal, portfolio_returns_with_tc, table1_metrics,
)
from network_momentum_paper_replication import BLOCK_SCHEMES  # noqa: E402

EXPANDING_BLOCKS = BLOCK_SCHEMES["expanding"]  # 3 blocks, matches the paper's own walk-forward convention
SUBCLASSES = {name: list(cfg.PRODUCTS) for name, cfg in CFG.items()}  # metals/precious/energy/ngl

_ABLATION_DIR = os.path.join(_THIS_DIR, "outputs", "network_momentum_subclass_ablation_v1")

# Known full-22-product expanding/shift0 result (already-validated v3 final results table,
# 2026-07-27) -- the baseline every sub-class comparison is measured against.
_FULL_UNIVERSE_SHARPE = dict(longonly=0.562, macd=0.276, linreg=0.898, gmom=0.773)


def _idx(dates: pd.DatetimeIndex, start: str, end: str) -> tuple[int, int]:
    start_idx = int(dates.searchsorted(pd.Timestamp(start)))
    end_idx = int(dates.searchsorted(pd.Timestamp(end), side="right")) - 1
    return start_idx, end_idx


def _subset_indices(subclass: str) -> list[int]:
    members = set(SUBCLASSES[subclass])
    return [i for i, p in enumerate(PRODUCTS) if p in members]


_WORKER_CTX: dict = {}


def _init_grid_worker_sub(U, target_y, fwd_ret, sigma_ann, is_roll_day, train_start_idx, fit_end_idx,
                           val_start_idx, train_end_idx):
    global _WORKER_CTX
    _WORKER_CTX = dict(U=U, target_y=target_y, fwd_ret=fwd_ret, sigma_ann=sigma_ann, is_roll_day=is_roll_day,
                        train_start_idx=train_start_idx, fit_end_idx=fit_end_idx,
                        val_start_idx=val_start_idx, train_end_idx=train_end_idx)


def _score_combo_sub(ab: tuple[float, float]) -> tuple[float, float, float]:
    """Same scoring logic as the main module's _score_combo (net-of-cost
    validation Sharpe), but use_cache=False (see module docstring) and
    operating on whatever (smaller) U this worker pool was initialized with."""
    alpha, beta = ab
    ctx = _WORKER_CTX
    feats = compute_network_features_range(ctx["U"], ctx["train_start_idx"], ctx["train_end_idx"], alpha, beta,
                                            step=GRID_SEARCH_STEP_DAYS, use_cache=False)
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


def run_subclass_block(subclass: str, block_idx: int, dates: pd.DatetimeIndex, U_sub: np.ndarray,
                        target_y_sub: np.ndarray, fwd_ret_sub: np.ndarray, sigma_ann_sub: np.ndarray,
                        is_roll_day_sub: np.ndarray, train_start: str, train_end: str, test_start: str,
                        test_end: str, log=print) -> dict:
    """Same structure as the main module's run_walk_forward_block, generalized
    to an arbitrary (smaller) asset count n_assets = U_sub.shape[1] instead of
    the module-level N_ASSETS=22 constant, and use_cache=False throughout
    (see module docstring for why)."""
    n_assets = U_sub.shape[1]
    train_start_idx, train_end_idx = _idx(dates, train_start, train_end)
    test_start_idx, test_end_idx = _idx(dates, test_start, test_end)

    n_train = train_end_idx - train_start_idx + 1
    n_val = max(round(0.10 * n_train), 60)
    val_start_idx = train_end_idx - n_val + 1
    fit_end_idx = val_start_idx - 1

    log(f"[{subclass}] Block {block_idx}: n_assets={n_assets}  "
        f"fit={dates[train_start_idx].date()}->{dates[fit_end_idx].date()} ({fit_end_idx-train_start_idx+1}d)  "
        f"valid={dates[val_start_idx].date()}->{dates[train_end_idx].date()} ({n_val}d)  "
        f"test={dates[test_start_idx].date()}->{dates[test_end_idx].date()} ({test_end_idx-test_start_idx+1}d)")

    sub_dir = os.path.join(_ABLATION_DIR, subclass)
    os.makedirs(sub_dir, exist_ok=True)
    grid_ckpt_path = os.path.join(
        sub_dir, f"gridscore_{train_start_idx}_{fit_end_idx}_{val_start_idx}_{train_end_idx}_shift0_tc{TC_BPS}.json")
    scored: dict[str, float] = {}
    if os.path.exists(grid_ckpt_path):
        with open(grid_ckpt_path) as f:
            scored = json.load(f)
        log(f"  [{subclass}] grid-score checkpoint: {len(scored)}/121 combos already scored, resuming")

    def _ab_key(a, b):
        return f"{a},{b}"

    combos = list(itertools.product(ALPHA_BETA_GRID, ALPHA_BETA_GRID))
    best_score, best_ab = -np.inf, (ALPHA_BETA_GRID[0], ALPHA_BETA_GRID[0])
    full_grid = []
    for alpha, beta in combos:
        k = _ab_key(alpha, beta)
        if k in scored:
            score = scored[k]
            full_grid.append((alpha, beta, score))
            if score > best_score:
                best_score, best_ab = score, (alpha, beta)

    remaining = [(a, b) for a, b in combos if _ab_key(a, b) not in scored]
    t_grid0 = time.time()
    ctx_args = (U_sub, target_y_sub, fwd_ret_sub, sigma_ann_sub, is_roll_day_sub, train_start_idx, fit_end_idx,
                val_start_idx, train_end_idx)
    if remaining:
        log(f"  [{subclass}] grid search: {len(remaining)}/{len(combos)} combos remaining, "
            f"{N_WORKERS} workers, n_assets={n_assets}...")
        with ProcessPoolExecutor(max_workers=N_WORKERS, initializer=_init_grid_worker_sub, initargs=ctx_args) as ex:
            done = 0
            for alpha, beta, score in ex.map(_score_combo_sub, remaining):
                done += 1
                full_grid.append((alpha, beta, score))
                scored[_ab_key(alpha, beta)] = score
                if score > best_score:
                    best_score, best_ab = score, (alpha, beta)
                if done % 20 == 0 or done == len(remaining):
                    tmp_path = grid_ckpt_path + f".tmp{os.getpid()}"
                    with open(tmp_path, "w") as f:
                        json.dump(scored, f)
                    os.replace(tmp_path, grid_ckpt_path)
                    log(f"  [{subclass}] grid search {done}/{len(remaining)} done "
                        f"({time.time()-t_grid0:.0f}s elapsed, best so far alpha={best_ab[0]} beta={best_ab[1]} "
                        f"sharpe={best_score:.3f})")
    else:
        log(f"  [{subclass}] grid search: all {len(combos)} combos already scored, skipping")
    alpha_star, beta_star = best_ab
    log(f"  [{subclass}] SELECTED alpha={alpha_star} beta={beta_star} (val net Sharpe={best_score:.3f}, "
        f"{time.time()-t_grid0:.0f}s)")

    t_final0 = time.time()
    train_feats = compute_network_features_range(U_sub, train_start_idx, train_end_idx, alpha_star, beta_star,
                                                  step=1, log=log, label=f"[{subclass}] train-fit",
                                                  use_cache=False)
    X_train = _flat(train_feats)
    y_train = target_y_sub[train_start_idx:train_end_idx + 1].reshape(-1)
    gmom_beta, gmom_intercept = fit_pooled_ols(X_train, y_train)

    U_train_flat = _flat(U_sub[train_start_idx:train_end_idx + 1])
    linreg_beta, linreg_intercept = fit_pooled_ols(U_train_flat, y_train)

    test_feats = compute_network_features_range(U_sub, test_start_idx, test_end_idx, alpha_star, beta_star,
                                                 step=1, log=log, label=f"[{subclass}] test-period",
                                                 use_cache=False)
    log(f"  [{subclass}] final train+test graph took {time.time()-t_final0:.0f}s")

    n_test = test_end_idx - test_start_idx + 1
    U_test = U_sub[test_start_idx:test_end_idx + 1]
    X_gmom = np.stack([test_feats[k] @ gmom_beta + gmom_intercept for k in range(n_test)])
    X_linreg = np.stack([U_test[k] @ linreg_beta + linreg_intercept for k in range(n_test)])
    x_gmom = np.sign(X_gmom)
    x_linreg = np.sign(X_linreg)
    x_macd = np.stack([macd_signal(U_test[k]) for k in range(n_test)])
    x_long = np.ones((n_test, n_assets))

    gmom_res = portfolio_returns_with_tc(x_gmom, fwd_ret_sub, sigma_ann_sub, is_roll_day_sub, test_start_idx,
                                          n_test, shift_n=0, tc_bps=TC_BPS)
    linreg_res = portfolio_returns_with_tc(x_linreg, fwd_ret_sub, sigma_ann_sub, is_roll_day_sub, test_start_idx,
                                            n_test, shift_n=0, tc_bps=TC_BPS)
    macd_res = portfolio_returns_with_tc(x_macd, fwd_ret_sub, sigma_ann_sub, is_roll_day_sub, test_start_idx,
                                          n_test, shift_n=0, tc_bps=TC_BPS)
    longonly_res = portfolio_returns_with_tc(x_long, fwd_ret_sub, sigma_ann_sub, is_roll_day_sub, test_start_idx,
                                              n_test, shift_n=0, tc_bps=TC_BPS)

    test_dates = dates[test_start_idx:test_end_idx + 1]
    return dict(
        subclass=subclass, n_assets=n_assets, alpha=alpha_star, beta=beta_star, validation_sharpe=best_score,
        full_grid=full_grid,
        gmom=pd.Series(gmom_res["returns"], index=test_dates), linreg=pd.Series(linreg_res["returns"], index=test_dates),
        macd=pd.Series(macd_res["returns"], index=test_dates), longonly=pd.Series(longonly_res["returns"], index=test_dates),
    )


def run_all_ablations(subclasses: list[str] | None = None, log=print) -> dict[str, dict]:
    subclasses = subclasses or list(SUBCLASSES)
    log("Loading full 22-product panel...")
    panel = load_panel()
    dates = panel["dates"]
    U = panel["U"]
    target_y = panel["target_y"].to_numpy()
    fwd_ret = panel["fwd_simple_ret"].to_numpy()
    sigma_ann = panel["sigma_annualized"].to_numpy()
    is_roll_day = panel["is_roll_day"]
    log(f"Panel: {len(dates)} days, {dates[0].date()} -> {dates[-1].date()}")

    all_results = {}
    for subclass in subclasses:
        idx = _subset_indices(subclass)
        log(f"\n########## {subclass.upper()} (n={len(idx)}: {[PRODUCTS[i] for i in idx]}) ##########")
        U_sub = U[:, idx, :]
        target_y_sub = target_y[:, idx]
        fwd_ret_sub = fwd_ret[:, idx]
        sigma_ann_sub = sigma_ann[:, idx]
        is_roll_day_sub = is_roll_day[:, idx]

        sub_dir = os.path.join(_ABLATION_DIR, subclass)
        os.makedirs(sub_dir, exist_ok=True)
        block_results = []
        for i, (tr_start, tr_end, te_start, te_end) in enumerate(EXPANDING_BLOCKS):
            ckpt_path = os.path.join(sub_dir, f"block_{i}.pkl")
            if os.path.exists(ckpt_path):
                res = pd.read_pickle(ckpt_path)
                log(f"[{subclass}] Block {i}: loaded from checkpoint (alpha*={res['alpha']} beta*={res['beta']})")
                block_results.append(res)
                continue
            tb0 = time.time()
            res = run_subclass_block(subclass, i, dates, U_sub, target_y_sub, fwd_ret_sub, sigma_ann_sub,
                                      is_roll_day_sub, tr_start, tr_end, te_start, te_end, log=log)
            log(f"[{subclass}] Block {i} done in {time.time()-tb0:.0f}s")
            pd.to_pickle(res, ckpt_path)
            block_results.append(res)

        combined = {name: pd.concat([r[name] for r in block_results]).sort_index()
                    for name in ("gmom", "linreg", "macd", "longonly")}
        metrics = {name: table1_metrics(combined[name]) for name in combined}
        all_results[subclass] = dict(blocks=block_results, combined=combined, metrics=metrics)
        log(f"[{subclass}] aggregated OOS Sharpe: longonly={metrics['longonly']['sharpe']:.3f}  "
            f"macd={metrics['macd']['sharpe']:.3f}  linreg={metrics['linreg']['sharpe']:.3f}  "
            f"gmom={metrics['gmom']['sharpe']:.3f}")

    return all_results


def print_comparison(all_results: dict[str, dict], log=print) -> pd.DataFrame:
    rows = [dict(universe="full-22 (known)", n_assets=22, **_FULL_UNIVERSE_SHARPE)]
    for subclass, res in all_results.items():
        m = res["metrics"]
        rows.append(dict(universe=subclass, n_assets=res["blocks"][0]["n_assets"],
                          longonly=m["longonly"]["sharpe"], macd=m["macd"]["sharpe"],
                          linreg=m["linreg"]["sharpe"], gmom=m["gmom"]["sharpe"]))
    df = pd.DataFrame(rows)
    log(f"\n{'universe':<16}{'n':>4}{'longonly':>10}{'macd':>8}{'linreg':>8}{'gmom':>8}")
    for _, r in df.iterrows():
        log(f"{r['universe']:<16}{r['n_assets']:>4}{r['longonly']:>10.3f}{r['macd']:>8.3f}{r['linreg']:>8.3f}{r['gmom']:>8.3f}")
    return df


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--subclass", type=str, default=None, choices=list(SUBCLASSES),
                         help="run only this subclass (default: all 4 in sequence)")
    args = parser.parse_args()

    subclasses = [args.subclass] if args.subclass else None
    print(f"N_WORKERS = {N_WORKERS}  TC_BPS = {TC_BPS}  shift_n=0  expanding blocks only")
    all_results = run_all_ablations(subclasses)

    if not args.subclass or len(all_results) == len(SUBCLASSES):
        # only print/save the full comparison once every subclass has a checkpoint on disk
        have_all = all(
            os.path.exists(os.path.join(_ABLATION_DIR, sc, f"block_{i}.pkl"))
            for sc in SUBCLASSES for i in range(len(EXPANDING_BLOCKS))
        )
        if have_all:
            full_all_results = run_all_ablations(list(SUBCLASSES))  # cheap: all checkpoints already exist
            df = print_comparison(full_all_results)
            out_path = os.path.join(_THIS_DIR, "outputs", "subclass_ablation_comparison.csv")
            df.to_csv(out_path, index=False)
            print(f"\nSaved: {out_path}")
