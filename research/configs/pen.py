"""
research/configs/pen.py
=========================
"Gas and Emissions" bucket (built 2026-10-31 as "Power, Emissions and Nat Gas", renamed and UK Gas added 2026-11-04; the module and key stay "pen" so the deployed Streamlit app and imports do not break): Henry Hub natural gas (configs/energy.py), TTF natural gas, UK Gas (NBP) and EUA carbon (configs/emissions.py). Each product keeps the data,
roll calendar, start date and parameters of its own config; this module only dispatches by product so the bucket looks like one asset class to the Streamlit Portfolio tab and the
cross-asset engine. The power products are not in yet (the name no longer says "power").

Carry tenor pairs (user decisions): Henry Hub F1-F3 + F1-F13 (the Energy setting), TTF F1-F2 + F1-F13 and EUA F1-F2 + F1-F5 (2026-10-31: short pair plus a pair 12 months out; TTF is monthly, EUA quarterly,
see emissions.py). CARRY_TENOR_PAIRS holds the short pair shown as the default (F1-F2, as for Precious and Agriculture); carry_pairs(product) returns each product's own list, the same mechanism Precious Metals and Agriculture use. TTF and EUA start dates: see emissions.py.
"""
from __future__ import annotations

import emissions as _em
import energy as _en

ASSET_CLASS = "Gas and Emissions"
PRODUCTS = ["NatGas", "TTF", "UKGas", "EUA"]
_SOURCE = {"NatGas": _en, "TTF": _em, "UKGas": _em, "EUA": _em}

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

CARRY_TENOR_PAIRS: list[tuple[str, str]] = [("F1", "F2")]   # the short pair shown as the default (TTF, EUA); Henry Hub keeps F1-F3 + F1-F13 via carry_pairs()
CARRY_LONG_FAR_BY_PRODUCT: dict[str, str] = {"NatGas": "F13", "TTF": "F13", "UKGas": "F13", "EUA": "F5"}
CARRY_CAPTION = "Carry and Carry momentum combine each product's short and long pair: Henry Hub F1-F3 + F1-F13, TTF F1-F2 + F1-F13, UK Gas F1-F2 + F1-F13, EUA F1-F2 + F1-F5 (12 months out), as in the Final dashboard."
STATARB_ENABLED = False


def carry_pairs(product: str) -> list[tuple[str, str]]:
    """The product's Carry / Carry-Momentum pairs: Henry Hub F1-F3 + F1-F13, TTF and UK Gas F1-F2 + F1-F13, EUA F1-F2 + F1-F5."""
    if product not in _SOURCE:
        raise ValueError(f"Unknown product {product!r}; valid: {PRODUCTS}")
    if _SOURCE[product] is _em:
        return _em.carry_pairs(product)
    if _SOURCE[product] is _en:
        return _en.carry_pairs(product)   # Henry Hub: F1-F3 + F1-F13, unchanged
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
