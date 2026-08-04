"""
research/cross_asset_engine.py
================================
Cross-asset (Metals + Energy + Precious + NGL) portfolio construction, per
Dimil Patel's methodology (Research_Methodology.docx Section 9, and
Analysis/Research_Dashboard_CombinedCarry.html): a hierarchical Cross-
Commodity Portfolio (style-level aggregation first, then Equal Weight /
Risk Parity) and Cross-Pair Portfolios (50/50 blends of two asset classes'
own Equal Weight portfolios).

DELIBERATELY a separate, isolated module -- does not modify common_engine.py,
research/engine.py, research/risk_parity.py, dashboard_portfolio_tab.py, or
any of the 4 live asset-class dashboards. Reuses combine_returns(),
combine_positions(), exec_shift(), log_return_daily(), and
rolling_erc_combine() from the existing two engines via import; does not
duplicate their logic. This mirrors why research/engine.py itself exists as
a separate copy from common_engine.py -- new, less-tested methodology stays
isolated from what four live dashboards and the offline research pipeline
currently depend on, until it's been reviewed and a decision is made about
whether/how to fold it back in.

Two calendar-alignment conventions, both real, both first-class (neither
silently preferred) pending a decision on which becomes the reported
default -- see the 2026-08-04 diagnostic (research/_calendar_diagnostic.py):
strict intersection loses 4.35% of the union's days across the 4 asset
classes, concentrated in Metals/Precious/NGL (Energy is never the missing
one -- it has the fullest calendar of the four).

- "intersection" (Mark Bogorad, "Risk Premia in Diversified Energy
  Portfolios", Dec 2025, Section 4 Data, p.12: "we eliminate dates on which
  CME and ICE calendars do not overlap, retaining only trading days when all
  contracts in the universe are simultaneously open... Any omitted ICE
  return on these isolated dates is naturally incorporated into the next
  available trading day's price"). Every asset class must have a genuine
  return for a date to count -- but critically, per that last sentence, a
  dropped date must NOT silently delete another member's real return on
  that date. Implemented (see _combine_intersection, fixed 2026-08-04 after
  a real bug was found via a worked example) by converting each series to a
  cumulative level, restricting to the intersected dates, and diffing
  ACROSS those surviving dates -- not by summing already-computed daily
  returns and dropping mismatched ones, which silently discarded real P&L
  for whichever member DIDN'T have the gap. Worth knowing: this project's
  own combine_returns() docstring documents that an EARLIER version of that
  function used union+zero-fill and was deliberately moved away from it
  after it measurably changed Energy's reference-strategy numbers -- Dimil's
  zero-fill convention (below) reintroduces that same choice at the
  cross-asset level, not necessarily wrong, but not new territory for this
  project either.
- "zero_fill" (Dimil Patel, commit 80d5f43 "Fix Energy's internal NYMEX/ICE
  calendar mismatch", Methodology doc Section 8-9): union of dates; a non-
  trading asset class gets an explicit 0.0 return that day at its normal
  fixed weight, rather than being dropped. Note this is NOT calendar-neutral
  for the Risk Parity leg specifically: a real return paired against an
  injected zero on the same date is a real data point fed into the rolling
  covariance estimate, which can bias correlation toward zero on exactly the
  days it's least informative to do so. This flows through deliberately
  (not specially handled) -- comparing how much it actually moves the ERC
  weights in practice is part of the point of keeping both methods.

Signal-level Carry / Carry-Momentum construction (Methodology doc Section 7,
"the equal-weighting across tenors is applied to the raw signal, and the
execution shift is applied once to the combined result -- not separately per
tenor before combining"): verified BYTE-FOR-BYTE against Dimil's real pushed
Metals numbers in research/_validate_signal_combine.py and
research/_validate_signal_combine2.py (5 of 6 rows exact match; Risk Parity
has a small, already-documented, pre-existing path-dependent drift between
this project's live-dashboard and offline-script ERC code paths, unrelated
to this module). This is NOT the same as the return-level "Combined Carry"
construction built into the Analysis/*.html reports earlier the same night
(2026-08-04) -- those average two tenor pairs' already-shifted, already-PnL'd
return series, which is mathematically different and does not reproduce
Dimil's numbers. dashboard_portfolio_tab.py's Combined Carry logic was
corrected to signal-level in this same session; the static HTML reports were
NOT (out of scope for tonight, per explicit instruction not to touch
reports).
"""
from __future__ import annotations

import importlib
import sys
import os

import numpy as np
import pandas as pd

_RESEARCH_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIGS_DIR = os.path.join(_RESEARCH_DIR, "configs")
for _p in (_RESEARCH_DIR, _CONFIGS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engine import (raw_signal_carry_v1, raw_signal_carry_v2, raw_signal_carrymom,
                     combine_positions, combine_returns, exec_shift, log_return_daily,
                     momentum_composite_position, value_v1_position)
from risk_parity import rolling_erc_combine
from run_regime_table import _metrics
from regimes import REGIMES, REPORT_START

ASSET_CLASSES = ["metals", "energy", "precious", "ngl"]
ASSET_CLASS_LABELS = {"metals": "Metals", "energy": "Energy", "precious": "Precious", "ngl": "NGL"}
# Dashboard-visible product lists (CLAUDE.md's documented exclusion: research configs' PRODUCTS
# is NOT what the live dashboard, or Dimil's cross-asset numbers, are built on -- Energy excludes
# Singapore Gasoil + Fuel Oil, NGL excludes Ethylene + Propylene; Metals/Precious unfiltered).
# Confirmed empirically: cfg.PRODUCTS (7-product) Energy Momentum full-sample IR=0.586 vs this
# filtered (5-product) basis IR=0.430, and Dimil's real pushed number is IR=0.436 -- close to the
# filtered basis, nowhere near the unfiltered one. Using cfg.PRODUCTS here would silently pull in
# Singapore Gasoil/Fuel Oil and Ethylene/Propylene, which the cross-asset methodology (following
# Dimil's own convention) should not.
DASHBOARD_PRODUCTS = {
    "energy": ["WTI", "Brent", "RBOB", "HeatingOil", "NatGas"],
    "ngl": ["Ethane", "Propane", "Butane", "Isobutane"],
}
# Metals-Precious and Energy-NGL deliberately excluded (Dimil's dashboard note: the two most
# correlated pairs, weakest diversification candidates).
CROSS_PAIRS = [("metals", "energy"), ("metals", "ngl"), ("precious", "energy"), ("precious", "ngl")]
CROSS_PAIR_LABELS = {
    ("metals", "energy"): "Metals-Energy", ("metals", "ngl"): "Metals-NGL",
    ("precious", "energy"): "Precious-Energy", ("precious", "ngl"): "Precious-NGL",
}
TC_BPS = 5

_CFG_CACHE: dict[str, object] = {}


def _get_cfg(asset_class: str):
    if asset_class not in _CFG_CACHE:
        _CFG_CACHE[asset_class] = importlib.import_module(asset_class)
    return _CFG_CACHE[asset_class]


def _carry_composite_raw(curve: pd.DataFrame, near: str, far: str, window: int) -> pd.Series:
    """V1+V2 composite raw (pre-shift) signal for ONE Carry tenor pair --
    same formula as engine.py's carry_v1v2_composite_position, one step
    earlier (no shift), so it can be combined further with another tenor
    pair's composite before a single shift is applied."""
    v1 = raw_signal_carry_v1(curve, near, far)
    v2 = raw_signal_carry_v2(curve, near, far, window=window)
    return combine_positions([v1, v2], "equal_weight")


def per_product_four_row(asset_class: str, tc_bps: int = TC_BPS) -> dict[str, dict[str, list[pd.Series]]]:
    """Momentum / Combined Carry / Combined CarryMom / Value gross AND net
    daily log-return series PER PRODUCT (not yet combined across products)
    for one asset class, on the dashboard-filtered product universe.
    Returns {style: {"gross": [...], "net": [...]}}. Signal-level Carry/
    CarryMom combination across tenor pairs when the asset class has >=2
    (verified against Dimil's real Metals numbers); a single tenor pair
    (Precious Metals) just flows through combine_positions with one leg, a
    no-op sign(), identical to using it directly.

    Deliberately does NOT take a calendar_method argument -- this is the
    expensive step (Excel curve loading + signal computation across every
    product), and it does not depend on how those products get combined
    afterward. Callers combine this function's output via combine_cross_
    asset(..., calendar_method) themselves (see asset_class_four_row below).
    Splitting it out this way lets a caller cache this function's result
    once per (asset_class, tc_bps) and reuse it across BOTH calendar
    methods, instead of redoing the expensive part on every method switch."""
    cfg = _get_cfg(asset_class)
    tenor_pairs = cfg.CARRY_TENOR_PAIRS
    products = DASHBOARD_PRODUCTS.get(asset_class, cfg.PRODUCTS)
    out = {style: {"gross": [], "net": []} for style in ("Momentum", "Combined Carry", "Combined CarryMom", "Value")}

    for p in products:
        curve = cfg.load_curve(p)
        raw = cfg.load_f1_series_logret(p)
        log_price, phase, f1r = raw["log_price"], raw["Phase"], raw["F1_raw"]

        mom_pos = momentum_composite_position(f1r, cfg.MOMENTUM_PAIRS, shift_n=cfg.MOMENTUM_SHIFT_N)
        g, n = log_return_daily(mom_pos, log_price, tc_bps, phase)
        if not n.empty:
            out["Momentum"]["gross"].append(g)
            out["Momentum"]["net"].append(n)

        carry_raws = [_carry_composite_raw(curve, near, far, cfg.CARRY_ZSCORE_WINDOW)
                      for near, far in tenor_pairs]
        carry_raws = [r for r in carry_raws if not r.empty]
        if carry_raws:
            combo = carry_raws[0] if len(carry_raws) == 1 else combine_positions(carry_raws, "equal_weight")
            pos = exec_shift(combo, cfg.CARRY_SHIFT_N).fillna(0)
            g, n = log_return_daily(pos, log_price, tc_bps, phase)
            if not n.empty:
                out["Combined Carry"]["gross"].append(g)
                out["Combined Carry"]["net"].append(n)

        cm_raws = [raw_signal_carrymom(curve, near, far, cfg.CARRY_MOMENTUM_HORIZON)
                   for near, far in tenor_pairs]
        cm_raws = [r for r in cm_raws if not r.empty]
        if cm_raws:
            combo = cm_raws[0] if len(cm_raws) == 1 else combine_positions(cm_raws, "equal_weight")
            pos = exec_shift(combo, cfg.CARRY_MOMENTUM_SHIFT_N).fillna(0)
            g, n = log_return_daily(pos, log_price, tc_bps, phase)
            if not n.empty:
                out["Combined CarryMom"]["gross"].append(g)
                out["Combined CarryMom"]["net"].append(n)

        val_pos = value_v1_position(curve, cfg.VALUE_CONTRACT, cfg.VALUE_LOOKBACK_DAYS,
                                     cfg.VALUE_THRESHOLD, shift_n=cfg.VALUE_SHIFT_N)
        g, n = log_return_daily(val_pos, log_price, tc_bps, phase)
        if not n.empty:
            out["Value"]["gross"].append(g)
            out["Value"]["net"].append(n)

    return out


def asset_class_four_row(asset_class: str, calendar_method: str = "intersection",
                          tc_bps: int = TC_BPS, styles: tuple[str, ...] | None = None,
                          per_product_fetcher=per_product_four_row
                          ) -> tuple[dict[str, pd.Series], dict[str, pd.Series]]:
    """Momentum / Combined Carry / Combined CarryMom / Value gross AND net
    daily log-return series for one asset class, combined across its
    products. Returns (gross_dict, net_dict). `calendar_method` governs
    that product-level combination (e.g. Energy's WTI/RBOB/HeatingOil/
    NatGas on NYMEX vs Brent on ICE) -- the same choice, applied one level
    down, as the cross-asset-level combination elsewhere in this module.
    Verified this matters in practice, not just in principle: without
    applying it here too, Energy's own numbers (the only asset class with a
    real internal exchange split) sit ~0.01 IR off Dimil's real pushed
    Cross-Commodity/Cross-Pair numbers even after everything else matches;
    with zero_fill applied consistently at both levels, the gap closes.

    `styles`, if given, restricts to a subset of the 4 (e.g. for a live UI
    toggle) -- default is all 4.

    `per_product_fetcher` defaults to the plain, uncached per_product_four_
    row() (this module deliberately stays Streamlit-free, so it can't cache
    directly itself) -- a caller running inside Streamlit should pass an
    st.cache_data-wrapped version so the expensive Excel-loading/signal step
    is cached across calendar_method/styles/combine_method changes, which
    don't affect its output at all. This is a dependency-injection seam,
    not a behavior change: with the default fetcher, this function's output
    is identical to before.

    Thin wrapper around per_product_four_row() -- see that function's
    docstring for why the expensive part is split out separately."""
    per_product = per_product_fetcher(asset_class, tc_bps)
    wanted = styles if styles is not None else tuple(per_product.keys())
    gross = {style: combine_cross_asset(per_product[style]["gross"], calendar_method) for style in wanted}
    net = {style: combine_cross_asset(per_product[style]["net"], calendar_method) for style in wanted}
    return gross, net


def asset_class_ew_portfolio(gross_four_row: dict[str, pd.Series],
                              net_four_row: dict[str, pd.Series]) -> tuple[pd.Series, pd.Series]:
    """One asset class's own Equal Weight portfolio (Momentum + Combined
    Carry + Combined CarryMom + Value, or whichever subset was passed in),
    gross and net. This 4-row-to-1 combine always uses plain equal_weight
    regardless of calendar_method -- by the time asset_class_four_row() has
    produced these series (using calendar_method consistently at the
    product level), they already share one asset class's own calendar, so
    there is no cross-calendar question left to answer at this step."""
    return (combine_returns(list(gross_four_row.values()), "equal_weight"),
            combine_returns(list(net_four_row.values()), "equal_weight"))


def _combine_intersection(series_list: list[pd.Series]) -> pd.Series:
    """Bogorad-style: keep only dates where every series has a genuine
    observation -- but a date being dropped for the group must NOT silently
    delete another member's real, already-realized return on that date.

    FIXED 2026-08-04 (was a real bug, not just a theoretical concern -- see
    the worked 3-day example that found it): the original version summed
    already-computed DAILY returns and let NaN-propagation-then-dropna
    exclude mismatched dates. Concretely: if Copper trades 3rd/4th/5th and
    WTI trades only 3rd/5th, naive sum-then-drop discards Copper's real
    3rd->4th return entirely (the 4th-Jan row is NaN because WTI has
    nothing there, so it gets dropped -- taking Copper's valid return down
    with it) while WTI's full 3rd->5th move survives intact. That's
    asymmetric and wrong: the commodity that traded every day loses real
    P&L; the commodity with the gap keeps all of its P&L.

    The fix matches Bogorad's own paper (Section 4, p.12): "Any omitted
    ICE return on these isolated dates is naturally incorporated into the
    next available trading day's price." Convert each return series to a
    CUMULATIVE level first (cumsum of log-returns behaves exactly like a
    log-price -- same telescoping-sum math, whether the series is a raw
    product return or an already-aggregated asset-class/style return),
    restrict every series to the intersected date set, then take the DIFF
    across those surviving dates. A dropped date's move is then naturally
    absorbed into whichever surviving date comes next for EVERY series
    independently -- nothing silently deleted, nothing double-counted.
    Verified against the 3-day example: Copper's level[5th] - level[3rd]
    correctly recovers its FULL 3rd->5th move (both legs), not just the
    4th->5th leg the old version kept.

    This is purely backward-looking (cumsum then diff on an already-sorted,
    already-past date index) -- no look-ahead is introduced."""
    cum_levels = [s.cumsum() for s in series_list]
    idx = cum_levels[0].index
    for c in cum_levels[1:]:
        idx = idx.intersection(c.index)
    idx = idx.sort_values()
    aligned = [c.reindex(idx).diff() for c in cum_levels]
    combined = aligned[0]
    for a in aligned[1:]:
        combined = combined + a
    return combined / len(series_list)


def _combine_zero_fill(series_list: list[pd.Series]) -> pd.Series:
    """Dimil-style: union of dates, a missing series gets an explicit 0.0
    return that day (at equal fixed weight, matching the other legs)."""
    idx = series_list[0].index
    for s in series_list[1:]:
        idx = idx.union(s.index)
    filled = [s.reindex(idx).fillna(0.0) for s in series_list]
    combined = filled[0]
    for s in filled[1:]:
        combined = combined + s
    return combined / len(filled)


def combine_cross_asset(series_list: list[pd.Series], calendar_method: str) -> pd.Series:
    if calendar_method not in ("intersection", "zero_fill"):
        raise ValueError(f"calendar_method must be 'intersection' or 'zero_fill', got {calendar_method!r}")
    return (_combine_intersection(series_list) if calendar_method == "intersection"
            else _combine_zero_fill(series_list))


STYLE_NAMES = ("Momentum", "Combined Carry", "Combined CarryMom", "Value")
STYLE_DISPLAY = {"Momentum": "Momentum", "Combined Carry": "Carry", "Combined CarryMom": "CarryMom", "Value": "Value"}


def cross_commodity_dynamic(calendar_method: str, tc_bps: int = TC_BPS,
                             asset_classes: tuple[str, ...] = tuple(ASSET_CLASSES),
                             styles: tuple[str, ...] = STYLE_NAMES,
                             combine_method: str = "equal_weight",
                             per_product_fetcher=per_product_four_row
                             ) -> tuple[dict[str, pd.Series], dict[str, pd.Series]]:
    """Two-stage hierarchical Cross-Commodity Portfolio (Methodology doc
    Section 9), generalized for a live UI: first equal-weight each selected
    style across the SELECTED asset classes (Momentum/Carry/CarryMom/Value
    -> one cross-commodity series each), then combine those style-level
    series into one portfolio via `combine_method` ("equal_weight" or
    "risk_parity"). NOT a single flat optimization over every underlying
    leg. Dimil's own construction is the default (all 4 asset classes, all
    4 styles, equal_weight) -- see cross_commodity_portfolio() below for the
    exact-match validated form this generalizes from.

    Returns (gross_dict, net_dict), each keyed by style display name
    ("Momentum"/"Carry"/"CarryMom"/"Value" -- NOT "Combined Carry", matching
    Dimil's own row naming) plus "Portfolio" for the final combined result.
    Requires >=2 asset classes and >=1 style; with exactly 1 style selected,
    "Portfolio" is identical to that one style (nothing to combine)."""
    if len(asset_classes) < 2:
        raise ValueError("cross_commodity_dynamic needs at least 2 asset classes")
    if not styles:
        raise ValueError("cross_commodity_dynamic needs at least 1 style")

    per_asset = {ac: asset_class_four_row(ac, calendar_method, tc_bps, styles, per_product_fetcher)
                 for ac in asset_classes}

    gross_styles, net_styles = {}, {}
    for style in styles:
        label = STYLE_DISPLAY[style]
        gross_styles[label] = combine_cross_asset([per_asset[ac][0][style] for ac in asset_classes], calendar_method)
        net_styles[label] = combine_cross_asset([per_asset[ac][1][style] for ac in asset_classes], calendar_method)

    if len(styles) == 1:
        only = next(iter(gross_styles))
        return {**gross_styles, "Portfolio": gross_styles[only]}, {**net_styles, "Portfolio": net_styles[only]}

    if combine_method == "equal_weight":
        g_port = combine_cross_asset(list(gross_styles.values()), calendar_method)
        n_port = combine_cross_asset(list(net_styles.values()), calendar_method)
    elif combine_method == "risk_parity":
        # rolling_erc_combine does its own strict dropna(how="any") internally on whatever series
        # it's given -- for zero_fill inputs, the injected zero-return days are real data points
        # to its rolling covariance estimate (not re-filtered out here); for intersection inputs,
        # its own dropna is redundant with (not a second, different filter from) what
        # combine_cross_asset already did. Either way, no special-casing needed here.
        g_port, _ = rolling_erc_combine(gross_styles, tilt=0.0)
        n_port, _ = rolling_erc_combine(net_styles, tilt=0.0)
    else:
        raise ValueError(f"combine_method must be 'equal_weight' or 'risk_parity', got {combine_method!r}")

    return {**gross_styles, "Portfolio": g_port}, {**net_styles, "Portfolio": n_port}


def cross_commodity_portfolio(calendar_method: str, tc_bps: int = TC_BPS) -> dict[str, pd.Series]:
    """Dimil's exact construction (all 4 asset classes, all 4 styles, Equal
    Weight AND Risk Parity both computed) -- kept as the validated,
    known-good reference form (see research/_validate_cross_asset_engine.py:
    9 of 10 rows match his real pushed numbers to 3 decimal places under
    zero_fill). cross_commodity_dynamic() above is the generalized version
    the live UI actually drives; this one exists so that validation script
    keeps working unchanged and there's always a fixed point to check new
    changes against."""
    g_ew, n_ew = cross_commodity_dynamic(calendar_method, tc_bps, tuple(ASSET_CLASSES), STYLE_NAMES, "equal_weight")
    _, n_rp = cross_commodity_dynamic(calendar_method, tc_bps, tuple(ASSET_CLASSES), STYLE_NAMES, "risk_parity")
    out = {k: v for k, v in n_ew.items() if k != "Portfolio"}
    out["EW PORT"] = n_ew["Portfolio"]
    out["Risk Parity"] = n_rp["Portfolio"]
    return out


def cross_n_portfolio(calendar_method: str, tc_bps: int = TC_BPS,
                       asset_classes: tuple[str, ...] = ("metals", "energy"),
                       per_product_fetcher=per_product_four_row
                       ) -> tuple[dict[str, pd.Series], dict[str, pd.Series]]:
    """Generalized Cross-Pair -> Cross-N: equal-weight combination of 2-4
    asset classes' own Equal Weight portfolios (Methodology doc Section 9's
    Cross-Pair construction, generalized from exactly-2 to 2-4). Returns
    (gross_dict, net_dict) keyed by asset class label plus "Portfolio" for
    the final N-way combination."""
    if not 2 <= len(asset_classes) <= 4:
        raise ValueError("cross_n_portfolio needs 2 to 4 asset classes")
    gross_by_class, net_by_class = {}, {}
    for ac in asset_classes:
        g4, n4 = asset_class_four_row(ac, calendar_method, tc_bps, per_product_fetcher=per_product_fetcher)
        g_ew, n_ew = asset_class_ew_portfolio(g4, n4)
        gross_by_class[ASSET_CLASS_LABELS[ac]] = g_ew
        net_by_class[ASSET_CLASS_LABELS[ac]] = n_ew
    g_port = combine_cross_asset(list(gross_by_class.values()), calendar_method)
    n_port = combine_cross_asset(list(net_by_class.values()), calendar_method)
    return {**gross_by_class, "Portfolio": g_port}, {**net_by_class, "Portfolio": n_port}


def cross_pair_portfolios(calendar_method: str, tc_bps: int = TC_BPS) -> dict[str, pd.Series]:
    """Dimil's exact 4 Cross-Pair Portfolios (Methodology doc Section 9):
    50/50 combination of two asset classes' own Equal Weight portfolios,
    for the 4 least-correlated pairs (Metals-Precious and Energy-NGL
    excluded per Dimil's own note). Kept as the validated, known-good
    reference form -- cross_n_portfolio() above is the generalized version
    (2-4 asset classes, user-selectable) the live UI actually drives."""
    out = {}
    for a, b in CROSS_PAIRS:
        _, n_dict = cross_n_portfolio(calendar_method, tc_bps, (a, b))
        out[CROSS_PAIR_LABELS[(a, b)]] = n_dict["Portfolio"]
    return out


def windows_for(series: pd.Series) -> dict[str, dict]:
    """Full-sample + regime + expanding-window metrics, matching every other
    report in this project (research/run_regime_table.py's own convention)."""
    out = {"full": _metrics(series.loc[REPORT_START:])}
    for rname, start, end in REGIMES:
        out[rname.split("_")[0]] = _metrics(series.loc[start:end])
    out["expA"] = _metrics(series.loc[REPORT_START:"2015-12-31"])
    out["expB"] = _metrics(series.loc[REPORT_START:"2019-12-31"])
    out["expC"] = _metrics(series.loc[REPORT_START:"2021-12-31"])
    out["expD"] = _metrics(series.loc[REPORT_START:])
    out["y26"] = _metrics(series.loc["2026-01-01":])
    return out


def full_report(calendar_method: str, tc_bps: int = TC_BPS) -> dict:
    """Everything needed to render one calendar method's tab: windowed
    metrics for the Cross-Commodity Portfolio's 6 rows and the 4 Cross-Pair
    Portfolios."""
    cc = cross_commodity_portfolio(calendar_method, tc_bps)
    cp = cross_pair_portfolios(calendar_method, tc_bps)
    return {
        "cross_commodity": {name: windows_for(series) for name, series in cc.items()},
        "cross_pair": {name: windows_for(series) for name, series in cp.items()},
    }
