"""
research/configs/petroleum.py
===============================
Petroleum bucket (2026-10-31): WTI, Brent, RBOB Gasoline, Heating Oil. This is the old Energy asset class without Henry Hub (NatGas moved to the Power, Emissions and Nat Gas
bucket, research/configs/pen.py) and without Singapore Gasoil / Fuel Oil (dashboard exclusions, as before). A thin wrapper: every parameter, loader, data file and calendar is
configs/energy.py's, unchanged, so the numbers of these four products are exactly the Energy numbers; only the product list and the asset-class label differ.
configs/energy.py itself is left as it was (StatArb and the earlier research read it).
"""
from __future__ import annotations

from energy import (  # noqa: F401  (re-exported on purpose)
    ANALYSIS_START, CALENDAR_FILE, CARRY_MOMENTUM_HORIZON, CARRY_MOMENTUM_SHIFT_N, CARRY_SHIFT_N, CARRY_TENOR_PAIRS,
    CARRY_ZSCORE_WINDOW, CURVE_FILE, METAL_CODES, METALS_CONFIG, MOMENTUM_PAIRS, MOMENTUM_SHIFT_N, ROLL_N, ROLL_RULE,
    SHEET_NAMES, STATARB_ENABLED, VALUE_CONTRACT, VALUE_LOOKBACK_DAYS, VALUE_SHIFT_N, VALUE_THRESHOLD,
    carry_pairs, load_curve, load_f1_series, load_f1_series_logret,
)

ASSET_CLASS = "Petroleum"
PRODUCTS = ["WTI", "Brent", "RBOB", "HeatingOil"]
