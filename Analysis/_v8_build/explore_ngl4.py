from facts3 import *
import importlib
v = "ngl"; M4 = MEMBERS[v]; pr = [p for _, p in M4]; three = [m for m in M4 if m[0] == "ngl"]
print("members", M4)
mom, car, cm, val, sk = (st(v, k) for k in SLEEVES); pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol"); ew4, iv4 = st4(v, "EW PORT"), st4(v, "Inverse Vol"); ewD, ivD = per(v, "EW PORT"), per(v, "Inverse Vol")
print("EW", {k: round(float(ew[k]), 3) for k in ("ir", "ret", "vol", "mdd")}, "IV", {k: round(float(iv[k]), 3) for k in ("ir", "ret", "vol", "mdd")})
print("EW4 (no skew)", round(float(ew4["ir"]), 3), round(float(ew4["vol"]), 2), "IV4", round(float(iv4["ir"]), 3))
print("ewD", [round(x, 2) for x in ewD], "ivD", [round(x, 2) for x in ivD])
ew4D = [st4(v, "EW PORT", w)["ir"] for w in ("p1", "p2", "p3")]; print("ew4D", [round(float(x), 2) for x in ew4D])
others = {t: st(t, "EW PORT")["ir"] for t in BUCKETS if t != v}; oi = {t: st(t, "Inverse Vol")["ir"] for t in BUCKETS if t != v}
print("others EW", {k: round(float(x), 2) for k, x in others.items()}); print("others IV", {k: round(float(x), 2) for k, x in oi.items()})
cs3 = pd.DataFrame({k: ew_intersection([nets()[m][k] for m in three]) for k in SLEEVES})
ew_3p, iv_3p = stats(cs3.mean(axis=1, skipna=False)), stats(inverse_vol(cs3))
print("three-MB-product basis EW", {k: round(float(ew_3p[k]), 3) for k in ("ir", "vol", "mdd", "ret")}, "IV", {k: round(float(iv_3p[k]), 3) for k in ("ir", "vol", "mdd")})
e4 = {p: stats(ew_intersection([nets()[(a, p)][k] for k in SLEEVES]))["ir"] for a, p in M4}; print("product EW-of-five IR", {k: round(float(x), 3) for k, x in e4.items()})
nap_e = ew_intersection([nets()[("naphtha", "Naphtha")][k] for k in SLEEVES]); cor_n = {}
for a, p in three:
    e = ew_intersection([nets()[(a, p)][k] for k in SLEEVES]); cor_n[p] = float(pd.concat([e, nap_e], axis=1).loc["2012-01-01":].dropna().corr().iloc[0, 1])
pet_ew = class_portfolios("petroleum")[0]; cor_pet = float(pd.concat([nap_e, pet_ew], axis=1).loc["2012-01-01":].dropna().corr().iloc[0, 1])
print("Naphtha corr", {k: round(x, 2) for k, x in cor_n.items()}, "vs Petroleum", round(cor_pet, 2))
npp = {k: pper("naphtha", "Naphtha", k) for k in SLEEVES}; print("Naphtha per period", {k: [round(x, 2) for x in v_] for k, v_ in npp.items()})
print("Skew P1 three MB", {p: round(pper(a, p, "Skewness")[0], 2) for a, p in three}, "all products P2", {p: round(pper(a, p, "Skewness")[1], 2) for a, p in M4})
vy = yearly_log(CS[v]["Value"]); print("Value yearly", {int(k): round(float(x), 2) for k, x in vy.loc[2020:].items()})
vpp = {p: pst(a, p, "Value", "p3")["ir"] for a, p in M4}; print("Value P3 by product", {k: round(float(x), 2) for k, x in vpp.items()})
mp = {p: pst(a, p, "Momentum")["ir"] for a, p in M4}; cp = {p: pst(a, p, "Carry")["ir"] for a, p in M4}; cmp_ = {p: pst(a, p, "CarryMom")["ir"] for a, p in M4}
vf = {p: pst(a, p, "Value")["ir"] for a, p in M4}; skp = {p: pst(a, p, "Skewness")["ir"] for a, p in M4}
for nme, d in (("Mom", mp), ("Carry", cp), ("CM", cmp_), ("Value", vf), ("Skew", skp)): print(nme, "full by product", {k: round(float(x), 2) for k, x in d.items()})
sy = yearly_log(CS[v]["Skewness"]); print("Skew yearly", {int(k): round(float(x), 2) for k, x in sy.items()})
lg = {p: legs(a, p) for a, p in M4}; print("Skew long% P3", {p: round(lg[p]["p3"]["long_pct"], 1) for p in pr})
print("episodes", {p: round(float(skew_episode("ngl", p, "2020-05-01", "2021-12-31")[0]), 2) for p in ("Propane", "Butane")})
cw = corr_within(v); print("NGL Skew corr Mom/Carry/Value", round(cw.loc["Skewness", "Momentum"], 2), round(cw.loc["Skewness", "Carry"], 2), round(cw.loc["Skewness", "Value"], 2))
print("other buckets' Skew-Mom", {t: round(corr_within(t).loc["Skewness", "Momentum"], 2) for t in BUCKETS if t != v}, "Skew-Carry", {t: round(corr_within(t).loc["Skewness", "Carry"], 2) for t in BUCKETS if t != v})
from engine import _carry_base
sl = pd.concat([_carry_base(importlib.import_module(a).load_curve(p), "F2", "F4").loc["2012-01-01":].dropna() for a, p in M4]); m_ = sl.index.month
print("F2-F4 winter/summer %", round(100 * sl[(m_ == 12) | (m_ <= 3)].mean(), 2), round(100 * sl[(m_ >= 6) & (m_ <= 9)].mean(), 2))
liq = pd.read_csv(os.path.join(REPO, "Analysis", "Liquidity_Cal2025_results.csv")).set_index("product"); print("L", {p: round(float(liq.loc[p, "L_strip"]), 2) for p in pr})
