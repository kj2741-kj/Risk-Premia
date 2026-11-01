"""
Adapter: HTTP-primitive params -> common_engine.py's Skewness-tab functions (ratio_log_returns, skewness_position,
skewness_window_sweep) -> JSON-safe response. Mirrors common_engine.render_skewness_tab section by section; no math is
reimplemented here.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from common_engine import (SKEWNESS_DEFAULT_WINDOWS, SKEWNESS_FEATURE_WINDOW, daily_returns, equity_curve, ratio_log_returns,
                           rolling_sharpe, skewness_position, skewness_window_sweep)
from common_shared import CHART_LAYOUT, COLORS, is_geometric, pos_metrics_generic, register_geo_inputs

from cache import load_series, locked
from config_registry import get_asset_config, get_product_code
from services.momentum import _OVERLAY_COLORS, _clean_metrics, _fig_to_json, _series_to_json

SWEEP_WINDOWS = tuple(range(40, 761, 20))


@locked
def get_skewness(
    asset_class: str, product: str, *,
    roll_method: str = "5td", roll_n: int = 5,
    tc_bps: int = 5, shift_n: int = 1,
    windows: list[int] | None = None,
    metrics_year_start: int | None = None, metrics_year_end: int | None = None,
    feature_window: int | None = None,
    equity_year_start: int | None = None, equity_year_end: int | None = None,
    rs_basis: str = "net",
) -> dict:
    code = get_product_code(asset_class, product)
    f1_df, _curve = load_series(asset_class, code, roll_method, roll_n)
    register_geo_inputs(f1_df)
    f1r, f1c, phase, f2r = f1_df["F1_raw"], f1_df["F1_continuous"], f1_df["Phase"], f1_df["F2_raw"]
    unit_label = get_asset_config(asset_class)["products"][product]["unit"]

    yr0, yr1 = int(f1r.index[0].year), int(f1r.index[-1].year)
    metrics_year_start, metrics_year_end = metrics_year_start or yr0, metrics_year_end or yr1
    equity_year_start, equity_year_end = equity_year_start or yr0, equity_year_end or yr1
    windows = sorted(set(windows)) if windows else list(SKEWNESS_DEFAULT_WINDOWS)
    if feature_window not in windows:
        feature_window = SKEWNESS_FEATURE_WINDOW if SKEWNESS_FEATURE_WINDOW in windows else windows[0]

    lret = ratio_log_returns(f1c, f1r, f2r, phase)

    range_mask = (f1r.index >= pd.Timestamp(f"{metrics_year_start}-01-01")) & (f1r.index <= pd.Timestamp(f"{metrics_year_end}-12-31"))
    f1r_s = f1r[range_mask]
    f1c_s, phase_s = f1c.reindex(f1r_s.index), phase.reindex(f1r_s.index)
    metrics = None
    if len(f1r_s) >= 40:
        feature_pos = skewness_position(lret, feature_window, shift_n).reindex(f1r_s.index).fillna(0)
        metrics = _clean_metrics(pos_metrics_generic(feature_pos, f1r_s, f1c_s, tc_bps, phase_s))

    sweep = skewness_window_sweep(lret, f1c, f"{metrics_year_start}-01-01", f"{metrics_year_end}-12-31", shift_n,
                                  SWEEP_WINDOWS, is_geometric())
    fig_sw, best = None, None
    if sweep["sharpe"].notna().any():
        fig_sw = go.Figure(go.Bar(
            x=sweep["window"], y=sweep["sharpe"],
            marker_color=[COLORS["green"] if (v == v and v >= 0) else COLORS["secondary"] for v in sweep["sharpe"]],
            hovertemplate="Window: %{x}d<br>Gross Sharpe: %{y:.3f}<extra></extra>"))
        fig_sw.add_hline(y=0, line=dict(color="#555", width=1, dash="dot"))
        fig_sw.update_layout(**CHART_LAYOUT, height=320, xaxis_title="Look-back window (days)", yaxis_title="Gross Sharpe",
                             title=dict(text=f"{product}: Sharpe by Skewness Window", font=dict(size=13)))
        b = sweep.loc[sweep["sharpe"].idxmax()]
        best = {"window": int(b["window"]), "sharpe": float(b["sharpe"])}

    sk = lret.rolling(feature_window).skew()
    fig_sk = go.Figure()
    fig_sk.add_trace(go.Scatter(x=sk.index, y=sk.values, mode="lines", name=f"Skewness ({feature_window}d)",
                                line=dict(color=COLORS["primary"], width=1.3)))
    fig_sk.add_hline(y=0, line=dict(color="#555", width=1, dash="dot"))
    fig_sk.update_layout(**CHART_LAYOUT, height=300, yaxis_title="Skewness")

    positions = {f"Skew({w})": skewness_position(lret, w, shift_n) for w in windows}
    eq_start, eq_end = pd.Timestamp(f"{equity_year_start}-01-01"), pd.Timestamp(f"{equity_year_end}-12-31")
    fig_eq, fig_rs = go.Figure(), go.Figure()
    for i, (label, pos) in enumerate(positions.items()):
        gross_pnl, net_pnl = daily_returns(pos, f1r, f1c, tc_bps, phase)
        eq = equity_curve(net_pnl[(net_pnl.index >= eq_start) & (net_pnl.index <= eq_end)])
        fig_eq.add_trace(go.Scatter(x=eq.index, y=eq.values, mode="lines", name=label,
                                    line=dict(color=_OVERLAY_COLORS[i % len(_OVERLAY_COLORS)], width=1.6)))
        rs = rolling_sharpe(net_pnl if rs_basis == "net" else gross_pnl, 252)
        fig_rs.add_trace(go.Scatter(x=rs.index, y=rs.values, mode="lines", name=label,
                                    line=dict(color=_OVERLAY_COLORS[i % len(_OVERLAY_COLORS)], width=1.3)))
    fig_eq.update_layout(**CHART_LAYOUT, height=380, yaxis_title="Cumulative Return (%)" if is_geometric() else f"Cumulative PnL ({unit_label})")
    fig_rs.add_hline(y=0, line=dict(color="#555", width=1, dash="dot"))
    fig_rs.update_layout(**CHART_LAYOUT, height=320, yaxis_title="Rolling Sharpe")

    return {
        "year_range": {"min": yr0, "max": yr1}, "unit_label": unit_label,
        "default_windows": list(SKEWNESS_DEFAULT_WINDOWS), "windows": windows, "feature_window": feature_window,
        "metrics": metrics,
        "sweep_fig": _fig_to_json(fig_sw) if fig_sw else None, "sweep_best": best,
        "rolling_skew_fig": _fig_to_json(fig_sk),
        "equity_curve_fig": _fig_to_json(fig_eq), "rolling_sharpe_fig": _fig_to_json(fig_rs),
        "positions": {label: _series_to_json(pos) for label, pos in positions.items()},
    }
