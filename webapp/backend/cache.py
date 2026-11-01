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

import contextlib
import functools
import threading

import streamlit as st

import common_curve_loader
import rolling_continuous
import rolling_continuous_5td

from common_shared import RETURN_BASIS_KEY, RETURN_BASIS_OPTIONS, register_geo_inputs
from config_registry import get_asset_config, get_product_source


@functools.lru_cache(maxsize=128)
def load_series(asset_class: str, product_code: str, roll_method: str, roll_n: int):
    """Returns (f1_df, curve) for one product, cached on primitives only.

    Built exactly as each Streamlit dashboard's app.py builds it: the product's own price file, calendar and config registry
    (PEN products differ), rolled by the chosen method, cut at the product's first date, F1_continuous re-anchored. f1_df has
    columns F1_raw/F2_raw/F1_continuous/Phase/is_roll_date/is_bridge_date/active_contract (see scripts/rolling_continuous.py);
    curve has columns F1..Fn raw price levels (see common_curve_loader.py).
    """
    ac = get_asset_config(asset_class)
    name = next(n for n, p in ac["products"].items() if p["code"] == product_code)
    src = get_product_source(asset_class, name)
    config, futures_file, calendar_file, start = src["rolling_config"], src["futures_file"], src["calendar_file"], src["start"]

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

    f1_df = rolling_continuous.reanchor_f1_continuous(f1_df[f1_df.index >= start])
    curve = common_curve_loader.load_curve_simple(futures_file, config[product_code]["price_sheet"])
    curve = curve[curve.index >= start]
    return f1_df, curve


# The shared engine reads the F2_raw / Phase of the product being computed from Streamlit's session_state (register_geo_inputs), which
# is process-global when there is no Streamlit runtime. Every service function therefore computes inside `engine_lock(f1_df)`, which
# serialises requests and registers that product's inputs, so the numbers equal the Streamlit app's (exact ratio returns on the
# geometric basis, the default return basis there).
_ENGINE_LOCK = threading.RLock()


@contextlib.contextmanager
def engine_lock(f1_df):
    with _ENGINE_LOCK:
        register_geo_inputs(f1_df)
        yield


def locked(fn):
    """Run a service function under the engine lock (see engine_lock) with the request's return basis applied.

    The shared engine reads the return basis (Arithmetic $ PnL / Geometric % return) from st.session_state, as the Streamlit sidebar radio
    sets it. `geometric` (default True, Streamlit's default) is taken off the call here and written to that state for the duration of it."""
    @functools.wraps(fn)
    def wrapper(*a, geometric: bool = True, **k):
        with _ENGINE_LOCK:
            st.session_state[RETURN_BASIS_KEY] = RETURN_BASIS_OPTIONS[1] if geometric else RETURN_BASIS_OPTIONS[0]
            return fn(*a, **k)
    return wrapper
