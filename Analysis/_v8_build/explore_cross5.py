from text_cross8 import *
from text_cross8 import _ir
bs, bs4 = book(); b6 = six_bucket_book(); start = bs.index[0]
cb = combined_book(); com = max(v.dropna().index[0] for v in cb.values())
print("two-stage round2:", {k: round(float(_ir(v.loc[com:])), 2) for k, v in cb.items()}, {k: float(_ir(v.loc[com:])) for k, v in cb.items()})
ps = pair_stats(); rows = sorted(ps, key=lambda p: -p["ew"]["ir"])
print("top pairs EW", [(p["name"], round(p["ew"]["ir"], 2), round(p["iv"]["ir"], 2)) for p in rows[:3]])
print("power pair EW", {p["name"]: round(p["ew"]["ir"], 2) for p in ps if "US Power" in p["name"]})
print("worst pairs", [(p["name"], round(p["ew"]["ir"], 2), round(p["iv"]["ir"], 2)) for p in rows[-3:]])
# six-bucket book on its own full window (from 2012)
def full(r):
    r = r.dropna(); ret = (np.exp(252 * r.mean()) - 1) * 100; vol = np.expm1(r).std(ddof=1) * np.sqrt(252) * 100; return round(ret / vol, 3), round(vol, 2), str(r.index[0].date())
print("six-bucket from own start: EW", full(b6["EW PORT"]), "IV", full(b6["Inverse Vol"]))
print("six-bucket book start", b6.index[0].date())
bE, bI = bench_corr(bs["EW PORT"]), bench_corr(bs["Inverse Vol"]); bS = bench_corr(bs["Skewness"])
print("seven bench EW/IV commodity index", round(bE["Commodity Index"], 3), round(bI["Commodity Index"], 3), "Skew", {k: round(v, 3) for k, v in bS.items()})
b6S = bench_corr(b6["Skewness"]); print("six-bucket Skewness bench (own window)", {k: round(v, 3) for k, v in b6S.items()})
print("seven vol/ret", round(float(stats(bs["EW PORT"])["vol"]), 2), round(float(stats(bs["Inverse Vol"])["vol"]), 2))
print("all periods positive EW", [round(stats(bs["EW PORT"], w)["ir"], 2) for w in ("p1", "p2", "p3")], "IV", [round(stats(bs["Inverse Vol"], w)["ir"], 2) for w in ("p1", "p2", "p3")])
