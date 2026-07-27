"""
network_momentum_research/network_momentum_paper_replication.py
=================================================
Full replication of Pu/Roberts/Dong/Zohren, "Network Momentum across Asset
Classes" (2023), adapted to this project's 22-product commodity-only
universe (Metals+Precious+Energy+NGL) in place of the paper's 64 futures
across 4 traditional asset classes. Every equation number below refers to
the paper (network_momentum_research/docs/Network momentum.pdf, verified page-by-page,
2026-07-25).

DATA CONSTRAINT DISCOVERED EMPIRICALLY (2026-07-25, confirmed with user):
the 8 momentum features (network_momentum_features.py) need their own
burn-in before being non-NaN (up to ~411 trading days for the slowest MACD
feature, then another 252 for EWM-winsorisation) -- the LATEST of the 22
products to clear this is NGL Propylene, on 2012-05-02. On TOP of that, the
graph-learning ensemble (Eq.5) needs delta CONSECUTIVE already-valid days of
history for its LARGEST lookback window (delta=1260, ~5yr) -- empirically
verified this pushes the first day the FULL 5-window ensemble is computable
to 2017-10-09. This is much later than the paper's own 1990-2000 setup
(they have 10+ years before their first test period; we only have ~7 years
before ours), so the walk-forward schedule below is compressed accordingly
(user's explicit decision, 2026-07-25): keep the paper's exact 5 lookback
windows (delta in {252,504,756,1008,1260}) rather than shrinking the model
spec, and shrink the CALENDAR instead.

WALK-FORWARD SCHEDULE (adapted, confirmed with user):
  Block 1: train 2017-10-09 -> 2020-12-31, test 2021-01-01 -> 2022-12-31
  Block 2: train 2017-10-09 -> 2022-12-31, test 2023-01-01 -> 2024-12-31
  Block 3: train 2017-10-09 -> 2024-12-31, test 2025-01-01 -> 2026-06-30
  (expanding training window, matching the paper's own walk-forward logic;
  last 10% of each training window held out as the validation slice for
  the alpha/beta grid search, exactly matching the paper's own "most
  recent 10% of training data" convention.)
  Aggregated OOS track record: 2021-01-01 -> 2026-06-30 (~5.5yr, 3 blocks) --
  proportionally scaled down from the paper's 22-year/5-block OOS period.

DISCLOSED COMPUTE COMPROMISE (not in the paper, needed for tractability --
flagged explicitly, not silently done): the paper's own Eq.4 graph is
re-estimated "on each trading day t" and its hyperparameter grid search
(11x11 = 121 discrete (alpha,beta) combos x 5 lookback windows) is run on
this daily-re-estimated graph over the validation slice. At this project's
scale that is still hundreds of thousands of individual convex-optimisation
solves. This module keeps DAILY graph re-estimation for everything that is
actually REPORTED (the final regression fit on the chosen hyperparameters,
and every test-period signal) -- but during the grid-search SCORING phase
only (ranking the 121 candidates against each other on the validation
slice), the graph is re-estimated at a MONTHLY (~21 trading day) cadence
instead of daily, purely to make the ranking tractable. This only affects
which (alpha,beta) gets selected, not the fidelity of the final backtest
built on top of that choice.
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import time

# Must be set before numpy's BLAS backend initialises (i.e. before `import numpy`
# below) so each of the N_WORKERS worker PROCESSES (see N_WORKERS/ProcessPoolExecutor
# below) doesn't ALSO spawn multiple BLAS threads internally -- oversubscribing an
# 8-core machine with e.g. 6 processes x 4 BLAS threads each would be slower than
# single-threaded-per-process, not faster. Our per-solve matrices (<=22x231) are
# tiny anyway, well below where multi-threaded BLAS would help.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
# This file lives in its own top-level network_momentum_research/ folder (moved 2026-07-27, separate git
# branch from the rest of the Risk Premia research), but still depends on the SHARED research/ infra
# (configs/*.py for data loading, ratio_continuous.py for the roll-adjusted continuous price -- both used
# by the other Momentum/Carry/Value/StatArb sleeves too, so they were deliberately NOT duplicated/moved
# here). _RESEARCH_DIR must be on sys.path (not just _CONFIGS_DIR) because configs/metals.py etc. themselves
# do `from ratio_continuous import ...`, which only resolves if research/ itself is already importable.
_RESEARCH_DIR = os.path.join(_THIS_DIR, "..", "research")
_CONFIGS_DIR = os.path.join(_RESEARCH_DIR, "configs")
for _p in (_CONFIGS_DIR, _RESEARCH_DIR, _THIS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import energy as energy_cfg  # noqa: E402
import metals as metals_cfg  # noqa: E402
import ngl as ngl_cfg  # noqa: E402
import precious as precious_cfg  # noqa: E402
from kalofolias_graph_learning import learn_graph  # noqa: E402
from network_momentum_features import MACD_PAIRS, compute_paper_momentum_features  # noqa: E402

CFG = {"metals": metals_cfg, "precious": precious_cfg, "energy": energy_cfg, "ngl": ngl_cfg}
UNIVERSE: list[tuple[str, str]] = [(asset, product) for asset, cfg in CFG.items() for product in cfg.PRODUCTS]
PRODUCTS: list[str] = [product for _, product in UNIVERSE]
N_ASSETS = len(PRODUCTS)  # 22

N_WORKERS = max(1, round(os.cpu_count() * 0.85))  # ~85% of cores (dialed back from 0.95 -- the 8/8-worker run got
# silently killed by something external after ~55min with zero cores left for the OS; reverting to leave 1 core free
# as a stability measure, since the earlier 7/8-worker chain ran fine for 135+ min). Parallelises the grid search's
# 121 independent combos.

DELTAS = (252, 504, 756, 1008, 1260)  # Eq.5's K=5 ensemble lookback windows
VOL_SPAN = 60  # Section 2.2's sigma_t EWMstd span
SIGMA_TGT = 0.15  # Eq.9's annualised target volatility

TC_BPS = 5  # round-trip transaction cost, same convention as engine.py's log_return_transaction_cost
            # (charged as tc_bps/10000/2 per unit of position CHANGE -- the /2 because tc_bps is a
            # round-trip rate and one directional change is half of a round trip -- plus an extra
            # half-rate charge on roll days where the position's sign is unchanged, since physically
            # rolling the futures contract is a real trade even when the strategy's stance doesn't move).
            # Was previously NOT applied anywhere in this module -- every prior Sharpe number in this
            # project's network-momentum results was gross-of-cost. Fixed 2026-07-26.

SHIFT_N = int(os.environ.get("SHIFT_N", "0"))  # extra days of execution delay AFTER the signal forms,
            # on top of the unavoidable 1-day minimum (signal uses data through day t's close, earliest
            # legal execution is day t+1). SHIFT_N=0 (the value used in every result before 2026-07-26)
            # is that fastest-legal minimum -- NOT literally "no delay", just no EXTRA delay beyond
            # what's unavoidable. This actually matches this project's OWN Momentum/Carry convention's
            # baseline (their shift_n=1 config value adds one FURTHER day on top of the same minimum,
            # via exec_shift's shift_n+1 formula) -- so SHIFT_N=1 here is the apples-to-apples match to
            # the rest of the project's more conservative execution-realism assumption, not a new idea.

ALPHA_BETA_GRID = (0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 10)  # paper's exact 11-point grid

# Walk-forward blocks: (train_start, train_end, test_start, test_end). ~10% of
# each held out at the END as the validation slice. Three schemes, selected via
# WALKFORWARD_VARIANT env var (mirrors the TRADEBOOK_ASSET_CLASS pattern in
# generate_tradebooks_logret.py):
#   "expanding" (default) -- train_start FIXED at the earliest tractable date,
#     train_end grows each block. This is the ORIGINAL scheme, matches the
#     paper's own walk-forward convention. Checkpoints/outputs unchanged
#     (no suffix), so existing Block 1/2/3 runs stay valid.
#   "rolling" -- SAME 3 test windows as "expanding", but train_start slides
#     forward so every block's training length equals Block 1's own length
#     (2017-10-09->2020-12-31, ~3.23yr) -- that length is forced by the data
#     (earliest date the delta=1260 feature ensemble is computable, see module
#     docstring), not cherry-picked, so it's a defensible fixed lookback.
#   "annual" -- SAME fixed expanding train_start as "expanding", but
#     recalibrates (grid search + regression refit) every calendar year
#     instead of every ~2 years, over the same 2021->2026-06 test span (6
#     blocks instead of 3) -- tests whether more frequent rebalancing changes
#     the result, still expanding.
TRAIN_START = "2017-10-09"

_EXPANDING_BLOCKS = [
    (TRAIN_START, "2020-12-31", "2021-01-01", "2022-12-31"),
    (TRAIN_START, "2022-12-31", "2023-01-01", "2024-12-31"),
    (TRAIN_START, "2024-12-31", "2025-01-01", "2026-06-30"),
]

_ROLLING_LOOKBACK = pd.Timestamp("2020-12-31") - pd.Timestamp(TRAIN_START)


def _rolling_block(train_end: str, test_start: str, test_end: str) -> tuple[str, str, str, str]:
    train_start = (pd.Timestamp(train_end) - _ROLLING_LOOKBACK).strftime("%Y-%m-%d")
    return (train_start, train_end, test_start, test_end)


_ROLLING_BLOCKS = [
    _rolling_block("2020-12-31", "2021-01-01", "2022-12-31"),
    _rolling_block("2022-12-31", "2023-01-01", "2024-12-31"),
    _rolling_block("2024-12-31", "2025-01-01", "2026-06-30"),
]

_ANNUAL_BLOCKS = [
    (TRAIN_START, "2020-12-31", "2021-01-01", "2021-12-31"),
    (TRAIN_START, "2021-12-31", "2022-01-01", "2022-12-31"),
    (TRAIN_START, "2022-12-31", "2023-01-01", "2023-12-31"),
    (TRAIN_START, "2023-12-31", "2024-01-01", "2024-12-31"),
    (TRAIN_START, "2024-12-31", "2025-01-01", "2025-12-31"),
    (TRAIN_START, "2025-12-31", "2026-01-01", "2026-06-30"),
]

BLOCK_SCHEMES = {"expanding": _EXPANDING_BLOCKS, "rolling": _ROLLING_BLOCKS, "annual": _ANNUAL_BLOCKS}

WALKFORWARD_VARIANT = os.environ.get("WALKFORWARD_VARIANT", "expanding")
if WALKFORWARD_VARIANT not in BLOCK_SCHEMES:
    raise ValueError(f"WALKFORWARD_VARIANT must be one of {list(BLOCK_SCHEMES)}, got {WALKFORWARD_VARIANT!r}")
BLOCKS = BLOCK_SCHEMES[WALKFORWARD_VARIANT]

GRID_SEARCH_STEP_DAYS = 21  # monthly-cadence graph re-estimation, GRID-SEARCH SCORING ONLY (see module docstring)


# ═══════════════════════════════════════════════════════════════
# Panel construction
# ═══════════════════════════════════════════════════════════════

def load_panel() -> dict:
    """Builds the common (all-22-products-valid) panel: 8-feature tensor U
    (T x N x 8), price and log_price matrices (T x N), aligned on the
    intersection of every product's own fully-valid-feature date range.
    Also carries each product's roll-`Phase` marker through (needed for the
    roll-day transaction-cost charge -- physically rolling a futures contract
    is a real trade even when a strategy's directional position doesn't
    change, same convention as engine.py's log_return_transaction_cost)."""
    prices, log_prices, feats, phases = {}, {}, {}, {}
    for asset, product in UNIVERSE:
        df = CFG[asset].load_f1_series_logret(product)
        prices[product] = df["F1_raw"]
        log_prices[product] = df["log_price"]
        phases[product] = df["Phase"]
        feats[product] = compute_paper_momentum_features(df["F1_raw"])

    common_idx = None
    for product in PRODUCTS:
        idx = feats[product].dropna().index
        common_idx = idx if common_idx is None else common_idx.intersection(idx)
    common_idx = common_idx.sort_values()

    U = np.stack([feats[p].reindex(common_idx).to_numpy() for p in PRODUCTS], axis=1)  # (T, N, 8)
    price_mat = pd.DataFrame({p: prices[p] for p in PRODUCTS}).reindex(common_idx)
    log_price_mat = pd.DataFrame({p: log_prices[p] for p in PRODUCTS}).reindex(common_idx)
    phase_mat = pd.DataFrame({p: phases[p] for p in PRODUCTS}).reindex(common_idx)
    is_roll_day = phase_mat.astype(str).apply(lambda c: c.str.startswith("Roll_LTD")).to_numpy()  # (T, N) bool

    # CRITICAL: daily_ret (feeds sigma/target_y/fwd_ret -- i.e. every Sharpe number and the vol-targeting
    # itself) must come from the ROLL-ADJUSTED continuous price (log_price_mat, already = log(F1_continuous_ratio),
    # never had this bug), NOT price_mat (F1_raw). F1_raw jumps on every roll day -- the price of the OLD
    # (expiring) contract vs. the NEW front-month contract are two different instruments, not one continuously
    # held position, so pct_change() on F1_raw would report a spurious mechanical "return" purely from the
    # contract switch. Confirmed empirically 2026-07-26: NatGas roll days showed up to 15.5% single-day
    # distortion this way (mean 0.52% across 247 roll days), WTI up to 4.75%, contaminating every prior Sharpe
    # number in this module. Using log_price_mat.diff() (a log return) rather than converting back to a simple
    # return -- matches this project's own established log-return-methodology convention (engine.py's
    # log_return_daily/log_return_metrics), negligible numerical difference from a simple return at daily
    # frequency, avoids an unneeded exp/log round-trip.
    daily_ret = log_price_mat.diff()
    sigma_daily = daily_ret.ewm(span=VOL_SPAN, min_periods=VOL_SPAN).std()  # Section 2.2 convention, NOT annualised
    sigma_annualized = sigma_daily * np.sqrt(252)  # Eq.9's sigma_i,t, paired with sigma_tgt=0.15 (annualised)
    fwd_simple_ret = daily_ret.shift(-1)  # r_{i,t:t+1}
    target_y = fwd_simple_ret / sigma_daily  # Section 2.2 "future 1-day volatility-scaled return"

    return dict(
        dates=common_idx, U=U, price=price_mat, log_price=log_price_mat,
        daily_ret=daily_ret, sigma_daily=sigma_daily, sigma_annualized=sigma_annualized,
        fwd_simple_ret=fwd_simple_ret, target_y=target_y, is_roll_day=is_roll_day,
    )


# ═══════════════════════════════════════════════════════════════
# Rolling graph ensemble (Eq.4-7)
# ═══════════════════════════════════════════════════════════════

def _build_V_t(U: np.ndarray, t_idx: int, delta: int) -> np.ndarray:
    """V_t (Section 3.1): stack the delta most recent days' 8-feature
    matrices, per asset, into one (N, 8*delta) row-per-asset matrix."""
    window = U[t_idx - delta + 1: t_idx + 1]  # (delta, N, 8)
    return window.transpose(1, 0, 2).reshape(U.shape[1], -1)  # (N, delta*8)


def rolling_ensemble_graph(U: np.ndarray, t_idx: int, alpha: float, beta: float,
                           warm_starts: dict[int, np.ndarray] | None) -> tuple[np.ndarray, dict[int, np.ndarray]]:
    """One day's Eq.5 ensemble + Eq.6 normalisation. `warm_starts` (per-delta
    condensed edge-weight vectors from the PREVIOUS call at this same
    (alpha,beta)) is optional but strongly recommended -- consecutive days'
    V_t differ by only one day's data, so warm-starting the FBF solver from
    yesterday's solution converges far faster than a cold zeros start."""
    if warm_starts is None:
        warm_starts = {}
    n = U.shape[1]
    A_sum = np.zeros((n, n))
    new_warm = {}
    for delta in DELTAS:
        V_t = _build_V_t(U, t_idx, delta)
        A_k, w_k = learn_graph(V_t, alpha, beta, w_init=warm_starts.get(delta))
        A_sum += A_k
        new_warm[delta] = w_k
    A_bar = A_sum / len(DELTAS)
    d_bar = A_bar.sum(axis=1)
    with np.errstate(divide="ignore"):
        d_inv_sqrt = np.where(d_bar > 0, 1.0 / np.sqrt(d_bar), 0.0)
    A_norm = (A_bar * d_inv_sqrt[:, None]) * d_inv_sqrt[None, :]  # Eq.6
    return A_norm, new_warm


def network_features(A_norm: np.ndarray, U_t: np.ndarray) -> np.ndarray:
    """Eq.7: u~_{i,t} = sum_j Abar_{ij,t} u_{j,t}, i.e. Abar @ U_t."""
    return A_norm @ U_t  # (N,8)


# Cache for the expensive part of compute_network_features_range (the actual graph-learning FBF
# optimization). Keyed ONLY on (start_idx, end_idx, step, alpha, beta) -- deliberately NOT on
# WALKFORWARD_VARIANT or SHIFT_N, because neither of those affects this computation at all: the graph
# only depends on U (the 8 raw-F1-based features, unaffected by the daily_ret/TC/shift fixes) and the
# day range/alpha/beta being asked for. Since `load_panel()` always builds the SAME full common-date
# panel regardless of variant, identical (start_idx,end_idx) pairs recur constantly across blocks
# (e.g. expanding Block 2 and annual Block 3 use IDENTICAL train dates -- confirmed 2026-07-26) and
# across shift0/shift1 (which only affects how the signal is later scored, not the graph itself). This
# cache turns most of those repeat computations into a disk read instead of a multi-minute FBF re-solve.
# _CACHE_VERSION bumped whenever upstream feature/graph logic changes, so a stale cache from before such
# a change can never be silently reused as if it were still valid.
_CACHE_VERSION = "v1"
FEATURE_CACHE_DIR = os.path.join(_THIS_DIR, "outputs", f"network_momentum_feature_cache_{_CACHE_VERSION}")


def _feature_cache_path(start_idx: int, end_idx: int, step: int, alpha: float, beta: float) -> str:
    os.makedirs(FEATURE_CACHE_DIR, exist_ok=True)
    return os.path.join(FEATURE_CACHE_DIR, f"feats_{start_idx}_{end_idx}_step{step}_a{alpha}_b{beta}.npy")


def compute_network_features_range(U: np.ndarray, start_idx: int, end_idx: int, alpha: float, beta: float,
                                    step: int = 1, log=None, log_every: int = 50, label: str = "",
                                    use_cache: bool = True) -> np.ndarray:
    """Network momentum features for every day in [start_idx, end_idx]
    (inclusive), re-estimating the graph every `step` trading days (step=1
    => literal daily re-estimation per Eq.4; step>1 holds the most-recently-
    estimated graph constant in between -- the disclosed grid-search-only
    compute compromise, see module docstring). Warm-starts the FBF solver
    across successive re-estimations. Returns (end_idx-start_idx+1, N, 8).

    `log`/`log_every`/`label`: optional progress heartbeat for the step=1
    daily-reestimation case, which previously ran fully silent for hundreds
    of days (this is what made Block 1's silent death undiagnosable -- no
    output between "SELECTED alpha/beta" and either a checkpoint or a
    crash). Only fires when `log` is passed; the grid-search's per-combo
    worker calls (step=GRID_SEARCH_STEP_DAYS) don't pass it, unaffected.

    `use_cache`: reads/writes FEATURE_CACHE_DIR (see module-level comment
    above) -- disabled only for tests/dry-runs that don't want to pollute
    the shared cache."""
    cache_path = _feature_cache_path(start_idx, end_idx, step, alpha, beta) if use_cache else None
    if cache_path is not None and os.path.exists(cache_path):
        if log is not None:
            log(f"    {label} loaded from feature cache ({cache_path})")
        return np.load(cache_path)

    n_days = end_idx - start_idx + 1
    out = np.empty((n_days, U.shape[1], U.shape[2]))
    warm = None
    A_norm = None
    next_reestimate = start_idx
    t0 = time.time()
    for t_idx in range(start_idx, end_idx + 1):
        if t_idx >= next_reestimate or A_norm is None:
            A_norm, warm = rolling_ensemble_graph(U, t_idx, alpha, beta, warm)
            next_reestimate = t_idx + step
        out[t_idx - start_idx] = network_features(A_norm, U[t_idx])
        done = t_idx - start_idx + 1
        if log is not None and (done % log_every == 0 or done == n_days):
            log(f"    {label} daily reestimation {done}/{n_days} days ({time.time()-t0:.0f}s elapsed)")

    if cache_path is not None:
        # tmp name must itself end in ".npy" -- np.save() silently APPENDS ".npy" to any name that
        # doesn't already end with it, which would otherwise make the os.replace() below target the
        # wrong (un-suffixed) filename and fail.
        tmp_path = os.path.join(FEATURE_CACHE_DIR, f".tmp_{os.getpid()}_{os.path.basename(cache_path)}")
        np.save(tmp_path, out)
        os.replace(tmp_path, cache_path)  # atomic -- safe even if two processes race on the same key
    return out


# ═══════════════════════════════════════════════════════════════
# Regression (Eq.8 GMOM / Eq.11 LinReg) + benchmark signals
# ═══════════════════════════════════════════════════════════════

def fit_pooled_ols(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    """Pooled panel OLS: y_it = X_it . beta + b. X is (M,8) stacked over all
    valid (asset,day) pairs, y is (M,). Returns (beta (8,), intercept b)."""
    mask = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    Xd = np.column_stack([X[mask], np.ones(mask.sum())])
    coef, *_ = np.linalg.lstsq(Xd, y[mask], rcond=None)
    return coef[:-1], float(coef[-1])


def macd_signal(U_t: np.ndarray) -> np.ndarray:
    """Eq.10: x_it = mean_k phi(y_it(S_k,L_k)) over the 3 MACD feature
    columns (already-winsorised, columns 5,6,7 of the 8-feature vector,
    see network_momentum_features.py's column order), phi(y)=y*exp(-y^2/4)/0.89."""
    macd_cols = U_t[:, 5:8]  # macd_8_24, macd_16_48, macd_32_96
    phi = macd_cols * np.exp(-macd_cols ** 2 / 4.0) / 0.89
    return phi.mean(axis=1)


def portfolio_returns_with_tc(X: np.ndarray, fwd_ret: np.ndarray, sigma_ann: np.ndarray, is_roll_day: np.ndarray,
                               start_idx: int, n_days: int, shift_n: int = None, tc_bps: int = TC_BPS) -> dict:
    """Net-of-cost daily portfolio return series (Eq.9 gross, minus per-asset
    transaction costs), vectorized over a whole [start_idx, start_idx+n_days)
    day range at once -- replaces the old scalar-per-day portfolio_return().

    `X` is (n_days, N) -- the raw signal for each day in that range (sign
    output for GMOM/LinReg, continuous phi-output for MACD, constant 1 for
    long-only). `fwd_ret`/`sigma_ann`/`is_roll_day` are the FULL-length (T,N)
    panel arrays. Execution happens `shift_n` days after the signal forms
    (module-level SHIFT_N default, or an explicit override for the
    sensitivity variant) -- day k's signal is applied against
    fwd_ret/sigma_ann/is_roll_day at row start_idx+k+shift_n. Rows that would
    run past the end of the loaded panel are set to NaN (at most `shift_n`
    days lost at the very tail of the very last block -- a disclosed minor
    edge effect, not a bug, and the output stays length-n_days either way so
    callers don't need special-case handling).

    Position sizing (Eq.9): scaled_position = X * (SIGMA_TGT/sigma_ann).
    Transaction cost: tc_bps/10000/2 per unit of day-to-day |scaled_position
    change| (first day of the range = change from flat), PLUS the same
    half-rate charge again on any day the position is held through a roll
    with unchanged sign -- identical convention to engine.py's
    log_return_transaction_cost, just applied to a vol-targeted notional
    instead of a +-1 unit position. This was NOT applied anywhere in this
    module before 2026-07-26 -- every prior result was gross-of-cost.

    Returns dict(returns=(n_days,) net portfolio return per day,
    avg_turnover=mean per-asset-day |scaled position change| (a standard
    turnover measure, answers "how much does this strategy actually trade"),
    one_way_frac=fraction of days where every valid asset got the same sign)."""
    if shift_n is None:
        shift_n = SHIFT_N
    T = fwd_ret.shape[0]
    exec_idx = np.arange(start_idx, start_idx + n_days) + shift_n
    in_bounds = exec_idx < T

    fr = np.full((n_days, X.shape[1]), np.nan)
    sa = np.full((n_days, X.shape[1]), np.nan)
    rd = np.zeros((n_days, X.shape[1]), dtype=bool)
    fr[in_bounds] = fwd_ret[exec_idx[in_bounds]]
    sa[in_bounds] = sigma_ann[exec_idx[in_bounds]]
    rd[in_bounds] = is_roll_day[exec_idx[in_bounds]]

    valid = np.isfinite(X) & np.isfinite(fr) & np.isfinite(sa) & (sa > 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        scaled = np.where(valid, X * (SIGMA_TGT / sa), 0.0)
    scaled = np.where(np.isfinite(scaled), scaled, 0.0)

    gross = scaled * np.where(np.isfinite(fr), fr, 0.0)

    prev = np.vstack([np.zeros((1, scaled.shape[1])), scaled[:-1]])
    chg = np.abs(scaled - prev)
    tc = chg * (tc_bps / 10000.0 / 2.0)

    cur_sign, prev_sign = np.sign(scaled), np.sign(prev)
    held_through_roll = rd & (scaled != 0) & (prev != 0) & (cur_sign == prev_sign)
    # FULL round-trip charge (tc_bps/10000), not a half-charge: on a held-through-roll day `chg` above is
    # ~0 (net exposure didn't change) so the base term contributes nothing, but a roll is physically TWO
    # trades -- sell the expiring contract, buy the new front-month, each its own one-way cost of
    # tc_bps/10000/2 -- so the total roll charge is 2x that, i.e. one full round-trip's worth. The earlier
    # tc_bps/10000/2 here charged only one of the two legs (same understatement as engine.py's
    # log_return_transaction_cost, which this was copied from -- not fixed there, flagged separately).
    tc = tc + held_through_roll.astype(float) * (tc_bps / 10000.0)

    net = np.where(valid, gross - tc, np.nan)
    n_valid_assets = valid.sum(axis=1)
    with np.errstate(invalid="ignore"):
        port_ret = np.where(n_valid_assets > 0, np.nansum(net, axis=1) / np.maximum(n_valid_assets, 1), np.nan)

    avg_turnover = float(chg[valid].mean()) if valid.any() else np.nan
    signs = np.where(valid, cur_sign, np.nan)
    one_way = [np.all(row[np.isfinite(row)] == row[np.isfinite(row)][0]) for row in signs if np.isfinite(row).any()]
    one_way_frac = float(np.mean(one_way)) if one_way else np.nan

    return dict(returns=port_ret, avg_turnover=avg_turnover, one_way_frac=one_way_frac)


# ═══════════════════════════════════════════════════════════════
# Table-1-style metrics
# ═══════════════════════════════════════════════════════════════

def table1_metrics(r: pd.Series) -> dict:
    a = r.dropna()
    if len(a) < 20 or a.std(ddof=1) == 0:
        return dict(ret=np.nan, vol=np.nan, sharpe=np.nan, downside_dev=np.nan, mdd=np.nan,
                    sortino=np.nan, calmar=np.nan, hit_rate=np.nan, avg_p_avg_l=np.nan)
    ret = float(a.mean() * 252)
    vol = float(a.std(ddof=1) * np.sqrt(252))
    downside = a[a < 0]
    downside_dev = float(downside.std(ddof=1) * np.sqrt(252)) if len(downside) > 1 else np.nan
    wealth = (1 + a).cumprod()
    mdd = float((wealth / wealth.cummax() - 1).min())
    hit_rate = float((a > 0).mean())
    avg_p = a[a > 0].mean()
    avg_l = a[a < 0].mean()
    return dict(
        ret=ret, vol=vol, sharpe=ret / vol if vol > 0 else np.nan,
        downside_dev=downside_dev, mdd=mdd,
        sortino=ret / downside_dev if downside_dev and downside_dev > 0 else np.nan,
        calmar=ret / abs(mdd) if mdd else np.nan,
        hit_rate=hit_rate, avg_p_avg_l=float(avg_p / abs(avg_l)) if avg_l else np.nan,
    )


def _flat(X3: np.ndarray) -> np.ndarray:
    """(days, N, 8) -> (days*N, 8), pooling every (asset,day) pair -- Eq.8/11's
    panel-regression convention ("estimated cross-sectionally...with in-sample
    data of all assets")."""
    return X3.reshape(-1, X3.shape[-1])


_WORKER_CTX: dict = {}


def _init_grid_worker(U, target_y, fwd_ret, sigma_ann, is_roll_day, train_start_idx, fit_end_idx, val_start_idx,
                       train_end_idx):
    """ProcessPoolExecutor initializer: each of the N_WORKERS worker processes
    receives the (small, <5MB) shared arrays ONCE at pool startup via initargs,
    not re-pickled per task."""
    global _WORKER_CTX
    _WORKER_CTX = dict(U=U, target_y=target_y, fwd_ret=fwd_ret, sigma_ann=sigma_ann, is_roll_day=is_roll_day,
                        train_start_idx=train_start_idx, fit_end_idx=fit_end_idx,
                        val_start_idx=val_start_idx, train_end_idx=train_end_idx)


def _score_combo(ab: tuple[float, float]) -> tuple[float, float, float]:
    """One (alpha,beta) candidate's validation-slice GMOM NET-of-cost Sharpe --
    the unit of work parallelised across N_WORKERS processes. Runs in a
    worker process, reading the shared context set up by _init_grid_worker.
    Scoring on NET (not gross) Sharpe as of 2026-07-26 -- selecting
    hyperparameters on a gross-of-cost criterion could favor a high-turnover
    (alpha,beta) that looks great before costs and mediocre after, which
    defeats the point of a deployable model; this makes selection consistent
    with what's actually reported."""
    alpha, beta = ab
    ctx = _WORKER_CTX
    feats = compute_network_features_range(ctx["U"], ctx["train_start_idx"], ctx["train_end_idx"], alpha, beta,
                                            step=GRID_SEARCH_STEP_DAYS)
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
                                     ctx["val_start_idx"], n_val)
    m = table1_metrics(pd.Series(res["returns"]))
    score = m["sharpe"] if np.isfinite(m["sharpe"]) else -np.inf
    return alpha, beta, score


def run_walk_forward_block(panel: dict, train_start: str, train_end: str, test_start: str, test_end: str,
                            grid: tuple[float, ...] = ALPHA_BETA_GRID, log=print) -> dict:
    dates = panel["dates"]
    U = panel["U"]
    target_y = panel["target_y"].to_numpy()
    fwd_ret = panel["fwd_simple_ret"].to_numpy()
    sigma_ann = panel["sigma_annualized"].to_numpy()
    is_roll_day = panel["is_roll_day"]

    train_start_idx = int(dates.searchsorted(pd.Timestamp(train_start)))
    train_end_idx = int(dates.searchsorted(pd.Timestamp(train_end), side="right")) - 1
    test_start_idx = int(dates.searchsorted(pd.Timestamp(test_start)))
    test_end_idx = int(dates.searchsorted(pd.Timestamp(test_end), side="right")) - 1

    n_train = train_end_idx - train_start_idx + 1
    n_val = max(round(0.10 * n_train), 60)
    val_start_idx = train_end_idx - n_val + 1
    fit_end_idx = val_start_idx - 1  # last day of the 90% fit-only portion

    log(f"Block: fit={dates[train_start_idx].date()}->{dates[fit_end_idx].date()} "
        f"({fit_end_idx-train_start_idx+1}d)  valid={dates[val_start_idx].date()}->{dates[train_end_idx].date()} "
        f"({n_val}d)  test={dates[test_start_idx].date()}->{dates[test_end_idx].date()} "
        f"({test_end_idx-test_start_idx+1}d)")

    # ---- Grid search: score every (alpha,beta) on the validation slice, in
    # parallel across N_WORKERS processes (~80% of cores) -- the 121 combos are
    # fully independent of each other. ----
    combos = list(itertools.product(grid, grid))
    best_score, best_ab = -np.inf, (grid[0], grid[0])

    # Grid-SCORE checkpoint (distinct from the feature cache above): the feature cache already made a
    # killed-mid-grid-search relaunch fast (each combo's underlying graph computation was individually
    # cached), but the run still had to resubmit and re-score EVERY combo from scratch, wasting the
    # already-scored ones' bookkeeping. This checkpoint persists (alpha,beta)->score as each combo
    # finishes, so a relaunch after another kill skips already-scored combos entirely, not just their
    # expensive inner computation. Keyed on the exact slice AND shift_n/tc_bps (unlike the feature cache,
    # the SCORE does depend on both -- portfolio_returns_with_tc inside _score_combo applies SHIFT_N/TC_BPS).
    grid_ckpt_path = os.path.join(
        FEATURE_CACHE_DIR, f"gridscore_{train_start_idx}_{fit_end_idx}_{val_start_idx}_{train_end_idx}"
        f"_shift{SHIFT_N}_tc{TC_BPS}.json")
    scored: dict[str, float] = {}
    if os.path.exists(grid_ckpt_path):
        with open(grid_ckpt_path) as f:
            scored = json.load(f)
        log(f"  grid-score checkpoint: {len(scored)}/{len(combos)} combos already scored, resuming")

    def _ab_key(a, b):
        return f"{a},{b}"

    full_grid = []  # every (alpha, beta, net_sharpe) -- not just the winner, so alpha/beta STABILITY across
                     # blocks can actually be analyzed later (was previously discarded, a real gap: the wild
                     # swings in which combo won block-to-block couldn't be investigated without this).
    for alpha, beta in combos:
        k = _ab_key(alpha, beta)
        if k in scored:
            score = scored[k]
            full_grid.append((alpha, beta, score))
            if score > best_score:
                best_score, best_ab = score, (alpha, beta)

    remaining = [(a, b) for a, b in combos if _ab_key(a, b) not in scored]
    t_grid0 = time.time()
    ctx_args = (U, target_y, fwd_ret, sigma_ann, is_roll_day, train_start_idx, fit_end_idx, val_start_idx,
                train_end_idx)
    if remaining:
        log(f"  grid search: {len(remaining)}/{len(combos)} combos remaining across {N_WORKERS} worker "
            f"processes (shift_n={SHIFT_N}, tc_bps={TC_BPS}, NET-of-cost selection)...")
        with ProcessPoolExecutor(max_workers=N_WORKERS, initializer=_init_grid_worker, initargs=ctx_args) as ex:
            done = 0
            for alpha, beta, score in ex.map(_score_combo, remaining):
                done += 1
                full_grid.append((alpha, beta, score))
                scored[_ab_key(alpha, beta)] = score
                if score > best_score:
                    best_score, best_ab = score, (alpha, beta)
                if done % 20 == 0 or done == len(remaining):
                    tmp_path = grid_ckpt_path + f".tmp{os.getpid()}"
                    with open(tmp_path, "w") as f:
                        json.dump(scored, f)
                    os.replace(tmp_path, grid_ckpt_path)  # atomic, safe against a kill mid-write
                    log(f"  grid search {done}/{len(remaining)} remaining combos done "
                        f"({len(full_grid)}/{len(combos)} total, {time.time()-t_grid0:.0f}s elapsed, "
                        f"best so far alpha={best_ab[0]} beta={best_ab[1]} sharpe={best_score:.3f})")
    else:
        log(f"  grid search: all {len(combos)} combos already scored (checkpoint), skipping compute entirely")
    alpha_star, beta_star = best_ab
    log(f"  SELECTED alpha={alpha_star} beta={beta_star}  (validation net Sharpe={best_score:.3f}, "
        f"grid search took {time.time()-t_grid0:.0f}s)")

    # ---- Refit regression on the FULL training window (100%, per paper's "all
    # preprocessed data up to the point of recalibration"), daily re-estimation ----
    t_final0 = time.time()
    train_feats = compute_network_features_range(U, train_start_idx, train_end_idx, alpha_star, beta_star, step=1,
                                                  log=log, label="train-fit")
    X_train, y_train = _flat(train_feats), target_y[train_start_idx:train_end_idx + 1].reshape(-1)
    gmom_beta, gmom_intercept = fit_pooled_ols(X_train, y_train)

    U_train_flat = _flat(U[train_start_idx:train_end_idx + 1])
    linreg_beta, linreg_intercept = fit_pooled_ols(U_train_flat, y_train)

    # ---- Test period: daily re-estimation, all 4 strategies ----
    test_feats = compute_network_features_range(U, test_start_idx, test_end_idx, alpha_star, beta_star, step=1,
                                                 log=log, label="test-period")
    log(f"  final train-fit graph + test-period graph took {time.time()-t_final0:.0f}s")

    n_test = test_end_idx - test_start_idx + 1
    U_test = U[test_start_idx:test_end_idx + 1]
    X_gmom = np.stack([test_feats[k] @ gmom_beta + gmom_intercept for k in range(n_test)])
    X_linreg = np.stack([U_test[k] @ linreg_beta + linreg_intercept for k in range(n_test)])
    x_gmom = np.sign(X_gmom)
    x_linreg = np.sign(X_linreg)
    x_macd = np.stack([macd_signal(U_test[k]) for k in range(n_test)])
    x_long = np.ones((n_test, N_ASSETS))

    gmom_res = portfolio_returns_with_tc(x_gmom, fwd_ret, sigma_ann, is_roll_day, test_start_idx, n_test)
    linreg_res = portfolio_returns_with_tc(x_linreg, fwd_ret, sigma_ann, is_roll_day, test_start_idx, n_test)
    macd_res = portfolio_returns_with_tc(x_macd, fwd_ret, sigma_ann, is_roll_day, test_start_idx, n_test)
    longonly_res = portfolio_returns_with_tc(x_long, fwd_ret, sigma_ann, is_roll_day, test_start_idx, n_test)

    log(f"  diagnostic: GMOM was a fully one-way (same sign every asset) bet on "
        f"{gmom_res['one_way_frac']:.1%} of test days; LinReg on {linreg_res['one_way_frac']:.1%} "
        f"(high fractions here mean the cross-sectional signal degenerated toward a "
        f"single market-wide bet, i.e. converges toward Long/Short Only rather than a genuine "
        f"asset-by-asset momentum signal)")
    log(f"  turnover (mean daily |position change| per asset): GMOM={gmom_res['avg_turnover']:.4f}  "
        f"LinReg={linreg_res['avg_turnover']:.4f}  MACD={macd_res['avg_turnover']:.4f}  "
        f"LongOnly={longonly_res['avg_turnover']:.4f}")

    test_dates = dates[test_start_idx:test_end_idx + 1]
    return dict(
        alpha=alpha_star, beta=beta_star, validation_sharpe=best_score, full_grid=full_grid,
        shift_n=SHIFT_N, tc_bps=TC_BPS,
        gmom_one_way_frac=gmom_res["one_way_frac"], linreg_one_way_frac=linreg_res["one_way_frac"],
        gmom_turnover=gmom_res["avg_turnover"], linreg_turnover=linreg_res["avg_turnover"],
        macd_turnover=macd_res["avg_turnover"], longonly_turnover=longonly_res["avg_turnover"],
        gmom=pd.Series(gmom_res["returns"], index=test_dates), linreg=pd.Series(linreg_res["returns"], index=test_dates),
        macd=pd.Series(macd_res["returns"], index=test_dates), longonly=pd.Series(longonly_res["returns"], index=test_dates),
    )


# "_v2" + shift tag: the pre-2026-07-26 checkpoints (network_momentum_checkpoints[_variant]/) are
# SUPERSEDED, not just outdated -- they were computed on a graph-learning solver that silently ignored
# the input data (see kalofolias_graph_learning.py's z-normalization fix) and had no transaction costs
# applied anywhere. Using a distinct directory name prevents ever accidentally loading one of those
# invalid checkpoints as if it were a valid post-fix result.
_CKPT_DIR_NAME = f"network_momentum_checkpoints_v3_{WALKFORWARD_VARIANT}_shift{SHIFT_N}"  # v3: the "v2"
# checkpoints (all 6 already-completed expanding+rolling shift0 blocks) are now STALE -- built on the
# daily_ret/roll-TC bug fixed 2026-07-26 -- bumping the version prevents ever accidentally reloading one
# of those as if it were valid post-fix output.
CHECKPOINT_DIR = os.path.join(_THIS_DIR, "outputs", _CKPT_DIR_NAME)


def _checkpoint_path(block_idx: int) -> str:
    return os.path.join(CHECKPOINT_DIR, f"block_{block_idx}.pkl")


def run_full_backtest(grid: tuple[float, ...] = ALPHA_BETA_GRID, log=print,
                       blocks_to_run: list[int] | None = None) -> dict:
    """`blocks_to_run`: 0-indexed block numbers to actually run/checkpoint this
    call (default: all, in sequence -- the original behaviour). Blocks are
    mutually independent (each only needs the shared `panel` + its own
    train/test split), so running a subset (e.g. just Block 2 while Block 1
    is separately retried) is valid -- not a partial/incorrect result, just
    a partial aggregation (below) limited to whichever blocks have a
    checkpoint on disk right now."""
    log("Loading panel...")
    t0 = time.time()
    panel = load_panel()
    log(f"Panel: {len(panel['dates'])} days, {panel['dates'][0].date()} -> {panel['dates'][-1].date()}, "
        f"{N_ASSETS} products. ({time.time()-t0:.1f}s)")

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    indices = blocks_to_run if blocks_to_run is not None else list(range(len(BLOCKS)))
    block_results = []
    for i in indices:
        tr_start, tr_end, te_start, te_end = BLOCKS[i]
        ckpt = _checkpoint_path(i)
        if os.path.exists(ckpt):
            res = pd.read_pickle(ckpt)
            log(f"\n=== Block {i+1}/{len(BLOCKS)}: loaded from checkpoint {ckpt} "
                f"(alpha*={res['alpha']} beta*={res['beta']}) ===")
            block_results.append(res)
            continue
        log(f"\n=== Block {i+1}/{len(BLOCKS)} ===")
        tb0 = time.time()
        res = run_walk_forward_block(panel, tr_start, tr_end, te_start, te_end, grid=grid, log=log)
        log(f"Block {i+1} done in {time.time()-tb0:.0f}s. alpha*={res['alpha']} beta*={res['beta']}")
        pd.to_pickle(res, ckpt)
        log(f"  checkpoint saved: {ckpt}")
        block_results.append(res)

    if not block_results:
        log("No blocks run and no checkpoints found -- nothing to aggregate.")
        return dict(blocks=[], combined={}, metrics={})

    combined = {
        name: pd.concat([r[name] for r in block_results]).sort_index()
        for name in ("gmom", "linreg", "macd", "longonly")
    }
    log("\n=== Aggregated OOS Table 1 (2026-07-25 replication, adapted 22-product commodity universe) ===")
    log(f"{'Strategy':<12}{'return':>9}{'vol':>8}{'sharpe':>9}{'downdev':>9}{'mdd':>8}"
        f"{'sortino':>9}{'calmar':>9}{'hitrate':>9}{'avgP/L':>8}")
    metrics_by_name = {}
    for name in ("longonly", "macd", "linreg", "gmom"):
        m = table1_metrics(combined[name])
        metrics_by_name[name] = m
        log(f"{name:<12}{m['ret']:>9.3f}{m['vol']:>8.3f}{m['sharpe']:>9.3f}{m['downside_dev']:>9.3f}"
            f"{m['mdd']:>8.3f}{m['sortino']:>9.3f}{m['calmar']:>9.3f}{m['hit_rate']:>9.3f}{m['avg_p_avg_l']:>8.3f}")

    return dict(blocks=block_results, combined=combined, metrics=metrics_by_name)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", type=int, default=None,
                         help="1-indexed block number to run alone (default: run/resume all 3 in sequence)")
    args = parser.parse_args()

    blocks_to_run = [args.block - 1] if args.block is not None else None
    print(f"WALKFORWARD_VARIANT = {WALKFORWARD_VARIANT}  ({len(BLOCKS)} blocks)")
    print(f"N_WORKERS = {N_WORKERS} ({os.cpu_count()} cores detected)")
    print(f"SHIFT_N = {SHIFT_N}  TC_BPS = {TC_BPS}")
    results = run_full_backtest(blocks_to_run=blocks_to_run)
    if results["blocks"]:
        out_dir = os.path.join(_THIS_DIR, "outputs")
        os.makedirs(out_dir, exist_ok=True)
        suffix = f"_block{args.block}" if args.block is not None else ""
        out_path = os.path.join(out_dir, f"network_momentum_replication_results_v3_{WALKFORWARD_VARIANT}_shift{SHIFT_N}{suffix}.csv")
        pd.DataFrame(results["combined"]).to_csv(out_path)
        print(f"\nSaved combined OOS return series to {out_path}")
        print("\nPer-block diagnostics:")
        for i, r in enumerate(results["blocks"]):
            print(f"  Block {i+1}: alpha={r['alpha']} beta={r['beta']} val_sharpe={r['validation_sharpe']:.3f}  "
                  f"turnover(gmom/linreg/macd/longonly)={r['gmom_turnover']:.4f}/{r['linreg_turnover']:.4f}/"
                  f"{r['macd_turnover']:.4f}/{r['longonly_turnover']:.4f}  "
                  f"one_way(gmom/linreg)={r['gmom_one_way_frac']:.1%}/{r['linreg_one_way_frac']:.1%}")
