"""
scripts/build_agri_calendar_real_cycle.py
==========================================
Rebuilds data/Prices_0924/Agri_Rolling_Calendar.xlsx keeping ONLY contract
months that are actually listed on the exchange, for each Agriculture product.

Why: the Bloomberg calendar pull generated tickers for months the exchange
does not list (Cotton: all 12 months vs 5 real; Soybean Meal: June; Cocoa:
June; Rough Rice: June/Dec; Live Cattle: 2005 Jan/Mar/May). Phantom months
have unique, plausible-looking dates, so a duplicate-LTD check cannot catch
them. Each phantom makes the roll engine start a spurious "F2 tracking"
phase and book a calendar spread as P&L on the bridge day.

Validated empirically before filtering (see assertions below): the price
curve switches contract on the day after a REAL LTD and does not on the day
after a phantom LTD.

Input : the current Agri_Rolling_Calendar.xlsx (already Sugar-free, Cocoa J23 dropped).
Output: same file, same schema; original saved as Agri_Rolling_Calendar_pre_phantom_fix.xlsx.
"""
import os
import shutil
import sys

import numpy as np
import pandas as pd

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))
from rolling_continuous import AGRI_CALENDAR_FILE, AGRI_CONFIG, AGRI_FUTURES_FILE, load_metal_prices  # noqa: E402

MONTH_CODES = "FGHJKMNQUVXZ"  # Jan..Dec
# Exchange-listed contract cycles (CBOT / ICE US / CME).
REAL_CYCLE = {
    "C": "HKNUZ", "W": "HKNUZ", "O": "HKNUZ", "RR": "FHKNUX", "S": "FHKNQUX",
    "BO": "FHKNQUVZ", "SM": "FHKNQUVZ", "KC": "HKNUZ", "CC": "HKNUZ", "JO": "FHKNUX",
    "CT": "HKNVZ", "FC": "FHJKQUVX", "LC": "GJMQVZ", "LH": "GJKMNQVZ",
}
EXPECTED_REMOVED = {"C": 0, "W": 0, "O": 0, "RR": 7, "S": 0, "BO": 0, "SM": 22,
                    "KC": 0, "CC": 11, "JO": 0, "CT": 154, "FC": 0, "LC": 3, "LH": 0}
BACKUP = AGRI_CALENDAR_FILE.replace(".xlsx", "_pre_phantom_fix.xlsx")


def real_months(code):
    return {MONTH_CODES.index(ch) + 1 for ch in REAL_CYCLE[code]}


def switch_ratio_at_ltd_plus_1(code, cal):
    """Median over contracts of sum|Fk[t]-Fk+1[t-1]| / sum|Fk[t]-Fk[t-1]| (k=1..4) on the
    first trading day after each LTD. < 1 means the curve rolled to the next contract."""
    cfg = AGRI_CONFIG[code]
    raw = pd.read_excel(AGRI_FUTURES_FILE, sheet_name=cfg["price_sheet"], header=None, skiprows=2)
    d = pd.to_datetime(raw[0], errors="coerce")
    K = 4
    px = pd.DataFrame({k: pd.to_numeric(raw[k], errors="coerce").values for k in range(1, K + 2)}, index=d.values)
    px = px[px.index.notna()].sort_index()
    A, B, C = px.iloc[:, :K].values, px.shift(1).iloc[:, 1:K + 1].values, px.shift(1).iloc[:, :K].values
    num, den = np.nansum(np.abs(A - B), 1), np.nansum(np.abs(A - C), 1)
    ratio = pd.Series(num / np.where(den > 0, den, np.nan), index=px.index)
    vals = []
    for l in pd.to_datetime(cal["LAST_TRADEABLE_DT"]):
        p = px.index.searchsorted(l, side="right") - 1
        if 0 < p < len(px) - 1:
            vals.append(ratio.iloc[p + 1])
    return float(np.nanmedian(vals)), len(vals)


def main():
    if not os.path.exists(BACKUP):
        shutil.copy2(AGRI_CALENDAR_FILE, BACKUP)
        print(f"Backup written: {BACKUP}")
    src = pd.ExcelFile(BACKUP)  # always rebuild from the untouched backup -> idempotent
    sheets, summary = {}, []
    for code, cfg in AGRI_CONFIG.items():
        df = pd.read_excel(src, sheet_name=cfg["calendar_sheet"])
        n0 = len(df)

        # Before filtering: confirm the price data distinguishes real from phantom months.
        is_real = df["Month"].isin(real_months(code))
        if (~is_real).any():
            r_med, _ = switch_ratio_at_ltd_plus_1(code, df[is_real])
            p_med, _ = switch_ratio_at_ltd_plus_1(code, df[~is_real])
            assert r_med < 1.0 < p_med, f"{code}: real {r_med:.2f} vs phantom {p_med:.2f}, price data does not support the filter"
            print(f"{code}: switch ratio real={r_med:.2f} phantom={p_med:.2f}")

        out = df[is_real].sort_values("LAST_TRADEABLE_DT").reset_index(drop=True)

        # Assertions on the filtered calendar.
        assert n0 - len(out) == EXPECTED_REMOVED[code], f"{code}: removed {n0 - len(out)}, expected {EXPECTED_REMOVED[code]}"
        assert set(out["Month"]) == real_months(code), f"{code}: month set {sorted(set(out['Month']))}"
        per_year = out.groupby("Year").size()
        assert (per_year == len(REAL_CYCLE[code])).all(), f"{code}: contracts per year {per_year[per_year != len(REAL_CYCLE[code])].to_dict()}"
        ltd = pd.to_datetime(out["LAST_TRADEABLE_DT"])
        dlv = pd.to_datetime(out["FUT_DLV_DT_LAST"])
        assert ltd.notna().all() and dlv.notna().all(), f"{code}: null dates"
        assert not ltd.duplicated().any(), f"{code}: duplicate LTD"
        assert ltd.is_monotonic_increasing, f"{code}: LTD not sorted"
        assert (ltd.dt.dayofweek < 5).all(), f"{code}: weekend LTD"
        assert (ltd <= dlv).all(), f"{code}: LTD after last delivery"
        assert out["Contract"].is_unique, f"{code}: duplicate contract id"
        # LTD must fall in/just before its delivery month (ICE Cotton/Coffee/Cocoa/OJ and CBOT
        # grains expire in or the month before delivery; allow 0-1 month lead).
        lead = (out["Year"] * 12 + out["Month"]) - (ltd.dt.year * 12 + ltd.dt.month)
        assert lead.between(0, 1).all(), f"{code}: LTD far from delivery month, leads={sorted(set(lead))}"

        sheets[cfg["calendar_sheet"]] = out
        summary.append((cfg["calendar_sheet"], len(out), ltd.min(), ltd.max(), n0 - len(out)))
        print(f"{code}: {n0} -> {len(out)} contracts ({n0 - len(out)} phantom removed)")

    readme = pd.DataFrame({"README": [
        "Agriculture Roll Calendar -- converted from Expiry_Calendars_Updated_2.xlsx (Agriculture sheet), then filtered to REAL exchange-listed contract months.",
        "Schema matches data/06-30/expiry_calendars_20260701.xlsx, for drop-in use with scripts/rolling_continuous.py's load_metal_calendar(). FUT_FIRST_TRADE_DT and FUT_DLV_DT_FIRST are blank (not in source). Only Contract/LAST_TRADEABLE_DT/FUT_DLV_DT_LAST are consumed by the roll engine.",
        "EXCLUDED: Sugar No.11 (SB) -- source corruption (off-cycle codes duplicate neighbour dates; 16 contracts share a stale 2024-09-13 date). Needs a clean re-pull.",
        "PHANTOM MONTHS REMOVED (rebuilt by scripts/build_agri_calendar_real_cycle.py): Bloomberg listed months the exchange does not list. Removed: Rough Rice 7 (Jun/Dec), Soybean Meal 22 (Jun), Cocoa 11 (Jun; J23 bad row already dropped earlier), Cotton 154 (all months except H/K/N/V/Z), Live Cattle 3 (2005 Jan/Mar/May). Original kept as Agri_Rolling_Calendar_pre_phantom_fix.xlsx.",
        "Real cycles: C/W/O/KC/CC HKNUZ; RR/JO FHKNUX; S FHKNQUX; BO/SM FHKNQUVZ; CT HKNVZ; FC FHJKQUVX; LC GJMQVZ; LH GJKMNQVZ.",
    ]})
    summ = pd.DataFrame(summary, columns=["Sheet", "Contracts", "Earliest LTD", "Latest LTD", "Phantoms removed"])
    with pd.ExcelWriter(AGRI_CALENDAR_FILE, engine="openpyxl") as xw:
        readme.to_excel(xw, sheet_name="README", index=False)
        summ.to_excel(xw, sheet_name="README", index=False, startrow=len(readme) + 2)
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name, index=False)

    # Re-read from disk and re-verify via the production loader.
    from rolling_continuous import get_metal_rolling_f1, load_metal_calendar
    for code, cfg in AGRI_CONFIG.items():
        cal = load_metal_calendar(AGRI_CALENDAR_FILE, cfg["calendar_sheet"])
        assert len(cal) == len(sheets[cfg["calendar_sheet"]]), f"{code}: loader row count mismatch"
        f1 = get_metal_rolling_f1(code, futures_file=AGRI_FUTURES_FILE, calendar_file=AGRI_CALENDAR_FILE,
                                  verbose=False, config=AGRI_CONFIG)
        assert f1["F1_continuous"].notna().all(), f"{code}: NaN in F1_continuous"
        r_med, n = switch_ratio_at_ltd_plus_1(code, pd.read_excel(AGRI_CALENDAR_FILE, sheet_name=cfg["calendar_sheet"]))
        assert r_med < 1.0, f"{code}: post-filter switch ratio {r_med:.2f}"
    print("All assertions passed; file re-read and rebuilt through the production roll builder.")


if __name__ == "__main__":
    main()
