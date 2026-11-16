"""Liquidity penalty (variant b: penalty and flat 5 bps netted over a product's five sleeves) applied to the Classical + New gen Energy portfolio (2026-11-15).
Run from the repo root:  FD_TAG=0930 python scripts/final_dashboard/classical_penalty.py [--classical]
Same construction as classical_portfolio.py (copied: align_intersection, ac_series, build) on the penalised product sleeves. Book weights: each of the 14 products carries
1 / (7 buckets x 2 products) of the capital (10 products: 1 / (5 x 2) with --classical), split over five sleeves by liquidity_penalty.per_unit_participation.
Check: with no penalty and per-sleeve flat cost (the committed sleeves) the four books reproduce Analysis/_classical_build/classical_ng_0930.json (or classical_0930.json)."""
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
import liquidity_penalty as lp

TAG = current_tag()
assert TAG == "0930"
check_run(TAG)
OUT = out_dir(TAG)
CLASSICAL_ONLY = "--classical" in sys.argv
nets, meta = pickle.load(open(OUT / "products_nets.pkl", "rb"))
trades, sigs = pickle.load(open(OUT / "products_trades.pkl", "rb"))
pos, phases = pickle.load(open(OUT / "products_pos.pkl", "rb"))
liq = pd.read_csv("Analysis/Liquidity_Cal2025_results.csv").set_index("product")
module = {m[1]: m[0] for _, (_, ms) in BUCKETS.items() for m in ms}
BKTS = ["petroleum", "metals", "precious", "agri", "softs"] + ([] if CLASSICAL_ONLY else ["pen", "ngl"])
CHOICE = {b: list(liq.loc[[p for _, p in BUCKETS[b][1]], "x_strip"].sort_values(ascending=False).index[:2]) for b in BKTS}
CLASSICAL = {b: (BUCKETS[b][0], [(module[p], p) for p in CHOICE[b]]) for b in BKTS}
REF = json.load(open(f"Analysis/_classical_build/{'classical' if CLASSICAL_ONLY else 'classical_ng'}_0930.json"))
WINDOWS = [("full", "2012-01-01", None), ("p1", "2012-01-01", "2016-12-31"), ("p2", "2017-01-01", "2021-12-31"), ("p3", "2022-01-01", "2026-12-31"), ("y26", "2026-01-01", None)]
members = [m for b in CLASSICAL for m in CLASSICAL[b][1]]
W = {m: 1.0 / (len(CLASSICAL) * len(CLASSICAL[b][1])) for b in CLASSICAL for m in CLASSICAL[b][1]}
VOL = lp.daily_notional_volume()


def align_intersection(lst):
    cum = [x.cumsum() for x in lst]
    idx = cum[0].index
    for c in cum[1:]:
        idx = idx.intersection(c.index)
    idx = idx.sort_values()
    return [c.reindex(idx).diff() for c in cum], idx


def build(nt):
    acs = {}
    for k, (_, mem) in CLASSICAL.items():
        styles = {}
        for st in STYLES:
            ser = [nt[m][st] for m in mem if not nt[m][st].empty]
            styles[st] = combine_cross_asset(ser) if len(ser) > 1 else ser[0]
        lst = list(styles.values())
        acs[k] = dict(styles=styles, ew=combine_returns(lst, "equal_weight"), iv=combine_returns(lst, "inverse_vol", vol_window=63))
    keys = list(CLASSICAL)
    books = {}
    for m1, t1 in (("ew", "EW"), ("iv", "Inverse Vol")):
        al, _ = align_intersection([acs[k][m1] for k in keys])
        for m2, t2 in (("equal_weight", "EW"), ("inverse_vol", "Inverse Vol")):
            books[f"{t1} sleeves, {t2} across"] = combine_returns(al, m2, vol_window=63)
    srows = {}
    for st in STYLES:
        al, _ = align_intersection([acs[k]["styles"][st] for k in keys])
        srows[st] = combine_returns(al, "equal_weight")
    lst = list(srows.values())
    bys = {**srows, "EW PORT": combine_returns(lst, "equal_weight"), "Inverse Vol": combine_returns(lst, "inverse_vol", vol_window=63)}
    books.update({f"By Style: {k}": v for k, v in bys.items()})
    alr, _ = align_intersection([acs[k]["ew"] for k in keys])
    books.update({f"Reference: {CLASSICAL[k][0]} ({' + '.join({'NatGas': 'Henry Hub'}.get(p, p) for _, p in CLASSICAL[k][1])}) EW PORT": a for k, a in zip(keys, alr)})
    return books


sub = {m: nets[m] for m in members}
base = build(sub)
for r in REF["windows"]["full"]:                       # check: unpenalised sleeves reproduce the published tab
    if r["name"] in base:
        assert abs(_metrics(base[r["name"]].loc["2012-01-01":])["ir"] - r["ir"]) < 6e-4, r["name"]
print("check PASS: unpenalised books reproduce", "classical" if CLASSICAL_ONLY else "classical_ng", "tab")

pk = lambda d: {m: d[m] for m in members}
scen = {"No penalty (committed, per-sleeve 5 bps)": base}
scen["Flat 5 bps netted, no penalty"] = build(lp.netted_nets(sub, pk(trades), pk(sigs), pk(pos), pk(phases), W, VOL, "none", 0.0, "b"))
for model in lp.MODELS:
    for cap in lp.CAPITALS_M:
        scen[f"{model} ${cap}M"] = build(lp.netted_nets(sub, pk(trades), pk(sigs), pk(pos), pk(phases), W, VOL, model, float(cap), "b"))

f3 = lambda d: {k: (None if pd.isna(v) else round(float(v), 3)) for k, v in d.items()}
names = [n for n in base if not n.startswith("By Style: ") or n in ("By Style: EW PORT", "By Style: Inverse Vol")]
res = {s: {n: {w: f3(_metrics(b[n].loc[a:e] if e else b[n].loc[a:])) for w, a, e in WINDOWS} for n in names} for s, b in scen.items()}
tag = "classical" if CLASSICAL_ONLY else "classical_ng"
json.dump(dict(members={b: CHOICE[b] for b in CHOICE}, weights={f"{m[1]}": W[m] for m in members}, res=res), open(OUT / f"{tag}_pen_b.json", "w"))
print("products:", CHOICE, "\nweight per product:", round(next(iter(W.values())), 4))
print("per-unit participation (share of a day's volume, one full sleeve unit) at $250M and $1B:")
for m in members:
    print(f"  {m[1]:12s} {lp.per_unit_participation(250, W[m], VOL[m[1]]):7.1%} {lp.per_unit_participation(1000, W[m], VOL[m[1]]):7.1%}")
print("\nFull-sample IR (2012-)")
tab = pd.DataFrame({s: {n: res[s][n]["full"]["ir"] for n in names} for s in res}).T
print(tab.round(2).to_string())
print("\nFull-sample max drawdown % / return % / vol %, EW sleeves EW across")
print(pd.DataFrame({s: {k: res[s]["EW sleeves, EW across"]["full"][k] for k in ("ret", "vol", "ir", "mdd")} for s in res}).T.round(2).to_string())
print("\nEW/EW IR by window")
print(pd.DataFrame({s: {w: res[s]["EW sleeves, EW across"][w]["ir"] for w, _, _ in WINDOWS} for s in res}).T.round(2).to_string())


# ---------- payload for the penalty page (windows + equity in the classical tab's own format; the other-book Reference rows are dropped) ----------
def equity(rows, step=5):
    df = pd.concat(rows, axis=1, keys=list(rows.keys())).loc["2012-01-01":].fillna(0.0).cumsum().iloc[::step]
    return dict(dates=[d.strftime("%Y-%m-%d") for d in df.index], series={k: [round(float(x), 5) for x in df[k]] for k in df.columns})


win = lambda rows: {w: [dict(name=k, **f3(_metrics(v.loc[a:e] if e else v.loc[a:]))) for k, v in rows.items()] for w, a, e in WINDOWS}
pay = {}
for s, b in scen.items():
    key = {"Flat 5 bps netted, no penalty": "none_0"}.get(s) or (None if s.startswith("No penalty") else s.replace(" $", "_").replace("M", ""))
    if key:
        pay[key] = dict(windows=win(b), equity=equity(b))
json.dump(pay, open(OUT / f"{tag}_pen_b_page.json", "w"))
# check: the unpenalised books reproduce every row of the published tab that this payload carries
ref_w = {r["name"]: r for r in REF["windows"]["full"]}
bw = {r["name"]: r for r in win(base)["full"]}
n = 0
for nm, r in bw.items():
    if nm in ref_w:
        assert abs(r["ir"] - ref_w[nm]["ir"]) < 6e-4 and abs(r["ret"] - ref_w[nm]["ret"]) < 6e-3, nm; n += 1
print("page payload keys:", list(pay), "| rows matched to the published tab:", n, "of", len(bw))
