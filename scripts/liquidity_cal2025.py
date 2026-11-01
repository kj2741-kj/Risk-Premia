"""Liquidity metric, Calendar 2025 (one-time snapshot), 26 products -> Analysis/Liquidity_Cal2025_results.csv.
x = ADV * P * sigma * multiplier = USD of one-sigma daily risk traded per day (Prof. Bouchouev's denominator); K/x with K = $1M.
ADV = mean over 2025 trading days of volume summed over the contracts of a 12-month strip (F1-F12 for monthly products, fewer for quarterly or
bi-monthly chains, see P below); NaN volume = 0. NGL is the CME half only (ICE to be added). Held-contract and F1-F3 ADV are kept as sensitivities.
Run from the repo root: python scripts/liquidity_cal2025.py. Needs data/Prices_1029 (volume), data/Prices_1029_merged (prices), data/Emissions_1029."""
import os, sys, warnings; warnings.filterwarnings("ignore")
os.environ["RP_PRICES_DIR"] = "Prices_1029_merged"
sys.path[:0] = ["research", "research/configs", "scripts"]   # run from the repo root
import importlib
import numpy as np, pandas as pd
V = "data/Prices_1029/"
EUR = 1.1300      # ECB euro reference rate, mean of 255 daily fixes in 2025 (data-api.ecb.europa.eu)
K = 1e6           # USD of 1-sigma daily risk per product (changed from 10e6 on 2026-11-01; the ranking by x does not depend on K)
OUT = "Analysis/Liquidity_Cal2025_results.csv"
# (module, engine product name, bucket, volume file kind, root, lot multiplier, price->USD/unit factor, fx, N contracts in a 12-month strip)
P = [
 ("metals", "Copper", "metals", "LME", "LP", 25, 1, 1, 12), ("metals", "Aluminium", "metals", "LME", "LA", 25, 1, 1, 12), ("metals", "Lead", "metals", "LME", "LL", 25, 1, 1, 12), ("metals", "Zinc", "metals", "LME", "LX", 25, 1, 1, 12),
 ("energy", "WTI", "petroleum", "ENERGY", "CL", 1000, 1, 1, 12), ("energy", "Brent", "petroleum", "ENERGY", "CO", 1000, 1, 1, 12), ("energy", "RBOB", "petroleum", "ENERGY", "XB", 42000, 0.01, 1, 12),
 ("energy", "HeatingOil", "petroleum", "ENERGY", "HO", 42000, 0.01, 1, 12), ("energy", "SingaporeGasoil", "petroleum", "ENERGY", "QS", 100, 1, 1, 12),
 ("energy", "NatGas", "pen", "ENERGY", "NG", 10000, 1, 1, 12), ("emissions", "TTF", "pen", "EMI", "TTF", 730.5, 1, EUR, 12), ("emissions", "EUA", "pen", "EMI", "EUA", 1000, 1, EUR, 4),
 ("ngl", "Ethane", "ngl", "NGL", "CAP", 42000, 1, 1, 12), ("ngl", "Propane", "ngl", "NGL", "BAP", 42000, 1, 1, 12), ("ngl", "Butane", "ngl", "NGL", "DAE", 42000, 1, 1, 12), ("ngl", "Isobutane", "ngl", "NGL", "IBD", 42000, 1, 1, 12),
 ("precious", "Gold", "precious", "PRECIOUS", "GC", 100, 1, 1, 6), ("precious", "Silver", "precious", "PRECIOUS", "SI", 5000, 1, 1, 5), ("precious", "Platinum", "precious", "PRECIOUS", "PL", 50, 1, 1, 4), ("precious", "Palladium", "precious", "PRECIOUS", "PA", 100, 1, 1, 4),
 ("agri", "Corn", "agri", "AGRI", "C", 5000, 0.01, 1, 5), ("agri", "Wheat", "agri", "AGRI", "W", 5000, 0.01, 1, 5), ("agri", "Soybean", "agri", "AGRI", "S", 5000, 0.01, 1, 7),
 ("agri", "SoybeanOil", "agri", "AGRI", "BO", 60000, 0.01, 1, 8), ("agri", "Coffee", "agri", "AGRI", "KC", 37500, 0.01, 1, 5), ("agri", "Sugar", "agri", "AGRI", "SB", 112000, 0.01, 1, 4),
]


def vol_sheet(kind, root):
    if kind == "EMI":
        d = pd.read_excel("data/Emissions_1029/Gas_Power_Emissions_Futures.xlsx", sheet_name=f"{root}_VOL", header=1)
    else:
        d = pd.read_excel(V + f"Volume_{kind}.xlsx", sheet_name=f"{root} Vol", header=0)
    d = d.rename(columns={d.columns[0]: "Date"}); d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
    return d.dropna(subset=["Date"]).set_index("Date").apply(pd.to_numeric, errors="coerce")


rows = []
for mod, name, bucket, kind, root, m, pf, fx, nstrip in P:
    cfg = importlib.import_module(mod); raw = cfg.load_f1_series_logret(name)
    r = raw.loc["2025-01-01":"2025-12-31"]
    sig = float(r["log_price"].diff().std())
    held_f2 = r["Phase"].isin(["Roll_LTD-5", "F2_Tracking"])
    px_held = np.where(held_f2, r["F2_raw"], r["F1_raw"]); pbar = float(np.nanmean(px_held)) * pf * fx
    v = vol_sheet(kind, root).reindex(r.index)
    allc = [c for c in v.columns if str(c).startswith("F")]
    tot = v[allc].sum(axis=1, min_count=1).fillna(0)
    strip_cols = [f"F{k}" for k in range(1, nstrip + 1) if f"F{k}" in v.columns]
    strip = v[strip_cols].sum(axis=1, min_count=1).fillna(0)
    f13 = v[[c for c in ("F1", "F2", "F3") if c in v.columns]].sum(axis=1, min_count=1).fillna(0)
    if bucket == "ngl":   # engine front for the swaps is the sheet's generic F2 (F3 after the roll)
        held = pd.Series(np.where(held_f2, v["F3"].fillna(0), v["F2"].fillna(0)), index=r.index)
    else:
        held = pd.Series(np.where(held_f2, v["F2"].fillna(0), v["F1"].fillna(0)), index=r.index)
    c = pbar * sig * m
    rows.append(dict(bucket=bucket, product=name, n_days=len(r), strip=f"F1-F{nstrip}", price_usd_unit=pbar, sigma=sig, mult=m, risk_per_contract=c,
                     adv_strip=float(strip.mean()), adv_strip_med=float(strip.median()), adv_held=float(held.mean()), adv_f1f3=float(f13.mean()), adv_total=float(tot.mean()),
                     strip_share_of_total=float(strip.sum() / tot.sum()) if tot.sum() else np.nan, share_days_print=float((strip > 0).mean()),
                     x_strip=float(strip.mean()) * c / 1e6, x_strip_med=float(strip.median()) * c / 1e6, x_held=float(held.mean()) * c / 1e6, x_f1f3=float(f13.mean()) * c / 1e6, x_total=float(tot.mean()) * c / 1e6))
    print("done", name, flush=True)
d = pd.DataFrame(rows)
d["N_contracts_for_K"] = K / d.risk_per_contract
d["L_strip"] = K / (d.x_strip * 1e6)       # K as a multiple of one day's market 1-sigma risk turnover
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40)
d = d.sort_values("x_strip", ascending=False)
d.round(5).to_csv(OUT, index=False)
print(d[["bucket", "product", "strip", "n_days", "price_usd_unit", "sigma", "mult", "risk_per_contract", "adv_strip", "strip_share_of_total", "share_days_print", "x_strip", "x_held", "x_f1f3", "L_strip"]].round(4).to_string(index=False))
