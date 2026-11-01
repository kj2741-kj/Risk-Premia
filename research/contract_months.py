"""Exact number of calendar months between two generic futures tenors (F_near, F_far) on every date (2026-10-12), for the per-month spread of the Carry-Momentum research variant.

Metals, Energy and NGL list a contract every month, so F_far - F_near tenors are exactly (far - near) months apart on every date.
Precious Metals and Agriculture list only some months (Gold Feb/Apr/Jun/Aug/Oct/Dec, Corn Mar/May/Jul/Sep/Dec, ...), so the gap depends on the date. From the product's own
expiry calendar (the Bloomberg-matched one the roll logic uses): on date t, F1 is the first contract whose last trade date is on or after t (Bloomberg rolls the day after the
last trade date), F_k is the k-th contract from there, and the gap between two tenors is the difference of their contract-month indices (Year*12 + Month). Contracts beyond the
end of the calendar are generated from the product's own cycle (months seen in the last five calendar years), with the end of the contract month as a stand-in last trade date."""
from __future__ import annotations

import numpy as np
import pandas as pd

import rolling_continuous as rc

MONTHLY = {"metals", "energy", "ngl"}


def _contracts(asset: str, product: str):
    import importlib
    if asset == "precious":
        cfgmod = importlib.import_module("precious"); code = cfgmod.METAL_CODES[product]; cfg = rc.PRECIOUS_CONFIG[code]; f = rc.PRECIOUS_CALENDAR_FILE
    elif asset == "agri":
        cfgmod = importlib.import_module("agri"); code = cfgmod.AGRI_CODES[product]; cfg = rc.AGRI_BBG_CONFIG[code]; f = rc.AGRI_CALENDAR_FILE_BBG
    else:
        raise ValueError(asset)
    cal = pd.read_excel(f, sheet_name=cfg["calendar_sheet"])
    cal = cal.dropna(subset=["Year", "Month"]).copy()
    cal["mi"] = cal["Year"].astype(int) * 12 + cal["Month"].astype(int)
    cal["ltd"] = pd.to_datetime(cal["LAST_TRADEABLE_DT"], errors="coerce")
    month_end = pd.to_datetime(dict(year=cal["Year"].astype(int), month=cal["Month"].astype(int), day=1)) + pd.offsets.MonthEnd(0)
    cal["ltd"] = cal["ltd"].fillna(month_end)
    cal = cal.sort_values("mi").drop_duplicates("mi")
    cal["ltd"] = cal["ltd"].cummax()                              # last trade dates must not go backwards
    last5 = cal[cal["Year"] >= cal["Year"].max() - 5]
    cycle = sorted(set(int(m) for m in last5["Month"]))
    mi, ltd = cal["mi"].tolist(), cal["ltd"].tolist()
    y = (mi[-1] - 1) // 12
    while y < cal["Year"].max() + 9:                              # extend with the product's own cycle, far beyond any price date
        y += 1
        for m in cycle:
            v = y * 12 + m
            if v > mi[-1]:
                mi.append(v); ltd.append(pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(0))
    return np.array(mi), np.array(pd.to_datetime(ltd), dtype="datetime64[ns]"), cycle


def months_between(asset: str, product: str, near: str, far: str, dates: pd.Index) -> pd.Series:
    kn, kf = int(near[1:]), int(far[1:])
    if asset in MONTHLY:
        return pd.Series(float(kf - kn), index=dates)
    mi, ltd, _ = _contracts(asset, product)
    pos = np.searchsorted(ltd, np.asarray(dates, dtype="datetime64[ns]"), side="left")   # first contract with last trade date >= date
    return pd.Series((mi[pos + kf - 1] - mi[pos + kn - 1]).astype(float), index=dates)
