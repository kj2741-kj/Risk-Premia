"""Shared helpers for the v4 build: per-product nets (five sleeves, 2012 variant), verified aggregation and statistics."""
import os, json, pickle
os.environ["RP_PRICES_DIR"] = "Prices_0930"
import numpy as np, pandas as pd
REPO = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia"
S = os.path.dirname(os.path.abspath(__file__))
SLEEVES = ["Momentum", "Carry", "CarryMom", "Value", "Skewness"]
PRODUCTS = {"metals": ["Copper", "Aluminium", "Lead", "Zinc"], "energy": ["WTI", "Brent", "RBOB", "HeatingOil", "NatGas"], "petroleum": ["WTI", "Brent", "RBOB", "HeatingOil"],
            "ngl": ["Ethane", "Propane", "Butane"], "precious": ["Gold", "Silver", "Platinum", "Palladium"],
            "agri": ["Corn", "Wheat", "Soybean", "LiveCattle"], "softs": ["Sugar", "Cocoa", "Coffee", "Cotton"]}   # 2026-11-10: Agriculture split into Agriculture and Softs
MEMBERS = {"metals": [("metals", p) for p in PRODUCTS["metals"]], "petroleum": [("energy", p) for p in PRODUCTS["petroleum"]],
           "pen": [("energy", "NatGas"), ("emissions", "TTF"), ("emissions", "UKGas"), ("emissions", "EUA")],
           "ngl": [("ngl", p) for p in PRODUCTS["ngl"]] + [("naphtha", "Naphtha"), ("mmb", "NatGasoline")],
           "precious": [("precious", p) for p in PRODUCTS["precious"]], "agri": [("agri", p) for p in PRODUCTS["agri"]], "softs": [("softs", p) for p in PRODUCTS["softs"]]}
BUCKETS = ["metals", "petroleum", "pen", "ngl", "precious", "agri", "softs"]
VARIANTS = {"metals": ("metals", PRODUCTS["metals"]), "petroleum": ("energy", PRODUCTS["petroleum"]), "energy": ("energy", PRODUCTS["energy"]),
            "energy_exng": ("energy", [p for p in PRODUCTS["energy"] if p != "NatGas"]), "ngl": ("ngl", PRODUCTS["ngl"]),
            "precious": ("precious", PRODUCTS["precious"]), "agri": ("agri", PRODUCTS["agri"]), "softs": ("softs", PRODUCTS["softs"])}
LABEL = {"pen": "Gas and Emissions", "petroleum": "Petroleum", "metals": "Metals", "energy": "Energy", "energy_exng": "Energy ex-NatGas", "ngl": "NGL", "precious": "Precious Metals", "agri": "Agriculture", "softs": "Softs"}
WINDOWS = {"full": ("2012-01-01", None), "p1": ("2012-01-01", "2016-12-31"), "p2": ("2017-01-01", "2021-12-31"), "p3": ("2022-01-01", None)}
D = json.load(open(os.path.join(REPO, "outputs", "final_dashboard_0930", "final_v3.json")))
_nets = None


def nets():
    global _nets
    if _nets is None:
        _nets = pickle.load(open(os.path.join(REPO, "outputs", "final_dashboard_0930", "products_nets.pkl"), "rb"))[0]
    return _nets


def stats(r, w="full"):
    s, e = WINDOWS[w]
    r = (r.loc[s:e] if e else r.loc[s:]).dropna()
    if len(r) < 20 or r.std(ddof=1) == 0:
        return None
    ret = (np.exp(252 * r.mean()) - 1) * 100
    vol = np.expm1(r).std(ddof=1) * np.sqrt(252) * 100
    cum = np.exp(r.cumsum()); mdd = (cum / cum.cummax() - 1).min() * 100
    return dict(ret=ret, vol=vol, mdd=mdd, ir=ret / vol)


def ew_intersection(series):
    cum = [s.cumsum() for s in series]
    idx = cum[0].index
    for c in cum[1:]:
        idx = idx.intersection(c.index)
    idx = idx.sort_values()
    return sum(c.reindex(idx).diff() for c in cum) / len(cum)


def inverse_vol(df, n=63):
    sig = df.rolling(n).std(ddof=1).shift(1).replace(0, np.nan)
    inv = 1 / sig
    w = inv.div(inv.sum(axis=1, skipna=False), axis=0)
    return (w * df).sum(axis=1, skipna=False).where(w.notna().all(axis=1))


def class_sleeves(variant, sleeves=SLEEVES):
    return pd.DataFrame({k: ew_intersection([nets()[m][k] for m in MEMBERS[variant]]) for k in sleeves})


def class_portfolios(variant, sleeves=SLEEVES):
    df = class_sleeves(variant, sleeves)
    return df.mean(axis=1, skipna=False), inverse_vol(df)


def yearly_log(r):
    r = r.loc["2012-01-01":].dropna()
    return r.groupby(r.index.year).sum()
