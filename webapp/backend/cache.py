"""
Primitive-keyed cache for the expensive per-product data-loading step
(Excel read + roll-adjusted F1 construction).

Deliberately NOT used for the heatmap functions in common_engine.py
(momentum_heatmap/carry_heatmap/value_heatmap) -- those are already wrapped
in @st.cache_data, which hashes pandas Series/DataFrame arguments correctly
via Streamlit's own content hasher. functools.lru_cache cannot hash a
Series/DataFrame at all, so it's only used here, one level up, where every
argument is already a plain string/int.
"""

import functools

import common_curve_loader
import rolling_continuous
import rolling_continuous_5td

from config_registry import get_asset_config


@functools.lru_cache(maxsize=128)
def load_series(asset_class: str, product_code: str, roll_method: str, roll_n: int):
    """Returns (f1_df, curve) for one product, cached on primitives only.

    f1_df has columns F1_raw/F2_raw/F1_continuous/Phase/is_roll_date/
    is_bridge_date/active_contract (see scripts/rolling_continuous.py);
    curve has columns F1..Fn raw price levels (see common_curve_loader.py).
    Both already sliced to >= 2006 and F1_continuous re-anchored, matching
    every existing Streamlit dashboard's app.py convention exactly.
    """
    ac = get_asset_config(asset_class)
    config = ac["rolling_config"]
    futures_file, calendar_file = ac["futures_file"], ac["calendar_file"]

    if roll_method == "ltd":
        f1_df = rolling_continuous.get_metal_rolling_f1(
            product_code, futures_file=futures_file, calendar_file=calendar_file,
            verbose=False, config=config, roll_day=roll_n,
        )
    else:
        f1_df = rolling_continuous_5td.get_rolling_f1_5td(
            product_code, futures_file=futures_file, calendar_file=calendar_file,
            verbose=False, config=config, roll_day=roll_n,
        )

    f1_df = rolling_continuous.reanchor_f1_continuous(f1_df[f1_df.index.year >= 2006])
    curve = common_curve_loader.load_curve_simple(futures_file, config[product_code]["price_sheet"])
    curve = curve[curve.index.year >= 2006]
    return f1_df, curve
