"""Exploration of the six-bucket facts and their check against the 0930 dashboard dataset (final_v3.json)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facts3 import *
pd.set_option("display.width", 250)
W3 = ("p1", "p2", "p3")

# ---- combined book (two stage), EW / IV, vs dashboard 'combined'
cb = combined_book()
print("COMBINED BOOK  members", D["combined"]["members"], D["combined"]["common_first"], D["combined"]["common_last"])
for (s1, s2), ser in cb.items():
    print(s1, s2, {w: round(stats(ser, w)["ir"], 3) for w in ("full",) + W3}, "ret/vol/mdd", [round(stats(ser)[k], 2) for k in ("ret", "vol", "mdd")])
print("dashboard combined windows (first rows):")
for r in D["combined"]["windows"]["full"]:
    print("  ", r["name"], r["ir"], r["ret"], r["vol"], r["mdd"])

# ---- by style (cross-bucket sleeves)
bs = bystyle()
print("\nBY STYLE (EW across 6 buckets, common dates) start", bs.index[0].date(), "end", bs.index[-1].date())
for k in SLEEVES + ["EW PORT", "Inverse Vol"]:
    print(" ", k, {w: round(stats(bs[k], w)["ir"], 3) for w in ("full",) + W3}, [round(stats(bs[k])[x], 2) for x in ("ret", "vol", "mdd")])
print("dashboard bystyle keys", list(D["bystyle"].keys())[:6])
for r in D["bystyle"]["windows"]["full"]:
    print("   D", r["name"], r["ir"], r["ret"], r["vol"], r["mdd"])

# ---- pairs
print("\nPAIRS vs dashboard crosspair")
ps = pair_stats()
cp = D["crosspair"]
print("crosspair keys", list(cp.keys())[:8])
for p in ps:
    print(f"{p['name']:38s} EW {p['ew']['ir']:+.3f} IV {p['iv']['ir']:+.3f} corr {p['corr']:+.3f}  EWp {[round(x,2) for x in p['ewp']]} IVp {[round(x,2) for x in p['ivp']]}")

# ---- within-bucket correlation (sleeve vs EW PORT)
print("\nWITHIN correlation")
for v in BUCKETS:
    c = corr_within(v)
    print(v, "Value-EW", round(c.loc["Value", "EW PORT"], 2), "Skew-EW", round(c.loc["Skewness", "EW PORT"], 2), "Mom-Carry", round(c.loc["Momentum", "Carry"], 2), "Mom-Value", round(c.loc["Momentum", "Value"], 2),
          "Skew-Value", round(c.loc["Skewness", "Value"], 2), "IV-EW", round(c.loc["Inverse Vol", "EW PORT"], 2), "Carry-CM", round(c.loc["Carry", "CarryMom"], 2))

# ---- cross-bucket correlation matrices by series
print("\nCROSS correlation EW PORT")
print(corr_cross("EW PORT").round(2))
for k in SLEEVES + ["Inverse Vol"]:
    c = corr_cross(k); iu = np.triu_indices(6, 1)
    vals = c.values[iu]
    print(k, "avg |corr|", round(np.mean(np.abs(vals)), 3), "max", round(vals.max(), 2), "min", round(vals.min(), 2))

# ---- benchmarks
print("\nBENCH corr of EW/IV books")
for (s1, s2), ser in cb.items():
    if s1 == "EW" and s2 == "EW": print("EW/EW", {k: round(v, 2) for k, v in bench_corr(ser).items()})
    if s1 == "IV" and s2 == "IV": print("IV/IV", {k: round(v, 2) for k, v in bench_corr(ser).items()})
print("Skewness cross sleeve bench", {k: round(v, 2) for k, v in bench_corr(bs["Skewness"]).items()})
