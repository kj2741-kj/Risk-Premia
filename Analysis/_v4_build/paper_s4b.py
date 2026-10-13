"""Paper Section 4.1.3 to 4.1.5 (Precious Metals, NGL, Agriculture). Every number is computed from the fact functions;
every qualitative claim is wrapped in chk(). blocks() returns the block list in document order."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facts3 import *

# --- number format of the paper: hyphen as the minus sign, no plus signs
def I(x):
    return "0.00" if abs(round(x, 2)) == 0 else f"{x:.2f}"


def N(x, d=2):
    return f"{0:.{d}f}" if abs(round(x, d)) == 0 else f"{x:.{d}f}"


def R(x):
    return "0.0%" if abs(round(x, 1)) == 0 else f"{x:.1f}%"



CLS = ("precious", "ngl", "agri")
PNAME = {"SoybeanOil": "Soybean Oil", "Sugar": "Sugar No.11"}
pn = lambda p: PNAME.get(p, p)
LONGNAME = {"CarryMom": "Carry-Momentum"}


def rr(x):
    """Annualised return as plain percent with a hyphen as the minus sign."""
    return f"{x:.1f}%"


def hu(x, d=2):
    """Round half up (avoids float artefacts such as 7.085 printing as 7.08)."""
    return f"{x + 1e-9:.{d}f}"


def prod_ir(a, p, k, w="full"):
    return pst(a, p, k, w)["ir"]


# =====================================================================================================================
def precious_blocks():
    v, a = "precious", "precious"
    pr = VARIANTS[v][1]
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol")
    ew4, iv4 = st4(v, "EW PORT"), st4(v, "Inverse Vol")
    ewD, ivD = per(v, "EW PORT"), per(v, "Inverse Vol")
    cw = corr_within(v)
    ry = real_yield_stats()
    tt = tenor_table(v)
    mp = {p: prod_ir(a, p, "Momentum") for p in pr}; cp = {p: prod_ir(a, p, "Carry") for p in pr}
    cmp_ = {p: prod_ir(a, p, "CarryMom") for p in pr}; vp = {p: prod_ir(a, p, "Value") for p in pr}
    skp = {p: prod_ir(a, p, "Skewness") for p in pr}
    lg = {p: legs(a, p) for p in pr}
    gm = yearly_log(nets()[(a, "Gold")]["Momentum"]); gv = yearly_log(nets()[(a, "Gold")]["Value"])
    gy = yearly_log(nets()[(a, "Gold")]["Skewness"]); sy = yearly_log(nets()[(a, "Silver")]["Skewness"])
    gslope = slope_stats(a, "Gold", "F1", "F7"); sslope = slope_stats(a, "Silver", "F1", "F6")
    gvp3 = pst(a, "Gold", "Value", "p3")["ir"]
    _g = importlib.import_module("precious").load_curve("Gold")["F1"]
    core_best = max(((p, k) for p in pr for k in CORE), key=lambda t: prod_ir(a, t[0], t[1]))

    # ---- claims
    chk(all(st(v, k)["ir"] < 0 for k in CORE) and sk["ir"] > 0, "Precious Metals: all four core sleeves negative, Skewness the only positive sleeve")
    chk(core_best == ("Silver", "Carry"), "best core product-sleeve in Precious Metals is Silver Carry")
    chk(cp["Palladium"] == min(cp.values()) and mp["Palladium"] == min(mp.values()) and cmp_["Palladium"] == min(cmp_.values()), "Palladium weakest metal in Momentum, Carry and Carry-Momentum")
    chk(pm[0] > -0.1 and pm[1] < -0.4 and pm[2] < -0.2, "Momentum: flat P1, negative P2 and P3")
    chk(max(abs(x) for x in mp.values()) < 0.4 and mp["Gold"] > 0 > mp["Silver"] and max(mp.values()) == mp["Gold"] and mp["Gold"] < 0.05, "no metal has a clear positive Momentum IR")
    chk(abs(round(ry["full"]["corr"], 2) + 0.39) < 0.006 and abs(round(ry["p2"]["corr"], 2) + 0.64) < 0.006 and abs(round(ry["p3"]["corr"], 2) + 0.24) < 0.006, "gold real-yield correlations")
    chk(round(gm.loc[2013], 2) == 0.25 and round(gm.loc[2025], 2) == 0.36, "gold Momentum 2013 and 2025")
    chk(sorted(gm.values)[-1] == gm.loc[2025] and sorted(gm.values)[-2] == gm.loc[2013] and sorted(gm.values)[-3] < 0.12, "gold Momentum: 2025 and 2013 are the two best years, no other year above 0.12")
    chk(round(_g.loc["2013-12-31"] / _g.loc["2012-12-31"] - 1, 2) == -0.28, "gold fell 28% in 2013 (front-month, calendar year)")
    chk(pc[0] < 0 and pc[1] < 0 and abs(pc[2]) < 0.05 and pcm[0] < 0 and abs(pcm[0]) < 0.1 and pcm[1] > 0 and pcm[2] < -0.5, "Carry negative P1, P2, about zero P3; Carry-Momentum slightly negative P1, positive P2, clearly negative P3")
    chk(all(gslope[w][0] < gslope[q][0] and sslope[w][0] < sslope[q][0] for w, q in (("p3", "p2"), ("p2", "p1"))), "Gold and Silver long-pair contango deepens from P1 to P3")
    chk([round(gslope[w][0], 1) for w in ("p3", "p2", "p1")] == [-4.5, -1.8, -0.6] and [round(sslope[w][0], 1) for w in ("p3", "p2", "p1")] == [-4.5, -2.3, -1.1], "curve slopes as quoted")
    chk(round(ry["p3"]["avg"], 2) == 1.60 and round(ry["p2"]["avg"], 2) == 0.03, "real yield averages P3 and P2")
    chk(tt["Carry"]["short"] < 0 and tt["Carry"]["long"] < 0 and tt["Carry"]["two"] < 0, "Carry negative on short pair, long pair and the sum")
    chk(tt["CarryMom"]["short"] < 0 and tt["CarryMom"]["two"] < 0 < tt["CarryMom"]["long"] < 0.05, "Carry-Momentum negative on short pair and sum, marginally positive on long pair alone")
    chk(cp["Gold"] >= 0 and cp["Silver"] > 0 and cp["Platinum"] > 0 and max(cp[p] for p in ("Gold", "Silver", "Platinum")) < 0.2 and cp["Palladium"] < -0.2, "Carry slightly positive in Gold, Silver, Platinum; Palladium negative")
    chk(abs(val["ir"]) < 0.1 and vp["Platinum"] > 0 > vp["Gold"] and abs(vp["Silver"]) < 0.1 and abs(vp["Palladium"]) < 0.1, "Value by metal")
    chk(abs(pv[0]) < 0.1 and pv[1] < 0 and pv[2] < pv[1], "Value: flat P1, negative P2, more negative P3")
    chk(round(gvp3, 2) == -0.61 and round(gv.loc[2025], 2) == -0.45, "gold Value P3 and 2025")
    chk(round(_g.loc["2022-09-30"]) == 1662 and round(_g.loc["2025-12-31"]) == 4341, "gold F1 levels")
    # Gold Value position in 2025 is short on nearly every day
    from engine import raw_signal_value
    _gc = importlib.import_module("precious").load_curve("Gold")
    _vpos = exec_shift(raw_signal_value(_gc, "F3", 1260, 0.10), 1).fillna(0).loc["2025-01-01":"2025-12-31"]
    chk((_vpos < 0).mean() > 0.9, "Gold Value position is short on more than 90% of days in 2025")
    chk(sk["ir"] > 0.05 and ps[0] < 0 < ps[1] and ps[2] > 0, "Skewness negative P1, positive P2 and P3")
    chk(skp["Silver"] == max(skp.values()) and skp["Silver"] > 0.1 and all(skp[p] < 0.1 for p in ("Gold", "Platinum", "Palladium")), "Silver is the best metal for Skewness")
    chk(lg["Gold"]["p3"]["long_pnl"] > 0.4 and lg["Silver"]["p3"]["long_pnl"] > 0.8 and gy.loc[2025] > 0.4 and sy.loc[2025] > 0.8 and sy.loc[2026] > 0.4 and sy.loc[2022] < -0.2, "Skewness P3 long legs and year concentration")
    chk(cw.loc["Skewness", "Value"] == cw.loc[SLEEVES, SLEEVES].min().min() and cw.loc["Skewness", "Value"] < -0.5, "Skewness-Value is the most negative pairing in the class")
    chk(ew["ir"] < 0 and iv["ir"] < 0 and all(x < 0 for x in ewD + ivD), "portfolios negative in every period")
    chk(ew4["ir"] < ew["ir"] < 0 and iv4["ir"] < iv["ir"] < 0, "Skewness trims the portfolio loss")
    cs = CS[v]["Skewness"].loc["2012-01-01":].dropna().cumsum(); cmo = CS[v]["Momentum"].loc["2012-01-01":].dropna().cumsum()
    chk(cmo.idxmax().year == 2020 and cmo.idxmin().year == 2025 and cs.idxmax().year == 2026 and cs.iloc[-1] < cs.max(), "Figure 3: Momentum peaks 2020 and bottoms 2025; Skewness peaks 2026 and gives back part of the gain")
    chk(st(v, "EW PORT")["ret"] < 0 and st(v, "EW PORT")["vol"] < min(st(v, k)["vol"] for k in SLEEVES), "portfolio volatility below every sleeve")

    B = []; P = lambda t: B.append(("p", t))
    B.append(("h3", "4.1.3 Precious Metals"))
    P(f"Precious Metals shows no clear premium from the core signals. Momentum (IR {I(mom['ir'])}), Carry ({I(car['ir'])}), Carry-Momentum ({I(cm['ir'])}) and Value ({I(val['ir'])}) all have a negative information ratio over the sample window, "
      f"and Skewness is the only sleeve with a positive one, a small {I(sk['ir'])}. Table 5 sets these results against the other asset classes. "
      f"Product by product, no core signal works across the four metals: the best core result in a single metal is Carry in Silver (IR {I(cp['Silver'])}), and Palladium is the weakest metal for Momentum, Carry and Carry-Momentum. "
      f"The subsections that follow take the sleeves in turn and relate the subperiod pattern to the market context, wording each link as consistent with the results and not as a test.")
    P(f"Momentum earns an annualised return of {rr(mom['ret'])} at a volatility of {V(mom['vol'])}, with a maximum drawdown of {M(mom['mdd'])} and an IR of {I(mom['ir'])}. It is flat in P1 (IR {I(pm[0])}) and negative in P2 ({I(pm[1])}) and P3 ({I(pm[2])}), "
      f"and no metal earns a clear positive result (Gold {I(mp['Gold'])}, Silver {I(mp['Silver'])}, Platinum {I(mp['Platinum'])}, Palladium {I(mp['Palladium'])}). Gold Momentum has two good years, 2013, when the front-month price fell by 28% and the position earned a log return of {N(gm.loc[2013])}, "
      f"and 2025 ({N(gm.loc[2025])}), and no other year above {N(sorted(gm.values)[-3])}. A possible reason is that trend rules have little to extract when returns follow macro variables instead of their own history. "
      f"The weekly correlation between gold returns and changes in the 10-year real yield (FRED series DFII10) is {N(ry['full']['corr'])} over the sample, {N(ry['p2']['corr'])} in P2 and {N(ry['p3']['corr'])} in P3, which is consistent with that reading.")
    P(f"Carry (annualised return {rr(car['ret'])}, IR {I(car['ir'])}) and Carry-Momentum ({rr(cm['ret'])}, IR {I(cm['ir'])}) show no consistent edge. Carry is negative in P1 (IR {I(pc[0])}) and P2 ({I(pc[1])}) and close to zero in P3 ({I(pc[2])}), "
      f"while Carry-Momentum is slightly negative in P1 ({I(pcm[0])}), positive in P2 ({I(pcm[1])}) and clearly negative in P3 ({I(pcm[2])}). The P3 result is consistent with a higher cost of carrying the physical metal when real yields are high, which pushes the curves of Gold and Silver deeper into contango. "
      f"The 10-year real yield averaged {U(ry['p3']['avg'])}% in P3 against {U(ry['p2']['avg'])}% in P2, and the average slope of the long tenor pair (Table 3) was {N(gslope['p3'][0], 1)}% for Gold (F1-F7) in P3 against {N(gslope['p2'][0], 1)}% in P2 and {N(gslope['p1'][0], 1)}% in P1, "
      f"and {N(sslope['p3'][0], 1)}% for Silver (F1-F6) in P3 against {N(sslope['p2'][0], 1)}% and {N(sslope['p1'][0], 1)}%.")
    P(f"The choice of tenor pairs does not change the conclusion. For reference, Carry has a negative IR on the short pair alone (F1-F2, {I(tt['Carry']['short'])}), on the long pair alone ({I(tt['Carry']['long'])}) and on their sum ({I(tt['Carry']['two'])}), "
      f"and Carry-Momentum is negative on the short pair ({I(tt['CarryMom']['short'])}) and on the sum ({I(tt['CarryMom']['two'])}) and only marginally positive on the long pair alone ({I(tt['CarryMom']['long'])}); the sum of Sections 3.3 and 3.4 remains the rule. "
      f"At the product level, Carry is close to zero or slightly positive in Gold ({I(cp['Gold'])}), Silver ({I(cp['Silver'])}) and Platinum ({I(cp['Platinum'])}), and the negative sleeve result comes from Palladium ({I(cp['Palladium'])}), "
      f"which is also the weakest metal for Momentum ({I(mp['Palladium'])}) and Carry-Momentum ({I(cmp_['Palladium'])}).")
    P(f"Value (annualised return {rr(val['ret'])}, IR {I(val['ir'])}) has no full-sample edge, and the picture differs by metal: Platinum is the only metal with a positive IR ({I(vp['Platinum'])}), Silver ({I(vp['Silver'])}) and Palladium ({I(vp['Palladium'])}) are close to zero and Gold is negative ({I(vp['Gold'])}). "
      f"By subperiod the sleeve is flat in P1 ({I(pv[0])}) and negative in P2 ({I(pv[1])}) and P3 ({I(pv[2])}). Gold's loss comes from P3 (IR {I(gvp3)}). The rule sells a metal whose third-contract price is more than 10% above its five-year average, "
      f"and the front-month gold price rose from ${_g.loc['2022-09-30']:,.0f} at the end of September 2022 to ${_g.loc['2025-12-31']:,.0f} at the end of 2025, while central banks bought 863 tonnes in 2025 against an annual average of 473 tonnes in 2010 to 2021 (World Gold Council). "
      f"Gold's Value position was short on more than 90% of the days of 2025 and lost {abs(gv.loc[2025]):.2f} in log return in that year.")
    P(f"Skewness (annualised return {rr(sk['ret'])}, volatility {V(sk['vol'])}, maximum drawdown {M(sk['mdd'])}, IR {I(sk['ir'])}) is the only positive sleeve of the class, and it is small. It is negative in P1 (IR {I(ps[0])}) and positive in P2 ({I(ps[1])}) and P3 ({I(ps[2])}). "
      f"Silver is the best metal (IR {I(skp['Silver'])}; Gold {I(skp['Gold'])}, Platinum {I(skp['Platinum'])}, Palladium {I(skp['Palladium'])}), so the sleeve result rests mainly on one metal. "
      f"The gain in P3 comes from long positions: the sleeve was long on {U(lg['Gold']['p3']['long_pct'], 0)}% of the days of P3 in Gold and {U(lg['Silver']['p3']['long_pct'], 0)}% in Silver, and the long legs earned {N(lg['Gold']['p3']['long_pnl'])} and {N(lg['Silver']['p3']['long_pnl'])} in log return before costs. "
      f"The gain is concentrated in 2025, when the sleeve returned {N(gy.loc[2025])} in Gold and {N(sy.loc[2025])} in Silver, and for Silver in 2026 ({N(sy.loc[2026])} to 23 September), after a loss of {abs(sy.loc[2022]):.2f} in 2022.")
    P(f"Because the position stayed long during the rally in gold, the result describes exposure to that rally more than a stable premium, a reading that agrees with the directional character of the Skewness sleeve noted in Section 3.6. "
      f"The sleeve has a correlation of {N(cw.loc['Skewness', 'Value'])} with Value, the most negative pairing in the class, which is consistent with Value selling the metals that have risen while Skewness stays long in them, and of {N(cw.loc['Skewness', 'Carry'])} with Carry. "
      f"Because of these offsets, adding Skewness to the four core sleeves trims the loss of the class portfolios but does not make them positive.")
    P(f"The Equal Weight portfolio (EW PORT; annualised return {rr(ew['ret'])}, volatility {V(ew['vol'])}, maximum drawdown {M(ew['mdd'])}, IR {I(ew['ir'])}) and the Inverse Vol portfolio ({rr(iv['ret'])}, {V(iv['vol'])}, {M(iv['mdd'])}, IR {I(iv['ir'])}) are both negative in the full sample and in every subperiod "
      f"(Equal Weight P1 {I(ewD[0])}, P2 {I(ewD[1])}, P3 {I(ewD[2])}; Inverse Vol {I(ivD[0])}, {I(ivD[1])} and {I(ivD[2])}). Skewness reduces the loss from {I(ew4['ir'])} to {I(ew['ir'])} for Equal Weight and from {I(iv4['ir'])} to {I(iv['ir'])} for Inverse Vol. In Figure 3 the portfolio lines fall by less than the Momentum line, whose cumulative return peaks in 2020 and reaches its low in 2025, while the Skewness line rises through 2025 and early 2026 and then gives back part of the gain. Section 4.2 treats the asset-class portfolios in full.")
    P(f"Virtual Barrels (2023, p. 86) attributes the success of these factor strategies in energy to the role of storage and to the behaviour of large market participants. Gold offers little of the second ingredient: producers hedge little, the global producer hedge book standing at 218 tonnes in the third quarter of 2017 and below 200 tonnes at the end of 2024 (World Gold Council), "
      f"so there are few commercial hedgers who would pay speculators for taking the other side. This is consistent with the absence of a premium in the core sleeves, although we do not test it. NGL, taken up next, is the opposite case: the core signals earn a positive IR in every subperiod, as they do in Energy, and earn more.")
    B.append(("fig", "fig_precious_combined.png", "Figure 3. Precious Metals: combined strategy performance (cumulative return, 2012 to 2026)"))
    return B


# =====================================================================================================================
def ngl_blocks():
    v, a = "ngl", "ngl"
    pr = VARIANTS[v][1]
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol")
    ew4, iv4 = st4(v, "EW PORT"), st4(v, "Inverse Vol")
    ewD, ivD = per(v, "EW PORT"), per(v, "Inverse Vol")
    ew4D = [st4(v, "EW PORT", w)["ir"] for w in ("p1", "p2", "p3")]
    cw = corr_within(v)
    oth = ("metals", "energy", "precious", "agri")
    oew = {t: st(t, "EW PORT")["ir"] for t in oth}; oiv = {t: st(t, "Inverse Vol")["ir"] for t in oth}
    mp = {p: prod_ir(a, p, "Momentum") for p in pr}; cp = {p: prod_ir(a, p, "Carry") for p in pr}
    cmp_ = {p: prod_ir(a, p, "CarryMom") for p in pr}; vf = {p: prod_ir(a, p, "Value") for p in pr}
    skp = {p: prod_ir(a, p, "Skewness") for p in pr}; skpp = {p: pper(a, p, "Skewness") for p in pr}
    vprod = {p: pper(a, p, "Value") for p in pr}; vpp = {p: prod_ir(a, p, "Value", "p3") for p in pr}
    lg = {p: legs(a, p) for p in pr}
    vy = yearly_log(CS[v]["Value"]); sy = yearly_log(CS[v]["Skewness"])
    from engine import _carry_base
    _ng = importlib.import_module("ngl")
    _sl = pd.concat([_carry_base(_ng.load_curve(p_), "F2", "F4").loc["2012-01-01":].dropna() for p_ in pr])
    _m = _sl.index.month
    f24w = 100 * _sl[(_m == 12) | (_m <= 3)].mean(); f24s = 100 * _sl[(_m >= 6) & (_m <= 9)].mean()
    _pr = _ng.load_f1_series_logret("Propane")["F1_raw"]
    eth_crash, _x = skew_episode(a, "Ethane", "2020-03-01", "2020-04-30")
    after = {p: skew_episode(a, p, "2020-05-01", "2021-12-31")[0] for p in ("Propane", "Butane", "Isobutane")}
    cmo = CS[v]["Momentum"].loc["2012-01-01":].dropna().cumsum()

    chk(all(x > 0 for x in pm + pc + pcm) and mom["ir"] > 0 and car["ir"] > 0 and cm["ir"] > 0, "NGL Momentum, Carry, Carry-Momentum positive in the full sample and every period")
    chk(ew["ir"] > max(oew.values()) and iv["ir"] > max(oiv.values()) and max(oew, key=oew.get) == "energy" and max(oiv, key=oiv.get) == "energy", "NGL portfolios highest full-sample IR; Energy second under both")
    chk(all(ewD[i] > max(stats(PORT[t][0], w)["ir"] for t in oth) and ivD[i] > max(stats(PORT[t][1], w)["ir"] for t in oth) for i, w in enumerate(("p1", "p2", "p3"))), "NGL portfolios highest IR in every subperiod under both constructions")
    chk(pv[0] < 0 and abs(pv[1]) < 0.1 and pv[2] > 0.8 and val["ir"] > 0 and ps[0] < -0.5 and ps[1] > 0.5 and ps[2] > 0 and sk["ir"] > 0, "NGL Value and Skewness patterns")
    chk(pm[1] > pm[0] > pm[2] > 0 and pc[2] < min(pc[0], pc[1]) and pcm[2] == max(pcm) and pv[2] == max(pv), "NGL: Momentum and Carry weakest in P3, Carry-Momentum and Value strongest in P3")
    allmins = {(c, k): min(pst(c, q, k)["ir"] for q in PRODUCTS[c]) for c in ("metals", "energy", "ngl", "precious", "agri") for k in SLEEVES}
    chk(max(allmins, key=allmins.get) == ("ngl", "Momentum") and min(mp.values()) > 0.6, "NGL Momentum has the highest weakest-product IR of any strategy in any class")
    chk(min(cp.values()) > 0.2 and min(cmp_.values()) > 0.05, "NGL Carry and Carry-Momentum positive in every product")
    chk(cmo.idxmax() == pd.Timestamp("2024-02-15") and cmo.iloc[-1] < cmo.max(), "NGL Momentum cumulative peak 15 Feb 2024, retraced since")
    chk(round(f24w, 1) == 3.7 and round(f24s, 1) == -1.7, "NGL F2-F4 seasonal slope")
    chk(all(vy.loc[y] > 0 for y in range(2022, 2027)) and vy.loc[2026] == vy.loc[2022:].max() and round(vy.loc[2026], 2) == 0.36 and round(vy.loc[2025], 2) == 0.09, "NGL Value 2022 to 2026")
    chk(vpp["Propane"] == max(vpp.values()) and vpp["Butane"] == sorted(vpp.values())[-2] and round(vpp["Propane"], 2) == 1.47, "NGL Value P3 led by Propane then Butane")
    chk(vf["Butane"] > 0.2 and vf["Isobutane"] > 0.1 and vf["Ethane"] < 0 and abs(vf["Propane"]) < 0.05, "NGL Value by product")
    chk(vprod["Propane"][0] < 0 and vprod["Propane"][1] < 0 and vprod["Propane"][2] > 1.4, "Propane Value by period")
    chk(round(_pr.loc["2026-02-27"], 2) == 0.67 and round(_pr.loc["2026-03-27"], 2) == 0.90, "Propane held contract prices")
    chk(all(skpp[p][0] < -0.2 for p in pr) and all(skpp[p][1] > 0.1 for p in pr), "NGL Skewness P1 negative and P2 positive in every product")
    chk(round(sy.loc[2020], 2) > 1.0 and sy.loc[2012] < -0.6 and sy.loc[2021] > 0.5 and sy.loc[2026] > 0.3, "NGL Skewness years")
    chk(eth_crash > 1.0 and min(after.values()) > 1.3, "NGL Skewness 2020 episode")
    chk(all(lg[p]["p3"]["long_pct"] > 75 for p in pr), "NGL Skewness long on most days of P3")
    flip = {}; short_feb = {}
    for p_ in pr:
        lp_ = _ng.load_f1_series_logret(p_)["log_price"]; pos_ = exec_shift(raw_signal_skewness(lp_, 252), 1).fillna(0)
        w_ = pos_.loc["2020-03-01":"2020-04-30"]; short_feb[p_] = float(pos_.loc["2020-02-24"]); flip[p_] = w_[w_ > 0].index[0]
    chk(all(x == -1 for x in short_feb.values()) and flip["Ethane"] == pd.Timestamp("2020-03-20") and all(flip[p_] == pd.Timestamp("2020-03-11") for p_ in ("Propane", "Butane", "Isobutane")), "NGL Skewness short on 24 Feb 2020 in all four, long from 11 March (Ethane 20 March)")
    cwc = {t: corr_within(t) for t in ("metals", "energy", "precious", "agri")}
    chk(all(cw.loc["Skewness", "Momentum"] < cwc[t].loc["Skewness", "Momentum"] and cw.loc["Skewness", "Carry"] < cwc[t].loc["Skewness", "Carry"] for t in cwc) and cw.loc["Skewness", "Value"] > 0, "NGL Skewness correlations most negative with Momentum and Carry; Value positive")
    chk(ew["ir"] > iv["ir"] and ew["ret"] > iv["ret"] and ew["mdd"] > iv["mdd"] and iv["vol"] < ew["vol"], "NGL EW ahead on return, IR, drawdown; IV marginally lower volatility")
    chk(ew4D[0] > ewD[0] and ew4D[1] < ewD[1] and abs(ew4["ir"] - ew["ir"]) < 0.05 and ew["vol"] < ew4["vol"], "Skewness lowers P1 and raises P2 portfolio IR, leaves the full sample unchanged, lowers volatility")
    sk1 = [skpp[p][0] for p in pr]

    B = []; P = lambda t: B.append(("p", t))
    B.append(("h3", "4.1.4 NGL"))
    P(f"NGL is the strongest asset class in the study. Momentum (IR {I(mom['ir'])}), Carry ({I(car['ir'])}) and Carry-Momentum ({I(cm['ir'])}) are positive in the full sample and in each of P1 to P3, "
      f"and the Equal Weight and Inverse Vol portfolios earn IRs of {I(ew['ir'])} and {I(iv['ir'])}, against {I(oew['energy'])} and {I(oiv['energy'])} for Energy, the next best class under either construction (Table 5). "
      f"The portfolio IR is also the highest of the five classes in each subperiod under both constructions (Table 6), so the result does not come from one episode. Value and Skewness are the exceptions within the class: "
      f"both are small in the full sample (IR {I(val['ir'])} and {I(sk['ir'])}), negative in P1 (Value {I(pv[0])}, Skewness {I(ps[0])}) and positive in P3 ({I(pv[2])} and {I(ps[2])}), and we show below that each rests on one regime.")
    P(f"Momentum earns an annualised return of {rr(mom['ret'])} at a volatility of {V(mom['vol'])}, with a maximum drawdown of {M(mom['mdd'])}. By subperiod the IR is {I(pm[0])} in P1, {I(pm[1])} in P2 and {I(pm[2])} in P3. "
      f"It works in every product (IR {I(min(mp.values()))} to {I(max(mp.values()))}), and its weakest product has the highest IR of any signal's weakest product in any asset class. "
      f"The cumulative return of the sleeve peaks on 15 February 2024 and retraces part of the gain afterwards (Figure 4), which is why the P3 IR is the lowest of the three. "
      f"The US export build-out is a possible backdrop for persistent trends: Mont Belvieu propane traded at an average discount of $0.89 per gallon to international prices in 2012, when export terminals were at capacity (EIA), and US propane exports averaged a record 1.8 million barrels per day in 2024 (EIA). "
      f"Ethane exports reached 492,000 barrels per day in 2024 against 65,000 in 2015, and normal butane exports 491,000 against 97,000 (OPIS, citing EIA). This is consistent with the results but is not tested.")
    P(f"Bogorad (2025a) is the closest comparison. He studies an equally weighted Momentum portfolio of Propane, Ethane and Butane over January 2015 to December 2025 and reports an IR of 0.99 for the full period, 1.23 up to the end of 2021 and 0.46 from 2022 (his Table 2), "
      f"so Momentum is profitable in both of his subsamples but weaker after 2022. Our Momentum IR of {I(mom['ir'])} and its decline to {I(pm[2])} in P3 point the same way. The two sets of figures are not like for like. "
      f"His contracts are ICE-listed, his window is shorter, his crossovers are (1,5), (5,20) and (10,60) against our (1,20), (5,60) and (20,250), his split date is 2 January 2022, and our universe adds Isobutane and starts in 2012. "
      f"He also excludes the average-settled front month and rolls into the nearest actively traded tenor, the same concern that leads us to use the second and third generic contracts as front and second contract (Section 2.3). "
      f"Bogorad (2025b) studies processing spreads between an NGL and its petrochemical derivative, a different strategy that we do not replicate.")
    P(f"Carry (annualised return {rr(car['ret'])}, volatility {V(car['vol'])}, maximum drawdown {M(car['mdd'])}, IR {I(car['ir'])}) is positive in every subperiod (P1 {I(pc[0])}, P2 {I(pc[1])}, P3 {I(pc[2])}) and in every product (IR {I(min(cp.values()))} to {I(max(cp.values()))}). "
      f"Averaged over the four products, the F2-F4 slope is {N(f24w, 1)}% in December to March, a backwardated curve, and {N(f24s, 1)}% in June to September, a contango, which is consistent with seasonal demand and inventory cycles that Carry can follow. "
      f"Bogorad (2025a) finds NGL carry substantially weaker and of little stand-alone value, and attributes this to term structures that inventory hedgers do not dominate and that are shaped by fractionation constraints and regional bottlenecks. "
      f"Our Carry result is much stronger. The methods and samples differ: he measures the slope between F4 and F15, we sum the z-scores of two slopes (F2-F4 and F2-F14, Table 3), and his window is 2015 to 2025. We do not go beyond these differences in explaining it.")
    P(f"Carry-Momentum (annualised return {rr(cm['ret'])}, IR {I(cm['ir'])}) is positive in every subperiod ({I(pcm[0])}, {I(pcm[1])} and {I(pcm[2])}) and in every product (IR {I(min(cmp_.values()))} to {I(max(cmp_.values()))}). "
      f"Unlike Momentum and Carry, its IR is highest in P3. Momentum and Carry weaken in P3 (IR {I(pm[2])} and {I(pc[2])}) while Carry-Momentum ({I(pcm[2])}) and Value ({I(pv[2])}) strengthen, "
      f"and the class portfolios keep an IR of {I(ewD[2])} (Equal Weight) and {I(ivD[2])} (Inverse Vol) in P3 even though two of the sleeves weaken, which is consistent with this rotation. "
      f"Value is the other source of the improvement and is the subject of the next paragraph.")
    P(f"The P3 result for Value ({I(pv[2])}) is not a one-year event: the sleeve earns a positive log return in each year from 2022 to 2026, and 2026 is its best year of the period ({N(vy.loc[2026])}, against {N(vy.loc[2025])} in 2025). "
      f"It is led by Propane (IR {I(vpp['Propane'])} in P3) and Butane ({I(vpp['Butane'])}). Over the full sample the edge sits in Butane ({I(vf['Butane'])}) and Isobutane ({I(vf['Isobutane'])}), while Ethane ({I(vf['Ethane'])}) and Propane ({I(vf['Propane'])}) show none, "
      f"and Propane's IR is {I(vprod['Propane'][0])} in P1, {I(vprod['Propane'][1])} in P2 and {I(vprod['Propane'][2])} in P3, so the class result is one of the P3 regime. "
      f"The war that began on 28 February 2026 and the closure of the Strait of Hormuz disrupted around 30% of global LPG supply (Veson Nautical estimate) and sent US LPG exports to a record 3.3 million barrels per day in April 2026 (S&P Global). "
      f"In our series the Propane contract held by the strategy rose from ${_pr.loc['2026-02-27']:.2f} per gallon on 27 February to ${_pr.loc['2026-03-27']:.2f} on 27 March, which is consistent with the gain in 2026.")
    P(f"Skewness (annualised return {rr(sk['ret'])}, volatility {V(sk['vol'])}, maximum drawdown {M(sk['mdd'])}, IR {I(sk['ir'])}) is a single-regime result. It is negative in all four products in P1 (IR {I(max(sk1))} to {I(min(sk1))}) and positive in all four in P2 ({I(min(x[1] for x in skpp.values()))} to {I(max(x[1] for x in skpp.values()))}). "
      f"By calendar year it loses {abs(sy.loc[2012]):.2f} in 2012 and earns {N(sy.loc[2020])} in 2020 and {N(sy.loc[2021])} in 2021. The sleeve was short in all four products on 24 February 2020, before the collapse of that spring. "
      f"Ethane's position earned {N(eth_crash)} in log return before costs in March and April 2020, turning long on 20 March, and the other three products turned long on 11 March and earned {N(after['Propane'])} in Propane, {N(after['Butane'])} in Butane and {N(after['Isobutane'])} in Isobutane from May 2020 to December 2021, "
      f"after which the sleeve stayed long on {U(min(lg[p]['p3']['long_pct'] for p in pr), 0)}% or more of the days of P3 in every product. Its P3 IR of {I(ps[2])} is small beside the 2020 to 2021 gain.")
    P(f"The sleeve correlates at {N(cw.loc['Skewness', 'Momentum'])} with Momentum and {N(cw.loc['Skewness', 'Carry'])} with Carry, the most negative pairings of any asset class for those two, and at {N(cw.loc['Skewness', 'Value'])} with Value. "
      f"At the product level Skewness is positive in Ethane ({I(skp['Ethane'])}), about flat in Isobutane ({I(skp['Isobutane'])}) and slightly negative in Propane ({I(skp['Propane'])}) and Butane ({I(skp['Butane'])}). "
      f"The weak full-sample result is compatible with Fernandez-Perez, Fuertes and Miffre (2021), who find no skewness premium in energy futures; their sort is cross-sectional and runs over a different window, so the two results are not a like-for-like test. "
      f"Here the sleeve matters mainly through diversification: adding it to the four core sleeves lowers the volatility of the Equal Weight portfolio from {V(ew4['vol'])} to {V(ew['vol'])}, while the full-sample IR is almost unchanged ({I(ew4['ir'])} to {I(ew['ir'])}; Inverse Vol {I(iv4['ir'])} to {I(iv['ir'])}).")
    P(f"The two portfolio constructions are close, with Equal Weight ahead on return, IR and drawdown: it earns {rr(ew['ret'])} a year at a volatility of {V(ew['vol'])} with a maximum drawdown of {M(ew['mdd'])}, against {rr(iv['ret'])}, {V(iv['vol'])} and {M(iv['mdd'])} for Inverse Vol. "
      f"The Equal Weight IR is {I(ewD[0])} in P1, {I(ewD[1])} in P2 and {I(ewD[2])} in P3, and the Inverse Vol IR {I(ivD[0])}, {I(ivD[1])} and {I(ivD[2])}. Skewness moves the profile between subperiods: the Equal Weight IR falls in P1 from {I(ew4D[0])} to {I(ewD[0])} and rises in P2 from {I(ew4D[1])} to {I(ewD[1])}. "
      f"In Figure 4 the Momentum and Carry sleeves accumulate most of their gain after 2018 and dominate the scale of the chart, while the portfolio lines are smoother and sit far below them because they average five sleeves, two of which are close to zero. "
      f"Section 4.2 sets the portfolios against those of the other classes. Agriculture, the last class, resembles Precious Metals: the core signals earn no premium and Skewness is the only positive sleeve.")
    B.append(("fig", "fig_ngl_combined.png", "Figure 4. NGL: combined strategy performance (cumulative return, 2012 to 2026)"))
    return B


def agri_blocks():
    v, a = "agri", "agri"
    pr = VARIANTS[v][1]
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol")
    ew4, iv4 = st4(v, "EW PORT"), st4(v, "Inverse Vol")
    ewD, ivD = per(v, "EW PORT"), per(v, "Inverse Vol")
    ew4D = [st4(v, "EW PORT", w)["ir"] for w in ("p1", "p2", "p3")]; iv4D = [st4(v, "Inverse Vol", w)["ir"] for w in ("p1", "p2", "p3")]
    cw = corr_within(v)
    tt = tenor_table(v)
    mp = {p: prod_ir(a, p, "Momentum") for p in pr}; skp = {p: prod_ir(a, p, "Skewness") for p in pr}
    core = {(p, k): prod_ir(a, p, k) for p in pr for k in CORE}
    best = max(core, key=core.get); worst3 = sorted(core, key=core.get)[:3]
    cof_cm = pper(a, "Coffee", "CarryMom"); cof_c = pper(a, "Coffee", "Carry"); cof_v = pper(a, "Coffee", "Value")
    ex_cof = [p for p in pr if p != "Coffee"]
    xc = {k: ew_intersection([nets()[(a, p)][k] for p in ex_cof]) for k in ("Carry", "CarryMom")}
    xcm_p2 = stats(xc["CarryMom"], "p2")["ir"]; xc_p3 = stats(xc["Carry"], "p3")["ir"]
    lg = {p: legs(a, p) for p in pr}
    _a = importlib.import_module("agri")
    _c = {p_: _a.load_curve(p_)["F1"] for p_ in ("Coffee", "Wheat", "Corn", "SoybeanOil")}
    cv = yearly_log(nets()[(a, "Corn")]["Value"]); cvp1 = pst(a, "Corn", "Value", "p1")["ir"]
    sy = yearly_log(CS[v]["Skewness"])
    wy = yearly_log(nets()[(a, "Wheat")]["Skewness"]); cy = yearly_log(nets()[(a, "Corn")]["Skewness"])
    soy_y = yearly_log(nets()[(a, "Soybean")]["Skewness"]); soyoil_y = yearly_log(nets()[(a, "SoybeanOil")]["Skewness"])
    cs = {k: (np.exp(CS[v][k].loc["2012-01-01":].fillna(0).cumsum()) - 1) * 100 for k in SLEEVES}
    ewc = (np.exp(PORT[v][0].loc["2012-01-01":].fillna(0).cumsum()) - 1) * 100; ivc = (np.exp(PORT[v][1].loc["2012-01-01":].fillna(0).cumsum()) - 1) * 100
    p3ret = stats(PORT[v][0], "p3")["ret"]; p1ret = stats(PORT[v][0], "p1")["ret"]

    # ---- claims
    chk(all(st(v, k)["ir"] < 0 for k in ("Momentum", "CarryMom", "Value")) and abs(car["ir"]) < 0.05 and sk["ir"] > 0.2 and ew["ir"] < 0 and iv["ir"] < 0, "agri: no core edge, Carry flat, Skewness the only positive sleeve, portfolios negative")
    chk({t for t in ("metals", "energy", "ngl", "precious", "agri") if st(t, "EW PORT")["ir"] < 0 and st(t, "Inverse Vol")["ir"] < 0} == {"precious", "agri"}, "Precious Metals and Agriculture are the only classes with both portfolios negative")
    chk(best == ("SoybeanOil", "Carry") and round(core[best], 2) == 0.22 and set(worst3) == {("Wheat", "CarryMom"), ("Corn", "Value"), ("Corn", "Momentum")}, "agri best and weakest core product-sleeves")
    chk(max(cs, key=lambda k: cs[k].iloc[-1]) == "Skewness" and min(cs, key=lambda k: cs[k].iloc[-1]) == "CarryMom" and ewc.iloc[-1] < 0 and ivc.iloc[-1] < 0 and ewc.idxmax() == pd.Timestamp("2014-10-03") and ivc.idxmax() == pd.Timestamp("2014-10-03"), "agri figure: Skewness highest, Carry-Momentum lowest, portfolios peak October 2014 and end below zero")
    chk(cs["Momentum"].idxmax() == pd.Timestamp("2014-10-02") and cs["Momentum"].iloc[-1] < 0, "agri Momentum peaks October 2014 and ends below zero")
    chk(pm[0] < 0 and pm[2] < 0 and 0 < pm[1] < 0.15 and all(mp[p] < 0 for p in ("Corn", "Wheat", "Soybean", "Sugar")) and 0 < mp["SoybeanOil"] < 0.15 and 0 < mp["Coffee"] < 0.15, "agri Momentum")
    chk(pc[0] < 0 and pcm[0] < 0 and pc[1] > 0 and pcm[1] > 0 and pc[2] < -0.3 and pcm[2] < -0.5 and pc[2] == min(pc) and pcm[2] == min(pcm), "agri Carry and Carry-Momentum: negative P1, positive P2, weakest P3")
    chk(round(cof_cm[1], 2) == 0.88 and round(cof_cm[2], 2) == -0.64 and round(cof_c[2], 2) == -0.61, "agri Coffee swing")
    chk(xcm_p2 < 0 < pcm[1] and xc_p3 > pc[2] + 0.3, "agri Coffee is the swing")
    chk(abs(_c["Coffee"].loc["2021-07-26"] / _c["Coffee"].loc["2021-07-19"] - 1 - 0.34) < 0.005 and _c["Coffee"][(_c["Coffee"] >= _c["Coffee"].loc["2021-07-26"]) & (_c["Coffee"].index < "2021-07-26")].index.max() == pd.Timestamp("2014-10-17"), "agri arabica +34% in a week and highest front-month price since October 2014")
    chk(round(_c["Coffee"].loc["2025-02-13"] / 100, 2) == 4.39 and _c["Coffee"].idxmax() == pd.Timestamp("2025-02-13") and round(_c["Coffee"].loc["2026-09-23"] / 100, 2) == 2.76, "agri Coffee high and end level")
    chk(abs(tt["Carry"]["short"] - tt["Carry"]["prev"]) < 1e-9 and abs(tt["CarryMom"]["short"] - tt["CarryMom"]["prev"]) < 1e-9, "agri short pair equals the previous single pair F1-F2")
    chk(tt["Carry"]["prev"] < tt["Carry"]["two"] < tt["Carry"]["long"] and tt["CarryMom"]["two"] < min(tt["CarryMom"]["short"], tt["CarryMom"]["long"]) and round(tt["Carry"]["prev"], 2) == -0.23 and round(tt["Carry"]["long"], 2) == 0.14, "agri tenor-pair comparison")
    chk(abs(pv[0]) < 0.05 and pv[1] < -0.2 and -0.1 < pv[2] < 0 and round(cvp1, 2) == -0.50 and [round(cv.loc[y], 2) for y in range(2012, 2017)] == [-0.03, -0.20, -0.05, -0.19, -0.12] and round(cof_v[0], 2) == 0.58, "agri Value")
    chk(_c["Corn"].loc["2012"].idxmax() == pd.Timestamp("2012-08-21") and round(_c["Corn"].loc["2012-08-21"] / 100, 2) == 8.31 and _c["Corn"].loc["2012-08-21"] == _c["Corn"].loc[:"2012-12-31"].max(), "agri Corn 2012 high in our series")
    chk(min(skp[p] for p in ("Corn", "Wheat", "Soybean", "SoybeanOil")) > 0.2 and skp["Coffee"] < -0.2 and -0.1 < skp["Sugar"] < 0 and skp["SoybeanOil"] == max(skp.values()), "agri Skewness by product")
    chk(ps[0] > 0.3 and ps[1] < -0.15 and ps[2] > 0.5, "agri Skewness periods")
    chk(sy.loc[2014] > 0.15 and sy.loc[2015] > 0.15 and sy.loc[2016] < -0.15, "agri Skewness 2014 to 2016")
    chk(lg["Wheat"]["full"]["long_pct"] < 20 and lg["Wheat"]["full"]["short_pnl"] > 0.9 and lg["Wheat"]["p3"]["short_pnl"] > 0.5, "agri Wheat short leg")
    chk(round(sy.loc[2022], 2) == 0.27 and cy.loc[2022] > 0.4 and soyoil_y.loc[2022] > 0.4 and soy_y.loc[2022] > 0.3 and wy.loc[2023] > 0.3, "agri Skewness 2022 and 2023")
    chk(lg["Coffee"]["full"]["long_pnl"] < -0.5 and lg["Coffee"]["full"]["short_pnl"] < -0.5, "agri Coffee Skewness loses on both legs")
    chk(cs["Skewness"].idxmax() == pd.Timestamp("2026-01-06") and cs["Skewness"].iloc[-1] < cs["Skewness"].max(), "agri Skewness cumulative high January 2026, gives back part")
    chk(all(abs(cw.loc["Skewness", k]) < 0.15 for k in ("Momentum", "Carry", "CarryMom", "Value")), "agri Skewness correlations small")
    chk(ewD[0] < 0 and ewD[1] > 0 and ewD[2] < -0.3 and ivD[0] < 0 and 0 < ivD[1] < 0.1 and ivD[2] < -0.25 and ew4D[2] < ewD[2] and iv4D[2] < ivD[2] and ew4["ir"] < ew["ir"] and iv4["ir"] < iv["ir"], "agri portfolios by period; Skewness trims P3 and the full-sample loss")
    chk(abs(ewD[0]) < 0.1 and ivD[0] < -0.2 and p3ret * 4.73 < p1ret * 5, "agri Equal Weight loses little in P1; Inverse Vol more; P3 loss larger")
    chk(round(_c["Wheat"].loc["2022-03-07"] / 100, 2) == 14.25 and _c["Wheat"].loc["2022"].idxmax() == pd.Timestamp("2022-03-07") and abs(_c["Wheat"].loc["2026-09-23"] / 100 - 7.085) < 1e-6, "agri Wheat levels")
    chk(round(_c["Corn"].loc["2022-04-29"] / 100, 2) == 8.18 and round(_c["Corn"].loc["2026-09-23"] / 100, 2) == 5.29 and round(_c["SoybeanOil"].loc["2022-04-28"], 1) == 90.6 and round(_c["SoybeanOil"].loc["2026-09-23"], 1) in (67.2, 67.3), "agri Corn and Soybean Oil levels")

    B = []; P = lambda t: B.append(("p", t))
    B.append(("h3", "4.1.5 Agriculture"))
    P(f"Agriculture is, with Precious Metals, one of the two classes in which neither portfolio earns a positive IR, and none of its four core sleeves has an edge. Momentum ({I(mom['ir'])}), Carry-Momentum ({I(cm['ir'])}) and Value ({I(val['ir'])}) are negative over the full sample and Carry is flat ({I(car['ir'])}). "
      f"Skewness is the only sleeve with a positive IR of any size ({I(sk['ir'])}). The Equal Weight portfolio earns {I(ew['ir'])} (annualised return {rr(ew['ret'])}, volatility {V(ew['vol'])}, maximum drawdown {M(ew['mdd'])}) and the Inverse Vol portfolio {I(iv['ir'])} ({rr(iv['ret'])}, {V(iv['vol'])}, {M(iv['mdd'])}). "
      f"The decomposition by product gives the same answer. The best core result in a single product is Carry in Soybean Oil (IR {I(core[('SoybeanOil', 'Carry')])}), and the weakest are Wheat Carry-Momentum ({I(core[('Wheat', 'CarryMom')])}), Corn Value ({I(core[('Corn', 'Value')])}) and Corn Momentum ({I(core[('Corn', 'Momentum')])}). "
      f"Figure 5 shows the same ordering in cumulative terms: Skewness finishes highest, Carry-Momentum finishes lowest, and the two portfolio lines rise to a peak in October 2014 and end below their starting level. The paragraphs below take the sleeves in turn.")
    P(f"Momentum earns an annualised return of {rr(mom['ret'])} at a volatility of {V(mom['vol'])}, with a maximum drawdown of {M(mom['mdd'])}. Its IR is {I(pm[0])} in P1, {I(pm[1])} in P2 and {I(pm[2])} in P3, so it loses in two of the three subperiods, and its cumulative return peaks in October 2014 and ends below its starting level. "
      f"By product it is negative in Corn ({I(mp['Corn'])}), Wheat ({I(mp['Wheat'])}), Soybean ({I(mp['Soybean'])}) and Sugar ({I(mp['Sugar'])}) and modestly positive in Soybean Oil ({I(mp['SoybeanOil'])}) and Coffee ({I(mp['Coffee'])}). "
      f"The P3 loss is consistent with the price path that opened that subperiod. Wheat peaked at ${_c['Wheat'].loc['2022-03-07'] / 100:.2f} per bushel on 7 March 2022 after Russia's invasion of Ukraine and stood at ${hu(_c['Wheat'].loc['2026-09-23'] / 100)} on 23 September 2026, Corn fell from ${_c['Corn'].loc['2022-04-29'] / 100:.2f} on 29 April 2022 to ${_c['Corn'].loc['2026-09-23'] / 100:.2f}, "
      f"and Soybean Oil from {_c['SoybeanOil'].loc['2022-04-28']:.1f} cents per pound on 28 April 2022 to {hu(_c['SoybeanOil'].loc['2026-09-23'], 1)}. The FAO food price index peaked in March 2022 at 159.3 points, the highest since 1990, and its 2023 average was 13.7% below that of 2022. "
      f"A trend rule that follows a spike is exposed to a reversal of this kind, as it was in Metals.")
    P(f"Carry (annualised return {rr(car['ret'])}, volatility {V(car['vol'])}, IR {I(car['ir'])}) and Carry-Momentum ({rr(cm['ret'])}, volatility {V(cm['vol'])}, maximum drawdown {M(cm['mdd'])}, IR {I(cm['ir'])}) are negative in P1 ({I(pc[0])} and {I(pcm[0])}), positive in P2 ({I(pc[1])} and {I(pcm[1])}) and weakest in P3 ({I(pc[2])} and {I(pcm[2])}). "
      f"The P2 and P3 results turn on Coffee. Carry-Momentum in Coffee has an IR of {I(cof_cm[1])} in P2, the period of the Brazilian frosts of July 2021, when arabica rose by 34% in a week in our series (19 to 26 July) to its highest front-month price since October 2014, and {I(cof_cm[2])} in P3, with Carry at {I(cof_c[2])}, "
      f"after the price reached ${_c['Coffee'].loc['2025-02-13'] / 100:.2f} per pound on 13 February 2025 in our front-month series and fell to ${_c['Coffee'].loc['2026-09-23'] / 100:.2f} by 23 September 2026. "
      f"Without Coffee, the class Carry-Momentum sleeve has an IR of {I(xcm_p2)} in P2, and the class Carry sleeve has an IR of {I(xc_p3)} in P3 against {I(pc[2])} with it. Repeated spikes and retracements of this kind are consistent with slope signals that change sign without a lasting trend to follow.")
    P(f"The two-pair rule of Sections 3.3 and 3.4 does not rescue either sleeve. The Carry IR is {I(tt['Carry']['prev'])} on the short pair (F1-F2) alone, {I(tt['Carry']['long'])} on the long pair alone and {I(tt['Carry']['two'])} on their sum. The Carry-Momentum IR is {I(tt['CarryMom']['short'])} on the short pair, {I(tt['CarryMom']['long'])} on the long pair and {I(tt['CarryMom']['two'])} on their sum. "
      f"The sum therefore lifts Carry above the short pair but lowers Carry-Momentum below either single pair. Because we chose the combination by comparing results on this sample, we read these figures as a description of the sample and not as evidence for or against the rule, a point to which Section 5.5 returns.")
    P(f"Value (annualised return {rr(val['ret'])}, volatility {V(val['vol'])}, maximum drawdown {M(val['mdd'])}, IR {I(val['ir'])}) is flat in P1 ({I(pv[0])}), negative in P2 ({I(pv[1])}) and slightly negative in P3 ({I(pv[2])}). "
      f"The P1 figure hides a split. Coffee earns {I(cof_v[0])} in that period, while Corn is the weakest product, with an IR of {I(cvp1)} and a loss in every year from 2012 to 2016 (log returns of {', '.join(N(cv.loc[y]) for y in range(2012, 2017))}). "
      f"This is consistent with the US drought of 2012, which pushed corn to a record (${_c['Corn'].loc['2012-08-21'] / 100:.2f} per bushel on 21 August in our series, with USDA projecting record season-average prices of $7.50 to $8.90 in August 2012). The rule sells a market that trades more than 10% above its five-year average, and it lost in each year from 2012 to 2016.")
    P(f"Skewness (annualised return {rr(sk['ret'])}, volatility {V(sk['vol'])}, maximum drawdown {M(sk['mdd'])}, IR {I(sk['ir'])}) is the one clearly positive sleeve, with an IR of {I(ps[0])} in P1, {I(ps[1])} in P2 and {I(ps[2])} in P3. It works in four of the six products (Soybean Oil {I(skp['SoybeanOil'])}, Soybean {I(skp['Soybean'])}, Corn {I(skp['Corn'])} and Wheat {I(skp['Wheat'])}) and is negative in Coffee ({I(skp['Coffee'])}) and Sugar ({I(skp['Sugar'])}). "
      f"The clearest case is Wheat. Its returns are spike-prone, so the trailing-year skewness is positive for most of the sample and the sleeve is short on {100 - lg['Wheat']['full']['long_pct']:.0f}% of days, as Section 3.6 prescribes after spike-prone returns. "
      f"That short leg earns {N(lg['Wheat']['full']['short_pnl'])} in log return before costs over the sample, of which {N(lg['Wheat']['p3']['short_pnl'])} falls in P3 as Wheat declined from its March 2022 peak. In 2022, Corn, Soybean Oil and Soybean add {N(cy.loc[2022])}, {N(soyoil_y.loc[2022])} and {N(soy_y.loc[2022])}, and Wheat adds {N(wy.loc[2023])} in 2023. "
      f"In Coffee, whose 2021 frost and 2025 record were both followed by sharp reversals, the signal loses on both legs (long leg {N(lg['Coffee']['full']['long_pnl'])}, short leg {N(lg['Coffee']['full']['short_pnl'])}).")
    P(f"The Skewness record is not a steady premium. The sleeve gains in 2014 and 2015 (log returns of {N(sy.loc[2014])} and {N(sy.loc[2015])}), loses {abs(sy.loc[2016]):.2f} in 2016, earns {N(sy.loc[2022])} in 2022 and reaches its cumulative high in January 2026 before giving back part of the gain, as Figure 5 shows. "
      f"It is nearly uncorrelated with the other four sleeves ({N(cw.loc['Skewness', 'Momentum'])} with Momentum, {N(cw.loc['Skewness', 'Carry'])} with Carry, {N(cw.loc['Skewness', 'CarryMom'])} with Carry-Momentum and {N(cw.loc['Skewness', 'Value'])} with Value), which fits its role in the portfolios, where it trims the losses without removing them. "
      f"The full-sample IRs improve from {I(ew4['ir'])} to {I(ew['ir'])} for Equal Weight and from {I(iv4['ir'])} to {I(iv['ir'])} for Inverse Vol when Skewness is added to the four core sleeves, and the P3 IRs from {I(ew4D[2])} to {I(ewD[2])} and from {I(iv4D[2])} to {I(ivD[2])}. "
      f"We read its gains as the product of particular episodes in grains and oilseeds and not as a premium of the kind found in NGL and Energy.")
    P(f"The two portfolios lose in P1 and P3 and gain slightly in P2. The Equal Weight IR is {I(ewD[0])} in P1, {I(ewD[1])} in P2 and {I(ewD[2])} in P3, and the Inverse Vol IR {I(ivD[0])}, {I(ivD[1])} and {I(ivD[2])}. "
      f"The P3 losses are the main drag on the full-sample result: Equal Weight returns {rr(p3ret)} a year in P3 against {rr(p1ret)} in P1, and Inverse Vol loses more than Equal Weight in P1. "
      f"The results are consistent with the view that spikes followed by reversals, in grains in 2022 and in coffee in 2024 and 2025, are the case that signals built on trend and curve slope handle worst. The reading is descriptive: we have run no significance tests, and the class rests on six products and a handful of episodes. "
      f"Section 4.2 places the portfolios of all five classes side by side.")
    B.append(("fig", "fig_agri_combined.png", "Figure 5. Agriculture: combined strategy performance (cumulative return, 2012 to 2026)"))
    return B


def blocks():
    out = []
    out += precious_blocks()
    out += ngl_blocks()
    out += agri_blocks()
    return out


if __name__ == "__main__":
    BL = blocks()
    for b in BL:
        if b[0] == "p":
            print("p [%d words]" % len(b[1].split()), b[1])
        elif b[0] == "tbl":
            print("tbl", b[1]); [print("   ", r) for r in b[2]]
        else:
            print(b[0], b[1:] if b[0] == "fig" else b[1])
        print()
    print("TOTAL WORDS (p blocks):", sum(len(b[1].split()) for b in BL if b[0] == "p"))
