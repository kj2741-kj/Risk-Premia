"""Checks of the product-level netting in the Streamlit Portfolio tab (dashboard_portfolio_tab._combine_sleeves), 2026-11-15.
Run from the repo root:  python research/_verify_portfolio_tab_netting.py [metals|petroleum|...]
1. Netting switched off (k = 1): the netted path equals the per-sleeve path for EW, Inverse Vol, ERC and DRP (the weights and the combine are reproduced exactly).
2. Netting on, EW and ERC: an independent recomputation from positions (gross - netted cost, weights applied directly) equals the tab's netted portfolio.
3. Netting never raises a portfolio's cost: netted net >= per-sleeve net on every day (EW)."""
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path[:0] = [".", "research", "research/configs", "scripts"]
import importlib

import numpy as np
import pandas as pd

import netting
import dashboard_portfolio_tab as T
from engine import log_return_transaction_cost

ac = sys.argv[1] if len(sys.argv) > 1 else "metals"
cfg = importlib.import_module(ac)
fails = []
ok = lambda c, m: print(("PASS " if c else "FAIL ") + m) or (None if c else fails.append(m))
excl = tuple(getattr(T, "_DEFAULT_EXCLUDED", {}).get(ac, ()))
gross, net, det = T._compute_reference_returns.__wrapped__(cfg, cfg.ASSET_CLASS, 5, excl) if hasattr(T._compute_reference_returns, "__wrapped__") else T._compute_reference_returns(cfg, cfg.ASSET_CLASS, 5, excl)
names = [k for k in net if k != "Skewness"]
G, N, D = {k: gross[k] for k in names}, {k: net[k] for k in names}, {k: det[k] for k in names}
print(ac, "strategies:", names, "products:", list(D[names[0]]["nets"]))

real = netting.netted
netting.netted = lambda nets, pos, ph, tc, a=None: {s: nets[s] for s in nets}
for m in T.COMBINE_METHODS:
    g0, n0 = T._combine_sleeves(G, N, m, 63)
    g1, n1 = T._combine_sleeves(G, N, m, 63, detail=D, tc_bps=5)
    d = float((n0 - n1).abs().max()) if n0.index.equals(n1.index) else np.inf
    ok(d < 1e-15 and g0.equals(g1), f"1. {m}: netting off == per-sleeve path (max diff {d:.1e})")
netting.netted = real

for m in ("Equal Weight", "Risk Parity (ERC, rolling)"):
    _, n1 = T._combine_sleeves(G, N, m, 63, detail=D, tc_bps=5)
    prods = list(D[names[0]]["nets"])
    idx = D[names[0]]["nets"][prods[0]].index
    same_cal = all(D[k]["nets"][p].index.equals(idx) for k in names for p in D[k]["nets"])
    if not same_cal:
        print(f"   2. {m}: products on different calendars, independent check skipped for this bucket"); continue
    if m == "Equal Weight":
        W = pd.DataFrame(1.0 / len(names), index=idx, columns=names)
    else:
        from risk_parity import rolling_erc_combine
        _, W = rolling_erc_combine(N, tilt=0.0)
        W = W.astype(float)
    Wp = W.reindex(idx, method="bfill")
    port = 0.0
    for p in prods:
        ks = [k for k in names if p in D[k]["nets"]]
        A = pd.DataFrame({k: Wp[k] / len(D[k]["nets"]) for k in ks})
        g = sum(A[k] * (D[k]["nets"][p] + log_return_transaction_cost(D[k]["pos"][p].reindex(idx).fillna(0.0), 5, D[k]["phase"][p])) for k in ks)
        tot = A.sum(axis=1)
        c = netting.netted_cost(pd.DataFrame({k: D[k]["pos"][p].reindex(idx).fillna(0.0) for k in ks}), D[ks[0]]["phase"][p], A.div(tot, axis=0).fillna(1.0 / len(ks)), 5) * tot
        port = port + g - c
    j = n1.dropna().index.intersection(port.dropna().index)[1:]
    d = float((n1.loc[j] - port.loc[j]).abs().max())
    ok(d < 1e-13, f"2. {m}: independent netted portfolio == tab (max diff {d:.1e}, {len(j)} days)")

_, n_ps = T._combine_sleeves(G, N, "Equal Weight", 63)
_, n_nt = T._combine_sleeves(G, N, "Equal Weight", 63, detail=D, tc_bps=5)
j = n_ps.dropna().index
ok(bool((n_nt.loc[j] - n_ps.loc[j] >= -1e-15).all()), f"3. EW netted >= per-sleeve on every day; IR-relevant mean gain {float((n_nt.loc[j] - n_ps.loc[j]).mean() * 252 * 1e4):.1f} bps a year")
print("RESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL")
