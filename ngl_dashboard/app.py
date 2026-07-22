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

Front-contract note: unlike every other dashboard, this one treats F2 as
the effective front/tradeable contract (F3 as next), not F1 -- NGL swaps
are monthly-averaging instruments where the nominal front contract (F1)
can be a stale/partial-month price. Set via NGL_CONFIG's f1_col/f2_col in
rolling_continuous.py (2026-07-10), matching Mark Bogorad's
paper2_energy_risk_premia NGL_SKIP_FRONT=True convention. The engine's
output is still internally named F1_raw/F1_continuous (generic across all
dashboards) but for this dashboard those values are F2/F2-continuous.
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

# ── Defaults tuned for NGL/petrochemical products (2026-07-10, re-checked
# after switching to F2-as-front on the same date -- see note below) ────────
# Momentum: best of the 3 fixed benchmark MA pairs, by net Sharpe (full
# history, Lag-1, 5bps) -- the benchmark set itself is untouched, this only
# picks which one is pre-featured in Performance Metrics.
MOMENTUM_DEFAULT_FEATURE = {
    "CAP": (1, 20), "BAP": (20, 250), "DAE": (5, 60),
    "IBD": (20, 250), "PCW": (1, 20), "PGP": (1, 20),
}
# Carry: (F1-F2)/F1 near-tenor roll yield is dominated by front-of-curve
# heating-season seasonality for NGLs, not genuine term structure -- it is
# strongly negative-Sharpe for every NGL ticker. The far-tenor V1 Level
# pair (F4-F15) -- what used to be a separate "V2 Long Slope" variant
# before V1/V2 were merged into one Level signal with a free contract
# pair -- matching Mark Bogorad's paper2_energy_risk_premia carry
# convention, is positive-Sharpe for 5 of 6 tickers and tracks the paper's
# own Ethane/Propane/Butane results far more closely. Applied uniformly
# (not per-product) to match the existing Metals/Energy convention of one
# fixed default carry set. "V2 (win=252)" here is Z-score (formerly V3,
# renumbered when V1/V2 merged).
CARRY_DEFAULT_ACTIVE = ["V1 (F4-F15)", "V2 (win=252)"]
CARRY_DEFAULT_FEATURE = "V1 (F4-F15)"
# Value: F12 / 10yr / +-10% (Mark's paper2 convention) ranks top-1-3 of a
# 9-combo grid (F8/F10/F12 x 5yr/7yr/10yr) for 4 of 6 tickers and is never
# negative for any of them, unlike the Metals/Energy default of F8/5yr
# (tuned for Copper), which is flat-to-negative for CAP/IBD/PCW/PGP.
# Applied uniformly for the same reason as Carry above.
VALUE_DEFAULT_ACTIVE = ("F12", "10yr", 0.10)

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
    st.caption("Front contract: **F2**, not F1 -- NGL swaps are monthly-averaging instruments where "
               "F1 can be a stale/partial-month price. All Momentum/Carry/Value PnL and the Momentum "
               "signal are based on F2 (rolling into F3), matching Mark Bogorad's NGL_SKIP_FRONT "
               "convention.")

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

tab_mom, tab_carry, tab_val, tab_compare = st.tabs(["⚡ Momentum", "📐 Carry", "📏 Value", "🔀 Comparison"])

key_prefix = f"ngl_{product_code}"

with tab_mom:
    mom_positions = render_momentum_tab(f1r, f1c, cfg["name"], unit, key_prefix=key_prefix, phase=phase,
                                         default_feature_pair=MOMENTUM_DEFAULT_FEATURE.get(product_code))

with tab_carry:
    carry_positions = render_carry_tab(curve, f1r, f1c, cfg["name"], unit, key_prefix=key_prefix, phase=phase,
                                        default_active_variants=CARRY_DEFAULT_ACTIVE,
                                        default_feature_variant=CARRY_DEFAULT_FEATURE,
                                        skip_front_contract=True)

with tab_val:
    contracts = [c for c in curve.columns if c.startswith("F") and c[1:].isdigit() and int(c[1:]) <= 15]
    value_positions = render_value_tab(curve, f1r, f1c, cfg["name"], unit, key_prefix=key_prefix,
                                        contracts=contracts, phase=phase,
                                        default_active_combo=VALUE_DEFAULT_ACTIVE,
                                        skip_front_contract=True)

with tab_compare:
    render_comparison_tab(f1r, f1c, cfg["name"], unit, key_prefix=key_prefix, phase=phase,
                           strategy_groups={"Momentum": mom_positions, "Carry": carry_positions,
                                            "Value": value_positions})
