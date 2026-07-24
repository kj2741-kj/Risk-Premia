"""
research/configs/ngl.py
=========================
Ex-ante locked config for the NGL asset class (Ethane, Propane, Butane,
Isobutane, Ethylene, Propylene). Built 2026-07-24, mirroring
research/configs/metals.py / precious.py / energy.py's structure.

Signal form and most parameters are identical to the other asset classes:
  - Momentum: 3-way MA-crossover composite, (1,20)/(5,60)/(20,250).
  - Carry: V1(Level)+V2(Z-score) composite, SINGLE tenor pair F4-F15 (per
    user's explicit choice: NGL keeps Bogorad's own convention rather than
    the Metals-style two-tier structure used for Energy). Verified via
    quote-availability (this file has no Volume column): all 6 products are
    well-quoted through F15 (worst case Propylene, 79.6%), supporting F4-F15
    for the whole product set. Note: this check only confirms a price EXISTS
    at each tenor, not whether it is genuinely fresh -- it cannot validate or
    contradict Bogorad's own stated reason for starting at F4 (NGL front-
    month prices are often stale or index-settled), which is taken on his
    own authority as a domain judgment, not re-derived here.
  - Carry-Momentum: same horizon=20, same F4-F15 tenor, kept separate from
    the Carry composite.
  - Value: same F8 contract / 5yr lookback / +-10% threshold.

NGL's own front-month convention (established elsewhere in this project,
e.g. ngl_dashboard/app.py and scripts/generate_tradebooks.py): the sheet's
literal F1 column is considered too stale/index-settled to trade, so
NGL_CONFIG's f1_col/f2_col already point at the sheet's F2/F3 columns for
the CONTINUOUS ROLL-ADJUSTED series (used for Momentum and PnL). This file's
load_curve() deliberately does NOT apply that same shift -- Carry/Value
reference specific curve tenors directly (F4, F15, F8), and Bogorad's own
F4 starting point is already his stated answer to the same staleness
concern, so stacking an additional shift on top of his own choice would be
an unjustified double-adjustment, not a more faithful replication.

STATARB: shared 8-spread sleeve defined in research/configs/energy.py
(explicitly cross-asset-class in Bogorad's own design) -- not duplicated
here, this module just supplies its own products' curves when energy.py's
STATARB_PAIRS references an ("ngl", product, tenor) leg.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_RESEARCH_DIR = os.path.dirname(_THIS_DIR)
_REPO_ROOT = os.path.dirname(_RESEARCH_DIR)
_SCRIPTS_DIR = os.path.join(_REPO_ROOT, "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from rolling_continuous import (NGL_CALENDAR_FILE, NGL_CONFIG, NGL_FUTURES_FILE,  # noqa: E402
                                 get_metal_rolling_f1, reanchor_f1_continuous)
from ratio_continuous import get_metal_rolling_f1_ratio, reanchor_f1_continuous_ratio  # noqa: E402

ASSET_CLASS = "NGL"

PRODUCTS = ["Ethane", "Propane", "Butane", "Isobutane", "Ethylene", "Propylene"]

METAL_CODES = {"Ethane": "CAP", "Propane": "BAP", "Butane": "DAE",
               "Isobutane": "IBD", "Ethylene": "PCW", "Propylene": "PGP"}

SHEET_NAMES = {"Ethane": "Ethane Argus", "Propane": "Propane Argus", "Butane": "Butane Argus",
               "Isobutane": "Isobutane Argus", "Ethylene": "Ethylene Argus", "Propylene": "Propylene Argus"}

CURVE_FILE = NGL_FUTURES_FILE
CALENDAR_FILE = NGL_CALENDAR_FILE
METALS_CONFIG = NGL_CONFIG  # kept under this name for uniformity with the other config modules

ANALYSIS_START = "2009-08-01"  # NGL's own actual data start (per user's earlier decision, not backfilled)

# ── Ex-ante strategy parameters ──
MOMENTUM_PAIRS: tuple[tuple[int, int], ...] = ((1, 20), (5, 60), (20, 250))
MOMENTUM_SHIFT_N = 1

# Single tenor pair, Bogorad's own F4-F15 convention (not the Metals-style two-tier).
CARRY_TENOR_PAIRS: list[tuple[str, str]] = [("F4", "F15")]
CARRY_ZSCORE_WINDOW = 252
CARRY_SHIFT_N = 1

CARRY_MOMENTUM_HORIZON = 20
CARRY_MOMENTUM_SHIFT_N = 1

VALUE_CONTRACT = "F8"
VALUE_LOOKBACK_DAYS = 1260
VALUE_THRESHOLD = 0.10
VALUE_SHIFT_N = 2

STATARB_ENABLED = True  # shared sleeve, see research/configs/energy.py::STATARB_PAIRS


def load_curve(product: str) -> pd.DataFrame:
    """Full F1..Fn raw price curve for one NGL product, sheet's literal
    column labels, NOT shifted for the front-month staleness convention
    (see module docstring)."""
    if product not in SHEET_NAMES:
        raise ValueError(f"Unknown NGL product {product!r}; valid: {PRODUCTS}")
    raw = pd.read_excel(CURVE_FILE, sheet_name=SHEET_NAMES[product], header=None, skiprows=2)
    dates = pd.to_datetime(raw[0], errors="coerce")
    n_tenors = raw.shape[1] - 1
    cols = {f"F{t + 1}": pd.to_numeric(raw[t + 1], errors="coerce").values for t in range(n_tenors)}
    curve = pd.DataFrame(cols, index=dates.values)
    curve = curve[curve.index.notna()].sort_index()
    return curve.loc[ANALYSIS_START:]


def load_f1_series(product: str) -> pd.DataFrame:
    """F1_raw / F1_continuous / Phase via the repo's validated roll-adjustment
    builder -- NGL_CONFIG's f1_col=2/f2_col=3 already applies the front-month
    shift here (dollar-PnL / additive convention, kept for parity)."""
    if product not in METAL_CODES:
        raise ValueError(f"Unknown NGL product {product!r}; valid: {PRODUCTS}")
    df = get_metal_rolling_f1(METAL_CODES[product], futures_file=CURVE_FILE,
                               calendar_file=CALENDAR_FILE, config=NGL_CONFIG, verbose=False)
    df = df.loc[ANALYSIS_START:]
    return reanchor_f1_continuous(df)


def load_f1_series_logret(product: str) -> pd.DataFrame:
    """F1_raw / F1_continuous_ratio / log_price / Phase, the log-return
    methodology series used by the research pipeline."""
    if product not in METAL_CODES:
        raise ValueError(f"Unknown NGL product {product!r}; valid: {PRODUCTS}")
    df = get_metal_rolling_f1_ratio(METAL_CODES[product], futures_file=CURVE_FILE,
                                     calendar_file=CALENDAR_FILE, config=NGL_CONFIG, verbose=False)
    df = df.loc[ANALYSIS_START:]
    df = reanchor_f1_continuous_ratio(df)
    price = df["F1_continuous_ratio"].where(df["F1_continuous_ratio"] > 0)
    df["log_price"] = np.log(price)
    return df
