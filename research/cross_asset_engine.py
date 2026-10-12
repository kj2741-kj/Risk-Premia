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

Calendar alignment: FINALIZED 2026-08-04 as intersection-only (Mark
Bogorad, "Risk Premia in Diversified Energy Portfolios", Dec 2025, Section
4 Data, p.12: "we eliminate dates on which CME and ICE calendars do not
overlap, retaining only trading days when all contracts in the universe
are simultaneously open... Any omitted ICE return on these isolated dates
is naturally incorporated into the next available trading day's price").
Every asset class must have a genuine return for a date to count -- but
critically, per that last sentence, a dropped date must NOT silently
delete another member's real return on that date. Implemented (see
_combine_intersection, fixed 2026-08-04 after a real bug was found via a
worked example) by converting each series to a cumulative level,
restricting to the intersected dates, and diffing ACROSS those surviving
dates -- not by summing already-computed daily returns and dropping
mismatched ones, which silently discarded real P&L for whichever member
DIDN'T have the gap.

This project previously carried a second convention, "zero_fill" (Dimil
Patel's union + explicit-zero-on-non-trading-days), as an equally-weighted
live UI toggle pending a decision. Removed 2026-08-04 (user's decision) in
favor of intersection alone, for two documented reasons: (1) zero_fill
systematically dilutes the equal-weight combine on any date one leg isn't
trading (dividing by the full leg count including an artificial 0.0),
mechanically suppressing volatility and inflating Sharpe/IR -- exactly what
Bogorad's own paper cites intersection as preventing ("This strict calendar
alignment prevents artificial suppression of volatility caused by
asynchronous holiday gaps"); (2) for the Risk Parity leg specifically, a
real return paired against an injected zero on the same date is a real data
point fed into the rolling covariance estimate, which can bias correlation
toward zero on exactly the days it's least informative to do so. A
diagnostic (research/_calendar_diagnostic.py, 2026-08-04) found strict
intersection loses 4.35% of the union's trading days across the 4 asset
classes, concentrated in Metals/Precious/NGL (Energy is never the missing
one) -- an accepted, known tradeoff of this convention, not eliminated by
the bug fix above, just no longer compounded by a silent PnL deletion on
top of it.

Signal-level Carry / Carry momentum construction (Methodology doc Section 7,
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
from typing import NamedTuple

import numpy as np
import pandas as pd

_RESEARCH_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIGS_DIR = os.path.join(_RESEARCH_DIR, "configs")
for _p in (_RESEARCH_DIR, _CONFIGS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engine import (raw_signal_carry_v1, raw_signal_carry_v2, raw_signal_carrymom, raw_signal_skewness,
                     combine_positions, combine_returns, exec_shift, log_return_daily,
                     momentum_composite_position, value_v1_position)
from risk_parity import rolling_erc_combine
from drp import rolling_drp_combine
from run_regime_table import _metrics
from regimes import REGIMES, REPORT_START

# ASSET_CLASSES is the original four-class set that the validated reference forms
# (cross_commodity_portfolio's defaults, cross_pair_portfolios, research/_validate_cross_asset_engine.py)
# are checked against -- unchanged. Agriculture was added 2026-10-11 as a fifth, selectable asset class:
# ALL_ASSET_CLASSES is what the live hub offers, and every function below that takes an `asset_classes`
# argument accepts "agri" alongside the original four.
ASSET_CLASSES = ["metals", "energy", "precious", "ngl"]
ALL_ASSET_CLASSES = ASSET_CLASSES + ["agri"]
ASSET_CLASS_LABELS = {"metals": "Metals", "energy": "Energy", "precious": "Precious", "ngl": "NGL",
                      "agri": "Agriculture"}
# Dashboard-visible product lists (CLAUDE.md's documented exclusion: research configs' PRODUCTS
# is NOT what the live dashboard, or the cross-asset numbers, are built on -- Energy excludes
# Singapore Gasoil + Fuel Oil, NGL excludes Ethylene + Propylene, Precious excludes Copper
# (COMEX); Metals unfiltered). Confirmed empirically: cfg.PRODUCTS (7-product) Energy Momentum
# full-sample IR=0.586 vs this filtered (5-product) basis IR=0.430, matching the real pushed
# number of IR=0.436 -- close to the filtered basis, nowhere near the unfiltered one. Using
# cfg.PRODUCTS here would silently pull in Singapore Gasoil/Fuel Oil, Ethylene/Propylene, and
# Copper (COMEX), which the cross-asset methodology should not.
# Copper (COMEX) removed from Precious 2026-08-05: miscategorized originally -- Copper is an
# industrial metal already covered by the Metals asset class (LME), not a precious metal.
DASHBOARD_PRODUCTS = {
    "energy": ["WTI", "Brent", "RBOB", "HeatingOil", "NatGas"],
    "ngl": ["Ethane", "Propane", "Butane", "Isobutane"],
    "precious": ["Gold", "Silver", "Platinum", "Palladium"],
    # Agriculture: six products only (2026-10-11), matching research/configs/agri.py's PRODUCTS and the
    # Agriculture dashboard. The other nine of the original 14-product build never enter a portfolio.
    "agri": ["Corn", "Wheat", "Soybean", "SoybeanOil", "Coffee", "Sugar"],
}
# All 6 possible pairs across the 4 asset classes. Metals-Precious and Energy-NGL are the two
# most correlated pairs (Correlations tab) -- included here too (2026-08-05) so that's visible
# directly in the Cross-Pair Portfolios numbers rather than assumed from the correlation tab alone.
CROSS_PAIRS = [("metals", "energy"), ("metals", "ngl"), ("precious", "energy"), ("precious", "ngl"),
               ("metals", "precious"), ("energy", "ngl")]
CROSS_PAIR_LABELS = {
    ("metals", "energy"): "Metals-Energy", ("metals", "ngl"): "Metals-NGL",
    ("precious", "energy"): "Precious-Energy", ("precious", "ngl"): "Precious-NGL",
    ("metals", "precious"): "Metals-Precious", ("energy", "ngl"): "Energy-NGL",
}
TC_BPS = 5

_CFG_CACHE: dict[str, object] = {}


def _get_cfg(asset_class: str):
    if asset_class not in _CFG_CACHE:
        _CFG_CACHE[asset_class] = importlib.import_module(asset_class)
    return _CFG_CACHE[asset_class]


CARRY_VARIANT_LABELS = {"V1": "V1 - Carry slope", "V2": "V2 - Z-score on carry slope"}
DEFAULT_CARRY_VARIANTS = ("V2",)       # the 2026-10-10 rule: V2 only
LEGACY_CARRY_VARIANTS = ("V1", "V2")   # the older V1+V2 composite, kept to reproduce pre-rule numbers


class CarrySpec(NamedTuple):
    """Hashable Carry settings for ONE asset class (so a Streamlit cache can key on it).
    `variants`: which Carry signals form the composite ("V2" alone = the 10 Oct rule; ("V1","V2") = the
    older composite). `zwindow`: V2's z-score window. `horizon`: Carry momentum (V3) horizon.
    `pairs`: the (near, far) tenor pairs, blended at signal level; each is used for Carry AND Carry
    momentum. A None field means "use the asset class's config value"."""
    variants: tuple = DEFAULT_CARRY_VARIANTS
    zwindow: int | None = None
    horizon: int | None = None
    pairs: tuple | None = None


def resolve_carry_spec(asset_class: str, spec: CarrySpec | None = None) -> CarrySpec:
    """Fill every None field from the asset class's config and validate the result."""
    cfg = _get_cfg(asset_class)
    spec = spec if spec is not None else CarrySpec()
    variants = tuple(v for v in ("V1", "V2") if v in tuple(spec.variants))
    if not variants or set(spec.variants) - {"V1", "V2"}:
        raise ValueError(f"carry variants must be a non-empty subset of ('V1','V2'), got {tuple(spec.variants)!r}")
    zwindow = int(spec.zwindow if spec.zwindow is not None else cfg.CARRY_ZSCORE_WINDOW)
    horizon = int(spec.horizon if spec.horizon is not None else cfg.CARRY_MOMENTUM_HORIZON)
    if not 20 <= zwindow <= 756:
        raise ValueError(f"zwindow must be 20-756, got {zwindow}")
    if not 1 <= horizon <= 252:
        raise ValueError(f"horizon must be 1-252, got {horizon}")
    raw_pairs = spec.pairs if spec.pairs is not None else cfg.CARRY_TENOR_PAIRS
    pairs = []
    for near, far in raw_pairs:
        if int(str(near)[1:]) >= int(str(far)[1:]):
            raise ValueError(f"tenor pair {near}-{far}: near must be a shorter tenor than far")
        if (str(near), str(far)) not in pairs:
            pairs.append((str(near), str(far)))
    if not pairs:
        raise ValueError(f"{asset_class}: no Carry tenor pair configured or chosen")
    return CarrySpec(variants, zwindow, horizon, tuple(pairs))


def default_carry_spec(asset_class: str) -> CarrySpec:
    """The rule default for one asset class: V2 only, the config's z-window, horizon and tenor pairs."""
    return resolve_carry_spec(asset_class, CarrySpec())


def _carry_composite_raw(curve: pd.DataFrame, near: str, far: str, window: int,
                          variants: tuple = DEFAULT_CARRY_VARIANTS) -> pd.Series:
    """Raw (pre-shift) Carry signal for ONE tenor pair: V2 alone by default (10 Oct rule), or the
    equal-weight composite of whichever `variants` are given (("V1","V2") = the older V1+V2 composite,
    same formula as engine.py's carry_v1v2_composite_position one step earlier, no shift). Returned
    unshifted so it can be combined with another tenor pair's signal before a single shift is applied."""
    sigs = []
    if "V1" in variants:
        sigs.append(raw_signal_carry_v1(curve, near, far))
    if "V2" in variants:
        sigs.append(raw_signal_carry_v2(curve, near, far, window=window))
    sigs = [x for x in sigs if not x.empty]
    if not sigs:
        return pd.Series(dtype=float)
    return sigs[0] if len(sigs) == 1 else combine_positions(sigs, "equal_weight")


# Skewness (added 2026-10-12): optional FIFTH style, off by default so every validated function below
# keeps its four-style output. Time-series form (one +1/-1 per product from minus the rolling skewness of
# the ratio-stitched continuous series' daily log returns), same rule as scripts/final_dashboard/
# skewness_research.py and the dashboards' Skewness tab (engine.raw_signal_skewness).
SKEWNESS_STYLE = "Skewness"
SKEWNESS_WINDOW_DEFAULT = 252
SKEWNESS_SHIFT_N_DEFAULT = 1


def per_product_four_row(asset_class: str, tc_bps: int = TC_BPS,
                          carry_spec: CarrySpec | None = None,
                          per_product_pairs: bool = False,
                          include_skewness: bool = False) -> dict[str, dict[str, list]]:
    """Momentum / Combined Carry / Combined CarryMom / Value gross AND net
    daily log-return series PER PRODUCT (not yet combined across products)
    for one asset class, on the dashboard-filtered product universe.
    Returns {style: {"gross": [...], "net": [...], "names": [...]}} -- the
    three lists stay index-aligned (out[style]["names"][i] is the product
    that produced out[style]["gross"][i]/["net"][i]), which a product can
    fail to contribute to (an empty net series is skipped, so list length
    can be less than len(products) and differ by style). "names" added
    2026-08-04 for dynamic_risk_parity combining (research/drp.py), which
    needs a named dict, not a positional list -- purely additive, every
    existing reader of "gross"/"net" is unaffected. Signal-level Carry/
    CarryMom combination across tenor pairs when the asset class has >=2
    (verified against Dimil's real Metals numbers); a single tenor pair
    (Precious Metals) just flows through combine_positions with one leg, a
    no-op sign(), identical to using it directly.

    This is the expensive step (Excel curve loading + signal computation
    across every product). Callers combine this function's output via
    combine_cross_asset() or rolling_drp_combine() themselves (see
    asset_class_four_row below). Splitting it out this way lets a caller
    cache this function's result once per (asset_class, tc_bps) and reuse
    it freely."""
    cfg = _get_cfg(asset_class)
    spec = resolve_carry_spec(asset_class, carry_spec)
    products = DASHBOARD_PRODUCTS.get(asset_class, cfg.PRODUCTS)
    # per_product_pairs (added 2026-10-11, default False so every existing caller, including the Streamlit hub, is unchanged):
    # when True each product uses its own pairs from cfg.carry_pairs(product) (Precious and Agriculture: the short F1-F2 pair plus
    # a long pair about 12 months out whose far leg differs by product; the other asset classes return the uniform pairs) instead of
    # one pair list for the whole asset class. spec.pairs is then ignored; zwindow / horizon / variants still come from `spec`.
    if per_product_pairs:
        pairs_by_product = {p: [(str(n), str(f)) for n, f in cfg.carry_pairs(p)] for p in products}
    else:
        pairs_by_product = {p: list(spec.pairs) for p in products}
    tenor_pairs = list(dict.fromkeys(pr for v in pairs_by_product.values() for pr in v))   # union, for the data checks below
    out = {style: {"gross": [], "net": [], "names": []}
           for style in ("Momentum", "Combined Carry", "Combined CarryMom", "Value")}
    if include_skewness:
        # include_skewness (2026-10-12, default False): also return a "Skewness" entry with the same
        # gross/net/names layout. Callers that pass styles=None to asset_class_four_row() will then see
        # five styles, so pass `styles` explicitly when only the original four are wanted.
        out[SKEWNESS_STYLE] = {"gross": [], "net": [], "names": []}
    # n_pairs (added 2026-10-11): how many of the chosen tenor pairs actually had data for each product, index-aligned
    # with names, so a caller can flag a product that was blended on fewer pairs than the user chose.
    out["Combined Carry"]["n_pairs"], out["Combined CarryMom"]["n_pairs"] = [], []
    pair_has_data = {pair: False for pair in tenor_pairs}

    for p in products:
        curve = cfg.load_curve(p)
        raw = cfg.load_f1_series_logret(p)
        log_price, phase, f1r = raw["log_price"], raw["Phase"], raw["F1_raw"]

        mom_pos = momentum_composite_position(f1r, cfg.MOMENTUM_PAIRS, shift_n=cfg.MOMENTUM_SHIFT_N)
        g, n = log_return_daily(mom_pos, log_price, tc_bps, phase)
        if not n.empty:
            out["Momentum"]["gross"].append(g)
            out["Momentum"]["net"].append(n)
            out["Momentum"]["names"].append(p)

        carry_raws = [_carry_composite_raw(curve, near, far, spec.zwindow, spec.variants)
                      for near, far in pairs_by_product[p]]
        for pair, r in zip(pairs_by_product[p], carry_raws):
            pair_has_data[pair] = pair_has_data[pair] or (not r.empty)
        carry_raws = [r for r in carry_raws if not r.empty]
        if carry_raws:
            combo = carry_raws[0] if len(carry_raws) == 1 else combine_positions(carry_raws, "equal_weight")
            pos = exec_shift(combo, cfg.CARRY_SHIFT_N).fillna(0)
            g, n = log_return_daily(pos, log_price, tc_bps, phase)
            if not n.empty:
                out["Combined Carry"]["gross"].append(g)
                out["Combined Carry"]["net"].append(n)
                out["Combined Carry"]["names"].append(p)
                out["Combined Carry"]["n_pairs"].append(len(carry_raws))

        cm_raws = [raw_signal_carrymom(curve, near, far, spec.horizon)
                   for near, far in pairs_by_product[p]]
        cm_raws = [r for r in cm_raws if not r.empty]
        if cm_raws:
            combo = cm_raws[0] if len(cm_raws) == 1 else combine_positions(cm_raws, "equal_weight")
            pos = exec_shift(combo, cfg.CARRY_MOMENTUM_SHIFT_N).fillna(0)
            g, n = log_return_daily(pos, log_price, tc_bps, phase)
            if not n.empty:
                out["Combined CarryMom"]["gross"].append(g)
                out["Combined CarryMom"]["net"].append(n)
                out["Combined CarryMom"]["names"].append(p)
                out["Combined CarryMom"]["n_pairs"].append(len(cm_raws))

        val_pos = value_v1_position(curve, cfg.VALUE_CONTRACT, cfg.VALUE_LOOKBACK_DAYS,
                                     cfg.VALUE_THRESHOLD, shift_n=cfg.VALUE_SHIFT_N)
        g, n = log_return_daily(val_pos, log_price, tc_bps, phase)
        if not n.empty:
            out["Value"]["gross"].append(g)
            out["Value"]["net"].append(n)
            out["Value"]["names"].append(p)

        if include_skewness:
            sk_raw = raw_signal_skewness(log_price, getattr(cfg, "SKEWNESS_WINDOW", SKEWNESS_WINDOW_DEFAULT))
            sk_pos = exec_shift(sk_raw, getattr(cfg, "SKEWNESS_SHIFT_N", SKEWNESS_SHIFT_N_DEFAULT)).fillna(0)
            g, n = log_return_daily(sk_pos, log_price, tc_bps, phase)
            if not n.empty:
                out[SKEWNESS_STYLE]["gross"].append(g)
                out[SKEWNESS_STYLE]["net"].append(n)
                out[SKEWNESS_STYLE]["names"].append(p)

    dead = [f"{n}-{f}" for (n, f), ok in pair_has_data.items() if not ok]
    if dead:
        raise ValueError(f"{asset_class}: tenor pair(s) {dead} have no data for any product in this asset class; "
                         f"choose pairs that exist in the curve")
    for style in ("Combined Carry", "Combined CarryMom"):
        if not out[style]["net"]:
            raise ValueError(f"{asset_class}: no product has data for {style} with tenor pairs "
                             f"{[f'{n}-{f}' for n, f in tenor_pairs]}; pick pairs that exist in the curve")
    return out


PRODUCT_COMBINE_METHODS = ("equal_weight", "dynamic_risk_parity")


def asset_class_four_row(asset_class: str, tc_bps: int = TC_BPS, styles: tuple[str, ...] | None = None,
                          per_product_fetcher=per_product_four_row, combine_method: str = "equal_weight"
                          ) -> tuple[dict[str, pd.Series], dict[str, pd.Series]]:
    """Momentum / Combined Carry / Combined CarryMom / Value gross AND net
    daily log-return series for one asset class, combined across its
    products. Returns (gross_dict, net_dict).

    `combine_method`: "equal_weight" (default, UNCHANGED behavior) combines
    products via combine_cross_asset()'s intersection convention (see
    module docstring). "dynamic_risk_parity" (2026-08-04, Phase 2) instead
    risk-weights products via research/drp.py's rolling_drp_combine() --
    Bogorad's Section 6.2 EWMA-vol/EWMA-cov/shrinkage/inverse-vol/vol-target
    recipe -- applied at the PRODUCT level per style, matching where the
    paper's own mechanism actually operates (asset/commodity level, not
    strategy/style level; see the style-level counterpart in
    asset_class_ew_portfolio below). Requires per_product_fetcher's output
    to include "names" (added alongside "gross"/"net" in per_product_four_
    row -- present on every code path as of 2026-08-04).

    Applying intersection (or DRP) at this per-product level matters in
    practice, not just in principle: Energy is the only asset class with a
    real internal exchange split (NYMEX vs ICE) -- without combining its
    products this way, Energy's own numbers sit measurably off the
    cross-commodity/cross-pair numbers that combine this function's output
    one level up.

    `styles`, if given, restricts to a subset of the 4 (e.g. for a live UI
    toggle) -- default is all 4.

    `per_product_fetcher` defaults to the plain, uncached per_product_four_
    row() (this module deliberately stays Streamlit-free, so it can't cache
    directly itself) -- a caller running inside Streamlit should pass an
    st.cache_data-wrapped version so the expensive Excel-loading/signal step
    is cached across styles/combine_method changes, which don't affect its
    output at all. This is a dependency-injection seam, not a behavior
    change: with the default fetcher and combine_method, this function's
    output is identical to before Phase 2.

    Thin wrapper around per_product_four_row() -- see that function's
    docstring for why the expensive part is split out separately."""
    if combine_method not in PRODUCT_COMBINE_METHODS:
        raise ValueError(f"combine_method must be one of {PRODUCT_COMBINE_METHODS}, got {combine_method!r}")
    per_product = per_product_fetcher(asset_class, tc_bps)
    wanted = styles if styles is not None else tuple(per_product.keys())

    if combine_method == "equal_weight":
        gross = {style: combine_cross_asset(per_product[style]["gross"]) for style in wanted}
        net = {style: combine_cross_asset(per_product[style]["net"]) for style in wanted}
    else:  # "dynamic_risk_parity"
        gross = {style: rolling_drp_combine(dict(zip(per_product[style]["names"],
                                                       per_product[style]["gross"])))[0]
                  for style in wanted}
        net = {style: rolling_drp_combine(dict(zip(per_product[style]["names"],
                                                     per_product[style]["net"])))[0]
                for style in wanted}
    return gross, net


STYLE_COMBINE_METHODS = ("equal_weight", "risk_parity", "dynamic_risk_parity")


def asset_class_ew_portfolio(gross_four_row: dict[str, pd.Series], net_four_row: dict[str, pd.Series],
                              combine_method: str = "equal_weight") -> tuple[pd.Series, pd.Series]:
    """One asset class's own style-level portfolio (Momentum + Combined
    Carry + Combined CarryMom + Value, or whichever subset was passed in),
    gross and net.

    `combine_method`: "equal_weight" (default, UNCHANGED behavior) -- by
    the time asset_class_four_row() has produced these series, they
    already share one asset class's own calendar, so there is no
    cross-calendar question left to answer at this step; combine_returns()
    is used directly (not combine_cross_asset(), which would additionally
    NaN the very first row via its cumsum-diff mechanism -- unnecessary
    and behavior-changing when every input already shares one index).
    "risk_parity" (2026-08-04, Phase 4) risk-weights the 4 styles via
    research/risk_parity.py's rolling_erc_combine() (tilt=0.0, pure ERC) --
    added to regenerate the dashboard's existing per-asset-class "Risk
    Parity (ERC, rolling)" row, which previously had no home in this module
    (only the cross-asset-class level had an ERC option, via
    cross_commodity_dynamic). "dynamic_risk_parity" (2026-08-04, Phase 2)
    instead risk-weights the 4 STYLES against each other via
    research/drp.py's rolling_drp_combine() -- the naming keeps this
    distinct from asset_class_four_row's own dynamic_risk_parity option
    above, which risk-weights PRODUCTS within a style instead; the two are
    independent layers and can be mixed freely by the caller (e.g.
    product-level DRP feeding into a style-level EW combine, or vice
    versa)."""
    if combine_method not in STYLE_COMBINE_METHODS:
        raise ValueError(f"combine_method must be one of {STYLE_COMBINE_METHODS}, got {combine_method!r}")
    if combine_method == "equal_weight":
        return (combine_returns(list(gross_four_row.values()), "equal_weight"),
                combine_returns(list(net_four_row.values()), "equal_weight"))
    elif combine_method == "risk_parity":
        g_port, _ = rolling_erc_combine(gross_four_row, tilt=0.0)
        n_port, _ = rolling_erc_combine(net_four_row, tilt=0.0)
        return g_port, n_port
    else:  # "dynamic_risk_parity"
        g_port, _ = rolling_drp_combine(gross_four_row)
        n_port, _ = rolling_drp_combine(net_four_row)
        return g_port, n_port


def combine_cross_asset(series_list: list[pd.Series]) -> pd.Series:
    """Bogorad-style intersection combine: keep only dates where every
    series has a genuine observation -- but a date being dropped for the
    group must NOT silently delete another member's real, already-realized
    return on that date.

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
    already-past date index) -- no look-ahead is introduced.

    This is the ONLY calendar-alignment convention this module supports as
    of 2026-08-04 -- a prior "zero_fill" (Dimil Patel's union + explicit
    zero on non-trading days) alternative was removed by the user's
    decision; see module docstring for the full rationale."""
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


STYLE_NAMES = ("Momentum", "Combined Carry", "Combined CarryMom", "Value")
ALL_STYLE_NAMES = STYLE_NAMES + (SKEWNESS_STYLE,)     # the four validated styles plus the optional fifth
STYLE_DISPLAY = {"Momentum": "Momentum", "Combined Carry": "Carry", "Combined CarryMom": "CarryMom", "Value": "Value",
                 SKEWNESS_STYLE: "Skewness"}
# "inverse_vol" (2026-10-12): style-level Inverse Vol as in the Final Research Dashboard (1/trailing 63-day vol,
# lagged one day, via engine.combine_returns). Appended last; the three original methods are unchanged.
CROSS_COMMODITY_COMBINE_METHODS = ("equal_weight", "risk_parity", "dynamic_risk_parity", "inverse_vol")


def cross_commodity_dynamic(tc_bps: int = TC_BPS,
                             asset_classes: tuple[str, ...] = tuple(ASSET_CLASSES),
                             styles: tuple[str, ...] = STYLE_NAMES,
                             combine_method: str = "equal_weight",
                             per_product_fetcher=per_product_four_row
                             ) -> tuple[dict[str, pd.Series], dict[str, pd.Series]]:
    """Two-stage hierarchical Cross-Commodity Portfolio (Methodology doc
    Section 9), generalized for a live UI: first equal-weight each selected
    style across the SELECTED asset classes (Momentum/Carry/CarryMom/Value
    -> one cross-commodity series each), then combine those style-level
    series into one portfolio via `combine_method` -- "equal_weight",
    "risk_parity" (ERC, research/risk_parity.py), or "dynamic_risk_parity"
    (Bogorad's Section 6.2 EWMA/shrinkage/vol-target recipe,
    research/drp.py; added 2026-08-04, Phase 3 -- the direct analog of the
    paper's own "DRP PORT" in Table 6, here risk-weighting the 4 STYLES
    across all selected asset classes at once). NOT a single flat
    optimization over every underlying leg. Dimil's own construction is the
    default (all 4 asset classes, all 4 styles, equal_weight) -- see
    cross_commodity_portfolio() below for the exact-match validated form
    this generalizes from.

    Returns (gross_dict, net_dict), each keyed by style display name
    ("Momentum"/"Carry"/"CarryMom"/"Value" -- NOT "Combined Carry", matching
    Dimil's own row naming) plus "Portfolio" for the final combined result.
    Requires >=2 asset classes and >=1 style; with exactly 1 style selected,
    "Portfolio" is identical to that one style (nothing to combine)."""
    if len(asset_classes) < 2:
        raise ValueError("cross_commodity_dynamic needs at least 2 asset classes")
    if not styles:
        raise ValueError("cross_commodity_dynamic needs at least 1 style")
    if combine_method not in CROSS_COMMODITY_COMBINE_METHODS:
        raise ValueError(f"combine_method must be one of {CROSS_COMMODITY_COMBINE_METHODS}, "
                          f"got {combine_method!r}")

    per_asset = {ac: asset_class_four_row(ac, tc_bps, styles, per_product_fetcher)
                 for ac in asset_classes}

    gross_styles, net_styles = {}, {}
    for style in styles:
        label = STYLE_DISPLAY[style]
        gross_styles[label] = combine_cross_asset([per_asset[ac][0][style] for ac in asset_classes])
        net_styles[label] = combine_cross_asset([per_asset[ac][1][style] for ac in asset_classes])

    if len(styles) == 1:
        only = next(iter(gross_styles))
        return {**gross_styles, "Portfolio": gross_styles[only]}, {**net_styles, "Portfolio": net_styles[only]}

    if combine_method == "equal_weight":
        g_port = combine_cross_asset(list(gross_styles.values()))
        n_port = combine_cross_asset(list(net_styles.values()))
    elif combine_method == "risk_parity":
        g_port, _ = rolling_erc_combine(gross_styles, tilt=0.0)
        n_port, _ = rolling_erc_combine(net_styles, tilt=0.0)
    elif combine_method == "inverse_vol":
        g_port = combine_returns(list(gross_styles.values()), "inverse_vol", vol_window=63)
        n_port = combine_returns(list(net_styles.values()), "inverse_vol", vol_window=63)
    else:  # "dynamic_risk_parity"
        g_port, _ = rolling_drp_combine(gross_styles)
        n_port, _ = rolling_drp_combine(net_styles)

    return {**gross_styles, "Portfolio": g_port}, {**net_styles, "Portfolio": n_port}


def cross_commodity_portfolio(tc_bps: int = TC_BPS,
                               asset_classes: tuple[str, ...] = tuple(ASSET_CLASSES),
                               per_product_fetcher=per_product_four_row) -> dict[str, pd.Series]:
    """Dimil's exact construction (by default all 4 original asset classes, all 4 styles, Equal
    Weight AND Risk Parity both computed; pass asset_classes=ALL_ASSET_CLASSES to include
    Agriculture; Carry follows the 10 Oct rule (V2 only) unless per_product_fetcher says otherwise) -- kept as the validated,
    known-good reference form (see research/_validate_cross_asset_engine.py).
    cross_commodity_dynamic() above is the generalized version the live UI
    actually drives; this one exists so that validation script keeps
    working unchanged and there's always a fixed point to check new
    changes against."""
    g_ew, n_ew = cross_commodity_dynamic(tc_bps, tuple(asset_classes), STYLE_NAMES, "equal_weight",
                                          per_product_fetcher=per_product_fetcher)
    _, n_rp = cross_commodity_dynamic(tc_bps, tuple(asset_classes), STYLE_NAMES, "risk_parity",
                                       per_product_fetcher=per_product_fetcher)
    out = {k: v for k, v in n_ew.items() if k != "Portfolio"}
    out["EW PORT"] = n_ew["Portfolio"]
    out["Risk Parity"] = n_rp["Portfolio"]
    return out


CROSS_N_COMBINE_METHODS = ("equal_weight", "dynamic_risk_parity")


def cross_n_portfolio(tc_bps: int = TC_BPS,
                       asset_classes: tuple[str, ...] = ("metals", "energy"),
                       per_product_fetcher=per_product_four_row,
                       combine_method: str = "equal_weight",
                       styles: tuple[str, ...] | None = None,
                       ) -> tuple[dict[str, pd.Series], dict[str, pd.Series]]:
    """Generalized Cross-Pair -> Cross-N: combination of 1-5 asset classes'
    own Equal Weight portfolios (Methodology doc Section 9's Cross-Pair
    construction, generalized from exactly-2 to 1-5 with Agriculture added 2026-10-11). Returns (gross_dict,
    net_dict) keyed by asset class label plus "Portfolio" for the final
    N-way combination. With exactly 1 asset class, "Portfolio" is identical
    to that one asset class's own EW portfolio (nothing to combine) --
    this is also each asset class's own individual result, letting a user
    drop down to a single asset class and see its number on its own,
    matching the same single-item convention already used for styles in
    cross_commodity_dynamic() above.

    `combine_method` (2026-08-04, Phase 3): "equal_weight" (default,
    UNCHANGED behavior) combines the N asset classes' own EW portfolios via
    combine_cross_asset(). "dynamic_risk_parity" instead risk-weights them
    via research/drp.py's rolling_drp_combine() -- the direct analog of the
    paper's own "DRP PORT" in Table 6, here risk-weighting whole ASSET
    CLASSES (Metals/Energy/Precious/NGL) against each other instead of the
    paper's 5 strategy sleeves. Each asset class's OWN portfolio is still
    built via asset_class_ew_portfolio()'s default equal_weight regardless
    of this parameter -- this function only controls the top-level combine
    across asset classes, not how each one's own 4 styles get combined
    (that's asset_class_ew_portfolio's own combine_method, Phase 2, a
    separate, independent decision a caller can make by building
    gross_by_class/net_by_class itself instead of calling this function).
    No "risk_parity" (ERC) option here -- not requested for this level;
    cross_commodity_dynamic above has it if needed at the style level."""
    if not 1 <= len(asset_classes) <= len(ALL_ASSET_CLASSES):
        raise ValueError(f"cross_n_portfolio needs 1 to {len(ALL_ASSET_CLASSES)} asset classes")
    unknown = [ac for ac in asset_classes if ac not in ASSET_CLASS_LABELS]
    if unknown:
        raise ValueError(f"unknown asset class(es) {unknown}; valid: {list(ASSET_CLASS_LABELS)}")
    if combine_method not in CROSS_N_COMBINE_METHODS:
        raise ValueError(f"combine_method must be one of {CROSS_N_COMBINE_METHODS}, got {combine_method!r}")
    gross_by_class, net_by_class = {}, {}
    for ac in asset_classes:
        # `styles` (2026-10-12, default None = every style the fetcher returns, as before): lets a caller whose
        # fetcher also returns "Skewness" choose whether each asset class's own portfolio uses four or five styles.
        g4, n4 = asset_class_four_row(ac, tc_bps, styles, per_product_fetcher=per_product_fetcher)
        g_ew, n_ew = asset_class_ew_portfolio(g4, n4)
        gross_by_class[ASSET_CLASS_LABELS[ac]] = g_ew
        net_by_class[ASSET_CLASS_LABELS[ac]] = n_ew
    if len(asset_classes) == 1:
        only = next(iter(gross_by_class))
        return {**gross_by_class, "Portfolio": gross_by_class[only]}, {**net_by_class, "Portfolio": net_by_class[only]}
    if combine_method == "equal_weight":
        g_port = combine_cross_asset(list(gross_by_class.values()))
        n_port = combine_cross_asset(list(net_by_class.values()))
    else:  # "dynamic_risk_parity"
        g_port, _ = rolling_drp_combine(gross_by_class)
        n_port, _ = rolling_drp_combine(net_by_class)
    return {**gross_by_class, "Portfolio": g_port}, {**net_by_class, "Portfolio": n_port}


def cross_pair_portfolios(tc_bps: int = TC_BPS) -> dict[str, pd.Series]:
    """Dimil's exact 4 Cross-Pair Portfolios (Methodology doc Section 9):
    50/50 combination of two asset classes' own Equal Weight portfolios,
    for the 4 least-correlated pairs (Metals-Precious and Energy-NGL
    excluded per Dimil's own note). Kept as the validated, known-good
    reference form -- cross_n_portfolio() above is the generalized version
    (1-4 asset classes, user-selectable) the live UI actually drives."""
    out = {}
    for a, b in CROSS_PAIRS:
        _, n_dict = cross_n_portfolio(tc_bps, (a, b))
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


def full_report(tc_bps: int = TC_BPS) -> dict:
    """Everything needed to render the Cross-Asset tab: windowed metrics for
    the Cross-Commodity Portfolio's 6 rows and the 4 Cross-Pair Portfolios."""
    cc = cross_commodity_portfolio(tc_bps)
    cp = cross_pair_portfolios(tc_bps)
    return {
        "cross_commodity": {name: windows_for(series) for name, series in cc.items()},
        "cross_pair": {name: windows_for(series) for name, series in cp.items()},
    }
