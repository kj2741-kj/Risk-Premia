"""
Adapter for the Fundamental Analysis tab -- Gorton/Hayashi/Rouwenhorst (2013)
cubic-spline basis-on-normalized-inventory regression. Wraps
scripts/ghr_spline_core.py's run_spline_analysis() (hand-rolled OLS +
Newey-West HAC, not statsmodels) and the Copper/WTI loader modules
unchanged -- no math is reimplemented here.
"""

import functools

from common_shared import CHART_LAYOUT
import ghr_copper_inventory_spline as ghr_copper
import ghr_wti_inventory_spline as ghr_wti
from ghr_spline_core import DEFAULT_X_RANGE, DEFAULT_Y_RANGE, run_spline_analysis

from services.momentum import _clean, _fig_to_json

# Loaders take no args and hit disk (Excel/CSV parsing) -- cache once per
# process, matching hub/app.py's own @st.cache_data(ttl=3600) on these exact
# functions.


@functools.lru_cache(maxsize=1)
def _copper_basis_f1f2():
    return ghr_copper.load_daily_basis_f1f2()


@functools.lru_cache(maxsize=1)
def _copper_basis_cash3m():
    return ghr_copper.load_daily_basis_cash3m()


@functools.lru_cache(maxsize=1)
def _copper_inventory():
    return ghr_copper.load_daily_inventory()


@functools.lru_cache(maxsize=1)
def _wti_basis_f1f2():
    return ghr_wti.load_daily_basis_f1f2()


@functools.lru_cache(maxsize=1)
def _wti_inventory():
    return ghr_wti.load_weekly_inventory()


def get_data_bounds(commodity: str, basis_source: str = "f1f2") -> dict:
    if commodity == "copper":
        daily_basis = _copper_basis_f1f2() if basis_source == "f1f2" else _copper_basis_cash3m()
        daily_stock = _copper_inventory()
    elif commodity == "wti":
        daily_basis, daily_stock = _wti_basis_f1f2(), _wti_inventory()
    else:
        raise KeyError(f"Unknown commodity {commodity!r}")
    data_min = max(daily_basis.index.min(), daily_stock.index.min())
    data_max = min(daily_basis.index.max(), daily_stock.index.max())
    return {"data_min": str(data_min.date()), "data_max": str(data_max.date())}


def get_ghr(
    commodity: str, *, basis_source: str = "f1f2",
    start: str | None = None, end: str | None = None,
    trailing_weeks: int = 52, nw_bandwidth: int = 52,
    fixed_scale: bool = True,
) -> dict:
    if commodity == "copper":
        daily_basis = _copper_basis_f1f2() if basis_source == "f1f2" else _copper_basis_cash3m()
        daily_stock = _copper_inventory()
        commodity_label = "Copper"
    elif commodity == "wti":
        basis_source = "f1f2"
        daily_basis, daily_stock = _wti_basis_f1f2(), _wti_inventory()
        commodity_label = "WTI Crude"
    else:
        raise KeyError(f"Unknown commodity {commodity!r}")

    x_range = DEFAULT_X_RANGE if fixed_scale else None
    y_range = DEFAULT_Y_RANGE if fixed_scale else None

    result = run_spline_analysis(
        daily_basis=daily_basis, daily_stock=daily_stock, commodity_label=commodity_label,
        basis_source=basis_source, start=start, end=end,
        trailing_weeks=trailing_weeks, nw_bandwidth=nw_bandwidth,
        save_outputs=False, x_range=x_range, y_range=y_range,
    )

    # Re-theme to match the rest of the app (the source script's own default
    # is "plotly_white" -- fine standalone, but a jarring light chart inside
    # an otherwise all-dark UI). Plotly's update_layout merges nested dicts,
    # so the x_range/y_range already applied above survive this.
    result["fig"].update_layout(**CHART_LAYOUT)

    merged = result["merged"]
    return {
        "fig": _fig_to_json(result["fig"]),
        "slopes": {k: _clean(v) for k, v in result["slopes"].items()},
        "r2": _clean(result["r2"]),
        "period_start": str(result["period_start"].date()),
        "period_end": str(result["period_end"].date()),
        "n_obs": int(len(merged)),
    }
