from facts2 import *


def precious():
    v, a = "precious", "precious"
    pr = VARIANTS[v][1]
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol")
    ew4, iv4 = st4(v, "EW PORT"), st4(v, "Inverse Vol")
    ewD, ivD = per(v, "EW PORT"), per(v, "Inverse Vol")
    cw = corr_within(v)
    ry = real_yield_stats()
    chk(abs(round(ry["full"]["corr"], 2) + 0.39) < 0.006 and abs(round(ry["p2"]["corr"], 2) + 0.64) < 0.006, "gold real-yield correlations")
    gm = yearly_log(nets()[(a, "Gold")]["Momentum"]); gv = yearly_log(nets()[(a, "Gold")]["Value"])
    chk(round(gm.loc[2013], 2) == 0.25 and round(gm.loc[2025], 2) == 0.36 and round(gv.loc[2025], 2) == -0.45, "gold yearly returns")
    chk(pm[0] > -0.1 and pm[1] < -0.4 and pm[2] < -0.2, "precious Momentum period pattern")
    chk(pc[0] < 0 and pc[1] < 0 and abs(pc[2]) < 0.05 and pcm[0] < 0 and pcm[1] > 0 and pcm[2] < -0.5, "precious Carry negative P1 and P2, flat P3; CarryMom slightly negative P1, positive P2, clearly negative P3")
    tt = tenor_table(v)
    chk(round(tt["Carry"]["prev"], 2) == -0.17 and round(tt["CarryMom"]["long"], 2) == 0.04, "precious tenor table")
    vp = {p: pst(a, p, "Value")["ir"] for p in pr}
    chk(vp["Platinum"] > 0 > vp["Gold"] and abs(vp["Silver"]) < 0.1 and abs(vp["Palladium"]) < 0.1, "precious Value by metal")
    gvp3 = pst(a, "Gold", "Value", "p3")["ir"]
    chk(round(gvp3, 2) == -0.61, "gold Value P3")
    mp = {p: pst(a, p, "Momentum")["ir"] for p in pr}; cp = {p: pst(a, p, "Carry")["ir"] for p in pr}; cmp_ = {p: pst(a, p, "CarryMom")["ir"] for p in pr}
    chk(cp["Palladium"] == min(cp.values()) and cp["Palladium"] < -0.2 and mp["Palladium"] < mp["Platinum"] < mp["Silver"] and cmp_["Palladium"] == min(cmp_.values()), "precious Palladium weakest in Carry, Momentum and Carry-Momentum")
    skp = {p: pst(a, p, "Skewness")["ir"] for p in pr}
    lg = {p: legs(a, p) for p in pr}
    chk(skp["Silver"] > 0.1 and max(skp.values()) == skp["Silver"] and sk["ir"] > 0, "precious Skewness")
    chk(lg["Gold"]["p3"]["long_pnl"] > 0.4 and lg["Silver"]["p3"]["long_pnl"] > 0.8, "precious Skewness P3 long legs")
    gy = yearly_log(nets()[(a, "Gold")]["Skewness"]); sy = yearly_log(nets()[(a, "Silver")]["Skewness"])
    chk(gy.loc[2025] > 0.4 and sy.loc[2025] > 0.8 and sy.loc[2026] > 0.4, "precious Skewness 2025 concentration")
    chk(ew["ir"] < 0 and iv["ir"] < 0 and all(x < 0 for x in ewD + ivD), "precious portfolios negative in every period")
    chk(all(st(v, k)["ir"] < 0 for k in CORE) and sk["ir"] > 0, "precious: every core strategy negative, Skewness positive")
    # checks added in the final verification pass
    gslope = slope_stats(a, "Gold", "F1", "F7"); sslope = slope_stats(a, "Silver", "F1", "F6")
    chk(all(gslope[w][0] < gslope[q][0] and sslope[w][0] < sslope[q][0] for w, q in (("p3", "p2"), ("p2", "p1"))), "precious Gold and Silver long-pair contango deepens from P1 to P3")
    chk([round(gslope[w][0], 1) for w in ("p3", "p2", "p1")] == [-4.5, -1.8, -0.6] and [round(sslope[w][0], 1) for w in ("p3", "p2", "p1")] == [-4.5, -2.3, -1.1], "precious curve slopes quoted")
    chk(sorted(gm.values)[-1] == gm.loc[2025] and sorted(gm.values)[-2] == gm.loc[2013] and sorted(gm.values)[-3] < 0.12, "gold Momentum: 2025 and 2013 are the two best years, no other year above 0.12")
    chk(abs(round(ry["p3"]["corr"], 2) + 0.24) < 0.006 and round(ry["p3"]["avg"], 2) == 1.60 and round(ry["p2"]["avg"], 2) == 0.03, "precious real-yield P3 figures")
    _g = importlib.import_module("precious").load_curve("Gold")["F1"]
    chk(round(_g.loc["2022-09-30"]) == 1662 and round(_g.loc["2025-12-31"]) == 4341 and round(_g.loc["2013-12-31"] / _g.loc["2012-12-31"] - 1, 2) == -0.28, "gold F1 levels and 2013 fall")
    chk(cw.loc["Skewness", "Value"] == cw.loc[["Momentum", "Carry", "CarryMom", "Value", "Skewness"], ["Momentum", "Carry", "CarryMom", "Value", "Skewness"]].min().min(), "precious Skewness-Value is the most negative pairing")
    sy_p3 = {y: sy.loc[y] for y in range(2022, 2027)}
    chk(sy.loc[2025] > 0.8 and sy.loc[2026] > 0.5 and sy.loc[2022] < -0.2 and gy.loc[2025] > 0.4 and lg["Gold"]["p3"]["long_pnl"] > 0.4, "precious Skewness P3 profile by year")
    blocks = [("h2", "Precious Metals")]
    B = blocks.append
    B(("b", f"Momentum ({line(mom)}) is flat in P1 (IR {I(pm[0])}) and negative in P2 ({I(pm[1])}) and P3 ({I(pm[2])}). Precious Metals are priced primarily off macro drivers, above all real yields (the weekly correlation of gold returns with changes in the 10-year real yield, FRED series DFII10, "
            f"is {N(ry['full']['corr'])} over the sample, {N(ry['p2']['corr'])} in P2 and {N(ry['p3']['corr'])} in P3), currency-debasement expectations and tail-risk demand, not off their own recent price action, so trend-following has nothing to extract. "
            f"Gold Momentum earned its two best years in the 2013 sell-off, when gold fell 28% on Fed tapering and ETF outflows (a log return of {N(gm.loc[2013])}), and in the 2025 rally ({N(gm.loc[2025])}), and little otherwise."))
    B(("b", f"Carry ({line(car)}) and Carry-Momentum ({line(cm)}) show no consistent edge: Carry is negative in P1 (IR {I(pc[0])}) and P2 ({I(pc[1])}) and flat in P3 ({I(pc[2])}), while Carry-Momentum is slightly negative in P1 ({I(pcm[0])}), positive in P2 ({I(pcm[1])}) and clearly negative in P3 ({I(pcm[2])}), "
            f"consistent with the post-2022 higher-real-yield environment pushing Gold and Silver deeper into cost-of-carry contango: the 10-year real yield averaged {U(ry['p3']['avg'])}% in P3 against {U(ry['p2']['avg'])}% in P2, and Gold's F1-F7 curve averaged {N(gslope['p3'][0],1)}% in P3 against {N(gslope['p2'][0],1)}% in P2 and {N(gslope['p1'][0],1)}% in P1 (Silver F1-F6 {N(sslope['p3'][0],1)}%, {N(sslope['p2'][0],1)}% and {N(sslope['p1'][0],1)}%)."))
    B(("b", f"The long tenor pair does not change that conclusion. Carry IR: previous single pair (F1-F3) {I(tt['Carry']['prev'])}, short pair F1-F2 {I(tt['Carry']['short'])}, long pair alone {I(tt['Carry']['long'])}, two-pair sum {I(tt['Carry']['two'])}. "
            f"Carry-Momentum IR: previous single pair {I(tt['CarryMom']['prev'])}, short pair {I(tt['CarryMom']['short'])}, long pair alone {I(tt['CarryMom']['long'])}, two-pair sum {I(tt['CarryMom']['two'])}."))
    B(("b", f"Value ({line(val)}) carries no full-sample edge, and the pattern is mixed at the product level: Platinum is the only metal with a positive signal (IR {I(vp['Platinum'])}), Silver ({I(vp['Silver'])}) and Palladium ({I(vp['Palladium'])}) are flat, and Gold ({I(vp['Gold'])}) is negative. "
            f"Gold's loss is a P3 loss ({I(gvp3)}): Value shorts a metal that trades more than 10% above its five-year average, and gold rose from $1,662 at the end of September 2022 to $4,341 at the end of 2025, with central banks buying 863 tonnes in 2025 against a 2010-2021 annual average of 473 tonnes (World Gold Council). "
            f"Gold's Value position lost {abs(gv.loc[2025]):.2f} in log return in 2025 alone."))
    B(("b", f"Skewness ({line(sk)}) is the only sleeve in this asset class with a positive full-sample IR, and it is small. It is negative in P1 (IR {I(ps[0])}) and positive in P2 ({I(ps[1])}) and P3 ({I(ps[2])}). Silver is the best metal (IR {I(skp['Silver'])}; Gold {I(skp['Gold'])}, Platinum {I(skp['Platinum'])}, Palladium {I(skp['Palladium'])}). "
            f"The P3 result comes from long positions: the sleeve was long on {U(lg['Gold']['p3']['long_pct'],0)}% of P3 days in Gold and {U(lg['Silver']['p3']['long_pct'],0)}% in Silver, and the long legs earned {N(lg['Gold']['p3']['long_pnl'])} and {N(lg['Silver']['p3']['long_pnl'])} in log return, "
            f"concentrated in 2025 (sleeve log return Gold {N(gy.loc[2025])}, Silver {N(sy.loc[2025])}), when gold rose to $4,341 by the end of the year, and for Silver also in 2026 ({N(sy.loc[2026])} to 23 September), after a loss of {abs(sy.loc[2022]):.2f} in 2022. "
            f"It correlates at {N(cw.loc['Skewness', 'Value'])} with Value, the strongest negative pairing in the asset class, consistent with Value shorting the metals that have rallied while Skewness stays long them, and at {N(cw.loc['Skewness', 'Carry'])} with Carry."))
    B(("b", f"Portfolio construction: Equal Weight ({line(ew)}) and Inverse Vol ({line(iv)}) are both net negative full-sample and in every period (P1 {I(ewD[0])} / {I(ivD[0])}, P2 {I(ewD[1])} / {I(ivD[1])}, P3 {I(ewD[2])} / {I(ivD[2])}). "
            f"Skewness trims the loss (Equal Weight {I(ew4['ir'])} to {I(ew['ir'])}, Inverse Vol {I(iv4['ir'])} to {I(iv['ir'])}) but does not turn it positive. Precious Metals is, with Agriculture, one of the two asset classes where no core strategy earns a worthwhile IR (here every core strategy is net negative full-sample) and neither construction earns a positive IR."))
    B(("b", f"Individual-metal decomposition: Momentum has no edge in any metal (Gold {I(mp['Gold'])}, Silver {I(mp['Silver'])}, Platinum {I(mp['Platinum'])}, Palladium {I(mp['Palladium'])}). Carry is near zero or slightly positive in Gold ({I(cp['Gold'])}), Silver ({I(cp['Silver'])}) and Platinum ({I(cp['Platinum'])}); "
            f"its negative blended IR comes from Palladium ({I(cp['Palladium'])}), which is also the weakest metal for Momentum ({I(mp['Palladium'])}) and Carry-Momentum ({I(cmp_['Palladium'])}). Value's only positive edge sits in Platinum (IR {I(vp['Platinum'])})."))
    B(("b", "Fundamentally, gold producers hedge little (the global producer hedge book was 218 tonnes in Q3 2017 and under 200 tonnes by the end of 2024, 182 tonnes on the World Gold Council's first estimate and about 194 tonnes after later revisions), "
            "so there are few commercial hedgers paying an insurance premium to transfer downside risk to financial counterparties; without that premium, Momentum has no structural engine to harvest here."))
    B(("fig", "fig_precious_combined.png", "Figure 3. Precious Metals: Combined Strategy Performance (Cumulative Return, 2012-2026)"))
    return blocks


if __name__ == "__main__":
    for b in precious():
        print(b[0], b[1] if b[0] != "fig" else b[1:])
        print()
