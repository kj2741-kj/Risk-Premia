"""
research/configs/metals.py
===========================
Ex-ante locked config for the Metals asset class (Copper, Aluminium, Lead,
Zinc). Locked 2026-07-23 -- see project_risk_premia_research_framework memory
#13/#14 for the full reasoning behind every choice below.

Nothing here is hardcoded into the shared engine (research/engine.py,
regimes.py, stats.py) -- this file is the ONLY place Metals-specific values
live. Replicating to Precious/Energy/NGL means writing a new sibling config
file with that asset class's own products/tenors/statarb flag, not touching
engine.py or this file.

Data loading deliberately reuses the repo's own validated infra rather than
reimplementing it:
  - Curve (F1..F27 raw price levels, needed for Carry/Value): parser here for
    the "simple" single-header-row format (Date,F1,F2,...,F27, no Volume/OI).
  - F1_continuous (ratio-back-adjusted, roll-aware): scripts/rolling_continuous
    .get_metal_rolling_f1() -- the SAME production-grade roll builder the live
    metals_dashboard uses. Not reimplemented here, so Momentum/TC calculations
    match the live dashboard's own convention exactly rather than risking a
    subtly different roll-adjustment logic. Confirmed before reuse: this
    module has zero Streamlit dependency, safe to import into a pure batch
    script.

DATA SOURCE UPDATED 2026-07-24 (user's request): switched from the legacy
`data/Metals Futures Curve.csv` (multi-header Price/Volume/OpenInt format,
Copper LME stops 2025-12-31, rest stop ~2026-05-19) to the newer
`data/06-30/Metals_Futures_Curve_Updated.xlsx` (simple single-header format,
covers 2005-01-01 through 2026-06-30 -- more history AND more recent data).
rolling_continuous.py already had a ready-made METALS_CONFIG/
METALS_FUTURES_FILE/METALS_CALENDAR_FILE for exactly this file (paired with
the matching 2026-07-01-vintage calendar) -- reused directly rather than
building a new one. IMPORTANT: this new file has NO Volume/OpenInterest
columns, so the liquidity/volume-based Carry tenor evidence (F1 vs F3 volume
peak, F13 annual convention) from the 2026-07-23 screen on the OLD file
still stands as the locked basis for CARRY_TENOR_PAIRS below -- it is not
re-derivable from this file and does not need to be, only the underlying
PRICE data source changed, not that decision.
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

from rolling_continuous import (METALS_CALENDAR_FILE, METALS_CONFIG,  # noqa: E402
                                 METALS_FUTURES_FILE, get_metal_rolling_f1,
                                 reanchor_f1_continuous)
from ratio_continuous import get_metal_rolling_f1_ratio, reanchor_f1_continuous_ratio  # noqa: E402

ASSET_CLASS = "Metals"

PRODUCTS = ["Copper", "Aluminium", "Lead", "Zinc"]

METAL_CODES = {"Copper": "LP", "Aluminium": "LA", "Lead": "LL", "Zinc": "LX"}

SHEET_NAMES = {"Copper": "Copper LME", "Aluminium": "Aluminium LME",
               "Lead": "Lead LME", "Zinc": "Zinc LME"}

CURVE_FILE = METALS_FUTURES_FILE
CALENDAR_FILE = METALS_CALENDAR_FILE

# Standardized analysis start (user's decision 2026-07-23: use 2006 uniformly
# for Metals/Energy/Precious rather than each file's own true earliest date).
ANALYSIS_START = "2006-01-01"

# ── Ex-ante strategy parameters, LOCKED 2026-07-23 (framework memory #14) ──
# Momentum: 3-way MA-crossover composite (Bogorad's own convention -- average
# the sign of several lookback pairs rather than picking one).
MOMENTUM_PAIRS: tuple[tuple[int, int], ...] = ((1, 20), (5, 60), (20, 250))
MOMENTUM_SHIFT_N = 1

# Carry: TWO tenor pairs kept, both uniform across all 4 Metals products,
# locked from the liquidity/volume check (2026-07-23) -- F3 is the volume
# PEAK for every product, F13 is the annual/Bouchouev-Bogorad-convention tenor
# (weaker liquidity for Lead/Zinc there, disclosed not hidden).
CARRY_TENOR_PAIRS: list[tuple[str, str]] = [("F1", "F3"), ("F1", "F13")]
# V1(Level)+V2(Z-score) composite -- deliberately excludes V3, kept separate below.
CARRY_ZSCORE_WINDOW = 252
CARRY_SHIFT_N = 1

# Carry-Momentum (V3): kept as ITS OWN separate strategy, not folded into the
# Carry composite above -- it's a rate-of-change/momentum-on-carry construct,
# a different economic hypothesis from V1/V2's level-based signal.
CARRY_MOMENTUM_HORIZON = 20
CARRY_MOMENTUM_SHIFT_N = 1

# Value: existing dashboard anchor, unchanged.
VALUE_CONTRACT = "F8"
VALUE_LOOKBACK_DAYS = 1260  # ~5yr trading days
VALUE_THRESHOLD = 0.10
VALUE_SHIFT_N = 2

# StatArb: NOT used for Metals -- tested rigorously (4 specifications: raw
# levels full-sample, log-prices full-sample, raw-levels regime-split,
# macro-factor-adjusted regime-split), genuine null across all 6 pairs incl.
# Zinc-Lead (the strongest a priori story). See project_bogorad_ngl_methodology
# memory for the full result. May revisit for Energy/NGL later, not Metals.
STATARB_ENABLED = False
STATARB_PAIRS: list[tuple[str, str]] = []


def load_curve(product: str) -> pd.DataFrame:
    """Full F1..F27 raw price curve for one Metals product (needed for Carry/
    Value, which reference specific tenors beyond F1). Parses the "simple"
    single-header-row format (title row, then Date/F1/F2/.../F27 header,
    data from row 2) used by Metals_Futures_Curve_Updated.xlsx -- NOT the
    legacy multi-header Price/Volume/OpenInt format."""
    if product not in SHEET_NAMES:
        raise ValueError(f"Unknown Metals product {product!r}; valid: {PRODUCTS}")
    raw = pd.read_excel(CURVE_FILE, sheet_name=SHEET_NAMES[product], header=None, skiprows=2)
    dates = pd.to_datetime(raw[0], errors="coerce")
    n_tenors = raw.shape[1] - 1
    cols = {f"F{t + 1}": pd.to_numeric(raw[t + 1], errors="coerce").values for t in range(n_tenors)}
    curve = pd.DataFrame(cols, index=dates.values)
    curve = curve[curve.index.notna()].sort_index()
    return curve.loc[ANALYSIS_START:]


def load_f1_series(product: str) -> pd.DataFrame:
    """F1_raw / F1_continuous / Phase for one Metals product, via the repo's
    own validated roll-adjustment builder -- NOT reimplemented here. Reanchors
    F1_continuous to the sliced window's first day per that function's own
    documented convention (cosmetic only, zero effect on PnL/Sharpe -- see
    reanchor_f1_continuous's docstring)."""
    if product not in METAL_CODES:
        raise ValueError(f"Unknown Metals product {product!r}; valid: {PRODUCTS}")
    df = get_metal_rolling_f1(METAL_CODES[product], futures_file=CURVE_FILE,
                               calendar_file=CALENDAR_FILE, config=METALS_CONFIG, verbose=False)
    df = df.loc[ANALYSIS_START:]
    return reanchor_f1_continuous(df)


def load_f1_series_logret(product: str) -> pd.DataFrame:
    """F1_raw / F1_continuous_ratio / log_price / Phase for one Metals
    product -- the LOG-RETURN methodology series (research/ratio_continuous.py),
    used for the cross-asset research pipeline instead of load_f1_series()'s
    additively-adjusted F1_continuous (which is fine for dollar PnL within a
    single product, but not for combining log returns across products/asset
    classes -- see project_risk_premia_research_framework memory #16)."""
    if product not in METAL_CODES:
        raise ValueError(f"Unknown Metals product {product!r}; valid: {PRODUCTS}")
    df = get_metal_rolling_f1_ratio(METAL_CODES[product], futures_file=CURVE_FILE,
                                     calendar_file=CALENDAR_FILE, config=METALS_CONFIG, verbose=False)
    df = df.loc[ANALYSIS_START:]
    df = reanchor_f1_continuous_ratio(df)
    price = df["F1_continuous_ratio"].where(df["F1_continuous_ratio"] > 0)
    df["log_price"] = np.log(price)
    return df
