"""
Adapter for the Cross-Asset Portfolio page -- mirrors hub/app.py's "Cross-Asset
Portfolio" tab (Cross-Commodity Portfolio, Cross-Asset-Class Portfolio,
Correlation vs Traditional Assets). All math lives in research/
cross_asset_engine.py and research/benchmarks.py, imported unchanged; only the
Streamlit widget orchestration is replaced.

Caching: per-asset-class, per-product signal computation (Excel loading +
Momentum/Carry/CarryMom/Value math) is the only expensive step, cached on
(asset_class, tc_bps) -- the same seam hub/app.py uses via per_product_fetcher.
"""

import functools

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import benchmarks
import cross_asset_engine as cae
from common_shared import CHART_LAYOUT

from services.momentum import _clean, _fig_to_json

PALETTE = ["#B87333", "#C9A84C", "#3D8F8A", "#5BAD72", "#B85450",
           "#A07898", "#6A6460", "#9BAAB3", "#7A8E9A", "#C8D0D8"]

ASSET_LABEL_TO_KEY = {v: k for k, v in cae.ASSET_CLASS_LABELS.items()}
STYLE_LABEL_TO_KEY = {"Momentum": "Momentum", "Carry": "Combined Carry",
                       "CarryMom": "Combined CarryMom", "Value": "Value"}
CC_COMBINE_KEYS = {"Equal Weight": "equal_weight", "Risk Parity": "risk_parity",
                    "Dynamic Risk Parity": "dynamic_risk_parity"}
CN_COMBINE_KEYS = {"Equal Weight": "equal_weight", "Dynamic Risk Parity": "dynamic_risk_parity"}


@functools.lru_cache(maxsize=16)
def _cached_per_product_four_row(asset_class: str, tc_bps: int):
    return cae.per_product_four_row(asset_class, tc_bps)


@functools.lru_cache(maxsize=4)
def _cached_cross_commodity_portfolio(tc_bps: int):
    return cae.cross_commodity_portfolio(tc_bps)


@functools.lru_cache(maxsize=4)
def _cached_cross_commodity_drp(tc_bps: int):
    _, n = cae.cross_commodity_dynamic(tc_bps, tuple(cae.ASSET_CLASSES), cae.STYLE_NAMES, "dynamic_risk_parity")
    return n["Portfolio"]


@functools.lru_cache(maxsize=1)
def _cached_benchmark_returns():
    return benchmarks.load_benchmark_returns()


def get_meta() -> dict:
    return {
        "asset_classes": list(cae.ASSET_CLASS_LABELS.values()),
        "styles": ["Momentum", "Carry", "CarryMom", "Value"],
        "cc_combine_methods": list(CC_COMBINE_KEYS),
        "cn_combine_methods": list(CN_COMBINE_KEYS),
    }


def _window_metrics(gross: pd.Series, net: pd.Series, yr_start: int, yr_end: int) -> dict:
    """hub/app.py::_ca_window_metrics."""
    def _slice(s):
        return s[(s.index.year >= yr_start) & (s.index.year <= yr_end)].dropna()

    def _true_ann_vol(s):
        if len(s) > 20 and s.std(ddof=1) > 0:
            log_ann = float(s.mean() * 252)
            ann = float((np.exp(log_ann) - 1) * 100)
            vol = float(np.expm1(s).std(ddof=1) * np.sqrt(252) * 100)
            return ann, vol
        return np.nan, np.nan

    def _sharpe(ann_pct, vol_pct):
        return float(ann_pct / vol_pct) if pd.notna(vol_pct) and vol_pct > 0 else np.nan

    g, n = _slice(gross), _slice(net)
    gross_ann, gross_vol = _true_ann_vol(g)
    ann, vol = _true_ann_vol(n)
    cum = n.cumsum()
    value = np.exp(cum)
    mdd = float((value / value.cummax() - 1).min() * 100) if len(cum) else np.nan
    return dict(gross=_sharpe(gross_ann, gross_vol), net=_sharpe(ann, vol), ann=ann, vol=vol, mdd=mdd)


def _equity_and_metrics(gross_dict: dict, net_dict: dict, *, yr_start, yr_end, focus, hidden,
                         default_focus: str = "Portfolio", height: int = 440) -> dict:
    """hub/app.py::_render_equity_and_metrics -- metric cards + cumulative
    equity chart + per-line return/vol/IR table."""
    labels = list(net_dict.keys())
    nonempty = [s for s in net_dict.values() if not s.empty]
    if not nonempty:
        return {"empty": True, "labels": labels}
    all_index = nonempty[0].index
    for s in nonempty[1:]:
        all_index = all_index.union(s.index)
    min_year, max_year = int(all_index.min().year), int(all_index.max().year)
    default_start = max(min_year, 2011)

    yr_start = int(yr_start) if yr_start else default_start
    yr_end = int(yr_end) if yr_end else max_year
    yr_start, yr_end = max(min_year, min(yr_start, max_year)), max(min_year, min(yr_end, max_year))
    if focus not in labels:
        focus = default_focus if default_focus in labels else labels[0]
    hidden = set(hidden or [])
    shown = [s for s in labels if s not in hidden]

    m = _window_metrics(gross_dict[focus], net_dict[focus], yr_start, yr_end)

    fig = go.Figure()
    rows = []
    for i, label in enumerate(shown):
        s = net_dict[label]
        window = s[(s.index.year >= yr_start) & (s.index.year <= yr_end)].dropna()
        if window.empty:
            continue
        eq = (np.exp(window.cumsum()) - 1) * 100
        width = 2.6 if label == "Portfolio" else 1.4
        fig.add_trace(go.Scatter(x=eq.index, y=eq.values, name=label, mode="lines",
                                  line=dict(color=PALETTE[i % len(PALETTE)], width=width)))
        if len(window) > 20 and window.std(ddof=1) > 0:
            ret = (np.exp(float(window.mean() * 252)) - 1) * 100
            vol = float(np.expm1(window).std(ddof=1) * np.sqrt(252) * 100)
            ir = ret / vol if vol > 0 else float("nan")
        else:
            ret = vol = ir = float("nan")
        rows.append({"strategy": label, "return": _clean(ret), "vol": _clean(vol), "ir": _clean(ir)})

    layout = dict(CHART_LAYOUT)
    layout["yaxis_title"] = "Cumulative Return (%)"
    fig.update_layout(**layout, title=f"Cumulative Equity, {yr_start} to {yr_end}", height=height)

    return {
        "empty": False, "labels": labels, "min_year": min_year, "max_year": max_year,
        "default_start": default_start, "yr_start": yr_start, "yr_end": yr_end, "focus": focus,
        "shown": shown, "metrics": {k: _clean(v) for k, v in m.items()},
        "equity_fig": _fig_to_json(fig), "table_rows": rows,
    }


def get_cross_commodity(*, tc_bps: int, assets: list[str], styles: list[str], combine: str,
                         yr_start=None, yr_end=None, focus=None, hidden=None) -> dict:
    if len(assets) < 2:
        return {"warning": "Pick at least 2 asset classes."}
    if not styles:
        return {"warning": "Pick at least 1 style."}
    asset_keys = tuple(ASSET_LABEL_TO_KEY[a] for a in assets)
    style_keys = tuple(STYLE_LABEL_TO_KEY[s] for s in styles)
    gross, net = cae.cross_commodity_dynamic(
        tc_bps, asset_keys, style_keys, CC_COMBINE_KEYS[combine],
        per_product_fetcher=_cached_per_product_four_row)
    return _equity_and_metrics(gross, net, yr_start=yr_start, yr_end=yr_end, focus=focus, hidden=hidden)


def get_cross_n(*, tc_bps: int, assets: list[str], combine: str,
                 yr_start=None, yr_end=None, focus=None, hidden=None) -> dict:
    if not 1 <= len(assets) <= 4:
        return {"warning": "Pick between 1 and 4 asset classes."}
    asset_keys = tuple(ASSET_LABEL_TO_KEY[a] for a in assets)
    gross, net = cae.cross_n_portfolio(
        tc_bps, asset_keys, per_product_fetcher=_cached_per_product_four_row,
        combine_method=CN_COMBINE_KEYS[combine])
    return _equity_and_metrics(gross, net, yr_start=yr_start, yr_end=yr_end, focus=focus, hidden=hidden)


def get_correlation(*, tc_bps: int, yr_start=None, yr_end=None, strategies=None) -> dict:
    strat_net = dict(_cached_cross_commodity_portfolio(tc_bps))
    strat_net["Dynamic Risk Parity"] = _cached_cross_commodity_drp(tc_bps)
    bench = _cached_benchmark_returns()

    years = []
    for s in list(strat_net.values()) + list(bench.values()):
        if not s.empty:
            years.append(int(s.index.min().year))
            years.append(int(s.index.max().year))
    min_year, max_year = min(years), max(years)
    default_start = max(min_year, 2011)
    yr_start = int(yr_start) if yr_start else default_start
    yr_end = int(yr_end) if yr_end else max_year

    all_labels = list(strat_net.keys())
    strategies = [s for s in (strategies if strategies is not None else all_labels) if s in all_labels]

    out = {"min_year": min_year, "max_year": max_year, "default_start": default_start,
           "yr_start": yr_start, "yr_end": yr_end, "strategy_labels": all_labels, "strategies": strategies,
           "fig": None, "warning": None}
    if not strategies:
        out["warning"] = "Pick at least 1 strategy to show."
        return out

    bench_labels = list(bench.keys())
    z, text = [], []
    for name in strategies:
        s = strat_net[name]
        s = s[(s.index.year >= yr_start) & (s.index.year <= yr_end)].dropna()
        z_row, t_row = [], []
        for b_name in bench_labels:
            b = bench[b_name]
            b = b[(b.index.year >= yr_start) & (b.index.year <= yr_end)]
            idx = s.index.intersection(b.index)
            if len(idx) > 20:
                c = float(s.loc[idx].corr(b.loc[idx]))
                z_row.append(c)
                t_row.append(f"{c:+.2f}")
            else:
                z_row.append(None)
                t_row.append("N/A")
        z.append(z_row)
        text.append(t_row)

    fig = go.Figure(data=go.Heatmap(
        z=z, x=bench_labels, y=strategies,
        colorscale=[[0, "#e34948"], [0.5, "#f0efec"], [1, "#2a78d6"]],
        zmin=-1, zmax=1, zmid=0,
        text=text, texttemplate="%{text}", textfont=dict(size=12, color="#111111"),
        colorbar=dict(title="Correlation"),
        hovertemplate="%{y} vs %{x}: %{z:+.3f}<extra></extra>",
    ))
    layout = dict(CHART_LAYOUT)
    layout.pop("yaxis", None)
    fig.update_layout(**layout, title=f"Correlation Matrix, {yr_start} to {yr_end}", height=380)
    out["fig"] = _fig_to_json(fig)
    return out
