"""Carry and Carry-Momentum combined by SUMMING the pair signals' underlying values before taking the sign. DEFAULT for the Final dashboard pipeline since 2026-10-13
(scripts/final_dashboard/compute_products.py, run_regime_table.py, cross_asset_engine.py and the Streamlit portfolio tab; no switch: the earlier sign-vote of engine.combine_positions, flat whenever the pairs disagreed, is in Git history and ENGINE_CHANGELOG).
The other functions in this file (standardised, per-month, no-z-score, z-score-difference) are the sandbox alternatives tested on 2026-10-12/13 and not adopted.

Carry V2: for each tenor pair the z-score of the carry slope (near - far) / near against its trailing `window` observations (the same z-score as
engine.raw_signal_carry_v2, WITHOUT taking its sign); the pairs' z-scores are summed and the sign of the sum is the signal, so the position is flat only if
the sum is exactly zero (no flat day because the pairs point in opposite directions).
Carry-Momentum V3: for each pair the change of the carry slope over `horizon` observations (engine.raw_signal_carrymom without its sign); summed across pairs
(raw slope changes, not standardised) and signed.
Missing values: if any pair's value is missing on a day (warm-up, a missing tenor price) the sum is missing and the signal of the last available day is carried
forward; before any signal exists the position is flat. The execution lag is applied afterwards, once, by the caller (engine.exec_shift)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import _carry_base, combine_positions, raw_signal_carry_v1


def combined_carry_signal(curve: pd.DataFrame, pairs: list, window: int, variants: tuple, index: pd.Index):
    """Pre-shift Carry signal across tenor `pairs` for one product (the rule used everywhere since 2026-10-13): V2 = sign of the SUM of the pairs' z-scores. If "V1" is also in
    `variants`, the V1 slope signs form one sign-vote group and the two groups are averaged with equal weight (V1 is optional and off by default). Returns (signal, number of
    pairs with data, {pair: has data})."""
    v1 = [raw_signal_carry_v1(curve, n, f) for n, f in pairs] if "V1" in variants else []
    zs = [carry_z(curve, n, f, window) for n, f in pairs] if "V2" in variants else []
    has = {pair: (bool(v1) and not v1[i].empty) or (bool(zs) and not zs[i].empty) for i, pair in enumerate(pairs)}
    v1, zs = [s for s in v1 if not s.empty], [z for z in zs if not z.empty]
    groups = []
    if v1:
        groups.append(v1[0] if len(v1) == 1 else combine_positions(v1, "equal_weight"))
    if zs:
        groups.append(summed_signal(zs, index))
    if not groups:
        return pd.Series(dtype=float), 0, has
    return (groups[0] if len(groups) == 1 else combine_positions(groups, "equal_weight")), max(len(v1), len(zs)), has


def combined_carrymom_signal(curve: pd.DataFrame, pairs: list, horizon: int, index: pd.Index):
    """Pre-shift Carry-Momentum signal across tenor `pairs` for one product: sign of the SUM of the pairs' raw `horizon`-observation slope changes. Returns (signal, number of pairs with data)."""
    parts = [p for p in (carry_slope_change(curve, n, f, horizon) for n, f in pairs) if not p.empty]
    if not parts:
        return pd.Series(dtype=float), 0
    return summed_signal(parts, index), len(parts)


def carry_z(curve: pd.DataFrame, near: str, far: str, window: int = 252) -> pd.Series:
    base = _carry_base(curve, near, far)
    if base.empty:
        return pd.Series(dtype=float)
    z = (base - base.rolling(window).mean()) / base.rolling(window).std()
    return z.replace([np.inf, -np.inf], np.nan)


def carry_slope_change(curve: pd.DataFrame, near: str, far: str, horizon: int = 20) -> pd.Series:
    base = _carry_base(curve, near, far)
    if base.empty:
        return pd.Series(dtype=float)
    return base - base.shift(horizon)


def carry_slope_change_std(curve: pd.DataFrame, near: str, far: str, horizon: int = 20, window: int = 252) -> pd.Series:
    """Standardised variant: the `horizon`-observation change of the carry slope divided by the standard deviation of that change over its trailing `window`
    observations (no demeaning, so the sign of the change is kept), so that pairs with different slope scales count comparably when summed."""
    ch = carry_slope_change(curve, near, far, horizon)
    if ch.empty:
        return ch
    return (ch / ch.rolling(window).std()).replace([np.inf, -np.inf], np.nan)


def carry_pm_change(curve: pd.DataFrame, near: str, far: str, months: pd.Series, horizon: int = 20) -> pd.Series:
    """Per-month spread variant: spread = (near price - far price) / months between the two legs on that date (plain price difference, see research/contract_months.py);
    the signal input is its `horizon`-observation change."""
    idx = curve[near].dropna().index.intersection(curve[far].dropna().index)
    sp = (curve[near].reindex(idx) - curve[far].reindex(idx)) / months.reindex(idx)
    return (sp - sp.shift(horizon)).replace([np.inf, -np.inf], np.nan)


def carry_slope(curve: pd.DataFrame, near: str, far: str) -> pd.Series:
    """Raw relative carry slope (near - far) / near, no z-score (research variant: Carry as the sign of the SUM of the pairs' raw slopes)."""
    return _carry_base(curve, near, far)


def carry_z_diff(curve: pd.DataFrame, near: str, far: str, window: int = 252, horizon: int = 20) -> pd.Series:
    """Carry-Momentum on z-scores: the Carry V2 z-score today minus the same z-score `horizon` observations earlier (research variant); summed across pairs by summed_signal."""
    z = carry_z(curve, near, far, window)
    if z.empty:
        return z
    return z - z.shift(horizon)


def summed_signal(parts: list[pd.Series], index: pd.Index) -> pd.Series:
    """Sign of the sum of `parts` (NaN if any part is missing), reindexed to the price `index`, last available signal carried forward; NaN only before the first signal."""
    parts = [s for s in parts if not s.empty]
    if not parts:
        return pd.Series(np.nan, index=index)
    sig = np.sign(pd.concat(parts, axis=1).sum(axis=1, skipna=False).where(pd.concat(parts, axis=1).notna().all(axis=1)))
    return sig.reindex(index.union(sig.index)).ffill().reindex(index)
