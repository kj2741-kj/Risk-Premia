from text_cross8 import *
from text_cross8 import _ir
ser = SLEEVES + ["EW PORT", "Inverse Vol"]; cx = {k: corr_cross(k) for k in ser}
cm_vals = [cx["CarryMom"].loc[a, b] for a, b in PAIR_ORDER]; pn = {k: cx[k].loc["petroleum", "ngl"] for k in ser}
print("CM max", round(max(cm_vals), 4), "== PN?", max(cm_vals) == pn["CarryMom"], "n_small", sum(1 for x in cm_vals if abs(x) < 0.10), "of", len(cm_vals))
ewc = cx["EW PORT"]; pw = {b: round(float(ewc.loc["power", b]), 3) for b in BUCKETS}; print("power corr", pw)
print("avg abs by series", {k: round(float(np.mean([abs(cx[k].loc[a, b]) for a, b in PAIR_ORDER])), 3) for k in ser})
bs, bs4 = book(); b6 = six_bucket_book(); start = bs.index[0]
ew, iv = stats(bs["EW PORT"]), stats(bs["Inverse Vol"])
def win(r):
    r = r.loc[start:].dropna(); ret = (np.exp(252 * r.mean()) - 1) * 100; vol = np.expm1(r).std(ddof=1) * np.sqrt(252) * 100
    cum = np.exp(r.cumsum()); return dict(ret=ret, vol=vol, mdd=(cum / cum.cummax() - 1).min() * 100, ir=ret / vol)
e6, i6 = win(b6["EW PORT"]), win(b6["Inverse Vol"])
print("seven EW", {k: round(float(ew[k]), 3) for k in ("ir", "vol", "mdd")}, "IV", {k: round(float(iv[k]), 3) for k in ("ir", "vol", "mdd")})
print("six   EW", {k: round(float(x), 3) for k, x in e6.items()}, "IV", {k: round(float(x), 3) for k, x in i6.items()})
cb = combined_book(); com = max(v.dropna().index[0] for v in cb.values()); cbw = {k: round(float(_ir(v.loc[com:])), 3) for k, v in cb.items()}
print("combined common start", com.date(), cbw)
