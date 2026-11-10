"""Liquidity metric, Calendar 2025, for the four products added on 2026-11-10: Live Cattle (Agriculture), Cocoa and Cotton (Softs), CME Natural Gasoline MMB (NGL).
Same definitions as scripts/liquidity_cal2025.py (x = ADV of a 12-month strip * price * sigma * multiplier in USD of one-sigma daily risk traded per day, L = K/x with K = USD 1M,
NaN volume = 0, held-contract and F1-F3 ADV as sensitivities); the other rows of Analysis/Liquidity_Cal2025_results.csv are NOT recomputed, the four rows are appended (replaced if present).
Volume comes from the 2026-11-10 drop (data/Prices_1110, generic volume of F1..Fn); prices and the roll-adjusted series from the engine (Prices_1029_merged, Calendar 2025 only, so the cut does not matter).
Strip: the contracts listed in 12 months (Live Cattle F1-F6, Cocoa and Cotton F1-F5, MMB F1-F12), the convention of the other products (Corn F1-F5, Soybean F1-F7, Sugar F1-F4).
Multipliers: Live Cattle 40,000 lb (price USc/lb, factor 0.01); Cocoa 10 MT (USD/MT); Cotton 50,000 lb (USc/lb, 0.01); MMB 42,000 gal (USD/gal).
Run from the repo root: python scripts/liquidity_cal2025_1110.py"""
import os, sys, warnings; warnings.filterwarnings("ignore")
os.environ["RP_PRICES_DIR"] = "Prices_1029_merged"
sys.path[:0] = ["research", "research/configs", "scripts"]
import importlib
import numpy as np, pandas as pd
K = 1e6
OUT = "Analysis/Liquidity_Cal2025_results.csv"
D = "data/Prices_1110/"
# (module, product, bucket, volume file, volume sheet, multiplier, price->USD/unit factor, N contracts in a 12-month strip)
P = [("agri", "LiveCattle", "agri", "Ag_Livestock_Futures.xlsx", "Live Cattle VOL", 40000, 0.01, 6),
     ("softs", "Cocoa", "softs", "Ag_Softs_Futures.xlsx", "Cocoa VOL", 10, 1, 5),
     ("softs", "Cotton", "softs", "Ag_Softs_Futures.xlsx", "Cotton 2 VOL", 50000, 0.01, 5),
     ("mmb", "NatGasoline", "ngl", "CME_Natural_Gasoline_Futures.xlsx", "NGS_CME_MMB_VOL", 42000, 1, 12)]
rows = []
for mod, name, bucket, f, sh, m, pf, nstrip in P:
    raw = importlib.import_module(mod).load_f1_series_logret(name)
    r = raw.loc["2025-01-01":"2025-12-31"]
    sig = float(r["log_price"].diff().std())
    held_f2 = r["Phase"].isin(["Roll_LTD-5", "F2_Tracking"])
    px_held = np.where(held_f2, r["F2_raw"], r["F1_raw"]); pbar = float(np.nanmean(px_held)) * pf
    v = pd.read_excel(D + f, sheet_name=sh, header=1); v = v.rename(columns={v.columns[0]: "Date"}); v["Date"] = pd.to_datetime(v["Date"], errors="coerce")
    v = v.dropna(subset=["Date"]).set_index("Date").apply(pd.to_numeric, errors="coerce").reindex(r.index)
    allc = [c for c in v.columns if str(c).startswith("F")]
    tot = v[allc].sum(axis=1, min_count=1).fillna(0)
    strip = v[[f"F{k}" for k in range(1, nstrip + 1) if f"F{k}" in v.columns]].sum(axis=1, min_count=1).fillna(0)
    f13 = v[[c for c in ("F1", "F2", "F3") if c in v.columns]].sum(axis=1, min_count=1).fillna(0)
    if bucket == "ngl":
        held = pd.Series(np.where(held_f2, v["F3"].fillna(0), v["F2"].fillna(0)), index=r.index)
    else:
        held = pd.Series(np.where(held_f2, v["F2"].fillna(0), v["F1"].fillna(0)), index=r.index)
    c = pbar * sig * m
    rows.append(dict(bucket=bucket, product=name, n_days=len(r), strip=f"F1-F{nstrip}", price_usd_unit=pbar, sigma=sig, mult=m, risk_per_contract=c,
                     adv_strip=float(strip.mean()), adv_strip_med=float(strip.median()), adv_held=float(held.mean()), adv_f1f3=float(f13.mean()), adv_total=float(tot.mean()),
                     strip_share_of_total=float(strip.sum() / tot.sum()) if tot.sum() else np.nan, share_days_print=float((strip > 0).mean()),
                     x_strip=float(strip.mean()) * c / 1e6, x_strip_med=float(strip.median()) * c / 1e6, x_held=float(held.mean()) * c / 1e6, x_f1f3=float(f13.mean()) * c / 1e6, x_total=float(tot.mean()) * c / 1e6))
new = pd.DataFrame(rows)
new["N_contracts_for_K"] = K / new.risk_per_contract
new["L_strip"] = K / (new.x_strip * 1e6)
old = pd.read_csv(OUT)
old = old[~old["product"].isin(new["product"])]
out = pd.concat([old, new[old.columns]], ignore_index=True).sort_values("x_strip", ascending=False)
out.round(9).to_csv(OUT, index=False)
pd.set_option("display.width", 220)
print(new[["bucket", "product", "strip", "n_days", "price_usd_unit", "sigma", "adv_strip", "share_days_print", "x_strip", "L_strip"]].round(5).to_string(index=False))
