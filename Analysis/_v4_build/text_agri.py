from facts2 import *


def agri():
    v, a = "agri", "agri"
    pr = VARIANTS[v][1]
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol")
    ew4, iv4 = st4(v, "EW PORT"), st4(v, "Inverse Vol")
    ewD, ivD = per(v, "EW PORT"), per(v, "Inverse Vol")
    ew4D, iv4D = [st4(v, "EW PORT", w)["ir"] for w in ("p1", "p2", "p3")], [st4(v, "Inverse Vol", w)["ir"] for w in ("p1", "p2", "p3")]
    cw = corr_within(v)
    chk(all(st(v, k)["ir"] < 0 for k in CORE) and sk["ir"] > 0.2, "agri: every core strategy negative, Skewness positive")
    chk(ew["ir"] < 0 and iv["ir"] < 0, "agri portfolios negative")
    mp = {p: pst(a, p, "Momentum")["ir"] for p in pr}
    chk(all(mp[p] < 0 for p in ("Corn", "Wheat", "Soybean", "Sugar")) and mp["SoybeanOil"] > 0 and mp["Coffee"] > 0, "agri Momentum by product")
    chk(pm[0] < 0 and pm[2] < 0 and pm[1] > 0, "agri Momentum periods")
    chk(pc[0] > 0 and pcm[0] > 0 and pc[1] > 0 and pcm[1] > 0 and pc[2] < -0.5 and pcm[2] < -0.5, "agri Carry/CarryMom periods")
    cof_cm = pper(a, "Coffee", "CarryMom"); cof_c = pper(a, "Coffee", "Carry")
    chk(round(cof_cm[1], 2) == 1.31 and round(cof_cm[2], 2) == -0.89 and round(cof_c[2], 2) == -0.72, "agri Coffee swing")
    tt = tenor_table(v)
    chk(round(tt["Carry"]["prev"], 2) == -0.23 and round(tt["Carry"]["long"], 2) == 0.14, "agri tenor table")
    chk(all(x <= 0.0 for x in (pv[1], pv[2])) and abs(pv[0]) < 0.05, "agri Value periods")
    cv = yearly_log(nets()[(a, "Corn")]["Value"])
    chk([round(cv.loc[y], 2) for y in range(2012, 2017)] == [-0.03, -0.20, -0.05, -0.19, -0.12], "agri Corn Value yearly")
    cvp1 = pst(a, "Corn", "Value", "p1")["ir"]
    chk(round(cvp1, 2) == -0.50, "agri Corn Value P1 (v3 printed -0.51 after double rounding)")
    skp = {p: pst(a, p, "Skewness")["ir"] for p in pr}; skpp = {p: pper(a, p, "Skewness") for p in pr}
    chk(min(skp[p] for p in ("Corn", "Wheat", "Soybean", "SoybeanOil")) > 0.2 and skp["Coffee"] < -0.2, "agri Skewness by product")
    lg = {p: legs(a, p) for p in pr}
    chk(lg["Wheat"]["full"]["long_pct"] < 20 and lg["Wheat"]["full"]["short_pnl"] > 0.9, "agri Wheat short leg")
    sy = yearly_log(CS[v]["Skewness"])
    wy = yearly_log(nets()[(a, "Wheat")]["Skewness"]); cy = yearly_log(nets()[(a, "Corn")]["Skewness"])
    soy_y = yearly_log(nets()[(a, "Soybean")]["Skewness"]); soyoil_y = yearly_log(nets()[(a, "SoybeanOil")]["Skewness"])
    chk(round(sy.loc[2022], 2) == 0.27 and cy.loc[2022] > 0.4 and soyoil_y.loc[2022] > 0.4 and soy_y.loc[2022] > 0.3 and wy.loc[2023] > 0.3, "agri Skewness 2022-2023")
    chk(ps[0] > 0 and ps[1] < 0 and ps[2] > 0.5, "agri Skewness periods")
    chk(ewD[2] < -0.3 and ivD[2] < -0.3 and ew4D[2] < ewD[2] and iv4D[2] < ivD[2], "agri P3 losses and Skewness trims them")
    core = {(p, k): pst(a, p, k)["ir"] for p in pr for k in CORE}
    best = max(core, key=core.get); worst3 = sorted(core, key=core.get)[:3]
    chk(best == ("Coffee", "CarryMom") and round(core[best], 2) == 0.14, "agri best core product-sleeve")
    chk(set(worst3) == {("Wheat", "CarryMom"), ("Corn", "Value"), ("Corn", "Momentum")}, f"agri weakest core product-sleeves {worst3}")
    allres = {(p, k): pst(a, p, k)["ir"] for p in pr for k in SLEEVES}
    chk(max(allres, key=allres.get) == ("SoybeanOil", "Skewness"), "agri best product-sleeve overall is SoybeanOil Skewness")
    names = {"CarryMom": "Carry-Momentum", "Momentum": "Momentum", "Value": "Value", "Carry": "Carry", "Skewness": "Skewness"}
    blocks = [("h2", "Agriculture")]
    B = blocks.append
    B(("b", f"Agriculture (six products: Corn, Wheat, Soybean, Soybean Oil, Coffee, Sugar) has no edge in any of the four core sleeves: all four are net negative full-sample, and Equal Weight ({line(ew)}) and Inverse Vol ({line(iv)}) follow. "
            f"Skewness ({line(sk)}) is the only sleeve with a positive full-sample IR. Together with Precious Metals it is one of the two asset classes where neither portfolio construction earns a positive IR."))
    B(("b", f"Momentum ({line(mom)}) is negative in P1 (IR {I(pm[0])}) and P3 ({I(pm[2])}) and marginally positive in P2 ({I(pm[1])}). By product it fails in Corn ({I(mp['Corn'])}), Wheat ({I(mp['Wheat'])}), Soybean ({I(mp['Soybean'])}) and Sugar ({I(mp['Sugar'])}) and works only modestly in Soybean Oil ({I(mp['SoybeanOil'])}) and Coffee ({I(mp['Coffee'])})."))
    B(("b", f"Carry ({line(car)}) and Carry-Momentum ({line(cm)}) earn a positive IR in P1 (Carry {I(pc[0])}, Carry-Momentum {I(pcm[0])}) and P2 ({I(pc[1])} / {I(pcm[1])}) and are at their worst in P3 ({I(pc[2])} / {I(pcm[2])}). "
            f"Coffee is the swing: Carry-Momentum in Coffee returns IR {I(cof_cm[1])} in P2, when the July 2021 Brazilian frosts lifted arabica by 34% in a week in our series (19 to 26 July) to its highest front-month price since October 2014 (Reuters, Bloomberg), and {I(cof_cm[2])} in P3 (Carry {I(cof_c[2])}), "
            f"after the price reached its high of $4.39/lb in our series on 13 February 2025 (market sources put the record for the most active contract at about $4.30 that month and the later all-time high at $4.38 on 23 October 2025) and fell back to $2.76/lb by 23 September 2026 in our series."))
    B(("b", f"The long tenor pair matters little for the result. Carry IR: previous single pair (F1-F2) {I(tt['Carry']['prev'])}, long pair alone {I(tt['Carry']['long'])}, two-pair blend {I(tt['Carry']['two'])}. Carry-Momentum IR: previous single pair {I(tt['CarryMom']['prev'])}, long pair alone {I(tt['CarryMom']['long'])}, two-pair blend {I(tt['CarryMom']['two'])}."))
    B(("b", f"Value ({line(val)}) is flat to negative: flat in P1 (IR {I(pv[0])}), negative in P2 ({I(pv[1])}) and P3 ({I(pv[2])}). Corn explains much of the P1 weakness in the individual products: Corn Value has an IR of {I(cvp1)} in P1 and loses in every year from 2012 to 2016 (log returns of {', '.join(N(cv.loc[y]) for y in range(2012, 2017))}), "
            f"starting with the 2012 US drought that pushed corn to a record, with USDA projecting record season-average prices of $7.50 to $8.90 per bushel in August 2012. Value shorts a market that trades more than 10% above its five-year average."))
    B(("b", f"Skewness ({line(sk)}) is the one positive sleeve: IR {I(ps[0])} in P1, {I(ps[1])} in P2 and {I(ps[2])} in P3. It works in four of the six products (Soybean Oil {I(skp['SoybeanOil'])}, Soybean {I(skp['Soybean'])}, Corn {I(skp['Corn'])}, Wheat {I(skp['Wheat'])}) and fails in Coffee ({I(skp['Coffee'])}) and Sugar ({I(skp['Sugar'])}). "
            f"The clearest case is Wheat: its returns are spike-prone (the 2012 drought, the 2022 invasion of Ukraine), so its trailing-year skewness is positive most of the time and the sleeve is short on {100 - lg['Wheat']['full']['long_pct']:.0f}% of days; that short leg earns {N(lg['Wheat']['full']['short_pnl'])} in log return over the sample, "
            f"including {N(lg['Wheat']['p3']['short_pnl'])} in P3 as Wheat fell from $14.25 on 7 March 2022 to $7.09. In 2022 Corn, Soybean Oil and Soybean add {N(cy.loc[2022])}, {N(soyoil_y.loc[2022])} and {N(soy_y.loc[2022])} in log return, and Wheat adds {N(wy.loc[2023])} in 2023 as it fell. In Coffee, where the 2021 frost and the 2025 record were followed by sharp reversals, the signal loses on both legs (long leg {N(lg['Coffee']['full']['long_pnl'])}, short leg {N(lg['Coffee']['full']['short_pnl'])}). "
            f"It correlates at {N(cw.loc['Skewness', 'Momentum'])} with Momentum, {N(cw.loc['Skewness', 'Carry'])} with Carry, {N(cw.loc['Skewness', 'CarryMom'])} with Carry-Momentum and {N(cw.loc['Skewness', 'Value'])} with Value."))
    B(("b", f"Portfolio construction: Equal Weight is positive in P1 ({I(ewD[0])}) and P2 ({I(ewD[1])}) and Inverse Vol in P1 ({I(ivD[0])}) and P2 ({I(ivD[1])}); both are clearly negative in P3 ({I(ewD[2])} / {I(ivD[2])}), and the P3 losses drive the negative full-sample result. "
            f"Skewness trims them (P3 Equal Weight {I(ew4D[2])} to {I(ewD[2])}, Inverse Vol {I(iv4D[2])} to {I(ivD[2])}; full-sample Equal Weight {I(ew4['ir'])} to {I(ew['ir'])}, Inverse Vol {I(iv4['ir'])} to {I(iv['ir'])}). "
            f"P3 opens with the Russia-Ukraine price spike and its reversal: Wheat peaked at $14.25/bu on 7 March 2022 and was $7.09 by 23 September 2026, Corn went from $8.18 on 29 April 2022 to $5.29 and Soybean Oil from 90.6 cents/lb on 28 April 2022 to 67.3, "
            f"while the FAO food price index peaked in March 2022 (159.3 points, the highest since 1990) and its 2023 average was 13.7% below 2022. Sharp spikes followed by reversals, in grains in 2022 and in coffee in 2024-2025, are the pattern signals built on trend and curve slope handle worst."))
    B(("b", f"Individual-product decomposition: no core sleeve works across the six products. The best single core product-sleeve result is Coffee Carry-Momentum (IR {I(core[best])}) and the three weakest are Wheat Carry-Momentum ({I(core[('Wheat', 'CarryMom')])}), Corn Value ({I(core[('Corn', 'Value')])}) and Corn Momentum ({I(core[('Corn', 'Momentum')])}); "
            f"no core product-sleeve result is above {I(core[best])}. The best results overall are Skewness in Soybean Oil ({I(skp['SoybeanOil'])}) and Soybean ({I(skp['Soybean'])})."))
    B(("fig", "fig_agri_combined.png", "Figure 5. Agriculture: Combined Strategy Performance (Cumulative Return, 2012-2026)"))
    return blocks


if __name__ == "__main__":
    for b in agri():
        print(b[0], b[1] if b[0] != "fig" else b[1:])
        print()
