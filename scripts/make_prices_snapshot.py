"""Builds data/Prices_0930/ (2026-10-31): the research-dashboard data snapshot.

Source: data/Prices_1029_merged (Prices_0924 history extended with the 29-Oct pull, NGL labels corrected) and data/Emissions_1029 (TTF, Henry Hub, EUA).
Every sheet is cut at CUTOFF (default 2026-09-30, the research cutoff chosen by the user although data run to 10-28/29). Nothing is altered except the cut;
the EUA files are reshaped into the layout the engine already reads. Run from the repo root:
  python scripts/make_prices_snapshot.py [YYYY-MM-DD]             -> data/Prices_0930 (everything, cut at the date)
  python scripts/make_prices_snapshot.py --emissions-only          -> adds ONLY the EUA/TTF files, uncut, to data/Prices_1029_merged (the Streamlit apps' folder,
                                                                      latest data in the files; written 2026-10-31 when the Streamlit apps were realigned)
Use it by setting RP_PRICES_DIR=Prices_0930 (scripts/rolling_continuous.py); the Streamlit apps keep reading Prices_0924 unless that is set.

Files written to data/Prices_0930/:
  - the six price workbooks, both volume workbooks and the seven calendar files of Prices_1029_merged (price/volume cut at CUTOFF, calendars copied);
  - Emissions_Futures_Updated.xlsx: sheets "EUA Carbon (ICE Endex)" (EUA_PX, F1..F13) and "TTF Natural Gas (ICE Endex)" (TTF_PX, F1..F72) of Gas_Power_Emissions_Futures.xlsx in the
    simple format (title row, Date,F1.. row, data from row 3);
  - Emissions_Expiry_Calendars.xlsx: sheets "MO - EUA (ICE Endex)" and "TZT - TTF Gas (ICE Endex)" = the EUA and TTF sheets of Gas_Power_Emissions_Expiry_History.xlsx in the calendar schema
    load_metal_calendar() reads (Contract, LAST_TRADEABLE_DT = Last Trade Date, FUT_DLV_DT_LAST = Last Delivery Date);
  - Gas_Power_Emissions_Futures.xlsx: the full TTF / Henry Hub / EUA price-volume-OI workbook cut at CUTOFF (volume and open interest for the liquidity check).
"""
import sys
import shutil
import datetime as dt
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "Prices_1029_merged"
EMI = ROOT / "data" / "Emissions_1029"
DST = ROOT / "data" / "Prices_0930"
EMISSIONS_ONLY = "--emissions-only" in sys.argv
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
CUTOFF = pd.Timestamp("2262-01-01") if EMISSIONS_ONLY else pd.Timestamp(_args[0] if _args else "2026-09-30")   # emissions-only: no cut
if EMISSIONS_ONLY:
    DST = ROOT / "data" / "Prices_1029_merged"

PRICE_FILES = ["Energy_Futures_Updated.xlsx", "Precious_Metals_Futures_Updated.xlsx", "Metals_Futures_Curve_Updated.xlsx", "Metals_Cash_3M_Updated.xlsx",
               "Agriculture_Futures_Updated.xlsx", "NGL_Futures_Updated_labels_corrected.xlsx",
               "Volume_OpenInterest_F1F3_Updated.xlsx", "Volume_OI_FullCurve_20240102_20261029.xlsx"]
CAL_FILES = ["Expiry_Calendars_Updated.xlsx", "Expiry_Calendars_Updated_1.xlsx", "Expiry_Calendars_Updated_2.xlsx", "Agri_expiry.xlsx",
             "Agri_Expiry_Calendar_Updated.xlsx", "Agri_Rolling_Calendar.xlsx", "Agri_Rolling_Calendar_bloomberg_matched.xlsx"]


def cut_workbook(wb, cutoff):
    """Delete every data row dated after cutoff, in every sheet whose column A holds dates. Returns {sheet: rows removed}."""
    removed = {}
    for ws in wb.worksheets:
        first_bad, last_date, prev = None, None, None
        for i, (a,) in enumerate(ws.iter_rows(min_col=1, max_col=1, values_only=True), start=1):
            if isinstance(a, (dt.datetime, dt.date)):
                d = pd.Timestamp(a)
                assert prev is None or d >= prev, f"{ws.title}: dates not ascending at row {i}"
                prev = d
                if d > cutoff and first_bad is None:
                    first_bad = i
        if first_bad is not None:
            n = ws.max_row - first_bad + 1
            ws.delete_rows(first_bad, n)
            removed[ws.title] = n
    return removed


def main():
    if not EMISSIONS_ONLY:
        DST.mkdir(exist_ok=False)
    for f in ([] if EMISSIONS_ONLY else CAL_FILES):
        shutil.copy(SRC / f, DST / f)
    for f in ([] if EMISSIONS_ONLY else PRICE_FILES):
        wb = openpyxl.load_workbook(SRC / f)
        rem = cut_workbook(wb, CUTOFF)
        rd = wb["README"] if "README" in wb.sheetnames else None
        if rd is not None:
            rd.append([]); rd.append(["CUT 2026-10-31", f"every sheet cut at {CUTOFF.date()} (scripts/make_prices_snapshot.py); source data/Prices_1029_merged"])
        if f.startswith("Volume_OI_FullCurve"):                       # keep the Index sheet's "last date with data" consistent with the cut
            ix = wb["Index"]
            for row in ix.iter_rows(min_row=2):
                if row[0].value in wb.sheetnames:
                    ws = wb[row[0].value]
                    last = None
                    for r in ws.iter_rows(min_row=2, values_only=True):
                        if any(v is not None for v in r[1:]):
                            last = r[0]
                    row[7].value = last.strftime("%Y-%m-%d") if last is not None else None
        wb.save(DST / f)
        print(f"{f}: removed rows after {CUTOFF.date()} in {len(rem)} sheets (max {max(rem.values()) if rem else 0})", flush=True)

    # --- emissions: EUA and TTF price curves in the simple format ---
    wbE = openpyxl.load_workbook(EMI / "Gas_Power_Emissions_Futures.xlsx")
    rem = cut_workbook(wbE, CUTOFF)
    out = openpyxl.Workbook()
    rd = out.active; rd.title = "README"
    for r in [["EUA carbon and TTF gas (ICE Endex) - Futures Curves", None], [None, None],
              ["Source", "data/Emissions_1029/Gas_Power_Emissions_Futures.xlsx, sheets EUA_PX and TTF_PX (Bloomberg generic MO1..MO13 and TZT1..TZT72, PX_LAST)"],
              ["Cut", "none (latest data in the file)" if EMISSIONS_ONLY else f"{CUTOFF.date()} (scripts/make_prices_snapshot.py)"],
              ["EUA", "Quarterly (Mar/Jun/Sep/Dec) from 2006, Dec only for 2005; Phase I contracts (to Mar-08) trade near zero, see config emissions.py"],
              ["TTF", "Monthly contracts, EUR/MWh; tenors beyond F3 are quoted only from 2012-10 (F6) and 2013-10 (F7+), see config emissions.py"],
              ["Format", "title row, Date,F1.. row, data from row 3 (same as Energy_Futures_Updated.xlsx)"]]:
        rd.append(r)
    for src, name in (("EUA_PX", "EUA Carbon (ICE Endex)"), ("TTF_PX", "TTF Natural Gas (ICE Endex)")):
        rows = [r for r in wbE[src].iter_rows(values_only=True)]
        hdr_i = next(i for i, r in enumerate(rows) if r[0] == "Date")
        header = [c for c in rows[hdr_i] if c is not None]
        data = [r[:len(header)] for r in rows[hdr_i + 1:] if isinstance(r[0], (dt.datetime, dt.date))]
        w = out.create_sheet(name)
        w.append([f"{name} -- Futures Curve (F1-F{len(header) - 1})"] + [None] * (len(header) - 1))
        w.append(header)
        for r in data:
            w.append(list(r)); w.cell(w.max_row, 1).number_format = "yyyy-mm-dd"
        print(f"{name}: {len(data)} rows, {data[0][0]:%Y-%m-%d} .. {data[-1][0]:%Y-%m-%d}", flush=True)
    out.save(DST / "Emissions_Futures_Updated.xlsx")
    if not EMISSIONS_ONLY:
        wbE.save(DST / "Gas_Power_Emissions_Futures.xlsx")
        print(f"Gas_Power_Emissions_Futures.xlsx: cut {len(rem)} sheets", flush=True)

    # --- emissions: EUA and TTF calendars in the load_metal_calendar schema ---
    with pd.ExcelWriter(DST / "Emissions_Expiry_Calendars.xlsx") as xw:
        for sheet, name in (("EUA", "MO - EUA (ICE Endex)"), ("TTF", "TZT - TTF Gas (ICE Endex)")):
            hist = pd.read_excel(EMI / "Gas_Power_Emissions_Expiry_History.xlsx", sheet_name=sheet, header=1)
            cal = pd.DataFrame({
                "Contract": hist["Ticker"].str.replace(" Comdty", "", regex=False),
                "Ticker": hist["Ticker"], "Year": pd.to_datetime(hist["Contract Month"]).dt.year, "Month": pd.to_datetime(hist["Contract Month"]).dt.month,
                "Delivery": hist["Name"],
                "LAST_TRADEABLE_DT": pd.to_datetime(hist["Last Trade Date"]), "FUT_NOTICE_FIRST": pd.to_datetime(hist["First Notice Date"]),
                "FUT_FIRST_TRADE_DT": pd.to_datetime(hist["First Trade Date"]), "FUT_DLV_DT_FIRST": pd.to_datetime(hist["First Delivery Date"]),
                "FUT_DLV_DT_LAST": pd.to_datetime(hist["Last Delivery Date"])})
            cal.to_excel(xw, sheet_name=name, index=False)
            print(f"Emissions_Expiry_Calendars.xlsx [{name}]: {len(cal)} contracts {cal.Contract.iloc[0]} .. {cal.Contract.iloc[-1]}", flush=True)


if __name__ == "__main__":
    main()
