"""
Agriculture Dashboard - Stage 2
==================================
Standalone Streamlit app, its own separate deployment. Corn, Wheat, Oats,
Rough Rice, Soybean, Soybean Oil, Soybean Meal, Coffee, Cocoa, Orange
Juice, Cotton No.2, Feeder Cattle, Live Cattle, Lean Hogs. Momentum /
Carry / Value only, same format as the Metals/Energy/Precious Metals
Stage 2 rebuilds -- reuses the identical shared engine (common_engine.py)
so all 5 dashboards behave identically.

Data source: data/Prices_0924/ (2026-09-24 Bloomberg pull) -- separate,
newer vintage than the other 4 asset classes' data/06-30/ files.

NOTE: Sugar No.11 (ICE) is in the source price data but excluded here --
no usable expiry-calendar coverage. The Prices_0924 calendar source
(Expiry_Calendars_Updated_2.xlsx) has confirmed corrupted Sugar contract
dates (off-cycle month codes duplicate a real contract's date; 16 recent
contracts share an identical stale date) -- excluded pending a clean
re-pull, not just a dashboard-display choice. See
scripts/rolling_continuous.py's AGRI_CONFIG comment and the
project_agri_expiry_calendar_source_errors memory.

NO PORTFOLIO TAB YET: Carry tenor pairs are not locked for this asset
class (user's explicit decision, 2026-09-29 -- Agri's 14 products range
from F1-F6 to F1-F10 depth, unlike Metals' uniform F1-F27, so no single
pair can be copied from another asset class). The Portfolio tab needs a
fixed Carry/CarryMom sleeve definition to combine across products, which
doesn't exist yet -- adding it now would mean either crashing on an empty
tenor-pair list or silently guessing one. Momentum/Carry/Value/Comparison
tabs below are fully interactive (tenor/lookback pickers live in the UI)
and do not depend on this locked decision at all.
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
                                 AGRI_CONFIG, AGRI_FUTURES_FILE, AGRI_CALENDAR_FILE)
from rolling_continuous_5td import get_rolling_f1 as get_rolling_f1_5td

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
    "C": "¢/bu", "W": "¢/bu", "O": "¢/bu", "RR": "$/cwt", "S": "¢/bu",
    "BO": "¢/lb", "SM": "$/ton", "KC": "¢/lb", "CC": "$/MT", "JO": "¢/lb",
    "CT": "¢/lb", "FC": "¢/lb", "LC": "¢/lb", "LH": "¢/lb",
}
PRODUCT_ORDER = ["C", "W", "O", "RR", "S", "BO", "SM", "KC", "CC", "JO", "CT", "FC", "LC", "LH"]

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
        ["N days before last trading day", "Nth trading day of the month"],
        index=0, key="agri_roll_method",
    )
    roll_n = st.number_input("N", min_value=1, max_value=10, value=5, step=1, key="agri_roll_n")
    st.caption("Sugar No.11 (ICE) is excluded — confirmed corrupted expiry-calendar data in the "
               "2026-09-24 source pull, not a usable roll calendar. No Portfolio tab yet: Carry tenor "
               "pairs aren't locked for this asset class (pending, per-product depth varies F1-F6 to "
               "F1-F10). Momentum/Carry/Value/Comparison below are unaffected — same "
               "Momentum/Carry/Value format as the Metals, Energy, Precious Metals, and NGL dashboards.")

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

tab_mom, tab_carry, tab_val, tab_compare = st.tabs(
    ["⚡ Momentum", "📐 Carry", "📏 Value", "🔀 Comparison"])

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
