"""
Adapter for the Value tab -- mirrors common_engine.render_value_tab()'s body
exactly (math + chart construction), minus the st.selectbox/st.slider param
reads.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from common_engine import daily_returns, equity_curve, rolling_sharpe, value_heatmap, value_v1_position
from common_shared import CHART_LAYOUT, COLORS, pos_metrics_generic

from cache import load_series
from config_registry import get_asset_config, get_product_code
from services.momentum import _clean_metrics, _fig_to_json, _series_to_json

_OVERLAY_COLORS = [COLORS["primary"], COLORS["green"], COLORS["secondary"],
                   "#A78BFA", "#F472B6", "#22D3EE", "#FB923C", "#60A5FA"]

LOOKBACK_MAP = {"1mo": 20, "1qtr": 60, "6mo": 120, "1yr": 252, "3yr": 756,
                "5yr": 1260, "7yr": 1764, "10yr": 2520}


def _load(asset_class: str, product: str, roll_method: str, roll_n: int):
    code = get_product_code(asset_class, product)
    f1_df, curve = load_series(asset_class, code, roll_method, roll_n)
    return f1_df["F1_raw"], f1_df["F1_continuous"], f1_df["Phase"], curve


def _resolve_lookback_days(lb_label: str) -> int:
    if lb_label in LOOKBACK_MAP:
        return LOOKBACK_MAP[lb_label]
    return int(lb_label.rstrip("d"))


def _all_contracts(curve, skip_front_contract: bool) -> list[str]:
    contracts = [c for c in curve.columns if c.startswith("F")]
    if skip_front_contract:
        contracts = [c for c in contracts if c != "F1"]
    return contracts


def _combo_label(c: dict) -> str:
    return f"{c['contract']} {c['lookback']} ±{c['threshold'] * 100:.0f}%"


def get_value(
    asset_class: str, product: str, *,
    roll_method: str = "ltd", roll_n: int = 5,
    tc_bps: int = 5, shift_n: int = 2,
    combos: list[dict] | None = None,
    skip_front_contract: bool = False,
    metrics_year_start: int | None = None, metrics_year_end: int | None = None,
    feature_combo: dict | None = None,
    equity_year_start: int | None = None, equity_year_end: int | None = None,
    focus_combo: dict | None = None,
    rs_basis: str = "net",
) -> dict:
    f1r, f1c, phase, curve = _load(asset_class, product, roll_method, roll_n)
    ac = get_asset_config(asset_class)
    unit_label = ac["products"][product]["unit"]
    contracts = _all_contracts(curve, skip_front_contract)

    yr0, yr1 = int(f1r.index[0].year), int(f1r.index[-1].year)
    metrics_year_start = metrics_year_start or yr0
    metrics_year_end = metrics_year_end or yr1
    equity_year_start = equity_year_start or yr0
    equity_year_end = equity_year_end or yr1

    default_contract = contracts[min(7, len(contracts) - 1)]
    # Asset-level override of the default (contract, lookback, threshold)
    # combo -- e.g. NGL uses F12/10yr/10% instead of the generic 8th-contract/
    # 5yr/10% (see ngl_dashboard/app.py's VALUE_DEFAULT_ACTIVE).
    default_combo = ac.get("value_default_combo") or {"contract": default_contract, "lookback": "5yr", "threshold": 0.10}
    combos = combos or [default_combo]

    positions = {
        _combo_label(c): value_v1_position(curve, c["contract"], _resolve_lookback_days(c["lookback"]),
                                            c["threshold"], shift_n=shift_n)
        for c in combos
    }
    positions = {k: v for k, v in positions.items() if not v.empty}

    if not positions:
        return {
            "year_range": {"min": yr0, "max": yr1}, "unit_label": unit_label, "contracts": contracts,
            "lookback_options": list(LOOKBACK_MAP.keys()), "default_combo": default_combo,
            "metrics": None, "equity_curve_fig": None, "rolling_sharpe_fig": None, "signal_position_fig": None,
            "positions": {},
        }

    default_label = _combo_label(default_combo)
    feature_label = _combo_label(feature_combo) if feature_combo else default_label
    if feature_label not in positions:
        feature_label = default_label if default_label in positions else next(iter(positions))
    focus_label = _combo_label(focus_combo) if focus_combo else feature_label
    if focus_label not in positions:
        focus_label = feature_label

    range_start, range_end = f"{metrics_year_start}-01-01", f"{metrics_year_end}-12-31"
    range_mask = (f1r.index >= range_start) & (f1r.index <= range_end)
    f1r_scoped, f1c_scoped = f1r[range_mask], f1c.reindex(f1r[range_mask].index)
    phase_scoped = phase.reindex(f1r_scoped.index)
    curve_scoped = curve[(curve.index >= range_start) & (curve.index <= range_end)]

    feature_combo_resolved = next(c for c in combos if _combo_label(c) == feature_label)
    feature_pos_scoped = value_v1_position(
        curve_scoped, feature_combo_resolved["contract"], _resolve_lookback_days(feature_combo_resolved["lookback"]),
        feature_combo_resolved["threshold"], shift_n=shift_n,
    )
    metrics = _clean_metrics(pos_metrics_generic(feature_pos_scoped, f1r_scoped, f1c_scoped, tc_bps, phase_scoped))

    eq_start, eq_end = f"{equity_year_start}-01-01", f"{equity_year_end}-12-31"
    fig_eq = go.Figure()
    for i, (label, pos) in enumerate(positions.items()):
        _, net_pnl = daily_returns(pos, f1r, f1c, tc_bps, phase)
        pnl_w = net_pnl[(net_pnl.index >= eq_start) & (net_pnl.index <= eq_end)]
        eq = equity_curve(pnl_w)
        fig_eq.add_trace(go.Scatter(x=eq.index, y=eq.values, mode="lines", name=label,
                                     line=dict(color=_OVERLAY_COLORS[i % len(_OVERLAY_COLORS)], width=1.6)))
    fig_eq.update_layout(**CHART_LAYOUT, height=380, yaxis_title=f"Cumulative PnL ({unit_label})")

    fig_rs = go.Figure()
    for i, (label, pos) in enumerate(positions.items()):
        gross_pnl, net_pnl = daily_returns(pos, f1r, f1c, tc_bps, phase)
        pnl = net_pnl if rs_basis == "net" else gross_pnl
        rs = rolling_sharpe(pnl, 252)
        fig_rs.add_trace(go.Scatter(x=rs.index, y=rs.values, mode="lines", name=label,
                                     line=dict(color=_OVERLAY_COLORS[i % len(_OVERLAY_COLORS)], width=1.3)))
    fig_rs.add_hline(y=0, line=dict(color="#555", width=1, dash="dot"))
    fig_rs.update_layout(**CHART_LAYOUT, height=320, yaxis_title="Rolling Sharpe")

    pos_w = positions[focus_label].reindex(f1r.index).fillna(0)
    pos_long, pos_short = pos_w.where(pos_w > 0, 0.0), pos_w.where(pos_w < 0, 0.0)
    fig_sig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35], vertical_spacing=0.04)
    fig_sig.add_trace(go.Scatter(x=f1r.index, y=f1r.values, name="F1 Price",
                                  line=dict(color=COLORS["primary"], width=1.5)), row=1, col=1)
    fig_sig.add_trace(go.Bar(x=pos_w.index, y=pos_long.values, name="Long (+1)", marker_color="#00E676"), row=2, col=1)
    fig_sig.add_trace(go.Bar(x=pos_w.index, y=pos_short.values, name="Short (-1)", marker_color="#FF1744"), row=2, col=1)
    fig_sig.update_layout(**CHART_LAYOUT, height=500, barmode="overlay",
                           title=dict(text=f"{focus_label} — Price & Position", font=dict(size=13)),
                           hovermode="x unified", showlegend=True)
    fig_sig.update_yaxes(title_text="F1 Price", row=1, col=1)
    fig_sig.update_yaxes(title_text="Position", tickvals=[-1, 0, 1], ticktext=["Short", "Flat", "Long"], row=2, col=1)

    return {
        "year_range": {"min": yr0, "max": yr1},
        "unit_label": unit_label,
        "contracts": contracts,
        "lookback_options": list(LOOKBACK_MAP.keys()),
        "default_combo": default_combo,
        "feature_label": feature_label,
        "focus_label": focus_label,
        "metrics": metrics,
        "equity_curve_fig": _fig_to_json(fig_eq),
        "rolling_sharpe_fig": _fig_to_json(fig_rs),
        "signal_position_fig": _fig_to_json(fig_sig),
        "positions": {label: _series_to_json(pos) for label, pos in positions.items()},
    }


def get_value_heatmap(
    asset_class: str, product: str, *,
    roll_method: str = "ltd", roll_n: int = 5,
    tc_bps: int = 5, shift_n: int = 2,
    skip_front_contract: bool = False,
    threshold: float = 0.10,
    year_start: int | None = None, year_end: int | None = None,
) -> dict:
    f1r, f1c, _phase, curve = _load(asset_class, product, roll_method, roll_n)
    yr0, yr1 = int(f1r.index[0].year), int(f1r.index[-1].year)
    year_start, year_end = year_start or yr0, year_end or yr1
    contracts = _all_contracts(curve, skip_front_contract)

    hm_df = value_heatmap(curve, tuple(contracts), tuple(LOOKBACK_MAP.items()), threshold, f1r, f1c,
                           f"{year_start}-01-01", f"{year_end}-12-31", shift_n)
    if hm_df.empty or not hm_df["sharpe"].notna().any():
        return {"fig": None, "best": None}

    lb_order = list(LOOKBACK_MAP.keys())
    pivot = hm_df.pivot(index="contract", columns="lookback", values="sharpe").reindex(index=contracts, columns=lb_order)
    fig_hm = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index, colorscale="RdYlGn", zmid=0,
        colorbar=dict(title="Sharpe"),
        hovertemplate="Contract: %{y}<br>Lookback: %{x}<br>Sharpe: %{z:.3f}<extra></extra>",
    ))
    fig_hm.update_layout(**CHART_LAYOUT, height=560,
                          title=dict(text=f"{product} — Value Sharpe by Contract × Lookback (±{threshold*100:.0f}%)",
                                     font=dict(size=13)),
                          xaxis_title="Lookback", yaxis_title="Contract")

    best = hm_df.loc[hm_df["sharpe"].idxmax()]
    return {
        "fig": _fig_to_json(fig_hm),
        "best": {"contract": str(best["contract"]), "lookback": str(best["lookback"]), "sharpe": float(best["sharpe"])},
    }
