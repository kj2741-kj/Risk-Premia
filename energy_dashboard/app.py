"""
Energy Dashboard - Stage 2
============================
Standalone Streamlit app, its own separate deployment. WTI Crude, Brent
Crude, RBOB Gasoline, Heating Oil ULSD, Nat Gas Henry Hub, Singapore
Gasoil, Fuel Oil 3.5% Barges. Momentum / Carry / Value only, same
format as the Metals Stage 2 rebuild -- reuses the identical shared
engine (common_engine.py) so both dashboards behave identically.

NOTE: ICE Gasoil London (GO), Singapore Jet Kerosene (SJ), and Naphtha
(NFY) are in the source price data but excluded here -- no usable
expiry-calendar coverage in data/06-30/expiry_calendars_20260701.xlsx
to build F1_continuous for them (GO/NFY: zero contracts with expiry
dates; SJ: too sparse, fails to build). See scripts/rolling_continuous.py
ENERGY_CONFIG for details.
"""

import os
import sys

import streamlit as st

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))

from common_shared import inject_css, section_header
from common_curve_loader import load_curve_simple
from common_engine import render_momentum_tab, render_carry_tab, render_value_tab, render_comparison_tab
from rolling_continuous import (get_metal_rolling_f1, reanchor_f1_continuous,
                                 ENERGY_CONFIG, ENERGY_FUTURES_FILE, ENERGY_CALENDAR_FILE)
from rolling_continuous_5td import get_rolling_f1 as get_rolling_f1_5td

st.set_page_config(
    page_title="Energy Risk Premia - Stage 2",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# unit_label: the product's natural pricing unit, used only for the
# TC-per-flip $ display in the sidebar -- has no effect on the Sharpe/PnL math.
PRODUCT_UNITS = {
    "CL": "/bbl", "CO": "/bbl", "XB": "/gal", "HO": "/gal",
    "NG": "/MMBtu", "QS": "/mt", "FO": "/mt",
}
PRODUCT_ORDER = ["CL", "CO", "XB", "HO", "NG", "QS", "FO"]

with st.sidebar:
    st.markdown('<p class="main-title">🛢️ Energy Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Stage 2 — Momentum, Carry, Value</p>', unsafe_allow_html=True)
    st.divider()
    product_code = st.radio(
        "Product", PRODUCT_ORDER, key="energy_product_choice",
        format_func=lambda c: ENERGY_CONFIG[c]["name"],
    )
    st.divider()
    st.markdown("**Rolling Configuration**")
    roll_method = st.selectbox(
        "Rolling Logic",
        ["N days before last trading day", "Nth trading day of the month"],
        index=0, key="energy_roll_method",
    )
    roll_n = st.number_input("N", min_value=1, max_value=10, value=5, step=1, key="energy_roll_n")
    st.caption("GO (ICE Gasoil London), SJ (Jet Kerosene) and NFY (Naphtha) are excluded — no usable "
               "expiry-calendar coverage to build a continuous series. Same Momentum/Carry/Value format "
               "as the Metals and Precious Metals dashboards.")

cfg = ENERGY_CONFIG[product_code]
unit = PRODUCT_UNITS[product_code]

if roll_method == "N days before last trading day":
    f1_df = get_metal_rolling_f1(product_code, futures_file=ENERGY_FUTURES_FILE,
                                  calendar_file=ENERGY_CALENDAR_FILE, verbose=False,
                                  config=ENERGY_CONFIG, roll_day=roll_n)
else:
    f1_df = get_rolling_f1_5td(product_code, futures_file=ENERGY_FUTURES_FILE,
                                calendar_file=ENERGY_CALENDAR_FILE, verbose=False,
                                config=ENERGY_CONFIG, roll_day=roll_n)
if f1_df.empty:
    st.error(f"Could not build F1_continuous for {cfg['name']}.")
    st.stop()
f1_df = reanchor_f1_continuous(f1_df[f1_df.index.year >= 2006])
f1r, f1c = f1_df["F1_raw"], f1_df["F1_continuous"]
phase = f1_df["Phase"]

curve = load_curve_simple(ENERGY_FUTURES_FILE, cfg["price_sheet"])
curve = curve[curve.index.year >= 2006]

st.markdown(f'<p class="main-title">🛢️ Energy Risk Premia — {cfg["name"]}</p>', unsafe_allow_html=True)
st.caption(f"Data: {f1r.index[0].date()} to {f1r.index[-1].date()}. "
           "PnL on F1_continuous, TC on F1_raw, active-day Sharpe, no look-ahead.")

tab_mom, tab_carry, tab_val, tab_compare = st.tabs(["⚡ Momentum", "📐 Carry", "📏 Value", "🔀 Comparison"])

key_prefix = f"energy_{product_code}"

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
