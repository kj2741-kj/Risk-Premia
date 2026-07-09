"""
ghr_wti_inventory_spline.py
==============================
WTI Crude data loaders for the GHR (Gorton, Hayashi & Rouwenhorst 2013)
cubic-spline basis-on-inventory regression. Shares the same econometrics core
(ghr_spline_core.py) as ghr_copper_inventory_spline.py.

Basis (Eq. 15 of the paper, using actual contract day-counts):
    basis_t = (F1_t / F2_t - 1) * 365 / (D2_t - D1_t)
  F1/F2   : nearest / next-nearest NYMEX WTI (CL) contract close, built via
            rolling_continuous.get_metal_rolling_f1("CL", config=ENERGY_CONFIG)
            from data/06-30/Energy_Futures_Updated.xlsx
  D1/D2   : days from t to the last-tradeable-date of the F1/F2 contract
            (data/06-30/expiry_calendars_20260701.xlsx,
             "CL - WTI Crude Oil (NYMEX)")

Normalized inventory (Section 3.2):
    x_t = I_t / I*_t,  I*_t = trailing 52-week average of I_{t-1..t-52}
  I     : EIA US crude oil stocks excl. SPR, weekly (Friday), thousand bbls
          (data/WTI_Crude_Inventory_2005_to_2026-07-09.xlsx) -- already
          weekly, so no daily->weekly resampling is needed for inventory,
          only for the basis (built from daily futures prices).

Outputs (outputs/ghr_wti/), file names tagged with basis source + period:
  wti_crude_basis_inventory_weekly_<source>_<start>_<end>.csv
  wti_crude_basis_vs_inventory_<source>_<start>_<end>.html
Console: Table III style slope/t-stat summary at x=1 and x=0.75.

Changing the analysis period:
  CLI:      python ghr_wti_inventory_spline.py --start 2015-01-01 --end 2020-12-31
  Python:   from ghr_wti_inventory_spline import run_analysis
            result = run_analysis(start="2015-01-01", end="2020-12-31")
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _SCRIPT_DIR)

from ghr_spline_core import (
    TRAILING_WEEKS, NW_BANDWIDTH, DEFAULT_X_RANGE, DEFAULT_Y_RANGE,
    f1f2_basis_from_curve, run_spline_analysis,
)
from rolling_continuous import get_metal_rolling_f1, ENERGY_CONFIG, ENERGY_FUTURES_FILE, ENERGY_CALENDAR_FILE

DATA_DIR = os.path.join(_REPO_ROOT, "data")
OUTPUTS_DIR = os.path.join(_REPO_ROOT, "outputs", "ghr_wti")

CALENDAR_SHEET = "CL - WTI Crude Oil (NYMEX)"
INVENTORY_XLSX = os.path.join(DATA_DIR, "WTI_Crude_Inventory_2005_to_2026-07-09.xlsx")
INVENTORY_SHEET = "WCESTUS1_Weekly"
INVENTORY_COL = "Crude_Oil_Inventory_ExclSPR_MBBL"


# ─────────────────────────────────────────────────────────────────────────────
# WTI-specific loaders
# ─────────────────────────────────────────────────────────────────────────────

def load_daily_basis_f1f2() -> pd.Series:
    """Eq. 15 basis from nearest/next-nearest NYMEX WTI (CL) contract closes."""
    px = get_metal_rolling_f1(
        "CL", config=ENERGY_CONFIG, futures_file=ENERGY_FUTURES_FILE,
        calendar_file=ENERGY_CALENDAR_FILE, verbose=False,
    )
    return f1f2_basis_from_curve(px["F1_raw"], px["F2_raw"], ENERGY_CALENDAR_FILE, CALENDAR_SHEET)


def load_weekly_inventory() -> pd.Series:
    """EIA US crude oil stocks excl. SPR, weekly (Friday), thousand barrels."""
    inv = pd.read_excel(INVENTORY_XLSX, sheet_name=INVENTORY_SHEET, parse_dates=["Date"])
    inv = inv.set_index("Date").sort_index()
    return pd.to_numeric(inv[INVENTORY_COL], errors="coerce").dropna()


BASIS_LOADERS = {
    "f1f2": load_daily_basis_f1f2,
}


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_analysis(
    start: str | None = None,
    end: str | None = None,
    basis_source: str = "f1f2",
    trailing_weeks: int = TRAILING_WEEKS,
    nw_bandwidth: int = NW_BANDWIDTH,
    output_dir: str = OUTPUTS_DIR,
    save_outputs: bool = True,
    x_range: tuple[float, float] | None = DEFAULT_X_RANGE,
    y_range: tuple[float, float] | None = DEFAULT_Y_RANGE,
) -> dict:
    if basis_source not in BASIS_LOADERS:
        raise ValueError(f"basis_source must be one of {list(BASIS_LOADERS)}, got {basis_source!r}")

    # Inventory is already weekly (Friday); run_spline_analysis's to_weekly_last
    # resample is a no-op pass-through in that case (last obs of an already-
    # single-obs week == itself).
    return run_spline_analysis(
        daily_basis=BASIS_LOADERS[basis_source](),
        daily_stock=load_weekly_inventory(),
        commodity_label="WTI Crude",
        basis_source=basis_source,
        start=start, end=end,
        trailing_weeks=trailing_weeks, nw_bandwidth=nw_bandwidth,
        output_dir=output_dir, save_outputs=save_outputs,
        x_range=x_range, y_range=y_range,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GHR cubic-spline basis-on-inventory regression for WTI Crude.")
    parser.add_argument("--start", default=None, help="Regression window start, YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="Regression window end, YYYY-MM-DD")
    parser.add_argument("--basis-source", choices=list(BASIS_LOADERS), default="f1f2",
                         help="'f1f2' (paper's exact F1/F2 day-count basis)")
    parser.add_argument("--trailing-weeks", type=int, default=TRAILING_WEEKS,
                         help="Weeks in the I* trailing average (default 52)")
    parser.add_argument("--nw-bandwidth", type=int, default=NW_BANDWIDTH,
                         help="Newey-West HAC lag window in weeks (default 52)")
    parser.add_argument("--output-dir", default=OUTPUTS_DIR, help="Where to save CSV/HTML outputs")
    parser.add_argument("--x-range", type=float, nargs=2, default=None, metavar=("MIN", "MAX"),
                         help=f"Plot x-axis range (default {DEFAULT_X_RANGE}, shared across commodities)")
    parser.add_argument("--y-range", type=float, nargs=2, default=None, metavar=("MIN", "MAX"),
                         help=f"Plot y-axis range (default {DEFAULT_Y_RANGE}, shared across commodities)")
    parser.add_argument("--autorange", action="store_true",
                         help="Disable fixed axis ranges (let plotly autorange instead)")
    args = parser.parse_args()

    if args.autorange:
        x_range, y_range = None, None
    else:
        x_range = tuple(args.x_range) if args.x_range else DEFAULT_X_RANGE
        y_range = tuple(args.y_range) if args.y_range else DEFAULT_Y_RANGE

    run_analysis(
        start=args.start,
        end=args.end,
        basis_source=args.basis_source,
        trailing_weeks=args.trailing_weeks,
        nw_bandwidth=args.nw_bandwidth,
        output_dir=args.output_dir,
        x_range=x_range, y_range=y_range,
    )


if __name__ == "__main__":
    main()
