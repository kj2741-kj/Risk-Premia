"""
research/configs/agri.py
===========================
Agriculture bucket, REDEFINED 2026-11-10: Corn, Wheat (CBOT SRW), Soybean, Live Cattle. The old six-product Agriculture (Corn, Wheat, Soybean, Soybean Oil, Coffee, Sugar, decided 2026-10-11)
was split in two: Coffee and Sugar moved to the Softs bucket (research/configs/softs.py: Sugar, Cocoa, Coffee, Cotton) and Soybean Oil was dropped; Live Cattle (Agriculture) and Cocoa and
Cotton (Softs) are new. This module also holds the loaders of all eight products (AGRI_CODES), which softs.py reuses, so the two buckets cannot drift apart.

DATA (2026-11-10 Bloomberg drop, scripts/new_products_1110.py): Agri_Softs_Futures_1110.xlsx + Agri_Softs_Calendar_1110.xlsx in the price folder (RP_PRICES_DIR). For the five products that
existed before (Corn, Wheat, Soybean, Coffee, Sugar) the prices equal the old Agriculture_Futures_Updated.xlsx on every overlapping cell (except the 2026-10-29 row, an intraday print in the old file,
and Soybean F18) and the calendar's last trade dates equal the validated Bloomberg-matched calendar on every overlapping contract, so their rolling series are unchanged (checked, see ENGINE_CHANGELOG).
The drop is deeper (Corn F13, Wheat F14, Soybean F18, Cotton F15 instead of F6-F8 history) and adds Live Cattle, Cocoa and Cotton on a clean calendar.

ROLL: unchanged engine, 5th trading day of the month in which each contract's last trade date falls (ROLL_RULE below); the day after the last trade date is the bridge. Verified for every product
that Bloomberg's generic F1 switches contract on exactly the day after the calendar's last trade date (aggregate shift test, ENGINE_CHANGELOG 2026-11-10).

CARRY TENOR PAIRS (user decision 2026-11-10): F1-F2 short pair for every product; long pair F1-F6 for Corn, Wheat, Sugar, Cocoa, Coffee and Cotton, F1-F7 for Live Cattle and Soybean
(CARRY_LONG_FAR_BY_PRODUCT). Spans in months: F1-F2 is 2-3 (Corn, Wheat, Cocoa, Coffee, Cotton), 1-2 (Soybean), 2 (Live Cattle), 2-5 (Sugar); F1-F6 is exactly 12 for Corn, Wheat, Cocoa, Coffee, Cotton
and 14-17 for Sugar; F1-F7 is exactly 12 for Live Cattle and 10-11 for Soybean (shown to and accepted by the user together with the volumes of each leg).
Below is the older text of the 14-product build, kept for history.

Original docstring (2026-09-29, 14 products):
Ex-ante config for the Agriculture asset class, mirroring research/configs/metals.py's structure -- same engine
(rolling_continuous.get_metal_rolling_f1 / ratio_continuous, both reused unchanged, zero new roll-adjustment logic written for this asset class).
Momentum/Value parameters are asset-independent engine conventions (identical across all asset classes, see feedback_risk_premia_shift_n1_locked).
Nothing here is hardcoded into the shared engine (research/engine.py, regimes.py, stats.py, common_engine.py): this file is the ONLY place Agri-specific values live.
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

from rolling_continuous import (apply_data_fixes, AGRI1110_CALENDAR_FILE, AGRI1110_CONFIG as AGRI_CONFIG,  # noqa: E402
                                 AGRI1110_FUTURES_FILE, get_metal_rolling_f1,
                                 reanchor_f1_continuous)
from ratio_continuous import get_metal_rolling_f1_ratio, reanchor_f1_continuous_ratio  # noqa: E402

ASSET_CLASS = "Agriculture"

# Four products in the Agriculture bucket (user's decision 2026-11-10). AGRI_CODES also lists the Softs products: softs.py imports them from here.
PRODUCTS = ["Corn", "Wheat", "Soybean", "LiveCattle"]
SOFTS_PRODUCTS = ["Sugar", "Cocoa", "Coffee", "Cotton"]

AGRI_CODES = {
    "Corn": "C", "Wheat": "W", "Soybean": "S", "LiveCattle": "LC",
    "Sugar": "SB", "Cocoa": "CC", "Coffee": "KC", "Cotton": "CT",
}

SHEET_NAMES = {product: AGRI_CONFIG[code]["price_sheet"] for product, code in AGRI_CODES.items()}

CURVE_FILE = AGRI1110_FUTURES_FILE
CALENDAR_FILE = AGRI1110_CALENDAR_FILE

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

# Carry: F1-F2 is the short pair of every product (CARRY_TENOR_PAIRS, also what the Streamlit Carry tab starts on); each product's long pair comes from carry_pairs() below
# (user decision 2026-11-10). The Streamlit Carry and Portfolio tabs let the user pick any other (near, far) pair.
CARRY_TENOR_PAIRS: list[tuple[str, str]] = [("F1", "F2")]
CARRY_ZSCORE_WINDOW = 252
CARRY_SHIFT_N = 1

# ── Roll rule (2026-10-11) ───────────────────────────────────────────────────
# Every research number (run_regime_table.py, cross_asset_engine.py, Final_Research_Dashboard.html) rolls on the 5th trading day
# of the month in which each contract's last trade date falls, not 5 trading days before it. See scripts/rolling_continuous.py
# (ROLL_RULES). The Streamlit apps keep their own "Rolling Logic" selector and are unaffected.
ROLL_RULE = "expiry_month_nth_td"
ROLL_N = 5

# Two tenor pairs per product (2026-10-11, user's decision): short F1-F2 plus a long pair about 12 months out. The far leg depends on
# each product's contract cycle: Corn/Wheat/Coffee five contracts a year (F6), Soybean seven (F8), Sugar four (F5), Soybean Oil eight
# (F8 is only 10-11 months: its price file stops at F8). CARRY_TENOR_PAIRS holds the uniform SHORT pair (also what the Streamlit app
# shows); the long pairs come from carry_pairs(product). Agriculture has had no liquidity study.
CARRY_LONG_FAR_BY_PRODUCT: dict[str, str] = {"Corn": "F6", "Wheat": "F6", "Soybean": "F7", "LiveCattle": "F7",
                                              "Sugar": "F6", "Cocoa": "F6", "Coffee": "F6", "Cotton": "F6"}   # user decision 2026-11-10


def carry_pairs(product: str) -> list[tuple[str, str]]:
    """Short pair(s) from CARRY_TENOR_PAIRS plus the product's long pair (F1 to its far leg), if one is defined."""
    pairs = list(CARRY_TENOR_PAIRS)
    far = CARRY_LONG_FAR_BY_PRODUCT.get(product)
    if far is not None and ("F1", far) not in pairs:
        pairs.append(("F1", far))
    return pairs

# Carry momentum (V3): kept as its own separate strategy, same as every
# other asset class -- horizon is asset-independent, tenor pair still
# pending same as Carry above (CarryMom needs a (near, far) pair too).
CARRY_MOMENTUM_HORIZON = 20
CARRY_MOMENTUM_SHIFT_N = 1

# Value: F3 contract / 5yr lookback / +-10% threshold / shift_n=1 --
# identical to all 4 existing asset classes, asset-independent convention.
VALUE_CONTRACT = "F2"   # 2026-11-01 (user decision): F2, not F3, for Precious/Agriculture (sparse contract cycles, F3 can be 4-6 months out). Value on F1/F2/F3 was tested on Prices_0930: IR about zero at all three, no meaningful difference.
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
        raise ValueError(f"Unknown Agri/Softs product {product!r}; valid: {list(AGRI_CODES)}")
    raw = pd.read_excel(CURVE_FILE, sheet_name=SHEET_NAMES[product], header=None, skiprows=2)
    dates = pd.to_datetime(raw[0], errors="coerce")
    n_tenors = raw.shape[1] - 1
    cols = {f"F{t + 1}": pd.to_numeric(raw[t + 1], errors="coerce").values for t in range(n_tenors)}
    curve = pd.DataFrame(cols, index=dates.values)
    curve = curve[curve.index.notna()].sort_index()
    curve = apply_data_fixes(curve, SHEET_NAMES[product], "F1")   # source-data fixes, see rolling_continuous.DATA_FIXES
    return curve.loc[ANALYSIS_START:]


def load_f1_series(product: str) -> pd.DataFrame:
    """F1_raw / F1_continuous / Phase for one Agri product, via the repo's
    own validated roll-adjustment builder -- NOT reimplemented here. Reanchors
    F1_continuous to the sliced window's first day per that function's own
    documented convention (cosmetic only, zero effect on PnL/Sharpe)."""
    if product not in AGRI_CODES:
        raise ValueError(f"Unknown Agri/Softs product {product!r}; valid: {list(AGRI_CODES)}")
    df = get_metal_rolling_f1(AGRI_CODES[product], futures_file=CURVE_FILE,
                               calendar_file=CALENDAR_FILE, config=AGRI_CONFIG, verbose=False,
                               roll_day=ROLL_N, roll_rule=ROLL_RULE)
    df = df.loc[ANALYSIS_START:]
    return reanchor_f1_continuous(df)


def load_f1_series_logret(product: str) -> pd.DataFrame:
    """F1_raw / F1_continuous_ratio / log_price / Phase for one Agri
    product -- the LOG-RETURN methodology series (research/ratio_continuous.py),
    used for the cross-asset research pipeline instead of load_f1_series()'s
    additively-adjusted F1_continuous (fine for dollar PnL within a single
    product, not for combining log returns across products/asset classes)."""
    if product not in AGRI_CODES:
        raise ValueError(f"Unknown Agri/Softs product {product!r}; valid: {list(AGRI_CODES)}")
    df = get_metal_rolling_f1_ratio(AGRI_CODES[product], futures_file=CURVE_FILE,
                                     calendar_file=CALENDAR_FILE, config=AGRI_CONFIG, verbose=False,
                               roll_day=ROLL_N, roll_rule=ROLL_RULE)
    df = df.loc[ANALYSIS_START:]
    df = reanchor_f1_continuous_ratio(df)
    price = df["F1_continuous_ratio"].where(df["F1_continuous_ratio"] > 0)
    df["log_price"] = np.log(price)
    return df
