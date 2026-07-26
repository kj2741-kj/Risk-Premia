"""
Adapter for the Comparison tab. Unlike Momentum/Carry/Value, this tab has no
strategy construction of its own -- it only overlays {label: position} dicts
already produced by those three tabs (see common_engine.render_comparison_tab's
docstring). The frontend already has those position series (each of the three
tab endpoints returns them under "positions"), so this endpoint takes them as
input rather than recomputing anything -- avoiding a second, potentially
divergent code path for rebuilding the same signals.
"""

import pandas as pd
import plotly.graph_objects as go

from common_engine import daily_returns, rolling_price_vol, rolling_sharpe
from common_shared import CHART_LAYOUT, COLORS

from cache import load_series
from config_registry import get_asset_config, get_product_code
from services.momentum import _fig_to_json

_OVERLAY_COLORS = [COLORS["primary"], COLORS["green"], COLORS["secondary"],
                   "#A78BFA", "#F472B6", "#22D3EE", "#FB923C", "#60A5FA"]

VOL_WINDOW_MAP = {"21d (1mo)": 21, "63d (1qtr)": 63, "126d (6mo)": 126, "252d (1yr)": 252}


def _series_from_json(dates: list[str], values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.to_datetime(dates))


def get_comparison(
    asset_class: str, product: str, *,
    roll_method: str = "ltd", roll_n: int = 5,
    groups: dict[str, dict[str, dict]],  # {"Momentum": {label: {"dates":[...],"values":[...]}}, ...}
    tc_bps: int = 5,
    vol_window_label: str = "63d (1qtr)",
    chosen: list[str] | None = None,
    equity_year_start: int | None = None, equity_year_end: int | None = None,
    rs_basis: str = "net",
    show_vol_overlay: bool = False,
) -> dict:
    code = get_product_code(asset_class, product)
    f1_df, _curve = load_series(asset_class, code, roll_method, roll_n)
    f1r, f1c, phase = f1_df["F1_raw"], f1_df["F1_continuous"], f1_df["Phase"]
    ac = get_asset_config(asset_class)
    unit_label = ac["products"][product]["unit"]

    yr0, yr1 = int(f1r.index[0].year), int(f1r.index[-1].year)
    equity_year_start = equity_year_start or yr0
    equity_year_end = equity_year_end or yr1

    vol_window = VOL_WINDOW_MAP.get(vol_window_label, 63)
    vol = rolling_price_vol(f1r, vol_window)
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Scatter(x=vol.index, y=vol.values, mode="lines", name=f"{product} Volatility",
                                  line=dict(color=COLORS["secondary"], width=1.4)))
    fig_vol.update_layout(**CHART_LAYOUT, height=300, yaxis_title=f"Annualized Vol ({unit_label})")

    all_positions: dict[str, pd.Series] = {}
    for group_name, group_positions in groups.items():
        for label, series_json in group_positions.items():
            all_positions[f"{group_name}: {label}"] = _series_from_json(series_json["dates"], series_json["values"])

    available_labels = list(all_positions.keys())
    chosen = [c for c in chosen if c in all_positions] if chosen else available_labels
    if not chosen:
        return {
            "year_range": {"min": yr0, "max": yr1}, "unit_label": unit_label,
            "available_labels": available_labels, "vol_fig": _fig_to_json(fig_vol),
            "equity_curve_fig": None, "rolling_sharpe_fig": None,
        }

    eq_start, eq_end = f"{equity_year_start}-01-01", f"{equity_year_end}-12-31"
    fig_eq = go.Figure()
    for i, label in enumerate(chosen):
        pos = all_positions[label]
        _, net_pnl = daily_returns(pos, f1r, f1c, tc_bps, phase)
        pnl_w = net_pnl[(net_pnl.index >= eq_start) & (net_pnl.index <= eq_end)]
        eq = pnl_w.fillna(0).cumsum()
        fig_eq.add_trace(go.Scatter(x=eq.index, y=eq.values, mode="lines", name=label,
                                     line=dict(color=_OVERLAY_COLORS[i % len(_OVERLAY_COLORS)], width=1.6)))
    layout = dict(CHART_LAYOUT, height=380, yaxis_title=f"Cumulative PnL ({unit_label})")
    if show_vol_overlay:
        vol_w = vol[(vol.index >= eq_start) & (vol.index <= eq_end)]
        fig_eq.add_trace(go.Scatter(x=vol_w.index, y=vol_w.values, mode="lines",
                                     name="Volatility (F1_raw, right axis)",
                                     line=dict(color="#8A8278", width=1.3, dash="dot"), yaxis="y2"))
        layout["yaxis2"] = dict(title=f"Annualized Vol ({unit_label})", overlaying="y", side="right", showgrid=False)
        layout["legend"] = dict(CHART_LAYOUT["legend"], orientation="h", y=1.15)
    fig_eq.update_layout(**layout)

    fig_rs = go.Figure()
    for i, label in enumerate(chosen):
        pos = all_positions[label]
        gross_pnl, net_pnl = daily_returns(pos, f1r, f1c, tc_bps, phase)
        pnl = net_pnl if rs_basis == "net" else gross_pnl
        rs = rolling_sharpe(pnl, 252)
        fig_rs.add_trace(go.Scatter(x=rs.index, y=rs.values, mode="lines", name=label,
                                     line=dict(color=_OVERLAY_COLORS[i % len(_OVERLAY_COLORS)], width=1.3)))
    fig_rs.add_hline(y=0, line=dict(color="#555", width=1, dash="dot"))
    fig_rs.update_layout(**CHART_LAYOUT, height=320, yaxis_title="Rolling Sharpe")

    return {
        "year_range": {"min": yr0, "max": yr1},
        "unit_label": unit_label,
        "available_labels": available_labels,
        "vol_fig": _fig_to_json(fig_vol),
        "equity_curve_fig": _fig_to_json(fig_eq),
        "rolling_sharpe_fig": _fig_to_json(fig_rs),
    }
