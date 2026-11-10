"""Calendar-2025 liquidity metric of the NGLs, CME plus ICE (2026-11-10), and the update of Analysis/Liquidity_Cal2025_results.csv for the five products that have ICE contracts.
Definition as scripts/liquidity_cal2025.py: x = ADV of a 12-month strip (F1-F12 generic volume summed, no print = 0) x P x sigma x lot, in USD million of one-sigma daily risk traded per day; L = K / x with K = USD 1M.
P is the mean 2025 price of the contract held (roll on the 5th trading day of the last-trade month; the F2/F3 columns are front/next because F1 is the month being priced), sigma the standard deviation of the daily log
returns of the roll-adjusted series in 2025, lot = 42,000 gallons (CME 42,000 gallons; ICE 1,000 barrels = 42,000 gallons).

VENUES per product (all on the CME product's own 2025 calendar; CME and ICE are separate markets and their volumes are added):
  Ethane CAP + ICE APT | Propane BAP + ICE ASO | Butane DAE + ICE ARA | Isobutane IBD + ICE AQC | Natural Gasoline CME MMB + CME OGC (Conway) + ICE KLI, DRS, DHW.
  Naphtha (Bloomberg KI series), Ethylene and Propylene have no ICE contract in the download and keep their rows.
COMBINED ROW: volume columns (ADV of the strip, F1-F3, all tenors, held contract) are sums over venues; x columns are sums of each venue's volume times its own risk per lot; days traded = share of days with any print in
either venue; price and sigma are strip-volume-weighted averages; risk per lot = x / ADV, so that x = ADV x risk per lot holds exactly.
CHECKS (asserted): with the CME venue alone the code reproduces every column of the existing CME-only rows of the CSV (10 columns, relative tolerance 1e-9).
Outputs: Analysis/NGL_Liquidity_CME_ICE_Cal2025_contracts.csv (per contract), Analysis/NGL_Liquidity_CME_ICE_Cal2025_products.csv (per product), and the updated Analysis/Liquidity_Cal2025_results.csv
(the CME-only version is kept as Analysis/Liquidity_Cal2025_results_CME_only.csv).  Run from the repo root: python scripts/liquidity_ngl_ice_1110.py"""
import os, sys, shutil, importlib, warnings
warnings.filterwarnings("ignore")
os.environ["RP_PRICES_DIR"] = "Prices_1029_merged"
sys.path[:0] = ["research", "research/configs", "scripts"]
import numpy as np, pandas as pd
from ratio_continuous import build_rolling_f1_ratio
import ice_ngl_1110 as ice
import new_products_1110 as npd

K = 1e6
LOT = 42000
START, END = "2025-01-01", "2025-12-31"
CME_FILE = "data/Prices_1110/CME_Natural_Gasoline_Futures.xlsx"
MAIN = "Analysis/Liquidity_Cal2025_results.csv"
KEEP = "Analysis/Liquidity_Cal2025_results_CME_only.csv"
OUT_C = "Analysis/NGL_Liquidity_CME_ICE_Cal2025_contracts.csv"
OUT_P = "Analysis/NGL_Liquidity_CME_ICE_Cal2025_products.csv"
STRIP = [f"F{k}" for k in range(1, 13)]
if not os.path.exists(KEEP):
    shutil.copy(MAIN, KEEP)
ref = pd.read_csv(KEEP).set_index("product")          # the CME-only file (never overwritten)
COLS = list(pd.read_csv(KEEP).columns)


def read_sheet(src, sheet, header=1):
    d = (src[sheet] if isinstance(src, dict) else pd.read_excel(src, sheet_name=sheet, header=header)).copy()
    d = d.rename(columns={d.columns[0]: "Date"}); d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
    d = d.dropna(subset=["Date"]).set_index("Date").sort_index().apply(pd.to_numeric, errors="coerce")
    assert d.index.is_monotonic_increasing and not d.index.has_duplicates, sheet
    return d


def cal_frame(c):
    return pd.DataFrame({"Contract": c["Contract"], "roll_date": pd.to_datetime(c["LAST_TRADEABLE_DT"]), "expiry_date": pd.to_datetime(c["FUT_DLV_DT_LAST"])}).dropna().sort_values("roll_date").reset_index(drop=True)


def ogc_calendar():
    h = pd.read_excel(CME_FILE, sheet_name="EXPIRY_HISTORY", header=1)
    m = h[(h["Root"] == "OGC") & (h["Contract Size"] == 42000)].copy()
    m["cm"] = pd.to_datetime(m["Contract Month"].astype(str) + "-01"); m = m.sort_values("cm").reset_index(drop=True)
    ltd = pd.to_datetime(m["Last Trade Date"]); assert ltd.is_monotonic_increasing and ltd.is_unique, "OGC last trade dates"
    return pd.DataFrame({"Contract": m["Ticker"], "roll_date": ltd, "expiry_date": pd.to_datetime(m["Last Delivery Date"])})


def engine_series(px, cal):
    """Roll-adjusted series of one contract family (swap convention: sheet F2/F3 = front/next); returns the 2025 slice and its log price."""
    px = px[px.notna().any(axis=1)]
    prices = pd.DataFrame({"F1_raw": px["F2"], "F2_raw": px["F3"]})
    raw = build_rolling_f1_ratio(prices, cal, roll_day=5, roll_rule="expiry_month_nth_td")
    lp = np.log(raw["F1_continuous_ratio"].where(raw["F1_continuous_ratio"] > 0))
    r = raw.loc[START:END].copy(); r["log_price"] = lp.loc[r.index]
    assert len(r) > 240, len(r)
    return r


def venue(r, vol):
    """Risk per lot and the daily volume series of one venue on the index of r (the product's calendar)."""
    sig = float(r["log_price"].diff().std())
    held_f2 = r["Phase"].isin(["Roll_LTD-5", "F2_Tracking"])
    pbar = float(np.nanmean(np.where(held_f2, r["F2_raw"], r["F1_raw"])))
    v = vol.reindex(r.index)
    allc = [c for c in v.columns if str(c).startswith("F")]
    s = dict(strip=v[[c for c in STRIP if c in v.columns]].sum(axis=1, min_count=1).fillna(0),
             f13=v[[c for c in ("F1", "F2", "F3") if c in v.columns]].sum(axis=1, min_count=1).fillna(0),
             tot=v[allc].sum(axis=1, min_count=1).fillna(0),
             held=pd.Series(np.where(held_f2, v["F3"].fillna(0), v["F2"].fillna(0)), index=r.index))
    return dict(pbar=pbar, sig=sig, c=pbar * sig * LOT, s=s, n=len(r))


def combine(name, bucket, venues):
    """One CSV row (original columns) from a list of venues on the same index."""
    idx = venues[0]["s"]["strip"].index
    S = {k: sum(v["s"][k].reindex(idx).fillna(0) for v in venues) for k in ("strip", "f13", "tot", "held")}
    adv = {k: sum(float(v["s"][k].reindex(idx).fillna(0).mean()) for v in venues) for k in S}
    x = {k: sum(float(v["s"][k].reindex(idx).fillna(0).mean()) * v["c"] for v in venues) / 1e6 for k in S}
    w = [float(v["s"]["strip"].reindex(idx).fillna(0).mean()) for v in venues]
    wsum = sum(w)
    pbar = sum(a * v["pbar"] for a, v in zip(w, venues)) / wsum; sig = sum(a * v["sig"] for a, v in zip(w, venues)) / wsum
    c_eff = x["strip"] * 1e6 / adv["strip"]
    tot_sum = sum(float(v["s"]["tot"].reindex(idx).fillna(0).sum()) for v in venues)
    strip_sum = sum(float(v["s"]["strip"].reindex(idx).fillna(0).sum()) for v in venues)
    row = dict(bucket=bucket, product=name, n_days=len(idx), strip="F1-F12", price_usd_unit=pbar, sigma=sig, mult=LOT, risk_per_contract=c_eff,
               adv_strip=adv["strip"], adv_strip_med=float(S["strip"].median()), adv_held=adv["held"], adv_f1f3=adv["f13"], adv_total=adv["tot"],
               strip_share_of_total=strip_sum / tot_sum if tot_sum else np.nan, share_days_print=float((S["strip"] > 0).mean()),
               x_strip=x["strip"], x_strip_med=float(S["strip"].median()) * c_eff / 1e6, x_held=x["held"], x_f1f3=x["f13"], x_total=x["tot"])
    row["N_contracts_for_K"] = K / c_eff
    row["L_strip"] = K / (row["x_strip"] * 1e6)
    return row


# ---------------------------------------------------------------- CME venues, validated against the CME-only rows
cme_book = pd.read_excel(CME_FILE, sheet_name=None, header=1)
vnc = pd.read_excel("data/Prices_1029/Volume_NGL.xlsx", sheet_name=None, header=0)
CMEV = {}
for prod, mod, root in (("Ethane", "ngl", "CAP"), ("Propane", "ngl", "BAP"), ("Butane", "ngl", "DAE"), ("Isobutane", "ngl", "IBD")):
    raw = importlib.import_module(mod).load_f1_series_logret(prod).loc[START:END]
    CMEV[prod] = venue(raw, read_sheet(vnc, f"{root} Vol", header=0))
raw = importlib.import_module("mmb").load_f1_series_logret("NatGasoline").loc[START:END]
CMEV["NatGasoline"] = venue(raw, read_sheet(cme_book, "NGS_CME_MMB_VOL"))
for prod, v in CMEV.items():
    row = combine(prod, "ngl", [v]); r0 = ref.loc[prod]
    for col in ("n_days", "price_usd_unit", "sigma", "risk_per_contract", "adv_strip", "adv_strip_med", "adv_held", "adv_f1f3", "adv_total", "strip_share_of_total", "share_days_print", "x_strip", "x_strip_med", "x_held", "x_f1f3", "x_total", "L_strip"):
        assert abs(row[col] - r0[col]) <= 1e-6 * max(1.0, abs(r0[col])), (prod, col, row[col], r0[col])
print("validation: the CME venue alone reproduces every column of the CME-only rows of Ethane, Propane, Butane, Isobutane and Natural Gasoline", flush=True)

# ---------------------------------------------------------------- other venues
OTHER = {"Ethane": [], "Propane": [], "Butane": [], "Isobutane": [], "NatGasoline": []}
ogc_r = engine_series(read_sheet(cme_book, "NGS_CME_OGC_PX"), ogc_calendar())
OTHER["NatGasoline"].append(("CME", "OGC Conway natural gasoline OPIS swap", venue(ogc_r, read_sheet(cme_book, "NGS_CME_OGC_VOL"))))
FAM = {"APT": "Ethane", "ASO": "Propane", "ARA": "Butane", "AQC": "Isobutane", "KLI": "NatGasoline", "DRS": "NatGasoline", "DHW": "NatGasoline"}
for pref, (root, name) in ice.ICE.items():
    rr = engine_series(ice.read_px(pref + "_PX"), cal_frame(ice.calendar(root)))
    OTHER[FAM[root]].append(("ICE", f"{root} {name}", venue(rr, ice.read_px(pref + "_VOL"))))

# ---------------------------------------------------------------- tables
LABEL = {"Ethane": "Ethane", "Propane": "Propane", "Butane": "Butane", "Isobutane": "Isobutane", "NatGasoline": "Natural Gasoline"}
CMENAME = {"Ethane": "CAP Mt Belvieu ethane swap", "Propane": "BAP Mt Belvieu propane swap", "Butane": "DAE Mt Belvieu normal butane swap", "Isobutane": "IBD Mt Belvieu isobutane swap", "NatGasoline": "MMB Mt Belvieu 5-decimal OPIS swap"}
crow, prow, newrows = [], [], {}
for prod in OTHER:
    vs = [("CME", CMENAME[prod], CMEV[prod])] + OTHER[prod]
    for ex, nm, v in vs:
        crow.append(dict(family=LABEL[prod], exchange=ex, contract=nm, price_usd_gal=v["pbar"], sigma=v["sig"], risk_per_lot=v["c"], adv_strip=float(v["s"]["strip"].reindex(CMEV[prod]["s"]["strip"].index).fillna(0).mean()),
                         x_strip=float(v["s"]["strip"].reindex(CMEV[prod]["s"]["strip"].index).fillna(0).mean()) * v["c"] / 1e6))
    newrows[prod] = combine(prod, "ngl", [v for _, _, v in vs])
    cme_only = combine(prod, "ngl", [v for ex, _, v in vs if ex == "CME"]); ice_only = [v for ex, _, v in vs if ex == "ICE"]
    xi = sum(float(v["s"]["strip"].reindex(CMEV[prod]["s"]["strip"].index).fillna(0).mean()) * v["c"] for v in ice_only) / 1e6
    prow.append(dict(family=LABEL[prod], adv_cme=cme_only["adv_strip"], adv_ice=sum(float(v["s"]["strip"].reindex(CMEV[prod]["s"]["strip"].index).fillna(0).mean()) for v in ice_only),
                     x_cme=cme_only["x_strip"], x_ice=xi, x_total=newrows[prod]["x_strip"], ice_share_x=xi / newrows[prod]["x_strip"], L_cme_only_ref=float(ref.loc[prod, "L_strip"]),
                     L_cme_ice=newrows[prod]["L_strip"], days_traded=newrows[prod]["share_days_print"]))
cdf = pd.DataFrame(crow); cdf["L_days"] = K / (cdf["x_strip"] * 1e6)
cdf.round(9).to_csv(OUT_C, index=False)
pdf = pd.DataFrame(prow)
for prod in ("Naphtha", "Propylene", "Ethylene"):
    r0 = ref.loc[prod]
    pdf.loc[len(pdf)] = dict(family=prod, adv_cme=r0["adv_strip"], adv_ice=0.0, x_cme=r0["x_strip"], x_ice=0.0, x_total=r0["x_strip"], ice_share_x=0.0, L_cme_only_ref=r0["L_strip"], L_cme_ice=r0["L_strip"], days_traded=r0["share_days_print"])
pdf = pdf.sort_values("x_total", ascending=False).reset_index(drop=True); pdf["rank"] = np.arange(1, len(pdf) + 1)
pdf.round(9).to_csv(OUT_P, index=False)

# ---------------------------------------------------------------- main CSV: replace the five rows
main = pd.read_csv(KEEP)
for prod, row in newrows.items():
    main.loc[main["product"] == prod, COLS] = [row[c] for c in COLS]
main = main.sort_values("x_strip", ascending=False)
main.round(9).to_csv(MAIN, index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(cdf.round(4).to_string(index=False)); print(); print(pdf.round(4).to_string(index=False))
print("updated", MAIN, "(CME-only version kept as", KEEP + ")")
