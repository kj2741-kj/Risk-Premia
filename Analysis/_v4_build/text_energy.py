from facts2 import *


def energy():
    v, vx, a = "energy", "energy_exng", "energy"
    pr = VARIANTS[v][1]
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol")
    ew4, iv4 = st4(v, "EW PORT"), st4(v, "Inverse Vol")
    ewx, ivx = st(vx, "EW PORT"), st(vx, "Inverse Vol")
    ewD, ivD = per(v, "EW PORT"), per(v, "Inverse Vol")
    cw = corr_within(v)
    chk(all(x > 0 for x in pm + pc + pcm), "energy Momentum/Carry/CarryMom positive in every period")
    chk(cm["ir"] > mom["ir"] > car["ir"] > 0 > val["ir"], "energy CarryMom strongest, Value only negative of core")
    chk(pc[2] < 0.05 and pc[2] < min(pc[0], pc[1]), "energy Carry weakest in P3")
    cpp = {p: pst(a, p, "Carry", "p3")["ir"] for p in pr}
    chk(cpp["WTI"] < 0 and cpp["Brent"] < 0 and cpp["HeatingOil"] > 0.8, "energy Carry P3 by product")
    chk(pv[0] < 0 and pv[2] < 0 and pv[1] > 0, "energy Value period pattern")
    # Momentum concentration
    mseries = CS[v]["Momentum"].loc["2012-01-01":].dropna()
    tot = mseries.sum(); yl = yearly_log(mseries)
    share4 = yl.loc[[2014, 2015, 2020, 2021]].sum() / tot * 100
    share22 = yl.loc[2022] / tot * 100
    share26 = mseries.loc["2026-01-01":].sum() / tot * 100
    chk(round(share4) == 95 and round(share22) == 14 and round(share26) == 23, f"energy Momentum concentration {share4:.1f} {share22:.1f} {share26:.1f}")
    # ex-NatGas improvements
    sx = {k: st(vx, k) for k in SLEEVES}
    chk(all(sx[k]["ir"] > st(v, k)["ir"] for k in SLEEVES), "energy ex-NatGas improves every sleeve")
    chk(ewx["ir"] > ew["ir"] and ivx["ir"] > iv["ir"], "energy ex-NatGas portfolios improve")
    # product decomposition
    mp = {p: pst(a, p, "Momentum")["ir"] for p in pr}; cmp_ = {p: pst(a, p, "CarryMom")["ir"] for p in pr}
    four = [p for p in pr if p != "NatGas"]
    lo = min(min(mp[p], cmp_[p]) for p in four); hi = max(max(mp[p], cmp_[p]) for p in four)
    chk(abs(mp["NatGas"]) < 0.05 and abs(cmp_["NatGas"]) < 0.05, "energy NatGas no edge in Momentum/CarryMom")
    vp = {p: pst(a, p, "Value")["ir"] for p in pr}
    chk(sum(1 for p in pr if vp[p] < 0) == 4 and abs(vp["Brent"]) < 0.05, "energy Value negative in four of five, flat Brent")
    neg = [vp[p] for p in pr if vp[p] < 0]
    # Skewness
    skp = {p: pst(a, p, "Skewness")["ir"] for p in pr}
    chk(all(skp[p] > 0.2 for p in four) and skp["NatGas"] < -0.3, "energy Skewness by product")
    lg = {p: legs(a, p) for p in pr}
    lpct3 = {p: lg[p]["p3"]["long_pct"] for p in pr}
    chk(min(lpct3[p] for p in ("WTI", "Brent", "RBOB")) >= 98 and lpct3["HeatingOil"] > 85, "energy Skewness long almost all of P3")
    chk(lg["WTI"]["p1"]["long_pnl"] < -0.5 and lg["Brent"]["p1"]["long_pnl"] < -0.3, "energy Skewness P1 long legs lose")
    skx = CS[vx]["Skewness"].loc["2012-01-01":].dropna(); ylx = yearly_log(skx); totx = skx.sum()
    yrs = ylx.loc[[2020, 2021, 2022, 2026]]
    shx = yrs.sum() / totx * 100
    chk(all(yrs > 0.4), "energy ex-NatGas Skewness big years")
    wti_p3 = pst(a, "WTI", "Skewness", "p3")["ir"]; rb_p3 = pst(a, "RBOB", "Skewness", "p3")["ir"]
    natgas_path = (np.exp(nets()[(a, "NatGas")]["Skewness"].loc["2012-01-01":].dropna().sum()) - 1) * 100
    chk(natgas_path < -90, "energy NatGas Skewness path")
    wti_crash, wti_flip = skew_episode(a, "WTI", "2020-03-01", "2020-04-30")
    wti_after, _ = skew_episode(a, "WTI", "2020-05-01", "2021-12-31")
    import datetime as _dt
    chk(wti_flip == _dt.date(2020, 3, 11) and wti_crash < -0.4 and wti_after > 1.0, "energy Skewness 2020 episode")
    wti_flip = _dt.datetime(2020, 3, 11)
    chk(all(x > 0 for x in ewD + ivD), "energy portfolios positive in every period")
    B = []
    blocks = [("h2", "Energy")]; B = blocks.append
    B(("b", f"Carry-Momentum ({line(cm)}) is the strongest individual strategy in the Energy basket and, like Momentum and Carry, is positive in every period (Carry-Momentum P1 {I(pcm[0])}, P2 {I(pcm[1])}, P3 {I(pcm[2])}), "
            f"the clearest evidence in Energy that term-structure changes carry genuine, repeatable information."))
    B(("b", f"Momentum ({line(mom)}): positive in every period (P1 {I(pm[0])}, P2 {I(pm[1])}, P3 {I(pm[2])}), with most of its return earned in a few large directional moves: calendar years 2014, 2015, 2020 and 2021 account for {share4:.0f}% of its cumulative log return. "
            f"They coincide with the 2014-2016 price collapse (WTI fell from $107 on 20 June 2014 to $26 on 11 February 2016 in our series, after OPEC's 27 November 2014 decision to hold output against rising US shale supply), the 2020 demand collapse and the 2021 recovery. "
            f"P3 is its weakest period even though it contains the March 2022 spike to $124 after Russia's invasion of Ukraine (calendar 2022 adds a further {share22:.0f}% of the total). "
            f"The war between the United States, Israel and Iran that began on 28 February 2026 then disrupted Gulf supply on a scale the IEA calls the largest in the history of the oil market, and Brent futures went from $72 on 27 February to $118 on 31 March; "
            f"the first nine months of 2026 alone are {share26:.0f}% of the sleeve's cumulative log return."))
    B(("b", f"Carry ({line(car)}) is positive in every period (P1 {I(pc[0])}, P2 {I(pc[1])}, P3 {I(pc[2])}) and weakest in P3 (IR {I(pc[2])}), where crude oil is the problem (WTI {I(cpp['WTI'])}, Brent {I(cpp['Brent'])}, against Heating Oil {I(cpp['HeatingOil'])}) "
            f"although the curves were the most backwardated of the sample (WTI F1-F3 backwardated on 87% of days in P3 against 24% in P1 and 46% in P2). The V2 signal is measured against each curve's own trailing 252-day slope, so a high level of backwardation does not by itself produce Carry returns."))
    B(("b", f"Value ({line(val)}) is the one consistent drag among the four core strategies on a full-sample basis, negative in P1 (IR {I(pv[0])}) and P3 ({I(pv[2])}) and marginally positive in P2 ({I(pv[1])}). "
            f"The 2014-2016 price collapse (WTI from $107 to $26), triggered by US shale supply growth and OPEC's decision to hold output, behaves as a persistent trend rather than a mean-reverting cycle, exactly the environment a reversion strategy is built to lose in. "
            f"It correlates at {N(cw.loc['Value', 'Momentum'])} with Momentum and {N(cw.loc['Value', 'Carry'])} with Carry, the same diversification relationship seen in Metals (-0.50 with Momentum)."))
    B(("b", f"Skewness ({line(sk)}): negative in P1 (IR {I(ps[0])}) and positive in P2 ({I(ps[1])}) and P3 ({I(ps[2])}); excluding Natural Gas it is {I(sx['Skewness']['ir'])} (Return {R(sx['Skewness']['ret'])}). It works in the four oil products (WTI {I(skp['WTI'])}, Brent {I(skp['Brent'])}, RBOB {I(skp['RBOB'])}, Heating Oil {I(skp['HeatingOil'])}) and fails in Natural Gas ({I(skp['NatGas'])}). "
            f"Its P2 and P3 results are largely one long position. The signal turned long on {wti_flip.day} {wti_flip.strftime('%B %Y')} in the middle of the 2020 collapse (WTI settled at -$37.63 on 20 April): the sleeve lost {abs(wti_crash):.2f} in log return in WTI over March and April, then earned {N(wti_after)} from May 2020 to December 2021 as prices recovered. "
            f"The trailing-year skewness of oil returns then stayed negative for years, so the sleeve was long on {U(lpct3['WTI'],0)}% of P3 days in WTI, {U(lpct3['Brent'],0)}% in Brent and {U(lpct3['RBOB'],0)}% in RBOB, and earned the 2022 spike and the 2026 war rally (P3 IR {I(wti_p3)} in WTI, {I(rb_p3)} in RBOB). "
            f"In P1 it was long on {U(lpct3['WTI'] * 0 + lg['WTI']['p1']['long_pct'],0)}% of WTI days and lost on those days ({N(lg['WTI']['p1']['long_pnl'])} in log return) as oil fell. For the ex-NatGas sleeve, calendar years 2020, 2021, 2022 and 2026 add {yrs.sum():.2f} of log return against a full-sample total of {totx:.2f}, so the other eleven years net {totx - yrs.sum():.2f}. "
            f"In Natural Gas the long leg loses {abs(lg['NatGas']['full']['long_pnl']):.2f} in log return over the sample and the sleeve ends {abs(natgas_path):.0f}% below its start. It correlates at {N(cw.loc['Skewness', 'Momentum'])} with Momentum, {N(cw.loc['Skewness', 'Carry'])} with Carry, {N(cw.loc['Skewness', 'CarryMom'])} with Carry-Momentum and {N(cw.loc['Skewness', 'Value'])} with Value."))
    B(("b", f"Portfolio construction: Equal Weight ({line(ew)}) and Inverse Vol ({line(iv)}) are almost identical and both positive in every period (Equal Weight P1 {I(ewD[0])}, P2 {I(ewD[1])}, P3 {I(ewD[2])}; Inverse Vol P1 {I(ivD[0])}, P2 {I(ivD[1])}, P3 {I(ivD[2])}). "
            f"Unlike Metals, where Inverse Vol lifts the portfolio, the choice of weighting makes no material difference in Energy. Adding Skewness as a fifth sleeve lifts the IR (Equal Weight {I(ew4['ir'])} to {I(ew['ir'])}, Inverse Vol {I(iv4['ir'])} to {I(iv['ir'])}) and lowers volatility (Equal Weight {V(ew4['vol'])} to {V(ew['vol'])}, Inverse Vol {V(iv4['vol'])} to {V(iv['vol'])}), mostly through P2 and P3."))
    B(("b", f"Excluding Natural Gas (Energy ex-NatGas) improves every sleeve: Momentum {I(mom['ir'])} to {I(sx['Momentum']['ir'])}, Carry {I(car['ir'])} to {I(sx['Carry']['ir'])}, Carry-Momentum {I(cm['ir'])} to {I(sx['CarryMom']['ir'])}, Value {I(val['ir'])} to {I(sx['Value']['ir'])}, Skewness {I(sk['ir'])} to {I(sx['Skewness']['ir'])} (IR). "
            f"Equal Weight ({line(ewx)}) and Inverse Vol ({line(ivx)}) rise accordingly (from IR {I(ew['ir'])} and {I(iv['ir'])} with Natural Gas)."))
    B(("b", f"Individual-product decomposition: Momentum and Carry-Momentum work across WTI, Brent, RBOB, and Heating Oil (IR {I(lo)} to {I(hi)}) but carry no edge in Natural Gas (IR {I(mp['NatGas'])} and {I(cmp_['NatGas'])}), consistent with gas's weather- and basis-driven price action decoupling from the broader term-structure logic: "
            f"the Natural Gas curve was in contango on 87%, 75% and 74% of days in the three periods, and Henry Hub averaged $2.77 in 2012, the lowest since 1999, on a mild winter, record storage and rising shale output (EIA). "
            f"Value is negative in four of the five products (IR {I(min(neg))} to {I(max(neg))}) and flat in Brent ({I(vp['Brent'])}), a broad, structural failure, not a concentration issue the way Momentum's weakness in Metals was."))
    B(("b", "Physical storage bottlenecks, pipeline capacity limits, and producers' structural need to hedge downside force the market to pay a continuous insurance premium to whoever takes the other side of that risk, "
            "the same economic logic that shows up as Carry-Momentum's clean, all-period positive record above. This is an interpretation consistent with the results, not a test of the hedging pressure hypothesis."))
    B(("fig", "fig_energy_combined.png", "Figure 2. Energy: Combined Strategy Performance (Cumulative Return, 2012-2026)"))
    return blocks


if __name__ == "__main__":
    for b in energy():
        print(b[0], b[1] if b[0] != "fig" else b[1:]); print()
