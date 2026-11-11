import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facts3 import *
pd.set_option("display.width", 250)
f = lambda x: f"{x:+.2f}"
# ---- NGL: four-product basis versus five
four = [m for m in MEMBERS["ngl"] if m[0] == "ngl"]
cs4 = pd.DataFrame({k: ew_intersection([nets()[m][k] for m in four]) for k in SLEEVES})
ew4p, iv4p = cs4.mean(axis=1, skipna=False), inverse_vol(cs4)
print("NGL four products EW", f(stats(ew4p)["ir"]), "IV", f(stats(iv4p)["ir"]), {w: f(stats(ew4p, w)["ir"]) for w in ("p1", "p2", "p3")}, "vol", round(stats(ew4p)["vol"], 1), "mdd", round(stats(ew4p)["mdd"], 1))
print("NGL four products sleeves", {k: f(stats(cs4[k])["ir"]) for k in SLEEVES})
nap = ew_intersection([nets()[("naphtha", "Naphtha")][k] for k in SLEEVES])
ngl4 = ew4p
j = pd.concat([nap, ngl4], axis=1, keys=["nap", "ngl4"]).loc["2012-01-01":].dropna()
print("corr Naphtha EW-of-5 vs four-NGL EW-of-5:", round(j.corr().iloc[0, 1], 2))
pet = class_portfolios("petroleum")[0]
j = pd.concat([nap, pet], axis=1, keys=["nap", "pet"]).loc["2012-01-01":].dropna()
print("corr Naphtha EW-of-5 vs Petroleum EW PORT:", round(j.corr().iloc[0, 1], 2))
for a, p in MEMBERS["ngl"]:
    e = ew_intersection([nets()[(a, p)][k] for k in SLEEVES]); j = pd.concat([e, nap], axis=1).loc["2012-01-01":].dropna()
    print("  corr", p, "vs Naphtha", round(j.corr().iloc[0, 1], 2))
# Naphtha F1 price raw
nm = importlib.import_module("naphtha").load_f1_series_logret("Naphtha")
fr = nm["F1_raw"].dropna()
print("Naphtha F1_raw first", fr.index[0].date(), round(fr.iloc[0], 1), "2012-01-03", round(fr.loc["2012-01-03":].iloc[0], 1), "max", fr.idxmax().date(), round(fr.max(), 1), "last", fr.index[-1].date(), round(fr.iloc[-1], 1))
for d0, d1 in (("2026-02-27", "2026-03-27"),):
    print("Naphtha", d0, round(fr.loc[:d0].iloc[-1], 1), d1, round(fr.loc[:d1].iloc[-1], 1))
# NGL sleeves by year since 2024
yl = pd.DataFrame({k: yearly_log(CS["ngl"][k]) for k in SLEEVES})
print("NGL EW PORT total log", round(PORT["ngl"][0].loc["2012-01-01":].sum(), 3), "years", {y: round(v, 2) for y, v in yearly_log(PORT["ngl"][0]).items() if y >= 2020})
# ---- Gas and Emissions
v = "pen"
ewp = PORT[v][0].loc["2012-01-01":].dropna(); tot = ewp.sum(); yl = yearly_log(ewp)
print("\nPEN EW PORT total log", round(tot, 3), "2021", round(yl[2021], 3), "share", round(yl[2021] / tot * 100), "2020-2023", round(yl.loc[2020:2023].sum() / tot * 100))
mask = ~((ewp.index >= "2021-07-01") & (ewp.index <= "2023-06-30"))
print("PEN EW excl 2021-07..2023-06 IR", f(stats(ewp[mask])["ir"]), "crisis only", f(stats(ewp[~mask])["ir"]), "all", f(stats(ewp)["ir"]))
for a, p in MEMBERS[v]:
    e = ew_intersection([nets()[(a, p)][k] for k in SLEEVES]).loc["2012-01-01":]
    m2 = ~((e.index >= "2021-07-01") & (e.index <= "2023-06-30"))
    print(f"  {p:8s} EW5 IR all {f(stats(e)['ir'])} excl-crisis {f(stats(e[m2])['ir'])} crisis {f(stats(e[~m2])['ir'])}  total log {e.sum():+.2f} 2021 {yearly_log(e).get(2021, 0):+.2f}")
ee = {p: ew_intersection([nets()[(a, p)][k] for k in SLEEVES]).loc["2012-01-01":] for a, p in MEMBERS[v]}
print(pd.DataFrame(ee).dropna().corr().round(2))
for mod, p in (("emissions", "TTF"), ("emissions", "UKGas"), ("emissions", "EUA"), ("energy", "NatGas")):
    r = importlib.import_module(mod).load_f1_series_logret(p)["F1_raw"].dropna()
    print(p, "F1_raw 2021-01-04", round(r.loc["2021-01-04":].iloc[0], 2), "max", r.idxmax().date(), round(r.max(), 2), "2026-09-30", round(r.iloc[-1], 2), "2024-12-31", round(r.loc[:"2024-12-31"].iloc[-1], 2))
# carry slope F1-F13 share backwardation for TTF in 2021-2022
for mod, p in (("emissions", "TTF"), ("emissions", "UKGas"), ("energy", "NatGas")):
    cur = importlib.import_module(mod).load_curve(p)
    sl = (cur["F1"] - cur["F13"]) / cur["F1"]
    print(p, "F1-F13 slope avg % P1/P2/P3", [round(100 * sl.loc[a:b].mean(), 1) for a, b in (("2012", "2016"), ("2017", "2021"), ("2022", "2026"))], "share backw", [round(100 * (sl.loc[a:b] > 0).mean()) for a, b in (("2012", "2016"), ("2017", "2021"), ("2022", "2026"))],
          "2021-07..2022-12 avg", round(100 * sl.loc["2021-07":"2022-12"].mean(), 1))
# skewness position share
for a, p in MEMBERS[v]:
    lg = legs(a, p); print(p, "long%", {w: round(lg[w]["long_pct"]) for w in ("full", "p1", "p2", "p3")}, "long pnl", round(lg["full"]["long_pnl"], 2), "short pnl", round(lg["full"]["short_pnl"], 2))
cw = corr_within(v); print(cw.round(2))
print("PEN skew yearly", yearly_log(CS[v]["Skewness"]).round(2).to_dict())
# value by product contributions
print("PEN Value full IR products", {p: f(pst(a, p, "Value")["ir"]) for a, p in MEMBERS[v]})
