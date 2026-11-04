"""Builds data/Emissions_1029/Power_Expiry_Calendars.xlsx (2026-11-04) from the EXPIRY_HISTORY sheets of PJM_Power_Futures.xlsx and US_Power_Futures.xlsx.
One sheet per Bloomberg root, in the format scripts/rolling_continuous.load_metal_calendar reads: Contract (ticker), LAST_TRADEABLE_DT (Last Trade Date),
FUT_DLV_DT_LAST (Last Delivery Date), plus the first-trade date, contract month and contract size for reference.
Run from the repo root:  python scripts/make_power_calendars.py"""
import os
import pandas as pd

D = os.path.join("data", "Emissions_1029")
OUT = os.path.join(D, "Power_Expiry_Calendars.xlsx")
FILES = ["PJM_Power_Futures.xlsx", "US_Power_Futures.xlsx"]

frames = []
for f in FILES:
    raw = pd.read_excel(os.path.join(D, f), sheet_name="EXPIRY_HISTORY", header=None)
    hdr = raw.iloc[1].tolist()
    df = raw.iloc[2:].copy()
    df.columns = hdr
    df["source_file"] = f
    frames.append(df)
cal = pd.concat(frames, ignore_index=True)
for c in ("First Trade Date", "Last Trade Date", "First Notice Date", "First Delivery Date", "Last Delivery Date"):
    cal[c] = pd.to_datetime(cal[c], errors="coerce")
cal = cal.dropna(subset=["Last Trade Date", "Last Delivery Date"])

with pd.ExcelWriter(OUT) as xw:
    for root, g in cal.groupby("Root"):
        g = g.sort_values("Last Trade Date")
        out = pd.DataFrame({"Contract": g["Ticker"].values, "LAST_TRADEABLE_DT": g["Last Trade Date"].values,
                            "FUT_DLV_DT_LAST": g["Last Delivery Date"].values, "FIRST_TRADE_DT": g["First Trade Date"].values,
                            "CONTRACT_MONTH": g["Contract Month"].astype(str).values, "CONTRACT_SIZE": g["Contract Size"].values,
                            "PRODUCT": g["Product"].values})
        out.to_excel(xw, sheet_name=str(root), index=False)
        print(root, len(out), out["LAST_TRADEABLE_DT"].min().date(), "->", out["LAST_TRADEABLE_DT"].max().date())
print("wrote", OUT)
