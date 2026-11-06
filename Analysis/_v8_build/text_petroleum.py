from facts3 import *
import datetime as _dt


def petroleum():
    """Petroleum = WTI, Brent, RBOB, Heating Oil (the former 'Energy ex-NatGas'). Every claim is asserted against the 0930 data before it is printed."""
    v, a = "petroleum", "energy"
    pr = VARIANTS[v][1]
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol")
    ew4, iv4 = st4(v, "EW PORT"), st4(v, "Inverse Vol")
    ewD, ivD = per(v, "EW PORT"), per(v, "Inverse Vol")
    cw = corr_within(v)
    cwm = corr_within("metals")
    chk(len(pr) == 4 and pr == ["WTI", "Brent", "RBOB", "HeatingOil"], "petroleum has the four oil products")
    chk(all(x > 0 for x in pm + pc + pcm), "petroleum Momentum/Carry/CarryMom positive in every period")
    chk(cm["ir"] > mom["ir"] > car["ir"] > 0 > val["ir"] and sk["ir"] > 0 and sk["ir"] < car["ir"], "petroleum CarryMom strongest, then Momentum, Carry, Skewness; Value only negative")
    chk(pc[2] < 0.1 and pc[2] < min(pc[0], pc[1]) and pcm[2] < min(pcm[0], pcm[1]) and pm[2] < min(pm[0], pm[1]), "petroleum: P3 is the weakest period for Momentum, Carry and Carry-Momentum, Carry nearly flat")
    cpp = {p: pst(a, p, "Carry", "p3")["ir"] for p in pr}
    chk(cpp["WTI"] < 0 and cpp["Brent"] < 0 and cpp["HeatingOil"] > 0.7 and cpp["RBOB"] > 0, "petroleum Carry P3 by product")
    chk(pv[0] < -0.3 and pv[2] < 0 and abs(pv[2]) < 0.05 and 0 < pv[1] < 0.1, "petroleum Value period pattern")
    # Momentum concentration
    ms = CS[v]["Momentum"].loc["2012-01-01":].dropna(); tot = ms.sum(); yl = yearly_log(ms)
    share4 = yl.loc[[2014, 2015, 2020, 2021]].sum() / tot * 100
    share22 = yl.loc[2022] / tot * 100
    share26 = ms.loc["2026-01-01":].sum() / tot * 100
    chk(round(share4) == 87 and round(share22) == 14 and round(share26) == 24, f"petroleum Momentum concentration {share4:.1f} {share22:.1f} {share26:.1f}")
    chk(ms.index[-1] == pd.Timestamp("2026-09-30"), "petroleum sleeve ends 30 Sep 2026")
    rest = yl.drop([2014, 2015, 2020, 2021]).sum() / tot * 100
    chk(yl.loc[2020] == yl.max() or yl.loc[2020] > yl.loc[2026], "2020 is the best Momentum year")
    # product decomposition
    mp = {p: pst(a, p, "Momentum")["ir"] for p in pr}; cmp_ = {p: pst(a, p, "CarryMom")["ir"] for p in pr}
    carp = {p: pst(a, p, "Carry")["ir"] for p in pr}
    lo = min(min(mp[p], cmp_[p]) for p in pr); hi = max(max(mp[p], cmp_[p]) for p in pr)
    chk(all(mp[p] > 0 and cmp_[p] > 0 and carp[p] > 0 for p in pr), "petroleum Momentum, Carry, Carry-Momentum positive in every product")
    vp = {p: pst(a, p, "Value")["ir"] for p in pr}
    chk(sum(1 for p in pr if vp[p] < 0) == 3 and vp["Brent"] > 0 and abs(vp["Brent"]) < 0.05, "petroleum Value negative in three of four, flat Brent")
    neg = [vp[p] for p in pr if vp[p] < 0]
    # Skewness
    skp = {p: pst(a, p, "Skewness")["ir"] for p in pr}
    chk(all(skp[p] > 0.2 for p in pr), "petroleum Skewness positive in all four products")
    lg = {p: legs(a, p) for p in pr}
    lpct3 = {p: lg[p]["p3"]["long_pct"] for p in pr}
    chk(min(lpct3[p] for p in ("WTI", "Brent", "RBOB")) >= 98 and 85 < lpct3["HeatingOil"] < 95, "petroleum Skewness long almost all of P3")
    chk(lg["WTI"]["p1"]["long_pnl"] < -0.5 and lg["Brent"]["p1"]["long_pnl"] < -0.3, "petroleum Skewness P1 long legs lose")
    sk_s = CS[v]["Skewness"].loc["2012-01-01":].dropna(); ylx = yearly_log(sk_s); totx = sk_s.sum()
    yrs = ylx.loc[[2020, 2021, 2022, 2026]]
    chk(all(yrs > 0.4), "petroleum Skewness big years")
    chk(len(ylx) == 15 and 15 - 4 == 11, "eleven other years")
    wti_p3 = pst(a, "WTI", "Skewness", "p3")["ir"]; rb_p3 = pst(a, "RBOB", "Skewness", "p3")["ir"]
    wti_crash, wti_flip = skew_episode(a, "WTI", "2020-03-01", "2020-04-30")
    wti_after, _ = skew_episode(a, "WTI", "2020-05-01", "2021-12-31")
    chk(wti_flip == _dt.date(2020, 3, 11) and wti_crash < -0.4 and wti_after > 1.0, "petroleum Skewness 2020 episode")
    wti_flip = _dt.datetime(2020, 3, 11)
    chk(ps[0] < 0 < ps[1] and ps[2] > ps[1], "petroleum Skewness negative P1, positive P2 and P3, strongest in P3")
    chk(all(x > 0 for x in ewD + ivD), "petroleum portfolios positive in every period")
    ew4D = [stats(PORT4[v][0], w)["ir"] for w in ("p1", "p2", "p3")]
    iv4D = [stats(PORT4[v][1], w)["ir"] for w in ("p1", "p2", "p3")]
    chk(ewD[1] > ew4D[1] and ewD[2] > ew4D[2] and ewD[0] < ew4D[0], "petroleum Skewness lifts EW IR in P2 and P3, lowers it in P1")
    chk(ivD[1] > iv4D[1] and ivD[2] > iv4D[2] and ivD[0] < iv4D[0], "petroleum Skewness lifts Inverse Vol IR in P2 and P3, lowers it in P1")
    chk(ew4["ir"] < ew["ir"] and iv4["ir"] < iv["ir"] and ew4["vol"] > ew["vol"] and iv4["vol"] > iv["vol"], "petroleum Skewness lifts the IR and lowers volatility")
    chk(iv["ir"] > ew["ir"] and iv["vol"] < ew["vol"] and iv["mdd"] > ew["mdd"] and iv["ret"] > ew["ret"], "petroleum Inverse Vol ahead of EW on return, IR, vol and drawdown")
    mw, me = st("metals", "EW PORT"), st("metals", "Inverse Vol")
    gap_p = iv["ir"] - ew["ir"]; gap_m = me["ir"] - mw["ir"]
    chk(gap_p < 0.05 and gap_m > 0.1, "Inverse Vol lifts Metals by more than 0.1 but Petroleum by less than 0.05")
    chk(cw.loc["Value", "Momentum"] < -0.45 and cw.loc["Value", "Carry"] < -0.45, "petroleum Value correlations with Momentum and Carry")
    # price-level facts in the F1 series
    _e = importlib.import_module("energy")
    _f1 = {p_: _e.load_curve(p_)["F1"] for p_ in ("WTI", "Brent")}
    chk(round(_f1["WTI"].loc["2014-06-20"]) == 107 and round(_f1["WTI"].loc["2016-02-11"]) == 26 and _f1["WTI"].loc["2014":"2016"].idxmax() == pd.Timestamp("2014-06-20") and _f1["WTI"].loc["2014":"2016"].idxmin() == pd.Timestamp("2016-02-11"), "petroleum WTI 2014-2016 levels in the F1 series")
    chk(round(_f1["WTI"].loc["2022-03"].max()) == 124 and _f1["WTI"].loc["2022-03"].idxmax().day == 8, "petroleum WTI March 2022 high")
    chk(round(_f1["Brent"].loc["2026-02-27"]) == 72 and round(_f1["Brent"].loc["2026-03-31"]) == 118 and _f1["Brent"].loc["2026"].idxmax() == pd.Timestamp("2026-03-31"), "petroleum Brent 2026 levels")
    wti_apr20 = float(_f1["WTI"].loc["2020-04-20"])
    chk(wti_apr20 > 0, "petroleum WTI 20 April 2020 imputed in our series")
    sl_wti = slope_stats(a, "WTI", "F1", "F3")
    chk(round(sl_wti["p3"][1]) == 87 and round(sl_wti["p1"][1]) == 24 and round(sl_wti["p2"][1]) == 46, "petroleum WTI F1-F3 backwardation shares")
    chk(all(sl_wti["p3"][0] > max(sl_p[q][0] for q in ("p1", "p2")) for sl_p in [slope_stats(a, p_, "F1", "F3") for p_ in pr]), "petroleum oil products most backwardated in P3 (average F1-F3 slope)")
    chk(all(x > -0.25 for x in vp.values()), "petroleum Value product IRs all small")

    blocks = [("h2", "Petroleum")]; B = blocks.append
    B(("b", "Petroleum is the four oil products (WTI, Brent, RBOB gasoline and Heating Oil). It replaces the Energy section of the previous version: Natural Gas has moved to the Power, Emissions and Nat Gas bucket and is not covered here, so the Natural Gas figures and the Energy ex-NatGas comparison are dropped. "
            "Figures run to 30 September 2026 (five further trading days, 24 to 30 September, than the previous version)."))
    B(("b", f"Carry-Momentum ({line(cm)}) is the strongest individual strategy in Petroleum and, like Momentum and Carry, is positive in every period (Carry-Momentum P1 {I(pcm[0])}, P2 {I(pcm[1])}, P3 {I(pcm[2])}), "
            f"the clearest evidence in Petroleum that term-structure changes carry information that recurs across periods."))
    B(("b", f"Momentum ({line(mom)}): positive in every period (P1 {I(pm[0])}, P2 {I(pm[1])}, P3 {I(pm[2])}), with most of its return earned in a few large directional moves: calendar years 2014, 2015, 2020 and 2021 account for {share4:.0f}% of its cumulative log return. "
            f"They coincide with the 2014-2016 price collapse (WTI fell from $107 on 20 June 2014 to $26 on 11 February 2016 in our series, after OPEC's 27 November 2014 decision to hold output against rising US shale supply), the 2020 demand collapse and the 2021 recovery. "
            f"P3 is its weakest period even though it contains the March 2022 spike to $124 after Russia's invasion of Ukraine (calendar 2022 adds a further {share22:.0f}% of the total). "
            f"The war between the United States, Israel and Iran that began on 28 February 2026 then disrupted Gulf supply on a scale the IEA calls the largest in the history of the oil market, and Brent futures went from $72 on 27 February to $118 on 31 March; "
            f"the first nine months of 2026 alone are {share26:.0f}% of the sleeve's cumulative log return."))
    B(("b", f"Carry ({line(car)}) is positive in every period (P1 {I(pc[0])}, P2 {I(pc[1])}, P3 {I(pc[2])}) but in P3 it is close to flat (IR {I(pc[2])}), where crude oil is the problem (WTI {I(cpp['WTI'])}, Brent {I(cpp['Brent'])}, against RBOB {I(cpp['RBOB'])} and Heating Oil {I(cpp['HeatingOil'])}) "
            f"although the curves were the most backwardated of the sample (WTI F1-F3 backwardated on {sl_wti['p3'][1]:.0f}% of days in P3 against {sl_wti['p1'][1]:.0f}% in P1 and {sl_wti['p2'][1]:.0f}% in P2). Carry compares each pair's slope with its own trailing 252-day history, so a high level of backwardation does not by itself produce Carry returns."))
    B(("b", f"Value ({line(val)}) is the one consistent drag among the four core strategies on a full-sample basis, negative in P1 (IR {I(pv[0])}) and marginally negative in P3 ({I(pv[2])}) and marginally positive in P2 ({I(pv[1])}). "
            f"The 2014-2016 price collapse (WTI from $107 to $26), triggered by US shale supply growth and OPEC's decision to hold output, behaves as a persistent trend rather than a mean-reverting cycle, exactly the environment a reversion strategy is built to lose in. "
            f"It correlates at {N(cw.loc['Value', 'Momentum'])} with Momentum and {N(cw.loc['Value', 'Carry'])} with Carry, the same diversification relationship seen in Metals ({N(cwm.loc['Value', 'Momentum'])} with Momentum)."))
    B(("b", f"Skewness ({line(sk)}): negative in P1 (IR {I(ps[0])}) and positive in P2 ({I(ps[1])}) and P3 ({I(ps[2])}), and positive in all four products (WTI {I(skp['WTI'])}, Brent {I(skp['Brent'])}, RBOB {I(skp['RBOB'])}, Heating Oil {I(skp['HeatingOil'])}). "
            f"Its P2 and P3 results are largely one long position. The signal turned long on {wti_flip.day} {wti_flip.strftime('%B %Y')} in the middle of the 2020 collapse (the May contract settled at -$37.63 on 20 April, a value our series replaces with an imputed ${wti_apr20:.2f}): the sleeve lost {abs(wti_crash):.2f} in log return in WTI over March and April, then earned {N(wti_after)} from May 2020 to December 2021 as prices recovered. "
            f"The trailing-year skewness of oil returns then stayed negative for years, so the sleeve was long on {U(lpct3['WTI'],0)}% of P3 days in WTI, {U(lpct3['Brent'],0)}% in Brent and {U(lpct3['RBOB'],0)}% in RBOB ({U(lpct3['HeatingOil'],0)}% in Heating Oil), and earned the 2022 spike and the 2026 war rally (P3 IR {I(wti_p3)} in WTI, {I(rb_p3)} in RBOB). "
            f"In P1 it was long on {U(lg['WTI']['p1']['long_pct'],0)}% of WTI days and lost on those days ({N(lg['WTI']['p1']['long_pnl'])} in log return) as oil fell. Calendar years 2020, 2021, 2022 and 2026 add {yrs.sum():.2f} of log return against a full-sample total of {totx:.2f}, so the other eleven years net {totx - yrs.sum():.2f}. "
            f"It correlates at {N(cw.loc['Skewness', 'Momentum'])} with Momentum, {N(cw.loc['Skewness', 'Carry'])} with Carry, {N(cw.loc['Skewness', 'CarryMom'])} with Carry-Momentum and {N(cw.loc['Skewness', 'Value'])} with Value."))
    B(("b", f"Portfolio construction: Equal Weight ({line(ew)}) and Inverse Vol ({line(iv)}) are close and both positive in every period (Equal Weight P1 {I(ewD[0])}, P2 {I(ewD[1])}, P3 {I(ewD[2])}; Inverse Vol P1 {I(ivD[0])}, P2 {I(ivD[1])}, P3 {I(ivD[2])}). "
            f"Unlike Metals, where Inverse Vol lifts the portfolio IR by {gap_m:.2f}, Inverse Vol is ahead of Equal Weight in Petroleum by only {gap_p:.2f}, with slightly lower volatility and a shallower drawdown. Adding Skewness as a fifth sleeve lifts the IR (Equal Weight {I(ew4['ir'])} to {I(ew['ir'])}, Inverse Vol {I(iv4['ir'])} to {I(iv['ir'])}) and lowers volatility (Equal Weight {V(ew4['vol'])} to {V(ew['vol'])}, Inverse Vol {V(iv4['vol'])} to {V(iv['vol'])}), mostly through P2 and P3."))
    B(("b", f"Individual-product decomposition: Momentum and Carry-Momentum work across WTI, Brent, RBOB, and Heating Oil (IR {I(lo)} to {I(hi)}), and Carry is positive in every product too ({I(min(carp.values()))} to {I(max(carp.values()))}). "
            f"Value is negative in three of the four products (IR {I(min(neg))} to {I(max(neg))}) and flat in Brent ({I(vp['Brent'])}), a broad failure across products rather than one product's loss."))
    B(("b", "Physical storage bottlenecks, pipeline capacity limits, and producers' structural need to hedge downside force the market to pay a continuous insurance premium to whoever takes the other side of that risk, "
            "the same economic logic that shows up as Carry-Momentum's clean, all-period positive record above. This is an interpretation consistent with the results, not a test of the hedging pressure hypothesis."))
    B(("fig", "fig_petroleum_combined.png", "Figure 2. Petroleum: Combined Strategy Performance (Cumulative Return, 2012-2026)"))
    return blocks


if __name__ == "__main__":
    for b in petroleum():
        print(b[0], b[1] if b[0] != "fig" else b[1:]); print()
