"""
research/configs/pen.py
=========================
"Power, Emissions and Nat Gas" bucket (2026-10-31): Henry Hub natural gas (configs/energy.py), TTF natural gas and EUA carbon (configs/emissions.py). Each product keeps the data,
roll calendar, start date and parameters of its own config; this module only dispatches by product so the bucket looks like one asset class to the Streamlit Portfolio tab and the
cross-asset engine. The other power products are not in yet.

Carry tenor pairs (user decisions): Henry Hub F1-F3 + F1-F13 (the Energy setting), TTF F1-F3 only, EUA F1-F3 only. CARRY_TENOR_PAIRS holds the uniform pair every product uses (F1-F3);
CARRY_LONG_FAR_BY_PRODUCT adds Henry Hub's long pair via carry_pairs(product), the same mechanism Precious Metals and Agriculture use. TTF and EUA start dates: see emissions.py.
"""
from __future__ import annotations

import emissions as _em
import energy as _en

ASSET_CLASS = "Power, Emissions and Nat Gas"
PRODUCTS = ["NatGas", "TTF", "EUA"]
_SOURCE = {"NatGas": _en, "TTF": _em, "EUA": _em}

# Shared strategy parameters: identical across energy.py and emissions.py (the checks below fail loudly if that ever stops being true).
MOMENTUM_PAIRS = _en.MOMENTUM_PAIRS
MOMENTUM_SHIFT_N = _en.MOMENTUM_SHIFT_N
CARRY_ZSCORE_WINDOW = _en.CARRY_ZSCORE_WINDOW
CARRY_SHIFT_N = _en.CARRY_SHIFT_N
CARRY_MOMENTUM_HORIZON = _en.CARRY_MOMENTUM_HORIZON
CARRY_MOMENTUM_SHIFT_N = _en.CARRY_MOMENTUM_SHIFT_N
VALUE_CONTRACT = _en.VALUE_CONTRACT
VALUE_LOOKBACK_DAYS = _en.VALUE_LOOKBACK_DAYS
VALUE_THRESHOLD = _en.VALUE_THRESHOLD
VALUE_SHIFT_N = _en.VALUE_SHIFT_N
ROLL_RULE = _en.ROLL_RULE
ROLL_N = _en.ROLL_N
for _name in ("MOMENTUM_PAIRS", "MOMENTUM_SHIFT_N", "CARRY_ZSCORE_WINDOW", "CARRY_SHIFT_N", "CARRY_MOMENTUM_HORIZON", "CARRY_MOMENTUM_SHIFT_N",
              "VALUE_CONTRACT", "VALUE_LOOKBACK_DAYS", "VALUE_THRESHOLD", "VALUE_SHIFT_N", "ROLL_RULE", "ROLL_N"):
    assert getattr(_en, _name) == getattr(_em, _name), f"pen.py: {_name} differs between energy.py and emissions.py"

CARRY_TENOR_PAIRS: list[tuple[str, str]] = [("F1", "F3")]
CARRY_LONG_FAR_BY_PRODUCT: dict[str, str] = {"NatGas": "F13"}
STATARB_ENABLED = False


def carry_pairs(product: str) -> list[tuple[str, str]]:
    """The product's Carry / Carry-Momentum pairs: F1-F3, plus F1-F13 for Henry Hub only."""
    if product not in _SOURCE:
        raise ValueError(f"Unknown product {product!r}; valid: {PRODUCTS}")
    pairs = list(CARRY_TENOR_PAIRS)
    far = CARRY_LONG_FAR_BY_PRODUCT.get(product)
    if far is not None and ("F1", far) not in pairs:
        pairs.append(("F1", far))
    return pairs


def load_curve(product: str):
    return _SOURCE[product].load_curve(product)


def load_f1_series(product: str):
    return _SOURCE[product].load_f1_series(product)


def load_f1_series_logret(product: str):
    return _SOURCE[product].load_f1_series_logret(product)
