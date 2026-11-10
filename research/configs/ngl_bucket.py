"""
research/configs/ngl_bucket.py
================================
The NGL bucket of the Streamlit apps and the hub (2026-11-04): the Mont Belvieu products of configs/ngl.py plus Naphtha (configs/naphtha.py). Same pattern as pen.py: each product keeps
the data file, calendar and parameters of its own config, this module only dispatches by product so the bucket looks like one asset class to the Portfolio tab and the cross-asset
engine (cross_asset_engine maps the bucket key "ngl" to this module). configs/ngl.py itself is untouched, so every script that reads it (run_regime_table, the tradebooks, the
network-momentum research) keeps its six-product NGL. The apps and the cross-asset layer still show only DASHBOARD_PRODUCTS["ngl"] / exclude Ethylene and Propylene.

Carry tenor pairs: F2-F4 + F2-F14 for the Mont Belvieu products (ngl.py), F2-F4 only for Naphtha (naphtha.py). carry_pairs(product) returns each
product's own list, the mechanism pen.py, Precious and Agriculture use.
"""
from __future__ import annotations

import mmb as _mmb
import naphtha as _nap
import ngl as _ngl

ASSET_CLASS = "NGL"
PRODUCTS = list(_ngl.PRODUCTS) + ["Naphtha", "NatGasoline"]
_SOURCE = {p: _ngl for p in _ngl.PRODUCTS}
_SOURCE["Naphtha"] = _nap
_SOURCE["NatGasoline"] = _mmb   # CME natural gasoline (MMB), added 2026-11-10
METAL_CODES = {**_ngl.METAL_CODES, **_nap.METAL_CODES, **_mmb.METAL_CODES}
SHEET_NAMES = {**_ngl.SHEET_NAMES, **_nap.SHEET_NAMES, **_mmb.SHEET_NAMES}

# parameters shared by every product of the bucket (the checks fail loudly if naphtha.py ever drifts from ngl.py)
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
for _name in ("MOMENTUM_PAIRS", "MOMENTUM_SHIFT_N", "CARRY_ZSCORE_WINDOW", "CARRY_SHIFT_N", "CARRY_MOMENTUM_HORIZON", "CARRY_MOMENTUM_SHIFT_N", "VALUE_CONTRACT",
              "VALUE_LOOKBACK_DAYS", "VALUE_THRESHOLD", "VALUE_SHIFT_N", "ROLL_RULE", "ROLL_N"):
    assert getattr(_ngl, _name) == getattr(_nap, _name), f"ngl_bucket.py: {_name} differs between ngl.py and naphtha.py"
    assert getattr(_ngl, _name) == getattr(_mmb, _name), f"ngl_bucket.py: {_name} differs between ngl.py and mmb.py"

CARRY_TENOR_PAIRS = _ngl.CARRY_TENOR_PAIRS            # the bucket default shown for the Mont Belvieu products; Naphtha has its own via carry_pairs()
STATARB_ENABLED = _ngl.STATARB_ENABLED
ANALYSIS_START = _ngl.ANALYSIS_START
CURVE_FILE = _ngl.CURVE_FILE
CALENDAR_FILE = _ngl.CALENDAR_FILE
METALS_CONFIG = _ngl.METALS_CONFIG


def carry_pairs(product: str) -> list[tuple[str, str]]:
    if product not in _SOURCE:
        raise ValueError(f"Unknown product {product!r}; valid: {PRODUCTS}")
    return _SOURCE[product].carry_pairs(product)


def load_curve(product: str):
    return _SOURCE[product].load_curve(product)


def load_f1_series(product: str):
    return _SOURCE[product].load_f1_series(product)


def load_f1_series_logret(product: str):
    return _SOURCE[product].load_f1_series_logret(product)
