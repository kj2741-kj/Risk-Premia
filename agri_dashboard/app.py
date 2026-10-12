"""
Agriculture Dashboard - Stage 2
==================================
Standalone Streamlit app, its own separate deployment. Six products only
(Corn, Wheat, Soybean, Soybean Oil, Coffee C, Sugar No.11), the Agriculture
book in Analysis/Final_Research_Dashboard.html. Momentum / Carry / Value /
Comparison tabs plus a Portfolio tab, same format as the Metals, Energy,
Precious Metals and NGL dashboards -- reuses the identical shared engine
(common_engine.py, dashboard_portfolio_tab.py).

Data source: data/Prices_0924/ (2026-09-24 Bloomberg pull). Roll calendar:
Agri_Rolling_Calendar_bloomberg_matched.xlsx (contract months Bloomberg's
generic F1..Fn actually uses; F1 rebuilt from it matches Bloomberg 100%).
This also supplies a clean Sugar calendar, so Sugar is back in.

Carry tenor pair: F1-F2 is the default (the pair locked in the final
dashboard, "no long pair defined yet"). It is only a default: the Carry tab
and the Portfolio tab both let the user pick any (Near, Far) pair for V1, V2
and V3. The other nine products of the original 14-product build (Oats,
Rough Rice, Soybean Meal, Cocoa, Orange Juice, Cotton, Feeder/Live Cattle,
Lean Hogs) are dropped from this dashboard; their calendar and data still
exist in scripts/rolling_continuous.py's AGRI_CONFIG.
"""

import os
import sys

import streamlit as st

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "research"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "research", "configs"))

from common_shared import inject_css, section_header
from common_curve_loader import load_curve_simple
from common_engine import render_momentum_tab, render_carry_tab, render_value_tab, render_comparison_tab
from rolling_continuous import (get_metal_rolling_f1, reanchor_f1_continuous,
                                 AGRI_BBG_CONFIG as AGRI_CONFIG, AGRI_FUTURES_FILE,
                                 AGRI_CALENDAR_FILE_BBG as AGRI_CALENDAR_FILE)
from rolling_continuous_5td import get_rolling_f1 as get_rolling_f1_5td
from dashboard_portfolio_tab import render_portfolio_tab
import agri as agri_research_cfg

st.set_page_config(
    page_title="Agriculture Risk Premia - Stage 2",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# unit_label: the product's natural pricing unit, used only for the
# TC-per-flip $ display in the sidebar -- has no effect on the Sharpe/PnL math.
PRODUCT_UNITS = {
    "C": "¢/bu", "W": "¢/bu", "S": "¢/bu", "BO": "¢/lb", "KC": "¢/lb", "SB": "¢/lb",
}
PRODUCT_ORDER = ["C", "W", "S", "BO", "KC", "SB"]

with st.sidebar:
    st.markdown('<p class="main-title">🌾 Agriculture Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Stage 2 — Momentum, Carry, Value</p>', unsafe_allow_html=True)
    st.divider()
    product_code = st.radio(
        "Product", PRODUCT_ORDER, key="agri_product_choice",
        format_func=lambda c: AGRI_CONFIG[c]["name"],
    )
    st.divider()
    st.markdown("**Rolling Configuration**")
    roll_method = st.selectbox(
        "Rolling Logic",
        ["N days before last trading day", "Nth trading day of the expiry month"],
        index=0, key="agri_roll_method",
    )
    roll_n = st.number_input("N", min_value=1, max_value=10, value=5, step=1, key="agri_roll_n")
    st.caption("Six products, Bloomberg-matched roll calendar. Carry defaults to the F1-F2 pair; "
               "the Carry and Portfolio tabs let you pick any other (Near, Far) pair.")

cfg = AGRI_CONFIG[product_code]
unit = PRODUCT_UNITS[product_code]

if roll_method == "N days before last trading day":
    f1_df = get_metal_rolling_f1(product_code, futures_file=AGRI_FUTURES_FILE,
                                  calendar_file=AGRI_CALENDAR_FILE, verbose=False,
                                  config=AGRI_CONFIG, roll_day=roll_n)
else:
    f1_df = get_rolling_f1_5td(product_code, futures_file=AGRI_FUTURES_FILE,
                                calendar_file=AGRI_CALENDAR_FILE, verbose=False,
                                config=AGRI_CONFIG, roll_day=roll_n)
if f1_df.empty:
    st.error(f"Could not build F1_continuous for {cfg['name']}.")
    st.stop()
f1_df = reanchor_f1_continuous(f1_df[f1_df.index.year >= 2006])
f1r, f1c = f1_df["F1_raw"], f1_df["F1_continuous"]
phase = f1_df["Phase"]

curve = load_curve_simple(AGRI_FUTURES_FILE, cfg["price_sheet"])
curve = curve[curve.index.year >= 2006]

st.markdown(f'<p class="main-title">🌾 Agriculture Risk Premia — {cfg["name"]}</p>', unsafe_allow_html=True)
st.caption(f"Data: {f1r.index[0].date()} to {f1r.index[-1].date()}. "
           "PnL on F1_continuous, TC on F1_raw, active-day Sharpe, no look-ahead.")

tab_mom, tab_carry, tab_val, tab_compare, tab_portfolio = st.tabs(
    ["⚡ Momentum", "📐 Carry", "📏 Value", "🔀 Comparison", "🧮 Portfolio"])

key_prefix = f"agri_{product_code}"

with tab_mom:
    mom_positions = render_momentum_tab(f1r, f1c, cfg["name"], unit, key_prefix=key_prefix, phase=phase)

with tab_carry:
    carry_positions = render_carry_tab(curve, f1r, f1c, cfg["name"], unit, key_prefix=key_prefix, phase=phase)

with tab_val:
    contracts = [c for c in curve.columns if c.startswith("F") and c[1:].isdigit() and int(c[1:]) <= 15]
    value_positions = render_value_tab(curve, f1r, f1c, cfg["name"], unit, key_prefix=key_prefix,
                                        contracts=contracts, phase=phase)

with tab_compare:
    render_comparison_tab(f1r, f1c, cfg["name"], unit, key_prefix=key_prefix, phase=phase,
                           strategy_groups={"Momentum": mom_positions, "Carry": carry_positions,
                                            "Value": value_positions})

with tab_portfolio:
    st.caption("Combines the 6 Agriculture products (Corn, Wheat, Soybean, Soybean Oil, Coffee, Sugar) "
               "into one asset-class-level portfolio, independent of the sidebar's Product selection above, "
               "which only affects the Momentum/Carry/Value/Comparison tabs. Carry and Carry momentum default "
               "to the F1-F2 pair; change Near/Far in Portfolio Construction below to use another tenor.")
    render_portfolio_tab(agri_research_cfg, key_prefix="agri_portfolio")
