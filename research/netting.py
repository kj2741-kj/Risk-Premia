"""Product-level netting of the flat transaction cost (user decision 2026-11-15). Used by the research dashboard pipeline
(scripts/final_dashboard) and by the Streamlit apps (cross_asset_engine.py, dashboard_portfolio_tab.py), so both report the same numbers.

RULE. Whenever several strategies (sleeves) of the SAME product sit in one portfolio, the product trades only the change in its net position:
    NP(t)      = sum_s a_s(t) * pos_s(t)          (a_s(t) = the sleeve's relative weight inside that portfolio on day t, sum_s a_s = 1)
    NP_prev(t) = sum_s a_s(t) * pos_s(t-1)        (same day's weights: only signal changes trade, weight drift is not charged,
                                                   exactly as the per-sleeve engine never charges re-weighting)
    units(t)   = |NP(t) - NP_prev(t)|  (+ |NP(0)| on the first day)
               + min(|NP|, |NP_prev|) on a roll day when NP and NP_prev are non-zero with the same sign (the net position is rolled)
    cost(t)    = units(t) * tc_bps / 10000 / 2       (the engine's half-of-round-trip convention, research/engine.py::log_return_transaction_cost)
For one sleeve with positions in {-1, 0, +1} this is exactly the engine's per-sleeve cost. Off roll days the netted cost is never larger
than the weighted per-sleeve cost (triangle inequality); netted() asserts it on every day.

IMPLEMENTATION. The netted product cost is pushed back into the sleeves: each sleeve's cost is scaled by k(t) = netted cost / weighted
per-sleeve cost (0 <= k <= 1), i.e. adjusted net_s = net_s + (1 - k) * tc_s. Any portfolio that combines these adjusted sleeves with the
SAME weights a_s(t) then carries exactly the netted cost (the scaling cancels in the weighted sum), and the existing combine functions and
their date alignment are reused unchanged. Single-strategy rows are NOT adjusted: a strategy shown on its own keeps its own cost.

WEIGHTS. Equal Weight: a_s = 1/n. Inverse Vol, Risk Parity (ERC) and Dynamic Risk Parity: the weight schedule the method solves on the
standalone (own-cost) sleeve-level series, i.e. the series displayed in the strategy rows; using the netted series instead would make the
weights depend on the cost they set. Weights at a portfolio-of-portfolios stage (across buckets) are solved on the netted portfolios, as
before, because those are the series being combined. A sleeve-level weight that applies to a coarser calendar (a bucket's or the book's common
dates) is mapped to each product date by the NEXT common date (backfill), because that is the date on which the product's return is booked
by the cumulative-level alignment (cross_asset_engine.combine_cross_asset)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import log_return_transaction_cost

ROLL_PREFIX = "Roll_LTD"


def sleeve_costs(pos: dict[str, pd.Series], phase: pd.Series | None, tc_bps: float, index: pd.Index) -> pd.DataFrame:
    """Per-sleeve engine cost (log-return units) on `index`, identical to the cost inside log_return_daily."""
    return pd.DataFrame({s: log_return_transaction_cost(p.reindex(index).fillna(0.0), tc_bps, phase) for s, p in pos.items()}, index=index)


def netted_cost(pos: pd.DataFrame, phase: pd.Series | None, a: pd.DataFrame, tc_bps: float) -> pd.Series:
    """Netted product cost per day for positions `pos` (columns = sleeves) and relative weights `a` (same shape, rows sum to 1)."""
    P = pos.fillna(0.0).values
    A = a.values
    prev = np.vstack([np.zeros((1, P.shape[1])), P[:-1]])
    np_now = (A * P).sum(axis=1)
    np_prev = (A * prev).sum(axis=1)
    units = np.abs(np_now - np_prev)
    if phase is not None:
        roll = phase.reindex(pos.index).astype(str).str.startswith(ROLL_PREFIX).values
        held = roll & (np_now != 0) & (np_prev != 0) & (np.sign(np_now) == np.sign(np_prev))
        units = units + np.where(held, np.minimum(np.abs(np_now), np.abs(np_prev)), 0.0)
    return pd.Series(units * (tc_bps / 10000.0 / 2.0), index=pos.index)


def netted(nets: dict[str, pd.Series], pos: dict[str, pd.Series], phase: pd.Series | None, tc_bps: float,
           a: pd.DataFrame | None = None) -> dict[str, pd.Series]:
    """Adjusted net series of one product's sleeves for a portfolio that holds them with relative weights `a`
    (DataFrame, index = any dates, columns = the sleeve names; None = equal weights). Returns {sleeve: adjusted net}."""
    names = [s for s in nets if not nets[s].empty]
    if len(names) < 2:
        return {s: nets[s] for s in nets}
    idx = nets[names[0]].index
    for s in names[1:]:
        assert nets[s].index.equals(idx), "sleeves of one product must share the product calendar"
    P = pd.DataFrame({s: pos[s].reindex(idx).fillna(0.0) for s in names}, index=idx)
    TC = sleeve_costs({s: pos[s] for s in names}, phase, tc_bps, idx)
    if a is None:
        A = pd.DataFrame(1.0 / len(names), index=idx, columns=names)
    else:
        A = a[names].reindex(idx, method="bfill")
        A = A.div(A.sum(axis=1), axis=0)                   # relative weights inside the product
        A = A.fillna(1.0 / len(names))                      # burn-in days without weights: the portfolio is undefined there anyway
    net_c = netted_cost(P, phase, A, tc_bps)
    per_c = (A * TC).sum(axis=1)
    roll = phase.reindex(idx).astype(str).str.startswith(ROLL_PREFIX) if phase is not None else pd.Series(False, index=idx)
    over = (net_c - per_c)[~roll.values]
    assert (over <= 1e-15).all(), f"netted cost above per-sleeve cost on a non-roll day: {over.max()}"
    k = (net_c / per_c).where(per_c > 0, 1.0).clip(upper=1.0)       # a roll day can, in rare mixed cases, net to more units; never charge more than per sleeve
    return {s: (nets[s] + (1.0 - k) * TC[s]) if s in names else nets[s] for s in nets}


def inverse_vol_weights(series: list[pd.Series], vol_window: int = 63) -> pd.DataFrame:
    """The weight schedule of engine.combine_returns(series, "inverse_vol"), columns 0..n-1 on the union index (NaN during burn-in)."""
    idx = series[0].index
    for s in series[1:]:
        idx = idx.union(s.index)
    rets = pd.concat([s.reindex(idx) for s in series], axis=1, ignore_index=True)
    vol = rets.rolling(vol_window, min_periods=vol_window).std(ddof=1).shift(1)
    inv = 1.0 / vol.replace(0.0, np.nan)
    return inv.div(inv.sum(axis=1, skipna=False), axis=0)


def combine_with_weights(series: list[pd.Series], w: pd.DataFrame) -> pd.Series:
    """engine.combine_returns(..., "inverse_vol") with a given weight schedule (same union index, same NaN rule)."""
    idx = w.index
    rets = pd.concat([s.reindex(idx) for s in series], axis=1, ignore_index=True)
    return (w * rets).sum(axis=1, skipna=False)


def apply_schedule(series_by_name: dict, W: pd.DataFrame) -> pd.Series:
    """The combine step of risk_parity.rolling_erc_combine / drp.rolling_drp_combine with a given weight schedule (same dropna(how="any") dates)."""
    names = list(W.columns)
    df = pd.concat([series_by_name[k] for k in names], axis=1, keys=names).dropna(how="any")
    assert df.index.equals(W.index), "weight schedule and series dates differ"
    return pd.Series((df.values * W.values.astype(float)).sum(axis=1), index=df.index)


def netted_strategy_portfolio(detail: dict, W: pd.DataFrame | None, tc_bps: float) -> dict:
    """Streamlit Portfolio tab: `detail` = {strategy label: {"nets": {product: net}, "pos": {product: pos}, "phase": {product: phase}}}, each strategy
    equal-weighted across its products (engine.combine_returns). W = strategy weights over time (columns = labels), None = equal.
    Returns {label: netted strategy series}, to be combined with the same W."""
    from engine import combine_returns
    labels = list(detail)
    prods = {}
    for lb in labels:
        for p in detail[lb]["nets"]:
            prods.setdefault(p, []).append(lb)
    adj = {lb: {} for lb in labels}
    for p, lbs in prods.items():
        idx = detail[lbs[0]]["nets"][p].index
        A = {}
        for lb in lbs:
            aw = pd.Series(1.0 / len(labels), index=idx) if W is None else W[lb].astype(float).reindex(idx, method="bfill")
            A[lb] = aw / len(detail[lb]["nets"])
        out = netted({lb: detail[lb]["nets"][p] for lb in lbs}, {lb: detail[lb]["pos"][p] for lb in lbs}, detail[lbs[0]]["phase"][p], tc_bps, pd.DataFrame(A, index=idx))
        for lb in lbs:
            adj[lb][p] = out[lb]
    return {lb: combine_returns([adj[lb][p] for p in detail[lb]["nets"]], "equal_weight") for lb in labels}
