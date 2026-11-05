"""UK Gas (ICE NBP) and Naphtha inputs from the 2026-11-03 Bloomberg drop, 2026-11-04.

PRICES: data/Prices_1103/New_Products_Futures_2006_to_date.xlsx (sheets "UK Gas - Price", "Naphtha - Price"; PX_LAST of the Bloomberg generics FN1..FN27 and KI1..KI24).
EXPIRY CALENDARS: data/Prices_1103/Expiry_Calendars_naphtha_UK_Gas.xlsx, Bloomberg's own historical expiry history (user-supplied 2026-11-04; sheets "UK Gas" 300 contracts
Jan-06..Dec-30 and "Naphtha" 288 contracts Jan-06..Dec-29, every row flagged OK). It replaced the calendar first derived from the exchange rule (kept below as `derived_*`
only to cross-check Bloomberg's dates; the two agree on 299 of 300 UK Gas and 286 of 288 Naphtha contracts, the differences being holiday handling).

UK GAS (ICE Futures Europe UK Natural Gas Futures, Bloomberg root FN, pence per therm): monthly contracts, lot = 1,000 therms a day over the delivery month (Bloomberg
"Contract Size" 28,000 to 31,000 therms, = 1,000 x days in the month); last trade = two business days before the first day of the delivery month, i.e. in the month before it.
NAPHTHA (Bloomberg KI generic, "KI.. COMB", USD per metric ton, monthly average-price swap on Platts Naphtha CIF NWE, 1,000 t a lot): the contract month is the pricing month,
last trade = last business day of that month (Bloomberg Last Trade Date = First Notice Date), the generic moves to the next month on the following business day.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil.easter import easter

ROOT = Path(__file__).resolve().parent.parent
DROP = ROOT / "data" / "Prices_1103" / "New_Products_Futures_2006_to_date.xlsx"
BBG_CAL = ROOT / "data" / "Prices_1103" / "Expiry_Calendars_naphtha_UK_Gas.xlsx"
MONTH_CODE = "FGHJKMNQUVXZ"
UKGAS_SHEET = "UK Gas NBP (ICE)"
UKGAS_CAL_SHEET = "FN - UK Gas NBP (ICE)"
NAPHTHA_SHEET = "Naphtha KI (COMB)"
NAPHTHA_CAL_SHEET = "KI - Naphtha CIF NWE (COMB)"
SRC_NOTE = "Bloomberg expiry history, Expiry_Calendars_naphtha&UK_Gas.xlsx (user-supplied 2026-11-04)"


# ───────────────────────── Bloomberg calendars (the ones in use) ─────────────────────────
def bloomberg_calendar(product: str) -> pd.DataFrame:
    """Bloomberg's expiry history for "UK Gas" or "Naphtha" in the schema load_metal_calendar() reads (Contract, LAST_TRADEABLE_DT, FUT_DLV_DT_LAST) plus the other Bloomberg fields.
    Checks: every row flagged OK, one row per contract month, contiguous months, last trade dates strictly increasing and not after the last delivery date."""
    raw = pd.read_excel(BBG_CAL, sheet_name=product, header=1).dropna(subset=["Ticker"])
    assert (raw["Date Check"] == "OK").all(), f"{product}: rows not flagged OK"
    cm = pd.to_datetime(raw["Contract Month"])
    raw = raw.assign(cm=cm).sort_values("cm").reset_index(drop=True)
    assert not raw["cm"].duplicated().any()
    assert (raw["cm"].diff().dropna().dt.days.between(28, 31)).all(), f"{product}: contract months not contiguous"
    ltd, fn, ldd = (pd.to_datetime(raw[c]) for c in ("Last Trade Date", "First Notice Date", "Last Delivery Date"))
    assert ltd.is_monotonic_increasing and ltd.is_unique and not ltd.isna().any() and not ldd.isna().any(), f"{product}: last trade dates not strictly increasing"
    assert (ltd <= ldd).all()
    contract = raw["Ticker"].str.replace(" COMB Comdty", "", regex=False).str.replace(" Comdty", "", regex=False)
    return pd.DataFrame({"Contract": contract, "Ticker": raw["Ticker"], "Year": raw["cm"].dt.year, "Month": raw["cm"].dt.month,
                         "Delivery": raw["cm"].dt.strftime("%b%y"), "LAST_TRADEABLE_DT": ltd, "FUT_NOTICE_FIRST": fn, "FUT_DLV_DT_LAST": ldd,
                         "Contract Size": raw["Contract Size"], "Currency": raw["Currency"], "Source": SRC_NOTE})


def uk_gas_calendar() -> pd.DataFrame:
    return bloomberg_calendar("UK Gas")


def naphtha_calendar() -> pd.DataFrame:
    return bloomberg_calendar("Naphtha")


# ───────────────────────── rule-derived calendars (cross-check only) ─────────────────────────
EXTRA_CLOSURES = ["2011-04-29", "2012-06-04", "2012-06-05", "2022-06-02", "2022-06-03", "2022-09-19", "2023-05-08"]


def uk_bank_holidays(y0: int, y1: int) -> set:
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


def derived_last_trade(product: str, years=range(2006, 2031)) -> pd.Series:
    """Last trade date from the exchange rule on a UK business-day calendar, indexed by (year, month). UK Gas: two business days before the delivery month;
    Naphtha: last business day of the pricing month. Used only to cross-check Bloomberg's calendar."""
    bd = business_days(); out = {}
    for y in years:
        for m in range(1, 13):
            d1 = pd.Timestamp(y, m, 1)
            out[(y, m)] = bd[bd < d1][-2] if product == "UK Gas" else bd[bd <= d1 + pd.offsets.MonthEnd(0)][-1]
    return pd.Series(out)


def compare_with_derived(product: str) -> pd.DataFrame:
    b = bloomberg_calendar(product).set_index(["Year", "Month"])["LAST_TRADEABLE_DT"]
    d = derived_last_trade(product).reindex(b.index)
    diff = pd.DataFrame({"bloomberg": b, "derived": d}); return diff[diff.bloomberg != diff.derived]


# ───────────────────────── prices ─────────────────────────
def read_drop(sheet: str) -> pd.DataFrame:
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
    ws.append([title] + [None] * (df.shape[1] - 1))
    ws.append([index_name] + list(df.columns))
    for t, row in df.iterrows():
        ws.append([t.to_pydatetime()] + [None if pd.isna(v) else float(v) for v in row.values])
        ws.cell(ws.max_row, 1).number_format = "yyyy-mm-dd"


def _write_calendar(path: Path, sheet: str, cal: pd.DataFrame):
    sheets = pd.read_excel(path, sheet_name=None) if path.exists() else {}
    sheets[sheet] = cal
    with pd.ExcelWriter(path) as xw:
        for k, v in sheets.items():
            v.to_excel(xw, sheet_name=k, index=False)


def add_ukgas(dst_dir, cutoff) -> dict:
    """UK Gas curve (Date, F1..F27 in the simple format) into dst_dir/Emissions_Futures_Updated.xlsx and Bloomberg's calendar into dst_dir/Emissions_Expiry_Calendars.xlsx.
    Rows after `cutoff` are not written."""
    import openpyxl
    dst = Path(dst_dir)
    px = drop_partial_last_rows(read_drop("UK Gas - Price"), "UK Gas").loc[:pd.Timestamp(cutoff)]
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
        rd.append(["UK Gas", f"ICE NBP, pence per therm, monthly; Bloomberg FN1..FN27 PX_LAST from data/Prices_1103/New_Products_Futures_2006_to_date.xlsx, to {px.index[-1].date()}; "
                              "calendar = Bloomberg expiry history (sheet FN - UK Gas NBP (ICE) of Emissions_Expiry_Calendars.xlsx)"])
    wb.save(fut)
    cal = uk_gas_calendar(); _write_calendar(dst / "Emissions_Expiry_Calendars.xlsx", UKGAS_CAL_SHEET, cal)
    return dict(rows=len(px), first=px.index[0].date(), last=px.index[-1].date(), contracts=len(cal))


def add_naphtha(dst_dir, cutoff) -> dict:
    """Naphtha curve (Date, F1..F24, simple format) into dst_dir/Naphtha_Futures_Updated.xlsx and Bloomberg's calendar into dst_dir/Naphtha_Expiry_Calendars.xlsx (both rewritten)."""
    import openpyxl
    dst = Path(dst_dir)
    px = drop_partial_last_rows(read_drop("Naphtha - Price"), "Naphtha").loc[:pd.Timestamp(cutoff)]
    assert px.index.is_monotonic_increasing and not px.index.has_duplicates
    wb = openpyxl.Workbook(); rd = wb.active; rd.title = "README"
    for r in [["Naphtha (Bloomberg KI generic, COMB) - Futures Curve", None], [None, None],
              ["Source", "data/Prices_1103/New_Products_Futures_2006_to_date.xlsx, sheet Naphtha - Price (PX_LAST of KI1..KI24)"],
              ["Cut", f"{px.index[-1].date()}"],
              ["Contract", "monthly average-price swap on Platts Naphtha CIF NWE, USD per metric ton, 1,000 t a lot; F1 is the month being priced (as for the NGL swaps)"],
              ["Calendar", "Naphtha_Expiry_Calendars.xlsx = Bloomberg expiry history (Expiry_Calendars_naphtha&UK_Gas.xlsx)"],
              ["Tenors", "F1-F4 are quoted every day; F14 and beyond on only 16 to 36% of days in 2024-2026; see research/configs/naphtha.py"],
              ["Format", "title row, Date,F1.. row, data from row 3 (same as the other price workbooks)"]]:
        rd.append(r)
    _write_sheet(wb, NAPHTHA_SHEET, f"{NAPHTHA_SHEET} -- Futures Curve (F1-F{px.shape[1]})", px)
    wb.save(dst / "Naphtha_Futures_Updated.xlsx")
    cal = naphtha_calendar()
    with pd.ExcelWriter(dst / "Naphtha_Expiry_Calendars.xlsx") as xw:
        cal.to_excel(xw, sheet_name=NAPHTHA_CAL_SHEET, index=False)
    return dict(rows=len(px), first=px.index[0].date(), last=px.index[-1].date(), contracts=len(cal))


if __name__ == "__main__":
    for p in ("UK Gas", "Naphtha"):
        d = compare_with_derived(p)
        print(f"{p}: Bloomberg vs rule-derived last trade dates differ on {len(d)} contracts"); print(d.to_string() if len(d) else "")
    for d, cut in (("data/Prices_1029_merged", "2026-10-29"), ("data/Prices_0930", "2026-09-30"), ("data/Prices_0924", "2026-09-23")):
        if d != "data/Prices_0924":
            print(d, "UK Gas", add_ukgas(ROOT / d, cut))
        print(d, "Naphtha", add_naphtha(ROOT / d, cut))
