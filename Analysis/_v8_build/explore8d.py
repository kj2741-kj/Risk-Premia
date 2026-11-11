import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facts3 import *
pd.set_option("display.width", 250)
f = lambda x: f"{x:+.2f}"
W3 = ("p1", "p2", "p3")
print("WITHIN: corr of each core sleeve with EW PORT; rank of Value / Skewness (1 = lowest)")
for v in BUCKETS:
    c = corr_within(v)
    s = c.loc[SLEEVES, "EW PORT"]
    rk = s.rank()
    print(v, {k: round(s[k], 2) for k in SLEEVES}, "Value rank", int(rk["Value"]), "Skew rank", int(rk["Skewness"]))
    pairs = {(a, b): c.loc[a, b] for i, a in enumerate(["Momentum", "Carry", "CarryMom"]) for b in ["Momentum", "Carry", "CarryMom"][i + 1:]}
    print("   base pairs", {k: round(x, 2) for k, x in pairs.items()}, "Value vs Mom/Carry/CM", [round(c.loc["Value", k], 2) for k in ("Momentum", "Carry", "CarryMom")], "Skew vs Mom/Carry/CM/Value", [round(c.loc["Skewness", k], 2) for k in ("Momentum", "Carry", "CarryMom", "Value")])
print("\nCROSS per series: top three pairs")
for k in SLEEVES + ["EW PORT", "Inverse Vol"]:
    c = corr_cross(k)
    pr = sorted(((c.loc[a, b], a, b) for a, b in PAIR_ORDER), reverse=True)
    print(k, [(f"{SHORT[a]}-{SHORT[b]}", round(x, 2)) for x, a, b in pr[:3]], "n>0.2:", sum(1 for x, a, b in pr if x > 0.2), "max", round(pr[0][0], 2))
print("\nBOOK")
bs = bystyle(); bs4 = bystyle4()
for lab, df in (("5 sleeves", bs), ("4 sleeves", bs4)):
    for k in ("EW PORT", "Inverse Vol"):
        s = stats(df[k]); print(lab, k, "IR", f(s["ir"]), "ret", round(s["ret"], 1), "vol", round(s["vol"], 1), "mdd", round(s["mdd"], 1), [f(stats(df[k], w)["ir"]) for w in W3])
print("worst bucket IR per sleeve:", {k: round(min(st(v, k)["ir"] for v in BUCKETS), 2) for k in SLEEVES}, "best", {k: round(max(st(v, k)["ir"] for v in BUCKETS), 2) for k in SLEEVES})
print("buckets with positive IR in all 3 periods (EW):", [v for v in BUCKETS if all(x > 0 for x in per(v, "EW PORT"))], "IV:", [v for v in BUCKETS if all(x > 0 for x in per(v, "Inverse Vol"))])
print("bucket EW vol:", {v: round(st(v, "EW PORT")["vol"], 1) for v in BUCKETS})
print("book stats by style sleeves:", {k: (f(stats(bs[k])["ir"]), [f(stats(bs[k], w)["ir"]) for w in W3]) for k in SLEEVES})
# two-stage reversed order and mixed
cb = combined_book()
print("two-stage (sleeves stage, across stage):", {k: round(stats(v)["ir"], 3) for k, v in cb.items()})
# pairs vs best bucket
ps = pair_stats()
print("best pair EW", max(ps, key=lambda p: p["ew"]["ir"])["name"], "best IV", max(ps, key=lambda p: p["iv"]["ir"])["name"])
print("pair vols best", [(p["name"], round(p["ew"]["vol"], 1)) for p in ps if p["name"] in ("Petroleum-NGL", "Gas and Emissions-NGL")])
print("negative IR pairs:", [(p["name"], round(p["ew"]["ir"], 2), round(p["iv"]["ir"], 2)) for p in ps if p["ew"]["ir"] < 0 or p["iv"]["ir"] < 0])
print("pairs P3 for the negative ones", [(p["name"], [round(x, 2) for x in p["ewp"]], [round(x, 2) for x in p["ivp"]]) for p in ps if p["ew"]["ir"] < 0])
print("bench EW", {k: round(v, 2) for k, v in bench_corr(bs["EW PORT"]).items()})
print("bench IV", {k: round(v, 2) for k, v in bench_corr(bs["Inverse Vol"]).items()})
print("bench EW4", {k: round(v, 2) for k, v in bench_corr(bs4["EW PORT"]).items()})
print("bench IV4", {k: round(v, 2) for k, v in bench_corr(bs4["Inverse Vol"]).items()})
print("bench Skew", {k: round(v, 2) for k, v in bench_corr(bs["Skewness"]).items()})
for v in BUCKETS:
    print(v, "bench corr commodity index EW PORT", round(bench_corr(PORT[v][0])["Commodity Index"], 2))
