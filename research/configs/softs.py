"""
research/configs/softs.py
===========================
Softs bucket (2026-11-10): Sugar No.11 (ICE US), Cocoa (ICE US), Coffee C (ICE US), Cotton No.2 (ICE US). Split out of the old six-product Agriculture bucket (Coffee, Sugar) plus the new
Cocoa and Cotton. A thin wrapper: every parameter, loader, data file and calendar is configs/agri.py's (the two buckets share one data drop, one calendar and one engine path), only the
product list and the asset-class label differ. Carry pairs (user decision 2026-11-10): F1-F2 plus F1-F6 for all four.
"""
from __future__ import annotations

from agri import (  # noqa: F401  (re-exported on purpose)
    ANALYSIS_START, CALENDAR_FILE, CARRY_MOMENTUM_HORIZON, CARRY_MOMENTUM_SHIFT_N, CARRY_SHIFT_N, CARRY_TENOR_PAIRS,
    CARRY_ZSCORE_WINDOW, CURVE_FILE, MOMENTUM_PAIRS, MOMENTUM_SHIFT_N, ROLL_N, ROLL_RULE,
    SHEET_NAMES, STATARB_ENABLED, VALUE_CONTRACT, VALUE_LOOKBACK_DAYS, VALUE_SHIFT_N, VALUE_THRESHOLD,
    AGRI_CODES, CARRY_LONG_FAR_BY_PRODUCT, carry_pairs, load_curve, load_f1_series, load_f1_series_logret,
)

ASSET_CLASS = "Softs"
PRODUCTS = ["Sugar", "Cocoa", "Coffee", "Cotton"]
