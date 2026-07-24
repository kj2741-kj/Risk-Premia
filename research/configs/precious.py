"""
research/configs/precious.py
==============================
Ex-ante locked config for the Precious Metals asset class (Gold, Silver,
Copper-COMEX, Platinum, Palladium). Built 2026-07-24, mirroring
research/configs/metals.py's structure and reusing the same shared engine
(research/engine.py, regimes.py, stats.py) -- nothing asset-specific lives
outside this file.

Signal form and parameter CONVENTIONS are identical to Metals (per user's
explicit "ex-ante is same as discussed" instruction) EXCEPT the Carry tenor,
which was re-derived from real data, not assumed:
  - Momentum: 3-way MA-crossover composite, same (1,20)/(5,60)/(20,250) pairs.
  - Carry: V1(Level)+V2(Z-score) composite, tenor pair F1-F2 ONLY (see below).
  - Carry-Momentum: same horizon=20, kept separate from the Carry composite.
  - Value: same F8 contract / 5yr lookback / +-10% threshold.
  - StatArb: NOT used -- already tested and excluded for Precious Metals
    (genuine null across all 10 pairs incl. Gold-Silver/Platinum-Palladium,
    see project_bogorad_ngl_methodology memory).

CARRY TENOR -- CORRECTED 2026-07-24 using REAL volume data (not the earlier
quote-availability proxy, which overstated liquidity by measuring "was a
price posted" rather than "did anyone trade"). Real volume comes from the
LEGACY `data/Metals Futures Curve.csv` file's CME/COMEX sheets (Copper CME,
GOLD CME, Silver CME, Platinum CME, Palladium CME) -- used STRICTLY for this
liquidity determination, not as a price source (prices still come from the
updated data/06-30 file via CURVE_FILE below). Findings:
  - Gold/Silver/Copper-COMEX are genuinely liquid (>=90% days actually
    traded) through F5-F7.
  - Platinum and Palladium are ONLY genuinely liquid through F1-F2 -- their
    F3 already fails on real volume (87.0% / 68.5% days traded, well below
    the quote-availability proxy's 98%/99.6% "quoted" reading for the same
    tenor -- a real, material gap between "quoted" and "traded").
  - F13 fails for ALL FIVE products on real volume, not just Platinum/
    Palladium: Gold 17.8%, Silver 11.1%, Copper-COMEX 1.3% days traded --
    decisively not viable anywhere in this asset class, unlike the
    quote-availability read which made it look merely "weak."
User's decision, given this: **F1-F2 as the single universal Carry tenor
pair, F1-F13 dropped entirely for Precious Metals** -- the only pair with
genuine real-volume support across all 5 products, rather than forcing a
longer tenor nothing here actually trades.
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

from rolling_continuous import (PRECIOUS_CALENDAR_FILE, PRECIOUS_CONFIG,  # noqa: E402
                                 PRECIOUS_FUTURES_FILE, get_metal_rolling_f1,
                                 reanchor_f1_continuous)
from ratio_continuous import get_metal_rolling_f1_ratio, reanchor_f1_continuous_ratio  # noqa: E402

ASSET_CLASS = "Precious Metals"

PRODUCTS = ["Gold", "Silver", "Copper_COMEX", "Platinum", "Palladium"]

METAL_CODES = {"Gold": "GC", "Silver": "SI", "Copper_COMEX": "HG", "Platinum": "PL", "Palladium": "PA"}

SHEET_NAMES = {"Gold": "Gold COMEX", "Silver": "Silver COMEX", "Copper_COMEX": "Copper CME (HG)",
               "Platinum": "Platinum NYMEX", "Palladium": "Palladium NYMEX"}

CURVE_FILE = PRECIOUS_FUTURES_FILE
CALENDAR_FILE = PRECIOUS_CALENDAR_FILE
METALS_CONFIG = PRECIOUS_CONFIG  # kept under this name so _rebuild_ratio_series-style callers stay uniform

# Standardized analysis start, same convention as Metals (2006-01-01) -- the
# actual Precious file goes back to 2005, not backfilled per the user's
# earlier decision to standardize at 2006 across Metals/Energy/Precious.
ANALYSIS_START = "2006-01-01"

# ── Ex-ante strategy parameters -- IDENTICAL to Metals (locked 2026-07-23/24) ──
MOMENTUM_PAIRS: tuple[tuple[int, int], ...] = ((1, 20), (5, 60), (20, 250))
MOMENTUM_SHIFT_N = 1

CARRY_TENOR_PAIRS: list[tuple[str, str]] = [("F1", "F2")]
CARRY_ZSCORE_WINDOW = 252
CARRY_SHIFT_N = 1

CARRY_MOMENTUM_HORIZON = 20
CARRY_MOMENTUM_SHIFT_N = 1

VALUE_CONTRACT = "F8"
VALUE_LOOKBACK_DAYS = 1260
VALUE_THRESHOLD = 0.10
VALUE_SHIFT_N = 2

# StatArb: NOT used -- tested rigorously (full 10-pair grid, incl.
# Gold-Silver and Platinum-Palladium), genuine null. See
# project_bogorad_ngl_methodology memory.
STATARB_ENABLED = False
STATARB_PAIRS: list[tuple[str, str]] = []


def load_curve(product: str) -> pd.DataFrame:
    """Full F1..Fn raw price curve for one Precious Metals product. Simple
    single-header-row format (same as the updated Metals file): title row,
    then Date/F1/F2/... header, data from row 2, no Volume/OpenInt columns."""
    if product not in SHEET_NAMES:
        raise ValueError(f"Unknown Precious Metals product {product!r}; valid: {PRODUCTS}")
    raw = pd.read_excel(CURVE_FILE, sheet_name=SHEET_NAMES[product], header=None, skiprows=2)
    dates = pd.to_datetime(raw[0], errors="coerce")
    n_tenors = raw.shape[1] - 1
    cols = {f"F{t + 1}": pd.to_numeric(raw[t + 1], errors="coerce").values for t in range(n_tenors)}
    curve = pd.DataFrame(cols, index=dates.values)
    curve = curve[curve.index.notna()].sort_index()
    return curve.loc[ANALYSIS_START:]


def load_f1_series(product: str) -> pd.DataFrame:
    """F1_raw / F1_continuous / Phase, via the repo's validated roll-adjustment
    builder (dollar-PnL / additive convention) -- not used by the log-return
    research pipeline, kept for parity with metals.py."""
    if product not in METAL_CODES:
        raise ValueError(f"Unknown Precious Metals product {product!r}; valid: {PRODUCTS}")
    df = get_metal_rolling_f1(METAL_CODES[product], futures_file=CURVE_FILE,
                               calendar_file=CALENDAR_FILE, config=PRECIOUS_CONFIG, verbose=False)
    df = df.loc[ANALYSIS_START:]
    return reanchor_f1_continuous(df)


def load_f1_series_logret(product: str) -> pd.DataFrame:
    """F1_raw / F1_continuous_ratio / log_price / Phase -- the log-return
    methodology series used by the research pipeline (research/engine.py's
    log_return_* functions)."""
    if product not in METAL_CODES:
        raise ValueError(f"Unknown Precious Metals product {product!r}; valid: {PRODUCTS}")
    df = get_metal_rolling_f1_ratio(METAL_CODES[product], futures_file=CURVE_FILE,
                                     calendar_file=CALENDAR_FILE, config=PRECIOUS_CONFIG, verbose=False)
    df = df.loc[ANALYSIS_START:]
    df = reanchor_f1_continuous_ratio(df)
    price = df["F1_continuous_ratio"].where(df["F1_continuous_ratio"] > 0)
    df["log_price"] = np.log(price)
    return df
