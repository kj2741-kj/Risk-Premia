"""Every number of Commodity_Rankings_<tag>.html against (1) the research dashboard's data, (2) a recomputation from the product return series, (3) the Streamlit/hub engine's series.
Run from the repo root:  RP_PRICES_DIR=Prices_0930 FD_TAG=0930 python scripts/final_dashboard/check_rankings_consistency.py   (or Prices_1029_merged / 1029)
Needs outputs/final_dashboard_<tag>/engine_per_product_v504.pkl (written by check_gas_emissions_math.py; the engine run takes about ten minutes, rebuilt here if absent)."""
import os, sys, re, json, pickle, warnings
warnings.filterwarnings("ignore")
sys.path[:0] = ["scripts/final_dashboard", "research", "research/configs", "scripts", "."]
from fd_config import tag_from_prices_dir, out_dir
import numpy as np, pandas as pd
TAG = tag_from_prices_dir()
import cross_asset_engine as cae
from engine import combine_returns
from run_regime_table import _metrics
D = out_dir(TAG)
res = json.load(open(D / "final_v3.json")); nets, meta = pickle.load(open(D / "products_nets.pkl", "rb"))
html = open(f"Analysis/Commodity_Rankings_{TAG}.html", encoding="utf8").read()
DATA = json.loads(re.search(r"const DATA=(\{.*?\});\n", html, re.S).group(1)); blk = DATA[list(DATA)[0]]
WIN = {"full": ("2012-01-01", None), "p1": ("2012-01-01", "2016-12-31"), "p2": ("2017-01-01", "2021-12-31"), "p3": ("2022-01-01", None), "y26": ("2026-01-01", None)}
SLEEVES = ["Momentum", "Carry", "CarryMom", "Value", "Skewness"]
BK = ["metals", "petroleum", "pen", "ngl", "precious", "agri", "softs"]
LABEL = {"metals": "Metals", "petroleum": "Petroleum", "pen": "Gas and Emissions", "ngl": "NGL", "precious": "Precious", "agri": "Agriculture", "softs": "Softs"}
fails = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)
    if not ok:
        fails.append(name)
pack = lambda m: [None if pd.isna(m[k]) else round(float(m[k]), 3) for k in ("ir", "ret", "vol", "mdd")]
sl = lambda s, w: s.loc[WIN[w][0]:WIN[w][1]] if WIN[w][1] else s.loc[WIN[w][0]:]
close = lambda a, b, tol=0.0011: all((x is None and y is None) or (x is not None and y is not None and abs(x - y) <= tol) for x, y in zip(a, b))
prods = blk["products"]
prods_all = prods
prods = [p for p in prods_all if p["asset"] != "US Power"]          # the seven research buckets; US Power is a standalone bucket on the page (own windows, from 2017) and is checked against its own tab below
check(f"page lists the expected products ({len(prods)} of the seven research buckets and {len(prods_all) - len(prods)} US Power series)", len(prods) == 29 and len(prods_all) == 34, ", ".join(f"{LABEL_} {sum(p['asset'] == LABEL_ for p in prods)}" for LABEL_ in LABEL.values()))
PJ = json.load(open(f"Analysis/_power_build/power_tab_{TAG}.json")); PDISP = {"PJM Peak": "PJM_Peak", "PJM OffPeak": "PJM_OffPeak", "ERCOT Peak": "ERCOT_Peak", "ERCOT OffPeak": "ERCOT_OffPeak", "MISO Peak": "MISO_Peak"}
bad = n = 0
for p in prods_all:
    if p["asset"] != "US Power": continue
    for s_ in SLEEVES:
        for w in WIN:
            n += 1; bad += not close(p["vals"][s_][w], pack(PJ["products"][f"power|{PDISP[p['name']]}"][s_][w]), 0.0)
cl = next(c for c in blk["classes"] if c["name"] == "US Power")
for r_i, row in enumerate(PJ["tab"]["windows"]["full"]):
    for w in WIN:
        n += 1; bad += not close(cl["vals"][row["name"]][w], pack(PJ["tab"]["windows"][w][r_i]), 0.0)
check(f"US Power rows on the page == the Power tab ({n} cells)", bad == 0, f"{bad} differing cells")
key_of = {}
for bk in BK:
    for a, p in res["tabs"][bk]["pkeys"] and [(k.split("|")[0], k.split("|")[1]) for k in res["tabs"][bk]["pkeys"]]:
        key_of[(LABEL[bk], p)] = (a, p)
check("every page product maps to a dashboard product", all((p["asset"], p["name"]) in key_of for p in prods))

# 1 page vs the research dashboard data (the HTML dashboard's own numbers)
bad = n = 0
for p in prods:
    a, nm = key_of[(p["asset"], p["name"])]
    for s in SLEEVES + ["EW-5"]:
        for w in WIN:
            ref = res["products"][f"{a}|{nm}"][s if s != "EW-5" else "EW PORT"][w]
            n += 1; bad += not close(p["vals"][s][w], pack(ref), 0.0)
check(f"1. page product rows == dashboard data (sleeves + EW-5, {n} cells x4 metrics)", bad == 0, f"{bad} differing cells")
bad = n = 0
for bk in BK:
    cl = next(c for c in blk["classes"] if c["name"] == LABEL[bk])
    for r_i, row in enumerate(res["tabs"][bk]["windows"]["full"]):
        for w in WIN:
            n += 1; bad += not close(cl["vals"][row["name"]][w], pack(res["tabs"][bk]["windows"][w][r_i]), 0.0)
check(f"1. page bucket rows == dashboard bucket tabs ({n} cells)", bad == 0, f"{bad} differing cells")

# 2 recomputed from the product return series (EW-5 and IV-5 are only on the rankings page, so they are rebuilt here)
bad = n = 0
for p in prods:
    a, nm = key_of[(p["asset"], p["name"])]; lst = [nets[(a, nm)][s] for s in SLEEVES]
    ser = {"EW-5": combine_returns(lst, "equal_weight"), "IV-5": combine_returns(lst, "inverse_vol", vol_window=63), **{s: nets[(a, nm)][s] for s in SLEEVES}}
    for k, v in ser.items():
        for w in WIN:
            n += 1; bad += not close(p["vals"][k][w], pack(_metrics(sl(v, w))), 0.0011)
check(f"2. page product rows (sleeves, EW-5, IV-5) == recomputed from the series ({n} cells)", bad == 0, f"{bad} differing cells")

# 3 Streamlit / hub engine series (the engine with the research Value warm-up, see check_gas_emissions_math.py)
CACHE = D / "engine_per_product_v504.pkl"
if CACHE.exists():
    PP = pickle.load(open(CACHE, "rb"))
else:
    orig = cae.value_v1_position
    cae.value_v1_position = lambda *a, **k: orig(*a, min_periods=504, **k)
    PP = {ac: cae.per_product_four_row(ac, 5, per_product_pairs=True, include_skewness=True) for ac in BK}
    cae.value_v1_position = orig; pickle.dump(PP, open(CACHE, "wb"))
STY = {"Momentum": "Momentum", "Combined Carry": "Carry", "Combined CarryMom": "CarryMom", "Value": "Value", "Skewness": "Skewness"}
eng = {}
for ac in BK:
    for st, lab in STY.items():
        for nm, net in zip(PP[ac][st]["names"], PP[ac][st]["net"]):
            eng.setdefault((LABEL[ac], nm), {})[lab] = net
check("3. engine covers every page product with five sleeves", all(len(eng.get((p["asset"], p["name"]), {})) == 5 for p in prods))
bad = n = 0
for p in prods:
    e = eng[(p["asset"], p["name"])]; lst = [e[s] for s in SLEEVES]
    ser = {"EW-5": combine_returns(lst, "equal_weight"), "IV-5": combine_returns(lst, "inverse_vol", vol_window=63), **e}
    for k, v in ser.items():
        for w in WIN:
            n += 1; bad += not close(p["vals"][k][w], pack(_metrics(sl(v, w))), 0.0011)
check(f"3. page product rows (sleeves, EW-5, IV-5) == Streamlit engine series ({n} cells)", bad == 0, f"{bad} differing cells")
bad = n = 0
for ac in BK:
    g4, n4 = cae.asset_class_four_row(ac, 5, None, lambda a, t: PP[a])
    rows = {STY[k]: v for k, v in n4.items()}; rows["EW PORT"] = cae.asset_class_ew_portfolio(g4, n4)[1]
    rows["Inverse Vol"] = combine_returns(list(n4.values()), "inverse_vol", vol_window=63)
    cl = next(c for c in blk["classes"] if c["name"] == LABEL[ac])
    for nm, v in rows.items():
        for w in WIN:
            n += 1; bad += not close(cl["vals"][nm][w], pack(_metrics(sl(v, w))), 0.0011)
check(f"3. page bucket rows (5 sleeves, EW PORT, Inverse Vol) == Streamlit engine ({n} cells)", bad == 0, f"{bad} differing cells")

# 4 internal consistency of what the page shows: IR = return / vol, drawdown <= 0
bad = 0
for p in prods:
    for k, byw in p["vals"].items():
        for w, (ir, ret, vol, mdd) in byw.items():
            if ir is not None and vol:
                bad += abs(ir - ret / vol) > 0.0105 * max(1.0, abs(ir))
            if mdd is not None:
                bad += mdd > 0
check("4. every cell: IR == return / vol (rounding) and drawdown <= 0", bad == 0, f"{bad} cells")
# 5 the two liquidity columns (Calendar-2025 snapshot): L = K / x in days and x in USD millions per day, from Analysis/Liquidity_Cal2025_results.csv
import csv
liq = {r["product"]: r for r in csv.DictReader(open("Analysis/Liquidity_Cal2025_results.csv", encoding="utf8"))}
bad = sum(abs(p["L"] - float(liq[p["name"]]["L_strip"])) > 1e-5 * max(1, abs(p["L"])) or abs(p["X"] - float(liq[p["name"]]["x_strip"])) > 1e-4 for p in prods)
check("5. page liquidity columns (Time to trade 1 sigma risk in Days, Risk Millions per day) == liquidity CSV for all products", bad == 0, f"{bad} differences")
bad = sum(abs(p["L"] * p["X"] - 1.0) > 2e-3 for p in prods)       # K = USD 1M: L x x = 1
check("5. L x (Risk Millions per day) == K = USD 1M for every product", bad == 0, f"{bad} differences")
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
