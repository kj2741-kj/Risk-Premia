"""UK Gas (ICE NBP) and Naphtha inputs from the 2026-11-03 Bloomberg drop (data/Prices_1103/New_Products_Futures_2006_to_date.xlsx), 2026-11-04.

The drop has prices, volume and open interest for both products but NO expiry calendar (its "Expiry Calendar" sheet says "No expiry data returned" and no other file in the
repo covers them). This module builds the calendars from the exchange rules and the engine inputs from the drop.

UK GAS (ICE Futures Europe UK Natural Gas Futures, Bloomberg root FN, pence per therm). Monthly contracts, 1,000 therms per day, delivered every day of the month, so one lot is
1,000 x days-in-month therms. Last trading day = two business days before the first calendar day of the delivery month (ICE contract spec 910), i.e. in the month before it,
the same rule as TTF. Business days = Monday-Friday minus UK bank holidays and the one-off closures (see EXTRA_CLOSURES). Validated 2026-11-04 against the Bloomberg generic series:
the generic F1 moves to the next contract on the first trading day after the rule's last trade date for the whole sample (median curve-shift statistic 0.34 on that day against
2.9 to 3.7 one to three business days earlier or later; 3.2 on an ordinary day); the same counting rule reproduces 290 of 341 Bloomberg TTF last trade dates, all 51 misses being
holiday-calendar differences between London and Amsterdam or contracts after 2029. FUT_DLV_DT_LAST = last day of the delivery month. FUT_NOTICE_FIRST and FUT_FIRST_TRADE_DT are left empty.
These dates are DERIVED, not Bloomberg's; a Bloomberg pull of LAST_TRADEABLE_DT for the FN contracts would replace them.

NAPHTHA (Bloomberg KI generic, USD per metric ton, a monthly average-price swap on Platts Naphtha CIF NWE; 1,000 t per lot on both ICE and CME). The contract month is the pricing
month, so F1 is the month being priced and its last trading day is the last business day of that month; the generic moves to the next month on the following business day (seen in
the drop: the open-interest column shifts on 2026-11-02 after the 2026-10-30 expiry). Weaker validation than UK Gas (median statistic 0.81 on the roll day against 1.1 to 1.5 at other lags).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil.easter import easter

ROOT = Path(__file__).resolve().parent.parent
DROP = ROOT / "data" / "Prices_1103" / "New_Products_Futures_2006_to_date.xlsx"
MONTH_CODE = "FGHJKMNQUVXZ"
UKGAS_SHEET = "UK Gas NBP (ICE)"
UKGAS_CAL_SHEET = "FN - UK Gas NBP (ICE)"
# One-off closures inside the data window (royal events); confirmed by missing rows in the drop (2011-04-29 wedding, 2012-06-04/05 Jubilee, 2022-06-02/03 Jubilee,
# 2022-09-19 state funeral, 2023-05-08 coronation)
EXTRA_CLOSURES = ["2011-04-29", "2012-06-04", "2012-06-05", "2022-06-02", "2022-06-03", "2022-09-19", "2023-05-08"]


def uk_bank_holidays(y0: int, y1: int) -> set:
    """England and Wales bank holidays y0..y1 (New Year, Good Friday, Easter Monday, early May, spring and summer bank holiday, Christmas, Boxing Day, with substitute days)."""
    H: set = set()

    def next_free(d):
        d = pd.Timestamp(d)
        while d.weekday() >= 5 or d in H:
            d += pd.Timedelta(days=1)
        return d

    def mon_on_or_after(y, m, day=1):
        d = pd.Timestamp(y, m, day)
        while d.weekday() != 0:
            d += pd.Timedelta(days=1)
        return d

    def last_mon(y, m):
        d = pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0)
        while d.weekday() != 0:
            d -= pd.Timedelta(days=1)
        return d

    for y in range(y0, y1 + 1):
        H.add(next_free(pd.Timestamp(y, 1, 1)))
        e = pd.Timestamp(easter(y))
        H.add(e - pd.Timedelta(days=2)); H.add(e + pd.Timedelta(days=1))
        H.add(mon_on_or_after(y, 5)); H.add(last_mon(y, 5)); H.add(last_mon(y, 8))
        H.add(next_free(pd.Timestamp(y, 12, 25))); H.add(next_free(pd.Timestamp(y, 12, 26)))
    return H


def business_days(start="2005-01-01", end="2031-12-31") -> pd.DatetimeIndex:
    hol = uk_bank_holidays(pd.Timestamp(start).year, pd.Timestamp(end).year) | {pd.Timestamp(x) for x in EXTRA_CLOSURES}
    return pd.DatetimeIndex(sorted(set(pd.bdate_range(start, end)) - hol))


def _months(first_year: int, last_year: int):
    return [(y, m) for y in range(first_year, last_year + 1) for m in range(1, 13)]


def uk_gas_calendar(first_year: int = 2006, last_year: int = 2030) -> pd.DataFrame:
    """Contract calendar in the schema load_metal_calendar() reads (Contract, LAST_TRADEABLE_DT, FUT_DLV_DT_LAST) plus Ticker/Year/Month/Delivery/FUT_DLV_DT_FIRST/Source."""
    bd = business_days()
    rows = []
    for y, m in _months(first_year, last_year):
        d1 = pd.Timestamp(y, m, 1)
        ltd = bd[bd < d1][-2]                                   # two business days before the first calendar day of the delivery month
        code = f"FN{MONTH_CODE[m - 1]}{y % 100:02d}"
        rows.append(dict(Contract=code, Ticker=f"{code} Comdty", Year=y, Month=m, Delivery=f"UK NBP {d1:%b%y}", LAST_TRADEABLE_DT=ltd,
                         FUT_NOTICE_FIRST=pd.NaT, FUT_FIRST_TRADE_DT=pd.NaT, FUT_DLV_DT_FIRST=d1, FUT_DLV_DT_LAST=d1 + pd.offsets.MonthEnd(0),
                         Source="DERIVED from ICE rule 910 (2 business days before the delivery month); not a Bloomberg field"))
    return pd.DataFrame(rows)


def naphtha_calendar(first_year: int = 2006, last_year: int = 2030) -> pd.DataFrame:
    bd = business_days()
    rows = []
    for y, m in _months(first_year, last_year):
        d1 = pd.Timestamp(y, m, 1); end = d1 + pd.offsets.MonthEnd(0)
        ltd = bd[bd <= end][-1]                                 # last business day of the pricing month
        code = f"KI{MONTH_CODE[m - 1]}{y % 100:02d}"
        rows.append(dict(Contract=code, Ticker=f"{code} Comdty", Year=y, Month=m, Delivery=f"Naphtha CIF NWE {d1:%b%y}", LAST_TRADEABLE_DT=ltd,
                         FUT_NOTICE_FIRST=pd.NaT, FUT_FIRST_TRADE_DT=pd.NaT, FUT_DLV_DT_FIRST=d1, FUT_DLV_DT_LAST=end,
                         Source="DERIVED (average-price swap, last business day of the pricing month); not a Bloomberg field"))
    return pd.DataFrame(rows)


def read_drop(sheet: str) -> pd.DataFrame:
    """One sheet of the drop (title row, Date/F1.. header row) as a Date-indexed frame."""
    d = pd.read_excel(DROP, sheet_name=sheet, header=1)
    d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
    d = d.dropna(subset=["Date"]).set_index("Date").sort_index()
    return d.apply(pd.to_numeric, errors="coerce")


def drop_partial_last_rows(px: pd.DataFrame, label: str) -> pd.DataFrame:
    """The drop was pulled intraday on 2026-11-03: a final row with a fraction of the usual tenors is not a settlement. Remove such trailing rows."""
    n = px.notna().sum(axis=1)
    ref = n.iloc[-60:-5].median()
    while len(px) and n.iloc[len(px) - 1] < 0.5 * ref:
        print(f"  {label}: dropped partial final row {px.index[-1].date()} ({n.iloc[len(px) - 1]} of ~{ref:.0f} tenors quoted)")
        px = px.iloc[:-1]
    return px


def _write_sheet(wb, name: str, title: str, df: pd.DataFrame, index_name: str = "Date"):
    if name in wb.sheetnames:
        del wb[name]
    ws = wb.create_sheet(name)
    ws.append([title] + [None] * (df.shape[1] - 1 if df.index.name else df.shape[1] - 1))
    ws.append([index_name] + list(df.columns))
    for t, row in df.iterrows():
        ws.append([t.to_pydatetime()] + [None if pd.isna(v) else float(v) for v in row.values])
        ws.cell(ws.max_row, 1).number_format = "yyyy-mm-dd"


def add_ukgas(dst_dir, cutoff: str | pd.Timestamp) -> dict:
    """Add the UK Gas curve (Date, F1..F27 in the simple format) to dst_dir/Emissions_Futures_Updated.xlsx and the derived calendar to dst_dir/Emissions_Expiry_Calendars.xlsx.
    Rows after `cutoff` are not written. Returns a small report dict."""
    import openpyxl
    dst = Path(dst_dir)
    px = read_drop("UK Gas - Price")
    px = drop_partial_last_rows(px, "UK Gas")
    px = px.loc[:pd.Timestamp(cutoff)]
    assert px.index.is_monotonic_increasing and not px.index.has_duplicates
    fut = dst / "Emissions_Futures_Updated.xlsx"
    wb = openpyxl.load_workbook(fut)
    _write_sheet(wb, UKGAS_SHEET, f"{UKGAS_SHEET} -- Futures Curve (F1-F{px.shape[1]})", px)
    if "README" in wb.sheetnames:
        rd = wb["README"]
        for r in list(rd.iter_rows(min_row=1, max_row=rd.max_row)):
            if r[0].value == "UK Gas":
                rd.delete_rows(r[0].row, 1)
                break
        rd.append(["UK Gas", f"ICE NBP, pence per therm, monthly; Bloomberg FN1..FN27 PX_LAST from data/Prices_1103/New_Products_Futures_2006_to_date.xlsx, to {px.index[-1].date()} "
                              "(the partial 2026-11-03 row dropped); calendar derived from the ICE rule, see scripts/new_products.py"])
    wb.save(fut)
    cal = uk_gas_calendar()
    calf = dst / "Emissions_Expiry_Calendars.xlsx"
    sheets = pd.read_excel(calf, sheet_name=None)
    sheets[UKGAS_CAL_SHEET] = cal
    with pd.ExcelWriter(calf) as xw:
        for k, v in sheets.items():
            v.to_excel(xw, sheet_name=k, index=False)
    return dict(rows=len(px), first=px.index[0].date(), last=px.index[-1].date(), contracts=len(cal))


def write_naphtha_inputs(dst_dir) -> dict:
    """Engine-format workbook + derived calendar for Naphtha (analysis only, not wired into any bucket): dst_dir/Naphtha_Futures.xlsx and dst_dir/Naphtha_Expiry_Calendar.xlsx."""
    import openpyxl
    dst = Path(dst_dir); dst.mkdir(parents=True, exist_ok=True)
    px = drop_partial_last_rows(read_drop("Naphtha - Price"), "Naphtha")
    wb = openpyxl.Workbook(); wb.active.title = "README"
    wb["README"].append(["Naphtha (Bloomberg KI generic, USD/t, monthly average-price swap, Platts CIF NWE) - engine-format copy of the 2026-11-03 drop"])
    _write_sheet(wb, "Naphtha KI", f"Naphtha KI -- Futures Curve (F1-F{px.shape[1]})", px)
    wb.save(dst / "Naphtha_Futures.xlsx")
    cal = naphtha_calendar()
    with pd.ExcelWriter(dst / "Naphtha_Expiry_Calendar.xlsx") as xw:
        cal.to_excel(xw, sheet_name="KI - Naphtha CIF NWE", index=False)
    return dict(rows=len(px), first=px.index[0].date(), last=px.index[-1].date())


if __name__ == "__main__":
    import sys
    for d, cut in (("data/Prices_1029_merged", "2026-10-29"), ("data/Prices_0930", "2026-09-30")):
        print(d, add_ukgas(ROOT / d, cut))
    print("naphtha", write_naphtha_inputs(ROOT / "data" / "Prices_1103" / "derived"))
