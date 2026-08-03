"""
research/configs/energy.py
============================
Ex-ante locked config for the Oil/Energy asset class (WTI, Brent, RBOB,
Heating Oil, Nat Gas, Singapore Gasoil, Fuel Oil). Built 2026-07-24, mirroring
research/configs/metals.py / precious.py's structure.

Signal form and most parameters are identical to Metals/Precious Metals:
  - Momentum: 3-way MA-crossover composite, (1,20)/(5,60)/(20,250).
  - Carry: V1(Level)+V2(Z-score) composite, TWO tenor pairs (per user's
    explicit choice: Energy keeps the Metals-style two-tier structure rather
    than Bogorad's single F4-F15, which is used for NGL instead).
  - Carry-Momentum: same horizon=20, kept separate from the Carry composite.
  - Value: F3 contract (changed from F8 2026-08-03, user's decision applied
    uniformly across all four asset classes) / 5yr lookback / +-10% threshold.

CARRY TENOR, verified via quote-availability (data/06-30 files have no
Volume column, same weaker-proxy caveat as Precious Metals):
  - F1-F3: solid for all 7 products.
  - F1-F13, changed 2026-08-03 from F1-F12 (user's decision, to match
    Metals' F1-F3/F1-F13 convention -- Fuel Oil, the original reason for
    F1-F12, is now excluded from the Energy dashboard/Portfolio tab, see
    energy_dashboard/app.py's ENERGY_PORTFOLIO_EXCLUDED). WTI/Brent/RBOB/
    Heating Oil/Nat Gas/Singapore Gasoil are all >=99.6% quoted through F13.
    CAVEAT: Fuel Oil has NO F13 column at all (only 12 tenors total) and
    remains in this file's own PRODUCTS list for the research pipeline
    (untouched, per the same dashboard-only-exclusion convention as
    Singapore Gasoil/Fuel Oil elsewhere) -- so Fuel Oil's Carry (F1-F13)
    and CarryMom (F1-F13) leg is silently flat/zero-contribution in
    run_regime_table.py's reports (no crash: _carry_base() returns an empty
    series when a tenor column is missing, which reindexes to all-zero
    position), diluting the reported 7-product average by one always-flat
    weight. The dashboard/Portfolio tab itself never sees this dilution
    since Fuel Oil is excluded from that view entirely.

STATARB -- new for this asset class, replicating Bogorad's Diversified
Energy Portfolios paper's 8-spread sleeve exactly: Ethane-Natgas,
Propane-Ethane, Propane-Butane, RBOB-Butane, RBOB-Brent, Brent-ULSD,
ULSD-WTI, WTI-Brent. This is explicitly CROSS-ASSET-CLASS (mixes Energy and
NGL legs) in his own design -- built once, shared by both energy.py and
ngl.py rather than duplicated. n=20 days, eps=10%, same signal form as
research/engine.py's statarb_spread_position (Value's threshold-on-MA rule,
applied to a spread instead of a single price).
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

from rolling_continuous import (ENERGY_CALENDAR_FILE, ENERGY_CONFIG,  # noqa: E402
                                 ENERGY_FUTURES_FILE, get_metal_rolling_f1,
                                 reanchor_f1_continuous)
from ratio_continuous import get_metal_rolling_f1_ratio, reanchor_f1_continuous_ratio  # noqa: E402

ASSET_CLASS = "Energy"

PRODUCTS = ["WTI", "Brent", "RBOB", "HeatingOil", "NatGas", "SingaporeGasoil", "FuelOil"]

METAL_CODES = {"WTI": "CL", "Brent": "CO", "RBOB": "XB", "HeatingOil": "HO",
               "NatGas": "NG", "SingaporeGasoil": "QS", "FuelOil": "FO"}

SHEET_NAMES = {"WTI": "WTI Crude (NYMEX)", "Brent": "Brent Crude (ICE)",
               "RBOB": "RBOB Gasoline (NYMEX)", "HeatingOil": "Heating Oil ULSD (NYMEX)",
               "NatGas": "Nat Gas Henry Hub (NYMEX)", "SingaporeGasoil": "Singapore Gasoil (ICE)",
               "FuelOil": "Fuel Oil 3.5pct Barges (ICE)"}

CURVE_FILE = ENERGY_FUTURES_FILE
CALENDAR_FILE = ENERGY_CALENDAR_FILE
METALS_CONFIG = ENERGY_CONFIG  # kept under this name for uniformity with metals.py/precious.py callers

# Standardized analysis start, same convention as Metals/Precious (2006-01-01).
ANALYSIS_START = "2006-01-01"

# ── Ex-ante strategy parameters ──
MOMENTUM_PAIRS: tuple[tuple[int, int], ...] = ((1, 20), (5, 60), (20, 250))
MOMENTUM_SHIFT_N = 1

CARRY_TENOR_PAIRS: list[tuple[str, str]] = [("F1", "F3"), ("F1", "F13")]
CARRY_ZSCORE_WINDOW = 252
CARRY_SHIFT_N = 1

CARRY_MOMENTUM_HORIZON = 20
CARRY_MOMENTUM_SHIFT_N = 1

VALUE_CONTRACT = "F3"
VALUE_LOOKBACK_DAYS = 1260
VALUE_THRESHOLD = 0.10
VALUE_SHIFT_N = 2

# StatArb -- Bogorad's 8-spread sleeve, shared across Energy and NGL.
STATARB_ENABLED = True
STATARB_LOOKBACK_DAYS = 20
STATARB_THRESHOLD = 0.10
STATARB_SHIFT_N = 2
# (asset_of_a, product_a, tenor_a), (asset_of_b, product_b, tenor_b) -- 'energy'/'ngl'
# tags which config's load_curve to call; F1 throughout matches Bogorad's own
# spread definitions (front-month crack/location spreads).
STATARB_PAIRS = [
    (("ngl", "Ethane", "F1"), ("energy", "NatGas", "F1")),
    (("ngl", "Propane", "F1"), ("ngl", "Ethane", "F1")),
    (("ngl", "Propane", "F1"), ("ngl", "Butane", "F1")),
    (("energy", "RBOB", "F1"), ("ngl", "Butane", "F1")),
    (("energy", "RBOB", "F1"), ("energy", "Brent", "F1")),
    (("energy", "Brent", "F1"), ("energy", "HeatingOil", "F1")),
    (("energy", "HeatingOil", "F1"), ("energy", "WTI", "F1")),
    (("energy", "WTI", "F1"), ("energy", "Brent", "F1")),
]


def load_curve(product: str) -> pd.DataFrame:
    """Full F1..Fn raw price curve for one Energy product. Simple
    single-header-row format, no Volume/OpenInt columns.

    WTI-only, single-cell fix: the raw F1 print on 2020-04-20 is the
    famous negative settlement (-37.63), a storage-constraint expiry
    artifact of the May 2020 contract's last hours of trading, not a
    genuine crude-oil value. It is invisible to Momentum/Carry/Value
    (their roll-adjusted continuous series had already switched to
    tracking F2 by that date, 5 business days ahead of expiry -- see
    ratio_continuous.py), but StatArb's WTI-Brent and HeatingOil-WTI
    legs use this literal raw column directly (correctly, matching
    Value's own convention of trading real contract levels, not a
    back-adjusted synthetic series -- see project memory 2026-07-24),
    so it must be cleaned at the source here. Fixed using the same
    technique as the HFS crack-spread project's price_fetcher.py:
    impute from Brent's own price that day minus the average WTI-Brent
    spread on the adjacent trading days (2020-04-17, 2020-04-21).
    Scoped to this one cell only -- no other date, tenor, or product."""
    if product not in SHEET_NAMES:
        raise ValueError(f"Unknown Energy product {product!r}; valid: {PRODUCTS}")
    raw = pd.read_excel(CURVE_FILE, sheet_name=SHEET_NAMES[product], header=None, skiprows=2)
    dates = pd.to_datetime(raw[0], errors="coerce")
    n_tenors = raw.shape[1] - 1
    cols = {f"F{t + 1}": pd.to_numeric(raw[t + 1], errors="coerce").values for t in range(n_tenors)}
    curve = pd.DataFrame(cols, index=dates.values)
    curve = curve[curve.index.notna()].sort_index()
    curve = curve.loc[ANALYSIS_START:]

    if product == "WTI":
        anomaly = pd.Timestamp("2020-04-20")
        if anomaly in curve.index and curve.loc[anomaly, "F1"] < 0:
            brent = load_curve("Brent")
            d17, d21 = pd.Timestamp("2020-04-17"), pd.Timestamp("2020-04-21")
            spread_17 = brent.loc[d17, "F1"] - curve.loc[d17, "F1"]
            spread_21 = brent.loc[d21, "F1"] - curve.loc[d21, "F1"]
            avg_spread = (spread_17 + spread_21) / 2
            curve.loc[anomaly, "F1"] = brent.loc[anomaly, "F1"] - avg_spread
    return curve


def load_f1_series(product: str) -> pd.DataFrame:
    """F1_raw / F1_continuous / Phase via the repo's validated roll-adjustment
    builder (dollar-PnL / additive convention) -- kept for parity, not used
    by the log-return research pipeline."""
    if product not in METAL_CODES:
        raise ValueError(f"Unknown Energy product {product!r}; valid: {PRODUCTS}")
    df = get_metal_rolling_f1(METAL_CODES[product], futures_file=CURVE_FILE,
                               calendar_file=CALENDAR_FILE, config=ENERGY_CONFIG, verbose=False)
    df = df.loc[ANALYSIS_START:]
    return reanchor_f1_continuous(df)


def load_f1_series_logret(product: str) -> pd.DataFrame:
    """F1_raw / F1_continuous_ratio / log_price / Phase -- the log-return
    methodology series used by the research pipeline."""
    if product not in METAL_CODES:
        raise ValueError(f"Unknown Energy product {product!r}; valid: {PRODUCTS}")
    df = get_metal_rolling_f1_ratio(METAL_CODES[product], futures_file=CURVE_FILE,
                                     calendar_file=CALENDAR_FILE, config=ENERGY_CONFIG, verbose=False)
    df = df.loc[ANALYSIS_START:]
    df = reanchor_f1_continuous_ratio(df)
    price = df["F1_continuous_ratio"].where(df["F1_continuous_ratio"] > 0)
    df["log_price"] = np.log(price)
    return df
