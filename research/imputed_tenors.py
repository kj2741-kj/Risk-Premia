"""Imputed prices for the only two tenor gaps inside the 2012 sample that a Carry long pair depends on (2026-10-13, agreed with Dimil).

    Heating Oil F13, 19 trading days 2012-04-02 to 2012-04-27: F13 = F12 - 2.805 cents/gal (mean of F13 - F12 over March 2012).
    Isobutane F14, 14 trading days 2013-03-01 to 2013-03-20:  F14 = F13 (the provider repeats F13 as F14; mean spread of February 2013 is 0).

Same-grade fill, missing cells only: a price that is present in the source file is never replaced, so if the provider file is ever repaired the real prices win.
The values are read from data/Imputed_Tenors/imputed_tenors_ho_isobutane.csv (built by Analysis/_v4_build/build_imputed_tenors.py; README in that folder).
Applied at the single place where each consumer reads the curves: research/configs/energy.py and ngl.py load_curve (research pipeline, Final dashboards, portfolio tab, hub)
and common_curve_loader.load_curve_simple (the standalone Streamlit dashboards)."""
from __future__ import annotations

import os

import pandas as pd

_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "Imputed_Tenors", "imputed_tenors_ho_isobutane.csv")
# (workbook file name, sheet name) -> product label in the CSV
SHEETS = {("Energy_Futures_Updated.xlsx", "Heating Oil ULSD (NYMEX)"): "HEATING_OIL",
          ("NGL_Futures_Updated_labels_corrected.xlsx", "Isobutane Argus"): "ISOBUTANE"}
_cache: dict = {}


def _table() -> pd.DataFrame:
    if "t" not in _cache:
        _cache["t"] = pd.read_csv(_CSV, parse_dates=["date"]) if os.path.exists(_CSV) else pd.DataFrame(columns=["date", "product", "leg_2_tenor", "leg_2_price_imputed"])
    return _cache["t"]


def apply_imputed(curve: pd.DataFrame, product_label: str) -> pd.DataFrame:
    """Fill the missing cells of `curve` (index = dates, columns F1, F2, ...) for one product label ('HEATING_OIL' or 'ISOBUTANE'); returns a copy."""
    t = _table()
    t = t[t["product"] == product_label]
    if t.empty:
        return curve
    out = curve.copy()
    for _, r in t.iterrows():
        d, col = pd.Timestamp(r["date"]), r["leg_2_tenor"]
        if d in out.index and col in out.columns and pd.isna(out.at[d, col]):
            out.at[d, col] = float(r["leg_2_price_imputed"])
    return out


def apply_imputed_for_sheet(curve: pd.DataFrame, filepath: str, sheet_name: str) -> pd.DataFrame:
    label = SHEETS.get((os.path.basename(str(filepath)), sheet_name))
    return apply_imputed(curve, label) if label else curve
