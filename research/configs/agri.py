"""
research/configs/agri.py
===========================
Ex-ante config for the Agriculture asset class (Corn, Wheat, Oats, Rough
Rice, Soybean, Soybean Oil, Soybean Meal, Coffee, Cocoa, Orange Juice,
Cotton No.2, Feeder Cattle, Live Cattle, Lean Hogs). Built 2026-09-29,
mirroring research/configs/metals.py's structure -- same engine
(rolling_continuous.get_metal_rolling_f1 / ratio_continuous, both reused
unchanged, zero new roll-adjustment logic written for this asset class).

Data source: data/Prices_0924/ (2026-09-24 Bloomberg pull), NOT data/06-30/
like the other 4 asset classes -- this is a separate, newer data drop.
  - Prices: Agriculture_Futures_Updated.xlsx, simple single-header-row
    format, f1_col=1/f2_col=2/data_start_row=2 -- verified directly against
    the raw sheet layout, same convention as Metals/Energy/Precious (no
    NGL-style front-month skip).
  - Calendar: Agri_Rolling_Calendar.xlsx, a CONVERTED workbook (not the raw
    Prices_0924 drop) -- reshaped from Expiry_Calendars_Updated_2.xlsx's
    consolidated "Agriculture" sheet into the one-sheet-per-product schema
    scripts/rolling_continuous.py's load_metal_calendar() expects. See
    scripts/rolling_continuous.py's AGRI_CONFIG comment block and the
    project_agri_expiry_calendar_source_errors memory for the two source
    data errors found and handled: one bad Cocoa row dropped (contract J23,
    a Bloomberg ticker-lookup collision), Sugar No.11 excluded entirely
    (confirmed systemic date corruption). Sugar is NOT in this file's
    PRODUCTS list -- it has no working calendar sheet to build a
    continuous series from, not just a dashboard-display exclusion like
    Energy's Singapore Gasoil/Fuel Oil.

Product depth varies 6-12 tenors across this asset class (Oats/Rough
Rice/Cotton to F6, Corn/Wheat/Soybean-complex/livestock to F8, Coffee/
Cocoa to F10), unlike Metals' uniform F1-F27 -- there is no single
Carry tenor pair that's valid for every product here the way F1-F3/F1-F13
works for Metals. CARRY_TENOR_PAIRS is left EMPTY below, pending a
per-product-family liquidity/depth study (user's explicit decision,
2026-09-29: "we decide carry tenor pairs later on, leave that as
pending for now"). Momentum/Value parameters ARE locked already, since
those are asset-independent engine conventions (identical across all 4
existing asset classes, not re-derived per asset) -- see
feedback_risk_premia_shift_n1_locked memory.

Nothing here is hardcoded into the shared engine (research/engine.py,
regimes.py, stats.py, common_engine.py) -- this file is the ONLY place
Agri-specific values live, same discipline as every other asset class's
config.
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

from rolling_continuous import (AGRI_CALENDAR_FILE, AGRI_CONFIG,  # noqa: E402
                                 AGRI_FUTURES_FILE, get_metal_rolling_f1,
                                 reanchor_f1_continuous)
from ratio_continuous import get_metal_rolling_f1_ratio, reanchor_f1_continuous_ratio  # noqa: E402

ASSET_CLASS = "Agriculture"

PRODUCTS = ["Corn", "Wheat", "Oats", "RoughRice", "Soybean", "SoybeanOil",
            "SoybeanMeal", "Coffee", "Cocoa", "OrangeJuice", "Cotton",
            "FeederCattle", "LiveCattle", "LeanHogs"]
# Sugar No.11 deliberately absent -- see module docstring.

AGRI_CODES = {
    "Corn": "C", "Wheat": "W", "Oats": "O", "RoughRice": "RR",
    "Soybean": "S", "SoybeanOil": "BO", "SoybeanMeal": "SM",
    "Coffee": "KC", "Cocoa": "CC", "OrangeJuice": "JO", "Cotton": "CT",
    "FeederCattle": "FC", "LiveCattle": "LC", "LeanHogs": "LH",
}

SHEET_NAMES = {product: AGRI_CONFIG[code]["price_sheet"] for product, code in AGRI_CODES.items()}

CURVE_FILE = AGRI_FUTURES_FILE
CALENDAR_FILE = AGRI_CALENDAR_FILE

# Standardized analysis start (matches Metals/Energy/Precious's own 2026-07-23
# decision to use 2006 uniformly rather than each file's true earliest date --
# Agri's own data also starts 2005-01-03, same situation).
ANALYSIS_START = "2006-01-01"

# ── Ex-ante strategy parameters ─────────────────────────────────────────
# Momentum: 3-way MA-crossover composite, identical form to all 4 existing
# asset classes -- this is an asset-independent engine convention, not
# re-derived per asset (see feedback_risk_premia_shift_n1_locked memory).
MOMENTUM_PAIRS: tuple[tuple[int, int], ...] = ((1, 20), (5, 60), (20, 250))
MOMENTUM_SHIFT_N = 1

# Carry: PENDING -- see module docstring. Left empty rather than guessed;
# any code iterating this list (e.g. dashboard_portfolio_tab.py's Carry/
# CarryMom sleeve) will see zero pairs and should skip those sleeves for
# Agri, not silently compute against a wrong/borrowed tenor pair.
CARRY_TENOR_PAIRS: list[tuple[str, str]] = []
CARRY_ZSCORE_WINDOW = 252
CARRY_SHIFT_N = 1

# Carry-Momentum (V3): kept as its own separate strategy, same as every
# other asset class -- horizon is asset-independent, tenor pair still
# pending same as Carry above (CarryMom needs a (near, far) pair too).
CARRY_MOMENTUM_HORIZON = 20
CARRY_MOMENTUM_SHIFT_N = 1

# Value: F3 contract / 5yr lookback / +-10% threshold / shift_n=1 --
# identical to all 4 existing asset classes, asset-independent convention.
VALUE_CONTRACT = "F3"
VALUE_LOOKBACK_DAYS = 1260  # ~5yr trading days
VALUE_THRESHOLD = 0.10
VALUE_SHIFT_N = 1

# StatArb: not evaluated for Agri yet -- no liquidity/cointegration study
# has been run (unlike Metals/Precious, which were tested and found null).
# Left disabled rather than assumed; revisit only if explicitly asked.
STATARB_ENABLED = False
STATARB_PAIRS: list[tuple[str, str]] = []


def load_curve(product: str) -> pd.DataFrame:
    """Full F1..Fn raw price curve for one Agri product (needed for Carry/
    Value, which reference specific tenors beyond F1). Parses the "simple"
    single-header-row format (title row, then Date/F1/F2/.../Fn header,
    data from row 2) used by Agriculture_Futures_Updated.xlsx -- same
    format as Metals_Futures_Curve_Updated.xlsx."""
    if product not in SHEET_NAMES:
        raise ValueError(f"Unknown Agri product {product!r}; valid: {PRODUCTS}")
    raw = pd.read_excel(CURVE_FILE, sheet_name=SHEET_NAMES[product], header=None, skiprows=2)
    dates = pd.to_datetime(raw[0], errors="coerce")
    n_tenors = raw.shape[1] - 1
    cols = {f"F{t + 1}": pd.to_numeric(raw[t + 1], errors="coerce").values for t in range(n_tenors)}
    curve = pd.DataFrame(cols, index=dates.values)
    curve = curve[curve.index.notna()].sort_index()
    return curve.loc[ANALYSIS_START:]


def load_f1_series(product: str) -> pd.DataFrame:
    """F1_raw / F1_continuous / Phase for one Agri product, via the repo's
    own validated roll-adjustment builder -- NOT reimplemented here. Reanchors
    F1_continuous to the sliced window's first day per that function's own
    documented convention (cosmetic only, zero effect on PnL/Sharpe)."""
    if product not in AGRI_CODES:
        raise ValueError(f"Unknown Agri product {product!r}; valid: {PRODUCTS}")
    df = get_metal_rolling_f1(AGRI_CODES[product], futures_file=CURVE_FILE,
                               calendar_file=CALENDAR_FILE, config=AGRI_CONFIG, verbose=False)
    df = df.loc[ANALYSIS_START:]
    return reanchor_f1_continuous(df)


def load_f1_series_logret(product: str) -> pd.DataFrame:
    """F1_raw / F1_continuous_ratio / log_price / Phase for one Agri
    product -- the LOG-RETURN methodology series (research/ratio_continuous.py),
    used for the cross-asset research pipeline instead of load_f1_series()'s
    additively-adjusted F1_continuous (fine for dollar PnL within a single
    product, not for combining log returns across products/asset classes)."""
    if product not in AGRI_CODES:
        raise ValueError(f"Unknown Agri product {product!r}; valid: {PRODUCTS}")
    df = get_metal_rolling_f1_ratio(AGRI_CODES[product], futures_file=CURVE_FILE,
                                     calendar_file=CALENDAR_FILE, config=AGRI_CONFIG, verbose=False)
    df = df.loc[ANALYSIS_START:]
    df = reanchor_f1_continuous_ratio(df)
    price = df["F1_continuous_ratio"].where(df["F1_continuous_ratio"] > 0)
    df["log_price"] = np.log(price)
    return df
