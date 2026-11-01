"""
Adapter for the Portfolio tab. Every computation is a direct call into dashboard_portfolio_tab.py (the Streamlit tab's own
module), so the reference strategies, the per-product Carry pairs (Precious, Agriculture, TTF, EUA, Henry Hub), the Combined
Carry / CarryMom rows, the Skewness sleeve, the combine methods and the metric formulas are the same code the Streamlit
dashboards run. This file only replaces the st.* widget and session-state orchestration with function arguments, and the
st.plotly_chart figure with figure JSON.

Log-return methodology (research/engine.py), not the dollar-PnL convention of the Momentum/Carry/Value tabs, as in Streamlit.

Simplification vs. the Streamlit tab: custom portfolios are not frozen at "Add" time. Every /results call recomputes every
portfolio fresh from the current tc_bps / combine_method.
"""

import importlib

import numpy as np
import plotly.graph_objects as go

import dashboard_portfolio_tab as dpt
from common_shared import CHART_LAYOUT

from cache import locked
from services.momentum import _clean, _fig_to_json

FAMILY_TITLE = dpt.FAMILY_TITLE
PALETTE = dpt.PALETTE

_CONFIG_MODULES = {"metals": "metals", "petroleum": "petroleum", "pen": "pen", "ngl": "ngl", "precious": "precious", "agri": "agri"}

# Dashboard-display-only product exclusions, as the Streamlit apps pass them (precious_metals_dashboard, ngl_dashboard).
EXCLUDED_PRODUCTS: dict[str, tuple[str, ...]] = {
    "precious": ("Copper_COMEX",),
    "ngl": ("Ethylene", "Propylene"),
}


def get_cfg(asset_class: str):
    if asset_class not in _CONFIG_MODULES:
        raise KeyError(f"Unknown asset class: {asset_class!r}")
    return importlib.import_module(_CONFIG_MODULES[asset_class])


def _data(asset_class: str):
    cfg = get_cfg(asset_class)
    return cfg, dpt._load_products(cfg, cfg.ASSET_CLASS, EXCLUDED_PRODUCTS.get(asset_class, ()))


def _has_multi_tenor(cfg) -> bool:
    return len(getattr(cfg, "CARRY_TENOR_PAIRS", [])) >= 2 or dpt._per_product_pairs(cfg)


def get_reference_strategies(asset_class: str) -> dict:
    cfg = get_cfg(asset_class)
    instances = dpt._build_reference_strategies(cfg)
    per_product = dpt._per_product_pairs(cfg)
    multi = _has_multi_tenor(cfg)
    long_note = ""
    if per_product:
        long_note = getattr(cfg, "CARRY_CAPTION", None) or (
            "Carry and Carry momentum for this asset class combine the short pair F1-F2 with a long pair that differs by product ("
            + ", ".join(f"{p_} F1-{f_}" for p_, f_ in cfg.CARRY_LONG_FAR_BY_PRODUCT.items()) + "), as in the Final dashboard.")
    combined = []
    if multi:
        combined = [
            {"label": "Combined Carry", "note": "Carry V2 (z-scores summed across the pairs)",
             "tenor_pairs": [list(p) for p in cfg.CARRY_TENOR_PAIRS]},
            {"label": "Combined CarryMom", "note": "Carry momentum (slope changes summed across the pairs)",
             "tenor_pairs": [list(p) for p in cfg.CARRY_TENOR_PAIRS]},
        ]
    return {
        "has_multi_tenor": multi,
        "per_product_pairs": per_product,
        "carry_note": long_note,
        "combined": combined,
        "strategies": [
            {
                "id": inst["id"], "label": inst["label"], "family": inst["family"], "shift_n": inst["shift_n"],
                "legs": inst["legs"],
                "legs_desc": [dpt._describe_leg(inst["family"], leg) for leg in inst["legs"]],
            }
            for inst in instances
        ],
    }


@locked
def get_results(
    asset_class: str, *, tc_bps: int = 5,
    combine_method: str = "Equal Weight", vol_window: int = 63, return_tilt: float = 0.0,
    custom_portfolios: list[dict] | None = None,
    yr_start: int | None = None, yr_end: int | None = None,
    metric_strategy: str | None = None, shown: list[str] | None = None,
    separate_tenor_carry: bool = False, geometric: bool = True,
) -> dict:
    cfg, (data, common_start, common_end) = _data(asset_class)
    excluded = EXCLUDED_PRODUCTS.get(asset_class, ())
    min_year, max_year = int(common_start.year), int(common_end.year)
    yr_start, yr_end = yr_start or min_year, yr_end or max_year

    per_product = dpt._per_product_pairs(cfg)
    has_multi = _has_multi_tenor(cfg)
    separate = bool(separate_tenor_carry) and has_multi and not per_product
    reference_strategies = dpt._build_reference_strategies(cfg)
    raw_gross, raw_net = dpt._compute_reference_returns(cfg, cfg.ASSET_CLASS, tc_bps, excluded)

    # Same flow as render_portfolio_tab: default view = Momentum, Combined Carry, Combined CarryMom, Value (+ Skewness).
    if raw_net and has_multi and not separate:
        by_id = {inst["id"]: inst for inst in reference_strategies}
        carry_inst = [by_id[f"carry_{n}{f}"] for n, f in cfg.CARRY_TENOR_PAIRS if f"carry_{n}{f}" in by_id]
        cm_inst = [by_id[f"carrymom_{n}{f}"] for n, f in cfg.CARRY_TENOR_PAIRS if f"carrymom_{n}{f}" in by_id]
        if len(carry_inst) == len(cfg.CARRY_TENOR_PAIRS) and len(cm_inst) == len(cfg.CARRY_TENOR_PAIRS):
            cc_g, cc_n = dpt._combined_tenor_family_returns("Carry", cfg, carry_inst, data, tc_bps)
            ccm_g, ccm_n = dpt._combined_tenor_family_returns("CarryMom", cfg, cm_inst, data, tc_bps)
            instance_gross = {"Momentum": raw_gross["Momentum"], "Combined Carry": cc_g, "Combined CarryMom": ccm_g, "Value": raw_gross["Value"]}
            instance_net = {"Momentum": raw_net["Momentum"], "Combined Carry": cc_n, "Combined CarryMom": ccm_n, "Value": raw_net["Value"]}
            if "Skewness" in raw_net:
                instance_gross["Skewness"], instance_net["Skewness"] = raw_gross["Skewness"], raw_net["Skewness"]
        else:
            instance_gross, instance_net = dict(raw_gross), dict(raw_net)
    else:
        instance_gross, instance_net = dict(raw_gross), dict(raw_net)

    agg_label = agg5_label = None
    if instance_net:
        agg_label = "Portfolio (all reference strategies)"
        core_g = {k: v for k, v in instance_gross.items() if k != "Skewness"}
        core_n = {k: v for k, v in instance_net.items() if k != "Skewness"}
        instance_gross[agg_label], instance_net[agg_label] = dpt._combine_sleeves(core_g, core_n, combine_method, vol_window, tilt=return_tilt)
        if "Skewness" in instance_net:
            agg5_label = "Portfolio (all reference strategies + Skewness)"
            five_g = {k: v for k, v in instance_gross.items() if k != agg_label}
            five_n = {k: v for k, v in instance_net.items() if k != agg_label}
            instance_gross[agg5_label], instance_net[agg5_label] = dpt._combine_sleeves(five_g, five_n, combine_method, vol_window, tilt=return_tilt)

    for portfolio in (custom_portfolios or []):
        gross_by_name, net_by_name = {}, {}
        for sleeve in portfolio["sleeves"]:
            g, n = dpt._instance_asset_returns(sleeve, data, tc_bps)
            if not n.empty:
                label = FAMILY_TITLE[sleeve["family"]]
                gross_by_name[label], net_by_name[label] = g, n
        if net_by_name:
            gc, nc = dpt._combine_sleeves(gross_by_name, net_by_name, combine_method, vol_window, tilt=return_tilt)
            instance_gross[portfolio["label"]], instance_net[portfolio["label"]] = gc, nc

    metric_labels = list(instance_net.keys())
    if not metric_labels:
        return {"common_start": str(common_start.date()), "common_end": str(common_end.date()), "min_year": min_year, "max_year": max_year,
                "metric_labels": [], "metrics": None, "equity_fig": None, "table_rows": []}

    metric_strategy = metric_strategy if metric_strategy in metric_labels else metric_labels[0]
    shown = [s for s in (shown or []) if s in metric_labels] or metric_labels
    m = dpt._window_metrics(instance_gross[metric_strategy], instance_net[metric_strategy], yr_start, yr_end, geometric)
    metrics = {k: _clean(v) for k, v in m.items()}

    fig = go.Figure()
    rows = []
    for i, label in enumerate(shown):
        s = instance_net[label]
        window = s[(s.index.year >= yr_start) & (s.index.year <= yr_end)].dropna()
        if window.empty:
            continue
        eq = (np.exp(window.cumsum()) - 1) * 100 if geometric else np.expm1(window).cumsum() * 100
        fig.add_trace(go.Scatter(x=eq.index, y=eq.values, name=label, mode="lines", line=dict(color=PALETTE[i % len(PALETTE)], width=1.6)))
        if len(window) > 20 and window.std(ddof=1) > 0:
            ret = (np.exp(float(window.mean() * 252)) - 1) * 100 if geometric else float(np.expm1(window).mean() * 252 * 100)
            vol = float(np.expm1(window).std(ddof=1) * np.sqrt(252) * 100)
            ir = ret / vol if vol > 0 else float("nan")
        else:
            ret = vol = ir = float("nan")
        rows.append({"strategy": label, "return": _clean(ret), "vol": _clean(vol), "ir": _clean(ir)})
    layout = dict(CHART_LAYOUT)
    layout["yaxis_title"] = "Cumulative Return (%)"
    fig.update_layout(**layout, title=f"Cumulative Equity, {yr_start} to {yr_end}", height=460)

    return {
        "common_start": str(common_start.date()), "common_end": str(common_end.date()),
        "min_year": min_year, "max_year": max_year,
        "metric_labels": metric_labels, "n_products": len(data),
        "agg_label": agg_label, "agg5_label": agg5_label, "combine_method": combine_method,
        "metrics": metrics, "equity_fig": _fig_to_json(fig), "table_rows": rows,
    }
