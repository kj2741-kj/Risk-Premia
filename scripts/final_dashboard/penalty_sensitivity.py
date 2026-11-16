"""Sensitivity of the liquidity penalty by portfolio level (2026-11-15). Run from the repo root:  FD_TAG=0930 python scripts/final_dashboard/penalty_sensitivity.py
-> outputs/final_dashboard_0930/penalty_sensitivity.json (read by build_penalty_sensitivity_page.py).

Levels and the capital C of the portfolio itself (USD millions; user lists, 2026-11-15):
  commodity (one product's five-sleeve portfolio)   1, 5, 10, 25, 50, 100      the product holds C
  asset class (bucket portfolio, 5 products)        5, 25, 50, 125, 250, 500    each of the bucket's n products holds C / n
  commodity pair (two buckets blended 50/50)        2, 10, 20, 50, 100     each bucket gets C / 2, each of its n products C / (2 n)
  cross-commodity book (seven buckets, 30 products) 25, 100, 250, 500, 1000, 2000   each bucket gets C / 7, each of its n products C / (7 n)
US Power is not in the book or the pairs (seven buckets only). Models: square-root and linear above P0 = 10% (liquidity_penalty.py), variant b (penalty and 5 bps netted
over a product's five sleeves). Base = the 5 bps netted across sleeves, no penalty (same netting, no impact cost). Capital weights are static: a product's dollars are the equal split
above on every day, also when the portfolio is blended by Inverse Vol (the penalty is not re-weighted with the Inverse Vol weights).
Cells: the IR of each row on the Full / P1 / P2 / P3 / 2026 windows (research _metrics, same as the dashboard)."""
import json
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from itertools import combinations

import numpy as np
import pandas as pd

sys.path.insert(0, "research"); sys.path.insert(0, "research/configs"); sys.path.insert(0, "scripts"); sys.path.insert(0, "scripts/final_dashboard")
from engine import combine_returns
from cross_asset_engine import combine_cross_asset
from run_regime_table import _metrics
from fd_config import BUCKETS, STYLES, current_tag, out_dir, check_run
import liquidity_penalty as lp

GRID = {"commodity": (1, 5, 10, 25, 50, 100), "bucket": (5, 25, 50, 125, 250, 500), "pair": (2, 10, 20, 50, 100, 200), "book": (25, 100, 250, 500, 1000, 2000)}
MODELS = ("sqrt", "linear")
WINDOWS = [("full", "2012-01-01", None), ("p1", "2012-01-01", "2016-12-31"), ("p2", "2017-01-01", "2021-12-31"), ("p3", "2022-01-01", "2026-12-31"), ("y26", "2026-01-01", None)]
LABEL = {"SingaporeGasoil": "Gas Oil", "HeatingOil": "Heating Oil", "NatGas": "Henry Hub", "UKGas": "UK Gas", "NatGasoline": "Natural Gasoline", "LiveCattle": "Live Cattle"}
KEYS = list(BUCKETS)
G = {}


def init():
    tag = current_tag()
    check_run(tag)
    out = out_dir(tag)
    nets, meta = pickle.load(open(out / "products_nets.pkl", "rb"))
    trades, sigs = pickle.load(open(out / "products_trades.pkl", "rb"))
    pos, ph = pickle.load(open(out / "products_pos.pkl", "rb"))
    prods = [m for _, (_, ms) in BUCKETS.items() for m in ms]
    G.update(nets={m: nets[m] for m in prods}, trades=trades, sigs=sigs, pos=pos, ph=ph, vol=lp.daily_notional_volume(), prods=prods)


def align_intersection(lst):
    cum = [x.cumsum() for x in lst]
    idx = cum[0].index
    for c in cum[1:]:
        idx = idx.intersection(c.index)
    idx = idx.sort_values()
    return [c.reindex(idx).diff() for c in cum], idx


def ir_rows(rows):
    return {name: {w: _metrics(s.loc[a:e] if e else s.loc[a:])["ir"] for w, a, e in WINDOWS} for name, s in rows.items()}


def penalised(model, cp):
    """cp: product key -> capital held by the product, USD millions. model 'none' = 5 bps netted only."""
    keys = G["prods"]
    sub = lambda d: {k: d[k] for k in keys}
    return lp.netted_nets(G["nets"], sub(G["trades"]), sub(G["sigs"]), sub(G["pos"]), sub(G["ph"]), cp, G["vol"], model, 1.0, "b")


def bucket_series(nets, key):
    members = BUCKETS[key][1]
    styles = {}
    for st in STYLES:
        ser = [nets[m][st] for m in members if not nets[m][st].empty]
        styles[st] = combine_cross_asset(ser) if len(ser) > 1 else ser[0]
    lst = list(styles.values())
    return combine_returns(lst, "equal_weight"), combine_returns(lst, "inverse_vol", vol_window=63), styles


def run(job):
    level, cap, model = job
    if not G:
        init()
    nb = {k: len(BUCKETS[k][1]) for k in KEYS}
    owner = {m: k for k in KEYS for m in BUCKETS[k][1]}
    if level == "commodity":
        cp = {m: float(cap) for m in G["prods"]}
    elif level == "bucket":
        cp = {m: cap / nb[owner[m]] for m in G["prods"]}
    elif level == "pair":
        cp = {m: cap / (2 * nb[owner[m]]) for m in G["prods"]}
    else:
        cp = {m: cap / (len(KEYS) * nb[owner[m]]) for m in G["prods"]}
    nets = penalised(model, cp)
    out = {}
    if level == "commodity":
        for k in KEYS:
            for m in BUCKETS[k][1]:
                st = [nets[m][s] for s in STYLES]
                out[f"{k}|{LABEL.get(m[1], m[1])}"] = ir_rows({"ew": combine_returns(st, "equal_weight"), "iv": combine_returns(st, "inverse_vol", vol_window=63)})
        return job, out
    acs = {k: dict(zip(("ew", "iv"), bucket_series(nets, k)[:2])) for k in KEYS}
    if level == "bucket":
        for k in KEYS:
            out[k] = ir_rows(acs[k])
    elif level == "book":
        rows = {}
        for m1 in ("ew", "iv"):
            al, _ = align_intersection([acs[k][m1] for k in KEYS])
            for m2, t2 in (("equal_weight", "ew"), ("inverse_vol", "iv")):
                rows[f"{m1}_{t2}"] = combine_returns(al, m2, vol_window=63)
        out["book"] = ir_rows(rows)
    else:
        for a, b in combinations(KEYS, 2):
            rows = {}
            for m1, m2 in (("ew", "equal_weight"), ("iv", "inverse_vol")):
                al, _ = align_intersection([acs[a][m1], acs[b][m1]])
                rows[m1] = combine_returns(al, m2, vol_window=63)
            out[f"{a}|{b}"] = ir_rows(rows)
    return job, out


if __name__ == "__main__":
    jobs = [(lv, 0, "none") for lv in GRID] + [(lv, c, m) for lv in GRID for c in GRID[lv] for m in MODELS]
    res = {}
    with ProcessPoolExecutor(max_workers=4) as ex:
        for (lv, c, m), out in ex.map(run, jobs):
            res[f"{lv}|{c}|{m}"] = out
            print("done", lv, c, m, flush=True)
    # cross-check: the base netted-only numbers of the book and the committed seven-bucket tab
    tag = current_tag()
    ref = json.load(open(out_dir(tag) / "final_v3_pen_none_0_b.json"))
    rb = {r["name"]: r["ir"] for r in ref["combined"]["windows"]["full"]}
    mine = res["book|0|none"]["book"]
    for k, nm in (("ew_ew", "EW sleeves, EW across"), ("ew_iv", "EW sleeves, Inverse Vol across"), ("iv_ew", "Inverse Vol sleeves, EW across"), ("iv_iv", "Inverse Vol sleeves, Inverse Vol across")):
        assert abs(mine[k]["full"] - rb[nm]) < 6e-4, (k, mine[k]["full"], rb[nm])
    rbk = {r["name"]: r["ir"] for r in ref["tabs"]["ngl"]["windows"]["full"]}
    assert abs(res["bucket|0|none"]["ngl"]["ew"]["full"] - rbk["EW PORT"]) < 6e-4
    print("base check PASS: book (4 books) and NGL bucket equal the 5 bps netted dashboard run")
    buckets = {k: dict(label=BUCKETS[k][0], n=len(BUCKETS[k][1])) for k in KEYS}
    json.dump(dict(grid=GRID, models=MODELS, windows=[w for w, _, _ in WINDOWS], buckets=buckets, res=res), open(out_dir(tag) / "penalty_sensitivity.json", "w"))
    print("saved")
