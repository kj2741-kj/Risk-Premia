"""Consistency audit of the Gas and Emissions bucket (UK Gas added, renamed 2026-11-04): HTML pages vs final_v3.json vs the Streamlit/hub engine vs the liquidity CSV.
Run from the repo root:  RP_PRICES_DIR=Prices_1029_merged FD_TAG=1029 python scripts/final_dashboard/check_gas_emissions_consistency.py   (or Prices_0930 / 0930)
Prints PASS/FAIL per check and exits non-zero on any failure."""
import os, sys, re, json, pickle, csv, warnings
warnings.filterwarnings("ignore")
sys.path[:0] = ["scripts/final_dashboard", "research", "research/configs", "scripts", "."]
from fd_config import TAGS, tag_from_prices_dir, out_dir
import numpy as np, pandas as pd
TAG = tag_from_prices_dir()
assert os.environ.get("FD_TAG", TAG) == TAG, "FD_TAG must match RP_PRICES_DIR"
import cross_asset_engine as cae
from run_regime_table import _metrics
D = out_dir(TAG)
res = json.load(open(D / "final_v3.json")); nets, meta = pickle.load(open(D / "products_nets.pkl", "rb"))
PEN = [("energy", "NatGas"), ("emissions", "TTF"), ("emissions", "UKGas"), ("emissions", "EUA")]
fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)
    if not ok:
        fails.append(name)


# 1. names and product lists in every page of this tag ----------------------------------------------------------------------------------------------------
pages = {f: open(f"Analysis/{f}_{TAG}.html", encoding="utf8").read() for f in ("Final_Research_Dashboard_2012", "Commodity_Rankings", "Skewness_Research", "VTI_Research")}
for f, h in pages.items():
    old = [t for t in ("Power, Emissions", "Power / Emissions", "Power/Emissions", "Emissions and Nat Gas") if t in h] + (["PEN"] if re.search(r"\bPEN\b", h) else [])
    check(f"{f}: no old bucket name", not old, str(old))
    check(f"{f}: 'Gas and Emissions' present", "Gas and Emissions" in h)
for f in ("Final_Research_Dashboard_2012", "Commodity_Rankings", "Skewness_Research"):
    check(f"{f}: UKGas present", "UKGas" in pages[f])

# 2. the dashboard's embedded data equals final_v3.json (+ liquidity meta) -------------------------------------------------------------------------------------
h = pages["Final_Research_Dashboard_2012"]
m = re.search(r"<script>\nconst D=(.*?);\n", h, re.S); emb = json.loads(m.group(1))
for k in ("tabs", "products", "combined", "crosspair", "corr", "equity", "bystyle"):
    sub = isinstance(res[k], dict) and all(x in emb[k] for x in res[k])      # extra entries (e.g. the Power tab) are allowed; every key of final_v3.json must be identical
    check(f"dashboard embedded '{k}' == final_v3.json", emb[k] == res[k] or (sub and all(emb[k][x] == res[k][x] for x in res[k])))
check("pen tab products", emb["tabs"]["pen"]["products"] == ["NatGas", "TTF", "UKGas", "EUA"], str(emb["tabs"]["pen"]["products"]))
check("pen tab label", emb["tabs"]["pen"]["label"] == "Gas and Emissions", emb["tabs"]["pen"]["label"])
liq = {r["product"]: r for r in csv.DictReader(open("Analysis/Liquidity_Cal2025_results.csv", encoding="utf8"))}
if os.path.exists("Analysis/Power_Liquidity_Cal2025_results.csv"):     # the Power tab has its own liquidity file
    liq.update({r["product"]: r for r in csv.DictReader(open("Analysis/Power_Liquidity_Cal2025_results.csv", encoding="utf8"))})
ok = all(abs(emb["meta"]["liq"][k] - float(liq[k.split("|")[1]]["L_strip"])) < 1e-12 for k in emb["meta"]["liq"])
check("dashboard By-product L == liquidity CSV L_strip (all products)", ok)
check("UKGas L in dashboard", abs(emb["meta"]["liq"]["emissions|UKGas"] - float(liq["UKGas"]["L_strip"])) < 1e-12, f"{emb['meta']['liq']['emissions|UKGas']:.5f}")

# 3. the Rankings page data equals final_v3.json / products pickle ------------------------------------------------------------------------------------------
h = pages["Commodity_Rankings"]
m = re.search(r"const DATA\s*=\s*(\{.*?\});\s*\n", h, re.S) or re.search(r"DATA\s*=\s*(\{.*?\})\s*;", h, re.S)
if m:
    rk = json.loads(m.group(1)); key = list(rk)[0]; blk = rk[key]
    names = [p["name"] for p in blk["products"] if p["asset"] == "Gas and Emissions"]
    check("Rankings: Gas and Emissions products", names == ["NatGas", "TTF", "UKGas", "EUA"], str(names))
    pk = lambda m_: [None if pd.isna(x) else round(float(x), 3) for x in (m_["ir"], m_["ret"], m_["vol"], m_["mdd"])]
    bad = 0
    for p in blk["products"]:
        if p["asset"] != "Gas and Emissions":
            continue
        a = dict(PEN)[p["name"]] if False else next(x for x, y in PEN if y == p["name"])
        for s in ("Momentum", "Carry", "CarryMom", "Value", "Skewness"):
            for w, v in p["vals"][s].items():
                bad += v != pk(res["products"][f"{a}|{p['name']}"][s][w])
    check("Rankings product rows == final_v3.json (Gas and Emissions, 5 sleeves x 5 windows)", bad == 0, f"{bad} differences")
    cl = next(c for c in blk["classes"] if c["name"] == "Gas and Emissions")
    bad = 0
    for r_i, row in enumerate(res["tabs"]["pen"]["windows"]["full"]):
        for w, v in cl["vals"][row["name"]].items():
            bad += v != pk(res["tabs"]["pen"]["windows"][w][r_i])
    check("Rankings bucket rows == final_v3.json tab 'pen'", bad == 0, f"{bad} differences")
else:
    check("Rankings DATA block found", False)

# 4. independent recomputation of the UK Gas product metrics from the series -------------------------------------------------------------------------------
WIN = {"full": ("2012-01-01", None), "p1": ("2012-01-01", "2016-12-31"), "p2": ("2017-01-01", "2021-12-31"), "p3": ("2022-01-01", None), "y26": ("2026-01-01", None)}
f3 = lambda d: {k: (None if pd.isna(v) else round(float(v), 3)) for k, v in d.items()}
bad = 0
for a, p in PEN:
    for s, ser in nets[(a, p)].items():
        for w, (st, e) in WIN.items():
            bad += f3(_metrics(ser.loc[st:e] if e else ser.loc[st:])) != res["products"][f"{a}|{p}"][s][w]
check("JSON product metrics == recomputed from the nets (4 products x 5 sleeves x 5 windows)", bad == 0, f"{bad} differences")

# 5. Streamlit / hub engine vs the research series ------------------------------------------------------------------------------------------------------------
fetch = lambda ac, tc: cae.per_product_four_row(ac, tc, per_product_pairs=True, include_skewness=True)
pp = fetch("pen", 5)
STY = {"Momentum": "Momentum", "Combined Carry": "Carry", "Combined CarryMom": "CarryMom", "Value": "Value", "Skewness": "Skewness"}
worst = 0.0; pre = {}
for sty, lab in STY.items():
    for nm, net in zip(pp[sty]["names"], pp[sty]["net"]):
        a = next(x for x, y in PEN if y == nm); r = nets[(a, nm)][lab]
        idx = r.index.union(net.index)
        d = (r.reindex(idx).fillna(0) - net.reindex(idx).fillna(0)).abs()
        worst = max(worst, float(d.loc["2012-01-01":].max()))          # the reporting window of every research page
        if d.loc[:"2011-12-31"].max() > 1e-9:
            pre[(nm, lab)] = round(float(d.loc[:"2011-12-31"].max()), 3)
check("engine per-product net series == research pickle from 2012-01-01 (4 products x 5 sleeves)", worst < 1e-9, f"worst abs diff {worst:.2e}")
check("pre-2012 differences are only the Value warm-up (research needs 504 observations, engine default 630)", all(k[1] == "Value" for k in pre), str(pre))
check("engine product list", cae.DASHBOARD_PRODUCTS["pen"] == ["NatGas", "TTF", "UKGas", "EUA"] and pp["Momentum"]["names"] == ["NatGas", "TTF", "UKGas", "EUA"], str(pp["Momentum"]["names"]))
gross, net = cae.asset_class_four_row("pen", per_product_fetcher=fetch)
bucket = {STY[k]: v for k, v in net.items()}
_, ew = cae.asset_class_ew_portfolio({k: v for k, v in gross.items()}, {k: v for k, v in net.items()})
rows = dict(bucket); rows["EW PORT"] = ew
bad = 0; worst_ir = 0.0
for w, (st, e) in WIN.items():
    for r_i, row in enumerate(res["tabs"]["pen"]["windows"][w]):
        if row["name"] in rows:
            mm = f3(_metrics(rows[row["name"]].loc[st:e] if e else rows[row["name"]].loc[st:]))
            for k in ("ir", "ret", "vol", "mdd"):
                d = abs((mm[k] or 0) - (row[k] or 0)); worst_ir = max(worst_ir, d)
            bad += mm != {k: row[k] for k in mm}
check("engine bucket series (5 sleeves + EW PORT) == dashboard tab 'pen' (all windows)", bad == 0, f"{bad} differing rows, worst abs diff {worst_ir:.3f}")

# 6. Streamlit app file and hub text -------------------------------------------------------------------------------------------------------------------------
app = open("pen_dashboard/app.py", encoding="utf8").read(); hub = open("hub/app.py", encoding="utf8").read()
check("pen app: UK Gas product wired", '"FN"' in app and "UKGas" in app and 'PRODUCT_ORDER = ["NG", "TZT", "FN", "MO"]' in app)
check("pen app: no old name in UI strings", "Power, Emissions &" not in app and "Power, Emissions &amp;" not in app)
check("hub: bucket entry renamed", '"Gas & Emissions"' in hub and '"Power, Emissions & Nat Gas"' not in hub)
# 7. Naphtha in the NGL bucket (2026-11-04) ------------------------------------------------------------------------------------------------------------------
check("ngl tab products (dashboard)", emb["tabs"]["ngl"]["products"] == ["Ethane", "Propane", "Butane", "Isobutane", "Naphtha"], str(emb["tabs"]["ngl"]["products"]))
check("Naphtha L in dashboard == liquidity CSV", abs(emb["meta"]["liq"]["naphtha|Naphtha"] - float(liq["Naphtha"]["L_strip"])) < 1e-12, f"{emb['meta']['liq']['naphtha|Naphtha']:.3f}")
if m:
    names = [p["name"] for p in blk["products"] if p["asset"] == "NGL"]
    check("Rankings: NGL products", names == ["Ethane", "Propane", "Butane", "Isobutane", "Naphtha"], str(names))
    bad = 0
    for p in blk["products"]:
        if p["name"] == "Naphtha":
            for s_ in ("Momentum", "Carry", "CarryMom", "Value", "Skewness"):
                for w, v in p["vals"][s_].items():
                    bad += v != pk(res["products"]["naphtha|Naphtha"][s_][w])
    check("Rankings Naphtha rows == final_v3.json", bad == 0, f"{bad} differences")
check("cross-asset engine: NGL products", cae.DASHBOARD_PRODUCTS["ngl"] == ["Ethane", "Propane", "Butane", "Isobutane", "Naphtha"])
ngl_app = open("ngl_dashboard/app.py", encoding="utf8").read()
check("ngl app: Naphtha wired", 'PRODUCT_ORDER = ["CAP", "BAP", "DAE", "IBD", "KI"]' in ngl_app and "NAPHTHA_CONFIG" in ngl_app and "import ngl_bucket" in ngl_app)
# 8. the standalone Power tab of the 0930 and 1029 pages must stay in place (built by scripts/power + power_tab_v3.py, not by the pipeline above) -------------------------------------------
if TAG in ("0930", "1029"):
    pw_ok = "power" in emb["tabs"] and emb["tabs"]["power"]["pkeys"] == ["power|PJM_Peak", "power|PJM_OffPeak", "power|ERCOT_Peak", "power|ERCOT_OffPeak", "power|MISO_Peak"]
    check(f"{TAG} page keeps the standalone Power tab (5 series), outside the six-bucket book", pw_ok and "power" not in emb["meta"]["keys"] and "power" not in emb["combined"]["members"])
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
