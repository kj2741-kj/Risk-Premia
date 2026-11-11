import sys, os, json, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facts3 import *
from engine import combine_returns
pd.set_option("display.width", 250)
f = lambda x: f"{x:+.2f}"
PJ = json.load(open(os.path.join(REPO, "Analysis", "_power_build", "power_tab_0930.json")))
N0 = pickle.load(open(os.path.join(REPO, "outputs", "power_0930", "power_nets.pkl"), "rb"))
nets_p = N0["nets"]; print("keys", list(nets_p.keys()))
members = ["PJM_Peak", "PJM_OffPeak", "ERCOT_Peak", "ERCOT_OffPeak", "MISO_Peak"]
PW = {"full": ("2017-01-01", None), "p2": ("2017-01-01", "2021-12-31"), "p3": ("2022-01-01", None), "y26": ("2026-01-01", None)}
def stp(r, w="full"):
    s, e = PW[w]; r = (r.loc[s:e] if e else r.loc[s:]).dropna()
    ret = (np.exp(252 * r.mean()) - 1) * 100; vol = np.expm1(r).std(ddof=1) * np.sqrt(252) * 100
    cum = np.exp(r.cumsum()); mdd = (cum / cum.cummax() - 1).min() * 100
    return dict(ret=ret, vol=vol, mdd=mdd, ir=ret / vol)
# the dashboard's own construction (power_tab_v3.py): combine_cross_asset over the members, then combine_returns
from cross_asset_engine import combine_cross_asset
sty = {k: combine_cross_asset([nets_p[p][k] for p in members]) for k in SLEEVES}
ew = combine_returns(list(sty.values()), "equal_weight"); iv = combine_returns(list(sty.values()), "inverse_vol", vol_window=63)
rows = {**sty, "EW PORT": ew, "Inverse Vol": iv}
bad = 0
for ri, row in enumerate(PJ["tab"]["windows"]["full"]):
    for w in ("full", "p2", "p3", "y26"):
        h = PJ["tab"]["windows"][w][ri]; m = stp(rows[row["name"]], w)
        for k in ("ir", "ret", "vol", "mdd"):
            if abs(h[k] - m[k]) > 0.0011: bad += 1; print("DIFF", row["name"], w, k, h[k], round(m[k], 4))
print("bucket cells differing:", bad)
for k, s in rows.items(): print(f"{k:12s}", {w: f(stp(s, w)["ir"]) for w in PW}, "ret/vol/mdd", [round(stp(s)[x], 1) for x in ("ret", "vol", "mdd")])
print("\nproducts x sleeves (IR full / p2 / p3)")
for p in members:
    print(p, {k: (f(stp(nets_p[p][k])["ir"]), f(stp(nets_p[p][k], "p2")["ir"]), f(stp(nets_p[p][k], "p3")["ir"])) for k in SLEEVES})
    e = combine_returns([nets_p[p][k] for k in SLEEVES], "equal_weight"); print("    EW5", f(stp(e)["ir"]), [round(stp(e)[x], 1) for x in ("ret", "vol", "mdd")])
# yearly
def yl(r): r = r.loc["2017-01-01":].dropna(); return r.groupby(r.index.year).sum()
print(pd.DataFrame({k: yl(sty[k]) for k in SLEEVES}).assign(EW=yl(ew)).round(2).to_string())
print("4 sleeves EW/IV", f(stp(combine_returns([sty[k] for k in CORE], "equal_weight"))["ir"]), f(stp(combine_returns([sty[k] for k in CORE], "inverse_vol", vol_window=63))["ir"]))
cw = pd.concat([pd.DataFrame(sty), ew.rename("EW PORT")], axis=1).loc["2017-01-01":].dropna().corr(); print(cw.round(2))
pe = pd.DataFrame({p: combine_returns([nets_p[p][k] for k in SLEEVES], "equal_weight") for p in members}).loc["2017-01-01":].dropna().corr(); print(pe.round(2))
liq = pd.read_csv(os.path.join(REPO, "Analysis", "Power_Liquidity_Cal2025_results.csv")); print(liq[["product", "L_strip", "x_strip"]].round(3).to_string())
print("data first/last", PJ["tab"]["data_first"], PJ["tab"]["data_last"], PJ["tab"]["pairs"], PJ["tab"]["rolls"])
print("book corr with other buckets EW:", {b: round(float(pd.concat([ew, PORT[b][0]], axis=1).loc["2017-01-01":].dropna().corr().iloc[0, 1]), 2) for b in BUCKETS})
print("bench corr power EW", {k: round(v, 2) for k, v in bench_corr(ew, "2017-01-01").items()})
