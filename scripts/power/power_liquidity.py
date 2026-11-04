"""Liquidity of the US Power series, Calendar 2025 (2026-11-04): same metric and method as scripts/liquidity_cal2025.py (x = ADV x mean price x sigma x multiplier, USD millions of one-sigma daily risk
traded per day; L = K / x with K = USD 1 million), computed for the six ICE series. 2025 data only. Writes Analysis/Power_Liquidity_Cal2025_results.csv.
ADV = mean over the 2025 trading days of the volume summed over F1-F12 (the twelve monthly contracts; a day without a print counts as zero; open interest is never used).
Price = mean 2025 unadjusted price of the contract held (F1 before the roll day, F2 from it to the last trade date). Sigma = std of the daily log returns of the roll-adjusted series over 2025.
Multiplier = mean contract size in MWh of the twelve 2025 delivery months, from the calendar (checked on ice.com 2026-11-04: all six monthly contracts are 1 MW, i.e. 1 MW for every hour of the contract period; the daily contracts are 800 MWh peak / 50 MWh off-peak) (the size field is a placeholder 1 for far contracts and a legacy 800 / 50 before 2018; 2025 months are 304-368 MWh peak,
352-417 off-peak). The four CME series have no 2025 data: their volume since launch is reported against ICE over the same dates.
Run from the repo root:  python scripts/power/power_liquidity.py"""
import os, sys
os.environ.setdefault("RP_PRICES_DIR", "Prices_0930")
sys.path[:0] = ["research", "research/configs", "scripts"]
import numpy as np, pandas as pd
import power as pw

K = 1e6
C = pd.concat([pd.read_excel(pw.CALENDAR_FILE, sheet_name=c) for c in pw.METAL_CODES.values()], keys=list(pw.METAL_CODES.values()), names=["root"]).reset_index(level=0)
C["size"] = pd.to_numeric(C["CONTRACT_SIZE"], errors="coerce")
rows = []
for p in pw.PRODUCTS:
    raw = pw.load_f1_series_logret(p)
    r = raw.loc["2025-01-01":"2025-12-31"]
    sig = float(r["log_price"].diff().std())
    held_f2 = r["Phase"].isin(["Roll_LTD-5", "F2_Tracking"])
    pbar = float(np.nanmean(np.where(held_f2, r["F2_raw"], r["F1_raw"])))
    v = pw.load_sheet(p, "VOL").reindex(r.index)
    oi = pw.load_sheet(p, "OI").reindex(r.index)
    strip = v[[f"F{k}" for k in range(1, 13)]].sum(axis=1, min_count=1).fillna(0)
    tot = v.sum(axis=1, min_count=1).fillna(0)
    held = pd.Series(np.where(held_f2, v["F2"].fillna(0), v["F1"].fillna(0)), index=r.index)
    sz = C[(C.root == pw.METAL_CODES[p]) & (C["CONTRACT_MONTH"].astype(str).str[:4] == "2025")]["size"]
    m = float(sz.mean())
    c = pbar * sig * m
    rows.append(dict(product=p, n_days=len(r), strip="F1-F12", price_usd_mwh=pbar, sigma=sig, mult_mwh=m, risk_per_contract=c, adv_strip=float(strip.mean()), adv_strip_med=float(strip.median()),
                     adv_held=float(held.mean()), adv_total=float(tot.mean()), strip_share_of_total=float(strip.sum() / tot.sum()), share_days_print=float((strip > 0).mean()),
                     oi_strip_mean=float(oi[[f"F{k}" for k in range(1, 13)]].sum(axis=1, min_count=1).mean()),
                     x_strip=float(strip.mean()) * c / 1e6, x_held=float(held.mean()) * c / 1e6, mwh_per_day=float(strip.mean()) * m))
d = pd.DataFrame(rows)
d["N_contracts_for_K"] = K / d.risk_per_contract
d["L_strip"] = K / (d.x_strip * 1e6)
d = d.sort_values("x_strip", ascending=False)
d.round(5).to_csv(os.path.join("Analysis", "Power_Liquidity_Cal2025_results.csv"), index=False)
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40)
print(d[["product", "n_days", "price_usd_mwh", "sigma", "mult_mwh", "risk_per_contract", "adv_strip", "adv_strip_med", "share_days_print", "strip_share_of_total", "x_strip", "x_held", "L_strip"]].round(4).to_string(index=False))

# CME series: no 2025 data; volume since launch against ICE over the same dates
print("\nCME (volume since launch, lots/day over F1-F12) against the ICE series of the same hub and profile over the same dates:")
ice_of = {"PJM_Peak_CME": "PJM_Peak", "PJM_OffPeak_CME": "PJM_OffPeak", "ERCOT_Peak_CME": "ERCOT_Peak", "ERCOT_OffPeak_CME": "ERCOT_OffPeak"}
crow = []
for k, (file, prefix, root) in pw.CME_SERIES.items():
    v = pw.load_sheet(k, "VOL", file=file, prefix=prefix)
    a = v.index.min()
    cme = v[[f"F{j}" for j in range(1, 13) if f"F{j}" in v.columns]].sum(axis=1, min_count=1).fillna(0).loc[a:"2026-11-02"]
    iv = pw.load_sheet(ice_of[k], "VOL").reindex(cme.index)
    ice = iv[[f"F{j}" for j in range(1, 13)]].sum(axis=1, min_count=1).fillna(0)
    px = pw.load_sheet(k, "PX", file=file, prefix=prefix)
    crow.append(dict(series=k, first_date=str(a.date()), days=len(cme), cme_adv_lots=round(float(cme.mean()), 1), cme_share_days_print=round(float((cme > 0).mean()), 3),
                     ice_adv_lots_same_dates=round(float(ice.mean()), 1), cme_to_ice=round(float(cme.mean() / ice.mean()), 3), cme_last_20d_adv=round(float(cme.tail(20).mean()), 1)))
cd = pd.DataFrame(crow); print(cd.to_string(index=False)); cd.to_csv(os.path.join("Analysis", "Power_Liquidity_CME_since_launch.csv"), index=False)
