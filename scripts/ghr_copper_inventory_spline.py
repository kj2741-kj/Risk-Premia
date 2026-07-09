"""
ghr_copper_inventory_spline.py
================================
LME Copper data loaders for the GHR (Gorton, Hayashi & Rouwenhorst 2013)
cubic-spline basis-on-inventory regression. The econometrics (design matrix,
OLS, Newey-West HAC, spline gradients, plotting) live in ghr_spline_core.py
and are shared across commodities -- see ghr_wti_inventory_spline.py for the
WTI counterpart.

Two interchangeable basis definitions (--basis-source / basis_source=):

  "f1f2" (default) -- Eq. 15 of the paper, using actual contract day-counts:
    basis_t = (F1_t / F2_t - 1) * 365 / (D2_t - D1_t)
    F1/F2   : nearest / next-nearest LME copper contract close
              (data/LME_Copper_Rolling_F1_v2.csv, F1_raw/F2_raw)
    D1/D2   : days from t to the last-tradeable-date of the F1/F2 contract
              (data/06-30/expiry_calendars_20260701.xlsx, "LP - Copper (LME)")

  "cash3m" -- LME cash vs 3-month forward, both from the same westmetall file
    as the inventory series:
    basis_t = (cash_t / 3m_t - 1) * 365 / days_t
    days_t  : calendar days between t and t + 3 calendar months (the actual
              LME 3m forward tenor), not a fixed 91-day assumption.

Normalized inventory (Section 3.2):
    x_t = I_t / I*_t,  I*_t = trailing 52-week average of I_{t-1..t-52}
  I     : LME copper warehouse stock (data/copper_lme_stock_westmetall.csv)

Outputs (outputs/ghr_copper/), file names tagged with basis source + period:
  copper_basis_inventory_weekly_<source>_<start>_<end>.csv
  copper_basis_vs_inventory_<source>_<start>_<end>.html
Console: Table III style slope/t-stat summary at x=1 and x=0.75.

Changing the analysis period:
  CLI:      python ghr_copper_inventory_spline.py --start 2015-01-01 --end 2020-12-31
  Python:   from ghr_copper_inventory_spline import run_analysis
            result = run_analysis(start="2015-01-01", end="2020-12-31")
  The I*/trailing-average is always computed over the FULL available stock
  history first -- --start/--end only trims the regression sample, so a
  narrow window still has a correctly-lookback-ed I* at its first date.
"""

from __future__ import annotations

import argparse
import os

import pandas as pd

from ghr_spline_core import (
    TRAILING_WEEKS, NW_BANDWIDTH, DEFAULT_X_RANGE, DEFAULT_Y_RANGE,
    f1f2_basis_from_curve, run_spline_analysis,
)

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
DATA_DIR = os.path.join(_REPO_ROOT, "data")
OUTPUTS_DIR = os.path.join(_REPO_ROOT, "outputs", "ghr_copper")

FUTURES_CSV = os.path.join(DATA_DIR, "LME_Copper_Rolling_F1_v2.csv")
CALENDAR_XLSX = os.path.join(DATA_DIR, "06-30", "expiry_calendars_20260701.xlsx")
CALENDAR_SHEET = "LP - Copper (LME)"
INVENTORY_CSV = os.path.join(DATA_DIR, "copper_lme_stock_westmetall.csv")


# ─────────────────────────────────────────────────────────────────────────────
# Copper-specific basis loaders
# ─────────────────────────────────────────────────────────────────────────────

def load_daily_basis_f1f2() -> pd.Series:
    """Eq. 15 basis from nearest/next-nearest LME copper contract closes."""
    px = pd.read_csv(FUTURES_CSV, parse_dates=["Date"]).set_index("Date").sort_index()
    return f1f2_basis_from_curve(px["F1_raw"], px["F2_raw"], CALENDAR_XLSX, CALENDAR_SHEET)


def load_daily_basis_cash3m() -> pd.Series:
    """LME cash vs 3-month forward basis, annualized using the actual 3m tenor day-count."""
    inv = pd.read_csv(INVENTORY_CSV, parse_dates=["date"]).set_index("date").sort_index()
    cash = pd.to_numeric(inv["cash"], errors="coerce")
    three_m = pd.to_numeric(inv["3m"], errors="coerce")
    df = pd.DataFrame({"cash": cash, "3m": three_m}).dropna()
    days_3m = ((df.index + pd.DateOffset(months=3)) - df.index).days.astype(float)
    return (df["cash"] / df["3m"] - 1.0) * 365.0 / days_3m * 100.0


def load_daily_inventory() -> pd.Series:
    """Date-indexed LME copper stock (metric tons), '-' placeholders -> NaN."""
    inv = pd.read_csv(INVENTORY_CSV, parse_dates=["date"]).set_index("date").sort_index()
    return pd.to_numeric(inv["stock"], errors="coerce").dropna()


BASIS_LOADERS = {
    "f1f2": load_daily_basis_f1f2,
    "cash3m": load_daily_basis_cash3m,
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

    return run_spline_analysis(
        daily_basis=BASIS_LOADERS[basis_source](),
        daily_stock=load_daily_inventory(),
        commodity_label="Copper",
        basis_source=basis_source,
        start=start, end=end,
        trailing_weeks=trailing_weeks, nw_bandwidth=nw_bandwidth,
        output_dir=output_dir, save_outputs=save_outputs,
        x_range=x_range, y_range=y_range,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GHR cubic-spline basis-on-inventory regression for LME Copper.")
    parser.add_argument("--start", default=None, help="Regression window start, YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="Regression window end, YYYY-MM-DD")
    parser.add_argument("--basis-source", choices=list(BASIS_LOADERS), default="f1f2",
                         help="'f1f2' (paper's exact F1/F2 day-count basis) or "
                              "'cash3m' (LME cash vs 3m forward)")
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
