"""
Reusable Portfolio tab for the asset-class dashboards.

Provides per-strategy-family leg customization (add, remove, and tweak legs;
choose how legs combine), a year-range slider that reshapes performance
metrics and the cumulative equity curve, and an equal-weight portfolio
builder over whichever strategy instances are selected.

Built on research/engine.py's log-return methodology rather than
common_engine.py's dollar-PnL convention, because portfolio construction
requires unit-normalized returns to combine legs, products, and strategies
correctly (see project_risk_premia_research_framework memory #16).
Consequently, the figures on this tab will not reconcile exactly with the
dollar-PnL Momentum, Carry, Value, and Comparison tabs elsewhere on the same
dashboard; the tab discloses this to the user directly.

Piloted on Metals (metals_dashboard/app.py). render_portfolio_tab() takes an
asset-class config module (research/configs/metals.py, or a future sibling
precious.py, energy.py, or ngl.py exposing the same interface: PRODUCTS,
load_curve(product), load_f1_series_logret(product), and the ex-ante
MOMENTUM_*, CARRY_*, and VALUE_* constants) plus a key_prefix for Streamlit
widget keys. Nothing here is Metals-specific, so the remaining three
dashboards can add the same tab later by importing their own config.

Combine-method roadmap: ship equal weight only for now; add inverse-vol and
risk-parity combiners once this tab has been reviewed and tested.
combine_returns() and combine_positions() in research/engine.py already
accept a method and weights argument for that purpose, but the UI exposes
only equal weight today.
"""

from __future__ import annotations

import os
import sys
import uuid

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
_RESEARCH_DIR = os.path.join(_REPO_ROOT, "research")
_RESEARCH_CONFIGS_DIR = os.path.join(_RESEARCH_DIR, "configs")
for _p in (_REPO_ROOT, _RESEARCH_DIR, _RESEARCH_CONFIGS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common_shared import CHART_LAYOUT, section_header  # noqa: E402
from engine import (combine_positions, combine_returns, exec_shift,  # noqa: E402
                     log_return_daily, raw_signal_carry_v1, raw_signal_carry_v2,
                     raw_signal_carrymom, raw_signal_momentum, raw_signal_value)

FAR_NEAR_OPTIONS = [f"F{i}" for i in range(1, 16)]

FAMILY_LEG_COLUMNS = {
    "Momentum": ["fast", "slow"],
    "Carry": ["type", "near", "far", "zwindow"],
    "CarryMom": ["near", "far", "horizon"],
    "Value": ["contract", "lookback", "threshold"],
}

DEFAULT_LEG = {
    "Momentum": {"fast": 5, "slow": 60},
    "Carry": {"type": "V1 Level", "near": "F1", "far": "F3", "zwindow": 252},
    "CarryMom": {"near": "F1", "far": "F3", "horizon": 20},
    "Value": {"contract": "F8", "lookback": 1260, "threshold": 0.10},
}

DEFAULT_SHIFT_N = {"Momentum": 1, "Carry": 1, "CarryMom": 1, "Value": 2}

PALETTE = ["#B87333", "#C9A84C", "#3D8F8A", "#5BAD72", "#B85450",
           "#A07898", "#6A6460", "#9BAAB3", "#7A8E9A", "#C8D0D8"]


# Data loading. This is the one genuinely expensive step (Excel parsing plus
# roll-adjustment across every product), so it is cached and the rest of the
# tab recomputes freely on every widget interaction.

@st.cache_data(show_spinner="Loading asset-class data for Portfolio tab...")
def _load_products(_cfg, cfg_name: str):
    """Load curve and log-return F1 series for every product in
    _cfg.PRODUCTS, then truncate all of them to the common date window
    across products (the latest start, the earliest end). This matches the
    convention already used by research/run_regime_table.py's build_table(),
    so the figures here are directly comparable to the regime-table results
    already reported elsewhere. `cfg_name` is a plain string so Streamlit's
    cache has something hashable to key on; the leading underscore on `_cfg`
    tells it to skip hashing the module object itself.
    """
    data = {}
    for product in _cfg.PRODUCTS:
        f1 = _cfg.load_f1_series_logret(product)
        curve = _cfg.load_curve(product)
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


def _build_default_instances(cfg) -> list[dict]:
    """Seed the six strategy instances that match the locked ex-ante
    parameter set exactly, so the tab opens showing today's official
    numbers before any customization."""
    instances = [{
        "id": "mom", "family": "Momentum", "label": "Momentum",
        "legs": [{"fast": f, "slow": s} for f, s in cfg.MOMENTUM_PAIRS],
        "shift_n": cfg.MOMENTUM_SHIFT_N, "combine_method": "equal_weight",
        "shared_tenor": None,
    }]
    for near, far in cfg.CARRY_TENOR_PAIRS:
        instances.append({
            "id": f"carry_{near}{far}", "family": "Carry", "label": f"Carry ({near}-{far})",
            "legs": [{"type": "V1 Level", "near": near, "far": far, "zwindow": cfg.CARRY_ZSCORE_WINDOW},
                     {"type": "V2 Z-score", "near": near, "far": far, "zwindow": cfg.CARRY_ZSCORE_WINDOW}],
            "shift_n": cfg.CARRY_SHIFT_N, "combine_method": "equal_weight",
            "shared_tenor": True,
        })
    for near, far in cfg.CARRY_TENOR_PAIRS:
        instances.append({
            "id": f"carrymom_{near}{far}", "family": "CarryMom", "label": f"CarryMom ({near}-{far})",
            "legs": [{"near": near, "far": far, "horizon": cfg.CARRY_MOMENTUM_HORIZON}],
            "shift_n": cfg.CARRY_MOMENTUM_SHIFT_N, "combine_method": "equal_weight",
            "shared_tenor": True,
        })
    instances.append({
        "id": "value", "family": "Value", "label": "Value",
        "legs": [{"contract": cfg.VALUE_CONTRACT, "lookback": cfg.VALUE_LOOKBACK_DAYS,
                  "threshold": cfg.VALUE_THRESHOLD}],
        "shift_n": cfg.VALUE_SHIFT_N, "combine_method": "equal_weight",
        "shared_tenor": None,
    })
    return instances


# Leg and dataframe conversion (for st.data_editor), plus signal dispatch.

def _legs_to_df(family: str, legs: list[dict]) -> pd.DataFrame:
    cols = FAMILY_LEG_COLUMNS[family]
    if not legs:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame([{c: leg.get(c) for c in cols} for leg in legs])[cols]


def _df_to_legs(family: str, df: pd.DataFrame) -> list[dict]:
    cols = FAMILY_LEG_COLUMNS[family]
    legs = []
    for _, row in df.iterrows():
        leg = {c: row[c] for c in cols if c in row.index and pd.notna(row[c])}
        if leg:
            legs.append(leg)
    return legs


def _safe_index(options: list, value, fallback: int = 0) -> int:
    return options.index(value) if value in options else fallback


def _column_config(cols: list[str]) -> dict:
    cfgmap = {
        "fast": st.column_config.NumberColumn("Fast MA", min_value=1, max_value=500, step=1),
        "slow": st.column_config.NumberColumn("Slow MA", min_value=2, max_value=500, step=1),
        "type": st.column_config.SelectboxColumn("Type", options=["V1 Level", "V2 Z-score"]),
        "near": st.column_config.SelectboxColumn("Near", options=FAR_NEAR_OPTIONS),
        "far": st.column_config.SelectboxColumn("Far", options=FAR_NEAR_OPTIONS),
        "zwindow": st.column_config.NumberColumn("Z-Window (V2 only)", min_value=20, max_value=756, step=1),
        "horizon": st.column_config.NumberColumn("Horizon", min_value=1, max_value=252, step=1),
        "contract": st.column_config.SelectboxColumn("Contract", options=FAR_NEAR_OPTIONS),
        "lookback": st.column_config.NumberColumn("Lookback (days)", min_value=20, max_value=2520, step=1),
        "threshold": st.column_config.NumberColumn("Threshold", min_value=0.0, max_value=1.0,
                                                     step=0.01, format="%.2f"),
    }
    return {c: cfgmap[c] for c in cols if c in cfgmap}


def _leg_raw_signal(family: str, leg: dict, product_data: dict) -> pd.Series:
    """Dispatch one leg to its raw-signal formula.

    A leg with a required field still unset (the row st.data_editor inserts
    the instant a user clicks its add-row control, before any cell is
    filled in) is skipped rather than raised on, so a partially entered row
    never crashes the app; it simply contributes nothing until completed.
    """
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
        if leg.get("type", "V1 Level") == "V1 Level":
            return raw_signal_carry_v1(curve, near, far)
        return raw_signal_carry_v2(curve, near, far, int(leg.get("zwindow") or 252))
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


def _instance_product_net_return(instance: dict, product_data: dict, tc_bps: int) -> pd.Series:
    if not instance["legs"]:
        return pd.Series(dtype=float)
    raws = [_leg_raw_signal(instance["family"], leg, product_data) for leg in instance["legs"]]
    raws = [r for r in raws if not r.empty]
    if not raws:
        return pd.Series(dtype=float)
    combo = raws[0] if len(raws) == 1 else combine_positions(raws, instance.get("combine_method", "equal_weight"))
    pos = exec_shift(combo, int(instance["shift_n"])).fillna(0)
    _, net = log_return_daily(pos, product_data["log_price"], tc_bps, product_data["phase"])
    return net


def _instance_asset_return(instance: dict, data: dict, tc_bps: int) -> pd.Series:
    nets = [_instance_product_net_return(instance, d, tc_bps) for d in data.values()]
    return combine_returns(nets, method="equal_weight")


def _render_instance(instance: dict, key_prefix: str) -> bool:
    """Render one strategy instance's expander. Returns True if the user
    clicked Remove, in which case the caller pops it from the list and
    reruns."""
    family = instance["family"]
    with st.expander(f"{instance['label']} ({family})", expanded=False):
        c1, c2 = st.columns([4, 1])
        with c1:
            instance["label"] = st.text_input("Label", value=instance["label"], key=f"{key_prefix}_label")
        with c2:
            st.write("")
            remove = st.button("Remove", key=f"{key_prefix}_remove", use_container_width=True)

        shared_cols: list[str] = []
        if family in ("Carry", "CarryMom"):
            shared = st.checkbox("Shared tenor pair across legs (uncheck to set near/far per leg)",
                                  value=bool(instance.get("shared_tenor", True)), key=f"{key_prefix}_shared")
            instance["shared_tenor"] = shared
            if shared:
                default_near = instance["legs"][0].get("near", "F1") if instance["legs"] else "F1"
                default_far = instance["legs"][0].get("far", "F3") if instance["legs"] else "F3"
                sc1, sc2 = st.columns(2)
                with sc1:
                    shared_near = st.selectbox("Near", FAR_NEAR_OPTIONS,
                                                index=_safe_index(FAR_NEAR_OPTIONS, default_near),
                                                key=f"{key_prefix}_near")
                with sc2:
                    shared_far = st.selectbox("Far", FAR_NEAR_OPTIONS,
                                               index=_safe_index(FAR_NEAR_OPTIONS, default_far, fallback=2),
                                               key=f"{key_prefix}_far")
                instance["_shared_near"], instance["_shared_far"] = shared_near, shared_far
                shared_cols = ["near", "far"]

        edit_cols = [c for c in FAMILY_LEG_COLUMNS[family] if c not in shared_cols]
        legs_df = _legs_to_df(family, instance["legs"])
        legs_df = legs_df[edit_cols] if not legs_df.empty else pd.DataFrame(columns=edit_cols)

        st.caption("Add or remove legs with the table's own row controls. Each row is averaged "
                    "into this strategy's composite signal.")
        edited = st.data_editor(legs_df, num_rows="dynamic", use_container_width=True,
                                 column_config=_column_config(edit_cols), key=f"{key_prefix}_legs")

        legs = _df_to_legs(family, edited)
        if shared_cols:
            for leg in legs:
                leg["near"], leg["far"] = instance["_shared_near"], instance["_shared_far"]
        instance["legs"] = legs

        cshift, ccombine = st.columns(2)
        with cshift:
            instance["shift_n"] = st.number_input("Execution lag (shift_n)", min_value=0, max_value=5,
                                                    value=int(instance["shift_n"]), step=1,
                                                    key=f"{key_prefix}_shift")
        with ccombine:
            st.selectbox("Combine legs via", ["Equal Weight"], index=0, disabled=True,
                          key=f"{key_prefix}_combine",
                          help="Weighted, inverse-vol, and risk-parity combiners are planned next, "
                               "once this tab has been reviewed and tested.")
            instance["combine_method"] = "equal_weight"

    return remove


def render_portfolio_tab(cfg, key_prefix: str) -> None:
    """Render the full Portfolio tab for one asset class.

    `key_prefix` should be stable and asset-class-level, not tied to
    whichever single product a sidebar radio has selected elsewhere on the
    page, because this tab always combines across every product in
    cfg.PRODUCTS.
    """
    st.caption(
        "Log-return methodology (research/engine.py), not the dollar-PnL convention used by the "
        "Momentum, Carry, Value, and Comparison tabs above. This is deliberate: strategies, "
        "products, and asset classes can only be combined into a portfolio without a "
        "price-level-scale distortion in log-return terms. Figures here will not reconcile "
        "exactly with those other tabs."
    )

    state_key = f"{key_prefix}_pf_instances"
    if state_key not in st.session_state:
        st.session_state[state_key] = _build_default_instances(cfg)
    instances: list[dict] = st.session_state[state_key]

    data, common_start, common_end = _load_products(cfg, cfg.ASSET_CLASS)
    st.caption(f"Common data window across all {len(data)} {cfg.ASSET_CLASS} products: "
               f"{common_start.date()} to {common_end.date()}.")

    tc_bps = st.number_input("Transaction cost (bps, round-trip)", min_value=0, max_value=50,
                              value=5, step=1, key=f"{key_prefix}_pf_tcbps")

    section_header("Strategies")
    to_remove = None
    for i, instance in enumerate(instances):
        if _render_instance(instance, key_prefix=f"{key_prefix}_inst_{instance['id']}"):
            to_remove = i
    if to_remove is not None:
        instances.pop(to_remove)
        st.rerun()

    add_cols = st.columns(4)
    for col, fam in zip(add_cols, ["Momentum", "Carry", "CarryMom", "Value"]):
        with col:
            if st.button(f"Add {fam}", key=f"{key_prefix}_add_{fam}", use_container_width=True):
                instances.append({
                    "id": f"{fam.lower()}_{uuid.uuid4().hex[:6]}", "family": fam, "label": f"{fam} (new)",
                    "legs": [dict(DEFAULT_LEG[fam])], "shift_n": DEFAULT_SHIFT_N[fam],
                    "combine_method": "equal_weight",
                    "shared_tenor": True if fam in ("Carry", "CarryMom") else None,
                })
                st.rerun()

    if not instances:
        st.info("No strategies defined. Add one above.")
        return

    with st.spinner("Computing strategy returns..."):
        instance_returns: dict[str, pd.Series] = {}
        for instance in instances:
            r = _instance_asset_return(instance, data, tc_bps)
            if not r.empty:
                instance_returns[instance["label"]] = r

    if not instance_returns:
        st.warning("No valid strategy output. Check leg parameters: a tenor pair or contract "
                    "that does not exist in the curve data returns an empty series.")
        return

    section_header("Portfolio")
    included = st.multiselect("Include in equal-weight portfolio", list(instance_returns.keys()),
                               default=list(instance_returns.keys()), key=f"{key_prefix}_pf_included")
    if included:
        instance_returns["EW Portfolio"] = combine_returns(
            [instance_returns[k] for k in included], method="equal_weight")

    section_header("Year range, cumulative equity, and metrics")
    min_year, max_year = int(common_start.year), int(common_end.year)
    yr_start, yr_end = st.slider("Year range", min_value=min_year, max_value=max_year,
                                  value=(min_year, max_year), step=1, key=f"{key_prefix}_pf_years")

    shown = st.multiselect("Strategies shown", list(instance_returns.keys()),
                            default=list(instance_returns.keys()), key=f"{key_prefix}_pf_shown")

    fig = go.Figure()
    rows = []
    for i, label in enumerate(shown):
        s = instance_returns[label]
        window = s[(s.index.year >= yr_start) & (s.index.year <= yr_end)].dropna()
        if window.empty:
            continue
        eq = window.cumsum() * 100
        fig.add_trace(go.Scatter(x=eq.index, y=eq.values, name=label, mode="lines",
                                  line=dict(color=PALETTE[i % len(PALETTE)], width=1.6)))
        if len(window) > 20 and window.std(ddof=1) > 0:
            ret = float(window.mean() * 252 * 100)
            vol = float(window.std(ddof=1) * np.sqrt(252) * 100)
            ir = ret / vol if vol > 0 else np.nan
        else:
            ret = vol = ir = np.nan
        rows.append({"Strategy": label, "Return (%/yr)": ret, "Vol (%/yr)": vol, "IR": ir})

    layout = dict(CHART_LAYOUT)
    layout["yaxis_title"] = "Cumulative Log-Return (%)"
    fig.update_layout(**layout, title=f"Cumulative Equity, {yr_start} to {yr_end}", height=460)
    st.plotly_chart(fig, use_container_width=True)

    if rows:
        metrics_df = pd.DataFrame(rows).set_index("Strategy")
        st.dataframe(
            metrics_df.style.format({"Return (%/yr)": "{:+.2f}", "Vol (%/yr)": "{:.2f}", "IR": "{:+.3f}"}),
            use_container_width=True)
