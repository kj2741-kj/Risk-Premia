"""Classical Portfolio (user, 2026-11-15): the two most liquid products of Petroleum, Base Metals, Precious, Agriculture and Softs, ten products.
Liquidity = Calendar-2025 x on the 12-month strip (Analysis/Liquidity_Cal2025_results.csv, column x_strip); the held-contract column gives the same top two.
Construction is the seven-bucket book's, line for line (analyze_v3.py): product sleeves from products_nets.pkl, each style combined across the bucket's
products with combine_cross_asset, bucket EW PORT / Inverse Vol (63d) across the five styles, book = the five buckets on common dates under the four
two-stage combinations, plus the By Style book. Reported from 2012 in Full / P1 / P2 / P3 / 2026 YTD with run_regime_table._metrics.
Basis 0930 only. Output: Analysis/Classical_Portfolio_0930.xlsx. Run from the repo root:  FD_TAG=0930 python scripts/final_dashboard/classical_portfolio.py
Checks (assert): (1) the same functions applied to fd_config.BUCKETS reproduce final_v3.json (bucket tabs, combined book, By Style) to its 3-decimal rounding;
(2) an independent re-implementation (plain pandas, no project combine functions) of the Classical EW sleeves / EW across book matches to 1e-12;
(3) the ten chosen products are the top two per bucket by x_strip and by x_held."""
import json
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "research"); sys.path.insert(0, "research/configs"); sys.path.insert(0, "scripts"); sys.path.insert(0, "scripts/final_dashboard")
from engine import combine_returns
from cross_asset_engine import combine_cross_asset
from run_regime_table import _metrics
from fd_config import BUCKETS, STYLES, current_tag, out_dir, check_run

TAG = current_tag()
assert TAG == "0930", "Classical Portfolio is on the 0930 basis only"
check_run(TAG)
OUT = out_dir(TAG)
nets, meta = pickle.load(open(OUT / "products_nets.pkl", "rb"))
ref = json.load(open(OUT / "final_v3.json"))
REPORT_START = "2012-01-01"
WINDOWS = [("full", REPORT_START, None), ("p1", "2012-01-01", "2016-12-31"), ("p2", "2017-01-01", "2021-12-31"), ("p3", "2022-01-01", "2026-12-31"), ("y26", "2026-01-01", None)]
WLAB = {"full": "Full 2012-", "p1": "P1 2012-16", "p2": "P2 2017-21", "p3": "P3 2022-", "y26": "2026 YTD"}

# ---------- product choice from the liquidity file (check 3) ----------
LIQ_BUCKET = {"petroleum": ["Brent", "WTI", "SingaporeGasoil", "HeatingOil", "RBOB"], "metals": ["Copper", "Aluminium", "Zinc", "Lead"],
              "precious": ["Gold", "Silver", "Platinum", "Palladium"], "agri": ["Corn", "Wheat", "Soybean", "LiveCattle"], "softs": ["Sugar", "Cocoa", "Coffee", "Cotton"]}
NEWGEN = "--newgen" in sys.argv      # "Classical + New gen Energy" (user, 2026-11-15): adds the top two of Gas and Emissions and NGL, same rule
if NEWGEN:
    LIQ_BUCKET = {**LIQ_BUCKET, "pen": ["NatGas", "TTF", "UKGas", "EUA"], "ngl": ["Ethane", "Propane", "Butane", "Naphtha", "NatGasoline"]}
for b in LIQ_BUCKET:
    assert set(LIQ_BUCKET[b]) == {p for _, p in BUCKETS[b][1]}, b          # the liquidity lists are exactly the published bucket members
liq = pd.read_csv("Analysis/Liquidity_Cal2025_results.csv").set_index("product")
CHOICE = {}
for b, prods in LIQ_BUCKET.items():
    top_strip = list(liq.loc[prods, "x_strip"].sort_values(ascending=False).index[:2])
    top_held = list(liq.loc[prods, "x_held"].sort_values(ascending=False).index[:2])
    assert set(top_strip) == set(top_held), (b, top_strip, top_held)
    CHOICE[b] = top_strip
module = {m[1]: m[0] for _, (_, ms) in BUCKETS.items() for m in ms}
ALL = "--all" in sys.argv            # research variant (2026-11-15): every product of the five buckets, no liquidity cut
if ALL:
    CHOICE = {b: [p for _, p in BUCKETS[b][1]] for b in LIQ_BUCKET}
    assert all(set(CHOICE[b]) == set(LIQ_BUCKET[b]) for b in LIQ_BUCKET)
CLASSICAL = {b: (BUCKETS[b][0], [(module[p], p) for p in CHOICE[b]]) for b in LIQ_BUCKET}
if ALL:
    assert all(CLASSICAL[b][1] == BUCKETS[b][1] for b in CLASSICAL)       # same members, same order as the published bucket tabs
NPROD = sum(len(v[1]) for v in CLASSICAL.values())
print("Classical members:", {b: CHOICE[b] for b in CHOICE})
assert not (ALL and NEWGEN)
assert NPROD == (21 if ALL else 14 if NEWGEN else 10)
NAME = f"Classical {'all products' if ALL else '+ New gen Energy' if NEWGEN else 'top 2'} ({NPROD} products)"
OUTFILE = f"Analysis/Classical_Portfolio{'_AllProducts' if ALL else '_NewGenEnergy' if NEWGEN else ''}_0930.xlsx"


# ---------- construction (copied from analyze_v3.py, parameterised by the bucket dict) ----------
def align_intersection(lst):
    cum = [x.cumsum() for x in lst]
    idx = cum[0].index
    for c in cum[1:]:
        idx = idx.intersection(c.index)
    idx = idx.sort_values()
    return [c.reindex(idx).diff() for c in cum], idx


def ac_series(members):
    styles = {}
    for st in STYLES:
        ser = [nets[m][st] for m in members if not nets[m][st].empty]
        styles[st] = combine_cross_asset(ser) if len(ser) > 1 else ser[0]
    lst = list(styles.values())
    return styles, combine_returns(lst, "equal_weight"), combine_returns(lst, "inverse_vol", vol_window=63)


def build(buckets):
    keys = list(buckets)
    acs = {}
    for k, (_, members) in buckets.items():
        styles, ew, iv = ac_series(members)
        acs[k] = dict(styles=styles, ew=ew, iv=iv)
    books = {}
    for m1, t1 in (("ew", "EW"), ("iv", "Inverse Vol")):
        al, idx = align_intersection([acs[k][m1] for k in keys])
        for m2, t2 in (("equal_weight", "EW"), ("inverse_vol", "Inverse Vol")):
            books[f"{t1} sleeves, {t2} across"] = combine_returns(al, m2, vol_window=63)
    srows = {}
    for st in STYLES:
        al, _ = align_intersection([acs[k]["styles"][st] for k in keys])
        srows[st] = combine_returns(al, "equal_weight")
    lst = list(srows.values())
    bystyle = {**srows, "EW PORT": combine_returns(lst, "equal_weight"), "Inverse Vol": combine_returns(lst, "inverse_vol", vol_window=63)}
    return acs, books, bystyle


def metrics_rows(rows):
    out = []
    for name, s in rows.items():
        for w, a, e in WINDOWS:
            m = _metrics(s.loc[a:e] if e else s.loc[a:])
            out.append(dict(series=name, window=WLAB[w], ret_pct=m["ret"], vol_pct=m["vol"], ir=m["ir"], mdd_pct=m["mdd"]))
    return out


def close(a, b, tol=0.0006):
    return (a is None and (b is None or np.isnan(b))) or (a is not None and abs(a - b) <= tol)


# ---------- check 1: the copied construction reproduces the published seven-bucket results ----------
acs7, books7, bys7 = build(BUCKETS)
n_cmp = 0
for k in BUCKETS:
    rows = dict(acs7[k]["styles"]); rows["EW PORT"] = acs7[k]["ew"]; rows["Inverse Vol"] = acs7[k]["iv"]
    for w, a, e in WINDOWS:
        for r in ref["tabs"][k]["windows"][w]:
            m = _metrics(rows[r["name"]].loc[a:e] if e else rows[r["name"]].loc[a:])
            for f in ("ir", "ret", "vol", "mdd"):
                assert close(r[f], m[f]), (k, w, r["name"], f, r[f], m[f]); n_cmp += 1
for w, a, e in WINDOWS:
    for r in ref["combined"]["windows"][w]:
        if r["name"] in books7:
            m = _metrics(books7[r["name"]].loc[a:e] if e else books7[r["name"]].loc[a:])
            for f in ("ir", "ret", "vol", "mdd"):
                assert close(r[f], m[f]), ("book", w, r["name"], f); n_cmp += 1
    for r in ref["bystyle"]["windows"][w]:
        m = _metrics(bys7[r["name"]].loc[a:e] if e else bys7[r["name"]].loc[a:])
        for f in ("ir", "ret", "vol", "mdd"):
            assert close(r[f], m[f]), ("bystyle", w, r["name"], f); n_cmp += 1
print(f"check 1 PASS: {n_cmp} published seven-bucket numbers reproduced")

# ---------- Classical Portfolio ----------
acsC, booksC, bysC = build(CLASSICAL)


if ALL:   # check 1b: with every product, the five bucket portfolios must equal the published bucket tabs exactly
    for k in CLASSICAL:
        for nm in ("ew", "iv"):
            a, b = acsC[k][nm].dropna(), acs7[k][nm].dropna()
            assert a.index.equals(b.index) and float((a - b).abs().max()) == 0.0, (k, nm)
        for st in STYLES:
            assert acsC[k]["styles"][st].dropna().equals(acs7[k]["styles"][st].dropna()), (k, st)
    print("check 1b PASS: five bucket portfolios identical to the published bucket tabs")

# ---------- check 2: independent re-implementation of EW sleeves, EW across (plain pandas) ----------
def inter_diff(series):
    df = pd.concat([s.cumsum() for s in series], axis=1, join="inner").sort_index()
    return df.diff()


bucket_ew = []
for k, (_, members) in CLASSICAL.items():
    style_lines = []
    for st in STYLES:
        d = inter_diff([nets[m][st] for m in members])
        style_lines.append(d.mean(axis=1, skipna=False))
    d = inter_diff([s.dropna() for s in style_lines]) if len({tuple(s.dropna().index) for s in style_lines}) > 1 else pd.concat(style_lines, axis=1)
    bucket_ew.append(d.mean(axis=1, skipna=False))
indep = inter_diff([s.dropna() for s in bucket_ew]).mean(axis=1, skipna=False)
mine = booksC["EW sleeves, EW across"]
j = indep.dropna().index.intersection(mine.dropna().index)
diff = float((indep.loc[j] - mine.loc[j]).abs().max())
m_i, m_m = _metrics(indep.loc[REPORT_START:]), _metrics(mine.loc[REPORT_START:])
print(f"check 2: max |indep - engine| = {diff:.2e} on {len(j)} days; IR indep {m_i['ir']:.6f} engine {m_m['ir']:.6f}")
assert diff < 1e-12 and abs(m_i["ir"] - m_m["ir"]) < 1e-9

# ---------- output ----------
rows_b = []
for k, (label, members) in CLASSICAL.items():
    r = dict(acsC[k]["styles"]); r["EW PORT"] = acsC[k]["ew"]; r["Inverse Vol"] = acsC[k]["iv"]
    for x in metrics_rows(r):
        rows_b.append(dict(bucket=label, products=" + ".join({"SingaporeGasoil": "Gas Oil"}.get(p, p) for _, p in members), **x))
book_rows = [dict(book=NAME, **x) for x in metrics_rows(booksC)] + [dict(book="Seven-bucket book (30 products)", **x) for x in metrics_rows(books7)]
bys_rows = [dict(book=NAME, **x) for x in metrics_rows(bysC)] + [dict(book="Seven-bucket book (30 products)", **x) for x in metrics_rows(bys7)]
al, idx = align_intersection([acsC[k]["ew"] for k in CLASSICAL])
corr = pd.concat(al, axis=1, keys=[CLASSICAL[k][0] for k in CLASSICAL]).loc[REPORT_START:].dropna().corr().round(3)
prod = pd.DataFrame([dict(bucket=CLASSICAL[b][0], product=p, x_strip_usd_m=liq.loc[p, "x_strip"], x_held_usd_m=liq.loc[p, "x_held"], K_over_x_days=liq.loc[p, "L_strip"],
                          first_data=str(meta[(module[p], p)]["first"])[:10], carry_pairs=", ".join("-".join(x) for x in meta[(module[p], p)]["pairs"])) for b in CHOICE for p in CHOICE[b]])
info = pd.DataFrame({"item": ["basis", "book common dates", "products", "construction", "selection caveat", "checks"],
                     "value": ["0930 (prices to 2026-09-30), reported from 2012-01-01", f"{idx.min().date()} to {idx.max().date()}",
                               "; ".join(f"{CLASSICAL[b][0]}: {', '.join(CHOICE[b])}" for b in CHOICE),
                               "Same as the seven-bucket book (analyze_v3.py): combine_cross_asset per style within bucket, EW / Inverse Vol (63d) across five styles, buckets on common dates, four two-stage combinations, By Style book",
                               "Products picked with Calendar-2025 liquidity and applied to a 2012 backtest (look-ahead in selection, same convention as the Isobutane removal)",
                               f"check 1: {n_cmp} published numbers reproduced; check 2: independent EW/EW book max diff {diff:.1e}; check 3: top two by x_strip = top two by x_held"]})
with pd.ExcelWriter(OUTFILE) as xw:
    info.to_excel(xw, "Info", index=False)
    pd.DataFrame(book_rows).to_excel(xw, "Book", index=False)
    pd.DataFrame(bys_rows).to_excel(xw, "By Style", index=False)
    pd.DataFrame(rows_b).to_excel(xw, "Buckets", index=False)
    corr.to_excel(xw, "Bucket corr (EW PORT)")
    prod.to_excel(xw, "Products", index=False)
print("common dates", idx.min().date(), idx.max().date())
print(pd.DataFrame(book_rows).query("window=='Full 2012-'").round(3).to_string(index=False))
print(pd.DataFrame(bys_rows).query("window=='Full 2012-'").round(3).to_string(index=False))
for w in ("P1 2012-16", "P2 2017-21", "P3 2022-", "2026 YTD"):
    print(w, pd.DataFrame(book_rows).query("window==@w")[["book", "series", "ir"]].round(2).values.tolist())
print(pd.DataFrame(rows_b).query("window=='Full 2012-'")[["bucket", "series", "ir", "vol_pct", "mdd_pct"]].round(2).to_string(index=False))
print(corr)

# ---------- dashboard JSON (2026-11-15): one tab per published variant (top 2 and + New gen Energy), read by build_final_dashboard_v3.py ----------
# Same window and rounding conventions as analyze_v3.py (win / f3 / equity). Tracked under Analysis/_classical_build/ so a rebuild on any machine has it.
if not ALL:
    f3 = lambda d: {k: (None if pd.isna(v) else round(float(v), 3)) for k, v in d.items()}
    win = lambda rows: {w: [dict(name=k, **f3(_metrics(v.loc[s:e] if e else v.loc[s:]))) for k, v in rows.items()] for w, s, e in WINDOWS}

    def equity(rows, step=5):
        df = pd.concat(rows, axis=1, keys=list(rows.keys())).loc[REPORT_START:]
        df = df.fillna(0.0).cumsum().iloc[::step]
        return dict(dates=[d.strftime("%Y-%m-%d") for d in df.index], series={k: [round(float(x), 5) for x in df[k]] for k in df.columns})

    dash = {}
    dash.update(booksC)
    dash.update({f"By Style: {k}": v for k, v in bysC.items()})
    alr, _ = align_intersection([acsC[k]["ew"] for k in CLASSICAL])
    dash.update({f"Reference: {CLASSICAL[k][0]} ({' + '.join({'SingaporeGasoil': 'Gas Oil', 'NatGas': 'Henry Hub'}.get(p, p) for _, p in CLASSICAL[k][1])}) EW PORT": a for k, a in zip(CLASSICAL, alr)})
    if NEWGEN:
        base = {b: CLASSICAL[b] for b in CLASSICAL if b not in ("pen", "ngl")}
        _, booksT, _ = build(base)
        dash["Reference: Classical (10 products), EW sleeves, EW across"] = booksT["EW sleeves, EW across"]
        dash["Reference: Classical (10 products), Inverse Vol sleeves, EW across"] = booksT["Inverse Vol sleeves, EW across"]
    dash["Reference: seven-bucket book (30 products), EW sleeves, EW across"] = books7["EW sleeves, EW across"]
    dash["Reference: seven-bucket book (30 products), Inverse Vol sleeves, EW across"] = books7["Inverse Vol sleeves, EW across"]
    key = "classical_ng" if NEWGEN else "classical"
    jout = dict(key=key, label="Classical + New gen Energy" if NEWGEN else "Classical", n_products=NPROD,
                members=[dict(bucket=CLASSICAL[b][0], products=[{"SingaporeGasoil": "Gas Oil", "NatGas": "Henry Hub"}.get(p, p) for _, p in CLASSICAL[b][1]]) for b in CLASSICAL],
                common_first=str(idx.min().date()), common_last=str(idx.max().date()), windows=win(dash), equity=equity(dash))
    # the dashboard rows must equal the Excel rows (same series, same metric function)
    xl = pd.DataFrame(book_rows)
    xl = xl[(xl.window == "Full 2012-") & (xl.book == NAME)].set_index("series")["ir"]
    n_eq = 0
    for r in jout["windows"]["full"]:
        if r["name"] in booksC:
            assert abs(r["ir"] - float(xl.loc[r["name"]])) < 5e-4, r["name"]; n_eq += 1
    assert n_eq == 4
    from pathlib import Path
    Path("Analysis/_classical_build").mkdir(exist_ok=True)
    json.dump(jout, open(f"Analysis/_classical_build/{key}_0930.json", "w"))
    print("dashboard json written", key, {r["name"]: r["ir"] for r in jout["windows"]["full"]})
