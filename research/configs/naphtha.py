"""
research/configs/naphtha.py
=============================
Naphtha (Bloomberg KI generic "COMB", Platts Naphtha CIF NWE monthly average-price swap, USD per metric ton, 1,000 t a lot), added to the NGL bucket 2026-11-04.
Mirrors configs/ngl.py: it is an average-price swap like the Mont Belvieu NGL swaps, so the same convention applies (the sheet's F2/F3 columns are the effective front/next
contract because F1 is the month being priced; roll on the 5th trading day of the month of each contract's last trade date; Momentum (1,20)/(5,60)/(20,250); Value F3 / 1260 days /
+-10%; Skewness 252 days; 5 bps costs). Shared parameters are imported from ngl.py so the two cannot drift apart.

DATA: Naphtha_Futures_Updated.xlsx (sheet "Naphtha KI (COMB)", F1..F24, PX_LAST of the 2026-11-03 Bloomberg drop) and Naphtha_Expiry_Calendars.xlsx (Bloomberg's expiry history:
last trade = last business day of the pricing month), both in the price folder selected by RP_PRICES_DIR (scripts/new_products.py writes them).

CARRY TENOR PAIR (user decision 2026-11-04): F2-F4 only, for Carry and Carry momentum. The NGL second pair F2-F14 is not used because Naphtha F14 is quoted on only 52% of days in 2023 and
16 to 36% in 2024-2026, which would leave the summed Carry signal missing on most days since 2023; F4 is quoted on every day.
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
from rolling_continuous import (NAPHTHA_CALENDAR_FILE, NAPHTHA_CONFIG, NAPHTHA_FUTURES_FILE,  # noqa: E402
                                 get_metal_rolling_f1, reanchor_f1_continuous)
from ratio_continuous import get_metal_rolling_f1_ratio, reanchor_f1_continuous_ratio  # noqa: E402

ASSET_CLASS = "NGL"
PRODUCTS = ["Naphtha"]
METAL_CODES = {"Naphtha": "KI"}
SHEET_NAMES = {"Naphtha": "Naphtha KI (COMB)"}
CURVE_FILE = NAPHTHA_FUTURES_FILE
CALENDAR_FILE = NAPHTHA_CALENDAR_FILE
METALS_CONFIG = NAPHTHA_CONFIG
ANALYSIS_START = "2006-01-01"          # the data begin 2006-01-03

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

CARRY_TENOR_PAIRS: list[tuple[str, str]] = [("F2", "F4")]


def carry_pairs(product: str = "Naphtha") -> list[tuple[str, str]]:
    return list(CARRY_TENOR_PAIRS)


def _check(product: str) -> None:
    if product not in SHEET_NAMES:
        raise ValueError(f"Unknown product {product!r}; valid: {PRODUCTS}")


def load_curve(product: str = "Naphtha") -> pd.DataFrame:
    """Raw Naphtha curve F1..F24 with the sheet's own labels (not shifted), from ANALYSIS_START."""
    _check(product)
    raw = pd.read_excel(CURVE_FILE, sheet_name=SHEET_NAMES[product], header=None, skiprows=2)
    dates = pd.to_datetime(raw[0], errors="coerce")
    cols = {f"F{t + 1}": pd.to_numeric(raw[t + 1], errors="coerce").values for t in range(raw.shape[1] - 1)}
    curve = pd.DataFrame(cols, index=dates.values)
    curve = curve[curve.index.notna()].sort_index()
    return curve.loc[ANALYSIS_START:]


def load_f1_series(product: str = "Naphtha") -> pd.DataFrame:
    _check(product)
    df = get_metal_rolling_f1(METAL_CODES[product], futures_file=CURVE_FILE, calendar_file=CALENDAR_FILE, config=NAPHTHA_CONFIG,
                               verbose=False, roll_day=ROLL_N, roll_rule=ROLL_RULE)
    return reanchor_f1_continuous(df.loc[ANALYSIS_START:])


def load_f1_series_logret(product: str = "Naphtha") -> pd.DataFrame:
    _check(product)
    df = get_metal_rolling_f1_ratio(METAL_CODES[product], futures_file=CURVE_FILE, calendar_file=CALENDAR_FILE, config=NAPHTHA_CONFIG,
                                     verbose=False, roll_day=ROLL_N, roll_rule=ROLL_RULE)
    df = reanchor_f1_continuous_ratio(df.loc[ANALYSIS_START:])
    price = df["F1_continuous_ratio"].where(df["F1_continuous_ratio"] > 0)
    df["log_price"] = np.log(price)
    return df
