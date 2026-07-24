"""
Reusable Portfolio tab for the asset-class dashboards.

Groups strategies by family (Momentum, Carry, Carry-Momentum, Value), each
with its own add/duplicate/remove controls and an explicit, editable leg
list. Provides a year-range slider that reshapes performance metrics and
the cumulative equity curve, a performance-metrics card section matching
the style of the standalone Momentum/Carry/Value tabs, and an equal-weight
portfolio builder over whichever strategy instances are selected.

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

import copy
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

from common_shared import CHART_LAYOUT, metric_card, section_header  # noqa: E402
from engine import (combine_positions, combine_returns, exec_shift,  # noqa: E402
                     log_return_daily, raw_signal_carry_v1, raw_signal_carry_v2,
                     raw_signal_carrymom, raw_signal_momentum, raw_signal_value)

FAR_NEAR_OPTIONS = [f"F{i}" for i in range(1, 16)]
CARRY_TYPES = ["V1 Level", "V2 Z-score", "V3 Carry-Momentum"]

FAMILY_ORDER = ["Momentum", "Carry", "CarryMom", "Value"]
FAMILY_TITLE = {"Momentum": "Momentum", "Carry": "Carry", "CarryMom": "Carry-Momentum", "Value": "Value"}
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


# Strategy instance and leg construction.

def _new_leg(family: str, near: str = "F1", far: str = "F3") -> dict:
    leg_id = uuid.uuid4().hex[:8]
    if family == "Momentum":
        return {"leg_id": leg_id, "fast": 5, "slow": 60}
    if family == "Carry":
        return {"leg_id": leg_id, "type": "V1 Level", "near": near, "far": far,
                "zwindow": 252, "horizon": 20}
    if family == "CarryMom":
        return {"leg_id": leg_id, "near": near, "far": far, "horizon": 20}
    if family == "Value":
        return {"leg_id": leg_id, "contract": "F8", "lookback": 1260, "threshold": 0.10}
    raise ValueError(f"Unknown family {family!r}")


def _new_instance(family: str, near: str = "F1", far: str = "F3") -> dict:
    return {
        "id": f"{family.lower()}_{uuid.uuid4().hex[:6]}", "family": family,
        "label": f"{FAMILY_TITLE[family]} (new)",
        "legs": [_new_leg(family, near, far)],
        "shift_n": DEFAULT_SHIFT_N[family], "combine_method": "equal_weight",
        "shared_tenor": True if family in ("Carry", "CarryMom") else None,
    }


def _duplicate_instance(instance: dict) -> dict:
    clone = copy.deepcopy(instance)
    clone["id"] = f"{instance['family'].lower()}_{uuid.uuid4().hex[:6]}"
    clone["label"] = f"{instance['label']} copy"
    for leg in clone["legs"]:
        leg["leg_id"] = uuid.uuid4().hex[:8]
    return clone


def _build_default_instances(cfg) -> list[dict]:
    """Seed the six strategy instances that match the locked ex-ante
    parameter set exactly, so the tab opens showing today's official
    numbers before any customization."""
    instances = [{
        "id": "mom", "family": "Momentum", "label": "Momentum",
        "legs": [{"leg_id": uuid.uuid4().hex[:8], "fast": f, "slow": s} for f, s in cfg.MOMENTUM_PAIRS],
        "shift_n": cfg.MOMENTUM_SHIFT_N, "combine_method": "equal_weight",
        "shared_tenor": None,
    }]
    for near, far in cfg.CARRY_TENOR_PAIRS:
        instances.append({
            "id": f"carry_{near}{far}", "family": "Carry", "label": f"Carry ({near}-{far})",
            "legs": [
                {"leg_id": uuid.uuid4().hex[:8], "type": "V1 Level", "near": near, "far": far,
                 "zwindow": cfg.CARRY_ZSCORE_WINDOW, "horizon": cfg.CARRY_MOMENTUM_HORIZON},
                {"leg_id": uuid.uuid4().hex[:8], "type": "V2 Z-score", "near": near, "far": far,
                 "zwindow": cfg.CARRY_ZSCORE_WINDOW, "horizon": cfg.CARRY_MOMENTUM_HORIZON},
            ],
            "shift_n": cfg.CARRY_SHIFT_N, "combine_method": "equal_weight",
            "shared_tenor": True,
        })
    for near, far in cfg.CARRY_TENOR_PAIRS:
        instances.append({
            "id": f"carrymom_{near}{far}", "family": "CarryMom", "label": f"CarryMom ({near}-{far})",
            "legs": [{"leg_id": uuid.uuid4().hex[:8], "near": near, "far": far,
                      "horizon": cfg.CARRY_MOMENTUM_HORIZON}],
            "shift_n": cfg.CARRY_MOMENTUM_SHIFT_N, "combine_method": "equal_weight",
            "shared_tenor": True,
        })
    instances.append({
        "id": "value", "family": "Value", "label": "Value",
        "legs": [{"leg_id": uuid.uuid4().hex[:8], "contract": cfg.VALUE_CONTRACT,
                  "lookback": cfg.VALUE_LOOKBACK_DAYS, "threshold": cfg.VALUE_THRESHOLD}],
        "shift_n": cfg.VALUE_SHIFT_N, "combine_method": "equal_weight",
        "shared_tenor": None,
    })
    return instances


def _safe_index(options: list, value, fallback: int = 0) -> int:
    return options.index(value) if value in options else fallback


# Signal dispatch.

def _leg_raw_signal(family: str, leg: dict, product_data: dict) -> pd.Series:
    """Dispatch one leg to its raw-signal formula.

    A leg with a required field still unset is skipped rather than raised
    on, so an incompletely configured leg never crashes the app; it simply
    contributes nothing until completed.
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
    """Gross and net daily log-return contribution of one strategy instance
    on one product."""
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
    """Gross and net asset-class-level return for one instance, equal-weighted
    across every product in `data`."""
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


def _window_metrics(gross: pd.Series, net: pd.Series, yr_start: int, yr_end: int) -> dict:
    """Sharpe, annualized return, vol, and max drawdown over [yr_start, yr_end],
    in the same shape as common_engine.py's pos_metrics_generic() so the
    metric cards read the same way as the standalone tabs. Once returns are
    equal-weighted across products, "active day" is no longer a single
    well-defined concept (a day can be active for one product and flat for
    another), so vol takes the place of the standalone tabs' "% Flat" card.
    """
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


def _fmt(x, fmt_spec: str) -> str:
    return "N/A" if x is None or (isinstance(x, float) and np.isnan(x)) else fmt_spec.format(x)


# Leg rendering.

def _render_leg(family: str, leg: dict, key_prefix: str,
                 shared_near: str | None, shared_far: str | None) -> bool:
    """Render one leg's parameter widgets inline. Returns True if its
    Remove button was clicked."""
    uses_shared = shared_near is not None

    if family == "Momentum":
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            leg["fast"] = st.number_input("Fast MA", min_value=1, max_value=500,
                                           value=int(leg.get("fast", 5)), step=1, key=f"{key_prefix}_fast")
        with c2:
            leg["slow"] = st.number_input("Slow MA", min_value=2, max_value=500,
                                           value=int(leg.get("slow", 60)), step=1, key=f"{key_prefix}_slow")
        with c3:
            st.write("")
            return st.button("Remove", key=f"{key_prefix}_rm", use_container_width=True)

    if family == "Carry":
        widths = [2, 1.6, 1] if uses_shared else [2, 1.3, 1.3, 1.6, 1]
        cols = st.columns(widths)
        i = 0
        with cols[i]:
            leg_type = st.selectbox("Type", CARRY_TYPES,
                                     index=_safe_index(CARRY_TYPES, leg.get("type", "V1 Level")),
                                     key=f"{key_prefix}_type")
            leg["type"] = leg_type
        i += 1
        if uses_shared:
            leg["near"], leg["far"] = shared_near, shared_far
        else:
            with cols[i]:
                leg["near"] = st.selectbox("Near", FAR_NEAR_OPTIONS,
                                            index=_safe_index(FAR_NEAR_OPTIONS, leg.get("near", "F1")),
                                            key=f"{key_prefix}_near")
            i += 1
            with cols[i]:
                leg["far"] = st.selectbox("Far", FAR_NEAR_OPTIONS,
                                           index=_safe_index(FAR_NEAR_OPTIONS, leg.get("far", "F3"), fallback=2),
                                           key=f"{key_prefix}_far")
            i += 1
        with cols[i]:
            if leg_type == "V2 Z-score":
                leg["zwindow"] = st.number_input("Z-Window", min_value=20, max_value=756,
                                                  value=int(leg.get("zwindow") or 252), step=1,
                                                  key=f"{key_prefix}_zwindow")
            elif leg_type == "V3 Carry-Momentum":
                leg["horizon"] = st.number_input("Horizon", min_value=1, max_value=252,
                                                  value=int(leg.get("horizon") or 20), step=1,
                                                  key=f"{key_prefix}_horizon")
            else:
                st.caption("No additional parameter for V1 Level.")
        i += 1
        with cols[i]:
            st.write("")
            return st.button("Remove", key=f"{key_prefix}_rm", use_container_width=True)

    if family == "CarryMom":
        widths = [2.5, 1] if uses_shared else [1.6, 1.6, 1.6, 1]
        cols = st.columns(widths)
        i = 0
        if uses_shared:
            leg["near"], leg["far"] = shared_near, shared_far
        else:
            with cols[i]:
                leg["near"] = st.selectbox("Near", FAR_NEAR_OPTIONS,
                                            index=_safe_index(FAR_NEAR_OPTIONS, leg.get("near", "F1")),
                                            key=f"{key_prefix}_near")
            i += 1
            with cols[i]:
                leg["far"] = st.selectbox("Far", FAR_NEAR_OPTIONS,
                                           index=_safe_index(FAR_NEAR_OPTIONS, leg.get("far", "F3"), fallback=2),
                                           key=f"{key_prefix}_far")
            i += 1
        with cols[i]:
            leg["horizon"] = st.number_input("Horizon", min_value=1, max_value=252,
                                              value=int(leg.get("horizon", 20)), step=1,
                                              key=f"{key_prefix}_horizon")
        i += 1
        with cols[i]:
            st.write("")
            return st.button("Remove", key=f"{key_prefix}_rm", use_container_width=True)

    if family == "Value":
        c1, c2, c3, c4 = st.columns([1.4, 1.6, 1.6, 1])
        with c1:
            leg["contract"] = st.selectbox("Contract", FAR_NEAR_OPTIONS,
                                            index=_safe_index(FAR_NEAR_OPTIONS, leg.get("contract", "F8"), fallback=7),
                                            key=f"{key_prefix}_contract")
        with c2:
            leg["lookback"] = st.number_input("Lookback (days)", min_value=20, max_value=2520,
                                               value=int(leg.get("lookback", 1260)), step=1,
                                               key=f"{key_prefix}_lookback")
        with c3:
            leg["threshold"] = st.number_input("Threshold", min_value=0.0, max_value=1.0,
                                                value=float(leg.get("threshold", 0.10)), step=0.01,
                                                format="%.2f", key=f"{key_prefix}_threshold")
        with c4:
            st.write("")
            return st.button("Remove", key=f"{key_prefix}_rm", use_container_width=True)

    raise ValueError(f"Unknown family {family!r}")


def _render_instance(instance: dict, key_prefix: str) -> str | None:
    """Render one strategy instance card. Returns "remove", "duplicate", or
    None."""
    family = instance["family"]
    action = None
    with st.expander(instance["label"], expanded=False):
        c1, c2, c3 = st.columns([4, 1, 1])
        with c1:
            instance["label"] = st.text_input("Label", value=instance["label"],
                                               key=f"{key_prefix}_label", label_visibility="collapsed")
        with c2:
            if st.button("Duplicate", key=f"{key_prefix}_dup", use_container_width=True):
                action = "duplicate"
        with c3:
            if st.button("Remove", key=f"{key_prefix}_remove", use_container_width=True):
                action = "remove"

        shared_near = shared_far = None
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

        st.caption("Each leg below is averaged into this strategy's composite signal.")
        leg_to_remove = None
        for leg in instance["legs"]:
            if _render_leg(family, leg, key_prefix=f"{key_prefix}_leg_{leg['leg_id']}",
                            shared_near=shared_near, shared_far=shared_far):
                leg_to_remove = leg["leg_id"]
        if leg_to_remove is not None:
            instance["legs"] = [leg for leg in instance["legs"] if leg["leg_id"] != leg_to_remove]
            st.rerun()

        if st.button("Add leg", key=f"{key_prefix}_addleg"):
            instance["legs"].append(_new_leg(family, shared_near or "F1", shared_far or "F3"))
            st.rerun()

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

    return action


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
    pending_remove = pending_duplicate = None
    for family in FAMILY_ORDER:
        st.markdown(f"**{FAMILY_TITLE[family]}**")
        family_indices = [i for i, inst in enumerate(instances) if inst["family"] == family]
        if not family_indices:
            st.caption("No strategies in this family yet.")
        for i in family_indices:
            action = _render_instance(instances[i], key_prefix=f"{key_prefix}_inst_{instances[i]['id']}")
            if action == "remove":
                pending_remove = i
            elif action == "duplicate":
                pending_duplicate = i
        default_near, default_far = (cfg.CARRY_TENOR_PAIRS[0] if getattr(cfg, "CARRY_TENOR_PAIRS", None)
                                      else ("F1", "F3"))
        if st.button(f"Add {FAMILY_TITLE[family]} strategy", key=f"{key_prefix}_add_{family}"):
            instances.append(_new_instance(family, default_near, default_far))
            st.rerun()
        st.divider()

    if pending_remove is not None:
        instances.pop(pending_remove)
        st.rerun()
    if pending_duplicate is not None:
        instances.insert(pending_duplicate + 1, _duplicate_instance(instances[pending_duplicate]))
        st.rerun()

    if not instances:
        st.info("No strategies defined. Add one above.")
        return

    with st.spinner("Computing strategy returns..."):
        instance_gross: dict[str, pd.Series] = {}
        instance_net: dict[str, pd.Series] = {}
        for instance in instances:
            g, n = _instance_asset_returns(instance, data, tc_bps)
            if not n.empty:
                instance_gross[instance["label"]] = g
                instance_net[instance["label"]] = n

    if not instance_net:
        st.warning("No valid strategy output. Check leg parameters: a tenor pair or contract "
                    "that does not exist in the curve data returns an empty series.")
        return

    section_header("Portfolio")
    included = st.multiselect("Include in equal-weight portfolio", list(instance_net.keys()),
                               default=list(instance_net.keys()), key=f"{key_prefix}_pf_included")
    if included:
        instance_gross["EW Portfolio"] = combine_returns(
            [instance_gross[k] for k in included], method="equal_weight")
        instance_net["EW Portfolio"] = combine_returns(
            [instance_net[k] for k in included], method="equal_weight")

    section_header("Year range")
    min_year, max_year = int(common_start.year), int(common_end.year)
    yr_start, yr_end = st.slider("Year range", min_value=min_year, max_value=max_year,
                                  value=(min_year, max_year), step=1, key=f"{key_prefix}_pf_years")

    section_header("Performance metrics")
    metric_labels = list(instance_net.keys())
    metric_default = "EW Portfolio" if "EW Portfolio" in metric_labels else metric_labels[0]
    metric_strategy = st.selectbox("Strategy", metric_labels,
                                    index=metric_labels.index(metric_default),
                                    key=f"{key_prefix}_pf_metric_strategy")
    m = _window_metrics(instance_gross[metric_strategy], instance_net[metric_strategy], yr_start, yr_end)
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    with mc1:
        metric_card("Gross Sharpe", _fmt(m["gross"], "{:+.2f}"))
    with mc2:
        metric_card("Net Sharpe", _fmt(m["net"], "{:+.2f}"))
    with mc3:
        metric_card("Ann Return (Net)", _fmt(m["ann"], "{:+.2f}"), unit="%")
    with mc4:
        metric_card("Ann Vol", _fmt(m["vol"], "{:.2f}"), unit="%")
    with mc5:
        metric_card("Max DD (Net)", _fmt(m["mdd"], "{:+.2f}"), unit="%")
    st.caption("Vol replaces the standalone tabs' \"% Flat\" card here: once returns are "
               "equal-weighted across products, a single day can be active for one product "
               "and flat for another, so \"active day\" no longer has one well-defined meaning.")

    section_header("Cumulative equity")
    shown = st.multiselect("Strategies shown", list(instance_net.keys()),
                            default=list(instance_net.keys()), key=f"{key_prefix}_pf_shown")

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
