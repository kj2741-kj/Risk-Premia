"""
US Power Dashboard
==================
Standalone Streamlit app, its own separate deployment (main file: power_dashboard/app.py). The standalone Power tab of the research dashboard: ICE monthly real-time power futures (USD/MWh),
peak and off-peak, on the PJM Western Hub, ERCOT North 345KV and MISO Indiana Hub; the five series whose Calendar-2025 time to trade 1 sigma risk is under 5 days (MISO OffPeak, 9.9 days, is
excluded). Momentum / Carry / Value / Skewness / Comparison / Portfolio, same format as the other dashboards, same shared engine (common_engine.py). Power is not part of the cross-asset book.

Data: data/Emissions_1029 (PJM_Power_Futures.xlsx, US_Power_Futures.xlsx, Power_Expiry_Calendars.xlsx), from 2015-01-02. Every delivery month is listed and the last trade date falls in the
delivery month, so the generic F1 is the contract delivering now; the roll (5th trading day of the expiry month) moves into the next month on the 5th trading day of the delivery month.
Carry and Carry momentum: F1-F2 + F1-F13 (research/configs/power.py).
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
# The Power files run to 2026-11-02; every other app ends on 2026-10-29 (data/Prices_1029_merged), and the 1029 research dashboard cuts Power there as well. One shared end date keeps the apps, the hub and the dashboard comparable.
os.environ.setdefault("RP_POWER_CUTOFF", "2026-10-29")

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
from rolling_continuous import get_metal_rolling_f1, reanchor_f1_continuous
from rolling_continuous_5td import get_rolling_f1 as get_rolling_f1_5td
from dashboard_portfolio_tab import render_portfolio_tab
import power as power_research_cfg              # research/configs/power.py

st.set_page_config(
    page_title="US Power Risk Premia",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# Per-product source: price workbook, calendar file, config registry (keyed by the Bloomberg family code), first date used, and the TC-per-flip unit label (display only).
_P = power_research_cfg
PRODUCT_ORDER = [_P.METAL_CODES[p] for p in ("PJM_Peak", "PJM_OffPeak", "ERCOT_Peak", "ERCOT_OffPeak", "MISO_Peak")]
PRODUCT_SOURCE = {_P.METAL_CODES[p]: dict(config=_P.POWER_CONFIG, futures=_P.SHEETS[p][0], calendar=_P.CALENDAR_FILE, start=_P.ANALYSIS_START, unit="/MWh") for p in _P.PRODUCTS}
PRODUCT_NAME = {_P.METAL_CODES[p]: _P.LABELS[p] for p in _P.PRODUCTS}
POWER_PORTFOLIO_EXCLUDED = ("MISO_OffPeak",)    # time to trade 1 sigma risk 9.9 days (Calendar 2025), above the 5-day line

with st.sidebar:
    st.markdown('<p class="main-title">⚡ US Power Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Stage 2: Momentum, Carry, Value, Skewness</p>', unsafe_allow_html=True)
    st.divider()
    return_basis_selector()
    st.divider()
    product_code = st.radio(
        "Product", PRODUCT_ORDER, key="power_product_choice",
        format_func=lambda c: PRODUCT_NAME[c],
    )
    st.divider()
    st.markdown("**Rolling Configuration**")
    roll_method = st.selectbox(
        "Rolling Logic",
        ["N days before last trading day", "Nth trading day of the expiry month"],
        index=1, key="power_roll_method",   # default: Nth trading day of the expiry month (same roll as the research numbers), 2026-10-11
    )
    roll_n = st.number_input("N", min_value=1, max_value=10, value=5, step=1, key="power_roll_n")
    st.caption("US power: PJM Western Hub, ERCOT North and MISO Indiana Hub real-time monthly futures (ICE), peak and off-peak. The generic F1 is the contract delivering in the current "
               "month; the default roll (5th trading day of the expiry month) moves into the next month on the 5th trading day of the delivery month. Same Momentum/Carry/Value/Skewness format as the other dashboards.")

src = PRODUCT_SOURCE[product_code]
cfg = src["config"][product_code]
unit = src["unit"]

if roll_method == "N days before last trading day":
    f1_df = get_metal_rolling_f1(product_code, futures_file=src["futures"],
                                  calendar_file=src["calendar"], verbose=False,
                                  config=src["config"], roll_day=roll_n)
else:
    f1_df = get_rolling_f1_5td(product_code, futures_file=src["futures"],
                                calendar_file=src["calendar"], verbose=False,
                                config=src["config"], roll_day=roll_n)
if f1_df.empty:
    st.error(f"Could not build F1_continuous for {cfg['name']}.")
    st.stop()
f1_df = reanchor_f1_continuous(f1_df[(f1_df.index >= src["start"]) & (f1_df.index <= os.environ["RP_POWER_CUTOFF"])])
f1r, f1c = f1_df["F1_raw"], f1_df["F1_continuous"]
phase = f1_df["Phase"]
register_geo_inputs(f1_df)

curve = load_curve_simple(src["futures"], cfg["price_sheet"])
curve = curve[(curve.index >= src["start"]) & (curve.index <= os.environ["RP_POWER_CUTOFF"])]

st.markdown(f'<p class="main-title">⚡ US Power Risk Premia: {cfg["name"]}</p>', unsafe_allow_html=True)
st.caption(f"Data: {f1r.index[0].date()} to {f1r.index[-1].date()}. "
           "PnL on F1_continuous, TC on F1_raw, active-day Sharpe, no look-ahead.")

tab_mom, tab_carry, tab_val, tab_skew, tab_compare, tab_portfolio = st.tabs(
    ["⚡ Momentum", "📐 Carry", "📏 Value", "📉 Skewness", "🔀 Comparison", "🧮 Portfolio"])

key_prefix = f"power_{product_code}"

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
    st.caption("Combines the 5 series (PJM Peak and OffPeak, ERCOT Peak and OffPeak, MISO Peak) into one portfolio, independent of the sidebar's Product selection above, "
               "which only affects the Momentum/Carry/Value/Skewness/Comparison tabs. The common data window starts on 2015-01-02. Carry and Carry momentum: F1-F2 + F1-F13.")
    render_portfolio_tab(power_research_cfg, key_prefix="power_portfolio",
                          excluded_products=POWER_PORTFOLIO_EXCLUDED)
