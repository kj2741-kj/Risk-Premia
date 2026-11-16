"""Checks of the product-level netting (2026-11-15). Run from the repo root:  FD_TAG=0930 python scripts/final_dashboard/check_netting.py
1. products_nets.pkl after the rerun of compute_products_v3.py equals the backup taken before it (the sleeves did not move).
2. With netting switched off (k = 1) the netted code path reproduces the per-sleeve construction exactly (bucket EW / Inverse Vol, By Style, product EW / IV).
3. Independent recomputation, without the k-scaling device: for Metals (one LME calendar) the bucket EW PORT and Inverse Vol equal
   sum_s a_s * mean_p gross_ps - mean_p netted_cost_p(a), with gross = net + per-sleeve cost and the netted cost from the positions directly.
4. Positions are in {-1, 0, +1}; how often a roll day would net to more units than per sleeve (clipped to per sleeve); savings per bucket."""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "research"); sys.path.insert(0, "research/configs"); sys.path.insert(0, "scripts"); sys.path.insert(0, "scripts/final_dashboard")
import netting
from engine import combine_returns, log_return_transaction_cost
from cross_asset_engine import combine_cross_asset
from fd_config import BUCKETS, STYLES, current_tag, out_dir
import netted_build

TAG = current_tag()
OUT = out_dir(TAG)
fails = []
ok = lambda c, msg: print(("PASS " if c else "FAIL ") + msg) or (None if c else fails.append(msg))

# 1
bk = Path(f"outputs/final_dashboard_{TAG}_pre_netting/products_nets.pkl")
if bk.exists():
    a, _ = pickle.load(open(bk, "rb")); b, _ = pickle.load(open(OUT / "products_nets.pkl", "rb"))
    d = max(float((a[m][s] - b[m][s]).abs().max()) for m in a for s in a[m] if not a[m][s].empty)
    ok(set(a) == set(b) and d == 0.0, f"1. product sleeves unchanged by the rerun (max diff {d})")
NB = netted_build.Netted(OUT, STYLES)
pv = np.unique(np.concatenate([NB.pos[m][s].values for m in NB.pos for s in NB.pos[m]]))
ok(set(pv) <= {-1.0, 0.0, 1.0}, f"4a. positions take only the values {sorted(set(pv))[:6]}")

# 2: k = 1
real = netting.netted
netting.netted = lambda nets, pos, ph, tc, a=None: {s: nets[s] for s in nets}
netted_build.netted = netting.netted
NB0 = netted_build.Netted(OUT, STYLES)
worst = 0.0
for k, (_, members) in BUCKETS.items():
    r = NB0.bucket(members)
    lst = list(r["styles"].values())
    for got, ref in ((r["ew"], combine_returns(lst, "equal_weight")), (r["iv"], combine_returns(lst, "inverse_vol", vol_window=63))):
        assert got.index.equals(ref.index)
        worst = max(worst, float((got - ref).abs().max()))
    for m in members:
        e, i = NB0.product_ports(m)
        lst = [NB0.nets[m][s] for s in STYLES]
        worst = max(worst, float((e - combine_returns(lst, "equal_weight")).abs().max()), float((i - combine_returns(lst, "inverse_vol", vol_window=63)).abs().max()))
ok(worst == 0.0, f"2. netting off reproduces the per-sleeve bucket and product portfolios exactly (max diff {worst})")
netting.netted = real; netted_build.netted = real

# 3: independent Metals recomputation
members = BUCKETS["metals"][1]
r = NB.bucket(members)
idx = NB.nets[members[0]]["Momentum"].index
assert all(NB.nets[m]["Momentum"].index.equals(idx) for m in members)
gross = {m: {s: NB.nets[m][s] + log_return_transaction_cost(NB.pos[m][s].reindex(idx).fillna(0.0), 5, NB.ph[m]) for s in STYLES} for m in members}
for name, a, port in (("EW", pd.DataFrame(0.2, index=idx, columns=list(STYLES)), r["ew"]), ("Inverse Vol", r["w"].set_axis(list(STYLES), axis=1).reindex(idx), r["iv"])):
    g = sum(a[s] * sum(gross[m][s] for m in members) / len(members) for s in STYLES)
    c = sum(netting.netted_cost(pd.DataFrame({s: NB.pos[m][s].reindex(idx).fillna(0.0) for s in STYLES}), NB.ph[m], a.fillna(0.2), 5) for m in members) / len(members)
    ind = (g - c)
    j = port.dropna().index.intersection(ind.dropna().index)[1:]
    d = float((port.loc[j] - ind.loc[j]).abs().max())
    ok(d < 1e-14, f"3. Metals {name}: independent netted portfolio equals the pipeline (max diff {d:.1e} over {len(j)} days)")

# 4: roll-day clipping and savings
clip = tot = 0
for m in NB.pos:
    idx = NB.nets[m]["Momentum"].index
    P = pd.DataFrame({s: NB.pos[m][s].reindex(idx).fillna(0.0) for s in STYLES})
    A = pd.DataFrame(0.2, index=idx, columns=list(STYLES))
    nc = netting.netted_cost(P, NB.ph[m], A, 5)
    pc = (A * netting.sleeve_costs({s: NB.pos[m][s] for s in STYLES}, NB.ph[m], 5, idx)).sum(axis=1)
    clip += int((nc > pc + 1e-15).sum()); tot += len(idx)
    if m in dict((mm, 1) for _, (_, ms) in BUCKETS.items() for mm in ms):
        pass
ok(True, f"4b. EW weights: days where a roll nets to more units than per sleeve (charged per sleeve instead): {clip} of {tot} product-days")
for k, (label, members) in BUCKETS.items():
    sav = []
    for m in members:
        idx = NB.nets[m]["Momentum"].index
        P = pd.DataFrame({s: NB.pos[m][s].reindex(idx).fillna(0.0) for s in STYLES})
        A = pd.DataFrame(0.2, index=idx, columns=list(STYLES))
        pc = (A * netting.sleeve_costs({s: NB.pos[m][s] for s in STYLES}, NB.ph[m], 5, idx)).sum(axis=1).loc["2012":]
        nc = netting.netted_cost(P, NB.ph[m], A, 5).loc["2012":]
        sav.append((pc.sum() - nc.sum()) / pc.sum())
    print(f"   {label}: EW netting removes {np.mean(sav) * 100:.0f}% of the 5 bps cost (product average, 2012 on)")
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL")
