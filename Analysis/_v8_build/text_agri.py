"""Agriculture bucket of v8 after the 10 November 2026 split: Corn, Wheat (CBOT SRW), Soybean and Live Cattle (Sugar, Cocoa, Coffee and Cotton are the Softs bucket, text_softs.py).
Every qualitative claim is asserted against the 0930 data before it is printed (chk); numbers come from the per-product net returns of outputs/final_dashboard_0930/products_nets.pkl."""
from facts2 import *
from facts_tenor import bucket_tenor_table


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
    # --- claims
    chk(all(st(v, k)["ir"] < 0 for k in ("Momentum", "Carry", "CarryMom", "Value")) and sk["ir"] > 0.4, "agri: Momentum, Carry, Carry-Momentum and Value negative, Skewness the only positive sleeve")
    chk(ew["ir"] < 0 and iv["ir"] < 0, "agri portfolios negative")
    neg_both = [t for t in BUCKETS if st(t, "EW PORT")["ir"] < 0 and st(t, "Inverse Vol")["ir"] < 0]
    chk(neg_both == ["precious", "agri", "softs"], f"buckets where neither portfolio earns a positive IR: {neg_both}")
    chk(all(x < 0 for x in pm), "agri Momentum negative in every period")
    mp = {p: pst(a, p, "Momentum")["ir"] for p in pr}
    chk(all(mp[p] < 0 for p in ("Corn", "Wheat", "Soybean")) and abs(mp["LiveCattle"]) < 0.05, "agri Momentum negative in Corn, Wheat, Soybean; Live Cattle flat")
    chk(all(x < 0 for x in pc + pcm) and pcm[2] < -1.0 and pc[1] < -0.6, "agri Carry and Carry-Momentum negative in every period, Carry-Momentum worst in P3, Carry worst in P2")
    cpp = {p: pst(a, p, "Carry")["ir"] for p in pr}; cmp_ = {p: pst(a, p, "CarryMom")["ir"] for p in pr}
    chk(min(cpp, key=cpp.get) == "LiveCattle" and min(cmp_, key=cmp_.get) == "LiveCattle" and cpp["LiveCattle"] < -0.5 and cmp_["LiveCattle"] < -0.6, "agri Live Cattle is the weakest product in Carry and Carry-Momentum")
    lcc = pper(a, "LiveCattle", "Carry")
    chk(lcc[1] < -1.0 and lcc[0] < -0.5, "agri Live Cattle Carry P1 and P2")
    chk(cmp_["Wheat"] < -0.5 and sorted(cmp_, key=cmp_.get)[1] == "Wheat", "agri Wheat is the second weakest in Carry-Momentum")
    chk(all(x < 0 for x in pv) and pv[0] < -0.4 and abs(pv[1]) < 0.1 and abs(pv[2]) < 0.1, "agri Value negative in every period, clearly only in P1")
    vp = {p: pst(a, p, "Value")["ir"] for p in pr}
    chk([p for p in pr if vp[p] > 0] == ["Wheat"] and min(vp, key=vp.get) == "Corn", "agri Wheat the only product with positive Value, Corn the weakest")
    wv = pper(a, "Wheat", "Value"); cvv = pper(a, "Corn", "Value"); lcv = pper(a, "LiveCattle", "Value")
    chk(wv[0] < 0 < wv[1] < wv[2] and cvv[0] < -0.5 and cvv[1] < -0.4 and lcv[2] < -0.8, "agri Value by period for Wheat, Corn, Live Cattle")
    cv = yearly_log(nets()[(a, "Corn")]["Value"])
    chk(all(cv.loc[y] < 0 for y in range(2012, 2017)), "agri Corn Value loses in every year 2012-2016")
    skp = {p: pst(a, p, "Skewness")["ir"] for p in pr}
    chk(all(skp[p] > 0 for p in pr) and max(skp, key=skp.get) == "Soybean" and skp["LiveCattle"] < 0.15, "agri Skewness positive in all four, best in Soybean, weakest Live Cattle")
    chk(ps[0] > 0 and ps[1] < 0 and ps[2] > 1.0, "agri Skewness periods")
    lg = {p: legs(a, p) for p in pr}
    chk(lg["Wheat"]["full"]["long_pct"] < 20 and lg["Wheat"]["full"]["short_pnl"] > 0.9, "agri Wheat short leg")
    wy = yearly_log(nets()[(a, "Wheat")]["Skewness"]); cy = yearly_log(nets()[(a, "Corn")]["Skewness"]); soy_y = yearly_log(nets()[(a, "Soybean")]["Skewness"]); sy = yearly_log(CS[v]["Skewness"])
    chk(cy.loc[2022] > 0.4 and soy_y.loc[2022] > 0.3 and wy.loc[2023] > 0.3 and sy.loc[2022] > 0.2, "agri Skewness 2022-2023")
    chk(all(x < 0 for x in ewD + ivD) and ewD[1] < ewD[0] and ivD[1] < ivD[0] and ewD[2] > ewD[0] and ivD[2] > ivD[0], "agri portfolios negative in every period, worst in P2, least negative in P3")
    chk(ew4["ir"] < ew["ir"] and iv4["ir"] < iv["ir"], "agri Skewness lifts the portfolio IR")
    chk(ew4D[0] < ewD[0] and ew4D[2] < ewD[2], "agri Skewness lifts Equal Weight P1 and P3")
    core = {(p, k): pst(a, p, k)["ir"] for p in pr for k in CORE}
    best = max(core, key=core.get); worst3 = sorted(core, key=core.get)[:3]
    chk(best == ("Wheat", "Value"), "agri best core product-sleeve is Wheat Value")
    chk(set(worst3) == {("LiveCattle", "CarryMom"), ("LiveCattle", "Carry"), ("Wheat", "CarryMom")}, f"agri weakest core product-sleeves {worst3}")
    allres = {(p, k): pst(a, p, k)["ir"] for p in pr for k in SLEEVES}
    chk(max(allres, key=allres.get) == ("Soybean", "Skewness"), "agri best product-sleeve overall is Soybean Skewness")
    names = {"CarryMom": "Carry-Momentum", "Momentum": "Momentum", "Value": "Value", "Carry": "Carry", "Skewness": "Skewness"}
    _a = importlib.import_module("agri")
    _c = {p_: _a.load_curve(p_)["F1"] for p_ in ("Wheat", "Corn")}
    chk(round(_c["Wheat"].loc["2022-03-07"] / 100, 2) == 14.25 and _c["Wheat"].loc["2022"].idxmax() == pd.Timestamp("2022-03-07"), "agri Wheat peak")
    chk(round(_c["Corn"].loc["2022-04-29"] / 100, 2) == 8.18, "agri Corn 2022 level")
    chk(_c["Wheat"].index[-1] == pd.Timestamp("2026-09-30"), "agri series end 30 Sep 2026")
    wh_end = _c["Wheat"].loc["2026-09-30"] / 100; co_end = _c["Corn"].loc["2026-09-30"] / 100
    chk(ps[2] > pv[2] and lg["Wheat"]["p3"]["short_pnl"] > 0.3, "agri Wheat short leg P3")
    pairs_txt = "F1-F2 plus F1-F6 for Corn and Wheat and F1-F2 plus F1-F7 for Soybean and Live Cattle"
    blocks = [("h2", "Agriculture")]
    B = blocks.append
    B(("b", f"Agriculture (four products: Corn, Wheat, Soybean and Live Cattle; Sugar and Coffee, previously part of it, are now in Softs and Soybean Oil is dropped) has no edge in any of the four core sleeves: Momentum ({I(mom['ir'])}), Carry ({I(car['ir'])}), Carry-Momentum ({I(cm['ir'])}) and Value ({I(val['ir'])}) are net negative full-sample, and Equal Weight ({line(ew)}) and Inverse Vol ({line(iv)}) follow. "
            f"Skewness ({line(sk)}) is the only sleeve with a positive full-sample IR. Together with Precious Metals and Softs it is one of three buckets where neither portfolio construction earns a positive IR. Live Cattle (CME, 40,000 lb, listed in six bimonthly contract months) is new to the bucket; Carry and Carry-Momentum use {pairs_txt}."))
    B(("b", f"Momentum ({line(mom)}) is negative in every period (P1 {I(pm[0])}, P2 {I(pm[1])}, P3 {I(pm[2])}). By product it is negative in Corn ({I(mp['Corn'])}), Wheat ({I(mp['Wheat'])}) and Soybean ({I(mp['Soybean'])}) and flat in Live Cattle ({I(mp['LiveCattle'])})."))
    B(("b", f"Carry ({line(car)}) and Carry-Momentum ({line(cm)}) are negative in every period (Carry P1 {I(pc[0])}, P2 {I(pc[1])}, P3 {I(pc[2])}; Carry-Momentum {I(pcm[0])}, {I(pcm[1])}, {I(pcm[2])}), Carry-Momentum worst in P3 and Carry worst in P2. "
            f"Live Cattle is the weakest product in both (Carry {I(cpp['LiveCattle'])}, Carry-Momentum {I(cmp_['LiveCattle'])}), with a Carry IR of {I(lcc[0])} in P1 and {I(lcc[1])} in P2; Wheat is the second weakest in Carry-Momentum ({I(cmp_['Wheat'])})."))
    ten, _, _ = bucket_tenor_table("agri")
    tc, tm = ten["Carry"], ten["CarryMom"]
    chk(all(tc[k]["ir"] < 0 and tm[k]["ir"] < 0 for k in ("short", "long", "two")) and tc["short"]["ir"] > tc["long"]["ir"] > tc["two"]["ir"] and tm["short"]["ir"] > tm["long"]["ir"] > tm["two"]["ir"], "agri tenor pairs: every variant negative, the short pair the best and the two-pair sum the worst in both sleeves")
    B(("b", f"The long tenor pair does not help in Agriculture. Carry IR: short pair alone (F1-F2) {I(tc['short']['ir'])}, long pair alone {I(tc['long']['ir'])}, two-pair sum {I(tc['two']['ir'])}. Carry-Momentum IR: short pair alone {I(tm['short']['ir'])}, long pair alone {I(tm['long']['ir'])}, two-pair sum {I(tm['two']['ir'])}. The two-pair sum, which the bucket uses, is the weakest variant for both sleeves and no variant earns a positive IR."))
    B(("b", f"Value ({line(val)}) is negative in every period: IR {I(pv[0])} in P1, {I(pv[1])} in P2 and {I(pv[2])} in P3. Wheat is the only product with a positive Value IR ({I(vp['Wheat'])}: {I(wv[0])} in P1, {I(wv[1])} in P2, {I(wv[2])} in P3). Corn is the weakest ({I(vp['Corn'])}; {I(cvv[0])} in P1 and {I(cvv[1])} in P2) and loses in every year from 2012 to 2016 (log returns of {', '.join(N(cv.loc[y]) for y in range(2012, 2017))}), "
            f"starting with the 2012 US drought that pushed corn to a record, with USDA projecting record season-average prices of $7.50 to $8.90 per bushel in August 2012; Live Cattle loses most in P3 (IR {I(lcv[2])}). "
            f"Value shorts a market that trades more than 10% above its five-year average, measured on the F2 contract (the previous version used F3), following the 1 November 2026 change to the Precious Metals and Agriculture configuration."))
    B(("b", f"Skewness ({line(sk)}) is the one positive sleeve: IR {I(ps[0])} in P1, {I(ps[1])} in P2 and {I(ps[2])} in P3. It is positive in all four products (Soybean {I(skp['Soybean'])}, Corn {I(skp['Corn'])}, Wheat {I(skp['Wheat'])}, Live Cattle {I(skp['LiveCattle'])}). "
            f"The clearest case is Wheat: its returns are spike-prone (the 2012 drought, the 2022 invasion of Ukraine), so its trailing-year skewness is positive most of the time and the sleeve is short on {100 - lg['Wheat']['full']['long_pct']:.0f}% of days; that short leg earns {N(lg['Wheat']['full']['short_pnl'])} in log return over the sample, "
            f"including {N(lg['Wheat']['p3']['short_pnl'])} in P3 as Wheat fell from ${_c['Wheat'].loc['2022-03-07'] / 100:.2f} on 7 March 2022 to ${wh_end:.2f}. In 2022 Corn and Soybean add {N(cy.loc[2022])} and {N(soy_y.loc[2022])} in log return, and Wheat adds {N(wy.loc[2023])} in 2023 as it fell. "
            f"It correlates at {N(cw.loc['Skewness', 'Momentum'])} with Momentum, {N(cw.loc['Skewness', 'Carry'])} with Carry, {N(cw.loc['Skewness', 'CarryMom'])} with Carry-Momentum and {N(cw.loc['Skewness', 'Value'])} with Value."))
    B(("b", f"Portfolio construction: Equal Weight is negative in every period (P1 {I(ewD[0])}, P2 {I(ewD[1])}, P3 {I(ewD[2])}), as is Inverse Vol (P1 {I(ivD[0])}, P2 {I(ivD[1])}, P3 {I(ivD[2])}); both are worst in P2 and least negative in P3. "
            f"Skewness trims the loss (full-sample Equal Weight {I(ew4['ir'])} to {I(ew['ir'])}, Inverse Vol {I(iv4['ir'])} to {I(iv['ir'])}; P1 Equal Weight {I(ew4D[0])} to {I(ewD[0])}, P3 {I(ew4D[2])} to {I(ewD[2])}). "
            f"P3 opens with the Russia-Ukraine price spike and its reversal: Wheat peaked at $14.25/bu on 7 March 2022 and was ${wh_end:.2f} by 30 September 2026, and Corn went from $8.18 on 29 April 2022 to ${co_end:.2f}, "
            f"while the FAO food price index peaked in March 2022 (159.3 points, the highest since 1990) and its 2023 average was 13.7% below 2022. Sharp spikes followed by reversals are the pattern signals built on trend and curve slope handle worst."))
    B(("b", f"Individual-product decomposition: no core sleeve works across the four products. The best single core product-sleeve result is {best[0]} {names[best[1]]} (IR {I(core[best])}) and the three weakest are Live Cattle Carry-Momentum ({I(core[('LiveCattle', 'CarryMom')])}), Live Cattle Carry ({I(core[('LiveCattle', 'Carry')])}) and Wheat Carry-Momentum ({I(core[('Wheat', 'CarryMom')])}); "
            f"the best result overall is Skewness in Soybean ({I(skp['Soybean'])})."))
    B(("fig", "fig_agri_combined.png", "Figure 5. Agriculture: Combined Strategy Performance (Cumulative Return, 2012-2026)"))
    return blocks


if __name__ == "__main__":
    for b in agri():
        print(b[0], b[1] if b[0] != "fig" else b[1:])
        print()


def _n(x, d=2):
    return f"{x:.{d}f}".replace("-", "−")


def agri_narr():
    """The narrative paragraph under the Agriculture heading (v7 layout: a typographic minus and no plus signs). Every claim asserted against the data."""
    v, a = "agri", "agri"
    pr = VARIANTS[v][1]
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol"); ewD, ivD = per(v, "EW PORT"), per(v, "Inverse Vol")
    chk(all(x < 0 for x in pm + pc + pcm + pv) and sk["ir"] > 0.4, "agri narrative: four core sleeves negative in every subperiod, Skewness positive")
    chk(pc[1] < -0.6 and pcm[2] < -1.0, "agri narrative: Carry worst in P2, Carry-Momentum worst in P3")
    cpp = {p: pst(a, p, "Carry")["ir"] for p in pr}; cmp_ = {p: pst(a, p, "CarryMom")["ir"] for p in pr}
    chk(min(cpp, key=cpp.get) == "LiveCattle" and min(cmp_, key=cmp_.get) == "LiveCattle", "agri narrative: Live Cattle weakest in Carry and Carry-Momentum")
    lg = legs(a, "Wheat")
    chk(lg["full"]["long_pct"] < 20 and lg["p3"]["short_pnl"] > 0.5 and ps[0] > 0 > ps[1] and ps[2] > 1.0, "agri narrative: Wheat short leg, Skewness by period")
    chk(all(pst(a, p, "Skewness")["ir"] > 0 for p in pr), "agri narrative: Skewness positive in all four products")
    chk(all(x < 0 for x in ewD + ivD) and ewD[1] < ewD[0] and ivD[1] < ivD[0], "agri narrative: portfolios negative in every subperiod, worst in P2")
    return (f"Agriculture (Corn, Wheat, Soybean and Live Cattle) shows no premium in any of the four core sleeves. Momentum (IR {_n(mom['ir'])}), Carry ({_n(car['ir'])}), Carry-Momentum ({_n(cm['ir'])}) and Value ({_n(val['ir'])}) are negative over the full sample and in every subperiod. "
            f"The curve signals lose most in P2 for Carry ({_n(pc[1])}) and in P3 for Carry-Momentum ({_n(pcm[2])}); P3 opens with the 2022 price spike in grains and its reversal. Live Cattle illustrates the weakness of the curve signals: it is the weakest product in both Carry ({_n(cpp['LiveCattle'])}) and Carry-Momentum ({_n(cmp_['LiveCattle'])}). "
            f"Signals built on trend and curve slope respond to such moves with a lag and are exposed to sharp reversals. Value is negative in every subperiod, with P1 the worst ({_n(pv[0])}). "
            f"Skewness is the only sleeve with a positive full-sample IR ({_n(sk['ir'])}) and is positive in all four products, but the result is uneven across subperiods (P1 {_n(ps[0])}, P2 {_n(ps[1])}, P3 {_n(ps[2])}) and is concentrated in P3, when spike-prone returns in Wheat kept the sleeve short on {100 - lg['full']['long_pct']:.0f}% of days and the short leg earned {_n(lg['p3']['short_pnl'])} in log return as prices fell from their 2022 peak. "
            f"The gains therefore appear to reflect the reversal of a single episode and not a stable premium. As a consequence, the Equal Weight (return {_n(ew['ret'], 1)}%, volatility {_n(ew['vol'], 1)}%, maximum drawdown {_n(ew['mdd'], 1)}%, IR {_n(ew['ir'])}) and Inverse Vol (return {_n(iv['ret'], 1)}%, volatility {_n(iv['vol'], 1)}%, maximum drawdown {_n(iv['mdd'], 1)}%, IR {_n(iv['ir'])}) portfolios are negative in every subperiod, with P2 the main drag ({_n(ewD[1])} and {_n(ivD[1])}).")
