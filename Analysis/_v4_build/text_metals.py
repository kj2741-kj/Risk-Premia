from facts import *


def metals():
    v, a = "metals", "metals"
    pr = VARIANTS[v][1]
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol")
    ew4, iv4 = st4(v, "EW PORT"), st4(v, "Inverse Vol")
    p3 = {p: pst(a, p, "Momentum", "p3")["ir"] for p in pr}
    chk(p3["Lead"] < p3["Zinc"] < p3["Copper"] < 0 < p3["Aluminium"], "metals Momentum P3 product ordering")
    chk(pm[0] < 0 and pm[2] < 0 and abs(pm[1]) < 0.1, "metals Momentum P1/P3 negative, P2 flat")
    chk(pc[0] > 0 and pc[1] < 0 and pc[2] <= 0 and pcm[0] > 0 and pcm[1] < 0 and pcm[2] < 0, "metals Carry/CarryMom sign pattern")
    cp1 = {p: pst(a, p, "Carry", "p1")["ir"] for p in pr}
    chk(cp1["Aluminium"] > 0.8 and cp1["Zinc"] > 0.7 and cp1["Copper"] < 0.3 and cp1["Lead"] < 0.3, "metals Carry P1 concentration")
    chk(all(x > 0 for x in pv), "metals Value positive in every period")
    chk(corr_within(v).loc["Value", "Momentum"] < -0.45, "metals Value-Momentum corr")
    vp3 = {p: pst(a, p, "Value", "p3")["ir"] for p in pr}
    chk(vp3["Copper"] < vp3["Aluminium"] < vp3["Zinc"] < vp3["Lead"], "metals Value P3 ordering")
    amom = {p: pst(a, p, "Momentum")["ir"] for p in pr}
    chk(amom["Aluminium"] > 0 and all(amom[p] < 0 for p in ("Copper", "Zinc", "Lead")), "metals Momentum by metal")
    avir = {p: pst(a, p, "Value")["ir"] for p in pr}
    chk(all(x > 0 for x in avir.values()), "metals Value positive in every metal")
    avg_vol = np.mean([pst(a, p, "Value")["vol"] for p in pr])
    avg_ir = np.mean(list(avir.values()))
    sk_p = {p: pst(a, p, "Skewness")["ir"] for p in pr}
    sk_pp = {p: pper(a, p, "Skewness") for p in pr}
    chk(max(abs(x) for x in sk_p.values()) < 0.2, "metals Skewness product IRs small")
    lg = {p: legs(a, p)["full"] for p in pr}
    chk(abs(sk["ir"]) < 0.1 and ps[1] > 0 > ps[0] and ps[2] < 0, "metals Skewness pattern")
    cw = corr_within(v)
    ewD = [st(v, "EW PORT", w)["ir"] for w in ("p1", "p2", "p3")]
    chk(ew["ir"] < 0 and iv["ir"] < 0.1 and val["ir"] > ew["ir"] and val["ir"] > iv["ir"], "metals portfolios below Value")
    blocks = [("h2", "Metals")]
    B = blocks.append
    B(("b", f"Momentum ({line(mom)}): negative in P1 (IR {I(pm[0])}) and P3 ({I(pm[2])}) and roughly flat in P2 ({I(pm[1])}). "
            f"The P3 losses are in Lead ({I(p3['Lead'])}), Zinc ({I(p3['Zinc'])}) and Copper ({I(p3['Copper'])}), the metals that spiked in 2021-2022 and "
            f"then reversed sharply, which is the whipsaw a trend signal cannot avoid; only Aluminium made money in P3 ({I(p3['Aluminium'])})."))
    B(("b", f"Carry ({line(car)}) and Carry-Momentum ({line(cm)}): both earn their positive results in P1 (IR {I(pc[0])} / {I(pcm[0])}) and turn negative in "
            f"P2 ({I(pc[1])} / {I(pcm[1])}) and P3 ({I(pc[2])} / {I(pcm[2])}). The P1 Carry result is concentrated in Aluminium (IR {I(cp1['Aluminium'])}) and Zinc "
            f"({I(cp1['Zinc'])}), the two metals whose curves were in the steepest contango of the period (average F1-F13 slope of -4.3% and -2.3%, backwardated on only 1% and 3% of days), "
            f"the years of large LME stocks, aluminium financing deals and warehouse queues of more than two years (Reuters, LME; the LME's first queue report, May 2014, put the longest aluminium wait at 748 days). "
            f"Contango eased from P2 (Aluminium -2.6% and -2.3%, Zinc +1.2% and +1.2%)."))
    B(("b", f"Value ({line(val)}): the strongest strategy and the only one with a clear edge, positive in every period (P1 {I(pv[0])}, P2 {I(pv[1])}, P3 {I(pv[2])}). "
            f"It correlates at {N(cw.loc['Value', 'Momentum'])} with Momentum full-sample, the most negative pairing within the asset class and the strongest diversification relationship."))
    B(("b", f"The P3 Value result ({I(pv[2])}) comes from the metals that overshot their five-year averages and fell back: Lead ({I(vp3['Lead'])}), Zinc ({I(vp3['Zinc'])}) and Aluminium ({I(vp3['Aluminium'])}). "
            f"Aluminium peaked at $3,876 on 4 March 2022 in our series (settlement basis; the LME intraday record, about $4,073 on 7 March, followed fears for European smelters under the energy crisis and for Russian supply) "
            f"and was down to $2,076 by December 2023, and Zinc fell from $4,523 in April 2022 to $2,240 in May 2023. Copper ({I(vp3['Copper'])}) is the exception because it kept rising to $14,851 on 22 September 2026, "
            f"the high of our series (the LME three-month record reported by market sources is about $14,875 on 10 September), which market reports tie to US tariff turmoil, tight concentrate supply and electrification and data-centre demand."))
    B(("b", f"Skewness ({line(sk)}): no stable edge, negative in P1 (IR {I(ps[0])}) and P3 ({I(ps[2])}) and positive in P2 ({I(ps[1])}). No metal carries a lasting signal: full-sample IRs are Copper {I(sk_p['Copper'])}, "
            f"Aluminium {I(sk_p['Aluminium'])}, Lead {I(sk_p['Lead'])} and Zinc {I(sk_p['Zinc'])}, and the sign of each metal reverses between periods (Aluminium {I(sk_pp['Aluminium'][0])}, {I(sk_pp['Aluminium'][1])}, {I(sk_pp['Aluminium'][2])}; "
            f"Zinc {I(sk_pp['Zinc'][0])}, {I(sk_pp['Zinc'][1])}, {I(sk_pp['Zinc'][2])}). The sleeve is long about half the time (Copper {U(lg['Copper']['long_pct'],0)}% of days, Zinc {U(lg['Zinc']['long_pct'],0)}%) and its short legs lose "
            f"(Copper {N(lg['Copper']['short_pnl'])}, Zinc {N(lg['Zinc']['short_pnl'])} in log return). It correlates at {N(cw.loc['Skewness', 'Value'])} with Value and {N(cw.loc['Skewness', 'Momentum'])} with Momentum."))
    B(("b", f"Portfolio construction: Equal Weight ({line(ew)}) and Inverse Vol ({line(iv)}) both underperform holding Value alone ({line(val)}) on IR. Inverse Vol has the shallower drawdown and lower volatility of the two, but neither approaches Value's IR. "
            f"Adding Skewness as a fifth sleeve lowers volatility (Equal Weight {V(ew4['vol'])} to {V(ew['vol'])}, Inverse Vol {V(iv4['vol'])} to {V(iv['vol'])}) but not the IR (Equal Weight {I(ew4['ir'])} to {I(ew['ir'])}, Inverse Vol {I(iv4['ir'])} to {I(iv['ir'])})."))
    B(("b", f"Individual-metal decomposition: Momentum's blended IR of {I(mom['ir'])} masks a single working metal. Aluminium alone returns IR {I(amom['Aluminium'])}, the only positive result among the four, while Copper, Zinc, and Lead are all negative "
            f"(Lead as low as {I(amom['Lead'])}). Value shows the opposite pattern, positive in every metal individually ({I(min(avir.values()))} to {I(max(avir.values()))}), with blended volatility of {V(val['vol'])} well below the roughly {V(avg_vol)} average held by any one metal alone."))
    B(("b", f"Why neither construction beats Value: diversification only adds value when it combines more than one genuine edge. Value is the only strategy with a clear edge (IR {I(val['ir'])}); Carry adds nothing ({I(car['ir'])}) and Momentum ({I(mom['ir'])}), "
            f"Carry-Momentum ({I(cm['ir'])}) and Skewness ({I(sk['ir'])}) are negative, so blending them with Value dilutes the one real signal in the book instead of diversifying real risk. The same logic applies within a strategy: blending Momentum across metals dilutes Aluminium's one working signal, "
            f"while blending Value across metals, where every metal carries a positive edge, lifts the IR above the average single metal ({I(val['ir'])} against {I(avg_ir)})."))
    B(("fig", "fig_metals_combined.png", "Figure 1. Metals: Combined Strategy Performance (Cumulative Return, 2012-2026)"))
    return blocks


if __name__ == "__main__":
    for b in metals():
        print(b[0], b[1][:2000] if b[0] != "fig" else b[1:]); print()
