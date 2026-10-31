"""Analysis stage of the 2012 research dashboard with the new buckets (2026-10-31) -> outputs/final_dashboard_<tag>/final_v3.json (tag from env FD_TAG, default 0930; see fd_config.py)
Input: products_nets.pkl (compute_products_v3.py). Reporting from 2012-01-01 in three periods (P1 2012-2016, P2 2017-2021, P3 2022 onwards) plus a 2026 year-to-date column.
Data through the tag's cutoff (0930: 2026-09-30, 1029: 2026-10-29). Methods: EW and Inverse Vol (63d trailing vol) only, as before.
Buckets (asset-class tabs): Metals, Petroleum (WTI, Brent, RBOB, HeatingOil), Power / Emissions / Nat Gas (NatGas, TTF, EUA), NGL, Precious, Agriculture.
The earlier "Energy" and "Energy ex-NatGas" tabs and every with/without-NatGas variant are gone. Combined book = all six buckets.
Run from the repo root after compute_products_v3.py."""
import json
import pickle
from itertools import combinations
from pathlib import Path

import sys
sys.path.insert(0, "research"); sys.path.insert(0, "research/configs"); sys.path.insert(0, "scripts")
import numpy as np
import pandas as pd
from engine import combine_returns
from cross_asset_engine import combine_cross_asset
from run_regime_table import _metrics

sys.path.insert(0, "scripts/final_dashboard")
from fd_config import TAGS, BUCKETS, STYLES, current_tag, out_dir, check_run
TAG = current_tag()
check_run(TAG)
OUT = out_dir(TAG)
REPORT_START = "2012-01-01"
REGIMES = [("P1_2012_2016", "2012-01-01", "2016-12-31"), ("P2_2017_2021", "2017-01-01", "2021-12-31"), ("P3_2022_onwards", "2022-01-01", "2026-12-31")]
CUTOFF = TAGS[TAG]["cutoff"]
nets, meta = pickle.load(open(OUT / "products_nets.pkl", "rb"))

KEYS = list(BUCKETS)
WINDOWS = [("full", REPORT_START, None)] + [(n.split("_")[0].lower(), s, e) for n, s, e in REGIMES] + [("y26", "2026-01-01", None)]
f3 = lambda d: {k: (None if pd.isna(v) else round(float(v), 3)) for k, v in d.items()}
win = lambda rows: {w: [dict(name=k, **f3(_metrics(v.loc[s:e] if e else v.loc[s:]))) for k, v in rows.items()] for w, s, e in WINDOWS}
pk = lambda a, p: f"{a}|{p}"


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


def equity(rows, step=5):
    """Cumulative LOG return from REPORT_START, sampled every `step` trading days (JS rebases and converts to % return)."""
    df = pd.concat(rows, axis=1, keys=list(rows.keys())).loc[REPORT_START:]
    df = df.fillna(0.0).cumsum().iloc[::step]
    return dict(dates=[d.strftime("%Y-%m-%d") for d in df.index], series={k: [round(float(x), 5) for x in df[k]] for k in df.columns})


res = {"tabs": {}, "products": {}, "combined": {}, "crosspair": {}, "corr": {}, "equity": {}, "meta": {}}
acs = {}
for key, (label, members) in BUCKETS.items():
    styles, ew, iv = ac_series(members)
    acs[key] = dict(styles=styles, ew=ew, iv=iv)
    rows = dict(styles); rows["EW PORT"] = ew; rows["Inverse Vol"] = iv
    res["tabs"][key] = dict(label=label, products=[p for _, p in members], pkeys=[pk(a, p) for a, p in members], windows=win(rows),
                            data_first=max(meta[m]["first"] for m in members), data_last=min(meta[m]["last"] for m in members),
                            pairs={pk(*m): ["-".join(x) for x in meta[m]["pairs"]] for m in members},
                            rolls={pk(*m): meta[m]["rolls"] for m in members})
    res["equity"][key] = equity(rows)
    print("tab", key, {r["name"]: r["ir"] for r in res["tabs"][key]["windows"]["full"]}, flush=True)

# per product detail (full sample + period IRs)
for key, (label, members) in BUCKETS.items():
    for a, p in members:
        d = {}
        for k, s in nets[(a, p)].items():
            d[k] = {w: f3(_metrics(s.loc[st:e] if e else s.loc[st:])) for w, st, e in WINDOWS}
        ew_p = combine_returns([nets[(a, p)][s] for s in STYLES], "equal_weight")
        d["EW PORT"] = {w: f3(_metrics(ew_p.loc[st:e] if e else ew_p.loc[st:])) for w, st, e in WINDOWS}
        res["equity"][f"prod|{a}|{p}"] = equity({**{s: nets[(a, p)][s] for s in STYLES}, "EW PORT": ew_p})
        res["products"][pk(a, p)] = d

# combined book: all six buckets
books = {}
for m1, t1 in (("ew", "EW"), ("iv", "Inverse Vol")):
    al, idx = align_intersection([acs[k][m1] for k in KEYS])
    for m2, t2 in (("equal_weight", "EW"), ("inverse_vol", "Inverse Vol")):
        books[f"{t1} sleeves, {t2} across"] = combine_returns(al, m2, vol_window=63)
al, idx = align_intersection([acs[k]["ew"] for k in KEYS])
ref = {f"Reference: {BUCKETS[k][0]} EW PORT": a for k, a in zip(KEYS, al)}
res["combined"] = dict(windows=win({**books, **ref}), members=KEYS, common_first=str(idx.min().date()), common_last=str(idx.max().date()))
res["equity"]["all6"] = equity({**books, **ref})
print("combined all6", res["combined"]["common_first"], res["combined"]["common_last"], {r["name"]: r["ir"] for r in res["combined"]["windows"]["full"][:4]}, flush=True)

# by-style book: each style equal-weighted across the six buckets (common dates), then the five style series combined by EW and Inverse Vol
srows = {}
for st in STYLES:
    al, _ = align_intersection([acs[k]["styles"][st] for k in KEYS])
    srows[st] = combine_returns(al, "equal_weight")
lst = list(srows.values())
rows = {**srows, "EW PORT": combine_returns(lst, "equal_weight"), "Inverse Vol": combine_returns(lst, "inverse_vol", vol_window=63)}
first = max(r.first_valid_index() for r in srows.values())
res["bystyle"] = dict(windows=win(rows), members=KEYS, common_first=str(first.date()), common_last=str(min(r.index.max() for r in srows.values()).date()))
res["equity"]["bystyle"] = equity(rows)
print("bystyle", {r["name"]: r["ir"] for r in res["bystyle"]["windows"]["full"]}, flush=True)

# cross-pair portfolios: two buckets' own portfolios blended 50/50 (EW) or by Inverse Vol, on the pair's common dates
LABEL = {k: v[0] for k, v in BUCKETS.items()}
for cons, m in (("EW", "equal_weight"), ("Inverse Vol", "inverse_vol")):
    series = {}
    for a, b in combinations(KEYS, 2):
        m1 = "ew" if cons == "EW" else "iv"            # each bucket portfolio built with the same method as the blend
        al, _ = align_intersection([acs[a][m1], acs[b][m1]])
        series[f"{LABEL[a]} - {LABEL[b]}"] = combine_returns(al, m, vol_window=63)
    res["crosspair"][cons] = win(series)

# correlations: within bucket, across buckets (common dates), rolling (common dates)
ROWS = list(STYLES) + ["EW PORT", "Inverse Vol"]
for key in KEYS:
    d = acs[key]
    df = pd.concat({**d["styles"], "EW PORT": d["ew"], "Inverse Vol": d["iv"]}, axis=1).loc[REPORT_START:].dropna()
    res["corr"].setdefault("within", {})[key] = [[round(float(x), 3) for x in r] for r in df[ROWS].corr().values]
cross = {}
for r in ROWS:
    getter = (lambda k: acs[k]["styles"][r]) if r in STYLES else (lambda k: acs[k]["ew"] if r == "EW PORT" else acs[k]["iv"])
    al, idx = align_intersection([getter(k) for k in KEYS])
    df = pd.concat(al, axis=1, keys=KEYS).loc[REPORT_START:].dropna()
    cross[r] = [[round(float(x), 3) for x in rr] for rr in df.corr().values]
    cross.setdefault("_n", {})[r] = int(len(df))
res["corr"]["cross"] = cross
res["corr"]["rows"] = ROWS
rc_series = {}
for nm in ("ew", "iv"):
    al, idx = align_intersection([acs[k][nm] for k in KEYS])
    df = pd.concat(al, axis=1, keys=KEYS).loc[REPORT_START:].dropna()
    rc_series[nm] = dict(dates=[d.strftime("%Y-%m-%d") for d in df.index], series={k: [round(float(x), 6) for x in df[k]] for k in KEYS})
assert all(len(v["dates"]) == len(s) for v in rc_series.values() for s in v["series"].values())
res["corr"]["rolling"] = rc_series
res["meta"] = dict(data_last={k: res["tabs"][k]["data_last"] for k in KEYS}, labels=LABEL, keys=KEYS, cutoff=CUTOFF,
                   rolls={pk(*m): meta[m]["rolls"] for m in meta}, pairs={pk(*m): ["-".join(x) for x in meta[m]["pairs"]] for m in meta})
json.dump(res, open(OUT / "final_v3.json", "w"))
print("saved final_v3.json", (OUT / "final_v3.json").stat().st_size // 1024, "KB")
