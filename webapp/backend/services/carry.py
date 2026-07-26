"""
Adapter for the Carry tab -- mirrors common_engine.render_carry_tab()'s body
exactly (math + chart construction), minus the st.selectbox/st.slider param
reads. V2 (Z-score) and V3 (Carry-Momentum) variants always use the tab's
single near_default/far_default pair (F1-F2, or F2-F3 if skip_front_contract)
-- only V1 lets the caller choose an arbitrary (near, far) pair -- this
matches render_carry_tab's _build_position() closure exactly, not a
simplification.
"""

from common_engine import carry_heatmap, carry_v1_position, carry_v3_position, carry_v4_position
import plotly.graph_objects as go
from common_shared import CHART_LAYOUT, COLORS, pos_metrics_generic

from cache import load_series
from config_registry import get_asset_config, get_product_code
from services.momentum import _clean_metrics, _fig_to_json, _series_to_json  # reuse, no reimplementation

_OVERLAY_COLORS = [COLORS["primary"], COLORS["green"], COLORS["secondary"],
                   "#A78BFA", "#F472B6", "#22D3EE", "#FB923C", "#60A5FA"]


def _load(asset_class: str, product: str, roll_method: str, roll_n: int):
    code = get_product_code(asset_class, product)
    f1_df, curve = load_series(asset_class, code, roll_method, roll_n)
    return f1_df["F1_raw"], f1_df["F1_continuous"], f1_df["Phase"], curve


def _all_contracts(curve, skip_front_contract: bool) -> list[str]:
    contracts = sorted(
        (c for c in curve.columns if c.startswith("F") and c[1:].isdigit() and curve[c].notna().any()),
        key=lambda c: int(c[1:]),
    )
    if skip_front_contract and "F1" in contracts:
        contracts.remove("F1")
    return contracts


def _variant_label(v: dict) -> str:
    if v["type"] == "V1":
        return f"V1 ({v['near']}-{v['far']})"
    if v["type"] == "V2":
        return f"V2 (win={v['window']})"
    return f"V3 (N={v['horizon']})"


def _build_position(v: dict, curve, shift_n: int, near_default: str, far_default: str):
    if v["type"] == "V1":
        return carry_v1_position(curve, v["near"], v["far"], shift_n=shift_n)
    if v["type"] == "V2":
        return carry_v3_position(curve, v["window"], shift_n=shift_n, near=near_default, far=far_default)
    return carry_v4_position(curve, v["horizon"], shift_n=shift_n, near=near_default, far=far_default)


def get_carry(
    asset_class: str, product: str, *,
    roll_method: str = "ltd", roll_n: int = 5,
    tc_bps: int = 5, shift_n: int = 1,
    variants: list[dict] | None = None,
    skip_front_contract: bool = False,
    metrics_year_start: int | None = None, metrics_year_end: int | None = None,
    feature_variant: dict | None = None,
    equity_year_start: int | None = None, equity_year_end: int | None = None,
    focus_variant: dict | None = None,
    rs_basis: str = "net",
) -> dict:
    from common_engine import daily_returns, equity_curve, rolling_sharpe  # local import, same module as momentum.py
    f1r, f1c, phase, curve = _load(asset_class, product, roll_method, roll_n)
    ac = get_asset_config(asset_class)
    unit_label = ac["products"][product]["unit"]
    near_default, far_default = ("F2", "F3") if skip_front_contract else ("F1", "F2")
    # Asset-level override of V1's default (near, far) pair -- e.g. NGL uses
    # F4-F15 (far-tenor) since near-tenor carry there is dominated by
    # heating-season seasonality, not genuine term structure (see
    # ngl_dashboard/app.py's CARRY_DEFAULT_ACTIVE).
    if ac.get("carry_default_near") and ac.get("carry_default_far"):
        near_default, far_default = ac["carry_default_near"], ac["carry_default_far"]

    yr0, yr1 = int(f1r.index[0].year), int(f1r.index[-1].year)
    metrics_year_start = metrics_year_start or yr0
    metrics_year_end = metrics_year_end or yr1
    equity_year_start = equity_year_start or yr0
    equity_year_end = equity_year_end or yr1

    variants = variants or [
        {"type": "V1", "near": near_default, "far": far_default},
        {"type": "V2", "window": 252},
        {"type": "V3", "horizon": 20},
    ]
    positions = {_variant_label(v): _build_position(v, curve, shift_n, near_default, far_default) for v in variants}
    positions = {k: v for k, v in positions.items() if not v.empty}

    all_contracts = _all_contracts(curve, skip_front_contract)

    if not positions:
        return {
            "year_range": {"min": yr0, "max": yr1}, "unit_label": unit_label, "contracts": all_contracts,
            "near_default": near_default, "far_default": far_default,
            "feature_label": None, "focus_label": None,
            "metrics": None, "equity_curve_fig": None, "rolling_sharpe_fig": None, "signal_position_fig": None,
            "positions": {},
        }

    default_v1_label = ac.get("carry_default_feature_label") or f"V1 ({near_default}-{far_default})"
    feature_label = _variant_label(feature_variant) if feature_variant else default_v1_label
    if feature_label not in positions:
        feature_label = default_v1_label if default_v1_label in positions else next(iter(positions))
    focus_label = _variant_label(focus_variant) if focus_variant else feature_label
    if focus_label not in positions:
        focus_label = feature_label

    range_start, range_end = f"{metrics_year_start}-01-01", f"{metrics_year_end}-12-31"
    range_mask = (f1r.index >= range_start) & (f1r.index <= range_end)
    f1r_scoped, f1c_scoped = f1r[range_mask], f1c.reindex(f1r[range_mask].index)
    phase_scoped = phase.reindex(f1r_scoped.index)
    curve_scoped = curve[(curve.index >= range_start) & (curve.index <= range_end)]

    feature_v = next(v for v in variants if _variant_label(v) == feature_label)
    feature_pos_scoped = _build_position(feature_v, curve_scoped, shift_n, near_default, far_default)
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

    from plotly.subplots import make_subplots
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
        "contracts": all_contracts,
        "near_default": near_default,
        "far_default": far_default,
        "feature_label": feature_label,
        "focus_label": focus_label,
        "metrics": metrics,
        "equity_curve_fig": _fig_to_json(fig_eq),
        "rolling_sharpe_fig": _fig_to_json(fig_rs),
        "signal_position_fig": _fig_to_json(fig_sig),
        "positions": {label: _series_to_json(pos) for label, pos in positions.items()},
    }


def get_carry_heatmap(
    asset_class: str, product: str, *,
    roll_method: str = "ltd", roll_n: int = 5,
    tc_bps: int = 5, shift_n: int = 1,
    skip_front_contract: bool = False,
    days: int | None = None, mode: str | None = None,
    year_start: int | None = None, year_end: int | None = None,
) -> dict:
    f1r, f1c, _phase, curve = _load(asset_class, product, roll_method, roll_n)
    yr0, yr1 = int(f1r.index[0].year), int(f1r.index[-1].year)
    year_start, year_end = year_start or yr0, year_end or yr1
    all_contracts = _all_contracts(curve, skip_front_contract)

    hm_df = carry_heatmap(curve, tuple(all_contracts), days, mode, f1r, f1c,
                           f"{year_start}-01-01", f"{year_end}-12-31", shift_n)
    if hm_df.empty or not hm_df["sharpe"].notna().any():
        return {"fig": None, "best": None}

    pivot = hm_df.pivot(index="near", columns="far", values="sharpe").reindex(index=all_contracts, columns=all_contracts)
    fig_hm = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index, colorscale="RdYlGn", zmid=0,
        colorbar=dict(title="Sharpe"),
        hovertemplate="Near: %{y}<br>Far: %{x}<br>Sharpe: %{z:.3f}<extra></extra>",
    ))
    if days is None:
        signal_desc = "V1 Level"
    elif mode == "Momentum":
        signal_desc = f"V3 Carry-Momentum ({days}d)"
    else:
        signal_desc = f"V2 Z-score ({days}d)"
    fig_hm.update_layout(**CHART_LAYOUT, height=560,
                          title=dict(text=f"{product} — Carry Sharpe by Contract Pair ({signal_desc})", font=dict(size=13)),
                          xaxis_title="Far Contract", yaxis_title="Near Contract")

    best = hm_df.loc[hm_df["sharpe"].idxmax()]
    return {
        "fig": _fig_to_json(fig_hm),
        "best": {"near": str(best["near"]), "far": str(best["far"]), "sharpe": float(best["sharpe"])},
    }
