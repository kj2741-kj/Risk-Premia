"""
research/stats.py
==================
Statistical rigor utilities shared across every asset class's research
pipeline: Benjamini-Hochberg FDR correction and Engle-Granger cointegration
screening (both directions, conservative p-value, optional regime-persistence
check). Refactored from the ad-hoc scripts run for the Metals and Precious
Metals stat-arb screens (2026-07-23) into reusable functions so the next
asset class doesn't re-derive this from scratch.
"""

from __future__ import annotations

import itertools

import pandas as pd
from statsmodels.tsa.stattools import coint

from regimes import REGIMES


def bh_fdr(pvals: dict[str, float], q: float = 0.10) -> set[str]:
    """Benjamini-Hochberg FDR correction. Returns the set of labels that survive
    at the given false-discovery-rate level q (default 10%, standard for
    exploratory finance research). Does NOT use a flat per-test cutoff like
    Bonferroni -- the critical value adapts per rank, (k/n)*q."""
    ranked = sorted(pvals.items(), key=lambda kv: kv[1])
    n = len(ranked)
    max_k = 0
    for k, (_, p) in enumerate(ranked, start=1):
        if p <= (k / n) * q:
            max_k = k
    return {ranked[i][0] for i in range(max_k)}


def engle_granger_conservative(series_a: pd.Series, series_b: pd.Series) -> float:
    """Runs Engle-Granger cointegration both directions (a~b and b~a) and
    returns the CONSERVATIVE (max, i.e. worse) p-value of the two -- cointegration
    can be mildly asymmetric depending on regression direction in finite samples,
    taking the max avoids over-claiming from a favorable direction."""
    _, p1, _ = coint(series_a, series_b)
    _, p2, _ = coint(series_b, series_a)
    return max(p1, p2)


def pairwise_cointegration_screen(price_df: pd.DataFrame, q: float = 0.10) -> dict[str, float]:
    """Full-sample Engle-Granger + BH-FDR screen across every pair of columns
    in price_df (price LEVELS, not returns/log-diffs -- cointegration is a
    statement about the levels' relationship). Returns {pair_label: conservative_p}
    for ALL pairs tested (not just survivors) -- call bh_fdr() on the result to
    get the survivor set."""
    products = list(price_df.columns)
    pvals = {}
    for a, b in itertools.combinations(products, 2):
        pvals[f"{a}-{b}"] = engle_granger_conservative(price_df[a], price_df[b])
    return pvals


def regime_persistence_screen(price_df: pd.DataFrame, q: float = 0.10) -> dict[str, list[str]]:
    """Runs pairwise_cointegration_screen + bh_fdr WITHIN each locked regime
    separately (not just full-sample), matching Bogorad's own selection
    criterion: "only pairs exhibiting persistent cointegration across multiple
    regimes are selected, filtering out transient relationships." Returns
    {pair_label: [list of regime names where it survived FDR]} -- a pair with
    only one regime in its list failed the persistence bar, per the Metals and
    Precious Metals screens already run (2026-07-23), which both came back
    with at most one surviving regime per pair -- not persistent, treated as a
    genuine null result for those asset classes.
    """
    survivorship: dict[str, list[str]] = {f"{a}-{b}": [] for a, b in itertools.combinations(price_df.columns, 2)}
    for name, start, end in REGIMES:
        sub = price_df.loc[start:end]
        if len(sub) < 30:
            continue
        pvals = pairwise_cointegration_screen(sub, q=q)
        survivors = bh_fdr(pvals, q=q)
        for pair in survivors:
            survivorship[pair].append(name)
    return survivorship
