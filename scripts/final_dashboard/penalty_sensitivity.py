"""Sensitivity of the liquidity penalty by portfolio level (2026-11-15). Run from the repo root:  FD_TAG=0930 python scripts/final_dashboard/penalty_sensitivity.py
-> outputs/final_dashboard_0930/penalty_sensitivity.json (read by build_penalty_sensitivity_page.py).

Levels and the capital C of the portfolio itself (USD millions; user lists, 2026-11-15):
  commodity (one product's five-sleeve portfolio)   1, 5, 10, 25, 50, 100      the product holds C
  asset class (bucket portfolio, 5 products)        5, 25, 50, 125, 250, 500    each of the bucket's n products holds C / n
  commodity pair (two buckets blended 50/50)        2, 10, 20, 50, 100     each bucket gets C / 2, each of its n products C / (2 n)
  cross-commodity book (seven buckets, 30 products) 25, 100, 250, 500, 1000, 2000   each bucket gets C / 7, each of its n products C / (7 n)
US Power is not in the book or the pairs (seven buckets only). Models: square-root and linear above P0 = 10% (liquidity_penalty.py), variant b (penalty and 5 bps netted over a product's
five sleeves, in DOLLARS). Base = the 5 bps netted across sleeves in dollars, no penalty.
DAILY WEIGHTS (user, 2026-11-15): the dollars one unit of a sleeve's position holds on a day = C x bucket weight x (1 / n products) x style weight, with the weights the portfolio actually uses
that day. Equal Weight: constants (1/5, 1/n, 1/7 or 1/2). Inverse Vol: 1 / trailing 63-day vol of the series being blended, lagged one day, normalised (the engine.combine_returns formula), computed on
the unpenalised (5 bps netted) series so the penalty does not feed back into its own weights. Commodity level: the product's five sleeves; asset class: the bucket's five style series; pair: the two
bucket portfolios and their styles; book: sleeves by the first method, buckets by the second. Before the first weights exist (63-day burn-in) the Equal Weight split is used. A change of weights
alone is not a trade (the dashboard does not charge for rebalancing).
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


def inv_vol_weights(series_list, window=63):
    """Daily weights engine.combine_returns(..., 'inverse_vol') applies to these series (columns in order); NaN before the burn-in ends."""
    idx = series_list[0].index
    for s in series_list[1:]:
        idx = idx.union(s.index)
    rets = pd.concat([s.reindex(idx) for s in series_list], axis=1)
    vol = rets.rolling(window, min_periods=window).std(ddof=1).shift(1)
    iv = 1.0 / vol.replace(0.0, np.nan)
    return iv.div(iv.sum(axis=1, skipna=False), axis=0)


def make_unit(cap, wb, n, ws, fb=1.0 / 7):
    """USD millions held by one unit of each sleeve: cap x wb(t) / n x ws(t). wb: float or Series (indexed by date); ws: None (Equal Weight, 1/styles) or DataFrame (columns = styles)."""
    def f(key, idx, styles):
        k = 1.0 / len(styles)
        w = pd.DataFrame(k, index=idx, columns=styles) if ws is None else ws[styles].reindex(ws.index.union(idx)).ffill().reindex(idx).fillna(k)
        if isinstance(wb, pd.Series):
            b = wb.reindex(wb.index.union(idx)).ffill().reindex(idx).fillna(fb)
            return w.mul(b, axis=0) * (cap / n)
        return w * (cap * wb / n)
    return f


def bucket_series(nets, key):
    members = BUCKETS[key][1]
    styles = {}
    for st in STYLES:
        ser = [nets[m][st] for m in members if not nets[m][st].empty]
        styles[st] = combine_cross_asset(ser) if len(ser) > 1 else ser[0]
    lst = list(styles.values())
    return combine_returns(lst, "equal_weight"), combine_returns(lst, "inverse_vol", vol_window=63), styles


def context():
    """Weights from the unpenalised (5 bps netted) series; computed once per process."""
    if "ctx" in G:
        return G["ctx"]
    if not G.get("nets"):
        init()
    keys = G["prods"]
    sub = lambda d: {k: d[k] for k in keys}
    base = lp.netted_nets(G["nets"], sub(G["trades"]), sub(G["sigs"]), sub(G["pos"]), sub(G["ph"]), {k: 0.0 for k in keys}, G["vol"], "none", 0.0, "b")
    c = dict(wprod={m: inv_vol_weights([base[m][s] for s in STYLES]).set_axis(STYLES, axis=1) for m in keys}, wstyle={}, port={}, bw={}, pw={})
    for k in KEYS:
        ew, iv, styles = bucket_series(base, k)
        c["port"][k] = dict(ew=ew, iv=iv)
        c["wstyle"][k] = inv_vol_weights([styles[s] for s in STYLES]).set_axis(STYLES, axis=1)
    for m1 in ("ew", "iv"):
        al, _ = align_intersection([c["port"][k][m1] for k in KEYS])
        c["bw"][m1] = inv_vol_weights(al).set_axis(KEYS, axis=1)                 # book: Inverse Vol across the seven buckets built with method m1
    for a, b in combinations(KEYS, 2):
        al, _ = align_intersection([c["port"][a]["iv"], c["port"][b]["iv"]])
        c["pw"][(a, b)] = inv_vol_weights(al).set_axis([a, b], axis=1)
    G["ctx"] = c
    return c


CACHE = {}


def bucket_port(k, cap, wb, m1, model, fb=1.0 / 7):
    """The bucket portfolio (method m1) with the penalty charged on the dollars its products actually hold. wb: float or Series = the bucket's weight in the larger portfolio."""
    ck = None if isinstance(wb, pd.Series) else (k, cap, model, m1, wb)
    if ck is not None and ck in CACHE:
        return CACHE[ck]
    c = context()
    mem = BUCKETS[k][1]
    sub = lambda d: {m: d[m] for m in mem}
    unit = make_unit(cap, wb, len(mem), None if m1 == "ew" else c["wstyle"][k], fb)
    nets = lp.netted_nets_dyn(sub(G["nets"]), sub(G["trades"]), sub(G["sigs"]), sub(G["pos"]), sub(G["ph"]), unit, G["vol"], model)
    r = bucket_series(nets, k)[0 if m1 == "ew" else 1]
    if ck is not None:
        CACHE[ck] = r
    return r


def run(job):
    level, cap, model = job
    c = context()
    C = 1.0 if model == "none" else float(cap)            # base: how the flat cost nets does not depend on the scale of C
    none = model == "none"
    out = {}
    if level == "commodity":
        for k in KEYS:
            for m in BUCKETS[k][1]:
                rows = {}
                for m1 in ("ew", "iv"):
                    unit = make_unit(C, 1.0, 1, None if m1 == "ew" else c["wprod"][m])
                    nets = lp.netted_nets_dyn({m: G["nets"][m]}, {m: G["trades"][m]}, {m: G["sigs"][m]}, {m: G["pos"][m]}, {m: G["ph"][m]}, unit, G["vol"], model)
                    st = [nets[m][s] for s in STYLES]
                    rows[m1] = combine_returns(st, "equal_weight") if m1 == "ew" else combine_returns(st, "inverse_vol", vol_window=63)
                out[f"{k}|{LABEL.get(m[1], m[1])}"] = ir_rows(rows)
    elif level == "bucket":
        for k in KEYS:
            out[k] = ir_rows({m1: bucket_port(k, C, 1.0, m1, model) for m1 in ("ew", "iv")})
    elif level == "book":
        rows = {}
        for m1 in ("ew", "iv"):
            for m2, meth in (("ew", "equal_weight"), ("iv", "inverse_vol")):
                ports = [bucket_port(k, C, 1.0 if none else (1.0 / len(KEYS) if m2 == "ew" else c["bw"][m1][k]), m1, model) for k in KEYS]
                al, _ = align_intersection(ports)
                rows[f"{m1}_{m2}"] = combine_returns(al, meth, vol_window=63)
        out["book"] = ir_rows(rows)
    else:
        for a, b in combinations(KEYS, 2):
            rows = {}
            for m1, meth in (("ew", "equal_weight"), ("iv", "inverse_vol")):
                if m1 == "ew":
                    ports = [bucket_port(k, C, 1.0 if none else 0.5, "ew", model) for k in (a, b)]
                else:
                    ports = [bucket_port(k, C, 1.0 if none else c["pw"][(a, b)][k], "iv", model, 0.5) for k in (a, b)]
                al, _ = align_intersection(ports)
                rows[m1] = combine_returns(al, meth, vol_window=63)
            out[f"{a}|{b}"] = ir_rows(rows)
    return job, out


if __name__ == "__main__":
    jobs = [(lv, 0, "none") for lv in GRID] + [(lv, c, m) for lv in GRID for c in GRID[lv] for m in MODELS]
    res = {}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for (lv, c, m), out in ex.map(run, jobs):
            res[f"{lv}|{c}|{m}"] = out
            print("done", lv, c, m, flush=True)
    old = json.load(open(out_dir(current_tag()) / "penalty_sensitivity_static.json"))["res"]
    n = 0
    for key, rows in res.items():
        for nm, mm in rows.items():
            for meth, wv in mm.items():
                if meth in ("ew", "ew_ew"):
                    assert abs(wv["full"] - old[key][nm][meth]["full"]) < 1e-9, (key, nm, meth, wv["full"], old[key][nm][meth]["full"]); n += 1
    print("check 1 PASS: Equal Weight cells equal the static-weight run:", n)
    tag = current_tag()
    ref = json.load(open(out_dir(tag) / "final_v3_pen_none_0_b.json"))
    rb = {r["name"]: r["ir"] for r in ref["combined"]["windows"]["full"]}
    assert abs(res["book|0|none"]["book"]["ew_ew"]["full"] - rb["EW sleeves, EW across"]) < 6e-4
    print("check 2 PASS. Base IR with Inverse Vol sleeves (dollar netting vs unit netting):", {k: (round(res["book|0|none"]["book"][k]["full"], 3), rb[nm]) for k, nm in (("iv_ew", "Inverse Vol sleeves, EW across"), ("iv_iv", "Inverse Vol sleeves, Inverse Vol across"))})
    buckets = {k: dict(label=BUCKETS[k][0], n=len(BUCKETS[k][1])) for k in KEYS}
    json.dump(dict(grid=GRID, models=MODELS, windows=[w for w, _, _ in WINDOWS], buckets=buckets, res=res), open(out_dir(tag) / "penalty_sensitivity.json", "w"))
    print("saved")
