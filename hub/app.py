"""
Metals Risk Premia - Project Hub
==================================
Standalone landing dashboard: project overview, methodology, headline
findings, and conclusion, with buttons linking OUT to each asset-class
dashboard, each of which is its own SEPARATE Streamlit app deployment
(own URL, own compute/memory allocation, own git folder) rather than a
page within this one.

Why separate deployments instead of one multi-page app: each Streamlit
Community Cloud app gets its own container/resource allocation, so
splitting Metals / Energy / Precious Metals / NGL into distinct
deployments means one heavy or crashing dashboard can't starve the
others, and two people can work on two different asset-class folders
independently without touching this hub or each other's deployment.

This file depends on common_shared.py (repo root) plus, for the
Fundamental Analysis tab only, the GHR inventory-spline engine under
scripts/ (ghr_spline_core.py, ghr_copper_inventory_spline.py,
ghr_wti_inventory_spline.py) and the underlying data/ files -- not on
any other dashboard folder (metals_dashboard/, energy_dashboard/).
"""

import os
import sys

import streamlit as st

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))

from common_shared import inject_css, metric_card, section_header
from ghr_spline_core import run_spline_analysis, DEFAULT_X_RANGE, DEFAULT_Y_RANGE
import ghr_copper_inventory_spline as ghr_copper
import ghr_wti_inventory_spline as ghr_wti

st.set_page_config(
    page_title="Metals Risk Premia - Hub",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()

# ═══════════════════════════════════════════════
# Deployment URLs for each asset-class dashboard.
# Fill in as each one is deployed as its own Streamlit Cloud app.
# ═══════════════════════════════════════════════
DASHBOARD_LINKS = {
    "Metals":         {"url": "https://risk-premia-metals.streamlit.app/", "ready": True,
                        "desc": "LME Copper & Aluminium. Momentum, Carry, Value — Stage 2 rebuild. "
                                "(Original 10-tab Stage 1 dashboard: metals-risk-premia-kj.streamlit.app)"},
    "Energy":         {"url": "https://risk-premia-energykj.streamlit.app/", "ready": True,
                        "desc": "WTI, Brent, RBOB, Heating Oil, Nat Gas, Singapore Gasoil, Fuel Oil. Momentum, Carry, Value."},
    "Precious Metals": {"url": None, "ready": False,
                        "desc": "Gold, Silver, Platinum, Palladium, Copper-CME. Stage 2, in progress."},
    "NGL / Refined":  {"url": None, "ready": False,
                        "desc": "Ethane, Propane, Butane, Isobutane, Ethylene, Propylene. Momentum, Carry, Value. Built — awaiting deployment."},
}

# ═══════════════════════════════════════════════
# Cached data loaders for the Fundamental Analysis tab.
# Cached separately from run_spline_analysis (the regression fit itself is
# cheap) so tweaking the date range / trailing-weeks / bandwidth doesn't
# re-read the underlying Excel/CSV files on every widget interaction.
# ═══════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner="Loading Copper F1/F2 basis...")
def _copper_basis_f1f2():
    return ghr_copper.load_daily_basis_f1f2()


@st.cache_data(ttl=3600, show_spinner="Loading Copper cash/3m basis...")
def _copper_basis_cash3m():
    return ghr_copper.load_daily_basis_cash3m()


@st.cache_data(ttl=3600, show_spinner="Loading Copper LME warehouse stocks...")
def _copper_inventory():
    return ghr_copper.load_daily_inventory()


@st.cache_data(ttl=3600, show_spinner="Loading WTI F1/F2 basis...")
def _wti_basis_f1f2():
    return ghr_wti.load_daily_basis_f1f2()


@st.cache_data(ttl=3600, show_spinner="Loading WTI EIA crude stocks...")
def _wti_inventory():
    return ghr_wti.load_weekly_inventory()


tab_overview, tab_fund = st.tabs(["🏠 Overview", "📊 Fundamental Analysis"])

# ═══════════════════════════════════════════════
# TAB 1 — Overview (unchanged content, just moved under a tab)
# ═══════════════════════════════════════════════
with tab_overview:
    st.markdown('<p class="main-title">⚙️ Metals Risk Premia</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="main-subtitle">Systematic Momentum, Carry &amp; Value risk premia across LME metals, '
        'energy, and refined products &mdash; supervised research with Prof. Ilia Bouchoev</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    section_header("WHAT THIS PROJECT IS")
    st.markdown(
        """
A systematic framework that decomposes commodity futures returns into three economically distinct,
near-uncorrelated risk premia — **Momentum** (trend persistence), **Carry** (curve shape / roll yield),
and **Value** (mean-reversion to a long-run anchor) — then combines them into an equal-weight portfolio.
The central result on the metals pilot (Copper, Aluminium): three orthogonal sleeves of similar
stand-alone Sharpe combine into a portfolio whose risk-adjusted return materially exceeds any single
sleeve, while roughly halving drawdown.

Stage 1 (complete) validated the framework on LME Copper and Aluminium. Stage 2 (in progress) extends
the same three strategies — kept deliberately simple for now (no CTA-paper trend, no structural
Anchors, no walk-forward OOS yet) — to Oil & Energy, Precious Metals, and refined NGL products.
"""
    )

    section_header("METHODOLOGY (SAME CONVENTION ACROSS EVERY ASSET CLASS)")
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("PnL Basis", "F1_continuous", unit="")
        st.caption("Ratio back-adjusted continuous front-month series. Signals read raw prices (F1_raw); "
                   "PnL always realises on F1_continuous.")
    with c2:
        metric_card("Sharpe Convention", "Active-Day", unit="")
        st.caption("Annualised mean/std of daily returns × √252, computed over days the strategy actually "
                   "holds a position — flat days don't dilute the ratio.")
    with c3:
        metric_card("Transaction Costs", "On F1_raw", unit="")
        st.caption("Round-trip cost = |Δposition| × (bps/10000/2) × F1_raw, charged at every position "
                   "change on the real traded price, not the adjusted series.")

    st.caption(
        "Execution timing: **Same-Day** = position(t) = signal(t−1) (shift-1). **Lag-1** = position(t) = "
        "signal(t−2) (shift-2, one extra day, no look-ahead either way). Which convention wins is "
        "strategy-specific and re-checked per asset class, not assumed."
    )

    section_header("HEADLINE FINDINGS (STAGE 1 — METALS)")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        metric_card("Copper EW Portfolio", "+0.73", unit=" Sharpe")
        st.caption("Net of 5bps, full sample 2006-2025. Best single sleeve (Momentum): +0.62.")
    with f2:
        metric_card("Aluminium EW Portfolio", "+0.85", unit=" Sharpe")
        st.caption("Net of 5bps, full sample 2006-2026. Best single sleeve (Carry): +0.64.")
    with f3:
        metric_card("Optimal Config", "Metal-Specific", unit="")
        st.caption("Copper wants a faster trend + curve-momentum carry; Aluminium wants a slower trend + "
                   "mean-reverting z-score carry. No one-size template.")
    with f4:
        metric_card("Diversification", "Corr < 0.25", unit="")
        st.caption("Momentum-Carry-Value position correlations mostly modest to negative — the combination, "
                   "not any one sleeve, is the product.")

    section_header("CONCLUSION")
    st.markdown(
        """
The diversification thesis holds on every metal tested so far: combining three economically distinct
premia consistently beats any single sleeve on a risk-adjusted basis, with materially lower drawdown.
Optimal parameters are asset-specific, not a one-size template — each new product gets its own
momentum speed, carry variant, and value anchor selected on its own data, same methodology throughout.
Stage 2 extends this test to a genuinely different asset class (energy, refined products) to see
whether the same three-premia structure holds outside metals.
"""
    )

    st.divider()
    section_header("EXPLORE THE DASHBOARDS")
    st.caption("Each asset class below is its own independent dashboard — click through for live signals, "
               "parameter controls, equity curves, rolling Sharpe, and performance metrics.")

    nav_cols = st.columns(4)
    for col, (name, info) in zip(nav_cols, DASHBOARD_LINKS.items()):
        with col:
            st.markdown(f"**{name}**")
            if info["ready"]:
                st.link_button(f"Open {name} →", info["url"], use_container_width=True)
            else:
                st.button("Coming Soon", disabled=True, use_container_width=True, key=f"soon_{name}")
            st.caption(info["desc"])

    st.divider()
    st.caption(
        "Data: LME futures curves (F1–F27), NYMEX/ICE/COMEX futures curves, LME Cash & 3M prices. "
        "Research prototype for academic purposes — in-sample backtests unless stated otherwise. Not "
        "investment advice."
    )

# ═══════════════════════════════════════════════
# TAB 2 — Fundamental Analysis (GHR inventory-vs-basis cubic spline)
# ═══════════════════════════════════════════════
with tab_fund:
    st.markdown('<p class="main-title">📊 Fundamental Analysis — Inventory vs Basis</p>', unsafe_allow_html=True)
    st.caption(
        "Gorton, Hayashi & Rouwenhorst (2013) replication: fits the futures basis on normalized inventory "
        "(I/I\\*, trailing 52-week average) via a cubic spline knotted at I/I\\*=1, plus monthly seasonal "
        "dummies, with Newey-West HAC standard errors. Weekly frequency throughout."
    )

    COMMODITY_OPTIONS = {"Copper (LME)": "copper", "WTI Crude (NYMEX)": "wti"}

    ctrl1, ctrl2, ctrl3 = st.columns([1.2, 1.2, 1.6])
    with ctrl1:
        commodity_choice = st.selectbox("Commodity", list(COMMODITY_OPTIONS.keys()), key="fund_commodity")
    commodity_key = COMMODITY_OPTIONS[commodity_choice]

    if commodity_key == "copper":
        with ctrl2:
            basis_source = st.selectbox(
                "Basis definition",
                ["f1f2", "cash3m"],
                format_func=lambda s: "F1/F2 futures (Eq. 15)" if s == "f1f2" else "Cash vs 3-month forward",
                key="fund_copper_basis_source",
            )
        daily_basis = _copper_basis_f1f2() if basis_source == "f1f2" else _copper_basis_cash3m()
        daily_stock = _copper_inventory()
        commodity_label = "Copper"
    else:
        basis_source = "f1f2"
        with ctrl2:
            st.selectbox("Basis definition", ["F1/F2 futures (Eq. 15)"], disabled=True, key="fund_wti_basis_source")
        daily_basis = _wti_basis_f1f2()
        daily_stock = _wti_inventory()
        commodity_label = "WTI Crude"

    data_min = max(daily_basis.index.min(), daily_stock.index.min()).date()
    data_max = min(daily_basis.index.max(), daily_stock.index.max()).date()

    with ctrl3:
        date_range = st.date_input(
            "Regression period",
            value=(data_min, data_max),
            min_value=data_min, max_value=data_max,
            key=f"fund_daterange_{commodity_key}",
        )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = data_min, data_max

    with st.expander("Advanced settings"):
        a1, a2, a3 = st.columns(3)
        with a1:
            trailing_weeks = st.number_input(
                "I* trailing weeks", min_value=4, max_value=156, value=52, step=1, key="fund_trailing_weeks")
        with a2:
            nw_bandwidth = st.number_input(
                "Newey-West bandwidth (weeks)", min_value=4, max_value=156, value=52, step=1, key="fund_nw_bandwidth")
        with a3:
            fixed_scale = st.checkbox(
                "Fixed axis scale (comparable across commodities)", value=True, key="fund_fixed_scale")
            st.caption(f"x: {DEFAULT_X_RANGE}, y: {DEFAULT_Y_RANGE}% p.a. when checked; autorange otherwise.")

    x_range = DEFAULT_X_RANGE if fixed_scale else None
    y_range = DEFAULT_Y_RANGE if fixed_scale else None

    try:
        result = run_spline_analysis(
            daily_basis=daily_basis,
            daily_stock=daily_stock,
            commodity_label=commodity_label,
            basis_source=basis_source,
            start=str(start_date), end=str(end_date),
            trailing_weeks=int(trailing_weeks), nw_bandwidth=int(nw_bandwidth),
            save_outputs=False,
            x_range=x_range, y_range=y_range,
        )
    except ValueError as e:
        st.error(str(e))
        st.stop()

    st.plotly_chart(result["fig"], use_container_width=True)

    s = result["slopes"]
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_card("Slope at I/I*=1", f"{s['slope_at_1']:.2f}", unit="")
        st.caption(f"t = {s['t_at_1']:.2f}")
    with m2:
        metric_card("Slope at I/I*=0.75", f"{s['slope_at_0.75']:.2f}", unit="")
        st.caption(f"t = {s['t_at_0.75']:.2f}")
    with m3:
        metric_card("Convexity (diff)", f"{s['diff']:.2f}", unit="")
        st.caption(f"t = {s['t_diff']:.2f}")
    with m4:
        metric_card("R²", f"{result['r2']:.3f}", unit="")
        st.caption(f"{len(result['merged'])} weekly obs, "
                   f"{result['period_start'].date()} to {result['period_end'].date()}")

    with st.expander("Merged weekly data"):
        st.dataframe(result["merged"], use_container_width=True)
        st.download_button(
            "Download CSV",
            result["merged"].to_csv().encode("utf-8"),
            file_name=f"{commodity_label.lower().replace(' ', '_')}_basis_inventory_weekly_{basis_source}.csv",
            mime="text/csv",
        )
