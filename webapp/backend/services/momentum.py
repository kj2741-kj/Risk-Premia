"""
Adapter: HTTP-primitive params -> common_engine.py's existing pure functions
-> JSON-safe response.

No math is reimplemented here. Every formula (ma_crossover_position,
momentum_heatmap, daily_returns, pos_metrics_generic, ...) is a direct call
into common_engine.py / common_shared.py, so the numbers are guaranteed
identical to the live Streamlit dashboards -- this file only replaces
st.slider/st.selectbox param-reading with function arguments, and
st.plotly_chart(fig) with fig serialized to JSON, mirroring
common_engine.render_momentum_tab()'s body section by section.
"""

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from common_engine import daily_returns, equity_curve, ma_crossover_position, momentum_heatmap, rolling_sharpe
from common_shared import CHART_LAYOUT, COLORS, pos_metrics_generic

from cache import load_series
from config_registry import get_asset_config, get_product_code

_OVERLAY_COLORS = [COLORS["primary"], COLORS["green"], COLORS["secondary"],
                   "#A78BFA", "#F472B6", "#22D3EE", "#FB923C", "#60A5FA"]

DEFAULT_PAIRS: list[tuple[int, int]] = [(1, 20), (5, 60), (20, 250)]


def _clean(x):
    if isinstance(x, (float, np.floating)):
        return None if np.isnan(x) else float(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    return x


def _clean_metrics(m: dict) -> dict:
    return {k: _clean(v) for k, v in m.items()}


def _series_to_json(s: pd.Series) -> dict:
    s = s.dropna()
    return {"dates": [d.strftime("%Y-%m-%d") for d in s.index], "values": [float(v) for v in s.to_numpy()]}


def _fig_to_json(fig: go.Figure) -> dict:
    # plotly.io.to_json (not fig.to_dict()) handles numpy arrays / NaN / datetime
    # correctly; round-tripping through json.loads gives a plain, JSON-safe dict.
    return json.loads(pio.to_json(fig))


def _load(asset_class: str, product: str, roll_method: str, roll_n: int):
    code = get_product_code(asset_class, product)
    f1_df, curve = load_series(asset_class, code, roll_method, roll_n)
    return f1_df["F1_raw"], f1_df["F1_continuous"], f1_df["Phase"], curve


def get_momentum(
    asset_class: str, product: str, *,
    roll_method: str = "ltd", roll_n: int = 5,
    tc_bps: int = 5, shift_n: int = 1,
    pairs: list[tuple[int, int]] | None = None,
    metrics_year_start: int | None = None, metrics_year_end: int | None = None,
    feature_pair: tuple[int, int] | None = None,
    equity_year_start: int | None = None, equity_year_end: int | None = None,
    focus_pair: tuple[int, int] | None = None,
    rs_basis: str = "net",
) -> dict:
    f1r, f1c, phase, _curve = _load(asset_class, product, roll_method, roll_n)
    ac = get_asset_config(asset_class)
    unit_label = ac["products"][product]["unit"]

    pairs = pairs or list(DEFAULT_PAIRS)
    yr0, yr1 = int(f1r.index[0].year), int(f1r.index[-1].year)
    metrics_year_start = metrics_year_start or yr0
    metrics_year_end = metrics_year_end or yr1
    equity_year_start = equity_year_start or yr0
    equity_year_end = equity_year_end or yr1

    # Per-product override of which default pair is initially featured (e.g.
    # NGL's momentum_default_feature) -- never adds a new pair, only changes
    # which already-active one is pre-selected, mirroring
    # render_momentum_tab's default_feature_pair kwarg exactly.
    code = get_product_code(asset_class, product)
    config_default_feature = ac.get("momentum_default_feature", {}).get(code)
    if feature_pair not in pairs:
        if config_default_feature and tuple(config_default_feature) in pairs:
            feature_pair = tuple(config_default_feature)
        elif (1, 20) in pairs:
            feature_pair = (1, 20)
        else:
            feature_pair = pairs[0]
    focus_pair = focus_pair if focus_pair in pairs else feature_pair

    # ── Performance Metrics: one featured pair, year-scoped (mirrors the
    # "Year range for performance metrics / heatmap" slider in the Streamlit tab). ──
    range_start = pd.Timestamp(f"{metrics_year_start}-01-01")
    range_end = pd.Timestamp(f"{metrics_year_end}-12-31")
    range_mask = (f1r.index >= range_start) & (f1r.index <= range_end)
    f1r_scoped = f1r[range_mask]
    f1c_scoped = f1c.reindex(f1r_scoped.index)
    phase_scoped = phase.reindex(f1r_scoped.index)

    f_fast, f_slow = feature_pair
    if len(f1r_scoped) < f_slow + 20:
        metrics = None
    else:
        feature_pos = ma_crossover_position(f1r_scoped, f_fast, f_slow, shift_n=shift_n)
        metrics = _clean_metrics(pos_metrics_generic(feature_pos, f1r_scoped, f1c_scoped, tc_bps, phase_scoped))

    # ── Full-history positions for every active pair (equity curve / rolling
    # Sharpe / signal-position all read from this, unscoped by year range). ──
    positions = {f"MA({f},{s})": ma_crossover_position(f1r, f, s, shift_n=shift_n) for f, s in pairs}

    # ── Cumulative PnL (Equity Curve): net PnL computed on full history,
    # THEN sliced to [equity_year_start, equity_year_end] and re-cumsummed --
    # narrowing the window re-baselines to 0, it does not cold-start signals. ──
    eq_start = pd.Timestamp(f"{equity_year_start}-01-01")
    eq_end = pd.Timestamp(f"{equity_year_end}-12-31")
    fig_eq = go.Figure()
    for i, (label, pos) in enumerate(positions.items()):
        _, net_pnl = daily_returns(pos, f1r, f1c, tc_bps, phase)
        pnl_w = net_pnl[(net_pnl.index >= eq_start) & (net_pnl.index <= eq_end)]
        eq = equity_curve(pnl_w)
        fig_eq.add_trace(go.Scatter(x=eq.index, y=eq.values, mode="lines", name=label,
                                     line=dict(color=_OVERLAY_COLORS[i % len(_OVERLAY_COLORS)], width=1.6)))
    fig_eq.update_layout(**CHART_LAYOUT, height=380, yaxis_title=f"Cumulative PnL ({unit_label})")

    # ── Rolling Sharpe (252-Day) ──────────────────────────────────────────
    fig_rs = go.Figure()
    for i, (label, pos) in enumerate(positions.items()):
        gross_pnl, net_pnl = daily_returns(pos, f1r, f1c, tc_bps, phase)
        pnl = net_pnl if rs_basis == "net" else gross_pnl
        rs = rolling_sharpe(pnl, 252)
        fig_rs.add_trace(go.Scatter(x=rs.index, y=rs.values, mode="lines", name=label,
                                     line=dict(color=_OVERLAY_COLORS[i % len(_OVERLAY_COLORS)], width=1.3)))
    fig_rs.add_hline(y=0, line=dict(color="#555", width=1, dash="dot"))
    fig_rs.update_layout(**CHART_LAYOUT, height=320, yaxis_title="Rolling Sharpe")

    # ── Signal & Position History: single focused strategy ────────────────
    focus_label = f"MA({focus_pair[0]},{focus_pair[1]})"
    pos_w = positions[focus_label].reindex(f1r.index).fillna(0)
    pos_long = pos_w.where(pos_w > 0, 0.0)
    pos_short = pos_w.where(pos_w < 0, 0.0)
    fig_sig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35], vertical_spacing=0.04)
    fig_sig.add_trace(go.Scatter(
        x=f1r.index, y=f1r.values, name="F1 Price", line=dict(color=COLORS["primary"], width=1.5),
        hovertemplate="%{x|%b %d, %Y}<br>F1: %{y:,.2f}<extra></extra>",
    ), row=1, col=1)
    fig_sig.add_trace(go.Bar(
        x=pos_w.index, y=pos_long.values, name="Long (+1)", marker_color="#00E676",
        hovertemplate="%{x|%b %d, %Y}<br>Long<extra></extra>",
    ), row=2, col=1)
    fig_sig.add_trace(go.Bar(
        x=pos_w.index, y=pos_short.values, name="Short (-1)", marker_color="#FF1744",
        hovertemplate="%{x|%b %d, %Y}<br>Short<extra></extra>",
    ), row=2, col=1)
    fig_sig.update_layout(**CHART_LAYOUT, height=500, barmode="overlay",
                           title=dict(text=f"{focus_label} — Price & Position", font=dict(size=13)),
                           hovermode="x unified", showlegend=True)
    fig_sig.update_yaxes(title_text="F1 Price", row=1, col=1)
    fig_sig.update_yaxes(title_text="Position", tickvals=[-1, 0, 1],
                          ticktext=["Short", "Flat", "Long"], row=2, col=1)
    fig_sig.update_xaxes(showspikes=True, spikecolor="#475569", spikethickness=1, spikemode="across")

    return {
        "year_range": {"min": yr0, "max": yr1},
        "unit_label": unit_label,
        "active_pairs": [list(p) for p in pairs],
        "feature_pair": list(feature_pair),
        "focus_pair": list(focus_pair),
        "metrics": metrics,
        "equity_curve_fig": _fig_to_json(fig_eq),
        "rolling_sharpe_fig": _fig_to_json(fig_rs),
        "signal_position_fig": _fig_to_json(fig_sig),
        "positions": {label: _series_to_json(pos) for label, pos in positions.items()},
    }


def get_momentum_heatmap(
    asset_class: str, product: str, *,
    roll_method: str = "ltd", roll_n: int = 5,
    tc_bps: int = 5, shift_n: int = 1,
    year_start: int | None = None, year_end: int | None = None,
    max_window: int = 250,
) -> dict:
    f1r, f1c, _phase, _curve = _load(asset_class, product, roll_method, roll_n)
    yr0, yr1 = int(f1r.index[0].year), int(f1r.index[-1].year)
    year_start, year_end = year_start or yr0, year_end or yr1

    # momentum_heatmap is @st.cache_data-wrapped in common_engine.py -- its
    # own hasher handles the f1r/f1c Series args correctly, so this call is
    # already cached; no separate cache layer needed here (see cache.py's
    # module docstring for why that's *not* true of the load_series step above).
    hm_df = momentum_heatmap(f1r, f1c, max_window, f"{year_start}-01-01", f"{year_end}-12-31", shift_n, tc_bps)
    if hm_df.empty or not hm_df["sharpe"].notna().any():
        return {"fig": None, "plot_config": {"scrollZoom": True}, "best": None}

    pivot = hm_df.pivot(index="fast", columns="slow", values="sharpe")
    fig_hm = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index, colorscale="RdYlGn", zmid=0,
        colorbar=dict(title="Sharpe"),
        hovertemplate="Fast MA: %{y}<br>Slow MA: %{x}<br>Sharpe: %{z:.3f}<extra></extra>",
    ))
    fig_hm.update_layout(**CHART_LAYOUT, height=560, dragmode="zoom",
                          title=dict(text=f"{product} — Sharpe by MA Crossover", font=dict(size=13)),
                          xaxis_title="Slow MA", yaxis_title="Fast MA")
    fig_hm.update_xaxes(rangeslider=dict(visible=False))

    best = hm_df.loc[hm_df["sharpe"].idxmax()]
    return {
        "fig": _fig_to_json(fig_hm),
        "plot_config": {"scrollZoom": True},
        "best": {"fast": int(best["fast"]), "slow": int(best["slow"]), "sharpe": float(best["sharpe"])},
    }
