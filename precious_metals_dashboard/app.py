"""
Precious Metals Dashboard - Stage 2
=====================================
Standalone Streamlit app, its own separate deployment. Gold, Silver,
Platinum, Palladium. Momentum / Carry / Value only, same format as the
Metals/Energy/NGL Stage 2 rebuilds -- reuses the identical shared engine
(common_engine.py) so every dashboard behaves identically. No custom
default overrides are needed here (unlike NGL) -- these are liquid,
standard COMEX/NYMEX futures with a normal front-month convention, so the
Metals/Energy defaults (F1-F2 carry, F8/5yr value) apply unchanged.

Copper (COMEX/HG) removed from this dashboard 2026-08-05 (user's explicit
decision) -- across the product selector, every standalone tab, and the
Portfolio tab. It was miscategorized here originally: Copper is an
industrial metal already covered by the Metals asset class (LME), not a
precious metal. Remains in research/configs/precious.py's own PRODUCTS
list for the research pipeline; this is a dashboard-display-only
exclusion, not an engine change.
"""

import os
import sys

import streamlit as st

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "research"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "research", "configs"))
# 2026-10-31: the Streamlit apps read the latest merged data (29-Oct pull on top of the 24-Sep history), not data/Prices_0924. scripts/rolling_continuous.py reads this env var;
# the research scripts leave it unset and keep their own data folders.
os.environ.setdefault("RP_PRICES_DIR", "Prices_1029_merged")

def _refresh_repo_modules(root=_REPO_ROOT):
    """Streamlit Cloud keeps imported modules alive across a git pull and reloads only files inside the app's own folder, so a push that
    changes a shared module (common_engine, research/*, scripts/*) breaks the running app until someone reboots it. Drop the repo's
    modules when any of their files changed since the last run (and on the first run of a process); the imports below then read the
    current code."""
    current = {}
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and name != "__main__" and os.path.abspath(f).startswith(root + os.sep):
            try:
                current[name] = os.stat(f).st_mtime_ns
            except OSError:
                pass
    previous = getattr(sys, "_rp_module_stamps", None)
    if previous is None or any(previous.get(n, s) != s for n, s in current.items()):
        for name in current:
            sys.modules.pop(name, None)
        sys._rp_module_stamps = dict(current)
    else:
        sys._rp_module_stamps = {**current, **previous}


_refresh_repo_modules()


from common_shared import inject_css, section_header, return_basis_selector, register_geo_inputs
from common_curve_loader import load_curve_simple
from common_engine import (render_momentum_tab, render_carry_tab, render_value_tab, render_skewness_tab,
                           render_comparison_tab)
from rolling_continuous import (get_metal_rolling_f1, reanchor_f1_continuous,
                                 PRECIOUS_CONFIG, PRECIOUS_FUTURES_FILE, PRECIOUS_CALENDAR_FILE)
from rolling_continuous_5td import get_rolling_f1 as get_rolling_f1_5td
from dashboard_portfolio_tab import render_portfolio_tab
import precious as precious_research_cfg

st.set_page_config(
    page_title="Precious Metals Risk Premia - Stage 2",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# unit_label: the product's natural pricing unit, used only for the
# TC-per-flip $ display in the sidebar -- has no effect on the Sharpe/PnL math.
# Copper (HG) removed 2026-08-05 -- see module docstring. Remains in
# research/configs/precious.py's own PRODUCTS list.
PRODUCT_UNITS = {
    "GC": "/oz", "SI": "/oz", "PL": "/oz", "PA": "/oz",
}
PRODUCT_ORDER = ["GC", "SI", "PL", "PA"]
PRECIOUS_PORTFOLIO_EXCLUDED = ("Copper_COMEX",)

with st.sidebar:
    st.markdown('<p class="main-title">✨ Precious Metals Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Stage 2: Momentum, Carry, Value, Skewness</p>', unsafe_allow_html=True)
    st.divider()
    return_basis_selector()
    st.divider()
    product_code = st.radio(
        "Product", PRODUCT_ORDER, key="precious_product_choice",
        format_func=lambda c: PRECIOUS_CONFIG[c]["name"],
    )
    st.divider()
    st.markdown("**Rolling Configuration**")
    roll_method = st.selectbox(
        "Rolling Logic",
        ["N days before last trading day", "Nth trading day of the expiry month"],
        index=1, key="precious_roll_method",   # default: Nth trading day of the expiry month (same roll as the research numbers), 2026-10-11
    )
    roll_n = st.number_input("N", min_value=1, max_value=10, value=5, step=1, key="precious_roll_n")
    st.caption("Gold, Silver, Platinum, Palladium (COMEX/NYMEX). Copper (COMEX) is excluded from "
               "this dashboard as of 2026-08-05; it remains in the underlying research config and "
               "engine. Same Momentum/Carry/Value format as the Metals, Energy, and NGL dashboards.")

cfg = PRECIOUS_CONFIG[product_code]
unit = PRODUCT_UNITS[product_code]

if roll_method == "N days before last trading day":
    f1_df = get_metal_rolling_f1(product_code, futures_file=PRECIOUS_FUTURES_FILE,
                                  calendar_file=PRECIOUS_CALENDAR_FILE, verbose=False,
                                  config=PRECIOUS_CONFIG, roll_day=roll_n)
else:
    f1_df = get_rolling_f1_5td(product_code, futures_file=PRECIOUS_FUTURES_FILE,
                                calendar_file=PRECIOUS_CALENDAR_FILE, verbose=False,
                                config=PRECIOUS_CONFIG, roll_day=roll_n)
if f1_df.empty:
    st.error(f"Could not build F1_continuous for {cfg['name']}.")
    st.stop()
f1_df = reanchor_f1_continuous(f1_df[f1_df.index.year >= 2006])
f1r, f1c = f1_df["F1_raw"], f1_df["F1_continuous"]
phase = f1_df["Phase"]
register_geo_inputs(f1_df)

curve = load_curve_simple(PRECIOUS_FUTURES_FILE, cfg["price_sheet"])
curve = curve[curve.index.year >= 2006]

st.markdown(f'<p class="main-title">✨ Precious Metals Risk Premia: {cfg["name"]}</p>', unsafe_allow_html=True)
st.caption(f"Data: {f1r.index[0].date()} to {f1r.index[-1].date()}. "
           "PnL on F1_continuous, TC on F1_raw, active-day Sharpe, no look-ahead.")

tab_mom, tab_carry, tab_val, tab_skew, tab_compare, tab_portfolio = st.tabs(
    ["⚡ Momentum", "📐 Carry", "📏 Value", "📉 Skewness", "🔀 Comparison", "🧮 Portfolio"])

key_prefix = f"precious_{product_code}"

with tab_mom:
    mom_positions = render_momentum_tab(f1r, f1c, cfg["name"], unit, key_prefix=key_prefix, phase=phase)

with tab_carry:
    carry_positions = render_carry_tab(curve, f1r, f1c, cfg["name"], unit, key_prefix=key_prefix, phase=phase)

with tab_val:
    contracts = [c for c in curve.columns if c.startswith("F") and c[1:].isdigit() and int(c[1:]) <= 15]
    value_positions = render_value_tab(curve, f1r, f1c, cfg["name"], unit, key_prefix=key_prefix,
                                        contracts=contracts, phase=phase)

with tab_skew:
    skew_positions = render_skewness_tab(f1r, f1c, cfg["name"], unit, key_prefix=key_prefix, phase=phase,
                                       f2r=f1_df["F2_raw"])

with tab_compare:
    render_comparison_tab(f1r, f1c, cfg["name"], unit, key_prefix=key_prefix, phase=phase,
                           strategy_groups={"Momentum": mom_positions, "Carry": carry_positions,
                                            "Value": value_positions, "Skewness": skew_positions})

with tab_portfolio:
    st.caption("Combines 4 Precious Metals products (Gold, Silver, Platinum, Palladium) into one "
               "asset-class-level portfolio, independent of the sidebar's Product selection "
               "above, which only affects the Momentum/Carry/Value/Skewness/Comparison tabs. Copper (COMEX) "
               "is excluded here too (dashboard-only, see sidebar note); it still exists in "
               "research/configs/precious.py's own PRODUCTS list for the research pipeline. No "
               "StatArb sleeve for this asset class: tested rigorously across all 10 pairs "
               "(including Gold-Silver and Platinum-Palladium) and found to be a genuine null, so "
               "it was never built here.")
    render_portfolio_tab(precious_research_cfg, key_prefix="precious_portfolio",
                          excluded_products=PRECIOUS_PORTFOLIO_EXCLUDED)
