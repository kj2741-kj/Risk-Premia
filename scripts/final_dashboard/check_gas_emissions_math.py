"""Second audit of the Gas and Emissions bucket (2026-11-04): independent math + the cross-asset layer.
  A. UK Gas (and TTF) continuous return series rebuilt from the raw curve and the calendar with plain pandas, compared with the engine's log_price.
  B. ret / vol / IR / max drawdown recomputed with their definitions from UK Gas sleeves and from the bucket portfolio, compared with the dashboard JSON.
  C. The Streamlit/hub engine (cross_asset_engine, all six buckets) vs the HTML pipeline (final_v3.json): bucket tabs, by-style book, the four combined books, all 15
     cross-pairs and the cross-bucket correlations, including the Gas and Emissions bucket.
Run from the repo root:  RP_PRICES_DIR=Prices_1029_merged FD_TAG=1029 python scripts/final_dashboard/check_gas_emissions_math.py   (or Prices_0930 / 0930).
The engine step takes about ten minutes; its per-product series are cached in outputs/final_dashboard_<tag>/engine_per_product.pkl (delete to refresh)."""
import os, sys, json, pickle, warnings
from itertools import combinations
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
fails = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)
    if not ok:
        fails.append(name)
WIN = {"full": ("2012-01-01", None), "p1": ("2012-01-01", "2016-12-31"), "p2": ("2017-01-01", "2021-12-31"), "p3": ("2022-01-01", None), "y26": ("2026-01-01", None)}
f3 = lambda d: {k: (None if pd.isna(v) else round(float(v), 3)) for k, v in d.items()}
sl = lambda s, w: s.loc[WIN[w][0]:WIN[w][1]] if WIN[w][1] else s.loc[WIN[w][0]:]

# ---------------- A. continuous series from the raw curve ------------------------------------------------------------------------------------------------------
PX = f"data/{os.environ['RP_PRICES_DIR']}/Emissions_Futures_Updated.xlsx"; CAL = f"data/{os.environ['RP_PRICES_DIR']}/Emissions_Expiry_Calendars.xlsx"
import emissions as em
for prod, psheet, csheet in (("UKGas", "UK Gas NBP (ICE)", "FN - UK Gas NBP (ICE)"), ("TTF", "TTF Natural Gas (ICE Endex)", "TZT - TTF Gas (ICE Endex)")):
    raw = pd.read_excel(PX, sheet_name=psheet, header=1); raw["Date"] = pd.to_datetime(raw["Date"], errors="coerce")
    curve = raw.dropna(subset=["Date"]).set_index("Date").sort_index().apply(pd.to_numeric, errors="coerce").loc[em.ANALYSIS_STARTS[prod]:]
    ltd = pd.to_datetime(pd.read_excel(CAL, sheet_name=csheet)["LAST_TRADEABLE_DT"]).sort_values().reset_index(drop=True)
    idx = curve.index; cols = list(curve.columns)
    pos = {t: i for i, t in enumerate(idx)}
    # roll day of contract k: 5th trading day of the month of its last trade date
    roll = {}
    for k, l in enumerate(ltd):
        mm = idx[(idx.year == l.year) & (idx.month == l.month)]
        roll[k] = mm[4] if len(mm) >= 5 else None
    f1k = np.searchsorted(ltd.values, idx.values, side="left")          # first contract with LTD >= t  (generic F1 at t)
    held = np.empty(len(idx), dtype=int)
    for i, t in enumerate(idx):
        k = f1k[i]; r = roll.get(k)
        # repo-wide engine convention: on the roll day the position already earns the NEXT contract's return, i.e. the roll is made at the previous close
        nxt = idx[i + 1] if i + 1 < len(idx) else None
        held[i] = k + 1 if (r is not None and nxt is not None and r <= nxt and t <= ltd[k]) else k
    px = curve.values
    ind = np.full(len(idx), np.nan)
    for i in range(1, len(idx)):
        h = held[i - 1]; a = h - f1k[i] ; b = h - f1k[i - 1]
        if 0 <= a < px.shape[1] and 0 <= b < px.shape[1]:
            p1, p0 = px[i, a], px[i - 1, b]
            if p1 > 0 and p0 > 0:
                ind[i] = np.log(p1 / p0)
    eng = (em.load_f1_series_logret(prod)["log_price"].diff()).reindex(idx)
    both = pd.DataFrame({"ind": ind, "eng": eng.values}, index=idx).dropna()
    d = (both.ind - both.eng).abs()
    check(f"A. {prod}: independent continuous returns == engine log_price diffs ({len(both)} days)", d.max() < 1e-9,
          f"max abs diff {d.max():.2e}, days differing {int((d > 1e-9).sum())}, engine NaN days {int(eng.isna().sum())}")

# ---------------- B. metric definitions --------------------------------------------------------------------------------------------------------------------------
def my_metrics(s):
    s = s.dropna()
    if len(s) < 20 or s.std(ddof=1) == 0:
        return dict(ret=None, vol=None, mdd=None, ir=None)
    ret = (np.exp(s.mean() * 252) - 1) * 100
    vol = np.expm1(s).std(ddof=1) * np.sqrt(252) * 100
    v = np.exp(s.cumsum()); mdd = (v / v.cummax() - 1).min() * 100
    return dict(ret=round(float(ret), 3), vol=round(float(vol), 3), mdd=round(float(mdd), 3), ir=round(float(ret / vol), 3))
bad = tot = 0
for a, p in [("emissions", "UKGas"), ("emissions", "TTF"), ("emissions", "EUA"), ("energy", "NatGas")]:
    for s_, ser in nets[(a, p)].items():
        for w in WIN:
            m1 = my_metrics(sl(ser, w)); m2 = res["products"][f"{a}|{p}"][s_][w]
            tot += 1; bad += any(abs((m1[k] or 0) - (m2[k] or 0)) > 0.0011 for k in m1)
check(f"B. ret/vol/IR/MDD recomputed by hand == dashboard JSON (4 Gas and Emissions products, {tot} sleeve-windows)", bad == 0, f"{bad} differences")
# the bucket: equal-weight of products per sleeve (intersection convention), then equal-weight of the five sleeves
members = [("energy", "NatGas"), ("emissions", "TTF"), ("emissions", "UKGas"), ("emissions", "EUA")]
def align(lst):
    cum = [x.cumsum() for x in lst]; idx = cum[0].index
    for c in cum[1:]:
        idx = idx.intersection(c.index)
    idx = idx.sort_values(); return [c.reindex(idx).diff() for c in cum]
STY = ("Momentum", "Carry", "CarryMom", "Value", "Skewness")
styles = {s_: sum(align([nets[m][s_] for m in members])) / len(members) for s_ in STY}
ew = sum(styles.values()) / len(STY)
bad = 0
for w in WIN:
    for r_i, row in enumerate(res["tabs"]["pen"]["windows"][w]):
        ser = styles.get(row["name"], ew if row["name"] == "EW PORT" else None)
        if ser is None:
            continue
        m1 = my_metrics(sl(ser, w)); bad += any(abs((m1[k] or 0) - (row[k] or 0)) > 0.0011 for k in m1)
check("B. Gas and Emissions bucket (5 sleeves + EW PORT) rebuilt by hand from the product series == dashboard tab", bad == 0, f"{bad} differences")
print("   bucket sleeves are combined on the products' common dates:", str(ew.dropna().index.min().date()), "to", str(ew.dropna().index.max().date()))

# ---------------- C. engine (Streamlit/hub) vs HTML pipeline, all six buckets ---------------------------------------------------------------------------------
BK = ["metals", "petroleum", "pen", "ngl", "precious", "agri"]
def engine_run(cache, value_min):
    """Per-product engine series for the six buckets; value_min=504 applies the research dashboard's Value warm-up (the engine default is 630 observations)."""
    if cache.exists():
        return pickle.load(open(cache, "rb"))
    orig = cae.value_v1_position
    if value_min:
        cae.value_v1_position = lambda *a, **k: orig(*a, min_periods=value_min, **k)
    try:
        pp = {ac: cae.per_product_four_row(ac, 5, per_product_pairs=True, include_skewness=True) for ac in BK}
    finally:
        cae.value_v1_position = orig
    pickle.dump(pp, open(cache, "wb")); return pp
PP0 = pickle.load(open(D / "engine_per_product.pkl", "rb")) if (D / "engine_per_product.pkl").exists() else (engine_run(D / "engine_per_product.pkl", None) if os.environ.get("CHECK_SHIPPED_ENGINE") else None)   # the engine as the Streamlit apps run it (slow: set CHECK_SHIPPED_ENGINE=1 to build)
PP = engine_run(D / "engine_per_product_v504.pkl", 504)       # the same with the research Value warm-up
check("C. engine bucket list and order == HTML", list(cae.ALL_ASSET_CLASSES) == BK == res["meta"]["keys"], str(cae.ALL_ASSET_CLASSES))
# the only difference between the engine as shipped and the research series (from 2012-01-01) must be the Value warm-up
M0 = {"Momentum": "Momentum", "Combined Carry": "Carry", "Combined CarryMom": "CarryMom", "Value": "Value", "Skewness": "Skewness"}
AC = {"metals": "metals", "petroleum": "energy", "ngl": "ngl", "precious": "precious", "agri": "agri"}
diffs = {}
for ac in BK:
    for sty, lab in M0.items():
        for nm, net in zip(PP[ac][sty]["names"], PP[ac][sty]["net"]):
            a_ = AC.get(ac) or ("energy" if nm == "NatGas" else "emissions")
            r = nets[(a_, nm)][lab]; idx = r.index.union(net.index)
            d = (r.reindex(idx).fillna(0) - net.reindex(idx).fillna(0)).abs().loc["2012-01-01":]
            if d.max() > 1e-9: diffs[(ac, nm, lab)] = d.max()
check("C. engine with the research Value warm-up (504): all 27 products x 5 sleeves == research series from 2012", not diffs, str(list(diffs)[:5]))
d0 = {}
for ac in (BK if PP0 else []):
    for sty, lab in M0.items():
        for nm, n0, n1 in zip(PP0[ac][sty]["names"], PP0[ac][sty]["net"], PP[ac][sty]["net"]):
            idx = n0.index.union(n1.index); d = (n0.reindex(idx).fillna(0) - n1.reindex(idx).fillna(0)).abs().loc["2012-01-01":]
            if d.max() > 1e-9: d0[(ac, nm, lab)] = str(d[d > 1e-9].index.max().date())
if PP0: check("C. engine as shipped (630) differs from the research series from 2012 ONLY in NGL Value, first half of 2012", all(k[0] == "ngl" and k[2] == "Value" and v < "2012-07-01" for k, v in d0.items()),
      str({k[1]: v for k, v in d0.items()}))
fetch = lambda ac, tc: PP[ac]
own, sty_nets = {}, {}
for ac in BK:
    g4, n4 = cae.asset_class_four_row(ac, 5, None, fetch)
    own[ac] = cae.asset_class_ew_portfolio(g4, n4)[1]; sty_nets[ac] = n4
def rows_equal(rows_html, series_by_name, label, tol=0.0011):
    bad = 0; n = 0
    for w in WIN:
        for r in rows_html[w]:
            if r["name"] in series_by_name:
                m = f3(_metrics(sl(series_by_name[r["name"]], w))); n += 1
                bad += any(abs((m[k] or 0) - (r[k] or 0)) > tol for k in m)
    return bad, n
NAME = {"Combined Carry": "Carry", "Combined CarryMom": "CarryMom"}
for ac in BK:
    series = {NAME.get(k, k): v for k, v in sty_nets[ac].items()}; series["EW PORT"] = own[ac]
    bad, n = rows_equal(res["tabs"][ac]["windows"], series, ac)
    check(f"C. bucket tab '{ac}': engine == HTML ({n} rows)", bad == 0, f"{bad} differences")
# by-style book
g_by, n_by = cae.cross_commodity_dynamic(5, tuple(BK), cae.ALL_STYLE_NAMES, "equal_weight", per_product_fetcher=fetch)
_, n_iv = cae.cross_commodity_dynamic(5, tuple(BK), cae.ALL_STYLE_NAMES, "inverse_vol", per_product_fetcher=fetch)
series = dict(n_by); series["EW PORT"] = n_by["Portfolio"]; series["Inverse Vol"] = n_iv["Portfolio"]
bad, n = rows_equal(res["bystyle"]["windows"], series, "bystyle")
check(f"C. by-style book over six buckets (incl. Gas and Emissions): engine == HTML ({n} rows)", bad == 0, f"{bad} differences")
# combined books: bucket portfolios EW across (and Inverse Vol across)
_, n_cn = cae.cross_n_portfolio(5, tuple(BK), fetch, "equal_weight")
al = align([own[ac] for ac in BK])
books = {"EW sleeves, EW across": n_cn["Portfolio"], "EW sleeves, Inverse Vol across": combine_returns(al, "inverse_vol", vol_window=63)}
bad, n = rows_equal(res["combined"]["windows"], books, "combined")
check(f"C. combined book (EW sleeves; EW and Inverse Vol across the six buckets): engine == HTML ({n} rows)", bad == 0, f"{bad} differences")
refs = {f"Reference: {res['tabs'][ac]['label']} EW PORT": s_ for ac, s_ in zip(BK, align([own[ac] for ac in BK]))}
bad, n = rows_equal(res["combined"]["windows"], refs, "refs")
check(f"C. combined-book reference rows (each bucket on the six-bucket common dates, incl. Gas and Emissions): engine == HTML ({n} rows)", bad == 0, f"{bad} differences")
# cross-pairs
_, cp = cae.cross_pair_portfolios_dynamic(5, tuple(BK), fetch)
bad = n = 0; labels = []
for a, b in combinations(BK, 2):
    lab = f"{res['tabs'][a]['label']} - {res['tabs'][b]['label']}"; labels.append(lab)
    html_rows = {w: res["crosspair"]["EW"][w] for w in WIN}
    eng = cp[cae.cross_pair_label(a, b)]
    for w in WIN:
        r = next(x for x in res["crosspair"]["EW"][w] if x["name"] == lab); m = f3(_metrics(sl(eng, w))); n += 1
        bad += any(abs((m[k] or 0) - (r[k] or 0)) > 0.0011 for k in m)
check(f"C. all {len(labels)} cross-pairs (EW) engine == HTML, {sum('Gas and Emissions' in l for l in labels)} of them with Gas and Emissions ({n} rows)", bad == 0 and len(labels) == 15, f"{bad} differences")
# cross-pair Inverse Vol (HTML-only construction): rebuilt from the engine's bucket Inverse Vol portfolios
iv = {ac: combine_returns(list(sty_nets[ac].values()), "inverse_vol", vol_window=63) for ac in BK}
bad = n = 0
for a, b in combinations(BK, 2):
    lab = f"{res['tabs'][a]['label']} - {res['tabs'][b]['label']}"; ser = combine_returns(align([iv[a], iv[b]]), "inverse_vol", vol_window=63)
    for w in WIN:
        r = next(x for x in res["crosspair"]["Inverse Vol"][w] if x["name"] == lab); m = f3(_metrics(sl(ser, w))); n += 1
        bad += any(abs((m[k] or 0) - (r[k] or 0)) > 0.0011 for k in m)
check(f"C. all 15 cross-pairs (Inverse Vol) rebuilt from engine series == HTML ({n} rows)", bad == 0, f"{bad} differences")
# correlations across buckets (EW PORT), from the REPORT_START
al = align([own[ac] for ac in BK]); df = pd.concat(al, axis=1, keys=BK).loc["2012-01-01":].dropna()
mine = np.round(df.corr().values, 3); html = np.array(res["corr"]["cross"]["EW PORT"])
check("C. cross-bucket correlation matrix (EW PORT, six buckets): engine == HTML", np.abs(mine - html).max() < 0.0011 and len(df) == res["corr"]["cross"]["_n"]["EW PORT"],
      f"max abs diff {np.abs(mine - html).max():.4f}, n {len(df)} vs {res['corr']['cross']['_n']['EW PORT']}; Gas and Emissions row {mine[2].tolist()}")
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
