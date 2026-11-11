from text_cross8 import *
ser = SLEEVES + ["EW PORT", "Inverse Vol"]; cx = {k: corr_cross(k) for k in ser}
cm_vals = [cx["CarryMom"].loc[a, b] for a, b in PAIR_ORDER]; pn = {k: cx[k].loc["petroleum", "ngl"] for k in ser}
print("CM max", round(float(max(cm_vals)), 4), "== PN", max(cm_vals) == pn["CarryMom"], "n_small(<0.10)", sum(1 for x in cm_vals if abs(x) < 0.10), "of", len(cm_vals))
bs, bs4 = book()
sP = {k: [round(float(stats(bs[k], w)["ir"]), 2) for w in W3] for k in SLEEVES}; print("sleeve IR P1/P2/P3:", sP)
print("EW/IV P:", [round(float(stats(bs["EW PORT"], w)["ir"]), 2) for w in W3], [round(float(stats(bs["Inverse Vol"], w)["ir"]), 2) for w in W3])
bS = bench_corr(bs["Skewness"]); print("Skewness bench:", {k: round(v, 3) for k, v in bS.items()})
bE, bI = bench_corr(bs["EW PORT"]), bench_corr(bs["Inverse Vol"]); print("book bench EW", {k: round(v, 3) for k, v in bE.items()}, "IV", {k: round(v, 3) for k, v in bI.items()})
ew, iv = stats(bs["EW PORT"]), stats(bs["Inverse Vol"]); ew4, iv4 = stats(bs4["EW PORT"]), stats(bs4["Inverse Vol"])
print("book EW", {k: round(float(ew[k]), 2) for k in ("ir", "ret", "vol", "mdd")}, "IV", {k: round(float(iv[k]), 2) for k in ("ir", "ret", "vol", "mdd")}, "no-skew EW", round(float(ew4["ir"]), 2), "IV", round(float(iv4["ir"]), 2))
