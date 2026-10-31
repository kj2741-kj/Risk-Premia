"""
Power, Emissions and Nat Gas Dashboard - Stage 2   (new 2026-10-31)
============================
Standalone Streamlit app, its own separate deployment (main file: pen_dashboard/app.py). The PEN bucket of the research dashboard: Henry Hub natural gas (NYMEX), TTF natural gas
(ICE Endex, European) and EUA carbon allowances (ICE Endex). The other power products are not in yet. Momentum / Carry / Value / Skewness / Comparison / Portfolio, same format as the
Petroleum, Metals, Precious Metals, NGL and Agriculture dashboards -- reuses the identical shared engine (common_engine.py).

Each product keeps its own data file, roll calendar and start date:
  * Henry Hub (NG):  Energy_Futures_Updated.xlsx + expiry_calendars_20260701.xlsx, from 2006.
  * TTF (TZT):       Emissions_Futures_Updated.xlsx + Emissions_Expiry_Calendars.xlsx (Bloomberg expiry history), from 2006. Monthly contracts, last trade two business days
                     before the delivery month.
  * EUA (MO):        same files, from 2008-04-01 (the first EU ETS Phase II day; the earlier generic series is Phase I contracts at 0.01-0.07 EUR). Quarterly contracts.
The Portfolio tab and the cross-asset hub use Carry F1-F3 for TTF and EUA and F1-F3 + F1-F13 for Henry Hub (research/configs/pen.py).
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
                                 ENERGY_CONFIG, ENERGY_FUTURES_FILE, ENERGY_CALENDAR_FILE,
                                 EMISSIONS_CONFIG, EMISSIONS_FUTURES_FILE, EMISSIONS_CALENDAR_FILE)
from rolling_continuous_5td import get_rolling_f1 as get_rolling_f1_5td
from dashboard_portfolio_tab import render_portfolio_tab
import pen as pen_research_cfg                  # Henry Hub + TTF + EUA, dispatching to configs/energy.py and configs/emissions.py
import emissions as emissions_research_cfg

st.set_page_config(
    page_title="Power, Emissions & Nat Gas Risk Premia - Stage 2",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# Per-product source: price file, calendar file, config registry, first date used, and the TC-per-flip unit label (display only, no effect on Sharpe/PnL).
PRODUCT_ORDER = ["NG", "TZT", "MO"]
PRODUCT_SOURCE = {
    "NG":  dict(config=ENERGY_CONFIG,    futures=ENERGY_FUTURES_FILE,    calendar=ENERGY_CALENDAR_FILE,    start="2006-01-01", unit="/MMBtu"),
    "TZT": dict(config=EMISSIONS_CONFIG, futures=EMISSIONS_FUTURES_FILE, calendar=EMISSIONS_CALENDAR_FILE,
                start=emissions_research_cfg.ANALYSIS_STARTS["TTF"], unit="/MWh"),
    "MO":  dict(config=EMISSIONS_CONFIG, futures=EMISSIONS_FUTURES_FILE, calendar=EMISSIONS_CALENDAR_FILE,
                start=emissions_research_cfg.ANALYSIS_STARTS["EUA"], unit="/t"),
}
PRODUCT_NAME = {"NG": "Nat Gas Henry Hub (NYMEX)", "TZT": "TTF Natural Gas (ICE Endex)", "MO": "EUA Carbon (ICE Endex)"}
PEN_PORTFOLIO_EXCLUDED = ()

with st.sidebar:
    st.markdown('<p class="main-title">⚡ Power, Emissions &amp; Nat Gas Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Stage 2: Momentum, Carry, Value, Skewness</p>', unsafe_allow_html=True)
    st.divider()
    return_basis_selector()
    st.divider()
    product_code = st.radio(
        "Product", PRODUCT_ORDER, key="pen_product_choice",
        format_func=lambda c: PRODUCT_NAME[c],
    )
    st.divider()
    st.markdown("**Rolling Configuration**")
    roll_method = st.selectbox(
        "Rolling Logic",
        ["N days before last trading day", "Nth trading day of the expiry month"],
        index=1, key="pen_roll_method",   # default: Nth trading day of the expiry month (same roll as the research numbers), 2026-10-11
    )
    roll_n = st.number_input("N", min_value=1, max_value=10, value=5, step=1, key="pen_roll_n")
    st.caption("Power, Emissions and Nat Gas bucket: Henry Hub (US natural gas), TTF (European natural gas) and EUA carbon allowances. TTF and EUA come from the "
               "Bloomberg pull of 29-Oct with their own expiry calendars; EUA starts on 2008-04-01 (first Phase II day). EUA data quality is still under review. "
               "Same Momentum/Carry/Value/Skewness format as the other dashboards.")

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
f1_df = reanchor_f1_continuous(f1_df[f1_df.index >= src["start"]])
f1r, f1c = f1_df["F1_raw"], f1_df["F1_continuous"]
phase = f1_df["Phase"]
register_geo_inputs(f1_df)

curve = load_curve_simple(src["futures"], cfg["price_sheet"])
curve = curve[curve.index >= src["start"]]

st.markdown(f'<p class="main-title">⚡ Power, Emissions &amp; Nat Gas Risk Premia: {cfg["name"]}</p>', unsafe_allow_html=True)
st.caption(f"Data: {f1r.index[0].date()} to {f1r.index[-1].date()}. "
           "PnL on F1_continuous, TC on F1_raw, active-day Sharpe, no look-ahead.")

tab_mom, tab_carry, tab_val, tab_skew, tab_compare, tab_portfolio = st.tabs(
    ["⚡ Momentum", "📐 Carry", "📏 Value", "📉 Skewness", "🔀 Comparison", "🧮 Portfolio"])

key_prefix = f"pen_{product_code}"

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
    st.caption("Combines the 3 products (Henry Hub, TTF, EUA) into one bucket-level portfolio, independent of the sidebar's Product selection above, "
               "which only affects the Momentum/Carry/Value/Skewness/Comparison tabs. The common data window starts with the latest product start "
               "(EUA, 2008-04-01). Carry and Carry momentum: Henry Hub F1-F3 + F1-F13, TTF and EUA F1-F3 only.")
    render_portfolio_tab(pen_research_cfg, key_prefix="pen_portfolio",
                          excluded_products=PEN_PORTFOLIO_EXCLUDED)
