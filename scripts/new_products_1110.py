"""Agriculture / Softs and CME natural gasoline (MMB) inputs from the 2026-11-10 Bloomberg drop (data/Prices_1110/), built 2026-11-10.

DROP FILES (data/Prices_1110/, copied hash-verified from Downloads\\Agri_11-Nov-...zip):
  Ag_Grains_Futures.xlsx, Ag_Oilseeds_Futures.xlsx, Ag_Livestock_Futures.xlsx, Ag_Softs_Futures.xlsx  PX_LAST / PX_VOLUME / OPEN_INT of Bloomberg generics F1..Fn, 2006-01-03 to 2026-11-10
  Ag_Expiry_Calendars.xlsx                                                                           every contract 2006 to 2030 (Last Trade Date, First Notice Date, Last Delivery Date)
  CME_Natural_Gasoline_Futures.xlsx                                                                  MMB (Mt Belvieu 5-decimal OPIS swap), CRP (legacy, data ends 2019-07), OGC (Conway, thin)

WHAT IS WRITTEN into every price folder (cut at the folder's data date, like UK Gas / Naphtha in new_products.py):
  Agri_Softs_Futures_1110.xlsx   one sheet per product, simple format (title row, Date,F1.. row, data from row 3): Corn CBOT, Wheat CBOT (SRW), Soybean CBOT, Live Cattle CME,
                                 Sugar No.11 ICE, Cocoa ICE, Coffee C ICE, Cotton No.2 ICE.  Sheet names equal the old Agriculture_Futures_Updated.xlsx names on purpose, so
                                 rolling_continuous.DATA_FIXES (Sugar F1 on 2025-06-30) applies unchanged.
  Agri_Softs_Calendar_1110.xlsx  one sheet per product in the schema load_metal_calendar() reads (Contract, LAST_TRADEABLE_DT, FUT_DLV_DT_LAST, ...); the 11-10 Bloomberg calendar.
  NGL_MMB_Futures.xlsx           sheet "Natural Gasoline MMB (CME)" (MMB1..MMB48 PX_LAST), VOL and OI sheets alongside.
Volume and open interest of the agri products stay in data/Prices_1110 (liquidity checks read them there).
  NGL_MMB_Expiry_Calendars.xlsx  sheet "MMB - Nat Gasoline Mt Belvieu": Bloomberg expiry history of MMB, eight ticker-collision rows (Morningstar fund, contract size 10, 2007-2009) removed.

CHECKS (assert, run on every build): one row per contract month, last trade dates strictly increasing, contract-month cycle equals the exchange cycle for 2006-2027, no duplicate dates,
trailing empty / partial rows removed, last date <= cutoff.  The calendars' last trade dates were also compared with the validated calendars already in use (identical on all 105+ overlapping contracts
per product, see ENGINE_CHANGELOG 2026-11-10).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from new_products import _write_sheet, drop_partial_last_rows   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DROP = ROOT / "data" / "Prices_1110"
MONTH_CODE = "FGHJKMNQUVXZ"

# product key -> (drop file, sheet prefix in the drop, calendar sheet / Product name in Ag_Expiry_Calendars.xlsx, output price sheet, output calendar sheet, expected contract-month cycle)
AGRI = {
    "C": ("Ag_Grains_Futures.xlsx", "Corn", "Grains", "Corn", "Corn CBOT", "C - Corn (CBOT)", "HKNUZ"),
    "W": ("Ag_Grains_Futures.xlsx", "Wheat SRW", "Grains", "Wheat SRW", "Wheat CBOT", "W - Wheat (CBOT)", "HKNUZ"),
    "S": ("Ag_Oilseeds_Futures.xlsx", "Soybeans", "Oilseeds", "Soybeans", "Soybean CBOT", "S - Soybean (CBOT)", "FHKNQUX"),
    "LC": ("Ag_Livestock_Futures.xlsx", "Live Cattle", "Livestock", "Live Cattle", "Live Cattle CME", "LC - Live Cattle (CME)", "GJMQVZ"),
    "SB": ("Ag_Softs_Futures.xlsx", "Sugar 11", "Softs", "Sugar 11", "Sugar No.11 ICE", "SB - Sugar No.11 (ICE)", "HKNV"),
    "CC": ("Ag_Softs_Futures.xlsx", "Cocoa", "Softs", "Cocoa", "Cocoa ICE", "CC - Cocoa (ICE)", "HKNUZ"),
    "KC": ("Ag_Softs_Futures.xlsx", "Coffee C", "Softs", "Coffee C", "Coffee C ICE", "KC - Coffee C (ICE)", "HKNUZ"),
    "CT": ("Ag_Softs_Futures.xlsx", "Cotton 2", "Softs", "Cotton 2", "Cotton No.2 ICE", "CT - Cotton No.2 (ICE)", "HKNVZ"),
}
MMB_PRICE_SHEET = "Natural Gasoline MMB (CME)"
MMB_CAL_SHEET = "MMB - Nat Gasoline Mt Belvieu"
SRC_NOTE = "Bloomberg expiry history, data/Prices_1110 (user-supplied 2026-11-10)"


_BOOKS: dict = {}


def _book(path: Path) -> dict:
    """Read each source workbook once (all sheets), not once per sheet."""
    if path not in _BOOKS:
        _BOOKS[path] = pd.read_excel(path, sheet_name=None, header=1)
    return _BOOKS[path]


def read_px(path: Path, sheet: str) -> pd.DataFrame:
    d = _book(path)[sheet].copy()
    d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
    d = d.dropna(subset=["Date"]).set_index("Date").sort_index()
    d = d.apply(pd.to_numeric, errors="coerce")
    d = d[d.notna().any(axis=1)]                       # all-empty trailing rows (MMB has an empty 2026-11-10 bar)
    assert d.index.is_monotonic_increasing and not d.index.has_duplicates, sheet
    return d


def agri_calendar(code: str) -> pd.DataFrame:
    f, _, cal_sheet, prod, _, _, cycle = AGRI[code]
    raw = pd.read_excel(DROP / "Ag_Expiry_Calendars.xlsx", sheet_name=cal_sheet, header=1)
    raw = raw[raw["Product"] == prod].copy()
    assert len(raw) > 90, (code, len(raw))
    cm = raw["Contract Month"].astype(str)
    raw["Month"] = cm.str[0].map(MONTH_CODE.index) + 1
    raw["Year"] = cm.str[1:].astype(int)
    raw = raw.sort_values(["Year", "Month"]).reset_index(drop=True)
    assert not raw[["Year", "Month"]].duplicated().any(), f"{code}: duplicate contract months"
    ltd = pd.to_datetime(raw["Last Trade Date"]); fnd = pd.to_datetime(raw["First Notice Date"]); ldd = pd.to_datetime(raw["Last Delivery Date"])
    assert not (ltd.isna().any() or ldd.isna().any()), f"{code}: missing dates"
    assert ltd.is_monotonic_increasing and ltd.is_unique, f"{code}: last trade dates not strictly increasing"
    # the exchange cycle: every contract month of 2006-2027 is one of the listed months, and every listed month of the period exists
    want = {MONTH_CODE.index(c) + 1 for c in cycle}
    for y in range(2006, 2028):
        got = set(raw.loc[raw["Year"] == y, "Month"])
        assert got == want, f"{code} {y}: contract months {sorted(got)} differ from the exchange cycle {sorted(want)}"
    contract = raw["Ticker"].astype(str).str.replace(" Comdty", "", regex=False).str.replace(" ", "", regex=False)
    return pd.DataFrame({"Contract": contract, "Ticker": raw["Ticker"], "Year": raw["Year"], "Month": raw["Month"],
                         "Delivery": pd.to_datetime(dict(year=raw["Year"], month=raw["Month"], day=1)).dt.strftime("%b%y"),
                         "LAST_TRADEABLE_DT": ltd, "FUT_NOTICE_FIRST": fnd, "FUT_DLV_DT_LAST": ldd,
                         "Contract Size": raw["Contract Size"], "Currency": raw["Currency"], "Source": SRC_NOTE})


def mmb_calendar() -> pd.DataFrame:
    h = pd.read_excel(DROP / "CME_Natural_Gasoline_Futures.xlsx", sheet_name="EXPIRY_HISTORY", header=1)
    m = h[h["Root"] == "MMB"].copy()
    real = (m["Contract Size"] == 42000) & m["Name"].astype(str).str.startswith("Mt Bl Nat Gas 5 D")
    assert (~real).sum() == 8 and (m.loc[~real, "Name"].astype(str).str.startswith("MStar")).all(), "MMB collision rows changed; inspect EXPIRY_HISTORY"
    m = m[real].copy()
    m["cm"] = pd.to_datetime(m["Contract Month"].astype(str) + "-01")
    m = m.sort_values("cm").reset_index(drop=True)
    assert m["cm"].is_unique and m["cm"].diff().dropna().dt.days.between(28, 31).all(), "MMB: contract months not contiguous"
    ltd = pd.to_datetime(m["Last Trade Date"]); fnd = pd.to_datetime(m["First Notice Date"]); ldd = pd.to_datetime(m["Last Delivery Date"])
    assert ltd.is_monotonic_increasing and ltd.is_unique and not ltd.isna().any() and (ltd <= ldd).all()
    lbd = m["cm"] + pd.offsets.BMonthEnd(0)
    assert ((lbd - ltd).dt.days.between(0, 3)).all(), "MMB: last trade date is not the (holiday-adjusted) last business day of the contract month"
    contract = m["Ticker"].astype(str).str.replace(" Comdty", "", regex=False)
    return pd.DataFrame({"Contract": contract, "Ticker": m["Ticker"], "Year": m["cm"].dt.year, "Month": m["cm"].dt.month, "Delivery": m["cm"].dt.strftime("%b%y"),
                         "LAST_TRADEABLE_DT": ltd, "FUT_NOTICE_FIRST": fnd, "FUT_DLV_DT_LAST": ldd, "Contract Size": m["Contract Size"],
                         "Currency": m["Currency"], "Source": SRC_NOTE})


def _new_wb(readme: list[list]):
    wb = openpyxl.Workbook(); rd = wb.active; rd.title = "README"
    for r in readme:
        rd.append(r)
    return wb


def add_agri_softs(dst_dir, cutoff) -> dict:
    """Write Agri_Softs_Futures_1110.xlsx and Agri_Softs_Calendar_1110.xlsx into dst_dir, every sheet cut at `cutoff` (volume and open interest are read from data/Prices_1110 by scripts/liquidity_cal2025_1110.py)."""
    dst = Path(dst_dir); cutoff = pd.Timestamp(cutoff)
    wb = _new_wb([["Agriculture and Softs (Bloomberg generic F1..Fn, PX_LAST) - 2026-11-10 drop", None], [None, None],
                  ["Source", "data/Prices_1110/Ag_*_Futures.xlsx (Bloomberg pull 2026-11-10 11:48-11:59)"], ["Cut", f"{cutoff.date()}"],
                  ["Products", "Corn, Wheat (CBOT SRW), Soybeans, Live Cattle (Agriculture bucket); Sugar No.11, Cocoa, Coffee C, Cotton No.2 (Softs bucket)"],
                  ["Calendar", "Agri_Softs_Calendar_1110.xlsx = Bloomberg expiry history of the same pull"],
                  ["Format", "title row, Date,F1.. row, data from row 3 (same as the other price workbooks)"]])
    cals, info = {}, {}
    for code, (f, prefix, _, _, sheet, cal_sheet, _) in AGRI.items():
        px = drop_partial_last_rows(read_px(DROP / f, prefix + " PX"), prefix).loc[:cutoff]
        _write_sheet(wb, sheet, f"{sheet} -- Futures Curve (F1-F{px.shape[1]})", px)
        cals[cal_sheet] = agri_calendar(code)
        info[code] = (px.index[0].date(), px.index[-1].date(), px.shape[1], len(cals[cal_sheet]))
    wb.save(dst / "Agri_Softs_Futures_1110.xlsx")
    with pd.ExcelWriter(dst / "Agri_Softs_Calendar_1110.xlsx") as xw:
        for k, v in cals.items():
            v.to_excel(xw, sheet_name=k, index=False)
    return info


def add_mmb(dst_dir, cutoff) -> dict:
    """Write NGL_MMB_Futures.xlsx (PX, VOL, OI) and NGL_MMB_Expiry_Calendars.xlsx into dst_dir, cut at `cutoff`."""
    dst = Path(dst_dir); cutoff = pd.Timestamp(cutoff)
    src = DROP / "CME_Natural_Gasoline_Futures.xlsx"
    px = read_px(src, "NGS_CME_MMB_PX").loc[:cutoff]
    wb = _new_wb([["CME natural gasoline, Mt Belvieu 5-decimal OPIS swap (Bloomberg root MMB) - Futures Curve", None], [None, None],
                  ["Source", "data/Prices_1110/CME_Natural_Gasoline_Futures.xlsx, sheets NGS_CME_MMB_PX / _VOL / _OI (Bloomberg generic MMB1..MMB48)"], ["Cut", f"{px.index[-1].date()}"],
                  ["Contract", "monthly cash-settled swap on the OPIS Mont Belvieu non-TET natural gasoline average, 42,000 gallons (1,000 bbl) a lot, USD per gallon; F1 is the month being priced "
                               "(as for the other NGL swaps and Naphtha): last trade = last business day of the pricing month, the generic moves to the next month the day after"],
                  ["Calendar", "NGL_MMB_Expiry_Calendars.xlsx = Bloomberg expiry history of MMB (261 contracts Oct-09 to Jun-31)"],
                  ["Format", "title row, Date,F1.. row, data from row 3"]])
    _write_sheet(wb, MMB_PRICE_SHEET, f"{MMB_PRICE_SHEET} -- Futures Curve (F1-F{px.shape[1]})", px)
    for kind, tag in (("VOL", "PX_VOLUME"), ("OI", "OPEN_INT")):
        _write_sheet(wb, f"MMB {kind}", f"MMB {tag}", read_px(src, f"NGS_CME_MMB_{kind}").loc[:cutoff])
    wb.save(dst / "NGL_MMB_Futures.xlsx")
    cal = mmb_calendar()
    with pd.ExcelWriter(dst / "NGL_MMB_Expiry_Calendars.xlsx") as xw:
        cal.to_excel(xw, sheet_name=MMB_CAL_SHEET, index=False)
    return dict(rows=len(px), first=px.index[0].date(), last=px.index[-1].date(), contracts=len(cal))


if __name__ == "__main__":
    for d, cut in (("data/Prices_1029_merged", "2026-10-29"), ("data/Prices_0930", "2026-09-30"), ("data/Prices_0924", "2026-09-23")):
        print(d, "Agri/Softs", add_agri_softs(ROOT / d, cut))
        print(d, "MMB", add_mmb(ROOT / d, cut))
