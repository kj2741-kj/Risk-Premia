"""
Adapter for the Portfolio tab -- mirrors dashboard_portfolio_tab.py's
computation exactly. Uses research/engine.py's LOG-RETURN methodology, not
common_engine.py's dollar-PnL convention -- these numbers will not reconcile
with the Momentum/Carry/Value/Comparison tabs (same disclosure the Streamlit
tab makes). research/engine.py and research/risk_parity.py have zero
Streamlit dependency, so they're reused verbatim; only the Streamlit
widget/session-state orchestration is replaced.

Simplification vs. the Streamlit tab: custom portfolios are NOT frozen at
"Add" time. Every /results call recomputes every portfolio (reference
strategies, their aggregate, and every custom portfolio) fresh from the
CURRENT tc_bps/combine_method -- more internally consistent (everything on
screen always reflects the current global settings) than the Streamlit
original, which keeps whatever tc_bps was active when a portfolio was added
even if tc_bps changes afterward.
"""

import functools
import importlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from common_shared import CHART_LAYOUT
from engine import (combine_positions, combine_returns, exec_shift, log_return_daily,
                     raw_signal_carry_v1, raw_signal_carry_v2, raw_signal_carrymom,
                     raw_signal_momentum, raw_signal_value)
from risk_parity import rolling_erc_combine

from services.momentum import _clean, _fig_to_json

PALETTE = ["#B87333", "#C9A84C", "#3D8F8A", "#5BAD72", "#B85450",
           "#A07898", "#6A6460", "#9BAAB3", "#7A8E9A", "#C8D0D8"]

FAMILY_TITLE = {"Momentum": "Momentum", "Carry": "Carry", "CarryMom": "Carry-Momentum", "Value": "Value"}

_CONFIG_MODULES = {"metals": "metals", "energy": "energy", "precious": "precious", "ngl": "ngl"}

# Dashboard-display-only product exclusions, mirroring energy_dashboard/app.py's
# ENERGY_PORTFOLIO_EXCLUDED (2026-08-03) -- research/configs/energy.py's own
# PRODUCTS list is untouched, this only filters what the Portfolio route
# computes/returns. Names match cfg.PRODUCTS' own strings (no space), not
# config_registry.py's display-label keys.
EXCLUDED_PRODUCTS: dict[str, tuple[str, ...]] = {
    "energy": ("SingaporeGasoil", "FuelOil"),
    "ngl": ("Ethylene", "Propylene"),
}


def get_cfg(asset_class: str):
    if asset_class not in _CONFIG_MODULES:
        raise KeyError(f"Unknown asset class: {asset_class!r}")
    return importlib.import_module(_CONFIG_MODULES[asset_class])


@functools.lru_cache(maxsize=8)
def _load_products(asset_class: str):
    """Curve + log-return F1 series for every product in cfg.PRODUCTS (minus
    EXCLUDED_PRODUCTS.get(asset_class, ())), truncated to the common date
    window across the remaining products. Cached on the primitive asset_class
    string only -- the expensive step (Excel parsing + roll-adjustment for
    every product)."""
    cfg = get_cfg(asset_class)
    excluded = EXCLUDED_PRODUCTS.get(asset_class, ())
    data = {}
    for product in cfg.PRODUCTS:
        if product in excluded:
            continue
        f1 = cfg.load_f1_series_logret(product)
        curve = cfg.load_curve(product)
        data[product] = {"f1r": f1["F1_raw"], "log_price": f1["log_price"],
                          "phase": f1["Phase"], "curve": curve}
    common_start = max(d["f1r"].index.min() for d in data.values())
    common_end = min(d["f1r"].index.max() for d in data.values())
    for d in data.values():
        d["f1r"] = d["f1r"].loc[common_start:common_end]
        d["log_price"] = d["log_price"].loc[common_start:common_end]
        d["phase"] = d["phase"].loc[common_start:common_end]
        d["curve"] = d["curve"].loc[common_start:common_end]
    return data, common_start, common_end


def _leg_raw_signal(family: str, leg: dict, product_data: dict) -> pd.Series:
    curve, f1r = product_data["curve"], product_data["f1r"]
    if family == "Momentum":
        fast, slow = leg.get("fast"), leg.get("slow")
        if fast is None or slow is None:
            return pd.Series(dtype=float)
        return raw_signal_momentum(f1r, int(fast), int(slow))
    if family == "Carry":
        near, far = leg.get("near"), leg.get("far")
        if near is None or far is None:
            return pd.Series(dtype=float)
        leg_type = leg.get("type", "V1 Level")
        if leg_type == "V1 Level":
            return raw_signal_carry_v1(curve, near, far)
        if leg_type == "V2 Z-score":
            return raw_signal_carry_v2(curve, near, far, int(leg.get("zwindow") or 252))
        if leg_type == "V3 Carry-Momentum":
            horizon = leg.get("horizon")
            if horizon is None:
                return pd.Series(dtype=float)
            return raw_signal_carrymom(curve, near, far, int(horizon))
        return pd.Series(dtype=float)
    if family == "CarryMom":
        near, far, horizon = leg.get("near"), leg.get("far"), leg.get("horizon")
        if near is None or far is None or horizon is None:
            return pd.Series(dtype=float)
        return raw_signal_carrymom(curve, near, far, int(horizon))
    if family == "Value":
        contract, lookback, threshold = leg.get("contract"), leg.get("lookback"), leg.get("threshold")
        if contract is None or lookback is None or threshold is None:
            return pd.Series(dtype=float)
        return raw_signal_value(curve, contract, int(lookback), float(threshold))
    raise ValueError(f"Unknown family {family!r}")


def _instance_product_returns(instance: dict, product_data: dict, tc_bps: int) -> tuple[pd.Series, pd.Series]:
    empty = pd.Series(dtype=float)
    if not instance["legs"]:
        return empty, empty
    raws = [_leg_raw_signal(instance["family"], leg, product_data) for leg in instance["legs"]]
    raws = [r for r in raws if not r.empty]
    if not raws:
        return empty, empty
    combo = raws[0] if len(raws) == 1 else combine_positions(raws, instance.get("combine_method", "equal_weight"))
    pos = exec_shift(combo, int(instance["shift_n"])).fillna(0)
    return log_return_daily(pos, product_data["log_price"], tc_bps, product_data["phase"])


def _instance_asset_returns(instance: dict, data: dict, tc_bps: int) -> tuple[pd.Series, pd.Series]:
    grosses, nets = [], []
    for product_data in data.values():
        g, n = _instance_product_returns(instance, product_data, tc_bps)
        if not n.empty:
            grosses.append(g)
            nets.append(n)
    empty = pd.Series(dtype=float)
    gross_agg = combine_returns(grosses, "equal_weight") if grosses else empty
    net_agg = combine_returns(nets, "equal_weight") if nets else empty
    return gross_agg, net_agg


def _build_reference_strategies(cfg) -> list[dict]:
    instances = [{
        "id": "mom", "family": "Momentum", "label": "Momentum",
        "legs": [{"fast": f, "slow": s} for f, s in cfg.MOMENTUM_PAIRS],
        "shift_n": cfg.MOMENTUM_SHIFT_N, "combine_method": "equal_weight",
    }]
    for near, far in cfg.CARRY_TENOR_PAIRS:
        instances.append({
            "id": f"carry_{near}{far}", "family": "Carry", "label": f"Carry ({near}-{far})",
            "legs": [
                {"type": "V1 Level", "near": near, "far": far,
                 "zwindow": cfg.CARRY_ZSCORE_WINDOW, "horizon": cfg.CARRY_MOMENTUM_HORIZON},
                {"type": "V2 Z-score", "near": near, "far": far,
                 "zwindow": cfg.CARRY_ZSCORE_WINDOW, "horizon": cfg.CARRY_MOMENTUM_HORIZON},
            ],
            "shift_n": cfg.CARRY_SHIFT_N, "combine_method": "equal_weight",
        })
    for near, far in cfg.CARRY_TENOR_PAIRS:
        instances.append({
            "id": f"carrymom_{near}{far}", "family": "CarryMom", "label": f"CarryMom ({near}-{far})",
            "legs": [{"near": near, "far": far, "horizon": cfg.CARRY_MOMENTUM_HORIZON}],
            "shift_n": cfg.CARRY_MOMENTUM_SHIFT_N, "combine_method": "equal_weight",
        })
    instances.append({
        "id": "value", "family": "Value", "label": "Value",
        "legs": [{"contract": cfg.VALUE_CONTRACT, "lookback": cfg.VALUE_LOOKBACK_DAYS,
                  "threshold": cfg.VALUE_THRESHOLD}],
        "shift_n": cfg.VALUE_SHIFT_N, "combine_method": "equal_weight",
    })
    return instances


def _describe_leg(family: str, leg: dict) -> str:
    if family == "Momentum":
        return f"MA crossover, fast={leg.get('fast')}, slow={leg.get('slow')}"
    if family == "Carry":
        leg_type = leg.get("type", "V1 Level")
        text = f"{leg_type} ({leg.get('near')}-{leg.get('far')})"
        if leg_type == "V2 Z-score":
            text += f", z-window={leg.get('zwindow')}"
        elif leg_type == "V3 Carry-Momentum":
            text += f", horizon={leg.get('horizon')}"
        return text
    if family == "CarryMom":
        return f"Carry-Momentum ({leg.get('near')}-{leg.get('far')}), horizon={leg.get('horizon')}"
    if family == "Value":
        return f"contract={leg.get('contract')}, lookback={leg.get('lookback')}d, threshold=+-{leg.get('threshold')}"
    return str(leg)


@functools.lru_cache(maxsize=32)
def _compute_reference_returns(asset_class: str, tc_bps: int) -> tuple[dict, dict]:
    """Never mutate the returned dicts -- lru_cache hands back the SAME
    object on a cache hit, so callers must copy before adding entries."""
    cfg = get_cfg(asset_class)
    reference_strategies = _build_reference_strategies(cfg)
    data, _, _ = _load_products(asset_class)
    gross: dict[str, pd.Series] = {}
    net: dict[str, pd.Series] = {}
    for instance in reference_strategies:
        g, n = _instance_asset_returns(instance, data, tc_bps)
        if not n.empty:
            gross[instance["label"]] = g
            net[instance["label"]] = n
    return gross, net


def _apply_weight_schedule(returns_by_name: dict, weights_over_time: pd.DataFrame) -> pd.Series:
    names = list(weights_over_time.columns)
    aligned = pd.concat([returns_by_name[k].reindex(weights_over_time.index).fillna(0.0)
                          for k in names], axis=1, keys=names)
    return pd.Series((aligned.values * weights_over_time.values).sum(axis=1), index=weights_over_time.index)


def _combine_sleeves(gross_by_name: dict, net_by_name: dict, combine_method: str,
                      vol_window: int = 63, tilt: float = 0.0) -> tuple[pd.Series, pd.Series]:
    if len(net_by_name) < 2:
        return (combine_returns(list(gross_by_name.values()), "equal_weight"),
                combine_returns(list(net_by_name.values()), "equal_weight"))
    if combine_method == "Inverse Vol":
        return (combine_returns(list(gross_by_name.values()), "inverse_vol", vol_window=vol_window),
                combine_returns(list(net_by_name.values()), "inverse_vol", vol_window=vol_window))
    if combine_method == "Risk Parity (ERC, rolling)":
        net_combined, weights_over_time = rolling_erc_combine(net_by_name, tilt=tilt)
        gross_combined = _apply_weight_schedule(gross_by_name, weights_over_time)
        return gross_combined, net_combined
    return (combine_returns(list(gross_by_name.values()), "equal_weight"),
            combine_returns(list(net_by_name.values()), "equal_weight"))


def _window_metrics(gross: pd.Series, net: pd.Series, yr_start: int, yr_end: int) -> dict:
    def _slice(s):
        return s[(s.index.year >= yr_start) & (s.index.year <= yr_end)].dropna()

    def _sharpe(s):
        return float(s.mean() / s.std(ddof=1) * np.sqrt(252)) if len(s) > 20 and s.std(ddof=1) > 0 else np.nan

    g, n = _slice(gross), _slice(net)
    if len(n) > 20 and n.std(ddof=1) > 0:
        ann = float(n.mean() * 252 * 100)
        vol = float(n.std(ddof=1) * np.sqrt(252) * 100)
    else:
        ann = vol = np.nan
    cum = n.cumsum()
    mdd = float((cum - cum.cummax()).min() * 100) if len(cum) else np.nan
    return dict(gross=_sharpe(g), net=_sharpe(n), ann=ann, vol=vol, mdd=mdd)


def get_reference_strategies(asset_class: str) -> dict:
    cfg = get_cfg(asset_class)
    instances = _build_reference_strategies(cfg)
    return {
        "strategies": [
            {
                "id": inst["id"], "label": inst["label"], "family": inst["family"], "shift_n": inst["shift_n"],
                "legs": inst["legs"],
                "legs_desc": [_describe_leg(inst["family"], leg) for leg in inst["legs"]],
            }
            for inst in instances
        ],
    }


def get_results(
    asset_class: str, *, tc_bps: int = 5,
    combine_method: str = "Equal Weight", vol_window: int = 63, return_tilt: float = 0.0,
    custom_portfolios: list[dict] | None = None,
    yr_start: int | None = None, yr_end: int | None = None,
    metric_strategy: str | None = None, shown: list[str] | None = None,
) -> dict:
    data, common_start, common_end = _load_products(asset_class)
    min_year, max_year = int(common_start.year), int(common_end.year)
    yr_start, yr_end = yr_start or min_year, yr_end or max_year

    ref_gross, ref_net = _compute_reference_returns(asset_class, tc_bps)
    instance_gross, instance_net = dict(ref_gross), dict(ref_net)  # copy: cached dicts must not be mutated

    if instance_net:
        agg_label = f"{combine_method} Portfolio (all reference strategies)"
        agg_gross, agg_net = _combine_sleeves(instance_gross, instance_net, combine_method, vol_window, tilt=return_tilt)
        instance_gross[agg_label] = agg_gross
        instance_net[agg_label] = agg_net

    for portfolio in (custom_portfolios or []):
        gross_by_name, net_by_name = {}, {}
        for sleeve in portfolio["sleeves"]:
            g, n = _instance_asset_returns(sleeve, data, tc_bps)
            if not n.empty:
                label = FAMILY_TITLE[sleeve["family"]]
                gross_by_name[label] = g
                net_by_name[label] = n
        if net_by_name:
            g_combined, n_combined = _combine_sleeves(gross_by_name, net_by_name, combine_method, vol_window, tilt=return_tilt)
            instance_gross[portfolio["label"]] = g_combined
            instance_net[portfolio["label"]] = n_combined

    metric_labels = list(instance_net.keys())
    if not metric_labels:
        return {
            "common_start": str(common_start.date()), "common_end": str(common_end.date()),
            "min_year": min_year, "max_year": max_year, "metric_labels": [],
            "metrics": None, "equity_fig": None, "table_rows": [],
        }

    metric_strategy = metric_strategy if metric_strategy in metric_labels else metric_labels[0]
    shown = [s for s in (shown or []) if s in metric_labels] or metric_labels

    metrics = {k: _clean(v) for k, v in
               _window_metrics(instance_gross[metric_strategy], instance_net[metric_strategy], yr_start, yr_end).items()}

    fig = go.Figure()
    rows = []
    for i, label in enumerate(shown):
        s = instance_net[label]
        window = s[(s.index.year >= yr_start) & (s.index.year <= yr_end)].dropna()
        if window.empty:
            continue
        eq = window.cumsum() * 100
        fig.add_trace(go.Scatter(x=eq.index, y=eq.values, name=label, mode="lines",
                                  line=dict(color=PALETTE[i % len(PALETTE)], width=1.6)))
        if len(window) > 20 and window.std(ddof=1) > 0:
            ret = float(window.mean() * 252 * 100)
            vol = float(window.std(ddof=1) * np.sqrt(252) * 100)
            ir = ret / vol if vol > 0 else float("nan")
        else:
            ret = vol = ir = float("nan")
        rows.append({"strategy": label, "return": _clean(ret), "vol": _clean(vol), "ir": _clean(ir)})

    layout = dict(CHART_LAYOUT)
    layout["yaxis_title"] = "Cumulative Log-Return (%)"
    fig.update_layout(**layout, title=f"Cumulative Equity, {yr_start} to {yr_end}", height=460)

    return {
        "common_start": str(common_start.date()), "common_end": str(common_end.date()),
        "min_year": min_year, "max_year": max_year,
        "metric_labels": metric_labels,
        "metrics": metrics,
        "equity_fig": _fig_to_json(fig),
        "table_rows": rows,
    }
