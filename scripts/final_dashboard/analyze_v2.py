"""Analysis stage for the rebuilt final dashboard -> outputs/final_dashboard/final_v2.json
Inputs: products_v2_nets.pkl (compute_products.py). Methods: EW and Inverse Vol (63d trailing vol) only.
Sections: asset-class tabs (Metals, Energy, Energy ex-NatGas, NGL, Precious, Agriculture), combined books (all 5 with / without NatGas),
cross-pair portfolios (10 pairs), correlations (within, cross-asset-class, rolling), equity curves. Run from the repo root."""
import sys, json, pickle
from itertools import combinations
from pathlib import Path

sys.path.insert(0, "research"); sys.path.insert(0, "research/configs"); sys.path.insert(0, "scripts")
import numpy as np
import pandas as pd
from engine import combine_returns
from cross_asset_engine import combine_cross_asset
from run_regime_table import _metrics
from regimes import REGIMES, REPORT_START

OUT = Path("outputs/final_dashboard")
nets, meta = pickle.load(open(OUT / "products_v2_nets.pkl", "rb"))
STYLES = ("Momentum", "Carry", "CarryMom", "Value")
PRODUCTS = {"metals": ["Copper", "Aluminium", "Lead", "Zinc"], "energy": ["WTI", "Brent", "RBOB", "HeatingOil", "NatGas"],
            "ngl": ["Ethane", "Propane", "Butane", "Isobutane"], "precious": ["Gold", "Silver", "Platinum", "Palladium"],
            "agri": ["Corn", "Wheat", "Soybean", "SoybeanOil", "Coffee", "Sugar"]}
VARIANTS = [("metals", "metals", PRODUCTS["metals"]), ("energy", "energy", PRODUCTS["energy"]),
            ("energy_exng", "energy", [p for p in PRODUCTS["energy"] if p != "NatGas"]),
            ("ngl", "ngl", PRODUCTS["ngl"]), ("precious", "precious", PRODUCTS["precious"]), ("agri", "agri", PRODUCTS["agri"])]
WINDOWS = [("full", REPORT_START, None)] + [(n.split("_")[0].lower(), s, e) for n, s, e in REGIMES] + [("y26", "2026-01-01", None)]
f3 = lambda d: {k: (None if pd.isna(v) else round(float(v), 3)) for k, v in d.items()}
win = lambda rows: {w: [dict(name=k, **f3(_metrics(v.loc[s:e] if e else v.loc[s:]))) for k, v in rows.items()] for w, s, e in WINDOWS}


def align_intersection(lst):
    cum = [x.cumsum() for x in lst]
    idx = cum[0].index
    for c in cum[1:]:
        idx = idx.intersection(c.index)
    idx = idx.sort_values()
    return [c.reindex(idx).diff() for c in cum], idx


def ac_series(asset, prods):
    styles = {}
    for st in STYLES:
        ser = [nets[(asset, p)][st] for p in prods if not nets[(asset, p)][st].empty]
        styles[st] = combine_cross_asset(ser) if len(ser) > 1 else ser[0]
    lst = list(styles.values())
    return styles, combine_returns(lst, "equal_weight"), combine_returns(lst, "inverse_vol", vol_window=63)


def equity(rows, step=5):
    """Cumulative LOG return from REPORT_START, sampled every `step` trading days (JS rebases and converts to % return)."""
    df = pd.concat(rows, axis=1, keys=list(rows.keys())).loc[REPORT_START:]
    df = df.fillna(0.0).cumsum().iloc[::step]
    return dict(dates=[d.strftime("%Y-%m-%d") for d in df.index], series={k: [round(float(x), 5) for x in df[k]] for k in df.columns})


res = {"tabs": {}, "products": {}, "combined": {}, "crosspair": {}, "corr": {}, "equity": {}, "meta": {}}
acs = {}
for key, asset, prods in VARIANTS:
    styles, ew, iv = ac_series(asset, prods)
    acs[key] = dict(styles=styles, ew=ew, iv=iv)
    rows = dict(styles); rows["EW PORT"] = ew; rows["Inverse Vol"] = iv
    res["tabs"][key] = dict(products=prods, windows=win(rows),
                            data_first=max(meta[(asset, p)]["first"] for p in prods), data_last=min(meta[(asset, p)]["last"] for p in prods),
                            pairs={p: ["-".join(x) for x in meta[(asset, p)]["pairs"]] for p in prods},
                            rolls={p: meta[(asset, p)]["rolls"] for p in prods})
    res["equity"][key] = equity(rows)
    print("tab", key, {r["name"]: r["ir"] for r in res["tabs"][key]["windows"]["full"]}, flush=True)

# per product detail (full sample + regimes IR)
for key, asset, prods in VARIANTS:
    if key == "energy_exng":
        continue
    for p in prods:
        d = {}
        for k, s in nets[(asset, p)].items():
            d[k] = {w: f3(_metrics(s.loc[st:e] if e else s.loc[st:])) for w, st, e in WINDOWS}
        res["products"][f"{asset}|{p}"] = d

# combined books
KEYS = {"all5": ["metals", "energy", "ngl", "precious", "agri"], "all5_exng": ["metals", "energy_exng", "ngl", "precious", "agri"]}
for label, keys in KEYS.items():
    books = {}
    for m1, t1 in (("ew", "EW"), ("iv", "Inverse Vol")):
        al, idx = align_intersection([acs[k][m1] for k in keys])
        for m2, t2 in (("equal_weight", "EW"), ("inverse_vol", "Inverse Vol")):
            books[f"{t1} sleeves, {t2} across"] = combine_returns(al, m2, vol_window=63)
    al, idx = align_intersection([acs[k]["ew"] for k in keys])
    ref = {f"Reference: {k} EW PORT": a for k, a in zip(keys, al)}
    res["combined"][label] = dict(windows=win({**books, **ref}), members=keys, common_first=str(idx.min().date()), common_last=str(idx.max().date()))
    res["equity"][label] = equity({**books, **ref})
    print("combined", label, res["combined"][label]["common_first"], res["combined"][label]["common_last"],
          {k: v["ir"] for k, v in zip(list({**books}.keys()), res["combined"][label]["windows"]["full"])}, flush=True)

# by-style book: each style (sleeve) equal-weighted across the asset classes (common dates), then the four style series combined by EW and Inverse Vol
res["bystyle"] = {}
for label, keys in (("with NatGas", KEYS["all5"]), ("ex-NatGas", KEYS["all5_exng"])):
    srows = {}
    for st in STYLES:
        al, _ = align_intersection([acs[k]["styles"][st] for k in keys])
        srows[st] = combine_returns(al, "equal_weight")
    lst = list(srows.values())
    rows = {**srows, "EW PORT": combine_returns(lst, "equal_weight"), "Inverse Vol": combine_returns(lst, "inverse_vol", vol_window=63)}
    first = max(r.first_valid_index() for r in srows.values())
    res["bystyle"][label] = dict(windows=win(rows), members=keys, common_first=str(first.date()), common_last=str(min(r.index.max() for r in srows.values()).date()))
    res["equity"]["bystyle " + label] = equity(rows)
    print("bystyle", label, {r["name"]: r["ir"] for r in res["bystyle"][label]["windows"]["full"]}, flush=True)

# cross-pair portfolios: two asset classes' own portfolios blended 50/50 (EW) or by Inverse Vol, on the pair's common dates
PAIRS = [(a, b) for a, b in combinations(["metals", "energy", "precious", "ngl", "agri"], 2)]
LABEL = {"metals": "Metals", "energy": "Energy", "energy_exng": "Energy ex-NatGas", "precious": "Precious", "ngl": "NGL", "agri": "Agriculture"}
for variant, sub in (("with NatGas", {}), ("ex-NatGas", {"energy": "energy_exng"})):
    out = {}
    for cons, m in (("EW", "equal_weight"), ("Inverse Vol", "inverse_vol")):
        series = {}
        for a, b in PAIRS:
            ka, kb = sub.get(a, a), sub.get(b, b)
            m1 = "ew" if cons == "EW" else "iv"            # each asset class portfolio built with the same method as the blend
            al, _ = align_intersection([acs[ka][m1], acs[kb][m1]])
            series[f"{LABEL[ka]} - {LABEL[kb]}"] = combine_returns(al, m, vol_window=63)
        out[cons] = win(series)
    res["crosspair"][variant] = out

# correlations (2011+): within asset class, across asset classes (common dates), rolling (common dates)
ROWS = list(STYLES) + ["EW PORT", "Inverse Vol"]
CORR_AC = ["metals", "energy", "precious", "ngl", "agri"]
for key, asset, prods in VARIANTS:
    d = acs[key]
    df = pd.concat({**d["styles"], "EW PORT": d["ew"], "Inverse Vol": d["iv"]}, axis=1).loc[REPORT_START:].dropna()
    res["corr"].setdefault("within", {})[key] = [[round(float(x), 3) for x in r] for r in df[ROWS].corr().values]
cross = {}
for r in ROWS:
    getter = (lambda k: acs[k]["styles"][r]) if r in STYLES else (lambda k: acs[k]["ew"] if r == "EW PORT" else acs[k]["iv"])
    al, idx = align_intersection([getter(k) for k in CORR_AC])
    df = pd.concat(al, axis=1, keys=CORR_AC).loc[REPORT_START:].dropna()
    cross[r] = [[round(float(x), 3) for x in rr] for rr in df.corr().values]
    cross.setdefault("_n", {})[r] = int(len(df))   # sample size per strategy row (Inverse Vol rows start later: NGL Inverse Vol is undefined before 2012-02-22)
res["corr"]["cross"] = cross
res["corr"]["rows"] = ROWS
al, idx = align_intersection([acs[k]["ew"] for k in CORR_AC])
dates = [d for d in idx if d >= pd.Timestamp(REPORT_START)]
rc_series = {}
for m1, nm in (("ew", "ew"), ("iv", "iv")):
    al, idx = align_intersection([acs[k][m1] for k in CORR_AC])
    df = pd.concat(al, axis=1, keys=CORR_AC).loc[REPORT_START:].dropna()
    rc_series[nm] = dict(dates=[d.strftime("%Y-%m-%d") for d in df.index], series={k: [round(float(x), 6) for x in df[k]] for k in CORR_AC})   # dates kept per method: the two samples differ in length
assert all(len(v["dates"]) == len(s) for v in rc_series.values() for s in v["series"].values())
res["corr"]["rolling"] = rc_series
res["meta"] = dict(data_last={a: min(meta[(a, p)]["last"] for p in PRODUCTS[a]) for a in PRODUCTS},
                   rolls={f"{a}|{p}": meta[(a, p)]["rolls"] for (a, p) in meta},
                   pairs={f"{a}|{p}": ["-".join(x) for x in meta[(a, p)]["pairs"]] for (a, p) in meta})
json.dump(res, open(OUT / "final_v2.json", "w"))
print("saved final_v2.json", (OUT / "final_v2.json").stat().st_size // 1024, "KB")
