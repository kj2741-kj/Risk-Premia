"""
Risk Premia - Project Hub
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
ghr_wti_inventory_spline.py) and the underlying data/ files, and does not
depend on any other dashboard folder (metals_dashboard/, energy_dashboard/).
"""

import os
import sys

import streamlit as st

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "research"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "research", "configs"))

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


import numpy as np
import pandas as pd
import plotly.graph_objects as go

from common_shared import inject_css, metric_card, section_header, CHART_LAYOUT
from ghr_spline_core import run_spline_analysis, DEFAULT_X_RANGE, DEFAULT_Y_RANGE
import ghr_copper_inventory_spline as ghr_copper
import ghr_wti_inventory_spline as ghr_wti
import cross_asset_engine as cae
import benchmarks

st.set_page_config(
    page_title="Risk Premia - Hub",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()

# Deployment URLs for each asset-class dashboard.
DASHBOARD_LINKS = {
    "Metals":         {"url": "https://risk-premia-metals.streamlit.app/", "ready": True,
                        "desc": "LME Copper and Aluminium. Momentum, Carry, and Value strategies. A fuller "
                                "10-tab research build is also available at metals-risk-premia-kj.streamlit.app."},
    "Energy":         {"url": "https://risk-premia-energykj.streamlit.app/", "ready": True,
                        "desc": "WTI, Brent, RBOB, Heating Oil, Nat Gas, Singapore Gasoil, Fuel Oil. Momentum, Carry, Value."},
    "Precious Metals": {"url": "https://risk-premia-pm.streamlit.app/", "ready": True,
                        "desc": "Gold, Silver, Platinum, Palladium. Momentum, Carry, Value."},
    "NGL / Refined":  {"url": "https://risk-premia-ngl.streamlit.app/", "ready": True,
                        "desc": "Ethane, Propane, Butane, Isobutane, Ethylene, Propylene. Momentum, Carry, Value."},
    "Agriculture":    {"url": "https://risk-premia-agri.streamlit.app/", "ready": True,
                        "desc": "Corn, Wheat, Soybean, Soybean Oil, Coffee, Sugar. Momentum, Carry, Value, Portfolio."},
}

# Cached data loaders for the Fundamental Analysis tab. Cached separately from
# run_spline_analysis (the regression fit itself is cheap) so tweaking the date
# range, trailing-weeks, or bandwidth doesn't re-read the underlying files on
# every widget interaction.

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


# Cross-Asset Portfolio tab (added 2026-08-04, rebuilt as a dynamic Portfolio Construction UI
# 2026-08-04 after feedback that the first static-report version was slow and non-interactive).
# cross_asset_engine.py is a new, isolated engine module -- see its own docstring for why it's
# kept separate from common_engine.py/research/engine.py rather than folded into either.
#
# Caching strategy: only the per-asset-class, per-product signal computation (Excel loading +
# Momentum/Carry/CarryMom/Value math) is genuinely expensive and is cached here, per
# (asset_class, tc_bps) -- the combine step downstream (intersection, the only convention this
# module supports as of 2026-08-04) is cheap. Passed into the engine via per_product_fetcher (a
# dependency-injection seam cross_asset_engine.py exposes specifically so it can stay
# Streamlit-free while still being cacheable at this layer). This is what makes switching
# styles or asset-class selection near-instant after the first load of a given asset class.
@st.cache_data(ttl=3600, show_spinner="Loading curve data and computing signals...")
def _cached_per_product_four_row(asset_class: str, tc_bps: int, carry_spec=None, per_product_pairs: bool = False):
    # carry_spec: a cae.CarrySpec (hashable, so it is part of the cache key). None = the rule default.
    # per_product_pairs: use each product's own tenor pairs (cfg.carry_pairs), see _uses_product_pairs.
    # include_skewness=True (2026-10-12): the result also carries a "Skewness" entry. Every consumer below passes its
    # `styles` explicitly, so the four-style defaults are unchanged unless Skewness is chosen.
    return cae.per_product_four_row(asset_class, tc_bps, carry_spec, per_product_pairs=per_product_pairs,
                                    include_skewness=True)


def _uses_product_pairs(asset_class: str, spec) -> bool:
    """True when the tenor pairs are the untouched rule default for this asset class. Then each product uses its own
    pairs from cfg.carry_pairs(product) (2026-10-12), as in Final_Research_Dashboard.html: Precious and Agriculture add a
    long pair whose far leg differs by product (the other asset classes give the same pairs for every product, so nothing
    changes for them). Any edit to the pairs in the Carry settings panel switches back to one uniform pair list (CUSTOM)."""
    return spec is None or tuple(spec.pairs) == tuple(cae.default_carry_spec(asset_class).pairs)


def _carry_fetcher(specs_key):
    """Per-product fetcher bound to one set of Carry settings. `specs_key` is a tuple of
    (asset_class, CarrySpec) pairs, i.e. hashable, so the cached functions below can take it."""
    specs = dict(specs_key)

    def fetch(asset_class: str, tc_bps: int):
        spec = specs.get(asset_class)
        return _cached_per_product_four_row(asset_class, tc_bps, spec, _uses_product_pairs(asset_class, spec))
    return fetch


@st.cache_data(ttl=3600, show_spinner="Computing Cross-Commodity Portfolio (Momentum/Carry/CarryMom/Value/EW/Risk Parity)...")
def _cached_cross_commodity_portfolio(tc_bps: int, specs_key=()):
    return cae.cross_commodity_portfolio(tc_bps, tuple(cae.ALL_ASSET_CLASSES),
                                          per_product_fetcher=_carry_fetcher(specs_key))


@st.cache_data(ttl=3600, show_spinner="Computing Dynamic Risk Parity Cross-Commodity Portfolio...")
def _cached_cross_commodity_drp(tc_bps: int, specs_key=()):
    # cross_commodity_portfolio() (above) is Dimil's own fixed EW+Risk Parity
    # reference form, kept unmodified as the validated known-good baseline
    # research/_validate_cross_asset_engine.py checks against -- Dynamic Risk
    # Parity is computed separately via the generalized cross_commodity_dynamic()
    # and merged in as an extra row, rather than editing that reference function.
    _, n = cae.cross_commodity_dynamic(tc_bps, tuple(cae.ALL_ASSET_CLASSES), cae.STYLE_NAMES, "dynamic_risk_parity",
                                  per_product_fetcher=_carry_fetcher(specs_key))
    return n["Portfolio"]


@st.cache_data(ttl=3600, show_spinner="Computing Skewness cross-commodity rows...")
def _cached_cross_commodity_skew(tc_bps: int, specs_key=()):
    """Extra correlation rows (2026-10-12): the Skewness style on its own, and the Equal Weight portfolio of all five
    styles (the four validated ones plus Skewness), each equal-weighted across all five asset classes."""
    _, n = cae.cross_commodity_dynamic(tc_bps, tuple(cae.ALL_ASSET_CLASSES), cae.ALL_STYLE_NAMES, "equal_weight",
                                       per_product_fetcher=_carry_fetcher(specs_key))
    return {"Skewness": n["Skewness"], "EW PORT + Skewness": n["Portfolio"]}


@st.cache_data(ttl=3600, show_spinner="Loading traditional-asset benchmark data...")
def _cached_benchmark_returns():
    return benchmarks.load_benchmark_returns()


PALETTE = ["#B87333", "#C9A84C", "#3D8F8A", "#5BAD72", "#B85450",
           "#A07898", "#6A6460", "#9BAAB3", "#7A8E9A", "#C8D0D8"]

ASSET_LABEL_TO_KEY = {v: k for k, v in cae.ASSET_CLASS_LABELS.items()}
STYLE_LABEL_TO_KEY = {"Momentum": "Momentum", "Carry": "Combined Carry",
                       "CarryMom": "Combined CarryMom", "Value": "Value", "Skewness": "Skewness"}


def _ca_fmt(x, fmt_spec: str) -> str:
    return "N/A" if x is None or (isinstance(x, float) and np.isnan(x)) else fmt_spec.format(x)


def _ca_window_metrics(gross: pd.Series, net: pd.Series, yr_start: int, yr_end: int) -> dict:
    """Same shape as dashboard_portfolio_tab.py's _window_metrics() -- Gross/Net Sharpe, Ann
    Return, Ann Vol, Max DD over a year range -- so these metric cards read identically to the
    per-asset-class dashboards' Portfolio tab."""
    def _slice(s):
        return s[(s.index.year >= yr_start) & (s.index.year <= yr_end)].dropna()

    def _true_ann_vol(s):
        """True compounded annual return and true annualized volatility of
        SIMPLE returns, not log-return figures -- see research/
        run_regime_table.py::_metrics for the full derivation of both."""
        if len(s) > 20 and s.std(ddof=1) > 0:
            log_ann = float(s.mean() * 252)
            ann = float((np.exp(log_ann) - 1) * 100)
            vol = float(np.expm1(s).std(ddof=1) * np.sqrt(252) * 100)
            return ann, vol
        return np.nan, np.nan

    def _sharpe(ann_pct, vol_pct):
        """IR from the SAME true-% ann/vol (same units) -- see
        research/run_regime_table.py::_metrics for the full rationale."""
        return float(ann_pct / vol_pct) if pd.notna(vol_pct) and vol_pct > 0 else np.nan

    g, n = _slice(gross), _slice(net)
    gross_ann, gross_vol = _true_ann_vol(g)
    ann, vol = _true_ann_vol(n)
    # True value-based drawdown, not log-space peak-to-trough -- see
    # research/run_regime_table.py::_metrics for the full derivation.
    cum = n.cumsum()
    value = np.exp(cum)
    mdd = float((value / value.cummax() - 1).min() * 100) if len(cum) else np.nan
    return dict(gross=_sharpe(gross_ann, gross_vol), net=_sharpe(ann, vol), ann=ann, vol=vol, mdd=mdd)


def _render_equity_and_metrics(gross_dict: dict, net_dict: dict, key_prefix: str,
                                default_focus: str = "Portfolio") -> None:
    """Metric cards + cumulative equity chart + per-line return/vol/IR table, matching
    dashboard_portfolio_tab.py's own Portfolio tab pattern (year-range slider, strategy picker
    for the metric cards, multiselect for which lines the chart shows)."""
    labels = list(net_dict.keys())
    nonempty = [s for s in net_dict.values() if not s.empty]
    if not nonempty:
        st.warning("No data for this selection.")
        return
    all_index = nonempty[0].index
    for s in nonempty[1:]:
        all_index = all_index.union(s.index)
    min_year, max_year = int(all_index.min().year), int(all_index.max().year)
    # Default to 2011 (REPORT_START), matching every other report in this project -- pre-2011
    # history exists only to warm up long-lookback signals (e.g. Value's 1260-day MA), not to be
    # read as part of the reported track record. Slider still allows going back further.
    default_start = max(min_year, 2011)

    c1, c2 = st.columns([1, 2])
    with c1:
        focus = st.selectbox("Strategy (for metric cards)", labels,
                              index=labels.index(default_focus) if default_focus in labels else 0,
                              key=f"{key_prefix}_focus")
    with c2:
        yr_start, yr_end = st.slider("Year range", min_value=min_year, max_value=max_year,
                                      value=(default_start, max_year), step=1, key=f"{key_prefix}_years")
    shown = st.multiselect("Lines shown on chart", labels, default=labels, key=f"{key_prefix}_shown")

    m = _ca_window_metrics(gross_dict[focus], net_dict[focus], yr_start, yr_end)
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    with mc1:
        metric_card("Gross Sharpe", _ca_fmt(m["gross"], "{:+.2f}"))
    with mc2:
        metric_card("Net Sharpe", _ca_fmt(m["net"], "{:+.2f}"))
    with mc3:
        metric_card("Ann Return (Net)", _ca_fmt(m["ann"], "{:+.2f}"), unit="%")
    with mc4:
        metric_card("Ann Vol", _ca_fmt(m["vol"], "{:.2f}"), unit="%")
    with mc5:
        metric_card("Max DD (Net)", _ca_fmt(m["mdd"], "{:+.2f}"), unit="%")

    section_header("Cumulative equity")
    fig = go.Figure()
    rows = []
    for i, label in enumerate(shown):
        s = net_dict[label]
        window = s[(s.index.year >= yr_start) & (s.index.year <= yr_end)].dropna()
        if window.empty:
            continue
        # True cumulative %, not log-return % -- see research/run_regime_table.py::_metrics for
        # the full derivation. Matches the metric cards above (ann/mdd already true %).
        eq = (np.exp(window.cumsum()) - 1) * 100
        width = 2.6 if label == "Portfolio" else 1.4
        dash = None if label == "Portfolio" else "solid"
        fig.add_trace(go.Scatter(x=eq.index, y=eq.values, name=label, mode="lines",
                                  line=dict(color=PALETTE[i % len(PALETTE)], width=width, dash=dash)))
        if len(window) > 20 and window.std(ddof=1) > 0:
            log_ret = float(window.mean() * 252)
            ret = (np.exp(log_ret) - 1) * 100
            # True annualized volatility of simple returns, not the log-return
            # distribution's spread -- see research/run_regime_table.py::
            # _metrics for the full derivation.
            vol = float(np.expm1(window).std(ddof=1) * np.sqrt(252) * 100)
            # IR from the SAME true-% ret/vol above (same units) -- see
            # research/run_regime_table.py::_metrics for the full rationale.
            ir = ret / vol if vol > 0 else np.nan
        else:
            ret = vol = ir = np.nan
        rows.append({"Strategy": label, "Return (%/yr)": ret, "Vol (%/yr)": vol, "IR": ir})

    layout = dict(CHART_LAYOUT)
    layout["yaxis_title"] = "Cumulative Return (%)"
    fig.update_layout(**layout, title=f"Cumulative Equity, {yr_start} to {yr_end}", height=440)
    st.plotly_chart(fig, use_container_width=True)

    if rows:
        st.dataframe(
            pd.DataFrame(rows).set_index("Strategy").style.format(
                {"Return (%/yr)": "{:+.2f}", "Vol (%/yr)": "{:.2f}", "IR": "{:+.3f}"}),
            use_container_width=True,
        )


tab_overview, tab_fund, tab_crossasset = st.tabs(
    ["🏠 Overview", "📊 Fundamental Analysis", "🌐 Cross-Asset Portfolio"])

# TAB 1: Overview
with tab_overview:
    st.markdown('<p class="main-title">⚙️ Risk Premia</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="main-subtitle">Systematic Momentum, Carry, and Value risk premia across LME metals, '
        'energy, precious metals, and refined products, developed as supervised research with '
        'Prof. Ilia Bouchoev.</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    section_header("WHAT THIS PROJECT IS")
    st.markdown(
        """
This project is a systematic framework that decomposes commodity futures returns into three
economically distinct, near-uncorrelated risk premia: **Momentum** (trend persistence), **Carry**
(curve shape and roll yield), and **Value** (mean-reversion to a long-run anchor), combined into an
equal-weight portfolio. The central result from the metals pilot on Copper and Aluminium is that three
orthogonal sleeves of similar stand-alone Sharpe ratio combine into a portfolio whose risk-adjusted
return materially exceeds any single sleeve, while roughly halving drawdown.

The framework was first validated on LME Copper and Aluminium, then extended, using the same three
strategies in a deliberately simplified form (no CTA-paper trend, no structural anchors, no
walk-forward out-of-sample testing yet), to oil and energy, precious metals, and refined NGL products.
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
        st.caption("Annualised mean and standard deviation of daily returns, scaled by the square root of "
                   "252 and computed over days the strategy actually holds a position, so flat days do not "
                   "dilute the ratio.")
    with c3:
        metric_card("Transaction Costs", "On F1_raw", unit="")
        st.caption("Round-trip cost = |Δposition| × (bps/10000/2) × F1_raw, charged at every position "
                   "change on the real traded price, not the adjusted series.")

    st.caption(
        "Execution timing follows two conventions: **Same-Day**, where position(t) = signal(t−1), and "
        "**Lag-1**, where position(t) = signal(t−2), one additional day of delay with no look-ahead bias "
        "in either case. Which convention performs better is strategy-specific and is re-checked for "
        "every asset class rather than assumed."
    )

    section_header("HEADLINE FINDINGS")
    st.info("Coming soon. Consolidated headline findings across Metals, Energy, Precious Metals, "
            "and NGL will be published here once results from all four asset classes are finalized.")

    section_header("CONCLUSION")
    st.markdown(
        """
The diversification thesis holds on every metal tested to date: combining three economically distinct
premia consistently outperforms any single sleeve on a risk-adjusted basis, with materially lower
drawdown. Optimal parameters are asset-specific rather than a single template; each new product is
assigned its own momentum speed, carry variant, and value anchor, selected from its own data using the
same methodology throughout. The framework has since been extended to genuinely different asset
classes, including energy and refined products, to test whether the same three-premia structure holds
outside metals.
"""
    )

    st.divider()
    section_header("EXPLORE THE DASHBOARDS")
    st.caption("Each asset class below is its own independent dashboard. Open one to explore live "
               "signals, parameter controls, equity curves, rolling Sharpe, and performance metrics.")

    nav_cols = st.columns(5)
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
        "Data sources: LME futures curves (F1-F27), NYMEX, ICE, and COMEX futures curves, and LME Cash "
        "and 3-Month prices. This is a research prototype for academic purposes; all backtests are "
        "in-sample unless otherwise stated, and nothing here constitutes investment advice."
    )

# TAB 2: Fundamental Analysis (GHR inventory-vs-basis cubic spline)
with tab_fund:
    st.markdown('<p class="main-title">📊 Fundamental Analysis: Inventory vs Basis</p>', unsafe_allow_html=True)
    st.caption(
        "A replication of Gorton, Hayashi & Rouwenhorst (2013): the futures basis is fit on normalized "
        "inventory (I/I\\*, trailing 52-week average) using a cubic spline knotted at I/I\\*=1, with "
        "monthly seasonal dummies and Newey-West HAC standard errors, all at weekly frequency."
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

# TAB 3: Cross-Asset Portfolio (Metals + Energy + Precious + NGL + Agriculture combined)
with tab_crossasset:
    st.markdown('<p class="main-title">🌐 Cross-Asset Portfolio</p>', unsafe_allow_html=True)
    st.caption(
        "Combining asset classes into one book (Research_Methodology.docx Section 9). "
        "Calendar alignment is by intersection: a date where any selected asset class isn't "
        "trading is dropped entirely, with a dropped date's move rolled into the next surviving "
        "date so no leg's real return is lost."
    )

    tc_bps = st.slider(
        "TC (bps, round-trip)", min_value=0, max_value=20, value=5, step=1, key="ca_tc_bps",
        help="Applied at every level of this construction (product, asset-class, cross-asset). "
             "Default 5bps matches every other report in this project.",
    )

    # ── Carry settings: default = the 10 Oct rule (V2 only, each asset class's locked tenor pairs).
    # Every portfolio, the correlation section and every combine method below read these settings.
    TENORS = [f"F{i}" for i in range(1, 16)]
    default_specs = {ac: cae.default_carry_spec(ac) for ac in cae.ALL_ASSET_CLASSES}
    with st.expander("Carry settings (default: V2 only, each asset class's locked tenor pairs)"):
        st.caption("Default is the 10 Oct rule: Carry = V2 (Z-score on carry slope) only, the asset class's "
                   "tenor pairs blended at signal level (shift applied once). Change anything below to "
                   "customise; every portfolio and the correlation section on this tab then use it. "
                   "Tenor pairs apply to both Carry and Carry momentum. Momentum and Value are unaffected. "
                   "With the pairs left at their defaults, Precious and Agriculture also blend each product's own long "
                   "pair (Gold F1-F7, Silver F1-F6, Platinum/Palladium F1-F5; Corn/Wheat/Coffee F1-F6, Soybean/Soybean Oil "
                   "F1-F8, Sugar F1-F5) with the F1-F2 shown, exactly as in the Final Research Dashboard. Editing any pair "
                   "below replaces that with one uniform pair list for the asset class.")
        k1, k2, k3 = st.columns([2, 1, 1])
        with k1:
            var_labels = st.multiselect(
                "Carry signals in the composite", list(cae.CARRY_VARIANT_LABELS.values()),
                default=[cae.CARRY_VARIANT_LABELS["V2"]], key="ca_carry_variants",
                help="V2 alone is the rule default. Adding V1 - Carry slope gives the older V1+V2 composite "
                     "(sign of the average, flat when they disagree).")
        with k2:
            z_override = st.number_input("V2 Z-window (days)", min_value=20, max_value=756, value=252, step=1,
                                          key="ca_carry_zwindow")
        with k3:
            h_override = st.number_input("Carry momentum horizon (days)", min_value=1, max_value=252, value=20,
                                          step=1, key="ca_carry_horizon")
        st.markdown("**Tenor pairs by asset class**")
        pair_choice = {}
        for ac in cae.ALL_ASSET_CLASSES:
            dp = list(default_specs[ac].pairs)
            r0, r1, r2, r3, r4, r5 = st.columns([1.2, 1, 1, 1.5, 1, 1])
            with r0:
                st.write(""); st.write(cae.ASSET_CLASS_LABELS[ac])
            with r1:
                n1 = st.selectbox("Near", TENORS, index=TENORS.index(dp[0][0]), key=f"ca_carry_{ac}_n1")
            with r2:
                f1 = st.selectbox("Far", TENORS, index=TENORS.index(dp[0][1]), key=f"ca_carry_{ac}_f1")
            with r3:
                use2 = st.checkbox("Second pair", value=len(dp) >= 2, key=f"ca_carry_{ac}_use2")
            chosen = [(n1, f1)]
            if use2:
                d2 = dp[1] if len(dp) >= 2 else ("F1", "F13")
                with r4:
                    n2 = st.selectbox("Near ", TENORS, index=TENORS.index(d2[0]), key=f"ca_carry_{ac}_n2")
                with r5:
                    f2 = st.selectbox("Far ", TENORS, index=TENORS.index(d2[1]), key=f"ca_carry_{ac}_f2")
                chosen.append((n2, f2))
            pair_choice[ac] = tuple(chosen)

    def _build_specs():
        """Resolve the widget choices into one validated CarrySpec per asset class, and check the chosen
        tenor pairs exist in the curve data. Returns (specs, notes). Raises ValueError with a readable
        message if a choice is invalid."""
        variants_key = tuple(k for k, lab in cae.CARRY_VARIANT_LABELS.items() if lab in var_labels)
        if not variants_key:
            raise ValueError("pick at least one Carry signal (V1 or V2)")
        specs = {ac: cae.resolve_carry_spec(
            ac, cae.CarrySpec(variants_key, int(z_override), int(h_override), pair_choice[ac]))
            for ac in cae.ALL_ASSET_CLASSES}
        notes = []
        for ac in cae.ALL_ASSET_CLASSES:
            pp = _cached_per_product_four_row(ac, tc_bps, specs[ac], _uses_product_pairs(ac, specs[ac]))
            total = len(pp["Momentum"]["names"])
            for style, label in (("Combined Carry", "Carry"), ("Combined CarryMom", "Carry momentum")):
                got = pp[style]["names"]
                thin = [n for n, k in zip(got, pp[style]["n_pairs"]) if k < len(specs[ac].pairs)]
                if thin:
                    notes.append(f"{cae.ASSET_CLASS_LABELS[ac]} {label}: {', '.join(thin)} had data for only some of the "
                                 f"chosen pairs, so they are blended on fewer pairs than the other products.")
                if len(got) < total:
                    missing = [n for n in pp["Momentum"]["names"] if n not in got]
                    notes.append(f"{cae.ASSET_CLASS_LABELS[ac]} {label}: no data for {', '.join(missing)} "
                                 f"on the chosen pair(s), so those products are left out of that sleeve.")
        return specs, notes

    carry_error, carry_notes = None, []
    try:
        carry_specs, carry_notes = _build_specs()
    except ValueError as e:
        carry_error = str(e)
        carry_specs = dict(default_specs)
    if carry_error:
        st.error(f"Carry settings not applied ({carry_error}). Showing the rule defaults until this is fixed.")
    for _n in carry_notes:
        st.warning(_n)
    is_default_carry = all(carry_specs[ac] == default_specs[ac] for ac in cae.ALL_ASSET_CLASSES)
    st.caption("Carry settings: **rule default (V2 only)**." if is_default_carry else
               "Carry settings: **CUSTOM** (differs from the V2-only rule default); numbers below are not "
               "comparable with the rule-default / Dimil figures.")
    carry_specs_key = tuple((ac, carry_specs[ac]) for ac in cae.ALL_ASSET_CLASSES)
    carry_fetcher = _carry_fetcher(carry_specs_key)

    st.divider()

    section_header("Cross-Commodity Portfolio")
    st.caption("Each selected style is first equal-weighted across the selected asset classes into "
               "one cross-commodity series per style, then those style-level series are combined "
               "into one portfolio: a two-stage hierarchical construction (Methodology doc "
               "Section 9), not a single flat optimization over every underlying leg.")

    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        cc_assets_labels = st.multiselect(
            "Asset classes", list(cae.ASSET_CLASS_LABELS.values()),
            default=list(cae.ASSET_CLASS_LABELS.values()), key="cc_assets")
    with cc2:
        cc_styles_labels = st.multiselect(
            "Styles", ["Momentum", "Carry", "CarryMom", "Value", "Skewness"],
            default=["Momentum", "Carry", "CarryMom", "Value"], key="cc_styles",
            help="Skewness (added 2026-10-12) is an optional fifth style, off by default so the headline book is the "
                 "validated four-style one: one +1/-1 per product from minus the 252-day rolling skewness of daily "
                 "log returns (Fernandez-Perez, Fuertes and Miffre 2021, Table 1, time-series form).")
    with cc3:
        cc_combine = st.selectbox(
            "Combine method", ["Equal Weight", "Inverse Vol", "Risk Parity", "Dynamic Risk Parity"], key="cc_combine",
            help="Equal Weight: fixed equal split across the selected styles. Inverse Vol: each style weighted by "
                 "1 / its own trailing 63-day volatility, lagged one day (as in the Final Research Dashboard). Risk Parity: rolling "
                 "Equal Risk Contribution over the full covariance matrix (research/risk_parity.py). "
                 "Dynamic Risk Parity: inverse-EWMA-vol weighting (20-day vol / 60-day covariance "
                 "half-lives, correlations shrunk 50% toward zero), rescaled to match Equal Weight's "
                 "own full-sample volatility (research/drp.py).")

    if len(cc_assets_labels) < 2:
        st.warning("Pick at least 2 asset classes.")
    elif not cc_styles_labels:
        st.warning("Pick at least 1 style.")
    else:
        cc_asset_keys = tuple(ASSET_LABEL_TO_KEY[l] for l in cc_assets_labels)
        cc_style_keys = tuple(STYLE_LABEL_TO_KEY[l] for l in cc_styles_labels)
        cc_combine_key = {"Equal Weight": "equal_weight", "Inverse Vol": "inverse_vol", "Risk Parity": "risk_parity",
                           "Dynamic Risk Parity": "dynamic_risk_parity"}[cc_combine]
        cc_gross, cc_net = cae.cross_commodity_dynamic(
            tc_bps, cc_asset_keys, cc_style_keys, cc_combine_key,
            per_product_fetcher=carry_fetcher)
        _render_equity_and_metrics(cc_gross, cc_net, key_prefix="cc")

    st.divider()

    section_header("Cross-Asset-Class Portfolio")
    st.caption("Combination of 1-5 asset classes' own Equal Weight portfolios (generalizes the "
               "4 fixed Cross-Pairs shown on the static report to any 1-5 you pick). Pick just "
               "one to see that asset class's own EW Portfolio number on its own, matching its "
               "individual dashboard's Portfolio tab.")

    cn1, cn2, cn3 = st.columns([3, 1, 1.4])
    with cn1:
        cn_assets_labels = st.multiselect(
            "Asset classes (choose 1-5)", list(cae.ASSET_CLASS_LABELS.values()),
            default=["Metals", "Energy"], key="cn_assets")
    with cn3:
        st.write("")
        cn_skew = st.checkbox("Add Skewness as a fifth style", value=False, key="cn_skew",
                              help="Off (default): each asset class's own portfolio is the Equal Weight of the four "
                                   "validated styles. On: Skewness is added as a fifth equal-weighted style inside "
                                   "each asset class before the asset classes are combined.")
    with cn2:
        cn_combine = st.selectbox(
            "Combine method", ["Equal Weight", "Dynamic Risk Parity"], key="cn_combine",
            help="Equal Weight: fixed equal split across the selected asset classes' own EW "
                 "portfolios. Dynamic Risk Parity: inverse-EWMA-vol weighting across those same "
                 "asset-class portfolios, rescaled to match Equal Weight's own full-sample "
                 "volatility (research/drp.py). No Risk Parity (ERC) option at this level.")

    if not 1 <= len(cn_assets_labels) <= len(cae.ALL_ASSET_CLASSES):
        st.warning(f"Pick between 1 and {len(cae.ALL_ASSET_CLASSES)} asset classes.")
    else:
        cn_asset_keys = tuple(ASSET_LABEL_TO_KEY[l] for l in cn_assets_labels)
        cn_combine_key = "equal_weight" if cn_combine == "Equal Weight" else "dynamic_risk_parity"
        cn_gross, cn_net = cae.cross_n_portfolio(
            tc_bps, cn_asset_keys, per_product_fetcher=carry_fetcher,
            combine_method=cn_combine_key,
            styles=cae.ALL_STYLE_NAMES if cn_skew else cae.STYLE_NAMES)
        _render_equity_and_metrics(cn_gross, cn_net, key_prefix="cn")

    st.divider()

    section_header("Correlation vs Traditional Assets")
    st.caption(
        "How the Cross-Commodity Portfolio's strategy rows (Momentum/Carry/CarryMom/Value/"
        "EW PORT/Risk Parity/Dynamic Risk Parity) correlate with Equity (S&P 500), Fixed Income "
        "(US Aggregate Bond), a broad passive Commodity Index (DBC), Gold as a distinct "
        "safe-haven, and a traditional 60/40 stock-bond portfolio: the standard \"does this "
        "add value beyond simple beta, and does it diversify a traditional portfolio\" questions "
        "for any systematic commodity strategy. Data: research/benchmarks.py (yfinance daily "
        "prices, cached locally)."
    )

    corr_strategy_net = dict(_cached_cross_commodity_portfolio(tc_bps, carry_specs_key))
    corr_strategy_net["Dynamic Risk Parity"] = _cached_cross_commodity_drp(tc_bps, carry_specs_key)
    corr_default_strats = list(corr_strategy_net.keys())          # the original rows stay the default view
    corr_strategy_net.update(_cached_cross_commodity_skew(tc_bps, carry_specs_key))   # Skewness rows: pick them below
    corr_bench_returns = _cached_benchmark_returns()

    corr_all_years = []
    for _s in list(corr_strategy_net.values()) + list(corr_bench_returns.values()):
        if not _s.empty:
            corr_all_years.append(int(_s.index.min().year))
            corr_all_years.append(int(_s.index.max().year))
    corr_min_year, corr_max_year = min(corr_all_years), max(corr_all_years)
    corr_default_start = max(corr_min_year, 2011)

    corr_c1, corr_c2 = st.columns([2, 1])
    with corr_c1:
        corr_yr_start, corr_yr_end = st.slider(
            "Year range", min_value=corr_min_year, max_value=corr_max_year,
            value=(corr_default_start, corr_max_year), step=1, key="corr_years",
            help="Restricts the correlation calculation to this sub-period: a static "
                 "recomputation over whichever years you pick, not a rolling window. Compare "
                 "different historical regimes (e.g. 2015-2020 vs 2020-2026) to see whether a "
                 "correlation is stable or regime-dependent.",
        )
    with corr_c2:
        corr_strat_labels = st.multiselect(
            "Strategies shown", list(corr_strategy_net.keys()),
            default=corr_default_strats, key="corr_strats_shown",
        )

    if not corr_strat_labels:
        st.warning("Pick at least 1 strategy to show.")
    else:
        corr_bench_labels = list(corr_bench_returns.keys())
        corr_z, corr_text = [], []
        for strat_name in corr_strat_labels:
            s = corr_strategy_net[strat_name]
            s = s[(s.index.year >= corr_yr_start) & (s.index.year <= corr_yr_end)].dropna()
            z_row, text_row = [], []
            for bench_name in corr_bench_labels:
                b = corr_bench_returns[bench_name]
                b = b[(b.index.year >= corr_yr_start) & (b.index.year <= corr_yr_end)]
                idx = s.index.intersection(b.index)
                if len(idx) > 20:
                    c = float(s.loc[idx].corr(b.loc[idx]))
                    z_row.append(c)
                    text_row.append(f"{c:+.2f}")
                else:
                    z_row.append(np.nan)
                    text_row.append("N/A")
            corr_z.append(z_row)
            corr_text.append(text_row)

        # Diverging blue/red pair, neutral gray midpoint (dataviz skill's reference palette) --
        # matches the blue-positive/red-negative convention already used in this project's
        # Research_Dashboard_CombinedCarry.html Correlations tab.
        corr_fig = go.Figure(data=go.Heatmap(
            z=corr_z, x=corr_bench_labels, y=corr_strat_labels,
            colorscale=[[0, "#e34948"], [0.5, "#f0efec"], [1, "#2a78d6"]],
            zmin=-1, zmax=1, zmid=0,
            text=corr_text, texttemplate="%{text}", textfont=dict(size=12, color="#111111"),
            colorbar=dict(title="Correlation"),
            hovertemplate="%{y} vs %{x}: %{z:+.3f}<extra></extra>",
        ))
        corr_layout = dict(CHART_LAYOUT)
        corr_layout.pop("yaxis", None)
        corr_fig.update_layout(**corr_layout,
                                title=f"Correlation Matrix, {corr_yr_start} to {corr_yr_end}",
                                height=380)
        st.plotly_chart(corr_fig, use_container_width=True)

    st.divider()
    st.caption(
        "Engine: research/cross_asset_engine.py (a new, isolated module that does not modify "
        "common_engine.py, research/engine.py, research/risk_parity.py, or any of the 4 live "
        "asset-class dashboards). Signal-level Carry/Carry momentum combination across tenor "
        "pairs (Methodology doc Section 7), not the return-level construction used in an earlier "
        "static HTML report edit; these numbers and those reports are not directly comparable "
        "until the reports are regenerated to match."
    )
