"""
research/regimes.py
====================
Locked Part-3 macro regime scheme (7 regimes, dateable cross-asset-class
events, 2006-present; NGL's own data starts 2009-08 so it has no usable
history for R1/R2/most of R3 -- see NGL_COMMON_WINDOW_START below).

Locked 2026-07-23. Do not add/remove/reword regimes here without re-running
every regime-split test that already depends on this list.
"""

from __future__ import annotations

import pandas as pd

REGIMES: list[tuple[str, str, str]] = [
    ("R1_PreGFC_Bull_Run",       "2006-01-03", "2008-08-31"),
    ("R2_GFC_Crash",             "2008-09-01", "2009-03-31"),  # short, ~125 trading days -- treat any Sharpe here as lower-confidence
    ("R3_PostGFC_QE_Recovery",   "2009-04-01", "2011-09-30"),
    ("R4_Supercycle_Unwind",     "2011-10-01", "2015-12-31"),
    ("R5_Recovery_Stabilization","2016-01-01", "2019-12-31"),
    ("R6_COVID_Shock",           "2020-01-01", "2021-12-31"),
    ("R7_PostCOVID_RussiaUkr",   "2022-01-01", "2026-12-31"),
]

# NGL's actual data start (earliest product, Propane, 2009-08-17) -- falls inside R3.
# Any cross-asset comparison that includes NGL should be restricted to this common
# window onward, not the full 2006 window (see project_risk_premia_research_framework
# memory #11 for the two-layer own-history-vs-common-window handling).
NGL_COMMON_WINDOW_START = "2009-10-01"


def slice_regime(df: pd.DataFrame | pd.Series, regime_name: str) -> pd.DataFrame | pd.Series:
    """Slice a date-indexed DataFrame/Series to one locked regime's window."""
    lookup = {name: (start, end) for name, start, end in REGIMES}
    if regime_name not in lookup:
        raise ValueError(f"Unknown regime {regime_name!r}; valid: {list(lookup)}")
    start, end = lookup[regime_name]
    return df.loc[start:end]


def iter_regimes(df: pd.DataFrame | pd.Series):
    """Yield (regime_name, start, end, sliced_data) for every locked regime,
    skipping regimes with fewer than 30 observations in this particular df
    (e.g. NGL products sliced against R1/R2, which have zero data there)."""
    for name, start, end in REGIMES:
        sub = df.loc[start:end]
        if len(sub) < 30:
            continue
        yield name, start, end, sub
