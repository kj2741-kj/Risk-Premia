"""
Reusable Portfolio tab for the asset-class dashboards.

Two parts. Reference Strategies: the six locked, officially reported
strategy configurations (Momentum, Carry F1-F3, Carry F1-F13, CarryMom
F1-F3, CarryMom F1-F13, Value), shown read-only as a comparison baseline.
Portfolio Construction: a single draft spanning all four strategy families
(Momentum, Carry, Carry-Momentum, Value), each off by default. Toggling a
family on reveals its own editable leg list; leaving a family off excludes
it entirely. One Add Portfolio button combines whichever families are
toggled on -- equal-weighted at the return level if more than one -- into
a new, named, comparable entry, then resets the draft.

A year-range slider, a performance-metrics card section styled like the
standalone Momentum/Carry/Value tabs, and a cumulative equity chart draw
from the combined pool of reference strategies, the reference EW Portfolio,
and every custom portfolio the user has added.

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

from common_shared import CHART_LAYOUT, metric_card, section_header  # noqa: E402
from engine import (combine_positions, combine_returns, exec_shift,  # noqa: E402
                     log_return_daily, raw_signal_carry_v1, raw_signal_carry_v2,
                     raw_signal_carrymom, raw_signal_momentum, raw_signal_value)
from risk_parity import rolling_erc_combine  # noqa: E402

COMBINE_METHODS = ["Equal Weight", "Risk Parity (ERC, rolling)"]

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


# Leg construction, shared by the reference strategies and the draft sleeves.

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


def _build_reference_strategies(cfg) -> list[dict]:
    """The six locked, officially reported strategy configurations. Fixed
    and read-only: not a starting point to edit in place, so the numbers
    already reported elsewhere for this asset class always stay
    reproducible on this tab."""
    instances = [{
        "id": "mom", "family": "Momentum", "label": "Momentum",
        "legs": [{"leg_id": uuid.uuid4().hex[:8], "fast": f, "slow": s} for f, s in cfg.MOMENTUM_PAIRS],
        "shift_n": cfg.MOMENTUM_SHIFT_N, "combine_method": "equal_weight",
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
        })
    for near, far in cfg.CARRY_TENOR_PAIRS:
        instances.append({
            "id": f"carrymom_{near}{far}", "family": "CarryMom", "label": f"CarryMom ({near}-{far})",
            "legs": [{"leg_id": uuid.uuid4().hex[:8], "near": near, "far": far,
                      "horizon": cfg.CARRY_MOMENTUM_HORIZON}],
            "shift_n": cfg.CARRY_MOMENTUM_SHIFT_N, "combine_method": "equal_weight",
        })
    instances.append({
        "id": "value", "family": "Value", "label": "Value",
        "legs": [{"leg_id": uuid.uuid4().hex[:8], "contract": cfg.VALUE_CONTRACT,
                  "lookback": cfg.VALUE_LOOKBACK_DAYS, "threshold": cfg.VALUE_THRESHOLD}],
        "shift_n": cfg.VALUE_SHIFT_N, "combine_method": "equal_weight",
    })
    return instances


def _default_sleeve(family: str) -> dict:
    """A blank, disabled draft sleeve for one strategy family. `enabled`
    starts False and `legs` starts empty -- a family contributes nothing to
    the portfolio being built until the user explicitly switches it on."""
    return {
        "family": family, "enabled": False, "legs": [],
        "shift_n": DEFAULT_SHIFT_N[family], "combine_method": "equal_weight",
        "shared_tenor": True if family in ("Carry", "CarryMom") else None,
    }


def _reference_leg_seed(cfg, family: str) -> list[dict]:
    """The official reference leg configuration for one family, used to
    pre-fill a draft sleeve the moment it is switched on -- so toggling a
    family on and clicking Add Portfolio with no further edits reproduces
    that family's own reference strategy exactly, directly answering "can I
    just add from the reference strategies". Carry and Carry-Momentum use
    the FIRST locked tenor pair (matching "Carry (F1-F3)"/"CarryMom
    (F1-F3)"); a second tenor variant, where the asset class has one, stays
    available as its own reference row for comparison, not as a second
    slot within one portfolio -- a portfolio has at most one Carry sleeve
    and one Carry-Momentum sleeve at a time, by design."""
    if family == "Momentum":
        return [{"leg_id": uuid.uuid4().hex[:8], "fast": f, "slow": s} for f, s in cfg.MOMENTUM_PAIRS]
    near, far = cfg.CARRY_TENOR_PAIRS[0] if getattr(cfg, "CARRY_TENOR_PAIRS", None) else ("F1", "F3")
    if family == "Carry":
        return [
            {"leg_id": uuid.uuid4().hex[:8], "type": "V1 Level", "near": near, "far": far,
             "zwindow": cfg.CARRY_ZSCORE_WINDOW, "horizon": cfg.CARRY_MOMENTUM_HORIZON},
            {"leg_id": uuid.uuid4().hex[:8], "type": "V2 Z-score", "near": near, "far": far,
             "zwindow": cfg.CARRY_ZSCORE_WINDOW, "horizon": cfg.CARRY_MOMENTUM_HORIZON},
        ]
    if family == "CarryMom":
        return [{"leg_id": uuid.uuid4().hex[:8], "near": near, "far": far,
                 "horizon": cfg.CARRY_MOMENTUM_HORIZON}]
    if family == "Value":
        return [{"leg_id": uuid.uuid4().hex[:8], "contract": cfg.VALUE_CONTRACT,
                 "lookback": cfg.VALUE_LOOKBACK_DAYS, "threshold": cfg.VALUE_THRESHOLD}]
    raise ValueError(f"Unknown family {family!r}")


def _reference_shift_n(cfg, family: str) -> int:
    return {"Momentum": cfg.MOMENTUM_SHIFT_N, "Carry": cfg.CARRY_SHIFT_N,
            "CarryMom": cfg.CARRY_MOMENTUM_SHIFT_N, "Value": cfg.VALUE_SHIFT_N}[family]


def _blank_draft() -> dict:
    return {family: _default_sleeve(family) for family in FAMILY_ORDER}


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
    """Gross and net daily log-return contribution of one strategy family
    (a reference strategy or a draft sleeve) on one product."""
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
    """Gross and net asset-class-level return for one strategy family,
    equal-weighted across every product in `data`."""
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


@st.cache_data(show_spinner="Computing reference strategy returns...")
def _compute_reference_returns(_cfg, cfg_name: str, tc_bps: int) -> tuple[dict[str, pd.Series], dict[str, pd.Series]]:
    """Gross/net return series for all six locked reference strategies.

    These never change for a given tc_bps (the six configurations are
    fixed, read-only), so recomputing them on every rerun -- including
    reruns triggered by something unrelated, like ticking a checkbox in
    the draft below -- was pure waste. `cfg_name`/`tc_bps` are the cache
    key; `_cfg`'s leading underscore tells Streamlit to skip hashing the
    module object itself, same convention as _load_products().
    """
    reference_strategies = _build_reference_strategies(_cfg)
    data, _, _ = _load_products(_cfg, cfg_name)
    gross: dict[str, pd.Series] = {}
    net: dict[str, pd.Series] = {}
    for instance in reference_strategies:
        g, n = _instance_asset_returns(instance, data, tc_bps)
        if not n.empty:
            gross[instance["label"]] = g
            net[instance["label"]] = n
    return gross, net


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


def _describe_leg(family: str, leg: dict) -> str:
    """Plain-text summary of one leg's parameters, for the read-only
    display of a reference strategy."""
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
        return (f"contract={leg.get('contract')}, lookback={leg.get('lookback')}d, "
                f"threshold=+-{leg.get('threshold')}")
    return str(leg)


def _render_reference_strategy(instance: dict) -> None:
    """Read-only card for one of the six locked reference strategies."""
    with st.expander(instance["label"], expanded=False):
        for leg in instance["legs"]:
            st.markdown(f"- {_describe_leg(instance['family'], leg)}")
        st.caption(f"Execution lag (shift_n): {instance['shift_n']}  |  Combine legs via: Equal Weight")


# Leg rendering (shared by every editable leg list -- currently only the
# Portfolio Construction draft's sleeves).

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


def _render_draft_sleeve(sleeve: dict, cfg, key_prefix: str) -> None:
    """Render one family's slot in the Portfolio Construction draft: an
    Include toggle, and -- once toggled on -- its editable leg list,
    pre-filled with that family's reference configuration so the family can
    be added exactly as reported with no further edits. A family left off
    contributes nothing when Add Portfolio is clicked."""
    family = sleeve["family"]
    with st.container(border=True):
        enabled = st.checkbox(f"Include {FAMILY_TITLE[family]}", value=sleeve["enabled"],
                               key=f"{key_prefix}_enabled")
        sleeve["enabled"] = enabled
        if not enabled:
            return

        if not sleeve["legs"]:
            sleeve["legs"] = _reference_leg_seed(cfg, family)
            sleeve["shift_n"] = _reference_shift_n(cfg, family)

        st.caption("Pre-filled with the reference parameters for this family -- edit below to "
                   "customize, or leave as-is to use it exactly as reported.")

        shared_near = shared_far = None
        if family in ("Carry", "CarryMom"):
            shared = st.checkbox("Shared tenor pair across legs (uncheck to set near/far per leg)",
                                  value=bool(sleeve.get("shared_tenor", True)), key=f"{key_prefix}_shared")
            sleeve["shared_tenor"] = shared
            if shared:
                default_near = sleeve["legs"][0].get("near", "F1")
                default_far = sleeve["legs"][0].get("far", "F3")
                sc1, sc2 = st.columns(2)
                with sc1:
                    shared_near = st.selectbox("Near", FAR_NEAR_OPTIONS,
                                                index=_safe_index(FAR_NEAR_OPTIONS, default_near),
                                                key=f"{key_prefix}_near")
                with sc2:
                    shared_far = st.selectbox("Far", FAR_NEAR_OPTIONS,
                                               index=_safe_index(FAR_NEAR_OPTIONS, default_far, fallback=2),
                                               key=f"{key_prefix}_far")

        st.caption("Each leg below is averaged into this family's composite signal.")
        leg_to_remove = None
        for leg in sleeve["legs"]:
            if _render_leg(family, leg, key_prefix=f"{key_prefix}_leg_{leg['leg_id']}",
                            shared_near=shared_near, shared_far=shared_far):
                leg_to_remove = leg["leg_id"]
        if leg_to_remove is not None:
            sleeve["legs"] = [leg for leg in sleeve["legs"] if leg["leg_id"] != leg_to_remove]
            st.rerun()

        if st.button("Add leg", key=f"{key_prefix}_addleg"):
            sleeve["legs"].append(_new_leg(family, shared_near or "F1", shared_far or "F3"))
            st.rerun()

        sleeve["shift_n"] = st.number_input("Execution lag (shift_n)", min_value=0, max_value=5,
                                             value=int(sleeve["shift_n"]), step=1, key=f"{key_prefix}_shift")


def _next_portfolio_number(key_prefix: str) -> int:
    counter_key = f"{key_prefix}_portfolio_counter"
    n = st.session_state.get(counter_key, 1)
    st.session_state[counter_key] = n + 1
    return n


def _apply_weight_schedule(returns_by_name: dict[str, pd.Series], weights_over_time: pd.DataFrame) -> pd.Series:
    """Apply an already-solved weight schedule (from rolling_erc_combine's
    second return value) to a second dict of return series sharing the
    same names -- used so gross returns are weighted by the SAME
    risk-parity schedule decided from net returns, rather than solving ERC
    a second time on gross (risk allocation should be decided on the
    tradeable, cost-inclusive series; gross is only for reporting)."""
    names = list(weights_over_time.columns)
    aligned = pd.concat([returns_by_name[k].reindex(weights_over_time.index).fillna(0.0)
                          for k in names], axis=1, keys=names)
    return pd.Series((aligned.values * weights_over_time.values).sum(axis=1), index=weights_over_time.index)


def _reset_sleeve_widget_state(family: str, key_prefix: str) -> None:
    """Reset one family's FIXED widget keys (checkbox, shift, shared-tenor,
    near/far) to their default values, so the draft's data reset is also
    genuinely reflected on screen. Streamlit widgets keep their last value
    by `key` regardless of the `value=`/`index=` argument passed on a later
    rerun, so reassigning the sleeve dict alone would leave the checkbox
    still showing checked.

    Deliberately SETS these keys rather than deleting them (`st.session_
    state[key] = default`, not `.pop(key)`) -- per-leg widget keys are left
    alone entirely and are never reset here. Two reasons: (1) a fresh leg
    always gets a brand-new random leg_id (see _new_leg), so its widget key
    has never been seen before and naturally starts at its own default --
    there is nothing stale to fix; (2) deleting a widget's session_state
    entry in the same run that widget was previously rendered, immediately
    followed by st.rerun(), was found to break Streamlit's own AppTest
    harness (KeyError deep inside its widget-state bookkeeping, not in this
    module) -- setting a value ahead of a widget's next instantiation is
    the standard, safe pattern; deleting mid-lifecycle is not."""
    fam_prefix = f"{key_prefix}_draft_{family}"
    st.session_state[f"{fam_prefix}_enabled"] = False
    st.session_state[f"{fam_prefix}_shift"] = DEFAULT_SHIFT_N[family]
    if family in ("Carry", "CarryMom"):
        st.session_state[f"{fam_prefix}_shared"] = True
        st.session_state[f"{fam_prefix}_near"] = "F1"
        st.session_state[f"{fam_prefix}_far"] = "F3"


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

    data, common_start, common_end = _load_products(cfg, cfg.ASSET_CLASS)
    st.caption(f"Common data window across all {len(data)} {cfg.ASSET_CLASS} products: "
               f"{common_start.date()} to {common_end.date()}.")

    tc_bps = st.number_input("Transaction cost (bps, round-trip)", min_value=0, max_value=50,
                              value=5, step=1, key=f"{key_prefix}_pf_tcbps")

    section_header("Reference strategies")
    st.caption("The officially reported parameter set for this asset class, shown here for "
               "comparison. Read-only -- use Portfolio Construction below to combine them: "
               "switching a family on there pre-fills it with these exact same parameters.")
    reference_strategies = _build_reference_strategies(cfg)
    for instance in reference_strategies:
        _render_reference_strategy(instance)

    section_header("Portfolio construction")
    st.caption("Switch on whichever strategy families belong in this portfolio. Each one "
               "pre-fills with its reference parameters above -- leave it as-is to add that "
               "reference strategy directly, or edit its legs to customize. One family alone "
               "becomes a single-strategy portfolio; several together are combined equal-weight. "
               "Add Portfolio saves the "
               "current draft as a new, comparable entry and clears the draft for the next one.")

    draft_key = f"{key_prefix}_pf_draft"
    reset_pending_key = f"{key_prefix}_pf_draft_reset_pending"

    # Apply any reset requested by a PREVIOUS run's Add Portfolio click here,
    # before any draft widget below is instantiated this run. Clearing a
    # widget's session_state entry in the very same run that widget was
    # rendered (then immediately st.rerun()-ing) is not a safe sequence --
    # deferring the actual clear to the top of the NEXT run, ahead of
    # rendering, keeps every widget's state deleted before it is ever
    # touched in that run rather than mid-lifecycle.
    if st.session_state.get(reset_pending_key):
        for family in FAMILY_ORDER:
            _reset_sleeve_widget_state(family, key_prefix)
        st.session_state[draft_key] = _blank_draft()
        st.session_state[reset_pending_key] = False

    if draft_key not in st.session_state:
        st.session_state[draft_key] = _blank_draft()
    draft: dict = st.session_state[draft_key]

    for family in FAMILY_ORDER:
        _render_draft_sleeve(draft[family], cfg, key_prefix=f"{key_prefix}_draft_{family}")

    portfolios_key = f"{key_prefix}_pf_portfolios"
    st.session_state.setdefault(portfolios_key, [])

    combine_method = st.selectbox(
        "Combine sleeves via", COMBINE_METHODS, index=0, key=f"{key_prefix}_pf_combine_method",
        help="Equal Weight: fixed equal capital split. Risk Parity (ERC): each sleeve "
             "contributes equal RISK, using a covariance matrix rolled forward every ~21 "
             "trading days from the trailing 252 days -- only matters with 2+ families enabled; "
             "with a single family it is identical to Equal Weight.")

    return_tilt = 0.0
    if combine_method == "Risk Parity (ERC, rolling)":
        return_tilt = st.slider(
            "Return tilt", min_value=0.0, max_value=1.0, value=0.0, step=0.05,
            key=f"{key_prefix}_pf_return_tilt",
            help="0 = pure Equal Risk Contribution (risk only, no return awareness). Sliding "
                 "up blends in a risk budget proportional to each sleeve's own trailing Sharpe "
                 "(same rolling window as the covariance, never looking ahead) -- a weak or "
                 "negative-Sharpe sleeve still keeps a small floor of risk budget rather than "
                 "being fully excluded, so even tilt=1 stays diversified, not concentrated in "
                 "a single sleeve. Trailing Sharpe over any one rolling window is a genuinely "
                 "noisy estimate -- this does not guarantee a higher return, it only tilts risk "
                 "toward whichever sleeve looked stronger recently.")

    if st.button("Add Portfolio", key=f"{key_prefix}_add_portfolio", type="primary"):
        enabled_sleeves = [draft[f] for f in FAMILY_ORDER if draft[f]["enabled"] and draft[f]["legs"]]
        if not enabled_sleeves:
            st.warning("Switch on at least one strategy family with at least one leg before adding a portfolio.")
        else:
            gross_by_name, net_by_name, sleeve_names = {}, {}, []
            for sleeve in enabled_sleeves:
                g, n = _instance_asset_returns(sleeve, data, tc_bps)
                if not n.empty:
                    label = FAMILY_TITLE[sleeve["family"]]
                    gross_by_name[label] = g
                    net_by_name[label] = n
                    sleeve_names.append(label)
            if not net_by_name:
                st.warning("No valid output from the selected families -- check leg parameters "
                           "(a tenor pair or contract that does not exist in the curve data "
                           "returns an empty series).")
            else:
                if combine_method == "Risk Parity (ERC, rolling)" and len(net_by_name) >= 2:
                    net_combined, weights_over_time = rolling_erc_combine(net_by_name, tilt=return_tilt)
                    gross_combined = _apply_weight_schedule(gross_by_name, weights_over_time)
                    method_note = (f"{combine_method}, tilt={return_tilt:.2f}"
                                   if return_tilt > 0 else combine_method)
                else:
                    gross_combined = combine_returns(list(gross_by_name.values()), "equal_weight")
                    net_combined = combine_returns(list(net_by_name.values()), "equal_weight")
                    method_note = combine_method
                n = _next_portfolio_number(key_prefix)
                st.session_state[portfolios_key].append({
                    "label": f"Portfolio {n}", "sleeves": sleeve_names, "combine_method": method_note,
                    "gross": gross_combined, "net": net_combined,
                })
                st.session_state[reset_pending_key] = True
                st.rerun()

    portfolios: list[dict] = st.session_state[portfolios_key]
    if portfolios:
        section_header("Your portfolios")
        to_remove = None
        for i, p in enumerate(portfolios):
            c1, c2 = st.columns([5, 1])
            with c1:
                method_note = p.get("combine_method", "Equal Weight")
                st.markdown(f"**{p['label']}** -- {' + '.join(p['sleeves'])}  \n"
                            f"<span style='color:#7A7068;font-size:0.82rem'>{method_note}</span>",
                            unsafe_allow_html=True)
            with c2:
                if st.button("Remove", key=f"{key_prefix}_pfremove_{i}", use_container_width=True):
                    to_remove = i
        if to_remove is not None:
            portfolios.pop(to_remove)
            st.rerun()

    instance_gross, instance_net = _compute_reference_returns(cfg, cfg.ASSET_CLASS, tc_bps)

    if instance_net:
        instance_gross["EW Portfolio (all reference strategies)"] = combine_returns(
            list(instance_gross.values()), "equal_weight")
        instance_net["EW Portfolio (all reference strategies)"] = combine_returns(
            list(instance_net.values()), "equal_weight")

    for p in portfolios:
        instance_gross[p["label"]] = p["gross"]
        instance_net[p["label"]] = p["net"]

    if not instance_net:
        st.warning("No valid strategy output.")
        return

    min_year, max_year = int(common_start.year), int(common_end.year)
    metric_labels = list(instance_net.keys())
    metric_default = portfolios[-1]["label"] if portfolios else metric_labels[0]

    # Everything below reads from `applied`, a snapshot only updated when
    # Refresh Results is clicked -- not from the form's live widget values --
    # so editing a leg or toggling a family elsewhere on the page (which
    # reruns the script, as every Streamlit interaction does) redraws this
    # section with UNCHANGED content instead of recomputing it against
    # whatever the slider/dropdown/multiselect happen to be sitting at
    # mid-adjustment. st.form() is what actually suppresses the rerun for
    # the widgets inside it; `applied` is what the drawing code below reads.
    applied_key = f"{key_prefix}_pf_applied"
    if applied_key not in st.session_state:
        st.session_state[applied_key] = {
            "yr_start": min_year, "yr_end": max_year,
            "metric_strategy": metric_default, "shown": list(metric_labels),
        }
    applied = st.session_state[applied_key]

    section_header("Year range, performance metrics, and cumulative equity")
    st.caption("Adjust the controls below, then click Refresh Results to redraw the chart, "
               "table, and metric cards with the new choices -- nothing recomputes until you do.")
    with st.form(key=f"{key_prefix}_pf_results_form"):
        yr_start_input, yr_end_input = st.slider(
            "Year range", min_value=min_year, max_value=max_year,
            value=(applied["yr_start"], applied["yr_end"]), step=1, key=f"{key_prefix}_pf_years")

        default_metric = applied["metric_strategy"] if applied["metric_strategy"] in metric_labels else metric_labels[0]
        metric_strategy_input = st.selectbox(
            "Strategy (for the metric cards below)", metric_labels,
            index=metric_labels.index(default_metric), key=f"{key_prefix}_pf_metric_strategy")

        shown_default = [s for s in applied["shown"] if s in metric_labels] or metric_labels
        shown_input = st.multiselect("Strategies shown (in the chart and table below)", metric_labels,
                                      default=shown_default, key=f"{key_prefix}_pf_shown")

        if st.form_submit_button("Refresh Results", type="primary"):
            st.session_state[applied_key] = {
                "yr_start": yr_start_input, "yr_end": yr_end_input,
                "metric_strategy": metric_strategy_input, "shown": shown_input,
            }
            applied = st.session_state[applied_key]

    yr_start, yr_end = applied["yr_start"], applied["yr_end"]
    metric_strategy = applied["metric_strategy"] if applied["metric_strategy"] in metric_labels else metric_labels[0]
    shown = [s for s in applied["shown"] if s in metric_labels] or metric_labels

    section_header("Performance metrics")
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
