"""Independent recomputation of the five-sleeve 2012 results from the per-product net log returns, written from
Research_Methodology_v4 (not from analyze_v2.py), compared with the dataset embedded in Dimil's committed HTML."""
import sys, os, json, pickle
import numpy as np, pandas as pd
REPO = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia"
S = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(S, "dimil_D.json")))
nets, meta = pickle.load(open(os.path.join(REPO, "outputs", "final_dashboard_2012", "products_2012_nets.pkl"), "rb"))

SLEEVES = ["Momentum", "Carry", "CarryMom", "Value", "Skewness"]
PRODUCTS = {"metals": ["Copper", "Aluminium", "Lead", "Zinc"], "energy": ["WTI", "Brent", "RBOB", "HeatingOil", "NatGas"],
            "ngl": ["Ethane", "Propane", "Butane", "Isobutane"], "precious": ["Gold", "Silver", "Platinum", "Palladium"],
            "agri": ["Corn", "Wheat", "Soybean", "SoybeanOil", "Coffee", "Sugar"]}
WINDOWS = {"full": ("2012-01-01", None), "p1": ("2012-01-01", "2016-12-31"), "p2": ("2017-01-01", "2021-12-31"), "p3": ("2022-01-01", None)}


def stats(r, w):
    s, e = WINDOWS[w]
    r = r.loc[s:e] if e else r.loc[s:]
    r = r.dropna()
    if len(r) < 20 or r.std(ddof=1) == 0:
        return None
    ret = (np.exp(252 * r.mean()) - 1) * 100
    vol = np.expm1(r).std(ddof=1) * np.sqrt(252) * 100
    cum = np.exp(r.cumsum()); mdd = (cum / cum.cummax() - 1).min() * 100
    return dict(ret=ret, vol=vol, mdd=mdd, ir=ret / vol)


def ew_intersection(series):
    """Section 9.1: cumulative level, restricted to common dates, differenced, averaged."""
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


def sleeves_for(asset, prods):
    return pd.DataFrame({k: ew_intersection([nets[(asset, p)][k] for p in prods]) for k in SLEEVES})


def portfolios(df):
    return df.mean(axis=1, skipna=False), inverse_vol(df)


results = {}
variants = {"metals": ("metals", PRODUCTS["metals"]), "energy": ("energy", PRODUCTS["energy"]),
            "energy_exng": ("energy", [p for p in PRODUCTS["energy"] if p != "NatGas"]), "ngl": ("ngl", PRODUCTS["ngl"]),
            "precious": ("precious", PRODUCTS["precious"]), "agri": ("agri", PRODUCTS["agri"])}
ac_port = {}
worst, n_cmp, bad = 0.0, 0, []


def compare(tag, mine, theirs):
    global worst, n_cmp
    for m in ("ret", "vol", "mdd", "ir"):
        if mine is None or theirs.get(m) is None:
            if (mine is None) != (theirs.get(m) is None):
                bad.append((tag, m, mine, theirs.get(m)))
            continue
        d = abs(mine[m] - theirs[m]); n_cmp += 1; worst = max(worst, d)
        if d > 0.0015:
            bad.append((tag, m, round(mine[m], 4), theirs[m]))


for t, (a, prods) in variants.items():
    df = sleeves_for(a, prods)
    ew, iv = portfolios(df)
    ac_port[t] = (ew, iv)
    for w in WINDOWS:
        rows = {r["name"]: r for r in D["tabs"][t]["windows"][w]}
        for k in SLEEVES:
            compare(f"tab {t} {w} {k}", stats(df[k], w), rows[k])
        compare(f"tab {t} {w} EW PORT", stats(ew, w), rows["EW PORT"])
        compare(f"tab {t} {w} Inverse Vol", stats(iv, w), rows["Inverse Vol"])
print(f"asset-class tabs: compared {n_cmp} numbers, worst abs difference {worst:.4f}, mismatches (>0.0015): {len(bad)}")
for b in bad[:12]:
    print("   ", b)

# products
n0, w0, b0 = n_cmp, worst, len(bad)
for key, d in D["products"].items():
    a, p = key.split("|")
    for k in SLEEVES:
        for w in WINDOWS:
            compare(f"prod {key} {k} {w}", stats(nets[(a, p)][k], w), d[k][w])
print(f"products: compared {n_cmp - n0} numbers, mismatches: {len(bad) - b0}")
for b in bad[b0:b0 + 8]:
    print("   ", b)

# combined books: sleeves stage (EW / IV) x across stage (EW / IV), five asset classes, with and without NatGas
def book(use_exng):
    keys = ["metals", "energy_exng" if use_exng else "energy", "ngl", "precious", "agri"]
    sleeve_tabs = {t: sleeves_for(*variants[t]) for t in keys}
    out = {}
    for s_stage in ("EW", "IV"):
        ac = {}
        for t in keys:
            ew, iv = portfolios(sleeve_tabs[t]); ac[t] = ew if s_stage == "EW" else iv
        ac_df = pd.DataFrame({t: ac[t] for t in keys})
        cum = [ac[t].dropna().cumsum() for t in keys]
        idx = cum[0].index
        for c in cum[1:]:
            idx = idx.intersection(c.index)
        idx = idx.sort_values()
        al = pd.DataFrame({t: c.reindex(idx).diff() for t, c in zip(keys, cum)})
        out[f"{s_stage} sleeves, EW across"] = al.mean(axis=1, skipna=False)
        out[f"{s_stage} sleeves, IV across"] = inverse_vol(al)
    return out, sleeve_tabs, keys


for flag, name in ((False, "all5"), (True, "all5_exng")):
    books, sleeve_tabs, keys = book(flag)
    n0, b0 = n_cmp, len(bad)
    for w in WINDOWS:
        rows = {r["name"]: r for r in D["combined"][name]["windows"][w]}
        for nm, ser in books.items():
            label = {"EW sleeves, EW across": "EW sleeves, EW across", "EW sleeves, IV across": "EW sleeves, Inverse Vol across",
                     "IV sleeves, EW across": "Inverse Vol sleeves, EW across", "IV sleeves, IV across": "Inverse Vol sleeves, Inverse Vol across"}[nm]
            if label in rows:
                compare(f"{name} {w} {label}", stats(ser, w), rows[label])
    print(f"combined {name}: compared {n_cmp - n0} numbers, mismatches {len(bad) - b0}; row names in dataset: {[r['name'] for r in D['combined'][name]['windows']['full']]}")
    for b in bad[b0:b0 + 6]:
        print("   ", b)

# By Style books
for flag, name in ((False, "with NatGas"), (True, "ex-NatGas")):
    keys = ["metals", "energy_exng" if flag else "energy", "ngl", "precious", "agri"]
    tabs = {t: sleeves_for(*variants[t]) for t in keys}
    style = {}
    for k in SLEEVES:
        style[k] = ew_intersection([tabs[t][k].dropna() for t in keys])
    sdf = pd.DataFrame(style).dropna()
    # Dimil: styles combined on common dates; IV across styles
    ew = sdf.mean(axis=1, skipna=False); iv = inverse_vol(sdf)
    n0, b0 = n_cmp, len(bad)
    for w in WINDOWS:
        rows = {r["name"]: r for r in D["bystyle"][name]["windows"][w]}
        for k in SLEEVES:
            compare(f"bystyle {name} {w} {k}", stats(sdf[k], w), rows[k])
        for lab, ser in (("EW PORT", ew), ("Inverse Vol", iv)):
            if lab in rows:
                compare(f"bystyle {name} {w} {lab}", stats(ser, w), rows[lab])
    print(f"by style {name}: compared {n_cmp - n0}, mismatches {len(bad) - b0}; names {[r['name'] for r in D['bystyle'][name]['windows']['full']]}")
    for b in bad[b0:b0 + 6]:
        print("   ", b)

# Cross pairs
from itertools import combinations
for flag, name in ((False, "with NatGas"), (True, "ex-NatGas")):
    keys = ["metals", "energy_exng" if flag else "energy", "ngl", "precious", "agri"]
    n0, b0 = n_cmp, len(bad)
    for meth in ("EW", "Inverse Vol"):
        for w in WINDOWS:
            rows = {r["name"]: r for r in D["crosspair"][name][meth][w]}
            for a, b in combinations(keys, 2):
                pa = ac_port[a][0 if meth == "EW" else 1]; pb = ac_port[b][0 if meth == "EW" else 1]
                cum = [pa.dropna().cumsum(), pb.dropna().cumsum()]
                idx = cum[0].index.intersection(cum[1].index).sort_values()
                al = pd.DataFrame({a: cum[0].reindex(idx).diff(), b: cum[1].reindex(idx).diff()})
                ser = al.mean(axis=1, skipna=False) if meth == "EW" else inverse_vol(al)
                lab = [r for r in rows if r.replace("(ex-NatGas)", "").replace("ex-NatGas", "").replace(" ", "").lower() in
                       (f"{a}-{b}".replace("energy_exng", "energy").replace("_", "").lower(), f"{b}-{a}".replace("energy_exng", "energy").replace("_", "").lower())]
                nm = {"metals": "Metals", "energy": "Energy", "energy_exng": "Energy", "ngl": "NGL", "precious": "Precious", "agri": "Agriculture"}
                cand = [r for r in rows if nm[a].replace(" ", "") in r.replace(" ", "") and nm[b].replace(" ", "") in r.replace(" ", "")]
                if len(cand) == 1:
                    compare(f"pair {name} {meth} {w} {cand[0]}", stats(ser, w), rows[cand[0]])
                else:
                    bad.append((f"pair label match {a}-{b}", "name", [r for r in rows][:3], cand))
    print(f"cross pairs {name}: compared {n_cmp - n0}, mismatches {len(bad) - b0}")
    for b in bad[b0:b0 + 6]:
        print("   ", b)
print(f"TOTAL compared {n_cmp} numbers; worst abs difference {worst:.4f}; mismatches {len(bad)}")
