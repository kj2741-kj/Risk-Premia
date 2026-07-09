"""
Metals Dashboard - Stage 2 (simplified 3-tab rebuild)
========================================================
Standalone Streamlit app, its own separate deployment. LME Copper and
Aluminium, Momentum / Carry / Value only (no Market Overview, Term
Structure, Volume, Statistics, or Portfolio tabs -- those live in the
original Stage 1 dashboard at github.com/kj2741-kj/Metals-Risk-Premia,
untouched). Deliberately simple per spec: MA-crossover momentum only,
Carry V1-V4, Value V1 MA-reversion only. No walk-forward OOS yet.
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
from rolling_continuous import get_metal_rolling_f1, METALS_CONFIG, METALS_FUTURES_FILE, METALS_CALENDAR_FILE
from rolling_continuous_5td import get_rolling_f1 as get_rolling_f1_5td

st.set_page_config(
    page_title="Metals Risk Premia - Stage 2",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# Data refreshed through 2026-06-30 (data/06-30/Metals_Futures_Curve_Updated.xlsx,
# same "simple" single-header-row format as Energy/Precious). Replaces the older
# "Metals Futures Curve.csv" (Copper LME sheet there stopped 2025-12-31).
CURVE_FILE = METALS_FUTURES_FILE
CALENDAR_FILE = METALS_CALENDAR_FILE

METAL_OPTIONS = {
    "Copper": {"code": "LP", "curve_sheet": METALS_CONFIG["LP"]["price_sheet"], "unit": "/MT"},
    "Aluminium": {"code": "LA", "curve_sheet": METALS_CONFIG["LA"]["price_sheet"], "unit": "/MT"},
}

with st.sidebar:
    st.markdown('<p class="main-title">⚙️ Metals Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Stage 2 — Momentum, Carry, Value</p>', unsafe_allow_html=True)
    st.divider()
    metal = st.radio("Metal", list(METAL_OPTIONS.keys()), key="metal_choice")
    st.divider()
    st.markdown("**Rolling Configuration**")
    roll_method = st.selectbox(
        "Rolling Logic",
        ["N days before last trading day", "Nth trading day of the month"],
        index=0, key="metals_roll_method",
    )
    roll_n = st.number_input("N", min_value=1, max_value=10, value=5, step=1, key="metals_roll_n")
    st.caption("Full 10-tab Stage 1 dashboard (Market Overview, Portfolio, etc.) lives at the original "
               "Metals-Risk-Premia deployment — this is the simplified Stage 2 rebuild, matching the "
               "format used for Energy / Precious Metals / NGL.")

cfg = METAL_OPTIONS[metal]

if roll_method == "N days before last trading day":
    f1_df = get_metal_rolling_f1(cfg["code"], futures_file=CURVE_FILE, calendar_file=CALENDAR_FILE,
                                  verbose=False, config=METALS_CONFIG, roll_day=roll_n)
else:
    f1_df = get_rolling_f1_5td(cfg["code"], futures_file=CURVE_FILE, calendar_file=CALENDAR_FILE,
                                verbose=False, config=METALS_CONFIG, roll_day=roll_n)
if f1_df.empty:
    st.error(f"Could not build F1_continuous for {metal}. Check data/06-30/Metals_Futures_Curve_Updated.xlsx "
             "and the expiry calendar file paths.")
    st.stop()
f1_df = f1_df[f1_df.index.year >= 2006]
f1r, f1c = f1_df["F1_raw"], f1_df["F1_continuous"]

curve = load_curve_simple(CURVE_FILE, cfg["curve_sheet"])
curve = curve[curve.index.year >= 2006]

st.markdown(f'<p class="main-title">⚙️ Metals Risk Premia — {metal}</p>', unsafe_allow_html=True)
st.caption(f"Data: {f1r.index[0].date()} to {f1r.index[-1].date()}. "
           "PnL on F1_continuous, TC on F1_raw, active-day Sharpe, no look-ahead.")

tab_mom, tab_carry, tab_val = st.tabs(["⚡ Momentum", "📐 Carry", "📏 Value"])

with tab_mom:
    render_momentum_tab(f1r, f1c, metal, cfg["unit"], key_prefix=f"metals_{cfg['code']}")

with tab_carry:
    render_carry_tab(curve, f1r, f1c, metal, cfg["unit"], key_prefix=f"metals_{cfg['code']}")

with tab_val:
    contracts = [c for c in curve.columns if c.startswith("F") and int(c[1:]) <= 15]
    render_value_tab(curve, f1r, f1c, metal, cfg["unit"], key_prefix=f"metals_{cfg['code']}", contracts=contracts)
