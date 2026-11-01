"""Comparison for Table 5 of the paper draft: the earlier sign-vote Carry and Carry-Momentum against the adopted summed rule, BOTH on the same (imputed-price) data.
The sign-vote nets are rebuilt here from the repository's own engine functions (engine.raw_signal_carry_v2 / raw_signal_carrymom, combine_positions 'equal_weight', exec_shift, fillna(0)),
exactly as compute_products.py did before 2026-10-13; every other sleeve is taken from outputs/final_dashboard_2012/products_2012_nets.pkl (summed rule, 504-observation Value).
Prints full-sample IRs per asset class (with NatGas) and the five-class Equal Weight book for both rules, and the share of days the two pairs disagree."""
import sys, os, importlib, pickle, copy
import numpy as np, pandas as pd
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [os.path.join(REPO, p) for p in ("research", os.path.join("research", "configs"), "scripts", os.path.join("Analysis", "_v4_build"))]
from engine import raw_signal_carry_v2, raw_signal_carrymom, combine_positions, exec_shift, log_return_daily
import rp

nets_sum, meta = pickle.load(open(os.path.join(REPO, "outputs", "final_dashboard_2012", "products_2012_nets.pkl"), "rb"))
nets_vote = copy.deepcopy(nets_sum)
dis = {}
for (a, p), m in meta.items():
    cfg = importlib.import_module(a); curve = cfg.load_curve(p); raw = cfg.load_f1_series_logret(p); lp, ph = raw["log_price"], raw["Phase"]
    W, H = cfg.CARRY_ZSCORE_WINDOW, cfg.CARRY_MOMENTUM_HORIZON
    zs = [raw_signal_carry_v2(curve, n, f, window=W) for n, f in m["pairs"]]
    ds = [raw_signal_carrymom(curve, n, f, H) for n, f in m["pairs"]]
    nets_vote[(a, p)]["Carry"] = log_return_daily(exec_shift(combine_positions(zs, "equal_weight"), cfg.CARRY_SHIFT_N).fillna(0), lp, 5, ph)[1]
    nets_vote[(a, p)]["CarryMom"] = log_return_daily(exec_shift(combine_positions(ds, "equal_weight"), cfg.CARRY_MOMENTUM_SHIFT_N).fillna(0), lp, 5, ph)[1]
    df = pd.concat(zs, axis=1).loc["2012-01-01":].dropna()
    dis.setdefault(a, []).append(float((df.iloc[:, 0] * df.iloc[:, 1] == -1).mean()))
pickle.dump((nets_vote, meta), open(os.path.join(REPO, "outputs", "final_dashboard_2012", "products_2012_vote_nets.pkl"), "wb"))

def run(nets):
    rp._nets = nets
    out = {}
    for v in ("metals", "energy", "ngl", "precious", "agri"):
        cs = rp.class_sleeves(v); out[v] = {k: rp.stats(cs[k])["ir"] for k in ("Carry", "CarryMom")}
    # five-class Equal Weight book: each sleeve equal-weighted across the five classes on common dates, then the five styles averaged
    cs = {v: rp.class_sleeves(v) for v in ("metals", "energy", "ngl", "precious", "agri")}
    idx = None; styles = {}
    for k in rp.SLEEVES:
        styles[k] = rp.ew_intersection([cs[v][k].dropna() for v in cs])
    book = pd.concat(styles, axis=1).mean(axis=1, skipna=False)
    out["all5_ew"] = rp.stats(book)["ir"]
    return out

s, v = run(nets_sum), run(nets_vote)
print("Disagreement share of days by class:", {a: round(100 * np.mean(x), 1) for a, x in dis.items()})
for k in ("Carry", "CarryMom"):
    print(k, "IR sign vote -> summed:", ", ".join(f"{a} {v[a][k]:+.2f} -> {s[a][k]:+.2f}" for a in ("metals", "energy", "ngl", "precious", "agri")))
print("Five-class Equal Weight book IR sign vote -> summed: %.3f -> %.3f" % (v["all5_ew"], s["all5_ew"]))
