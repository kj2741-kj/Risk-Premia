"""Liquidity metric, Calendar 2025 (one-time snapshot), 30 products -> Analysis/Liquidity_Cal2025_results.csv (2026-11-04: + Ethylene, Propylene (all six NGL), UK Gas and the Naphtha candidate).
x = ADV * P * sigma * multiplier = USD of one-sigma daily risk traded per day (Prof. Bouchouev's denominator); K/x with K = $1M.
ADV = mean over 2025 trading days of volume summed over the contracts of a 12-month strip (F1-F12 for monthly products, fewer for quarterly or
bi-monthly chains, see P below); NaN volume = 0. NGL is the CME half only (ICE to be added). Held-contract and F1-F3 ADV are kept as sensitivities.
Run from the repo root: python scripts/liquidity_cal2025.py. Needs data/Prices_1029 (volume), data/Prices_1029_merged (prices; UK Gas curve and derived calendar inside), data/Emissions_1029,
data/Prices_1103 (UK Gas and Naphtha volume; Naphtha engine inputs in data/Prices_1103/derived, written by scripts/new_products.py)."""
import os, sys, warnings; warnings.filterwarnings("ignore")
os.environ["RP_PRICES_DIR"] = "Prices_1029_merged"
sys.path[:0] = ["research", "research/configs", "scripts"]   # run from the repo root
import importlib
import numpy as np, pandas as pd
V = "data/Prices_1029/"
EUR = 1.1300      # ECB euro reference rate, mean of 255 daily fixes in 2025 (data-api.ecb.europa.eu)
GBP = 1.3184      # USD per GBP, mean of the 255 daily crosses EURUSD/EURGBP of the ECB fixes in 2025 (same source)
THERMS_PER_LOT = 1000 * 365 / 12   # UK Gas: 1,000 therms a day over an average month (30.4167 days), the analogue of the 730.5 MWh used for TTF
K = 1e6           # USD of 1-sigma daily risk per product (changed from 10e6 on 2026-11-01; the ranking by x does not depend on K)
OUT = "Analysis/Liquidity_Cal2025_results.csv"
# (module, engine product name, bucket, volume file kind, root, lot multiplier, price->USD/unit factor, fx, N contracts in a 12-month strip)
P = [
 ("metals", "Copper", "metals", "LME", "LP", 25, 1, 1, 12), ("metals", "Aluminium", "metals", "LME", "LA", 25, 1, 1, 12), ("metals", "Lead", "metals", "LME", "LL", 25, 1, 1, 12), ("metals", "Zinc", "metals", "LME", "LX", 25, 1, 1, 12),
 ("energy", "WTI", "petroleum", "ENERGY", "CL", 1000, 1, 1, 12), ("energy", "Brent", "petroleum", "ENERGY", "CO", 1000, 1, 1, 12), ("energy", "RBOB", "petroleum", "ENERGY", "XB", 42000, 0.01, 1, 12),
 ("energy", "HeatingOil", "petroleum", "ENERGY", "HO", 42000, 0.01, 1, 12), ("energy", "SingaporeGasoil", "petroleum", "ENERGY", "QS", 100, 1, 1, 12),
 ("energy", "NatGas", "pen", "ENERGY", "NG", 10000, 1, 1, 12), ("emissions", "TTF", "pen", "EMI", "TTF", 730.5, 1, EUR, 12), ("emissions", "EUA", "pen", "EMI", "EUA", 1000, 1, EUR, 4),
 ("ngl", "Ethylene", "ngl", "NGL", "PCW", 100000, 1, 1, 12), ("ngl", "Propylene", "ngl", "NGL", "PGP", 100000, 1, 1, 12),
 ("emissions", "UKGas", "pen", "UKG", "UKG", THERMS_PER_LOT, 0.01, GBP, 12), ("naphtha", "Naphtha", "candidate", "NAP", "NAP", 1000, 1, 1, 12),
 ("ngl", "Ethane", "ngl", "NGL", "CAP", 42000, 1, 1, 12), ("ngl", "Propane", "ngl", "NGL", "BAP", 42000, 1, 1, 12), ("ngl", "Butane", "ngl", "NGL", "DAE", 42000, 1, 1, 12), ("ngl", "Isobutane", "ngl", "NGL", "IBD", 42000, 1, 1, 12),
 ("precious", "Gold", "precious", "PRECIOUS", "GC", 100, 1, 1, 6), ("precious", "Silver", "precious", "PRECIOUS", "SI", 5000, 1, 1, 5), ("precious", "Platinum", "precious", "PRECIOUS", "PL", 50, 1, 1, 4), ("precious", "Palladium", "precious", "PRECIOUS", "PA", 100, 1, 1, 4),
 ("agri", "Corn", "agri", "AGRI", "C", 5000, 0.01, 1, 5), ("agri", "Wheat", "agri", "AGRI", "W", 5000, 0.01, 1, 5), ("agri", "Soybean", "agri", "AGRI", "S", 5000, 0.01, 1, 7),
 ("agri", "SoybeanOil", "agri", "AGRI", "BO", 60000, 0.01, 1, 8), ("agri", "Coffee", "agri", "AGRI", "KC", 37500, 0.01, 1, 5), ("agri", "Sugar", "agri", "AGRI", "SB", 112000, 0.01, 1, 4),
]


def vol_sheet(kind, root):
    if kind in ("UKG", "NAP"):   # 2026-11-03 drop: title row, Date/F1.. header row; the extra "Total" column is not a tenor
        d = pd.read_excel("data/Prices_1103/New_Products_Futures_2006_to_date.xlsx", sheet_name=("UK Gas - Volume" if kind == "UKG" else "Naphtha - Volume"), header=1)
    elif kind == "EMI":
        d = pd.read_excel("data/Emissions_1029/Gas_Power_Emissions_Futures.xlsx", sheet_name=f"{root}_VOL", header=1)
    else:
        d = pd.read_excel(V + f"Volume_{kind}.xlsx", sheet_name=f"{root} Vol", header=0)
    d = d.rename(columns={d.columns[0]: "Date"}); d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
    return d.dropna(subset=["Date"]).set_index("Date").apply(pd.to_numeric, errors="coerce")


def load_naphtha_logret():
    """Engine series for Naphtha (candidate, not in any bucket): derived calendar (last business day of the pricing month), same roll rule as every product."""
    from rolling_continuous import apply_data_fixes   # noqa: F401  (no fixes defined for Naphtha)
    from ratio_continuous import get_metal_rolling_f1_ratio, reanchor_f1_continuous_ratio
    D = "data/Prices_1103/derived/"
    cfgd = {"KI": {"name": "Naphtha", "price_sheet": "Naphtha KI", "calendar_sheet": "KI - Naphtha CIF NWE", "f1_col": 1, "f2_col": 2, "data_start_row": 2}}
    df = get_metal_rolling_f1_ratio("KI", futures_file=D + "Naphtha_Futures.xlsx", calendar_file=D + "Naphtha_Expiry_Calendar.xlsx", config=cfgd,
                                    verbose=False, roll_day=5, roll_rule="expiry_month_nth_td")
    df = reanchor_f1_continuous_ratio(df)
    price = df["F1_continuous_ratio"].where(df["F1_continuous_ratio"] > 0); df["log_price"] = np.log(price)
    return df


rows = []
for mod, name, bucket, kind, root, m, pf, fx, nstrip in P:
    raw = load_naphtha_logret() if mod == "naphtha" else importlib.import_module(mod).load_f1_series_logret(name)
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
