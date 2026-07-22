"""
common_engine.py
=================
Generic, product-agnostic Momentum / Carry / Value strategy engine and
Streamlit tab renderers, shared by every asset-class dashboard (Metals,
Energy, Precious Metals, NGL). Each dashboard's app.py just loads its
own F1_continuous + curve data and calls render_momentum_tab /
render_carry_tab / render_value_tab -- all the signal math, charts,
and layout live here once.

Stage 2 scope (deliberately simple, per spec): MA-crossover momentum
only (no CTA/Baz-Granger, no structural Anchors), Carry V1-V3 (V1 Level
[Roll Yield/Long Slope merged, any contract pair], V2 Z-score, V3
Carry-Momentum), Value V1 MA-reversion only. No OOS / walk-forward yet
-- in-sample only.

Conventions (identical to Stage 1 / Metals dashboard):
  - PnL = position x delta(F1_continuous), ratio back-adjusted.
  - Transaction costs charged on F1_raw at each position change.
  - Sharpe = annualised, active-day convention.
  - Execution timing = shift_n applied to the signal series, via
    exec_shift(sig, shift_n) = sig.shift(shift_n + 1): a position decided
    from signal[t] needs F1_raw[t] as an input, so it can't exist until
    AFTER the t-1->t return already happened -- pairing signal[t] with that
    same return (a raw shift(0)) uses day t's close twice and is a same-bar
    look-ahead leak, not a valid "faster" execution. shift(1) is therefore
    the fastest any position can legitimately go live; shift_n counts EXTRA
    days of delay on top of that 1-day floor, not the raw shift itself. So:
      Same Day (Shift-0): position[t] = signal[t-1]  -- the fastest
        legitimate entry (the 1-day floor, no extra delay).
      Lag-1 (Shift-1):    position[t] = signal[t-2]  -- one extra day of
        delay on top of the floor.
      Lag-2 (Shift-2):    position[t] = signal[t-3]  -- two extra days of
        delay on top of the floor.
    All three are distinct, realistically-tradeable series -- none of them
    can ever pair a signal with the same-bar return that produced it. See
    exec_shift()'s docstring for the full worked mechanics.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from common_shared import (CHART_LAYOUT, COLORS, pos_metrics_generic, section_header, tc_label_map,
                            metric_card, transaction_cost)

_OVERLAY_COLORS = [COLORS["primary"], COLORS["green"], COLORS["secondary"],
                   "#A78BFA", "#F472B6", "#22D3EE", "#FB923C", "#60A5FA"]


# ═══════════════════════════════════════════════════════════════
# GENERIC RETURN / EQUITY / ROLLING-SHARPE HELPERS
# ═══════════════════════════════════════════════════════════════

def daily_returns(pos: pd.Series, f1r: pd.Series, f1c: pd.Series, tc_bps: int,
                   phase: pd.Series | None = None) -> tuple[pd.Series, pd.Series]:
    """Gross and net daily $PnL (native unit, e.g. USD/MT) for a position series.
    Dollar terms, not %-of-notional -- %-of-notional requires dividing by
    F1_continuous[t-1], which can be zero/negative (confirmed for Aluminium, WTI,
    Nat Gas, Fuel Oil), silently flipping return signs or inflating magnitudes.
    Pass `phase` to also charge roll-day TC (see common_shared.transaction_cost())."""
    pos = pos.reindex(f1c.index).fillna(0.0)
    gp = pos * f1c.diff()
    tc = transaction_cost(pos, f1r, tc_bps, phase)
    net = gp - tc
    return gp, net


def equity_curve(pnl: pd.Series) -> pd.Series:
    """Cumulative $PnL path (native unit, e.g. USD/MT)."""
    return pnl.fillna(0).cumsum()


def rolling_sharpe(pnl: pd.Series, window: int = 252) -> pd.Series:
    """Rolling Sharpe from a $PnL series (dimensionless -- $ cancels in the ratio)."""
    r = pnl.fillna(0)
    return r.rolling(window).mean() / r.rolling(window).std() * np.sqrt(252)


def rolling_price_vol(price: pd.Series, window: int = 252) -> pd.Series:
    """Rolling annualized volatility of the underlying itself (not a strategy):
    std of the price series' daily $ change, scaled by sqrt(252). Native-unit
    ($ per contract, e.g. USD/MT) terms, same as rolling_sharpe/daily_returns
    elsewhere in this file -- NOT %-of-notional, which would require dividing
    by price[t-1] (unsafe for a back-adjusted level, see pos_metrics_generic's
    docstring). Pass F1_raw (the actual traded front-month price) for this --
    F1_raw does carry roll-day jumps (unlike F1_continuous), which is a
    deliberate choice here: this is meant to read as the realized volatility
    of the real, tradeable contract, not a back-adjusted synthetic series."""
    return price.diff().rolling(window).std() * np.sqrt(252)


TIMING_OPTIONS = ["Same Day (Shift-0)", "Lag-1 (Shift-1)", "Lag-2 (Shift-2)"]
TIMING_SHIFT = {"Same Day (Shift-0)": 0, "Lag-1 (Shift-1)": 1, "Lag-2 (Shift-2)": 2}


def exec_shift(sigbin: pd.Series, shift_n: int) -> pd.Series:
    """Returns the position that actually earns PnL: Position[t] = Signal[t-(shift_n+1)].

    signal[t] needs F1_raw[t] as an input, so it isn't known until AFTER the
    t-1->t return has already happened -- pairing signal[t] with that same
    return (a raw shift(0)) uses day t's close twice (once to compute the
    signal, once as the return's endpoint), a same-bar look-ahead leak. The
    fastest a position can legitimately be live is the day immediately
    following the signal that decided it, i.e. shift(1) at minimum.

    shift_n is therefore "extra days of delay ON TOP OF that 1-day floor",
    not the raw shift itself: shift_n=0 ("Same Day") = shift(1), the fastest
    legitimate entry; shift_n=1 ("Lag-1") = shift(2), one more day of delay;
    shift_n=2 ("Lag-2") = shift(3), two more days of delay. This keeps all
    three dropdown options distinct and none of them can ever leak, unlike a
    naive shift(shift_n) where shift_n=0 would leak and shift_n=1 would be
    the true fastest-legitimate case (making "Same Day" a misnomer)."""
    return sigbin.shift(shift_n + 1)


# ═══════════════════════════════════════════════════════════════
# MOMENTUM: MA CROSSOVER
# ═══════════════════════════════════════════════════════════════

def ma_crossover_position(f1r: pd.Series, fast: int, slow: int, shift_n: int = 1) -> pd.Series:
    sig = np.sign(f1r.rolling(fast).mean() - f1r.rolling(slow).mean())
    return exec_shift(sig, shift_n).fillna(0)


@st.cache_data(show_spinner="Computing 250x250 momentum heatmap...")
def momentum_heatmap(f1r: pd.Series, f1c: pd.Series, max_window: int,
                      start: str, end: str, shift_n: int, tc_bps: int) -> pd.DataFrame:
    """Full-resolution grid of gross Sharpe for every valid (fast, slow) pair,
    fast/slow in [1, max_window], slow > fast, over [start, end].

    Vectorized: every rolling-mean window (1..max_window) is precomputed once
    into a 2D array, then each (fast, slow) pair's Sharpe is derived from two
    columns of that array with plain numpy ops -- no per-pair pandas rolling
    calls, no TC/net computation (not needed for the heatmap). A naive
    pandas-rolling-per-pair loop is what the previous coarse-grid version did;
    it does not scale to a 250x250 (~31k valid pairs) grid.
    """
    # eff_shift = shift_n + 1 -- see exec_shift()'s docstring: a position
    # decided using day t's own signal cannot legitimately capture day t's
    # own return, so the floor is shift(1); shift_n counts EXTRA days of
    # delay on top of that floor, keeping Same Day/Lag-1/Lag-2 distinct.
    eff_shift = shift_n + 1

    mask = (f1r.index >= pd.Timestamp(start)) & (f1r.index <= pd.Timestamp(end))
    f1r_w = f1r[mask].astype(float)
    f1c_w = f1c[mask].astype(float)
    n = len(f1r_w)
    if n < eff_shift + 20:
        return pd.DataFrame(columns=["fast", "slow", "sharpe"])

    delta = f1c_w.diff().values

    sma = np.full((n, max_window), np.nan)
    for k in range(max_window):
        sma[:, k] = f1r_w.rolling(k + 1).mean().values

    # Batch the inner (slow) loop into one 2D numpy op per fast value instead
    # of looping pair-by-pair (250 outer iterations instead of ~31k total).
    # Sharpe computed via masked sum/count instead of nanmean/nanstd (which
    # carry extra overhead) -- roughly 2x faster on top of the batching.
    delta_shifted = delta[eff_shift:]
    fast_out, slow_out, sharpe_out = [], [], []
    for fi in range(max_window - 1):
        fast_col = sma[:, fi]
        slow_cols = sma[:, fi + 1:max_window]                       # (n, n_slow)
        raw_sig = np.sign(fast_col[:, None] - slow_cols)
        sig = raw_sig[:-eff_shift, :]                               # aligned to delta_shifted
        pos = np.where(np.isfinite(sig), sig, 0.0)
        pnl = pos * delta_shifted[:, None]
        active_mask = (pos != 0) & np.isfinite(pnl)
        pnl_masked = np.where(active_mask, pnl, 0.0)
        counts = active_mask.sum(axis=0)
        sum_pnl = pnl_masked.sum(axis=0)
        sum_sq = (pnl_masked ** 2).sum(axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            means = sum_pnl / counts
            stds = np.sqrt(np.maximum(sum_sq / counts - means ** 2, 0.0))  # ddof=0, matches active.std()
            sharpe_row = np.where((counts > 20) & (stds > 0), means / stds * np.sqrt(252), np.nan)

        n_slow = max_window - (fi + 1)
        fast_out.append(np.full(n_slow, fi + 1))
        slow_out.append(np.arange(fi + 2, max_window + 1))
        sharpe_out.append(sharpe_row)

    return pd.DataFrame({
        "fast": np.concatenate(fast_out),
        "slow": np.concatenate(slow_out),
        "sharpe": np.concatenate(sharpe_out),
    })


def render_momentum_tab(f1r: pd.Series, f1c: pd.Series, product: str, unit_label: str,
                         key_prefix: str, heatmap_max_window: int = 250, phase: pd.Series | None = None,
                         default_feature_pair: tuple[int, int] | None = None):
    """Momentum tab: heatmap w/ year-range toggle, 3 default benchmark MAs + custom MA,
    multi-strategy equity curve, rolling Sharpe, performance metrics, TC filter.
    `phase` (if passed) adds roll-day TC on top of position-change TC.
    `default_feature_pair` overrides which of the active strategies is
    pre-selected in the Performance Metrics card (falls back to MA(1,20) if
    omitted or not in the active list) -- does NOT change the 3 benchmark
    pairs themselves, only which one is shown first.
    Returns the {label: position} dict of the currently active/chosen
    strategies, for the Comparison tab to overlay alongside Carry/Value."""
    yr0, yr1 = int(f1r.index[0].year), int(f1r.index[-1].year)

    section_header(f"MOMENTUM — {product}")
    st.caption("Moving-average crossover: signal(t) = sign[MA(F1_raw, fast) − MA(F1_raw, slow)]. "
               "Scope is limited to MA crossover; CTA/Baz-Granger and structural anchor signals "
               "are not included.")

    tc_col, timing_col, _ = st.columns([1, 1, 2])
    with tc_col:
        tc_map = tc_label_map(float(f1r.dropna().iloc[-1]), unit_label)
        tc_label = st.selectbox("Transaction Cost", list(tc_map.keys()), index=1, key=f"{key_prefix}_mom_tc")
        tc_bps = tc_map[tc_label]
    with timing_col:
        timing = st.selectbox("Execution Timing", TIMING_OPTIONS, index=1, key=f"{key_prefix}_mom_timing")
        shift_n = TIMING_SHIFT[timing]

    # ── Strategies to Compare: 3 default benchmarks + custom (selection UI only) ──
    st.markdown("**Strategies to Compare**")
    default_pairs = [(1, 20), (5, 60), (20, 250)]
    ss_key = f"{key_prefix}_mom_active"
    if ss_key not in st.session_state:
        st.session_state[ss_key] = list(default_pairs)

    bcol1, bcol2, bcol3, bcol4 = st.columns([1, 1, 1, 1])
    with bcol1:
        cf = st.number_input("Custom Fast", min_value=1, max_value=500, value=10, key=f"{key_prefix}_mom_cf")
    with bcol2:
        cs = st.number_input("Custom Slow", min_value=2, max_value=1000, value=50, key=f"{key_prefix}_mom_cs")
    with bcol3:
        st.write("")
        st.write("")
        if st.button("Add Custom MA", key=f"{key_prefix}_mom_add"):
            if cs > cf and (int(cf), int(cs)) not in st.session_state[ss_key]:
                st.session_state[ss_key] = st.session_state[ss_key] + [(int(cf), int(cs))]
    with bcol4:
        st.write("")
        st.write("")
        if st.button("Reset to Defaults", key=f"{key_prefix}_mom_reset"):
            st.session_state[ss_key] = list(default_pairs)

    active = st.session_state[ss_key]
    chosen = st.multiselect(
        "Active strategies (performance metrics / equity curve / rolling Sharpe below)",
        options=active, default=active,
        format_func=lambda p: f"MA({p[0]},{p[1]})",
        key=f"{key_prefix}_mom_multiselect",
    )

    st.divider()

    # ── Year-range slider: shared by Performance Metrics (below) and the heatmap ──
    hm_yr = st.slider("Year range for performance metrics / heatmap", yr0, yr1, (yr0, yr1),
                       key=f"{key_prefix}_mom_hm_yr")
    range_start, range_end = pd.Timestamp(f"{hm_yr[0]}-01-01"), pd.Timestamp(f"{hm_yr[1]}-12-31")
    range_mask = (f1r.index >= range_start) & (f1r.index <= range_end)
    f1r_scoped = f1r[range_mask]
    f1c_scoped = f1c.reindex(f1r_scoped.index)
    phase_scoped = phase.reindex(f1r_scoped.index) if phase is not None else None

    # ── Performance Metrics: ONE featured strategy from the active list above,
    # scoped to the year range above -- recomputes when either changes. ──────
    st.markdown("**Performance Metrics**")
    if not chosen:
        st.info("Select at least one strategy above to see its performance metrics.")
    else:
        if default_feature_pair is not None and default_feature_pair in chosen:
            default_feature = default_feature_pair
        elif (1, 20) in chosen:
            default_feature = (1, 20)
        else:
            default_feature = chosen[0]
        feature_pair = st.selectbox(
            "Strategy to feature", options=chosen, index=chosen.index(default_feature),
            format_func=lambda p: f"MA({p[0]},{p[1]})", key=f"{key_prefix}_mom_feature",
        )
        f_fast, f_slow = feature_pair
        if len(f1r_scoped) < f_slow + 20:
            st.info("Not enough data in the selected year range for this pair.")
        else:
            feature_pos = ma_crossover_position(f1r_scoped, f_fast, f_slow, shift_n=shift_n)
            m = pos_metrics_generic(feature_pos, f1r_scoped, f1c_scoped, tc_bps, phase_scoped)
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                metric_card("Gross Sharpe", _fmt_metric(m["gross"], "{:+.2f}"))
            with c2:
                metric_card("Net Sharpe", _fmt_metric(m["net"], "{:+.2f}"))
            with c3:
                metric_card("Ann PnL (Net)", _fmt_metric(m["ann"], "{:+,.2f}"), unit=f" {unit_label}")
            with c4:
                metric_card("Max DD (Net)", _fmt_metric(m["mdd"], "{:+,.2f}"), unit=f" {unit_label}")
            with c5:
                metric_card("% Flat", _fmt_metric(m["flat_pct"], "{:.0f}"), unit="%")

    st.divider()

    # ── Heatmap (uses the same year-range slider) ────────────────────────────
    st.markdown(f"**Sharpe Heatmap — Fast × Slow MA Crossover ({heatmap_max_window}×{heatmap_max_window})**")
    st.caption("Scroll/drag to zoom into any region, double-click to reset. Every integer "
               f"(fast, slow) pair with 1 ≤ fast < slow ≤ {heatmap_max_window} is included.")
    hm_df = momentum_heatmap(f1r, f1c, heatmap_max_window,
                              f"{hm_yr[0]}-01-01", f"{hm_yr[1]}-12-31", shift_n, tc_bps)
    if not hm_df.empty and hm_df["sharpe"].notna().any():
        pivot = hm_df.pivot(index="fast", columns="slow", values="sharpe")
        fig_hm = go.Figure(data=go.Heatmap(
            z=pivot.values, x=pivot.columns, y=pivot.index,
            colorscale="RdYlGn", zmid=0, colorbar=dict(title="Sharpe"),
            hovertemplate="Fast MA: %{y}<br>Slow MA: %{x}<br>Sharpe: %{z:.3f}<extra></extra>",
        ))
        fig_hm.update_layout(**CHART_LAYOUT, height=560, dragmode="zoom",
                              title=dict(text=f"{product} — Sharpe by MA Crossover", font=dict(size=13)),
                              xaxis_title="Slow MA", yaxis_title="Fast MA")
        fig_hm.update_xaxes(rangeslider=dict(visible=False))
        st.plotly_chart(fig_hm, use_container_width=True, key=f"{key_prefix}_mom_hm",
                         config={"scrollZoom": True})
        best = hm_df.loc[hm_df["sharpe"].idxmax()]
        st.caption(f"Best in range {hm_yr[0]}-{hm_yr[1]}: MA({int(best['fast'])},{int(best['slow'])}) "
                   f"gross Sharpe {best['sharpe']:+.2f}.")
    else:
        st.info("Not enough data in the selected year range to compute a heatmap.")

    # ── Cumulative PnL / Rolling Sharpe / Signal & Position: every active
    # strategy overlaid simultaneously, full history. show_metrics=False since
    # Performance Metrics is already shown (featured strategy) above. ────────
    if not chosen:
        st.divider()
        st.info("Select at least one strategy above to see its equity curve.")
        return {}

    positions = {f"MA({f},{s})": ma_crossover_position(f1r, f, s, shift_n=shift_n) for f, s in chosen}
    _render_multi_strategy_block(
        positions, f1r, f1c, tc_bps, key_prefix + "_mom", unit_label, show_metrics=False, phase=phase,
    )
    return positions


# ═══════════════════════════════════════════════════════════════
# CARRY: V1 LEVEL (ROLL YIELD / LONG SLOPE), V2 Z-SCORE, V3 CARRY-MOMENTUM
# ═══════════════════════════════════════════════════════════════

def _carry_base(curve: pd.DataFrame, a: str, b: str) -> pd.Series:
    if a not in curve.columns or b not in curve.columns:
        return pd.Series(dtype=float)
    fa, fb = curve[a].dropna(), curve[b].dropna()
    idx = fa.index.intersection(fb.index)
    return ((fa.reindex(idx) - fb.reindex(idx)) / fa.reindex(idx)).replace([np.inf, -np.inf], np.nan).dropna()


def carry_v1_position(curve: pd.DataFrame, near: str = "F1", far: str = "F2", shift_n: int = 1) -> pd.Series:
    """V1 Level -- covers what used to be separate V1 Roll Yield (near-tenor
    pair) and V2 Long Slope (far-tenor pair) variants: identical formula,
    the only difference was which (near, far) pair fed it, so one function
    with a free pair argument replaces both."""
    raw = _carry_base(curve, near, far)
    return exec_shift(np.sign(raw), shift_n).fillna(0)


def carry_v3_position(curve: pd.DataFrame, window: int = 252, shift_n: int = 1,
                       near: str = "F1", far: str = "F2") -> pd.Series:
    base = _carry_base(curve, near, far)
    if base.empty:
        return pd.Series(dtype=float)
    z = (base - base.rolling(window).mean()) / base.rolling(window).std()
    return exec_shift(np.sign(z.replace([np.inf, -np.inf], np.nan)), shift_n).fillna(0)


def carry_v4_position(curve: pd.DataFrame, horizon: int = 20, shift_n: int = 1,
                       near: str = "F1", far: str = "F2") -> pd.Series:
    base = _carry_base(curve, near, far)
    if base.empty:
        return pd.Series(dtype=float)
    raw = base - base.shift(horizon)
    return exec_shift(np.sign(raw), shift_n).fillna(0)


@st.cache_data(show_spinner="Computing carry Sharpe heatmap...")
def carry_heatmap(curve: pd.DataFrame, contracts: tuple[str, ...], days: int | None, mode: str | None,
                   f1r: pd.Series, f1c: pd.Series, start: str, end: str, shift_n: int) -> pd.DataFrame:
    """Gross Sharpe for every valid (near, far) contract-pair (near before far
    in `contracts`, e.g. F1 before F27), over [start, end].
    `days=None` -> V1 Level signal: sign of the raw (near-far)/near yield.
    `days=N, mode="Momentum"` -> V3 Carry-Momentum: sign of the yield's N-day change.
    `days=N, mode="Zscore"` -> V2 Z-score: sign of (yield - rolling_mean(N)) / rolling_std(N).
    (`mode` is an internal identifier, independent of the V1/V2/V3 numbering
    shown in the UI, so a future renumbering doesn't need to touch this.)
    Gross only (no TC), matching momentum_heatmap's convention -- not needed
    for a heatmap meant to compare shapes across many combinations at a glance.
    Uses a plain per-pair loop rather than momentum_heatmap's raw-numpy
    vectorization: this grid tops out around a few hundred pairs (e.g. 27
    contracts -> 351 pairs), two orders of magnitude smaller than momentum's
    250x250/~31k-pair grid, so the extra vectorization isn't needed here."""
    mask = (f1r.index >= pd.Timestamp(start)) & (f1r.index <= pd.Timestamp(end))
    f1r_w = f1r[mask]
    f1c_w = f1c.reindex(f1r_w.index)
    curve_w = curve[(curve.index >= pd.Timestamp(start)) & (curve.index <= pd.Timestamp(end))]

    rows = []
    for i, near in enumerate(contracts):
        for far in contracts[i + 1:]:
            if days is None:
                pos = carry_v1_position(curve_w, near, far, shift_n=shift_n)
            elif mode == "Zscore":
                pos = carry_v3_position(curve_w, days, shift_n=shift_n, near=near, far=far)
            else:
                pos = carry_v4_position(curve_w, days, shift_n=shift_n, near=near, far=far)
            sharpe = np.nan if pos.empty else pos_metrics_generic(pos, f1r_w, f1c_w)["gross"]
            rows.append({"near": near, "far": far, "sharpe": sharpe})
    return pd.DataFrame(rows)


def render_carry_tab(curve: pd.DataFrame, f1r: pd.Series, f1c: pd.Series, product: str,
                      unit_label: str, key_prefix: str,
                      phase: pd.Series | None = None,
                      default_active_variants: list[str] | None = None,
                      default_feature_variant: str | None = None,
                      skip_front_contract: bool = False):
    """Carry tab: V1-V3 sub-variant selector, equity curve compare, rolling Sharpe,
    signal + position chart, performance metrics, TC filter.

    Renumbered from the original V1-V4 scheme: V1 Roll Yield and V2 Long
    Slope were the identical formula with just a different (near, far)
    pair, so they're merged into one "V1 Level" variant with a free
    Near/Far picker (any pair, not just the two presets each used to
    offer) -- eliminating the old V2 slot. The old V3 Z-score is now V2,
    and the old V4 Carry-Momentum is now V3, closing the gap. Every label
    still spells out which original strategy it is (e.g. "V1 Level (Roll
    Yield / Long Slope)", "V2 Z-score", "V3 Carry-Momentum") so the
    renumbering doesn't create ambiguity about which logic is which.

    `phase` (if passed) adds roll-day TC on top of position-change TC.
    `default_active_variants`/`default_feature_variant` override the
    pre-selected carry variant(s) (falls back to V1 (F1-F2) + V2 (win=252),
    featuring V1, if omitted) -- for products where the near-tenor V1
    definition isn't the appropriate carry signal (e.g. NGL swaps, where
    F1-F2 is dominated by front-of-curve seasonality rather than genuine
    term structure).
    `skip_front_contract=True` shifts every F1/F2-hardcoded default (V1's
    Near/Far picker, V2/V3's near/far base, and the Sharpe Heatmap's
    contract axis) one contract out to start at F2/F3 instead of F1/F2 --
    for NGL swaps specifically, where F1 is a monthly-averaging,
    stale/partial-month price rather than a genuine single-expiry-day
    futures price (see NGL_CONFIG's f1_col/f2_col comment in
    rolling_continuous.py, and the NGL dashboard's own F2-as-front
    convention already applied to its Momentum tab).
    Returns the {label: position} dict of the currently active/chosen
    variants, for the Comparison tab to overlay alongside Momentum/Value."""
    near_default, far_default = ("F2", "F3") if skip_front_contract else ("F1", "F2")

    section_header(f"CARRY — {product}")
    st.caption("Term structure carry: long in backwardation, short in contango. Three variants are "
               "available: V1 Level (Roll Yield / Long Slope, any contract pair), V2 Z-score, "
               "and V3 Carry-Momentum.")

    tc_col, timing_col, _ = st.columns([1, 1, 2])
    with tc_col:
        tc_map = tc_label_map(float(f1r.dropna().iloc[-1]), unit_label)
        tc_label = st.selectbox("Transaction Cost", list(tc_map.keys()), index=1, key=f"{key_prefix}_car_tc")
        tc_bps = tc_map[tc_label]
    with timing_col:
        timing = st.selectbox("Execution Timing", TIMING_OPTIONS, index=1, key=f"{key_prefix}_car_timing")
        shift_n = TIMING_SHIFT[timing]
        if shift_n == 0:
            st.caption("ℹ️ Same Day (Shift-0) enters at Position[t] = Signal[t−1], the earliest a position "
                       "can be established without pairing it with the same-bar return that produced the "
                       "signal, which would introduce look-ahead bias. Lag-1 adds one additional day of "
                       "delay (Signal[t−2]); Lag-2 adds two (Signal[t−3]).")

    # Every contract with real price data, product-agnostic (e.g. F1..F27 for
    # Copper, F1..F20 for Gold) -- shared by the "V1 Level" custom Near/Far
    # pickers below and the Sharpe Heatmap further down, so both draw from the
    # exact same valid-contract list. Same "real data only" filter as the
    # heatmap's own list (a header-only, all-empty far column doesn't count).
    all_contracts = sorted((c for c in curve.columns
                            if c.startswith("F") and c[1:].isdigit() and curve[c].notna().any()),
                           key=lambda c: int(c[1:]))
    if skip_front_contract and "F1" in all_contracts:
        all_contracts.remove("F1")

    V1_LABEL, V2_LABEL, V3_LABEL = "V1 Level (Roll Yield / Long Slope)", "V2 Z-score (252d)", "V3 Carry-Momentum"

    st.markdown("**Add a Carry Variant**")
    st.caption("V1 Level takes any (Near, Far) contract pair -- covers what used to be separate V1 Roll "
               "Yield and V2 Long Slope variants, the identical formula just with a different pair, so "
               "one flow covers both (same unification as the heatmap's \"N/A\" mode below).")
    vcol1, vcol2, vcol3, vcol4 = st.columns([1.3, 1, 1, 0.9])
    with vcol1:
        vgroup = st.selectbox("Variant", [V1_LABEL, V2_LABEL, V3_LABEL], key=f"{key_prefix}_car_vgroup")
    near_sub = far_sub = None
    with vcol2:
        if vgroup == V1_LABEL:
            near_options = all_contracts[:-1] if len(all_contracts) > 1 else all_contracts
            near_idx = near_options.index(near_default) if near_default in near_options else 0
            near_sub = st.selectbox("Near", near_options, index=near_idx, key=f"{key_prefix}_car_near")
        elif vgroup == V3_LABEL:
            sub = st.selectbox("Horizon (days)", [5, 10, 20, 60], index=2, key=f"{key_prefix}_car_sub")
        elif vgroup == V2_LABEL:
            sub = st.selectbox("Window (days)", [126, 252, 504], index=1, key=f"{key_prefix}_car_sub")
    with vcol3:
        if vgroup == V1_LABEL:
            far_options = [c for c in all_contracts if int(c[1:]) > int(near_sub[1:])]
            far_idx = far_options.index(far_default) if far_default in far_options else 0
            # Keyed on near_sub so switching Near always yields a fresh, valid
            # Far list -- a fixed key here could otherwise retain a stale Far
            # selection that isn't in the new (near-dependent) options list.
            far_sub = st.selectbox("Far", far_options, index=far_idx, key=f"{key_prefix}_car_far_{near_sub}")
    with vcol4:
        st.write("")
        st.write("")
        add_clicked = st.button("Add", key=f"{key_prefix}_car_add")

    ss_key = f"{key_prefix}_car_active"
    if ss_key not in st.session_state:
        st.session_state[ss_key] = (list(default_active_variants) if default_active_variants
                                     else [f"V1 ({near_default}-{far_default})", "V2 (win=252)"])

    if add_clicked:
        if vgroup == V1_LABEL:
            label = f"V1 ({near_sub}-{far_sub})"
        elif vgroup == V2_LABEL:
            label = f"V2 (win={sub})"
        else:
            label = f"V3 (N={sub})"
        if label not in st.session_state[ss_key]:
            st.session_state[ss_key] = st.session_state[ss_key] + [label]

    def _build_position(label: str, crv: pd.DataFrame) -> pd.Series:
        # V1 Level (near-far pair) -- the merged former V1 Roll Yield / V2 Long
        # Slope. V2 Z-score / V3 Carry-Momentum keep their original underlying
        # functions (carry_v3_position/carry_v4_position); only the label
        # prefix shown to the user was renumbered to close the V1-V3 gap.
        if label.startswith("V1"):
            pair = label[label.index("(") + 1: label.index(")")]
            a, b = pair.split("-")
            return carry_v1_position(crv, a, b, shift_n=shift_n)
        if label.startswith("V2"):
            win = int(label.split("=")[1].rstrip(")"))
            return carry_v3_position(crv, win, shift_n=shift_n, near=near_default, far=far_default)
        if label.startswith("V3"):
            n = int(label.split("=")[1].rstrip(")"))
            return carry_v4_position(crv, n, shift_n=shift_n, near=near_default, far=far_default)
        return pd.Series(dtype=float)

    chosen = st.multiselect(
        "Active carry variants", options=st.session_state[ss_key], default=st.session_state[ss_key],
        key=f"{key_prefix}_car_multiselect",
    )
    if not chosen:
        st.info("Add at least one carry variant above.")
        return {}

    positions = {label: _build_position(label, curve) for label in chosen}
    positions = {k: v for k, v in positions.items() if not v.empty}
    if not positions:
        st.info("No valid data for the selected carry variant(s).")
        return {}

    # ── Year-range slider: scoped ONLY to Performance Metrics below -- the
    # heatmap has its own independent year-range slider (see below), and the
    # equity curve, rolling Sharpe, and signal/position charts further down
    # keep using the full-history `positions` dict, unaffected by either. ───
    yr0, yr1 = int(f1r.index[0].year), int(f1r.index[-1].year)
    car_yr = st.slider("Year range for performance metrics", yr0, yr1, (yr0, yr1),
                        key=f"{key_prefix}_car_yr")
    range_start, range_end = pd.Timestamp(f"{car_yr[0]}-01-01"), pd.Timestamp(f"{car_yr[1]}-12-31")
    range_mask = (f1r.index >= range_start) & (f1r.index <= range_end)
    f1r_scoped = f1r[range_mask]
    f1c_scoped = f1c.reindex(f1r_scoped.index)
    phase_scoped = phase.reindex(f1r_scoped.index) if phase is not None else None
    curve_scoped = curve[(curve.index >= range_start) & (curve.index <= range_end)]

    # ── Performance Metrics: ONE featured strategy from the active list above,
    # recomputed on the year-scoped curve above -- recomputes when either the
    # feature choice or the year range changes. ──────────────────────────────
    st.markdown("**Performance Metrics**")
    feature_options = list(positions.keys())
    if default_feature_variant and default_feature_variant in feature_options:
        default_feature = default_feature_variant
    elif f"V1 ({near_default}-{far_default})" in feature_options:
        default_feature = f"V1 ({near_default}-{far_default})"
    else:
        default_feature = feature_options[0]
    feature_label = st.selectbox("Strategy to feature", options=feature_options,
                                  index=feature_options.index(default_feature), key=f"{key_prefix}_car_feature")
    feature_pos_scoped = _build_position(feature_label, curve_scoped)
    m = pos_metrics_generic(feature_pos_scoped, f1r_scoped, f1c_scoped, tc_bps, phase_scoped)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Gross Sharpe", _fmt_metric(m["gross"], "{:+.2f}"))
    with c2:
        metric_card("Net Sharpe", _fmt_metric(m["net"], "{:+.2f}"))
    with c3:
        metric_card("Ann PnL (Net)", _fmt_metric(m["ann"], "{:+,.2f}"), unit=f" {unit_label}")
    with c4:
        metric_card("Max DD (Net)", _fmt_metric(m["mdd"], "{:+,.2f}"), unit=f" {unit_label}")
    with c5:
        metric_card("% Flat", _fmt_metric(m["flat_pct"], "{:.0f}"), unit="%")

    st.divider()

    # ── Sharpe Heatmap: every valid (near, far) contract-pair up to whatever
    # far-month the product's own curve data actually has (e.g. F27 for
    # Copper, F15 for Gold) -- not the F15 cap used elsewhere for the Value
    # tab's contract dropdown. "Horizon (days)" defaults to N/A (the plain
    # V1 Level signal); typing a day-count reveals the Mode radio to
    # reinterpret that same number as either V3 Carry-Momentum or V2
    # Z-score, so one grid covers all three variants. Has its OWN
    # independent year-range slider -- not linked to the Performance Metrics
    # slider above or the equity curve's "Time period" slider below. ────────
    st.markdown(f"**Sharpe Heatmap — Contract Pair × Carry Signal**")
    st.caption('"N/A" -> V1 Level signal (long in backwardation, short in contango). Enter a whole '
               "number of days to reinterpret that same horizon as V3 Carry-Momentum or V2 Z-score.")
    hcol1, hcol2 = st.columns([1, 1.4])
    with hcol1:
        days_raw = st.text_input("Horizon (days)", value="N/A", key=f"{key_prefix}_car_hm_days")
    days_clean = days_raw.strip()
    hm_days: int | None = None
    hm_mode: str | None = None
    if days_clean.upper() not in ("N/A", "NA", ""):
        try:
            parsed = int(days_clean)
            if parsed <= 0:
                st.warning("Horizon must be a positive whole number of days -- showing the V1 Level "
                           "signal instead.")
            else:
                hm_days = parsed
        except ValueError:
            st.warning('Enter a whole number of days, or "N/A" for the V1 Level signal -- showing '
                       "V1 Level for now.")
    if hm_days is not None:
        with hcol2:
            mode_label = st.radio("Interpret as", [V3_LABEL, V2_LABEL], horizontal=True,
                                   key=f"{key_prefix}_car_hm_mode")
            hm_mode = "Momentum" if mode_label == V3_LABEL else "Zscore"

    car_hm_yr = st.slider("Year range for heatmap", yr0, yr1, (yr0, yr1), key=f"{key_prefix}_car_hm_yr")

    # `all_contracts` (every real-data contract, F1 already dropped above if
    # skip_front_contract) was computed earlier, shared with the "Add a
    # Carry Variant" Near/Far pickers above.
    hm_df = carry_heatmap(curve, tuple(all_contracts), hm_days, hm_mode, f1r, f1c,
                          f"{car_hm_yr[0]}-01-01", f"{car_hm_yr[1]}-12-31", shift_n)
    if not hm_df.empty and hm_df["sharpe"].notna().any():
        pivot = hm_df.pivot(index="near", columns="far", values="sharpe").reindex(
            index=all_contracts, columns=all_contracts)
        fig_hm = go.Figure(data=go.Heatmap(
            z=pivot.values, x=pivot.columns, y=pivot.index,
            colorscale="RdYlGn", zmid=0, colorbar=dict(title="Sharpe"),
            hovertemplate="Near: %{y}<br>Far: %{x}<br>Sharpe: %{z:.3f}<extra></extra>",
        ))
        if hm_days is None:
            signal_desc = "V1 Level"
        elif hm_mode == "Momentum":
            signal_desc = f"V3 Carry-Momentum ({hm_days}d)"
        else:
            signal_desc = f"V2 Z-score ({hm_days}d)"
        fig_hm.update_layout(**CHART_LAYOUT, height=560,
                             title=dict(text=f"{product} — Carry Sharpe by Contract Pair ({signal_desc})",
                                        font=dict(size=13)),
                             xaxis_title="Far Contract", yaxis_title="Near Contract")
        st.plotly_chart(fig_hm, use_container_width=True, key=f"{key_prefix}_car_hm")
        best = hm_df.loc[hm_df["sharpe"].idxmax()]
        st.caption(f"Best in range {car_hm_yr[0]}-{car_hm_yr[1]}: ({best['near']}, {best['far']}) "
                  f"gross Sharpe {best['sharpe']:+.2f}.")
    else:
        st.info("Not enough data in the selected year range to compute a heatmap.")

    # ── Cumulative PnL and Rolling Sharpe each get their OWN independent
    # strategy selector (defaulting to every active carry variant), so one
    # chart can show a different subset of strategies than the other. ───────
    st.divider()
    _render_equity_curve_with_selector(positions, f1r, f1c, tc_bps, key_prefix + "_car", unit_label, phase=phase)
    st.divider()
    _render_rolling_sharpe_with_selector(positions, f1r, f1c, tc_bps, key_prefix + "_car", phase=phase)
    st.divider()
    _render_signal_position_section(positions, f1r, key_prefix + "_car")
    return positions


# ═══════════════════════════════════════════════════════════════
# VALUE: V1 MA-REVERSION ONLY
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


def _resolve_lookback_days(lb_label: str, lookback_map: dict[str, int]) -> int:
    """Preset labels (e.g. '5yr') resolve via lookback_map; custom entries are
    encoded as 'NNd' (e.g. '45d') by the Value tab's manual-lookback input."""
    if lb_label in lookback_map:
        return lookback_map[lb_label]
    return int(lb_label.rstrip("d"))


@st.cache_data(show_spinner="Computing value Sharpe heatmap...")
def value_heatmap(curve: pd.DataFrame, contracts: tuple[str, ...], lookback_items: tuple[tuple[str, int], ...],
                   threshold: float, f1r: pd.Series, f1c: pd.Series, start: str, end: str,
                   shift_n: int) -> pd.DataFrame:
    """Gross Sharpe for every (contract, lookback) combination, over [start, end],
    at a fixed threshold (selected above the heatmap, not a grid axis -- the
    deviation signal always needs some threshold to fire, unlike Carry's
    optional "N/A" Days mode). `lookback_items` is (label, days) pairs, e.g.
    [("1mo", 20), ...] -- Value's lookbacks are conventionally discrete
    regimes (1mo through 10yr, per the "Add a Value Variant" presets), not a
    continuously-tunable window the way Momentum's MA pairs are, so this uses
    the same preset labels rather than a fine continuous day-count grid.
    Gross only (no TC), matching momentum_heatmap/carry_heatmap's convention.
    Plain per-pair loop, same reasoning as carry_heatmap: this grid is
    similarly small (e.g. 27 contracts x 8 lookbacks = 216 cells)."""
    mask = (f1r.index >= pd.Timestamp(start)) & (f1r.index <= pd.Timestamp(end))
    f1r_w = f1r[mask]
    f1c_w = f1c.reindex(f1r_w.index)
    curve_w = curve[(curve.index >= pd.Timestamp(start)) & (curve.index <= pd.Timestamp(end))]

    rows = []
    for contract in contracts:
        for label, days in lookback_items:
            pos = value_v1_position(curve_w, contract, days, threshold, shift_n=shift_n)
            sharpe = np.nan if pos.empty else pos_metrics_generic(pos, f1r_w, f1c_w)["gross"]
            rows.append({"contract": contract, "lookback": label, "sharpe": sharpe})
    return pd.DataFrame(rows)


def render_value_tab(curve: pd.DataFrame, f1r: pd.Series, f1c: pd.Series, product: str,
                      unit_label: str, key_prefix: str, contracts: list[str] | None = None,
                      phase: pd.Series | None = None,
                      default_active_combo: tuple[str, str, float] | None = None,
                      skip_front_contract: bool = False):
    """Value tab: V1 MA-reversion only, equity curve compare, rolling Sharpe,
    performance metrics, TC filter.
    `phase` (if passed) adds roll-day TC on top of position-change TC.
    `default_active_combo` is a (contract, lookback_label, threshold) tuple
    overriding the pre-selected value variant (falls back to the 8th
    contract / 5yr / 10% if omitted).
    `skip_front_contract=True` drops F1 from both the "Add a Value Variant"
    Contract dropdown and the Sharpe Heatmap's contract axis -- same reason
    as Carry's: for NGL swaps, F1 is a monthly-averaging, stale/partial-month
    price rather than a genuine single-expiry-day futures price (see
    NGL_CONFIG's f1_col/f2_col comment in rolling_continuous.py).
    Returns the {label: position} dict of the currently active/chosen
    variants, for the Comparison tab to overlay alongside Momentum/Carry."""
    section_header(f"VALUE — {product}")
    st.caption("Moving-average reversion: deviation = (Fk − MA_N)/MA_N. Long (+1) when cheap "
               "(below −T), short (−1) when expensive (above +T), flat otherwise. Only the "
               "MA-reversion variant is implemented; the Baz-Granger reversal variant is not included.")

    tc_col, timing_col, _ = st.columns([1, 1, 2])
    with tc_col:
        tc_map = tc_label_map(float(f1r.dropna().iloc[-1]), unit_label)
        tc_label = st.selectbox("Transaction Cost", list(tc_map.keys()), index=1, key=f"{key_prefix}_val_tc")
        tc_bps = tc_map[tc_label]
    with timing_col:
        timing = st.selectbox("Execution Timing", TIMING_OPTIONS, index=2, key=f"{key_prefix}_val_timing")
        shift_n = TIMING_SHIFT[timing]
        if shift_n == 0:
            st.caption("ℹ️ Same Day (Shift-0) enters at Position[t] = Signal[t−1], the earliest a position "
                       "can be established without pairing it with the same-bar return that produced the "
                       "signal, which would introduce look-ahead bias. Lag-1 adds one additional day of "
                       "delay (Signal[t−2]); Lag-2 adds two (Signal[t−3]).")

    if contracts is None:
        contracts = [c for c in curve.columns if c.startswith("F")]
    if skip_front_contract:
        contracts = [c for c in contracts if c != "F1"]

    lookback_map = {"1mo": 20, "1qtr": 60, "6mo": 120, "1yr": 252, "3yr": 756,
                     "5yr": 1260, "7yr": 1764, "10yr": 2520}

    st.markdown("**Add a Value Variant**")
    vcol1, vcol2, vcol3, vcol4 = st.columns([1, 1, 1, 1])
    with vcol1:
        v_contract = st.selectbox("Contract", contracts, index=min(7, len(contracts) - 1),
                                   key=f"{key_prefix}_val_contract")
    with vcol2:
        lb_labels = list(lookback_map.keys()) + ["Custom"]
        v_lb_choice = st.selectbox("Lookback", lb_labels, index=lb_labels.index("5yr"),
                                    key=f"{key_prefix}_val_lb")
        if v_lb_choice == "Custom":
            v_lb_days = st.number_input("Custom lookback (trading days)", min_value=5, max_value=5000,
                                         value=252, step=1, key=f"{key_prefix}_val_lb_custom")
            v_lb_label = f"{int(v_lb_days)}d"
        else:
            v_lb_label = v_lb_choice
    with vcol3:
        thr_options = [0.05, 0.10, 0.15, 0.20, "Custom"]
        v_thr_choice = st.selectbox("Threshold", thr_options, index=1,
                                     format_func=lambda x: f"±{x*100:.0f}%" if isinstance(x, float) else x,
                                     key=f"{key_prefix}_val_thr")
        if v_thr_choice == "Custom":
            v_thr_pct = st.number_input("Custom threshold (%)", min_value=0.5, max_value=100.0,
                                         value=10.0, step=0.5, key=f"{key_prefix}_val_thr_custom")
            v_thr = v_thr_pct / 100.0
        else:
            v_thr = v_thr_choice
    with vcol4:
        st.write("")
        st.write("")
        add_clicked = st.button("Add", key=f"{key_prefix}_val_add")

    ss_key = f"{key_prefix}_val_active"
    default_contract = contracts[min(7, len(contracts) - 1)]
    default_combo = default_active_combo if default_active_combo else (default_contract, "5yr", 0.10)
    if ss_key not in st.session_state:
        st.session_state[ss_key] = [default_combo]

    if add_clicked:
        combo = (v_contract, v_lb_label, v_thr)
        if combo not in st.session_state[ss_key]:
            st.session_state[ss_key] = st.session_state[ss_key] + [combo]

    chosen = st.multiselect(
        "Active value variants", options=st.session_state[ss_key], default=st.session_state[ss_key],
        format_func=lambda c: f"{c[0]} {c[1]} ±{c[2]*100:.0f}%",
        key=f"{key_prefix}_val_multiselect",
    )
    if not chosen:
        st.info("Add at least one value variant above.")
        return {}

    label_to_combo = {f"{c} {lb} ±{thr*100:.0f}%": (c, lb, thr) for c, lb, thr in chosen}
    positions = {
        label: value_v1_position(curve, c, _resolve_lookback_days(lb, lookback_map), thr, shift_n=shift_n)
        for label, (c, lb, thr) in label_to_combo.items()
    }
    positions = {k: v for k, v in positions.items() if not v.empty}
    if not positions:
        st.info("No valid data for the selected value variant(s).")
        return {}

    # ── Year-range slider: scoped ONLY to Performance Metrics below -- the
    # equity curve, rolling Sharpe, and signal/position charts further down
    # keep using the full-history `positions` dict, unaffected by this. ─────
    yr0, yr1 = int(f1r.index[0].year), int(f1r.index[-1].year)
    val_yr = st.slider("Year range for performance metrics", yr0, yr1, (yr0, yr1),
                        key=f"{key_prefix}_val_yr")
    range_start, range_end = pd.Timestamp(f"{val_yr[0]}-01-01"), pd.Timestamp(f"{val_yr[1]}-12-31")
    range_mask = (f1r.index >= range_start) & (f1r.index <= range_end)
    f1r_scoped = f1r[range_mask]
    f1c_scoped = f1c.reindex(f1r_scoped.index)
    phase_scoped = phase.reindex(f1r_scoped.index) if phase is not None else None
    curve_scoped = curve[(curve.index >= range_start) & (curve.index <= range_end)]

    # ── Performance Metrics: ONE featured strategy from the active list above,
    # recomputed on the year-scoped curve above -- recomputes when either the
    # feature choice or the year range changes. ──────────────────────────────
    st.markdown("**Performance Metrics**")
    feature_options = list(positions.keys())
    default_label = f"{default_combo[0]} {default_combo[1]} ±{default_combo[2]*100:.0f}%"
    default_feature = default_label if default_label in feature_options else feature_options[0]
    feature_label = st.selectbox("Strategy to feature", options=feature_options,
                                  index=feature_options.index(default_feature), key=f"{key_prefix}_val_feature")
    v_c, v_lb, v_thr = label_to_combo[feature_label]
    feature_pos_scoped = value_v1_position(curve_scoped, v_c, _resolve_lookback_days(v_lb, lookback_map), v_thr, shift_n=shift_n)
    m = pos_metrics_generic(feature_pos_scoped, f1r_scoped, f1c_scoped, tc_bps, phase_scoped)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Gross Sharpe", _fmt_metric(m["gross"], "{:+.2f}"))
    with c2:
        metric_card("Net Sharpe", _fmt_metric(m["net"], "{:+.2f}"))
    with c3:
        metric_card("Ann PnL (Net)", _fmt_metric(m["ann"], "{:+,.2f}"), unit=f" {unit_label}")
    with c4:
        metric_card("Max DD (Net)", _fmt_metric(m["mdd"], "{:+,.2f}"), unit=f" {unit_label}")
    with c5:
        metric_card("% Flat", _fmt_metric(m["flat_pct"], "{:.0f}"), unit="%")

    st.divider()

    # ── Sharpe Heatmap: Contract x Lookback grid, at a fixed Threshold (not a
    # grid axis -- the deviation signal always needs some threshold to fire,
    # unlike Carry's optional "N/A" Days mode). Contract axis uses every
    # contract with real price data, dynamically capped per product (e.g. F27
    # for Copper) -- not the F15 cap used by "Add a Value Variant" above,
    # same convention as Carry's heatmap. Has its OWN independent year-range
    # slider -- not linked to Performance Metrics above or the equity curve's
    # "Time period" slider below. ─────────────────────────────────────────────
    st.markdown(f"**Sharpe Heatmap — Contract × Lookback**")
    st.caption("Deviation = (Fk − MA_N)/MA_N at a fixed threshold below; long (+1) when cheap, short "
               "(−1) when expensive. Contract and Lookback are the grid; Threshold is a separate "
               "control since the signal always needs one to fire.")
    hm_thr = st.selectbox("Threshold", [0.05, 0.10, 0.15, 0.20], index=1,
                           format_func=lambda x: f"±{x*100:.0f}%", key=f"{key_prefix}_val_hm_thr")

    all_contracts = sorted((c for c in curve.columns
                            if c.startswith("F") and c[1:].isdigit() and curve[c].notna().any()),
                           key=lambda c: int(c[1:]))
    if skip_front_contract and "F1" in all_contracts:
        all_contracts.remove("F1")

    val_hm_yr = st.slider("Year range for heatmap", yr0, yr1, (yr0, yr1), key=f"{key_prefix}_val_hm_yr")

    lookback_items = tuple(lookback_map.items())
    hm_df = value_heatmap(curve, tuple(all_contracts), lookback_items, hm_thr, f1r, f1c,
                          f"{val_hm_yr[0]}-01-01", f"{val_hm_yr[1]}-12-31", shift_n)
    if not hm_df.empty and hm_df["sharpe"].notna().any():
        lb_order = list(lookback_map.keys())
        pivot = hm_df.pivot(index="contract", columns="lookback", values="sharpe").reindex(
            index=all_contracts, columns=lb_order)
        fig_hm = go.Figure(data=go.Heatmap(
            z=pivot.values, x=pivot.columns, y=pivot.index,
            colorscale="RdYlGn", zmid=0, colorbar=dict(title="Sharpe"),
            hovertemplate="Contract: %{y}<br>Lookback: %{x}<br>Sharpe: %{z:.3f}<extra></extra>",
        ))
        fig_hm.update_layout(**CHART_LAYOUT, height=560,
                             title=dict(text=f"{product} — Value Sharpe by Contract × Lookback "
                                             f"(±{hm_thr*100:.0f}%)", font=dict(size=13)),
                             xaxis_title="Lookback", yaxis_title="Contract")
        st.plotly_chart(fig_hm, use_container_width=True, key=f"{key_prefix}_val_hm")
        best = hm_df.loc[hm_df["sharpe"].idxmax()]
        st.caption(f"Best in range {val_hm_yr[0]}-{val_hm_yr[1]}: {best['contract']} / {best['lookback']} "
                  f"gross Sharpe {best['sharpe']:+.2f}.")
    else:
        st.info("Not enough data in the selected year range to compute a heatmap.")

    # ── Cumulative PnL and Rolling Sharpe each get their OWN independent
    # strategy selector (defaulting to every active value variant), so one
    # chart can show a different subset of strategies than the other. ───────
    st.divider()
    _render_equity_curve_with_selector(positions, f1r, f1c, tc_bps, key_prefix + "_val", unit_label, phase=phase)
    st.divider()
    _render_rolling_sharpe_with_selector(positions, f1r, f1c, tc_bps, key_prefix + "_val", phase=phase)
    st.divider()
    _render_signal_position_section(positions, f1r, key_prefix + "_val")
    return positions


# ═══════════════════════════════════════════════════════════════
# SHARED: multi-strategy equity curve + rolling Sharpe + metrics table
# ═══════════════════════════════════════════════════════════════

def _fmt_metric(x, fmt: str) -> str:
    return "N/A" if x is None or (isinstance(x, float) and np.isnan(x)) else fmt.format(x)


def _render_multi_strategy_block(positions: dict[str, pd.Series], f1r: pd.Series, f1c: pd.Series,
                                  tc_bps: int, key_prefix: str, unit_label: str = "/unit",
                                  show_charts: bool = True, show_metrics: bool = True,
                                  phase: pd.Series | None = None):
    """show_charts=False renders ONLY the Performance Metrics section (no
    equity curve / rolling Sharpe / signal & position). show_metrics=False
    renders ONLY the charts (no Performance Metrics) -- for call sites that
    already show a Performance Metrics card/table for this same set of
    strategies elsewhere on the page, so it isn't shown twice. Pass `phase`
    so TC also charges for rolling a held position forward (see
    common_shared.transaction_cost())."""
    if not positions:
        st.info("No valid strategies to display.")
        return

    st.divider()

    # Compute once, up front -- every section below reads from this same
    # pass, so nothing is recomputed and nothing here is hardcoded to a
    # fixed number of strategies: the loop just runs over whatever
    # `positions` holds.
    pnl_cache = {}
    metrics_by_label = {}
    for label, pos in positions.items():
        gross_pnl, net_pnl = daily_returns(pos, f1r, f1c, tc_bps, phase)
        pnl_cache[label] = (gross_pnl, net_pnl)
        metrics_by_label[label] = pos_metrics_generic(pos, f1r, f1c, tc_bps, phase)

    # ── Performance Metrics ───────────────────────────────────────────────
    # Single strategy -> cards (spacious, nothing to compare against).
    # Multiple strategies -> one compact row per strategy in a small table,
    # so comparing several active strategies doesn't take a full card-row
    # each -- scales to however many strategies are actually selected.
    if show_metrics:
        st.markdown("**Performance Metrics**")
        if len(metrics_by_label) == 1:
            label, m = next(iter(metrics_by_label.items()))
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                metric_card("Gross Sharpe", _fmt_metric(m["gross"], "{:+.2f}"))
            with c2:
                metric_card("Net Sharpe", _fmt_metric(m["net"], "{:+.2f}"))
            with c3:
                metric_card("Ann PnL (Net)", _fmt_metric(m["ann"], "{:+,.2f}"), unit=f" {unit_label}")
            with c4:
                metric_card("Max DD (Net)", _fmt_metric(m["mdd"], "{:+,.2f}"), unit=f" {unit_label}")
            with c5:
                metric_card("% Flat", _fmt_metric(m["flat_pct"], "{:.0f}"), unit="%")
        else:
            table_rows = [{
                "Strategy": label,
                "Gross Sharpe": m["gross"], "Net Sharpe": m["net"],
                f"Ann PnL Net ({unit_label})": m["ann"], f"Max DD Net ({unit_label})": m["mdd"],
                "% Flat": m["flat_pct"],
            } for label, m in metrics_by_label.items()]
            mdf = pd.DataFrame(table_rows).set_index("Strategy")
            st.dataframe(
                mdf.style.format({
                    "Gross Sharpe": "{:+.2f}", "Net Sharpe": "{:+.2f}",
                    f"Ann PnL Net ({unit_label})": "{:+,.2f}", f"Max DD Net ({unit_label})": "{:+,.2f}",
                    "% Flat": "{:.0f}",
                }),
                use_container_width=True,
            )

    if not show_charts:
        return

    if show_metrics:
        st.divider()

    # ── Cumulative PnL (Equity Curve) -- its own time-period slider, default
    # = full history; narrowing it re-baselines the curve to 0 at that start
    # date. Reuses pnl_cache's already-computed full-history net PnL (signals
    # stay warmed up on full history; only the displayed/summed window
    # narrows), independent of any "Year range for performance metrics"
    # slider elsewhere on this tab. ──────────────────────────────────────────
    st.markdown(f"**Cumulative PnL (Equity Curve, {unit_label}) — Net of TC**")
    start, end = _time_window_slider(f1r, key_prefix)
    pnl_by_label = {label: net_pnl for label, (gross_pnl, net_pnl) in pnl_cache.items()}
    _plot_equity_curve_from_pnl(pnl_by_label, start, end, key_prefix, unit_label)

    st.markdown("**Rolling Sharpe (252-Day)**")
    basis = st.radio("Basis", ["Gross", "Net of TC"], index=1, horizontal=True, key=f"{key_prefix}_rs_basis")
    fig_rs = go.Figure()
    for i, (label, (gross_pnl, net_pnl)) in enumerate(pnl_cache.items()):
        pnl = net_pnl if basis.startswith("Net") else gross_pnl
        rs = rolling_sharpe(pnl, 252)
        fig_rs.add_trace(go.Scatter(x=rs.index, y=rs.values, mode="lines", name=label,
                                     line=dict(color=_OVERLAY_COLORS[i % len(_OVERLAY_COLORS)], width=1.3)))
    fig_rs.add_hline(y=0, line=dict(color="#555", width=1, dash="dot"))
    fig_rs.update_layout(**CHART_LAYOUT, height=320, yaxis_title="Rolling Sharpe")
    st.plotly_chart(fig_rs, use_container_width=True, key=f"{key_prefix}_rollsharpe")

    # Signal & Position history -- user picks which active strategy to show
    # (the chart is inherently single-strategy: a price + long/short bar
    # panel), matching the Stage 1 Metals dashboard's two-panel style.
    st.markdown("**Signal & Position History**")
    focus_label = st.selectbox("Strategy to display", options=list(positions.keys()),
                                key=f"{key_prefix}_sigpos_focus")
    render_signal_position_chart(positions[focus_label], f1r, focus_label, key_prefix)


def _sync_multiselect_new_options(key: str, options: list[str]) -> None:
    """Keeps a persisted multiselect selection in sync with `options`: any
    label not present the last time this ran (e.g. a variant just added via
    the "Add a ... Variant" button above) is auto-selected, while labels the
    user has deliberately deselected stay deselected. Must run BEFORE the
    widget with this `key` is instantiated -- Streamlit widgets read their
    value from session_state on creation and otherwise ignore `default`
    once that key already exists, which is exactly why newly-added
    strategies previously didn't show up without picking them again."""
    prev_key = f"{key}__prev_options"
    prev_options = st.session_state.get(prev_key, [])
    stored = st.session_state.get(key)
    if stored is None:
        st.session_state[key] = list(options)
    else:
        newly_added = [o for o in options if o not in prev_options]
        kept = [o for o in stored if o in options]
        st.session_state[key] = kept + [o for o in newly_added if o not in kept]
    st.session_state[prev_key] = list(options)


def _time_window_slider(f1r: pd.Series, key_prefix: str,
                         label: str = "Time period for equity curve") -> tuple[pd.Timestamp, pd.Timestamp]:
    """Year-range slider (default = full history) that scopes ONLY the
    equity curve to a sub-period -- independent of any 'Year range for
    performance metrics' slider elsewhere on the same tab (that one recomputes
    signals fresh on truncated price data; this one doesn't touch signals at
    all, see _plot_equity_curve_from_pnl)."""
    yr0, yr1 = int(f1r.index[0].year), int(f1r.index[-1].year)
    win = st.slider(label, yr0, yr1, (yr0, yr1), key=f"{key_prefix}_eqwin_yr")
    return pd.Timestamp(f"{win[0]}-01-01"), pd.Timestamp(f"{win[1]}-12-31")


def _plot_equity_curve_from_pnl(pnl_by_label: dict[str, pd.Series], start: pd.Timestamp, end: pd.Timestamp,
                                 key_prefix: str, unit_label: str = "/unit",
                                 vol_series: pd.Series | None = None):
    """Cumulative PnL restricted to [start, end]. `pnl_by_label` holds each
    strategy's FULL-HISTORY net PnL (already TC-adjusted, computed from the
    complete price series so moving-average/rolling-window signals stay
    properly warmed up) -- this just slices the PnL to the window and cumsums
    from there, so the curve restarts at 0 at the window's start regardless
    of what happened before it. Deliberately NOT slicing the price/position
    series first and recomputing: that would cold-start every rolling signal
    at the window boundary, degrading the first stretch of the chart with an
    artifact that never existed in the actual (full-history) strategy.

    `vol_series` (optional) overlays a rolling-volatility line on a secondary
    right-hand y-axis, sliced to the same [start, end] window -- lets you see
    at a glance whether a strategy's equity curve is moving with, against, or
    independent of the underlying's own volatility regime."""
    fig_eq = go.Figure()
    for i, (label, net_pnl) in enumerate(pnl_by_label.items()):
        pnl_w = net_pnl[(net_pnl.index >= start) & (net_pnl.index <= end)]
        eq = equity_curve(pnl_w)
        fig_eq.add_trace(go.Scatter(x=eq.index, y=eq.values, mode="lines", name=label,
                                     line=dict(color=_OVERLAY_COLORS[i % len(_OVERLAY_COLORS)], width=1.6)))
    layout = dict(CHART_LAYOUT, height=380, yaxis_title=f"Cumulative PnL ({unit_label})")
    if vol_series is not None:
        vol_w = vol_series[(vol_series.index >= start) & (vol_series.index <= end)]
        fig_eq.add_trace(go.Scatter(
            x=vol_w.index, y=vol_w.values, mode="lines", name="Volatility (F1_raw, right axis)",
            line=dict(color="#8A8278", width=1.3, dash="dot"), yaxis="y2",
        ))
        layout["yaxis2"] = dict(title=f"Annualized Vol ({unit_label})", overlaying="y", side="right",
                                 showgrid=False)
        layout["legend"] = dict(CHART_LAYOUT["legend"], orientation="h", y=1.15)
    fig_eq.update_layout(**layout)
    st.plotly_chart(fig_eq, use_container_width=True, key=f"{key_prefix}_equity_chart")


def _plot_rolling_sharpe(positions: dict[str, pd.Series], f1r: pd.Series, f1c: pd.Series,
                          tc_bps: int, key_prefix: str, basis: str = "Net of TC",
                          phase: pd.Series | None = None):
    """Plot-only: rolling 252-day Sharpe for whatever `positions` already
    contains -- no selector of its own. Shared by the per-tab selector
    wrappers below and by the Comparison tab's single unified selector."""
    fig_rs = go.Figure()
    for i, label in enumerate(positions):
        gross_pnl, net_pnl = daily_returns(positions[label], f1r, f1c, tc_bps, phase)
        pnl = net_pnl if basis.startswith("Net") else gross_pnl
        rs = rolling_sharpe(pnl, 252)
        fig_rs.add_trace(go.Scatter(x=rs.index, y=rs.values, mode="lines", name=label,
                                     line=dict(color=_OVERLAY_COLORS[i % len(_OVERLAY_COLORS)], width=1.3)))
    fig_rs.add_hline(y=0, line=dict(color="#555", width=1, dash="dot"))
    fig_rs.update_layout(**CHART_LAYOUT, height=320, yaxis_title="Rolling Sharpe")
    st.plotly_chart(fig_rs, use_container_width=True, key=f"{key_prefix}_rollsharpe_chart")


def _render_equity_curve_with_selector(positions: dict[str, pd.Series], f1r: pd.Series, f1c: pd.Series,
                                        tc_bps: int, key_prefix: str, unit_label: str = "/unit",
                                        phase: pd.Series | None = None):
    """Cumulative PnL (equity curve) with its OWN strategy multiselect,
    independent of whatever is chosen for the Rolling Sharpe chart. Also has
    its own time-period slider (default = full history) directly above the
    chart -- narrowing it re-baselines the curve to 0 at that start date,
    independent of the 'Year range for performance metrics' slider above."""
    st.markdown(f"**Cumulative PnL (Equity Curve, {unit_label}) — Net of TC**")
    options = list(positions.keys())
    _sync_multiselect_new_options(f"{key_prefix}_equity_select", options)
    chosen = st.multiselect("Strategies to show", options=options,
                            key=f"{key_prefix}_equity_select")
    if not chosen:
        st.info("Select at least one strategy above.")
        return
    start, end = _time_window_slider(f1r, key_prefix)
    pnl_by_label = {label: daily_returns(positions[label], f1r, f1c, tc_bps, phase)[1] for label in chosen}
    _plot_equity_curve_from_pnl(pnl_by_label, start, end, key_prefix, unit_label)


def _render_rolling_sharpe_with_selector(positions: dict[str, pd.Series], f1r: pd.Series, f1c: pd.Series,
                                          tc_bps: int, key_prefix: str, phase: pd.Series | None = None):
    """Rolling Sharpe (252-day) with its OWN strategy multiselect,
    independent of whatever is chosen for the Cumulative PnL chart."""
    st.markdown("**Rolling Sharpe (252-Day)**")
    options = list(positions.keys())
    _sync_multiselect_new_options(f"{key_prefix}_rollsharpe_select", options)
    chosen = st.multiselect("Strategies to show", options=options,
                            key=f"{key_prefix}_rollsharpe_select")
    if not chosen:
        st.info("Select at least one strategy above.")
        return

    basis = st.radio("Basis", ["Gross", "Net of TC"], index=1, horizontal=True, key=f"{key_prefix}_rs_basis")
    _plot_rolling_sharpe({k: positions[k] for k in chosen}, f1r, f1c, tc_bps, key_prefix, basis, phase)


def _render_signal_position_section(positions: dict[str, pd.Series], f1r: pd.Series, key_prefix: str):
    """Signal & Position history -- single-strategy view (a price + long/short
    bar panel), so it keeps its own focus selector drawing from the full
    active-strategy list, independent of the equity curve/rolling Sharpe
    selectors above."""
    st.markdown("**Signal & Position History**")
    focus_label = st.selectbox("Strategy to display", options=list(positions.keys()),
                                key=f"{key_prefix}_sigpos_focus")
    render_signal_position_chart(positions[focus_label], f1r, focus_label, key_prefix)


def render_signal_position_chart(pos: pd.Series, f1r: pd.Series, label: str, key_prefix: str):
    """Two-panel chart: F1_raw price (top) + Long/Short position bars (bottom).
    Matches the Stage 1 Metals dashboard's 'Signal & Position' chart exactly."""
    st.divider()
    section_header(f"SIGNAL & POSITION HISTORY — {label}")
    st.caption("Top: F1_raw price. Bottom: the position this strategy actually holds each day "
               "(+1 long, −1 short, 0 flat).")

    pos_w = pos.reindex(f1r.index).fillna(0)
    pos_long = pos_w.where(pos_w > 0, 0.0)
    pos_short = pos_w.where(pos_w < 0, 0.0)

    fig_sig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35], vertical_spacing=0.04)
    fig_sig.add_trace(go.Scatter(
        x=f1r.index, y=f1r.values, name="F1 Price",
        line=dict(color=COLORS["primary"], width=1.5),
        hovertemplate="%{x|%b %d, %Y}<br>F1: %{y:,.2f}<extra></extra>",
    ), row=1, col=1)
    fig_sig.add_trace(go.Bar(
        x=pos_w.index, y=pos_long.values, name="Long (+1)", marker_color="#00E676", opacity=1.0,
        hovertemplate="%{x|%b %d, %Y}<br>Long<extra></extra>",
    ), row=2, col=1)
    fig_sig.add_trace(go.Bar(
        x=pos_w.index, y=pos_short.values, name="Short (-1)", marker_color="#FF1744", opacity=1.0,
        hovertemplate="%{x|%b %d, %Y}<br>Short<extra></extra>",
    ), row=2, col=1)
    fig_sig.update_layout(
        **CHART_LAYOUT, height=500, barmode="overlay",
        title=dict(text=f"{label} — Price & Position", font=dict(size=13)),
        hovermode="x unified", showlegend=True,
    )
    fig_sig.update_yaxes(title_text="F1 Price", row=1, col=1)
    fig_sig.update_yaxes(title_text="Position", tickvals=[-1, 0, 1],
                          ticktext=["Short", "Flat", "Long"], row=2, col=1)
    fig_sig.update_xaxes(showspikes=True, spikecolor="#475569", spikethickness=1, spikemode="across")
    st.plotly_chart(fig_sig, use_container_width=True, key=f"{key_prefix}_sigpos")


# ═══════════════════════════════════════════════════════════════
# COMPARISON: cross-strategy overlay (Momentum + Carry + Value)
# ═══════════════════════════════════════════════════════════════

def render_comparison_tab(f1r: pd.Series, f1c: pd.Series, product: str, unit_label: str,
                           key_prefix: str, strategy_groups: dict[str, dict[str, pd.Series]],
                           phase: pd.Series | None = None):
    """Comparison tab: superimposes whatever strategies are currently active
    (checked) in this product's Momentum, Carry, and Value tabs -- there is
    no separate strategy picker here, it just reads the {label: position}
    dicts those three tabs already return.

    `strategy_groups` looks like {"Momentum": {...}, "Carry": {...},
    "Value": {...}}; each label is prefixed with its group name (e.g.
    "Carry: V1 (F1-F2)") so identically-named variants across groups never
    collide. A single shared multiselect drives BOTH charts below -- unlike
    the per-tab equity/rolling-Sharpe selectors (which are independent of
    each other), removing a strategy here removes it from both at once,
    since the point of this tab is a like-for-like overlay.

    `phase` (if passed) adds roll-day TC on top of position-change TC.

    Also renders an Underlying Volatility chart at the very top, above the
    strategy-comparison charts -- a property of the product's F1_raw (actual
    traded front-month) price itself, independent of any strategy, so it
    always renders even when no strategy is currently active."""
    section_header(f"COMPARISON — {product}")
    st.caption("Overlays every strategy currently selected in the Momentum, Carry, and Value tabs above "
               "-- add or remove strategies below in Momentum/Carry/Value, then come back here to see "
               "them update. One filter controls both charts.")

    st.markdown(f"**Underlying Volatility — {product}**")
    st.caption(f"Rolling annualized volatility of {product}'s daily $ change in F1_raw (the actual traded "
               f"front-month price -- carries roll-day jumps, unlike the back-adjusted F1_continuous used "
               f"for PnL elsewhere), in {unit_label} terms -- a property of the underlying itself, "
               "independent of any strategy or the filter below.")
    vol_window_map = {"21d (1mo)": 21, "63d (1qtr)": 63, "252d (1yr)": 252}
    vol_window_label = st.radio("Window", list(vol_window_map.keys()), index=1, horizontal=True,
                                 key=f"{key_prefix}_cmp_vol_window")
    vol = rolling_price_vol(f1r, vol_window_map[vol_window_label])
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Scatter(
        x=vol.index, y=vol.values, mode="lines", name=f"{product} Volatility",
        line=dict(color=COLORS["secondary"], width=1.4),
    ))
    fig_vol.update_layout(**CHART_LAYOUT, height=300, yaxis_title=f"Annualized Vol ({unit_label})")
    st.plotly_chart(fig_vol, use_container_width=True, key=f"{key_prefix}_cmp_vol_chart")

    st.divider()

    all_positions: dict[str, pd.Series] = {}
    for group_name, group_positions in strategy_groups.items():
        for label, pos in group_positions.items():
            all_positions[f"{group_name}: {label}"] = pos

    if not all_positions:
        st.info("No strategies are currently active -- select at least one in the Momentum, Carry, or "
                "Value tabs above and it will appear here.")
    else:
        tc_col, _ = st.columns([1, 3])
        with tc_col:
            tc_map = tc_label_map(float(f1r.dropna().iloc[-1]), unit_label)
            tc_label = st.selectbox("Transaction Cost", list(tc_map.keys()), index=1, key=f"{key_prefix}_cmp_tc")
            tc_bps = tc_map[tc_label]

        st.markdown("**Strategies to Compare**")
        options = list(all_positions.keys())
        chosen = st.multiselect(
            "Add or remove strategies (drawn from whatever is currently active in Momentum / Carry / Value)",
            options=options, default=options, key=f"{key_prefix}_cmp_select",
        )
        if not chosen:
            st.info("Select at least one strategy above.")
        else:
            positions = {label: all_positions[label] for label in chosen}

            st.divider()
            st.markdown(f"**Cumulative PnL (Equity Curve, {unit_label}) — Net of TC**")
            start, end = _time_window_slider(f1r, key_prefix + "_cmp")
            show_vol_overlay = st.checkbox(
                f"Superimpose Volatility ({vol_window_label} window, from the chart above)",
                key=f"{key_prefix}_cmp_vol_overlay",
            )
            pnl_by_label = {label: daily_returns(positions[label], f1r, f1c, tc_bps, phase)[1]
                            for label in positions}
            _plot_equity_curve_from_pnl(pnl_by_label, start, end, key_prefix + "_cmp", unit_label,
                                        vol_series=vol if show_vol_overlay else None)

            st.divider()
            st.markdown("**Rolling Sharpe (252-Day)**")
            basis = st.radio("Basis", ["Gross", "Net of TC"], index=1, horizontal=True,
                              key=f"{key_prefix}_cmp_rs_basis")
            _plot_rolling_sharpe(positions, f1r, f1c, tc_bps, key_prefix + "_cmp", basis, phase)
