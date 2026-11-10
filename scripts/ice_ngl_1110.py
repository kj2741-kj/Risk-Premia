"""ICE NGL futures from the 2026-11-10 Bloomberg download (data/Prices_1110/ICE_NGL_Futures.xlsx; user-supplied from the Drive folder Agri_11-Nov), stored as engine-format files.

SOURCE SHEETS: <PRODUCT>_PX / _VOL / _OI (generic F1..Fn, daily from 2015-01-08; C5 natural gasoline Non-TET from 2018-02-19), EXPIRY_HISTORY (every monthly contract), EXPIRY_SNAPSHOT.
CONTRACTS (Bloomberg root, OPIS-settled monthly swaps, 1,000 barrels = 42,000 gallons a lot, USD per gallon):
  APT  C2 ethane, Mt Belvieu Non-TET          ASO  C3 propane, Mt Belvieu TET            ARA  C4 normal butane, Mt Belvieu Non-TET   AQC  C4 isobutane, Mt Belvieu Non-TET
  KLI  C5 natural gasoline, Mt Belvieu Non-TET   DRS  C5 natural gasoline, Mt Belvieu TET   DHW  C5 natural gasoline, Conway in-well

WRITTEN into every price folder (cut at the folder's data date):
  NGL_ICE_Futures.xlsx           README + one sheet per root "<ROOT> - <product>" with the PX_LAST curve in the simple format (title row, Date,F1.. row, data from row 3)
  NGL_ICE_Expiry_Calendars.xlsx  one sheet per root in the schema load_metal_calendar() reads (Contract, LAST_TRADEABLE_DT, FUT_DLV_DT_LAST, ...), Bloomberg expiry history

The ICE curves are stored only; no engine config reads them yet (the liquidity metric reads the raw download, scripts/liquidity_ngl_ice_1110.py).
Checks (assert): dates strictly increasing and unique, one calendar row per contract month, last trade dates strictly increasing, contract size 1,000, no all-empty rows kept.
"""
from __future__ import annotations

import sys
from pathlib import Path

import openpyxl
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from new_products import _write_sheet   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "Prices_1110" / "ICE_NGL_Futures.xlsx"
SRC_NOTE = "Bloomberg expiry history, data/Prices_1110/ICE_NGL_Futures.xlsx (user-supplied 2026-11-10)"
ICE = {   # sheet prefix -> (root, short name)
    "C2_ETH_APT": ("APT", "C2 ethane Mt Belvieu Non-TET"), "C3_PRO_ASO": ("ASO", "C3 propane Mt Belvieu TET"),
    "C4_NBU_ARA": ("ARA", "C4 normal butane Mt Belvieu Non-TET"), "C4_IBU_AQC": ("AQC", "C4 isobutane Mt Belvieu Non-TET"),
    "C5_NGS_KLI": ("KLI", "C5 natural gasoline Mt Belvieu Non-TET"), "C5_NGS_DRS": ("DRS", "C5 natural gasoline Mt Belvieu TET"),
    "C5_NGS_DHW": ("DHW", "C5 natural gasoline Conway in-well"),
}
_BOOK = {}


def book() -> dict:
    if not _BOOK:
        _BOOK.update(pd.read_excel(RAW, sheet_name=None, header=1))
    return _BOOK


def read_px(sheet: str) -> pd.DataFrame:
    d = book()[sheet].copy()
    d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
    d = d.dropna(subset=["Date"]).set_index("Date").sort_index().apply(pd.to_numeric, errors="coerce")
    d = d[d.notna().any(axis=1)]
    assert d.index.is_monotonic_increasing and not d.index.has_duplicates, sheet
    return d


def calendar(root: str) -> pd.DataFrame:
    h = book()["EXPIRY_HISTORY"]
    m = h[h["Root"] == root].copy()
    assert (m["Contract Size"] == 1000).all(), f"{root}: contract size"
    m["cm"] = pd.to_datetime(m["Contract Month"].astype(str) + "-01")
    m = m.sort_values("cm").reset_index(drop=True)
    assert m["cm"].is_unique, f"{root}: duplicate contract months"
    ltd = pd.to_datetime(m["Last Trade Date"]); fnd = pd.to_datetime(m["First Notice Date"]); ldd = pd.to_datetime(m["Last Delivery Date"])
    assert ltd.is_monotonic_increasing and ltd.is_unique and not ltd.isna().any() and not ldd.isna().any() and (ltd <= ldd).all(), f"{root}: last trade dates"
    contract = m["Ticker"].astype(str).str.replace(" Comdty", "", regex=False)
    return pd.DataFrame({"Contract": contract, "Ticker": m["Ticker"], "Year": m["cm"].dt.year, "Month": m["cm"].dt.month, "Delivery": m["cm"].dt.strftime("%b%y"),
                         "LAST_TRADEABLE_DT": ltd, "FUT_NOTICE_FIRST": fnd, "FUT_DLV_DT_LAST": ldd, "Contract Size": m["Contract Size"], "Currency": m["Currency"], "Source": SRC_NOTE})


def add_ice_ngl(dst_dir, cutoff) -> dict:
    dst = Path(dst_dir); cutoff = pd.Timestamp(cutoff)
    wb = openpyxl.Workbook(); rd = wb.active; rd.title = "README"
    for r in [["ICE NGL futures (Bloomberg generic F1..Fn, PX_LAST, USD per gallon) - 2026-11-10 download", None], [None, None],
              ["Source", "data/Prices_1110/ICE_NGL_Futures.xlsx (Bloomberg pull 2026-11-10 14:41)"], ["Cut", f"{cutoff.date()}"],
              ["Contracts", "OPIS-settled monthly swaps, 1,000 barrels (42,000 gallons) a lot; roots APT (ethane), ASO (propane), ARA (normal butane), AQC (isobutane), KLI / DRS / DHW (natural gasoline: Mt Belvieu Non-TET, Mt Belvieu TET, Conway)"],
              ["Convention", "as the CME NGL swaps: F1 is the month being priced (last trade = last business day of the month)"],
              ["Format", "title row, Date,F1.. row, data from row 3 (same as the other price workbooks); volume and open interest stay in the raw download"]]:
        rd.append(r)
    cals, info = {}, {}
    for pref, (root, name) in ICE.items():
        px = read_px(pref + "_PX").loc[:cutoff]
        sheet = f"{root} - {name}"[:31]
        _write_sheet(wb, sheet, f"{name} (ICE {root}) -- Futures Curve (F1-F{px.shape[1]})", px)
        cals[f"{root} - {name}"[:31]] = calendar(root)
        info[root] = (px.index[0].date(), px.index[-1].date(), px.shape[1], len(cals[f"{root} - {name}"[:31]]))
    wb.save(dst / "NGL_ICE_Futures.xlsx")
    with pd.ExcelWriter(dst / "NGL_ICE_Expiry_Calendars.xlsx") as xw:
        for k, v in cals.items():
            v.to_excel(xw, sheet_name=k, index=False)
    return info


if __name__ == "__main__":
    for d, cut in (("data/Prices_1029_merged", "2026-10-29"), ("data/Prices_0930", "2026-09-30"), ("data/Prices_0924", "2026-09-23")):
        print(d, add_ice_ngl(ROOT / d, cut), flush=True)
