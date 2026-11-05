"""
research/configs/emissions.py
===============================
Config for the European gas and carbon products of the "Gas and Emissions" bucket (renamed from "Power, Emissions and Nat Gas" on 2026-11-04) of the research dashboard: EUA carbon allowances (ICE Endex, Bloomberg
root MO), TTF natural gas (ICE Endex, root TZT) and, since 2026-11-04, UK Gas (ICE NBP, root FN, pence per therm; monthly; calendar = Bloomberg expiry history (scripts/new_products.py); Carry F1-F2 + F1-F13 like TTF, F13 quoted from 2008-04-11). Added 2026-10-31. Henry Hub stays in configs/energy.py (the bucket takes NatGas from there). The other power
products come later. Mirrors configs/energy.py: same signal forms, same engine, nothing new in the shared engine. (The module name is historical: it holds the
non-US products of the bucket.)

DATA (RP_PRICES_DIR=Prices_0930, see scripts/make_prices_snapshot.py): Emissions_Futures_Updated.xlsx (EUA_PX F1..F13 and TTF_PX F1..F72 of the Bloomberg pull of 29-Oct,
cut at 2026-09-30) and Emissions_Expiry_Calendars.xlsx (Gas_Power_Emissions_Expiry_History.xlsx: Last Trade Date, Last Delivery Date).

CONTRACTS AND ROLLS. The Bloomberg generic F1 moves to the next contract on the trading day after the last trade date, the convention every other product here uses, so the
existing roll / bridge machinery applies unchanged. Verified 2026-10-31: EUA 74 of 74 rolls on the 5th trading day of the last-trade-date month and 74 of 74 bridges on the
day after the last trade date; TTF the same test (see ENGINE_CHANGELOG.md) and its calendar aligns with the data (the F1-vs-F2 splice error is lowest on the last-trade day,
and 32 of the 40 strongest contract-switch signatures fall on the day after it).
  * EUA: quarterly Mar/Jun/Sep/Dec (Dec only for 2005 and 2029-2031), last trade = third Monday of the delivery month.
  * TTF: monthly contracts, last trade = two business days before the first day of the delivery month (so in the month before it), EUR/MWh.

START DATES (user decision 2026-10-31: research starts in 2011, so a later start is harmless).
  * EUA: 2008-04-01, the first Phase II day. Before it the generic series is Phase I contracts at 0.01-0.07 EUR, and F1 jumps from 0.02 to 22.52 on 2008-04-01 (log move 7.0).
  * TTF: 2006-01-01 (the data begin 2005-06-29; same convention as Energy).

CARRY (user decision 2026-10-31, replaces the earlier F1-F3-only rule): a short pair F1-F2 plus a pair about 12 months out, for both products, matching the Precious / Agriculture
convention (short F1-F2 plus a long pair of roughly 12 months). EUA is quarterly, so F1-F2 spans 3 months and F1-F5 spans 12 months. TTF is monthly, so F1-F2 spans 1 month and F1-F13
spans 12 months. EUA F5 is quoted on 99.8% of days from 2008-04. TTF F13 only exists from 2013-10-04 (F4 and F5 are almost never quoted before 2012, F6 starts 2012-10-02, F7 to F72
start 2013-10-04), so the TTF long-pair z-score cannot exist before about October 2014 (252-day window); until then the summed carry value is missing and the previous signal is kept
(flat before any signal exists), i.e. TTF Carry and Carry momentum are flat for the first part of the reporting window. Carry V2 = sign of the summed z-scores (research/carry_zsum.py).

OTHER SETTINGS as everywhere: Momentum (1,20)/(5,60)/(20,250); Value F3, 1260-day average, +-10% (504 observations minimum in the dashboard); Skewness 252 days; 5 bps costs with
roll days charged (log_return_daily).
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

from rolling_continuous import (apply_data_fixes, EMISSIONS_CALENDAR_FILE, EMISSIONS_CONFIG,  # noqa: E402
                                 EMISSIONS_FUTURES_FILE, get_metal_rolling_f1, reanchor_f1_continuous)
from ratio_continuous import get_metal_rolling_f1_ratio, reanchor_f1_continuous_ratio  # noqa: E402

ASSET_CLASS = "Emissions"

PRODUCTS = ["EUA", "TTF", "UKGas"]
METAL_CODES = {"EUA": "MO", "TTF": "TZT", "UKGas": "FN"}
SHEET_NAMES = {"EUA": "EUA Carbon (ICE Endex)", "TTF": "TTF Natural Gas (ICE Endex)", "UKGas": "UK Gas NBP (ICE)"}

CURVE_FILE = EMISSIONS_FUTURES_FILE
CALENDAR_FILE = EMISSIONS_CALENDAR_FILE
METALS_CONFIG = EMISSIONS_CONFIG   # same name as energy.py/metals.py for uniformity

ANALYSIS_STARTS = {"EUA": "2008-04-01",    # first Phase II day, see the module docstring
                   "TTF": "2006-01-01",
                   "UKGas": "2006-01-01"}   # data begin 2006-01-03

# ── Strategy parameters: identical to configs/energy.py except the carry tenors ──
MOMENTUM_PAIRS: tuple[tuple[int, int], ...] = ((1, 20), (5, 60), (20, 250))
MOMENTUM_SHIFT_N = 1

CARRY_TENOR_PAIRS: list[tuple[str, str]] = [("F1", "F2")]   # short pair for both products (user decision 2026-10-31)
CARRY_LONG_FAR_BY_PRODUCT: dict[str, str] = {"TTF": "F13", "EUA": "F5", "UKGas": "F13"}   # long pair F1-far: 12 months out (monthly TTF: F13; quarterly EUA: F5)
CARRY_ZSCORE_WINDOW = 252
CARRY_SHIFT_N = 1

ROLL_RULE = "expiry_month_nth_td"   # 5th trading day of the month in which each contract's last trade date falls (the repo-wide research rule)
ROLL_N = 5


def carry_pairs(product: str) -> list[tuple[str, str]]:
    """Carry / Carry-Momentum tenor pairs (summed z-scores): the short pair F1-F2 plus the product's long pair (TTF F1-F13, EUA F1-F5)."""
    if product not in SHEET_NAMES:
        raise ValueError(f"Unknown product {product!r}; valid: {PRODUCTS}")
    pairs = list(CARRY_TENOR_PAIRS)
    far = CARRY_LONG_FAR_BY_PRODUCT.get(product)
    if far is not None and ("F1", far) not in pairs:
        pairs.append(("F1", far))
    return pairs


CARRY_MOMENTUM_HORIZON = 20
CARRY_MOMENTUM_SHIFT_N = 1

VALUE_CONTRACT = "F3"
VALUE_LOOKBACK_DAYS = 1260
VALUE_THRESHOLD = 0.10
VALUE_SHIFT_N = 1

STATARB_ENABLED = False


def _check(product: str) -> None:
    if product not in SHEET_NAMES:
        raise ValueError(f"Unknown product {product!r}; valid: {PRODUCTS}")


def load_curve(product: str) -> pd.DataFrame:
    """Full raw price curve (EUA F1..F13, TTF F1..F72) from the product's start date. Simple single-header-row format (title row, Date,F1.. row)."""
    _check(product)
    raw = pd.read_excel(CURVE_FILE, sheet_name=SHEET_NAMES[product], header=None, skiprows=2)
    dates = pd.to_datetime(raw[0], errors="coerce")
    n_tenors = raw.shape[1] - 1
    cols = {f"F{t + 1}": pd.to_numeric(raw[t + 1], errors="coerce").values for t in range(n_tenors)}
    curve = pd.DataFrame(cols, index=dates.values)
    curve = curve[curve.index.notna()].sort_index()
    curve = curve.loc[ANALYSIS_STARTS[product]:]
    return apply_data_fixes(curve, SHEET_NAMES[product], "F1")


def load_f1_series(product: str) -> pd.DataFrame:
    """F1_raw / F1_continuous / Phase, additive (dollar-PnL) convention; kept for parity, not used by the log-return research pipeline."""
    _check(product)
    df = get_metal_rolling_f1(METAL_CODES[product], futures_file=CURVE_FILE, calendar_file=CALENDAR_FILE, config=EMISSIONS_CONFIG,
                               verbose=False, roll_day=ROLL_N, roll_rule=ROLL_RULE)
    df = df.loc[ANALYSIS_STARTS[product]:]
    return reanchor_f1_continuous(df)


def load_f1_series_logret(product: str) -> pd.DataFrame:
    """F1_raw / F1_continuous_ratio / log_price / Phase: the log-return series used by the research pipeline."""
    _check(product)
    df = get_metal_rolling_f1_ratio(METAL_CODES[product], futures_file=CURVE_FILE, calendar_file=CALENDAR_FILE, config=EMISSIONS_CONFIG,
                                     verbose=False, roll_day=ROLL_N, roll_rule=ROLL_RULE)
    df = df.loc[ANALYSIS_STARTS[product]:]
    df = reanchor_f1_continuous_ratio(df)
    price = df["F1_continuous_ratio"].where(df["F1_continuous_ratio"] > 0)
    df["log_price"] = np.log(price)
    return df
