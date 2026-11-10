"""
research/configs/mmb.py
=========================
CME natural gasoline, Mont Belvieu 5-decimal OPIS swap (Bloomberg root MMB; 42,000 gal = 1,000 bbl a lot, USD per gallon), added to the NGL bucket 2026-11-10.
Mirrors naphtha.py / ngl.py: a monthly cash-settled average-price swap, so the same convention applies (the sheet's F2/F3 columns are the effective front/next contract because F1 is the month
being priced; roll on the 5th trading day of the month of each contract's last trade date; Momentum (1,20)/(5,60)/(20,250); Value F3 / 1260 days / +-10%; 5 bps costs). Shared parameters are
imported from ngl.py so the two cannot drift apart.

Why MMB and not the other two natural-gasoline contracts in the drop: CRP (legacy) has no data after 2019-07; OGC (Conway) trades about 15 lots a day with F2 open interest around 100; MMB trades
about 250 lots a day in F2 with 21k open interest across F1-F6 (last year). ICE natural gasoline is not available on this terminal.

DATA: NGL_MMB_Futures.xlsx (sheet "Natural Gasoline MMB (CME)", F1..F48, PX_LAST, 2009-09-22 to the cut) and NGL_MMB_Expiry_Calendars.xlsx (Bloomberg expiry history, last trade = last business day of
the pricing month), written by scripts/new_products_1110.py into the price folder selected by RP_PRICES_DIR.

CARRY TENOR PAIRS (user decision 2026-11-10, "match other NGLs"): F2-F4 + F2-F14, exactly the Mont Belvieu pairs. Unlike Naphtha, MMB F14 is quoted on
about 99-100% of days in every year since 2010, so both pairs are usable. The final tenor choice is the user's, from the F2-F3 gap check (monthly, 1 month, as every NGL).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))
_SCRIPTS_DIR = os.path.join(_REPO_ROOT, "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import ngl as _ngl  # noqa: E402
from rolling_continuous import (MMB_CALENDAR_FILE, MMB_CONFIG, MMB_FUTURES_FILE,  # noqa: E402
                                 get_metal_rolling_f1, reanchor_f1_continuous)
from ratio_continuous import get_metal_rolling_f1_ratio, reanchor_f1_continuous_ratio  # noqa: E402

ASSET_CLASS = "NGL"
PRODUCTS = ["NatGasoline"]
METAL_CODES = {"NatGasoline": "MMB"}
SHEET_NAMES = {"NatGasoline": "Natural Gasoline MMB (CME)"}
CURVE_FILE = MMB_FUTURES_FILE
CALENDAR_FILE = MMB_CALENDAR_FILE
METALS_CONFIG = MMB_CONFIG
ANALYSIS_START = "2009-10-01"          # first real contract month Oct-09 (the first price row, 2009-09-22, carries only far tenors)

# shared with ngl.py
MOMENTUM_PAIRS = _ngl.MOMENTUM_PAIRS
MOMENTUM_SHIFT_N = _ngl.MOMENTUM_SHIFT_N
CARRY_ZSCORE_WINDOW = _ngl.CARRY_ZSCORE_WINDOW
CARRY_SHIFT_N = _ngl.CARRY_SHIFT_N
CARRY_MOMENTUM_HORIZON = _ngl.CARRY_MOMENTUM_HORIZON
CARRY_MOMENTUM_SHIFT_N = _ngl.CARRY_MOMENTUM_SHIFT_N
VALUE_CONTRACT = _ngl.VALUE_CONTRACT
VALUE_LOOKBACK_DAYS = _ngl.VALUE_LOOKBACK_DAYS
VALUE_THRESHOLD = _ngl.VALUE_THRESHOLD
VALUE_SHIFT_N = _ngl.VALUE_SHIFT_N
ROLL_RULE = _ngl.ROLL_RULE
ROLL_N = _ngl.ROLL_N
STATARB_ENABLED = False

CARRY_TENOR_PAIRS: list[tuple[str, str]] = [("F2", "F4"), ("F2", "F14")]   # as the Mont Belvieu NGL products


def carry_pairs(product: str = "NatGasoline") -> list[tuple[str, str]]:
    return list(CARRY_TENOR_PAIRS)


def _check(product: str) -> None:
    if product not in SHEET_NAMES:
        raise ValueError(f"Unknown product {product!r}; valid: {PRODUCTS}")


def load_curve(product: str = "NatGasoline") -> pd.DataFrame:
    """Raw MMB curve F1..F48 with the sheet's own labels (not shifted), from ANALYSIS_START."""
    _check(product)
    raw = pd.read_excel(CURVE_FILE, sheet_name=SHEET_NAMES[product], header=None, skiprows=2)
    dates = pd.to_datetime(raw[0], errors="coerce")
    cols = {f"F{t + 1}": pd.to_numeric(raw[t + 1], errors="coerce").values for t in range(raw.shape[1] - 1)}
    curve = pd.DataFrame(cols, index=dates.values)
    curve = curve[curve.index.notna()].sort_index()
    return curve.loc[ANALYSIS_START:]


def load_f1_series(product: str = "NatGasoline") -> pd.DataFrame:
    _check(product)
    df = get_metal_rolling_f1(METAL_CODES[product], futures_file=CURVE_FILE, calendar_file=CALENDAR_FILE, config=MMB_CONFIG,
                               verbose=False, roll_day=ROLL_N, roll_rule=ROLL_RULE)
    return reanchor_f1_continuous(df.loc[ANALYSIS_START:])


def load_f1_series_logret(product: str = "NatGasoline") -> pd.DataFrame:
    _check(product)
    df = get_metal_rolling_f1_ratio(METAL_CODES[product], futures_file=CURVE_FILE, calendar_file=CALENDAR_FILE, config=MMB_CONFIG,
                                     verbose=False, roll_day=ROLL_N, roll_rule=ROLL_RULE)
    df = reanchor_f1_continuous_ratio(df.loc[ANALYSIS_START:])
    price = df["F1_continuous_ratio"].where(df["F1_continuous_ratio"] > 0)
    df["log_price"] = np.log(price)
    return df
