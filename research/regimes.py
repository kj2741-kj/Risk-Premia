"""
research/regimes.py
====================
Locked Part-3 macro regime scheme, dateable cross-asset-class events.

REVISED 2026-07-24 (user's decision): reporting now starts 2011-01-01 across
every asset class, dropping the pre-2011 regimes (the former Pre-GFC Bull
Run, GFC Crash, and Post-GFC QE Recovery windows) entirely. Reason: those
windows sit inside or overlap the burn-in period for the longest-lookback
signals (Value's 1260-day/630-min-period moving average in particular) -- for
Metals/Energy/Precious Metals, whose price history starts 2006-01, the Value
signal was empirically flat (non-trading) for ~96% of the old first window,
only going live in mid-2008; Momentum and Carry lost roughly their first
burn-in year too. By 2011, every signal in every asset class (including NGL,
whose own history starts 2009-08 -- see research/run_regime_table.py's
build_strategy_net_series for how per-product warm-up now uses each product's
own full history rather than the common-start-truncated one) has cleared its
longest burn-in window, so results reported from 2011 onward are on equal,
fully-warmed-up footing across all four asset classes -- see project memory
for the full reasoning. The first remaining regime's start was moved from
2011-10-01 to 2011-01-01 so it aligns exactly with the new reporting cutoff
instead of leaving a gap.

RENUMBERED 2026-07-24 (same session, user's follow-up): the four surviving
regimes are relabeled R1-R4 (were R4-R7) now that the dropped regimes are
gone -- starting the visible sequence at R4 read as an orphaned/confusing
label with nothing before it. R1 here refers to Supercycle Unwind, NOT the
former Pre-GFC Bull Run window of the same code in the pre-revision scheme;
don't conflate the two if reading old notes/commits that predate this rename.

Do not add/remove/reword regimes here without re-running every regime-split
test that already depends on this list (run_regime_table.py, statarb.py,
stats.py's regime_persistence_screen).
"""

from __future__ import annotations

import pandas as pd

REGIMES: list[tuple[str, str, str]] = [
    ("R1_Supercycle_Unwind",     "2011-01-01", "2015-12-31"),
    ("R2_Recovery_Stabilization","2016-01-01", "2019-12-31"),
    ("R3_COVID_Shock",           "2020-01-01", "2021-12-31"),
    ("R4_PostCOVID_RussiaUkr",   "2022-01-01", "2026-12-31"),
]

# Reporting start for the "Full sample" summary, uniform across every asset
# class -- see module docstring for why 2011 rather than each asset's own
# (much earlier, burn-in-affected) data start.
REPORT_START = "2011-01-01"


def slice_regime(df: pd.DataFrame | pd.Series, regime_name: str) -> pd.DataFrame | pd.Series:
    """Slice a date-indexed DataFrame/Series to one locked regime's window."""
    lookup = {name: (start, end) for name, start, end in REGIMES}
    if regime_name not in lookup:
        raise ValueError(f"Unknown regime {regime_name!r}; valid: {list(lookup)}")
    start, end = lookup[regime_name]
    return df.loc[start:end]


def iter_regimes(df: pd.DataFrame | pd.Series):
    """Yield (regime_name, start, end, sliced_data) for every locked regime,
    skipping regimes with fewer than 30 observations in this particular df."""
    for name, start, end in REGIMES:
        sub = df.loc[start:end]
        if len(sub) < 30:
            continue
        yield name, start, end, sub
