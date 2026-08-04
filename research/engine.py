"""
research/engine.py
===================
Pure signal / PnL / Sharpe primitives for the offline research pipeline
(ex-ante-parameter-locked backtests, regime analysis, stat-arb screening,
eventual cross-asset portfolio construction).

Deliberately a SEPARATE copy from common_engine.py / common_shared.py, not an
import -- the dashboards (metals_dashboard, energy_dashboard, precious_metals_
dashboard, ngl_dashboard) must never be affected by anything this research
pipeline does, and this pipeline should never need a Streamlit runtime just to
run a batch backtest. The functions below are copied VERBATIM (no logic
changes) from common_engine.py and common_shared.py as they stood on
2026-07-23 -- see the "Copied from" note on each function. If a genuine bug
fix is ever needed in one of these, fix it in BOTH places and note the date,
since there is no longer a single source of truth by construction.

Conventions preserved exactly from the dashboards (do not change without
re-checking against common_engine.py):
  - PnL = position x delta(F1_continuous), ratio back-adjusted, native-unit
    dollar terms (not %-of-notional -- back-adjusted levels can go negative).
  - Transaction costs charged on F1_raw at each position change, plus a
    roll-day charge for positions held through a contract roll.
  - Sharpe = annualised, ACTIVE-DAY convention (only days where position!=0).
  - Execution timing: exec_shift(sig, shift_n) = sig.shift(shift_n + 1) --
    shift_n is EXTRA delay on top of the 1-day floor needed to avoid same-bar
    look-ahead leakage, not the raw shift itself.

Carry naming note (source of a real mismatch worth remembering): the
dashboards' UI labels "V1 Level / V2 Z-score / V3 Carry-Momentum" map to code
functions carry_v1_position / carry_v3_position / carry_v4_position
respectively -- there is no carry_v2_position in the source, an old variant
was apparently retired. Use carry_v3_position when the research plan says
"the V2 Z-score anchor", not a function literally named v2.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ═══════════════════════════════════════════════════════════════
# TRANSACTION COST + POSITION METRICS
# Copied from common_shared.py (transaction_cost, pos_metrics_generic)
# ═══════════════════════════════════════════════════════════════

def transaction_cost(pos, f1r, tc_bps: int, phase=None):
    """Shared TC convention: tc[t] = |position[t]-position[t-1]| * (tc_bps/10000/2) * F1_raw[t],
    first day's TC based on the position's absolute size (a flip from flat).
    PLUS a roll-day charge for positions held through a contract roll (Phase == "Roll_LTD-N"),
    charged only for exposure with the same sign before and after the roll."""
    pos = pos.reindex(f1r.index).fillna(0.0)
    chg = pos.diff().abs()
    if len(chg):
        chg.iloc[0] = abs(pos.iloc[0])
    tc = chg * (tc_bps / 10000.0 / 2.0) * f1r.reindex(pos.index)

    if phase is not None:
        phase = phase.reindex(pos.index)
        is_roll_day = phase.astype(str).str.startswith("Roll_LTD")
        prev_pos = pos.shift(1)
        held_through_roll = is_roll_day & (pos != 0) & (prev_pos != 0) & (np.sign(pos) == np.sign(prev_pos))
        tc = tc + held_through_roll.astype(float) * (tc_bps / 10000.0 / 2.0) * f1r.reindex(pos.index)

    return tc


def pos_metrics_generic(pos, f1r, f1c, tc_bps: int = 5, phase=None) -> dict:
    """Active-day gross/net Sharpe, annualized $PnL, max-DD ($) for a position series.
    PnL on F1_continuous; TC on F1_raw. Native dollar/unit terms (e.g. USD/MT, USD/bbl),
    not %-of-notional. `ann`/`mdd` computed on NET (TC-adjusted) PnL."""
    pos = pos.reindex(f1c.index).fillna(0.0)
    gp = pos * f1c.diff()
    tc = transaction_cost(pos, f1r, tc_bps, phase)
    net = gp - tc

    def _s(pnl):
        a = pnl[pos != 0].dropna()
        return float(a.mean() / a.std(ddof=1) * np.sqrt(252)) if len(a) > 20 and a.std(ddof=1) > 0 else np.nan

    cum = net.fillna(0).cumsum()
    value = np.exp(cum)
    ann_pnl = net.dropna().mean() * 252 if net.notna().any() else np.nan
    return dict(gross=_s(gp), net=_s(net),
                ann=float(ann_pnl) if pd.notna(ann_pnl) else np.nan,
                mdd=float((value / value.cummax() - 1).min()), nact=int((pos != 0).sum()),
                flat_pct=float(100 * (pos == 0).sum() / len(pos)) if len(pos) else np.nan)


# ═══════════════════════════════════════════════════════════════
# GENERIC RETURN / EQUITY / ROLLING-SHARPE HELPERS
# Copied from common_engine.py
# ═══════════════════════════════════════════════════════════════

def daily_returns(pos: pd.Series, f1r: pd.Series, f1c: pd.Series, tc_bps: int,
                   phase: pd.Series | None = None) -> tuple[pd.Series, pd.Series]:
    """Gross and net daily $PnL (native unit, e.g. USD/MT) for a position series."""
    pos = pos.reindex(f1c.index).fillna(0.0)
    gp = pos * f1c.diff()
    tc = transaction_cost(pos, f1r, tc_bps, phase)
    net = gp - tc
    return gp, net


# ═══════════════════════════════════════════════════════════════
# LOG-RETURN PnL / SHARPE (new -- for the cross-asset research pipeline,
# per the user's decision 2026-07-23 to switch to Bogorad's own log-return
# methodology so Metals/Precious/Energy/NGL results combine without a
# price-level-scale distortion). Uses a RATIO-adjusted continuous price
# (research/ratio_continuous.py), NOT the dashboards' additively-adjusted
# F1_continuous (which goes negative for a majority of history on several
# products -- fatal for logs). TC here is a pure bps drag, no need to scale
# by F1_raw since log-returns are already normalized/unit-free.
# ═══════════════════════════════════════════════════════════════

def log_return_transaction_cost(pos: pd.Series, tc_bps: int, phase: pd.Series | None = None) -> pd.Series:
    """Log-return-space TC: tc[t] = |position[t]-position[t-1]| * (tc_bps/10000/2),
    first day's TC based on the position's absolute size (a flip from flat).
    The /2 matches the dollar-PnL transaction_cost()'s convention exactly
    (tc_bps is a ROUND-TRIP cost, so one directional change is charged half
    of it) -- this file originally omitted the /2 here, a real bug caught via
    the Excel-tradebook cross-check (2026-07-23): it silently charged TC at
    DOUBLE the intended rate in every log-return backtest run before the fix.
    PLUS a roll-day charge for positions held through a contract roll (same
    economic reason as the dollar version's transaction_cost() -- rolling is
    a real trade even when the strategy's directional position doesn't
    change), charged only for exposure with the same sign before and after."""
    pos = pos.fillna(0.0)
    chg = pos.diff().abs()
    if len(chg):
        chg.iloc[0] = abs(pos.iloc[0])
    tc = chg * (tc_bps / 10000.0 / 2.0)

    if phase is not None:
        phase = phase.reindex(pos.index)
        is_roll_day = phase.astype(str).str.startswith("Roll_LTD")
        prev_pos = pos.shift(1)
        held_through_roll = is_roll_day & (pos != 0) & (prev_pos != 0) & (np.sign(pos) == np.sign(prev_pos))
        tc = tc + held_through_roll.astype(float) * (tc_bps / 10000.0 / 2.0)

    return tc


def log_return_daily(pos: pd.Series, log_price: pd.Series, tc_bps: int,
                      phase: pd.Series | None = None) -> tuple[pd.Series, pd.Series]:
    """Gross and net daily LOG-RETURN contribution for a position series.
    `log_price` = np.log(F1_continuous_ratio) -- a ratio-adjusted continuous
    price already logged. Position convention: +-1 = fully long/short one
    unit of notional exposure, 0 = flat -- gross contribution is simply
    pos[t] * (log_price[t]-log_price[t-1]), the position decided at t-1
    (already embedded in pos[t] via exec_shift) times that day's log return."""
    pos = pos.reindex(log_price.index).fillna(0.0)
    gp = pos * log_price.diff()
    tc = log_return_transaction_cost(pos, tc_bps, phase)
    net = gp - tc
    return gp, net


def log_return_metrics(pos: pd.Series, log_price: pd.Series, tc_bps: int = 5,
                        phase: pd.Series | None = None) -> dict:
    """Active-day gross/net Sharpe (annualized), annualized log-return, max
    drawdown (in cumulative log-return terms) -- log-return-space analog of
    pos_metrics_generic(), for the cross-asset research pipeline."""
    pos = pos.reindex(log_price.index).fillna(0.0)
    gp, net = log_return_daily(pos, log_price, tc_bps, phase)

    def _s(pnl):
        a = pnl[pos != 0].dropna()
        return float(a.mean() / a.std(ddof=1) * np.sqrt(252)) if len(a) > 20 and a.std(ddof=1) > 0 else np.nan

    cum = net.fillna(0).cumsum()
    value = np.exp(cum)
    ann_ret = net.dropna().mean() * 252 if net.notna().any() else np.nan
    return dict(gross=_s(gp), net=_s(net),
                ann=float(ann_ret) if pd.notna(ann_ret) else np.nan,
                mdd=float((value / value.cummax() - 1).min()), nact=int((pos != 0).sum()),
                flat_pct=float(100 * (pos == 0).sum() / len(pos)) if len(pos) else np.nan)


def equity_curve(pnl: pd.Series) -> pd.Series:
    """Cumulative $PnL path (native unit, e.g. USD/MT)."""
    return pnl.fillna(0).cumsum()


def rolling_sharpe(pnl: pd.Series, window: int = 252) -> pd.Series:
    """Rolling Sharpe from a $PnL series (dimensionless -- $ cancels in the ratio)."""
    r = pnl.fillna(0)
    return r.rolling(window).mean() / r.rolling(window).std() * np.sqrt(252)


def rolling_price_vol(price: pd.Series, window: int = 252) -> pd.Series:
    """EWMA (span=window) annualized volatility of the underlying's daily $ change.
    Per Bouchouev's Virtual Barrels Ch. 8.4: EWMA avoids the "volatility ghost" a fixed
    rolling window suffers (a shock distorts the estimate for exactly the window length,
    then vanishes abruptly)."""
    daily_chg = price.diff()
    return daily_chg.ewm(span=window, min_periods=max(window // 4, 5)).std() * np.sqrt(252)


TIMING_OPTIONS = ["Same Day (Shift-0)", "Lag-1 (Shift-1)", "Lag-2 (Shift-2)"]
TIMING_SHIFT = {"Same Day (Shift-0)": 0, "Lag-1 (Shift-1)": 1, "Lag-2 (Shift-2)": 2}


def exec_shift(sigbin: pd.Series, shift_n: int) -> pd.Series:
    """Position that actually earns PnL: Position[t] = Signal[t-(shift_n+1)].
    shift_n is EXTRA delay on top of the 1-day floor needed to avoid same-bar look-ahead."""
    return sigbin.shift(shift_n + 1)


# ═══════════════════════════════════════════════════════════════
# MOMENTUM: MA CROSSOVER
# Copied from common_engine.py
# ═══════════════════════════════════════════════════════════════

def ma_crossover_position(f1r: pd.Series, fast: int, slow: int, shift_n: int = 1) -> pd.Series:
    sig = np.sign(f1r.rolling(fast).mean() - f1r.rolling(slow).mean())
    return exec_shift(sig, shift_n).fillna(0)


def momentum_composite_position(f1r: pd.Series, pairs: tuple[tuple[int, int], ...],
                                 shift_n: int = 1) -> pd.Series:
    """Ex-ante Momentum anchor (locked 2026-07-23): average the RAW sign of
    several MA-crossover pairs into one composite, per Bogorad's own
    convention (his Table 1: (1,5)/(5,20)/(10,60) averaged) -- averaging
    smooths "which lookback is right" fragility since every pair measures the
    SAME hypothesis (price trend) at a different speed. `pairs` is NOT
    hardcoded here -- pass whichever (fast, slow) tuples this asset class's
    config specifies (e.g. Metals config: ((1,20),(5,60),(20,250)), matching
    the crossovers already used in the dashboards' own Momentum tab).

    Raw (unshifted, unfilled) signs are summed and divided BEFORE shifting/
    filling, so a date where any one pair is still in its own burn-in window
    (NaN) propagates NaN for the whole composite rather than being silently
    treated as "flat" -- avoids a longer-lookback pair's burn-in period
    quietly biasing the composite toward zero early in the sample."""
    n = len(pairs)
    total = None
    for fast, slow in pairs:
        sig = np.sign(f1r.rolling(fast).mean() - f1r.rolling(slow).mean())
        total = sig if total is None else total + sig
    composite_sign = np.sign(total / n)
    return exec_shift(composite_sign, shift_n).fillna(0)


# ═══════════════════════════════════════════════════════════════
# CARRY: V1 LEVEL / V2 Z-SCORE (code name carry_v3) / V3 CARRY-MOMENTUM (code name carry_v4)
# Copied from common_engine.py -- see module docstring for the naming mismatch
# ═══════════════════════════════════════════════════════════════

def _carry_base(curve: pd.DataFrame, a: str, b: str) -> pd.Series:
    if a not in curve.columns or b not in curve.columns:
        return pd.Series(dtype=float)
    fa, fb = curve[a].dropna(), curve[b].dropna()
    idx = fa.index.intersection(fb.index)
    return ((fa.reindex(idx) - fb.reindex(idx)) / fa.reindex(idx)).replace([np.inf, -np.inf], np.nan).dropna()


def carry_v1_position(curve: pd.DataFrame, near: str = "F1", far: str = "F2", shift_n: int = 1) -> pd.Series:
    """UI label: "V1 Level" -- sign of the raw (near-far)/near slope."""
    raw = _carry_base(curve, near, far)
    return exec_shift(np.sign(raw), shift_n).fillna(0)


def carry_v3_position(curve: pd.DataFrame, window: int = 252, shift_n: int = 1,
                       near: str = "F1", far: str = "F2") -> pd.Series:
    """UI label: "V2 Z-score" (win=252 default)."""
    base = _carry_base(curve, near, far)
    if base.empty:
        return pd.Series(dtype=float)
    z = (base - base.rolling(window).mean()) / base.rolling(window).std()
    return exec_shift(np.sign(z.replace([np.inf, -np.inf], np.nan)), shift_n).fillna(0)


def carry_v4_position(curve: pd.DataFrame, horizon: int = 20, shift_n: int = 1,
                       near: str = "F1", far: str = "F2") -> pd.Series:
    """UI label: "V3 Carry-Momentum" (N=20 default)."""
    base = _carry_base(curve, near, far)
    if base.empty:
        return pd.Series(dtype=float)
    raw = base - base.shift(horizon)
    return exec_shift(np.sign(raw), shift_n).fillna(0)


def carry_v1v2_composite_position(curve: pd.DataFrame, near: str = "F1", far: str = "F2",
                                   zscore_window: int = 252, shift_n: int = 1) -> pd.Series:
    """Ex-ante Carry anchor (locked 2026-07-23): average V1 (Level) and V2
    (Z-score) into one composite -- deliberately NOT including V3
    (Carry-Momentum), which is a rate-of-change/momentum-on-carry construct,
    a genuinely different economic hypothesis from V1/V2's level-based signal,
    kept as its own separate strategy instead (see carry_v4_position).
    V1 and V2 are both derived from the same raw carry slope (V2 just
    normalizes it against its own recent history), so averaging them is the
    same "same hypothesis, different lens" logic as momentum_composite_position,
    unlike a V1+V2+V3 blend which would mix level and rate-of-change.

    `near`/`far`/`zscore_window` are NOT hardcoded for any one asset class --
    pass whichever tenor pair this asset's config specifies (e.g. Metals:
    ("F1","F3") and ("F1","F13"), called once per locked tenor pair)."""
    base = _carry_base(curve, near, far)
    if base.empty:
        return pd.Series(dtype=float)
    v1_sign = np.sign(base)
    z = (base - base.rolling(zscore_window).mean()) / base.rolling(zscore_window).std()
    v2_sign = np.sign(z.replace([np.inf, -np.inf], np.nan))
    composite_sign = np.sign((v1_sign + v2_sign) / 2)
    return exec_shift(composite_sign, shift_n).fillna(0)


# ═══════════════════════════════════════════════════════════════
# VALUE: V1 MA-REVERSION
# Copied from common_engine.py
# ═══════════════════════════════════════════════════════════════

def value_v1_position(curve: pd.DataFrame, contract: str, lookback: int, threshold: float,
                       shift_n: int = 2) -> pd.Series:
    if contract not in curve.columns:
        return pd.Series(dtype=float)
    fk = curve[contract].dropna()
    if len(fk) < max(lookback // 2, 60):
        return pd.Series(dtype=float)
    ma = fk.rolling(lookback, min_periods=max(lookback // 2, min(lookback, 60))).mean()
    dev = ((fk - ma) / ma.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).dropna()
    sig = pd.Series(np.where(dev.values < -threshold, 1.0, np.where(dev.values > threshold, -1.0, 0.0)),
                     index=dev.index)
    return exec_shift(sig, shift_n).fillna(0)


# ═══════════════════════════════════════════════════════════════
# STATARB: VALUE SIGNAL APPLIED TO A SPREAD INSTEAD OF A PRICE
# New (not in common_engine.py -- no dashboard has a StatArb tab yet).
# Same formula as value_v1_position, generalized to take a pre-built spread
# series directly instead of a single curve/contract, so it works for a
# cross-product spread like Zinc-Lead as well as an intra-product one.
# ═══════════════════════════════════════════════════════════════

def statarb_spread_position(spread: pd.Series, lookback: int, threshold: float,
                             shift_n: int = 2) -> pd.Series:
    """spread = price_A - price_B (or any pre-built spread series). Same
    threshold-on-moving-average rule as value_v1_position, applied to the
    spread's own recent moving average instead of a single asset's long-run one
    (Bogorad's own StatArb convention uses a much shorter lookback here, e.g.
    n=20 days, vs Value's multi-year lookback -- a spread's fair value re-
    equilibrates via a physical mechanism much faster than an outright price's
    long-run fundamental level does)."""
    s = spread.dropna()
    if len(s) < max(lookback // 2, 20):
        return pd.Series(dtype=float)
    ma = s.rolling(lookback, min_periods=max(lookback // 2, min(lookback, 20))).mean()
    dev = (s - ma).dropna()
    denom = ma.reindex(dev.index).abs().replace(0, np.nan)
    pct_dev = (dev / denom).replace([np.inf, -np.inf], np.nan).dropna()
    sig = pd.Series(np.where(pct_dev.values < -threshold, 1.0, np.where(pct_dev.values > threshold, -1.0, 0.0)),
                     index=pct_dev.index)
    return exec_shift(sig, shift_n).fillna(0)


# Portfolio-tab support: raw (pre-shift) leg signals and pluggable combiners.
# Used by dashboard_portfolio_tab.py for the customizable Metals Portfolio
# tab. These do not modify any function above; the locked composite
# functions (momentum_composite_position, carry_v1v2_composite_position)
# remain the source of truth for the definitive regime-table and tradebook
# numbers. Each raw_signal_* function reproduces its corresponding locked
# position function's formula one step earlier, in pre-shift, pre-fillna
# space, so combine_positions() can average across an arbitrary,
# user-editable leg list the same way the two locked composites already do
# for their own fixed leg counts.

def raw_signal_momentum(f1r: pd.Series, fast: int, slow: int) -> pd.Series:
    """Raw, pre-shift MA-crossover sign. Same formula as ma_crossover_position."""
    return np.sign(f1r.rolling(fast).mean() - f1r.rolling(slow).mean())


def raw_signal_carry_v1(curve: pd.DataFrame, near: str = "F1", far: str = "F2") -> pd.Series:
    """Raw, pre-shift V1 Level sign. Same formula as carry_v1_position."""
    return np.sign(_carry_base(curve, near, far))


def raw_signal_carry_v2(curve: pd.DataFrame, near: str = "F1", far: str = "F2",
                         window: int = 252) -> pd.Series:
    """Raw, pre-shift V2 Z-score sign. Same formula as carry_v3_position."""
    base = _carry_base(curve, near, far)
    if base.empty:
        return pd.Series(dtype=float)
    z = (base - base.rolling(window).mean()) / base.rolling(window).std()
    return np.sign(z.replace([np.inf, -np.inf], np.nan))


def raw_signal_carrymom(curve: pd.DataFrame, near: str = "F1", far: str = "F2",
                         horizon: int = 20) -> pd.Series:
    """Raw, pre-shift V3 Carry-Momentum sign. Same formula as carry_v4_position."""
    base = _carry_base(curve, near, far)
    if base.empty:
        return pd.Series(dtype=float)
    return np.sign(base - base.shift(horizon))


def raw_signal_value(curve: pd.DataFrame, contract: str, lookback: int, threshold: float) -> pd.Series:
    """Raw, pre-shift Value MA-reversion sign. Same formula as value_v1_position: NaN during
    the moving average's own burn-in window, zero inside the threshold band, plus or minus one
    outside it."""
    if contract not in curve.columns:
        return pd.Series(dtype=float)
    fk = curve[contract].dropna()
    if len(fk) < max(lookback // 2, 60):
        return pd.Series(dtype=float)
    ma = fk.rolling(lookback, min_periods=max(lookback // 2, min(lookback, 60))).mean()
    dev = ((fk - ma) / ma.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    sig = pd.Series(np.where(dev.values < -threshold, 1.0, np.where(dev.values > threshold, -1.0, 0.0)),
                     index=dev.index)
    return sig.where(dev.notna())


def combine_positions(raw_signals: list[pd.Series], method: str = "equal_weight",
                       weights: list[float] | None = None) -> pd.Series:
    """Combine several raw, pre-shift leg signs into one raw composite sign.

    Generalizes momentum_composite_position and carry_v1v2_composite_position's own
    "sum raw signs, divide, take the sign" pattern to an arbitrary leg count and a pluggable
    combination method. The caller still applies exec_shift() and fillna(0) to the result.
    This function deliberately stays in raw-signal space so a NaN burn-in period on any one leg
    propagates correctly (skipna is disabled) rather than being silently treated as a flat vote,
    matching the discipline of the two locked composite functions.
    """
    raw_signals = [s for s in raw_signals if not s.empty]
    if not raw_signals:
        return pd.Series(dtype=float)
    idx = raw_signals[0].index
    for s in raw_signals[1:]:
        idx = idx.union(s.index)
    aligned = pd.concat([s.reindex(idx) for s in raw_signals], axis=1)
    if method == "equal_weight":
        combo = aligned.mean(axis=1, skipna=False)
    elif method == "weighted":
        if weights is None or len(weights) != len(raw_signals):
            raise ValueError("weighted combine requires exactly one weight per leg")
        w = np.asarray(weights, dtype=float)
        w = w / w.sum()
        combo = (aligned * w).sum(axis=1, skipna=False)
    else:
        raise ValueError(f"Unknown combine method {method!r}. Only 'equal_weight' and 'weighted' "
                          f"are implemented; inverse-vol and risk-parity are a planned follow-up.")
    return np.sign(combo)


def combine_returns(net_returns: list[pd.Series], method: str = "equal_weight",
                     weights: list[float] | None = None, vol_window: int = 63) -> pd.Series:
    """Combine several already-computed daily net return series into one, via a weighted average.

    Used both to aggregate per-product strategy returns into one asset-class line, and to
    combine per-strategy asset-class lines into one portfolio.

    'inverse_vol' reweights daily: each series' weight is 1 / its own trailing `vol_window`-day
    realized vol (rolling std of ITS OWN return history, recomputed every day), normalized so
    the weights sum to 1 across series on that day. This is a rolling, look-ahead-free scheme --
    day t's weights use only returns strictly before t via pandas rolling's own window semantics
    -- as opposed to fixing weights once from full-sample vol, which would leak future
    information into the weights applied to the past. The tradeoff is a `vol_window`-day burn-in
    before any weight (and therefore the combined series) is defined, on top of each leg's own
    burn-in.

    When every input series already shares the exact same date index (true for every product
    within Metals, Precious Metals, and NGL -- confirmed, no internal exchange split), this is
    plain pandas addition (no reindex, no fillna), matching run_regime_table.py's historical
    behavior exactly: each per-product `net` series is already reindexed to ITS OWN calendar
    upstream (log_return_daily reindexes to log_price's index), fixing internal burn-in gaps
    only, and summing series with identical indices needs no further alignment step.

    When the input series' indices DIFFER (Energy: NYMEX (WTI/RBOB/HeatingOil/NatGas) vs ICE
    (Brent/SingaporeGasoil) vs Argus-style (FuelOil); or any two strategies with different
    burn-in lengths, e.g. Value's 1260-day lookback vs Momentum's shorter MAs, early in the
    sample before both have burned in), this function no longer does bare summation-then-later-
    dropna. FIXED 2026-08-04, propagated here from research/cross_asset_engine.py after a real
    bug was found and worked through by hand (see that module's _combine_intersection for the
    full derivation): summing already-computed daily returns and letting a mismatched date go
    to NaN (later dropped by whatever computes metrics) silently DELETES a non-gapped member's
    real, already-realized return on that date -- e.g. if Copper trades 3rd/4th/5th Jan but WTI
    trades only 3rd/5th, naive sum-then-drop discards Copper's real 3rd->4th return entirely
    (the 4th-Jan row goes to NaN because WTI has nothing there) while WTI's full 3rd->5th move
    survives intact -- asymmetric and wrong. The fix: convert each series to a CUMULATIVE level
    (cumsum of log-returns behaves exactly like a log-price -- same telescoping-sum math),
    restrict to the intersected date set, then diff ACROSS those surviving dates. A dropped
    date's move is then naturally absorbed into whichever surviving date comes next for EVERY
    series independently -- nothing silently deleted, nothing double-counted. This is purely
    backward-looking (cumsum then diff on an already-sorted, already-past index); no look-ahead
    is introduced. When indices already match, this produces numerically IDENTICAL output to
    the plain-sum path (nothing to absorb), which is why the plain-sum path stays as a fast-path
    special case rather than being replaced outright -- most calls in this project (Metals,
    Precious, NGL, same-burn-in strategy combinations) hit that fast path unchanged.

    This is also NOT the Excel tradebook generator's stricter day-INTERSECTION convention, which
    is specific to that formula-audit tool (see project_risk_premia_research_framework memory
    #21) -- multiple, each-correct-for-its-own-purpose conventions exist in this project; this
    function must stay matched to run_regime_table.py's, since that is the one whose output is
    the officially reported number.
    """
    net_returns = [s for s in net_returns if not s.empty]
    if not net_returns:
        return pd.Series(dtype=float)

    def _combine_aligned_or_intersected(series_list, weight_arr=None):
        indices_match = all(s.index.equals(series_list[0].index) for s in series_list[1:])
        if indices_match:
            if weight_arr is None:
                combined = series_list[0]
                for s in series_list[1:]:
                    combined = combined + s
                return combined / len(series_list)
            combined = series_list[0] * weight_arr[0]
            for s, wi in zip(series_list[1:], weight_arr[1:]):
                combined = combined + s * wi
            return combined
        # Indices differ -- cumulative-level intersect-then-diff, so a dropped date doesn't
        # silently delete another member's real return (see docstring above).
        cum_levels = [s.cumsum() for s in series_list]
        idx = cum_levels[0].index
        for c in cum_levels[1:]:
            idx = idx.intersection(c.index)
        idx = idx.sort_values()
        aligned = [c.reindex(idx).diff() for c in cum_levels]
        if weight_arr is None:
            combined = aligned[0]
            for a in aligned[1:]:
                combined = combined + a
            return combined / len(series_list)
        combined = aligned[0] * weight_arr[0]
        for a, wi in zip(aligned[1:], weight_arr[1:]):
            combined = combined + a * wi
        return combined

    if method == "equal_weight":
        return _combine_aligned_or_intersected(net_returns)
    if method == "weighted":
        if weights is None or len(weights) != len(net_returns):
            raise ValueError("weighted combine requires exactly one weight per series")
        w = np.asarray(weights, dtype=float)
        w = w / w.sum()
        return _combine_aligned_or_intersected(net_returns, w)
    if method == "inverse_vol":
        if len(net_returns) == 1:
            return net_returns[0]
        idx = net_returns[0].index
        for s in net_returns[1:]:
            idx = idx.union(s.index)
        rets = pd.concat([s.reindex(idx) for s in net_returns], axis=1)
        vol = rets.rolling(vol_window, min_periods=vol_window).std(ddof=1)
        inv_vol = 1.0 / vol.replace(0.0, np.nan)
        w = inv_vol.div(inv_vol.sum(axis=1, skipna=False), axis=0)
        return (w * rets).sum(axis=1, skipna=False)
    raise ValueError(f"Unknown combine method {method!r}. Only 'equal_weight', 'weighted', and "
                      f"'inverse_vol' are implemented; risk-parity is a planned follow-up.")
