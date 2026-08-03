"""
Per-asset-class config for the generic Momentum/Carry/Value/Comparison router.

Hoists the same per-file dict of defaults each Streamlit dashboard's app.py
already passes as kwargs (see metals_dashboard/app.py vs ngl_dashboard/app.py)
into one shared structure, so one generic router can serve all four asset
classes instead of duplicating route code per asset class.
"""

import rolling_continuous as rc

METALS = {
    "asset_class": "metals",
    "label": "Metals",
    "rolling_config": rc.METALS_CONFIG,
    "futures_file": rc.METALS_FUTURES_FILE,
    "calendar_file": rc.METALS_CALENDAR_FILE,
    "products": {
        "Copper": {"code": "LP", "unit": "/MT"},
        "Aluminium": {"code": "LA", "unit": "/MT"},
        "Lead": {"code": "LL", "unit": "/MT"},
        "Zinc": {"code": "LX", "unit": "/MT"},
    },
    "skip_front_contract": False,
    "momentum_default_feature": {},
    "carry_default_near": None,
    "carry_default_far": None,
    "carry_default_feature_label": None,
    "value_default_combo": None,
}

ENERGY = {
    "asset_class": "energy",
    "label": "Energy",
    "rolling_config": rc.ENERGY_CONFIG,
    "futures_file": rc.ENERGY_FUTURES_FILE,
    "calendar_file": rc.ENERGY_CALENDAR_FILE,
    "products": {
        "WTI Crude": {"code": "CL", "unit": "/bbl"},
        "Brent Crude": {"code": "CO", "unit": "/bbl"},
        "RBOB Gasoline": {"code": "XB", "unit": "/gal"},
        "Heating Oil": {"code": "HO", "unit": "/gal"},
        "Nat Gas": {"code": "NG", "unit": "/MMBtu"},
    },
    # Singapore Gasoil and Fuel Oil removed 2026-08-03 (matching the Streamlit
    # energy_dashboard's own exclusion, same day) -- both remain in
    # research/configs/energy.py's own PRODUCTS list for the portfolio route,
    # excluded there via portfolio.EXCLUDED_PRODUCTS instead of here.
    "skip_front_contract": False,
    "momentum_default_feature": {},
    "carry_default_near": None,
    "carry_default_far": None,
    "carry_default_feature_label": None,
    "value_default_combo": None,
}

PRECIOUS = {
    "asset_class": "precious",
    "label": "Precious Metals",
    "rolling_config": rc.PRECIOUS_CONFIG,
    "futures_file": rc.PRECIOUS_FUTURES_FILE,
    "calendar_file": rc.PRECIOUS_CALENDAR_FILE,
    "products": {
        "Gold": {"code": "GC", "unit": "/oz"},
        "Silver": {"code": "SI", "unit": "/oz"},
        "Copper (CME)": {"code": "HG", "unit": "/lb"},
        "Platinum": {"code": "PL", "unit": "/oz"},
        "Palladium": {"code": "PA", "unit": "/oz"},
    },
    "skip_front_contract": False,
    "momentum_default_feature": {},
    "carry_default_near": None,
    "carry_default_far": None,
    "carry_default_feature_label": None,
    "value_default_combo": None,
}

# NGL swaps are monthly-averaging instruments where the nominal F1 can be a
# stale/partial-month price, so the whole asset class treats F2 as the
# effective front contract (skip_front_contract=True, matching Bogorad's
# NGL_SKIP_FRONT convention and ngl_dashboard/app.py exactly). Carry/Value
# defaults also shift to far-tenor / different anchors because near-tenor
# carry here is dominated by heating-season seasonality, not genuine term
# structure -- see ngl_dashboard/app.py's CARRY_DEFAULT_ACTIVE/VALUE_DEFAULT_ACTIVE.
NGL = {
    "asset_class": "ngl",
    "label": "NGL / Refined",
    "rolling_config": rc.NGL_CONFIG,
    "futures_file": rc.NGL_FUTURES_FILE,
    "calendar_file": rc.NGL_CALENDAR_FILE,
    "products": {
        "Ethane": {"code": "CAP", "unit": "/gal"},
        "Propane": {"code": "BAP", "unit": "/gal"},
        "Butane": {"code": "DAE", "unit": "/gal"},
        "Isobutane": {"code": "IBD", "unit": "/gal"},
        "Ethylene": {"code": "PCW", "unit": "/lb"},
        "Propylene": {"code": "PGP", "unit": "/lb"},
    },
    "skip_front_contract": True,
    # Per-product override of which of the 3 default MA pairs is initially
    # featured in the Momentum tab's Performance Metrics card (all 6 values
    # are already members of the standard default active-pair set, so this
    # never needs to add a new pair -- only changes which one is highlighted).
    "momentum_default_feature": {
        "CAP": (1, 20), "BAP": (20, 250), "DAE": (5, 60),
        "IBD": (20, 250), "PCW": (1, 20), "PGP": (1, 20),
    },
    "carry_default_near": "F4",
    "carry_default_far": "F15",
    "carry_default_feature_label": "V1 (F4-F15)",
    # No NGL-specific override as of 2026-08-03 -- falls back to services/
    # value.py's own generic default (F3 / 5yr / 10%), matching the Streamlit
    # ngl_dashboard's same-day change (see that file's history: previously
    # F12/10yr, empirically tuned, superseded by the user's decision to force
    # F3 uniformly across all four asset classes, not by new evidence).
    "value_default_combo": None,
}

REGISTRY: dict[str, dict] = {
    "metals": METALS,
    "energy": ENERGY,
    "precious": PRECIOUS,
    "ngl": NGL,
}


def get_asset_config(asset_class: str) -> dict:
    if asset_class not in REGISTRY:
        raise KeyError(f"Unknown asset class: {asset_class!r}")
    return REGISTRY[asset_class]


def get_product_code(asset_class: str, product: str) -> str:
    ac = get_asset_config(asset_class)
    if product not in ac["products"]:
        raise KeyError(f"Unknown product {product!r} for asset class {asset_class!r}")
    return ac["products"][product]["code"]
