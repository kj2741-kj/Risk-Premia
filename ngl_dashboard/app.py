"""
NGL / Refined Products Dashboard - Stage 2
============================================
Standalone Streamlit app, its own separate deployment. Ethane, Propane,
Butane, Isobutane (Mt Belvieu NGL swaps). Momentum / Carry / Value
only, same format as the Metals and Energy Stage 2 rebuilds -- reuses
the identical shared engine (common_engine.py) so all three dashboards
behave identically.

Ethylene and Propylene (the two Mt Belvieu / Polymer Grade petrochemicals)
removed from this dashboard 2026-08-03 (user's explicit decision), across
the product selector, every standalone tab, and the Portfolio tab -- same
pattern as Singapore Gasoil/Fuel Oil's removal from the Energy dashboard
the same day. Both remain in research/configs/ngl.py's own PRODUCTS list
for the research pipeline; this is a dashboard-display-only exclusion, not
an engine change. Neither product appears in any StatArb pair (research/
configs/energy.py's STATARB_PAIRS, shared with NGL) either, so there is
nothing to change there -- checked before this removal.

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
sys.path.insert(0, os.path.join(_REPO_ROOT, "research"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "research", "configs"))

from common_shared import inject_css, section_header
from common_curve_loader import load_curve_simple
from common_engine import render_momentum_tab, render_carry_tab, render_value_tab, render_comparison_tab
from rolling_continuous import (get_metal_rolling_f1, reanchor_f1_continuous,
                                 NGL_CONFIG, NGL_FUTURES_FILE, NGL_CALENDAR_FILE)
from rolling_continuous_5td import get_rolling_f1 as get_rolling_f1_5td
from dashboard_portfolio_tab import render_portfolio_tab
import ngl as ngl_research_cfg

st.set_page_config(
    page_title="NGL Risk Premia - Stage 2",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# unit_label: the product's natural pricing unit, used only for the
# TC-per-flip $ display in the sidebar -- has no effect on the Sharpe/PnL math.
# Ethylene (PCW) and Propylene (PGP) removed 2026-08-03 -- see module
# docstring. Both remain in research/configs/ngl.py's own PRODUCTS list.
PRODUCT_UNITS = {
    "CAP": "/gal", "BAP": "/gal", "DAE": "/gal", "IBD": "/gal",
}
PRODUCT_ORDER = ["CAP", "BAP", "DAE", "IBD"]
NGL_PORTFOLIO_EXCLUDED = ("Ethylene", "Propylene")

# ── Defaults tuned for NGL/petrochemical products (2026-07-10, re-checked
# after switching to F2-as-front on the same date -- see note below) ────────
# Momentum: best of the 3 fixed benchmark MA pairs, by net Sharpe (full
# history, Lag-1, 5bps) -- the benchmark set itself is untouched, this only
# picks which one is pre-featured in Performance Metrics.
MOMENTUM_DEFAULT_FEATURE = {
    "CAP": (1, 20), "BAP": (20, 250), "DAE": (5, 60), "IBD": (20, 250),
}
# Carry: (F1-F2)/F1 near-tenor roll yield is dominated by front-of-curve
# heating-season seasonality for NGLs, not genuine term structure -- it is
# strongly negative-Sharpe for every NGL ticker. The far-tenor V1 Level
# pair (originally F4-F15, what used to be a separate "V2 Long Slope"
# variant before V1/V2 were merged into one Level signal with a free
# contract pair) -- matching Mark Bogorad's paper2_energy_risk_premia carry
# convention, is positive-Sharpe for 5 of 6 tickers and tracks the paper's
# own Ethane/Propane/Butane results far more closely. Applied uniformly
# (not per-product) to match the existing Metals/Energy convention of one
# fixed default carry set. "V2 (win=252)" here is Z-score (formerly V3,
# renumbered when V1/V2 merged). "V3 (N=20)" is Carry-Momentum (formerly
# V4) -- added to the default set uniformly across all dashboards, matching
# Bouchouev's Virtual Barrels finding that carry-momentum (his eq. 5.3,
# sign(Carry - MA(Carry, n))) was his most robust systematic oil signal
# across "hundreds of different blends," outperforming both plain carry
# and plain momentum standalone.
#
# CHANGED 2026-08-03: tenor pair moved from F4-F15 to F2-F14 (user's
# decision, for a 12-month rather than 11-month span). NOT yet re-verified
# against the near-tenor seasonality finding two paragraphs above -- F2 is
# back in the same front-of-curve region that F1-F2 was rejected from.
# See research/configs/ngl.py's docstring for the same caveat.
CARRY_DEFAULT_ACTIVE = ["V1 (F2-F14)", "V2 (win=252)", "V3 (N=20)"]
CARRY_DEFAULT_FEATURE = "V1 (F2-F14)"
# Value: no NGL-specific override as of 2026-08-03 -- falls back to
# render_value_tab's own default (F3 / 5yr / 10%), same as every other
# dashboard, per the user's explicit decision to force F3 uniformly across
# all four asset classes. (Previously F12/10yr, empirically tuned for NGL;
# that finding is superseded by this decision, not by new evidence.)

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
    st.caption("Ethane/Propane/Butane/Isobutane are Mt Belvieu NGL swaps. Ethylene and Propylene "
               "(the Mt Belvieu / Polymer Grade petrochemicals) are excluded from this dashboard as "
               "of 2026-08-03; both remain in the underlying research config and engine. Same "
               "Momentum/Carry/Value format as the Metals and Energy dashboards.")
    st.caption("Front contract: **F2**, not F1 -- NGL swaps are monthly-averaging instruments where "
               "F1 can be a stale/partial-month price. All Momentum/Carry/Value PnL and the Momentum "
               "signal are based on F2 (rolling into F3).")

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

tab_mom, tab_carry, tab_val, tab_compare, tab_portfolio = st.tabs(
    ["⚡ Momentum", "📐 Carry", "📏 Value", "🔀 Comparison", "🧮 Portfolio"])

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
                                        skip_front_contract=True)

with tab_compare:
    render_comparison_tab(f1r, f1c, cfg["name"], unit, key_prefix=key_prefix, phase=phase,
                           strategy_groups={"Momentum": mom_positions, "Carry": carry_positions,
                                            "Value": value_positions})

with tab_portfolio:
    st.caption("Combines 4 NGL products (Ethane, Propane, Butane, Isobutane) into one "
               "asset-class-level portfolio -- independent of the sidebar's Product selection "
               "above, which only affects the Momentum/Carry/Value/Comparison tabs. Ethylene and "
               "Propylene are excluded here too (dashboard-only, see sidebar note); both still "
               "exist in research/configs/ngl.py's own PRODUCTS list for the research pipeline. "
               "Carry and Carry-Momentum use NGL's single F4-F15 tenor pair, not the Metals-style "
               "two-tier structure. Does not include the StatArb sleeve (the 8-spread cross-asset "
               "book, shared with Energy) -- this tab covers Momentum, Carry, Carry-Momentum, and "
               "Value only.")
    render_portfolio_tab(ngl_research_cfg, key_prefix="ngl_portfolio",
                          excluded_products=NGL_PORTFOLIO_EXCLUDED)
