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
only (no CTA/Baz-Granger, no structural Anchors), Carry V1-V4, Value
V1 MA-reversion only. No OOS / walk-forward yet -- in-sample only.

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

from common_shared import CHART_LAYOUT, COLORS, pos_metrics_generic, section_header, tc_label_map

_OVERLAY_COLORS = [COLORS["primary"], COLORS["green"], COLORS["secondary"],
                   "#A78BFA", "#F472B6", "#22D3EE", "#FB923C", "#60A5FA"]


# ═══════════════════════════════════════════════════════════════
# GENERIC RETURN / EQUITY / ROLLING-SHARPE HELPERS
# ═══════════════════════════════════════════════════════════════

def daily_returns(pos: pd.Series, f1r: pd.Series, f1c: pd.Series, tc_bps: int) -> tuple[pd.Series, pd.Series]:
    """Gross and net daily $PnL (native unit, e.g. USD/MT) for a position series.
    Dollar terms, not %-of-notional -- %-of-notional requires dividing by
    F1_continuous[t-1], which can be zero/negative (confirmed for Aluminium, WTI,
    Nat Gas, Fuel Oil), silently flipping return signs or inflating magnitudes."""
    pos = pos.reindex(f1c.index).fillna(0.0)
    gp = pos * f1c.diff()
    chg = pos.diff().abs()
    if len(chg):
        chg.iloc[0] = abs(pos.iloc[0])
    tc = chg * (tc_bps / 10000.0 / 2.0) * f1r.reindex(f1c.index)
    net = gp - tc
    return gp, net


def equity_curve(pnl: pd.Series) -> pd.Series:
    """Cumulative $PnL path (native unit, e.g. USD/MT)."""
    return pnl.fillna(0).cumsum()


def rolling_sharpe(pnl: pd.Series, window: int = 252) -> pd.Series:
    """Rolling Sharpe from a $PnL series (dimensionless -- $ cancels in the ratio)."""
    r = pnl.fillna(0)
    return r.rolling(window).mean() / r.rolling(window).std() * np.sqrt(252)


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
                         key_prefix: str, heatmap_max_window: int = 250):
    """Momentum tab: heatmap w/ year-range toggle, 3 default benchmark MAs + custom MA,
    multi-strategy equity curve, rolling Sharpe, performance metrics, TC filter."""
    yr0, yr1 = int(f1r.index[0].year), int(f1r.index[-1].year)

    section_header(f"MOMENTUM — {product}")
    st.caption("MA crossover: signal(t) = sign[ MA(F1_raw, fast) − MA(F1_raw, slow) ]. "
               "No CTA/Baz-Granger, no Anchors — Stage 2 scope.")

    tc_col, timing_col, _ = st.columns([1, 1, 2])
    with tc_col:
        tc_map = tc_label_map(float(f1r.dropna().iloc[-1]), unit_label)
        tc_label = st.selectbox("Transaction Cost", list(tc_map.keys()), index=1, key=f"{key_prefix}_mom_tc")
        tc_bps = tc_map[tc_label]
    with timing_col:
        timing = st.selectbox("Execution Timing", TIMING_OPTIONS, index=1, key=f"{key_prefix}_mom_timing")
        shift_n = TIMING_SHIFT[timing]
        if shift_n == 0:
            st.caption("ℹ️ Same Day (Shift-0) enters at Position[t] = Signal[t-1] -- the fastest a position "
                       "can legitimately go live, since pairing it with Signal[t]'s own same-bar return would "
                       "be a look-ahead leak. Lag-1 adds one more day of delay (Signal[t-2]), Lag-2 adds two (Signal[t-3]).")

    # ── Shared year-range toggle (drives both the drill-down below and the heatmap) ──
    hm_yr = st.slider("Year range for heatmap / drill-down", yr0, yr1, (yr0, yr1), key=f"{key_prefix}_mom_hm_yr")
    range_start, range_end = pd.Timestamp(f"{hm_yr[0]}-01-01"), pd.Timestamp(f"{hm_yr[1]}-12-31")
    range_mask = (f1r.index >= range_start) & (f1r.index <= range_end)
    f1r_scoped = f1r[range_mask]
    f1c_scoped = f1c.reindex(f1r_scoped.index)

    # ── Drill-down: analyze one specific MA pair, scoped to the year range above ──
    st.markdown("**Analyze a Specific MA Pair (scoped to the year range above)**")
    st.caption("Pick any Fast/Slow pair -- same MA crossover math as the heatmap below, computed only "
               "over the selected year range (identical scoping to the heatmap itself, so the Sharpe here "
               "lines up with that pair's heatmap cell).")
    dcol1, dcol2, _ = st.columns([1, 1, 2])
    with dcol1:
        df_fast = st.number_input("Fast", min_value=1, max_value=heatmap_max_window, value=1,
                                   key=f"{key_prefix}_mom_drill_fast")
    with dcol2:
        df_slow = st.number_input("Slow", min_value=2, max_value=heatmap_max_window, value=20,
                                   key=f"{key_prefix}_mom_drill_slow")
    if df_slow <= df_fast:
        st.warning("Slow MA must be greater than Fast MA.")
    elif len(f1r_scoped) < df_slow + 20:
        st.info("Not enough data in the selected year range for this pair.")
    else:
        drill_label = f"MA({int(df_fast)},{int(df_slow)}) [{hm_yr[0]}-{hm_yr[1]}]"
        _render_multi_strategy_block(
            {drill_label: ma_crossover_position(f1r_scoped, int(df_fast), int(df_slow), shift_n=shift_n)},
            f1r_scoped, f1c_scoped, tc_bps, key_prefix + "_mom_drill", unit_label,
        )

    st.divider()

    # ── Heatmap with year-range toggle ──────────────────────────────────────
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

    st.divider()

    # ── Strategy selection: 3 default benchmarks + custom ───────────────────
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
        "Active strategies (equity curve / rolling Sharpe / metrics below)",
        options=active, default=active,
        format_func=lambda p: f"MA({p[0]},{p[1]})",
        key=f"{key_prefix}_mom_multiselect",
    )

    if not chosen:
        st.info("Select at least one strategy above.")
        return

    _render_multi_strategy_block(
        {f"MA({f},{s})": ma_crossover_position(f1r, f, s, shift_n=shift_n) for f, s in chosen},
        f1r, f1c, tc_bps, key_prefix + "_mom", unit_label,
    )


# ═══════════════════════════════════════════════════════════════
# CARRY: V1 ROLL YIELD, V2 LONG SLOPE, V3 Z-SCORE, V4 CARRY-MOMENTUM
# ═══════════════════════════════════════════════════════════════

def _carry_base(curve: pd.DataFrame, a: str, b: str) -> pd.Series:
    if a not in curve.columns or b not in curve.columns:
        return pd.Series(dtype=float)
    fa, fb = curve[a].dropna(), curve[b].dropna()
    idx = fa.index.intersection(fb.index)
    return ((fa.reindex(idx) - fb.reindex(idx)) / fa.reindex(idx)).replace([np.inf, -np.inf], np.nan).dropna()


def carry_v1_position(curve: pd.DataFrame, near: str = "F1", far: str = "F2", shift_n: int = 1) -> pd.Series:
    raw = _carry_base(curve, near, far)
    return exec_shift(np.sign(raw), shift_n).fillna(0)


def carry_v2_position(curve: pd.DataFrame, j: str, k: str, shift_n: int = 1) -> pd.Series:
    return carry_v1_position(curve, j, k, shift_n)


def carry_v3_position(curve: pd.DataFrame, window: int = 252, shift_n: int = 1) -> pd.Series:
    base = _carry_base(curve, "F1", "F2")
    if base.empty:
        return pd.Series(dtype=float)
    z = (base - base.rolling(window).mean()) / base.rolling(window).std()
    return exec_shift(np.sign(z.replace([np.inf, -np.inf], np.nan)), shift_n).fillna(0)


def carry_v4_position(curve: pd.DataFrame, horizon: int = 20, shift_n: int = 1) -> pd.Series:
    base = _carry_base(curve, "F1", "F2")
    if base.empty:
        return pd.Series(dtype=float)
    raw = base - base.shift(horizon)
    return exec_shift(np.sign(raw), shift_n).fillna(0)


def render_carry_tab(curve: pd.DataFrame, f1r: pd.Series, f1c: pd.Series, product: str,
                      unit_label: str, key_prefix: str, tenor_pairs: list[tuple[str, str]] | None = None):
    """Carry tab: V1-V4 sub-variant selector, equity curve compare, rolling Sharpe,
    signal + position chart, performance metrics, TC filter."""
    section_header(f"CARRY — {product}")
    st.caption("Term structure carry: long in backwardation, short in contango. "
               "V1 Roll Yield, V2 Long Slope, V3 Z-score, V4 Carry-Momentum. Stage 2 scope.")

    tc_col, timing_col, _ = st.columns([1, 1, 2])
    with tc_col:
        tc_map = tc_label_map(float(f1r.dropna().iloc[-1]), unit_label)
        tc_label = st.selectbox("Transaction Cost", list(tc_map.keys()), index=1, key=f"{key_prefix}_car_tc")
        tc_bps = tc_map[tc_label]
    with timing_col:
        timing = st.selectbox("Execution Timing", TIMING_OPTIONS, index=1, key=f"{key_prefix}_car_timing")
        shift_n = TIMING_SHIFT[timing]
        if shift_n == 0:
            st.caption("ℹ️ Same Day (Shift-0) enters at Position[t] = Signal[t-1] -- the fastest a position "
                       "can legitimately go live, since pairing it with Signal[t]'s own same-bar return would "
                       "be a look-ahead leak. Lag-1 adds one more day of delay (Signal[t-2]), Lag-2 adds two (Signal[t-3]).")

    if tenor_pairs is None:
        tenor_pairs = [("F3", "F15"), ("F6", "F18"), ("F9", "F21"), ("F12", "F24")]

    st.markdown("**Add a Carry Variant**")
    vcol1, vcol2, vcol3 = st.columns([1.2, 1.6, 1])
    with vcol1:
        vgroup = st.selectbox("Variant", ["V1 Roll Yield (F1-F2)", "V2 Long Slope", "V3 Z-score (252d)",
                                          "V4 Carry-Momentum"], key=f"{key_prefix}_car_vgroup")
    with vcol2:
        if vgroup == "V2 Long Slope":
            sub = st.selectbox("Tenor pair", [f"{a}-{b}" for a, b in tenor_pairs], key=f"{key_prefix}_car_sub")
        elif vgroup == "V4 Carry-Momentum":
            sub = st.selectbox("Horizon (days)", [5, 10, 20, 60], index=2, key=f"{key_prefix}_car_sub")
        elif vgroup == "V3 Z-score (252d)":
            sub = st.selectbox("Window (days)", [126, 252, 504], index=1, key=f"{key_prefix}_car_sub")
        else:
            sub = st.selectbox("Pair", ["F1-F2", "F1-F3"], key=f"{key_prefix}_car_sub")
    with vcol3:
        st.write("")
        st.write("")
        add_clicked = st.button("Add", key=f"{key_prefix}_car_add")

    ss_key = f"{key_prefix}_car_active"
    if ss_key not in st.session_state:
        st.session_state[ss_key] = ["V1 (F1-F2)", "V3 (win=252)"]

    if add_clicked:
        label = {
            "V1 Roll Yield (F1-F2)": f"V1 ({sub})",
            "V2 Long Slope": f"V2 ({sub})",
            "V3 Z-score (252d)": f"V3 (win={sub})",
            "V4 Carry-Momentum": f"V4 (N={sub})",
        }[vgroup]
        if label not in st.session_state[ss_key]:
            st.session_state[ss_key] = st.session_state[ss_key] + [label]

    def _build_position(label: str) -> pd.Series:
        if label.startswith("V1"):
            pair = label[label.index("(") + 1: label.index(")")]
            a, b = pair.split("-")
            return carry_v1_position(curve, a, b, shift_n=shift_n)
        if label.startswith("V2"):
            pair = label[label.index("(") + 1: label.index(")")]
            a, b = pair.split("-")
            return carry_v2_position(curve, a, b, shift_n=shift_n)
        if label.startswith("V3"):
            win = int(label.split("=")[1].rstrip(")"))
            return carry_v3_position(curve, win, shift_n=shift_n)
        if label.startswith("V4"):
            n = int(label.split("=")[1].rstrip(")"))
            return carry_v4_position(curve, n, shift_n=shift_n)
        return pd.Series(dtype=float)

    chosen = st.multiselect(
        "Active carry variants", options=st.session_state[ss_key], default=st.session_state[ss_key],
        key=f"{key_prefix}_car_multiselect",
    )
    if not chosen:
        st.info("Add at least one carry variant above.")
        return

    positions = {label: _build_position(label) for label in chosen}
    positions = {k: v for k, v in positions.items() if not v.empty}

    _render_multi_strategy_block(positions, f1r, f1c, tc_bps, key_prefix + "_car", unit_label)


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
    ma = fk.rolling(lookback, min_periods=max(lookback // 2, 60)).mean()
    dev = ((fk - ma) / ma.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).dropna()
    sig = pd.Series(np.where(dev.values < -threshold, 1.0, np.where(dev.values > threshold, -1.0, 0.0)),
                     index=dev.index)
    return exec_shift(sig, shift_n).fillna(0)


def render_value_tab(curve: pd.DataFrame, f1r: pd.Series, f1c: pd.Series, product: str,
                      unit_label: str, key_prefix: str, contracts: list[str] | None = None):
    """Value tab: V1 MA-reversion only, equity curve compare, rolling Sharpe,
    performance metrics, TC filter."""
    section_header(f"VALUE — {product}")
    st.caption("MA-reversion: deviation = (Fk − MA_N)/MA_N. +1 if cheap (< −T), −1 if expensive (> +T), "
               "0 otherwise. Stage 2 scope: V1 MA-reversion only, no Baz-Granger reversal.")

    tc_col, timing_col, _ = st.columns([1, 1, 2])
    with tc_col:
        tc_map = tc_label_map(float(f1r.dropna().iloc[-1]), unit_label)
        tc_label = st.selectbox("Transaction Cost", list(tc_map.keys()), index=1, key=f"{key_prefix}_val_tc")
        tc_bps = tc_map[tc_label]
    with timing_col:
        timing = st.selectbox("Execution Timing", TIMING_OPTIONS, index=2, key=f"{key_prefix}_val_timing")
        shift_n = TIMING_SHIFT[timing]
        if shift_n == 0:
            st.caption("ℹ️ Same Day (Shift-0) enters at Position[t] = Signal[t-1] -- the fastest a position "
                       "can legitimately go live, since pairing it with Signal[t]'s own same-bar return would "
                       "be a look-ahead leak. Lag-1 adds one more day of delay (Signal[t-2]), Lag-2 adds two (Signal[t-3]).")

    if contracts is None:
        contracts = [c for c in curve.columns if c.startswith("F")]

    lookback_map = {"1yr": 252, "3yr": 756, "5yr": 1260, "7yr": 1764, "10yr": 2520}

    st.markdown("**Add a Value Variant**")
    vcol1, vcol2, vcol3, vcol4 = st.columns([1, 1, 1, 1])
    with vcol1:
        v_contract = st.selectbox("Contract", contracts, index=min(7, len(contracts) - 1),
                                   key=f"{key_prefix}_val_contract")
    with vcol2:
        v_lb_label = st.selectbox("Lookback", list(lookback_map.keys()), index=2, key=f"{key_prefix}_val_lb")
    with vcol3:
        v_thr = st.selectbox("Threshold", [0.05, 0.10, 0.15, 0.20], index=1,
                              format_func=lambda x: f"±{x*100:.0f}%", key=f"{key_prefix}_val_thr")
    with vcol4:
        st.write("")
        st.write("")
        add_clicked = st.button("Add", key=f"{key_prefix}_val_add")

    ss_key = f"{key_prefix}_val_active"
    default_contract = contracts[min(7, len(contracts) - 1)]
    if ss_key not in st.session_state:
        st.session_state[ss_key] = [(default_contract, "5yr", 0.10)]

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
        return

    positions = {
        f"{c} {lb} ±{thr*100:.0f}%": value_v1_position(curve, c, lookback_map[lb], thr, shift_n=shift_n)
        for c, lb, thr in chosen
    }
    positions = {k: v for k, v in positions.items() if not v.empty}

    _render_multi_strategy_block(positions, f1r, f1c, tc_bps, key_prefix + "_val", unit_label)


# ═══════════════════════════════════════════════════════════════
# SHARED: multi-strategy equity curve + rolling Sharpe + metrics table
# ═══════════════════════════════════════════════════════════════

def _render_multi_strategy_block(positions: dict[str, pd.Series], f1r: pd.Series, f1c: pd.Series,
                                  tc_bps: int, key_prefix: str, unit_label: str = "/unit"):
    if not positions:
        st.info("No valid strategies to display.")
        return

    st.divider()
    st.markdown(f"**Cumulative PnL (Equity Curve, {unit_label}) — Net of TC**")
    fig_eq = go.Figure()
    metrics_rows = []
    pnl_cache = {}
    for i, (label, pos) in enumerate(positions.items()):
        gross_pnl, net_pnl = daily_returns(pos, f1r, f1c, tc_bps)
        pnl_cache[label] = (gross_pnl, net_pnl)
        eq = equity_curve(net_pnl)
        fig_eq.add_trace(go.Scatter(x=eq.index, y=eq.values, mode="lines", name=label,
                                     line=dict(color=_OVERLAY_COLORS[i % len(_OVERLAY_COLORS)], width=1.6)))
        m = pos_metrics_generic(pos, f1r, f1c, tc_bps)
        metrics_rows.append({
            "Strategy": label, "Gross Sharpe": m["gross"], "Net Sharpe": m["net"],
            f"Ann PnL ({unit_label})": m["ann"], f"Max DD ({unit_label})": m["mdd"], "% Flat": m["flat_pct"],
        })
    fig_eq.update_layout(**CHART_LAYOUT, height=380, yaxis_title=f"Cumulative PnL ({unit_label})")
    st.plotly_chart(fig_eq, use_container_width=True, key=f"{key_prefix}_equity")

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

    st.markdown("**Performance Metrics**")
    mdf = pd.DataFrame(metrics_rows).set_index("Strategy")
    st.dataframe(
        mdf.style.format({
            "Gross Sharpe": "{:+.2f}", "Net Sharpe": "{:+.2f}",
            f"Ann PnL ({unit_label})": "{:+,.2f}", f"Max DD ({unit_label})": "{:+,.2f}", "% Flat": "{:.0f}",
        }),
        use_container_width=True,
    )

    # Signal & Position history -- user picks which active strategy to show
    # (the chart is inherently single-strategy: a price + long/short bar
    # panel), matching the Stage 1 Metals dashboard's two-panel style.
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
