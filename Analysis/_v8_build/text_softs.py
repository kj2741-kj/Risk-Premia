"""Softs bucket of v8 (new on 10 November 2026): Sugar No.11, Cocoa, Coffee C and Cotton No.2 (ICE US), split out of the old Agriculture bucket (Sugar and Coffee) plus the new Cocoa and Cotton.
Every qualitative claim is asserted against the 0930 data before it is printed (chk). The Coffee episodes (July 2021 frost, February 2025 high) are the ones already verified in the Agriculture text of v7."""
from facts2 import *


def softs():
    v, a = "softs", "softs"
    pr = VARIANTS[v][1]
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol")
    ew4, iv4 = st4(v, "EW PORT"), st4(v, "Inverse Vol")
    ewD, ivD = per(v, "EW PORT"), per(v, "Inverse Vol")
    ew4D = [st4(v, "EW PORT", w)["ir"] for w in ("p1", "p2", "p3")]
    cw = corr_within(v)
    # --- bucket level
    chk(val["ir"] > 0 and all(st(v, k)["ir"] < 0 for k in ("Momentum", "Carry", "CarryMom", "Skewness")), "softs: Value the only positive sleeve")
    chk(ew["ir"] < 0 and iv["ir"] < 0, "softs portfolios negative")
    neg_both = [t for t in BUCKETS if st(t, "EW PORT")["ir"] < 0 and st(t, "Inverse Vol")["ir"] < 0]
    chk(neg_both == ["precious", "agri", "softs"], f"buckets where neither portfolio earns a positive IR: {neg_both}")
    neg_sk = [t for t in BUCKETS if st(t, "Skewness")["ir"] < 0]
    chk(neg_sk == ["metals", "softs"], f"Skewness negative full-sample in {neg_sk}")
    chk(all(x < 0 for x in ps) and ps[0] > -0.3 and ps[1] < -0.35 and ps[2] < -0.35, "softs Skewness negative in every period")
    lower = [t for t in BUCKETS if st(t, "EW PORT")["ir"] < st4(t, "EW PORT")["ir"]]
    chk(lower == ["metals", "softs"], f"adding Skewness lowers the Equal Weight IR in {lower}")
    chk(pm[0] < -0.4 and abs(pm[1]) < 0.1 and abs(pm[2]) < 0.1, "softs Momentum by period")
    mp = {p: pst(a, p, "Momentum")["ir"] for p in pr}
    chk(mp["Coffee"] > 0 and all(mp[p] < 0 for p in ("Sugar", "Cocoa", "Cotton")) and min(mp, key=mp.get) == "Cotton", "softs Momentum positive only in Coffee, weakest in Cotton")
    chk(pc[0] < 0 < pc[1] and pc[2] < -0.3 and pcm[0] < 0 < pcm[1] and pcm[2] < -0.6, "softs Carry and Carry-Momentum: negative P1, positive P2, negative P3")
    cp = {p: pst(a, p, "Carry")["ir"] for p in pr}; cmp_ = {p: pst(a, p, "CarryMom")["ir"] for p in pr}
    cof_c = pper(a, "Coffee", "Carry"); cof_cm = pper(a, "Coffee", "CarryMom"); cot_c = pper(a, "Cotton", "Carry"); cot_cm = pper(a, "Cotton", "CarryMom")
    chk(cof_c[0] > 0.5 and cof_c[1] > 0.5 and cof_c[2] < -0.5 and cof_cm[1] > 0.8 and cof_cm[2] < -0.6, "softs Coffee Carry and Carry-Momentum swing")
    chk(min(cp, key=cp.get) == "Cotton" and min(cmp_, key=cmp_.get) == "Cotton" and all(x < 0 for x in cot_c + cot_cm), "softs Cotton the weakest in Carry and Carry-Momentum, negative in every period")
    ex_cof = [p_ for p_ in pr if p_ != "Coffee"]
    _xc = {k_: ew_intersection([nets()[(a, p_)][k_] for p_ in ex_cof]) for k_ in ("Carry", "CarryMom")}
    chk(stats(_xc["CarryMom"], "p2")["ir"] < 0 < pcm[1] and stats(_xc["Carry"], "p2")["ir"] < 0 < pc[1], "softs Coffee is the swing: without it Carry and Carry-Momentum are negative in P2")
    vp = {p: pst(a, p, "Value")["ir"] for p in pr}
    chk(pv[0] > 0.5 and pv[1] > 0.1 and pv[2] < -0.2, "softs Value by period")
    chk(vp["Cotton"] > vp["Cocoa"] > 0.1 and vp["Sugar"] < 0 and abs(vp["Coffee"]) < 0.01, "softs Value by product")
    cov = pper(a, "Cocoa", "Value"); cotv = pper(a, "Cotton", "Value"); cofv = pper(a, "Coffee", "Value")
    chk(cov[0] > 0.7 and cov[1] > 0.6 and cov[2] < -0.2 and cotv[2] > 0.4 and cofv[0] > 0.5, "softs Value by product and period")
    vy = yearly_log(CS[v]["Value"]); cvy = yearly_log(nets()[(a, "Cocoa")]["Value"])
    chk(vy.idxmin() == 2024 and vy.loc[2024] < -0.4 and cvy.loc[2024] < -1.4 and cvy.loc[2025] > 0.6 and cvy.loc[2026] > 0.4, "softs Value worst in 2024 (Cocoa -1.49), Cocoa recovers in 2025 and 2026")
    chk(sum(vy.loc[y] for y in range(2022, 2027)) < 0 < sum(vy.loc[y] for y in range(2022, 2027) if y != 2024), "softs Value P3 loss comes from 2024")
    _a = importlib.import_module("agri")
    _c = {p_: _a.load_curve(p_)["F1"] for p_ in ("Coffee", "Cocoa")}
    chk(abs(_c["Coffee"].loc["2021-07-26"] / _c["Coffee"].loc["2021-07-19"] - 1 - 0.34) < 0.005 and _c["Coffee"].loc["2021-07":"2021-08"].idxmax() == pd.Timestamp("2021-07-26"), "softs arabica +34% 19 to 26 July 2021")
    chk(round(_c["Coffee"].loc["2025-02-13"] / 100, 2) == 4.39 and _c["Coffee"].idxmax() == pd.Timestamp("2025-02-13"), "softs Coffee $4.39 high")
    chk(_c["Cocoa"].idxmax() == pd.Timestamp("2024-12-18") and round(_c["Cocoa"].max()) == 12565 and _c["Cocoa"].index[-1] == pd.Timestamp("2026-09-30"), "softs Cocoa high 18 Dec 2024")
    cof_end = _c["Coffee"].loc["2026-09-30"] / 100; coc_end = float(_c["Cocoa"].loc["2026-09-30"]); coc_hi = float(_c["Cocoa"].max())
    skp = {p: pst(a, p, "Skewness")["ir"] for p in pr}
    chk(all(skp[p] < 0 for p in pr) and min(skp, key=skp.get) == "Coffee" and max(skp, key=skp.get) == "Cotton", "softs Skewness negative in all four products, worst in Coffee")
    lg = {p: legs(a, p) for p in pr}
    csy = yearly_log(nets()[(a, "Cocoa")]["Skewness"]); cfy = yearly_log(nets()[(a, "Coffee")]["Skewness"])
    chk(csy.loc[2024] > 0.8 and csy.loc[2025] < -0.5 and csy.loc[2026] < -0.5, "softs Cocoa Skewness 2024 to 2026")
    chk(lg["Cocoa"]["full"]["short_pnl"] < -1.2 and lg["Cocoa"]["p3"]["short_pnl"] < -0.8 and lg["Cocoa"]["full"]["long_pnl"] > 0, "softs Cocoa Skewness short leg loses")
    chk(lg["Coffee"]["full"]["long_pnl"] < -0.6 and lg["Coffee"]["full"]["short_pnl"] < -0.6 and cfy.loc[2021] < -0.4 and cfy.loc[2024] < -0.5, "softs Coffee Skewness loses on both legs")
    chk(max(abs(x) for x in (skp["Sugar"], skp["Cotton"])) < 0.1, "softs Sugar and Cotton Skewness near zero")
    chk(lg["Sugar"]["full"]["long_pct"] < 30 and lg["Sugar"]["full"]["short_pnl"] > 0 and lg["Sugar"]["full"]["long_pnl"] < -0.5, "softs Sugar Skewness mostly short")
    chk(all(x < 0 for x in ewD[:1] + ewD[2:]) and ewD[1] > 0 and ivD[1] > 0 and ewD[2] < -0.7 and ivD[2] < -0.7 and ewD[2] < ew4D[2], "softs portfolios: P2 positive, P1 and P3 negative, P3 the worst and worsened by Skewness")
    chk(ewD[0] > ew4D[0] - 0.12 and ew4D[1] > ewD[1] and ew4["ir"] > ew["ir"] and iv4["ir"] > iv["ir"], "softs Skewness lowers the full-sample IR and P2")
    core = {(p, k): pst(a, p, k)["ir"] for p in pr for k in CORE}
    best = max(core, key=core.get); worst3 = sorted(core, key=core.get)[:3]
    chk(best == ("Cotton", "Value"), f"softs best core product-sleeve {best}")
    chk(worst3 == [("Cotton", "CarryMom"), ("Cotton", "Carry"), ("Cotton", "Momentum")], f"softs weakest core product-sleeves {worst3}")
    sg = {k: pst(a, "Sugar", k)["ir"] for k in SLEEVES}
    chk(max(abs(x) for x in sg.values()) < 0.1, "softs Sugar within 0.1 of zero in every sleeve")
    cofe = {k: pst(a, "Coffee", k)["ir"] for k in ("Momentum", "Carry", "CarryMom")}
    chk(all(cofe[k] > 0 for k in cofe), "softs Coffee positive in the three trend and curve sleeves")
    wsk = cw.loc["Skewness"]
    names = {"CarryMom": "Carry-Momentum", "Momentum": "Momentum", "Value": "Value", "Carry": "Carry", "Skewness": "Skewness"}
    pairs_txt = "F1-F2 plus F1-F6 for all four products"
    blocks = [("h2", "Softs")]
    B = blocks.append
    B(("b", f"Softs (four ICE US products: Sugar No.11, Cocoa, Coffee C and Cotton No.2) is a new bucket, split out of the previous Agriculture bucket (Sugar and Coffee) with Cocoa and Cotton added. Value is its only positive sleeve ({line(val)}); Momentum ({I(mom['ir'])}), Carry ({I(car['ir'])}), Carry-Momentum ({I(cm['ir'])}) and Skewness ({I(sk['ir'])}) are net negative full-sample, and Equal Weight ({line(ew)}) and Inverse Vol ({line(iv)}) follow. "
            f"Together with Precious Metals and Agriculture it is one of three buckets where neither portfolio construction earns a positive IR, and with Metals one of two where Skewness is negative full-sample. Carry and Carry-Momentum use {pairs_txt}."))
    B(("b", f"Momentum ({line(mom)}) is clearly negative in P1 (IR {I(pm[0])}) and close to zero in P2 ({I(pm[1])}) and P3 ({I(pm[2])}). Coffee is the only product with a positive full-sample IR ({I(mp['Coffee'])}); Sugar ({I(mp['Sugar'])}), Cocoa ({I(mp['Cocoa'])}) and Cotton ({I(mp['Cotton'])}), the weakest, are negative."))
    B(("b", f"Carry ({line(car)}) and Carry-Momentum ({line(cm)}) are negative in P1 (Carry {I(pc[0])}, Carry-Momentum {I(pcm[0])}), positive in P2 ({I(pc[1])} / {I(pcm[1])}) and negative in P3 ({I(pc[2])} / {I(pcm[2])}). "
            f"Coffee is the swing: its Carry IR is {I(cof_c[0])} in P1 and {I(cof_c[1])} in P2 and {I(cof_c[2])} in P3, and its Carry-Momentum IR is {I(cof_cm[1])} in P2, when the July 2021 Brazilian frosts lifted arabica by 34% in a week in our series (19 to 26 July) to its highest front-month price since October 2014 (Reuters, Bloomberg), and {I(cof_cm[2])} in P3, "
            f"after the price reached its high of $4.39/lb in our series on 13 February 2025 (our series is the front-month, March, contract; the most active contract set its record at about $4.30 that month) and fell back to ${cof_end:.2f}/lb by 30 September 2026 in our series. Without Coffee, both sleeves are negative in P2. "
            f"Cotton is the weakest product in both sleeves (Carry {I(cp['Cotton'])}, Carry-Momentum {I(cmp_['Cotton'])}) and is negative in every period."))
    B(("b", f"Value ({line(val)}) is the one positive sleeve: IR {I(pv[0])} in P1, {I(pv[1])} in P2 and {I(pv[2])} in P3. By product it is positive in Cotton ({I(vp['Cotton'])}) and Cocoa ({I(vp['Cocoa'])}), flat in Coffee ({I(vp['Coffee'])}) and negative in Sugar ({I(vp['Sugar'])}). Cocoa earns {I(cov[0])} in P1 and {I(cov[1])} in P2 and loses in P3 ({I(cov[2])}); Cotton earns {I(cotv[2])} in P3 and Coffee {I(cofv[0])} in P1. "
            f"The P3 loss comes from 2024 and the cocoa rally: the front-month price in our series reached ${coc_hi:,.0f}/MT on 18 December 2024, Value is short a market that trades more than 10% above its five-year average, and the sleeve loses {abs(vy.loc[2024]):.2f} in log return in 2024 (Cocoa {N(cvy.loc[2024])}), its worst year; it recovers in 2025 and 2026 as Cocoa falls back to ${coc_end:,.0f}/MT by 30 September 2026 (Cocoa {N(cvy.loc[2025])} in 2025 and {N(cvy.loc[2026])} in 2026). "
            f"Value is measured on the F2 contract, as in Precious Metals and Agriculture."))
    B(("b", f"Skewness ({line(sk)}) is the only sleeve that is negative in every period (IR {I(ps[0])} in P1, {I(ps[1])} in P2, {I(ps[2])} in P3) and it is negative in all four products, worst in Coffee ({I(skp['Coffee'])}) and Cocoa ({I(skp['Cocoa'])}), near zero in Sugar ({I(skp['Sugar'])}) and Cotton ({I(skp['Cotton'])}). "
            f"In Cocoa it earns {N(csy.loc[2024])} in log return in 2024, as the price rose, then loses {abs(csy.loc[2025]):.2f} in 2025 and {abs(csy.loc[2026]):.2f} in 2026 as it fell back; its short leg loses {abs(lg['Cocoa']['full']['short_pnl']):.2f} over the sample, {abs(lg['Cocoa']['p3']['short_pnl']):.2f} of it in P3. "
            f"In Coffee, where the 2021 frost and the 2025 record were followed by sharp reversals, the signal loses on both legs (long leg {N(lg['Coffee']['full']['long_pnl'])}, short leg {N(lg['Coffee']['full']['short_pnl'])}; {N(cfy.loc[2021])} in 2021 and {N(cfy.loc[2024])} in 2024). "
            f"In Sugar the sleeve is short on {100 - lg['Sugar']['full']['long_pct']:.0f}% of days: the short leg earns {N(lg['Sugar']['full']['short_pnl'])} and the long leg loses {abs(lg['Sugar']['full']['long_pnl']):.2f}. "
            f"It correlates at {N(wsk['Momentum'])} with Momentum, {N(wsk['Carry'])} with Carry, {N(wsk['CarryMom'])} with Carry-Momentum and {N(wsk['Value'])} with Value."))
    B(("b", f"Portfolio construction: Equal Weight is negative in P1 ({I(ewD[0])}), marginally positive in P2 ({I(ewD[1])}) and clearly negative in P3 ({I(ewD[2])}); Inverse Vol is {I(ivD[0])}, {I(ivD[1])} and {I(ivD[2])}. "
            f"Skewness lowers the result here, as it does in Metals and in no other bucket: the Equal Weight IR is {I(ew4['ir'])} without it and {I(ew['ir'])} with it (Inverse Vol {I(iv4['ir'])} and {I(iv['ir'])}), P2 falls from {I(ew4D[1])} to {I(ewD[1])} and P3 from {I(ew4D[2])} to {I(ewD[2])}."))
    B(("b", f"Individual-product decomposition: Coffee is the only product with a positive IR in Momentum ({I(cofe['Momentum'])}), Carry ({I(cofe['Carry'])}) and Carry-Momentum ({I(cofe['CarryMom'])}), and all three are small. The best single core product-sleeve result is {best[0]} {names[best[1]]} (IR {I(core[best])}) and the three weakest are Cotton Carry-Momentum ({I(core[('Cotton', 'CarryMom')])}), Cotton Carry ({I(core[('Cotton', 'Carry')])}) and Cotton Momentum ({I(core[('Cotton', 'Momentum')])}); "
            f"Sugar is within {max(abs(x) for x in sg.values()):.2f} of zero in all five sleeves."))
    B(("fig", "fig_softs_combined.png", "Figure ?. Softs: Combined Strategy Performance (Cumulative Return, 2012-2026)"))
    return blocks


if __name__ == "__main__":
    for b in softs():
        print(b[0], b[1] if b[0] != "fig" else b[1:])
        print()


def _n(x, d=2):
    return f"{x:.{d}f}".replace("-", "−")


def softs_narr():
    """The narrative paragraph under the Softs heading (same layout as the Agriculture one). Every claim asserted against the data."""
    v, a = "softs", "softs"
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol"); ewD, ivD = per(v, "EW PORT"), per(v, "Inverse Vol")
    chk(val["ir"] > 0 and all(st(v, k)["ir"] < 0 for k in ("Momentum", "Carry", "CarryMom", "Skewness")), "softs narrative: Value the only positive sleeve")
    chk(pc[1] > 0 and pcm[1] > 0.3 and pc[2] < -0.3 and pcm[2] < -0.6 and pv[0] > 0.5 and pv[2] < 0 and all(x < 0 for x in ps), "softs narrative: curve signals positive in P2 and negative in P3; Value positive in P1 and negative in P3; Skewness negative in every subperiod")
    cof_cm = pper(a, "Coffee", "CarryMom")
    chk(cof_cm[1] > 0.8 and cof_cm[2] < -0.6, "softs narrative: Coffee swing")
    _a = importlib.import_module("agri"); cc = _a.load_curve("Cocoa")["F1"]
    chk(cc.idxmax() == pd.Timestamp("2024-12-18") and round(cc.max()) == 12565, "softs narrative: Cocoa high")
    vy = yearly_log(CS[v]["Value"]); chk(vy.idxmin() == 2024, "softs narrative: Value worst year 2024")
    chk(ewD[0] < 0 < ewD[1] and ewD[2] < -0.7 and ivD[2] < -0.7 and ivD[0] < 0 < ivD[1], "softs narrative: portfolios negative in P1 and P3, positive in P2")
    return (f"Softs (Sugar, Cocoa, Coffee and Cotton) has one positive sleeve, Value (IR {_n(val['ir'])}), while Momentum ({_n(mom['ir'])}), Carry ({_n(car['ir'])}), Carry-Momentum ({_n(cm['ir'])}) and Skewness ({_n(sk['ir'])}) are negative over the full sample. "
            f"Carry and Carry-Momentum are positive only in P2 ({_n(pc[1])} and {_n(pcm[1])}) and fall to {_n(pc[2])} and {_n(pcm[2])} in P3. Coffee illustrates the mechanism: Carry-Momentum earns an IR of {_n(cof_cm[1])} in P2, when the Brazilian frosts of July 2021 drove prices higher, and {_n(cof_cm[2])} in P3, after the record price of February 2025 and the decline that followed. "
            f"Value earns {_n(pv[0])} in P1 and {_n(pv[1])} in P2 but {_n(pv[2])} in P3, where the loss comes from 2024 (the sleeve returns {_n(vy.loc[2024])} in log return that year), when the front-month price of Cocoa in our series reached ${cc.max():,.0f} per tonne on 18 December 2024. "
            f"Skewness is negative in every subperiod (P1 {_n(ps[0])}, P2 {_n(ps[1])}, P3 {_n(ps[2])}) and lowers the portfolio result. As a consequence, the Equal Weight (return {_n(ew['ret'], 1)}%, volatility {_n(ew['vol'], 1)}%, maximum drawdown {_n(ew['mdd'], 1)}%, IR {_n(ew['ir'])}) and Inverse Vol (return {_n(iv['ret'], 1)}%, volatility {_n(iv['vol'], 1)}%, maximum drawdown {_n(iv['mdd'], 1)}%, IR {_n(iv['ir'])}) portfolios are negative, "
            f"marginally positive only in P2 ({_n(ewD[1])} and {_n(ivD[1])}), with P3 the main drag ({_n(ewD[2])} and {_n(ivD[2])}).")
