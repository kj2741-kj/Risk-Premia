"""
NGL / Refined Products Dashboard - Stage 2
============================================
Standalone Streamlit app, its own separate deployment. Ethane, Propane,
Butane, Isobutane (Mt Belvieu NGL swaps) plus Ethylene, Propylene
(Mt Belvieu / Polymer Grade petrochemicals). Momentum / Carry / Value
only, same format as the Metals and Energy Stage 2 rebuilds -- reuses
the identical shared engine (common_engine.py) so all three dashboards
behave identically.

Ticker note: CAP/BAP/DAE/PCW's price-sheet names in NGL_Futures_Updated.xlsx
were originally mislabeled (cyclically swapped commodities); corrected
2026-07-10 after cross-verification against the Mark Bogorad NGL paper
replication and the expiry calendar file's own (independently correct)
sheet names. See that workbook's README "CORRECTION NOTE" for detail.
"""

import os
import sys

import streamlit as st

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))

from common_shared import inject_css, section_header
from common_curve_loader import load_curve_simple
from common_engine import render_momentum_tab, render_carry_tab, render_value_tab
from rolling_continuous import (get_metal_rolling_f1, reanchor_f1_continuous,
                                 NGL_CONFIG, NGL_FUTURES_FILE, NGL_CALENDAR_FILE)
from rolling_continuous_5td import get_rolling_f1 as get_rolling_f1_5td

st.set_page_config(
    page_title="NGL Risk Premia - Stage 2",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# unit_label: the product's natural pricing unit, used only for the
# TC-per-flip $ display in the sidebar -- has no effect on the Sharpe/PnL math.
PRODUCT_UNITS = {
    "CAP": "/gal", "BAP": "/gal", "DAE": "/gal", "IBD": "/gal",
    "PCW": "/lb", "PGP": "/lb",
}
PRODUCT_ORDER = ["CAP", "BAP", "DAE", "IBD", "PCW", "PGP"]

with st.sidebar:
    st.markdown('<p class="main-title">🧪 NGL Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Stage 2 — Momentum, Carry, Value</p>', unsafe_allow_html=True)
    st.divider()
    product_code = st.radio(
        "Product", PRODUCT_ORDER, key="ngl_product_choice",
        format_func=lambda c: NGL_CONFIG[c]["name"],
    )
    st.divider()
    st.markdown("**Rolling Configuration**")
    roll_method = st.selectbox(
        "Rolling Logic",
        ["N days before last trading day", "Nth trading day of the month"],
        index=0, key="ngl_roll_method",
    )
    roll_n = st.number_input("N", min_value=1, max_value=10, value=5, step=1, key="ngl_roll_n")
    st.caption("Ethane/Propane/Butane/Isobutane are Mt Belvieu NGL swaps; Ethylene/Propylene are "
               "Mt Belvieu / Polymer Grade petrochemical futures. Same Momentum/Carry/Value format "
               "as the Metals and Energy dashboards.")

cfg = NGL_CONFIG[product_code]
unit = PRODUCT_UNITS[product_code]

if roll_method == "N days before last trading day":
    f1_df = get_metal_rolling_f1(product_code, futures_file=NGL_FUTURES_FILE,
                                  calendar_file=NGL_CALENDAR_FILE, verbose=False,
                                  config=NGL_CONFIG, roll_day=roll_n)
else:
    f1_df = get_rolling_f1_5td(product_code, futures_file=NGL_FUTURES_FILE,
                                calendar_file=NGL_CALENDAR_FILE, verbose=False,
                                config=NGL_CONFIG, roll_day=roll_n)
if f1_df.empty:
    st.error(f"Could not build F1_continuous for {cfg['name']}.")
    st.stop()
f1_df = reanchor_f1_continuous(f1_df[f1_df.index.year >= 2006])
f1r, f1c = f1_df["F1_raw"], f1_df["F1_continuous"]
phase = f1_df["Phase"]

curve = load_curve_simple(NGL_FUTURES_FILE, cfg["price_sheet"])
curve = curve[curve.index.year >= 2006]

st.markdown(f'<p class="main-title">🧪 NGL Risk Premia — {cfg["name"]}</p>', unsafe_allow_html=True)
st.caption(f"Data: {f1r.index[0].date()} to {f1r.index[-1].date()}. "
           "PnL on F1_continuous, TC on F1_raw, active-day Sharpe, no look-ahead.")

tab_mom, tab_carry, tab_val = st.tabs(["⚡ Momentum", "📐 Carry", "📏 Value"])

with tab_mom:
    render_momentum_tab(f1r, f1c, cfg["name"], unit, key_prefix=f"ngl_{product_code}", phase=phase)

with tab_carry:
    render_carry_tab(curve, f1r, f1c, cfg["name"], unit, key_prefix=f"ngl_{product_code}", phase=phase)

with tab_val:
    contracts = [c for c in curve.columns if c.startswith("F") and c[1:].isdigit() and int(c[1:]) <= 15]
    render_value_tab(curve, f1r, f1c, cfg["name"], unit, key_prefix=f"ngl_{product_code}",
                      contracts=contracts, phase=phase)
