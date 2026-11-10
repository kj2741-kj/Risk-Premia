"""
Agriculture Dashboard - Stage 2
==================================
Standalone Streamlit app, its own separate deployment. Four products (Corn, Wheat, Soybean, Live Cattle) since the 2026-11-10 split of the old six-product
Agriculture book into Agriculture and Softs (Sugar, Cocoa, Coffee, Cotton; softs_dashboard/app.py). Momentum / Carry / Value / Comparison tabs plus a
Portfolio tab, same format as the Metals, Petroleum, NGL and Precious dashboards -- reuses the identical shared engine (common_engine.py,
dashboard_portfolio_tab.py).

Data source: the 2026-11-10 Bloomberg drop, Agri_Softs_Futures_1110.xlsx + Agri_Softs_Calendar_1110.xlsx in the price folder (scripts/new_products_1110.py;
AGRI1110_CONFIG in scripts/rolling_continuous.py). Corn, Wheat and Soybean are identical to the earlier files on every overlapping cell.

Carry tenor pairs (user decision 2026-11-10): F1-F2 short pair for every product, long pair F1-F6 (Corn, Wheat) and F1-F7 (Soybean, Live Cattle), used by the
Portfolio tab (research/configs/agri.py carry_pairs). The Carry tab lets the user pick any (Near, Far) pair for V1, V2 and V3.
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
                                 AGRI1110_CONFIG as AGRI_CONFIG, AGRI1110_FUTURES_FILE as AGRI_FUTURES_FILE,
                                 AGRI1110_CALENDAR_FILE as AGRI_CALENDAR_FILE)
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
    "C": "¢/bu", "W": "¢/bu", "S": "¢/bu", "LC": "¢/lb",
}
PRODUCT_ORDER = ["C", "W", "S", "LC"]

with st.sidebar:
    st.markdown('<p class="main-title">🌾 Agriculture Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Stage 2 — Momentum, Carry, Value, Skewness</p>', unsafe_allow_html=True)
    st.divider()
    return_basis_selector()
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
        index=1, key="agri_roll_method",   # default: Nth trading day of the expiry month (same roll as the research numbers), 2026-10-11
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
register_geo_inputs(f1_df)

curve = load_curve_simple(AGRI_FUTURES_FILE, cfg["price_sheet"])
curve = curve[curve.index.year >= 2006]

st.markdown(f'<p class="main-title">🌾 Agriculture Risk Premia — {cfg["name"]}</p>', unsafe_allow_html=True)
st.caption(f"Data: {f1r.index[0].date()} to {f1r.index[-1].date()}. "
           "PnL on F1_continuous, TC on F1_raw, active-day Sharpe, no look-ahead.")

tab_mom, tab_carry, tab_val, tab_skew, tab_compare, tab_portfolio = st.tabs(
    ["⚡ Momentum", "📐 Carry", "📏 Value", "📉 Skewness", "🔀 Comparison", "🧮 Portfolio"])

key_prefix = f"agri_{product_code}"

with tab_mom:
    mom_positions = render_momentum_tab(f1r, f1c, cfg["name"], unit, key_prefix=key_prefix, phase=phase)

with tab_carry:
    carry_positions = render_carry_tab(curve, f1r, f1c, cfg["name"], unit, key_prefix=key_prefix, phase=phase)

with tab_val:
    contracts = [c for c in curve.columns if c.startswith("F") and c[1:].isdigit() and int(c[1:]) <= 15]
    value_positions = render_value_tab(curve, f1r, f1c, cfg["name"], unit, key_prefix=key_prefix,
                                        contracts=contracts, phase=phase,
                                        default_active_combo=(agri_research_cfg.VALUE_CONTRACT, "5yr", agri_research_cfg.VALUE_THRESHOLD))   # 2026-11-01: F2 for Precious/Agriculture, as the research config

with tab_skew:
    skew_positions = render_skewness_tab(f1r, f1c, cfg["name"], unit, key_prefix=key_prefix, phase=phase,
                                       f2r=f1_df["F2_raw"])

with tab_compare:
    render_comparison_tab(f1r, f1c, cfg["name"], unit, key_prefix=key_prefix, phase=phase,
                           strategy_groups={"Momentum": mom_positions, "Carry": carry_positions,
                                            "Value": value_positions, "Skewness": skew_positions})

with tab_portfolio:
    st.caption("Combines the 4 Agriculture products (Corn, Wheat, Soybean, Live Cattle) "
               "into one asset-class-level portfolio, independent of the sidebar's Product selection above, "
               "which only affects the Momentum/Carry/Value/Skewness/Comparison tabs. Carry and Carry momentum use each product's "
               "F1-F2 pair plus its long pair (F1-F6 Corn and Wheat, F1-F7 Soybean and Live Cattle); change Near/Far in Portfolio Construction below to use another tenor.")
    render_portfolio_tab(agri_research_cfg, key_prefix="agri_portfolio")
