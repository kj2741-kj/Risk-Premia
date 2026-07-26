"""
Per-asset-class config for the generic Momentum/Carry/Value/Comparison router.

Hoists the same per-file dict of defaults each Streamlit dashboard's app.py
already passes as kwargs (see metals_dashboard/app.py vs ngl_dashboard/app.py)
into one shared structure, so one generic router can serve all four asset
classes instead of duplicating route code per asset class.

Only Metals is registered for now (Phase 1 vertical slice) -- Energy,
Precious, NGL are added the same way in a later phase.
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
    # Per-product overrides passed to render_momentum_tab/render_carry_tab/
    # render_value_tab (default_feature_pair, default_active_variants,
    # default_feature_variant, default_active_combo, skip_front_contract) --
    # none for Metals. NGL will populate this heavily (see ngl_dashboard/app.py).
    "defaults": {},
}

REGISTRY: dict[str, dict] = {
    "metals": METALS,
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
