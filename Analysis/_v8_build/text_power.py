from power_facts import *


def power():
    """US Power (standalone) section. Every claim is asserted against the 0930 Power data before it is printed."""
    ew, iv, ew4, iv4 = stp(EW_P), stp(IV_P), stp(EW4_P), stp(IV4_P)
    sl = {k: stp(STY_P[k]) for k in SLEEVES}
    per_ = lambda s: [stp(s, w)["ir"] for w in ("p2", "p3")]
    ewP, ivP = per_(EW_P), per_(IV_P)
    chk(PJ["tab"]["data_first"] == "2015-01-02" and PJ["tab"]["data_last"] == "2026-09-30" and PJ["tab"]["products"] == [LABEL_P[p] for p in MEMBERS_P], "Power data window and members")
    liq = pd.read_csv(os.path.join(REPO, "Analysis", "Power_Liquidity_Cal2025_results.csv")).set_index("product")
    Lp = {p: float(liq.loc[p, "L_strip"]) for p in MEMBERS_P}; Lx = float(liq.loc["MISO_OffPeak", "L_strip"])
    chk([round(Lp[p], 2) if Lp[p] < 1 else round(Lp[p], 1) for p in MEMBERS_P] == [0.10, 0.47, 0.36, 4.7, 4.7] and round(Lx, 1) == 9.9, "Power time to trade 1 sigma of risk")
    chk(all(v == 141 for v in PJ["tab"]["rolls"].values()), "141 rolls per series")
    chk(ew["ir"] > 0 and iv["ir"] > 0 and ewP[0] > 0.8 and ewP[1] < 0 < ivP[1] and abs(ewP[1]) < 0.05, "Power: positive full sample, strong P2, flat P3 (EW slightly negative, IV slightly positive)")
    y26e, y26i = stp(EW_P, "y26")["ir"], stp(IV_P, "y26")["ir"]
    chk(y26e < 0 and y26i < 0, "Power 2026 year to date negative under both constructions")
    sv = [stp(STY_P[k])["vol"] for k in SLEEVES]; pvol = {p: stp(combine_returns([NETS_P[p][k] for k in SLEEVES], "equal_weight"))["vol"] for p in MEMBERS_P}
    chk(min(sv) > 51 and max(sv) < 58 and 29 < ew["vol"] < 30, "sleeve vols 52 to 58, bucket 29.4")
    # sleeves
    pm, pc, pcm, pv, ps = ([stp(STY_P[k], w)["ir"] for w in ("p2", "p3")] for k in SLEEVES)
    chk(sl["Value"]["ir"] > sl["Carry"]["ir"] > sl["Momentum"]["ir"] > sl["Skewness"]["ir"] > 0 > sl["CarryMom"]["ir"], "Power sleeve order: Value, Carry, Momentum, Skewness positive; Carry-Momentum negative")
    chk(all(x > 0 for x in pv) and pc[0] > 2 and pc[1] < 0 and pcm[0] > 0 > pcm[1] and all(x > 0 for x in pm) and ps[0] < 0 < ps[1], "Power sleeve period pattern")
    yy = {k: yl_p(STY_P[k]) for k in SLEEVES}; ye = yl_p(EW_P)
    allv = sorted(((abs(yy[k][y]), k, y, yy[k][y]) for k in SLEEVES for y in yy[k].index), reverse=True)
    chk((allv[0][1], allv[0][2]) == ("Carry", 2022) and (allv[1][1], allv[1][2]) == ("Skewness", 2024) and round(yy["Carry"][2022], 2) == -1.85 and round(yy["Skewness"][2024], 2) == 1.63, "largest sleeve-years")
    chk(ye.idxmin() == 2022 and round(ye[2022], 2) == -0.38 and round(yy["CarryMom"][2022], 2) == -0.89 and round(yy["Value"][2022], 2) == 0.86, "2022: EW worst year; Value the only sleeve that earns")
    chk(all(yy[k][2022] < 0 for k in ("Momentum", "Carry", "CarryMom")) and yy["Skewness"][2022] > 0 and yy["Value"][2022] > 0, "2022 signs by sleeve")
    # products
    e5 = {p: stp(combine_returns([NETS_P[p][k] for k in SLEEVES], "equal_weight")) for p in MEMBERS_P}
    chk(max(e5, key=lambda p: e5[p]["ir"]) == "ERCOT_Peak" and min(e5, key=lambda p: e5[p]["ir"]) == "ERCOT_OffPeak" and e5["ERCOT_OffPeak"]["ir"] < 0, "ERCOT Peak best product, ERCOT OffPeak the only negative")
    chk(round(e5["ERCOT_Peak"]["vol"]) == 67 and round(e5["ERCOT_Peak"]["mdd"]) == -85 and min(x["vol"] for x in e5.values()) > 34, "ERCOT Peak vol 67% and drawdown -85%; every product above 34% vol")
    pcor = pd.DataFrame({p: combine_returns([NETS_P[p][k] for k in SLEEVES], "equal_weight") for p in MEMBERS_P}).loc["2017-01-01":].dropna().corr()
    chk(round(pcor.loc["PJM_Peak", "MISO_Peak"], 2) == 0.67 and round(pcor.loc["PJM_Peak", "PJM_OffPeak"], 2) == 0.62 and round(pcor.loc["ERCOT_Peak", "ERCOT_OffPeak"], 2) == 0.47, "product correlations")
    cross = [pcor.loc[a, b] for a in ("ERCOT_Peak", "ERCOT_OffPeak") for b in ("PJM_Peak", "PJM_OffPeak", "MISO_Peak")]
    chk(max(cross) < 0.15, "ERCOT versus PJM and MISO below 0.15")
    pp = lambda p, k, w="full": stp(NETS_P[p][k], w)["ir"]
    cp = {p: pp(p, "Carry") for p in MEMBERS_P}; cp2 = {p: pp(p, "Carry", "p2") for p in MEMBERS_P}; cp3 = {p: pp(p, "Carry", "p3") for p in MEMBERS_P}
    chk(all(x > 0 for x in cp2.values()) and round(cp2["ERCOT_Peak"], 2) == 3.84 and sum(1 for x in cp3.values() if x < 0) == 4 and cp3["MISO_Peak"] > 0, "Carry by product and period")
    chk(cp["ERCOT_Peak"] > cp["MISO_Peak"] > cp["PJM_OffPeak"] > cp["PJM_Peak"] > 0 > cp["ERCOT_OffPeak"], "Carry by product")
    vp = {p: pp(p, "Value") for p in MEMBERS_P}
    chk(all(x > 0.15 for x in vp.values()) and round(min(vp.values()), 2) == 0.18 and round(max(vp.values()), 2) == 0.36, "Value positive in all five products")
    cw = pd.concat([pd.DataFrame(STY_P), EW_P.rename("EW PORT")], axis=1).loc["2017-01-01":].dropna().corr()
    chk(round(cw.loc["Value", "Momentum"], 2) == -0.15 and round(cw.loc["Value", "Skewness"], 2) == -0.21 and round(cw.loc["Value", "EW PORT"], 2) == 0.31 and cw.loc["Skewness", "EW PORT"] == cw.loc[SLEEVES, "EW PORT"].min(), "Power sleeve correlations")
    skp = {p: pp(p, "Skewness") for p in MEMBERS_P}; sk3 = {p: pp(p, "Skewness", "p3") for p in MEMBERS_P}
    chk(skp["PJM_Peak"] < -0.4 and skp["PJM_OffPeak"] < -0.4 and round(skp["ERCOT_OffPeak"], 2) == 0.88 and round(sk3["ERCOT_OffPeak"], 2) == 1.97 and yy["Skewness"].min() == yy["Skewness"][2019] and round(yy["Skewness"][2019], 2) == -0.87, "Skewness by product and year")
    chk(ew["mdd"] < min(st(t, "EW PORT")["mdd"] for t in BUCKETS) and abs(ew["ret"] - iv["ret"]) < 0.1, "Power EW drawdown deeper than any bucket; the two constructions return the same")
    chk(ew["vol"] > max(st(t, "EW PORT")["vol"] for t in BUCKETS), "Power portfolio volatility is the highest")
    chk(sorted(cw.loc[SLEEVES, "EW PORT"].rank().items(), key=lambda kv: kv[1])[1][0] == "Value", "Value second-least correlated with the portfolio after Skewness")
    chk(sorted(Lp, key=Lp.get)[-2:] == ["ERCOT_OffPeak", "MISO_Peak"], "ERCOT OffPeak and MISO Peak have the longest times to trade")
    chk(iv["ir"] > ew["ir"] and iv["vol"] < ew["vol"] and iv["mdd"] > ew["mdd"], "IV slightly ahead, lower volatility, shallower drawdown")
    chk(ew4["ir"] < ew["ir"] and iv4["ir"] < iv["ir"] and round(ew4["ir"], 2) == 0.28 and round(iv4["ir"], 2) == 0.25, "Skewness lifts EW and IV")
    oc = {b: float(pd.concat([EW_P, PORT[b][0]], axis=1).loc["2017-01-01":].dropna().corr().iloc[0, 1]) for b in BUCKETS}
    chk(min(oc.values()) > -0.03 and max(oc.values()) < 0.05, "Power EW PORT versus the six buckets' EW PORT")
    bc = bench_corr(EW_P, "2017-01-01")
    chk(max(abs(v) for v in bc.values()) < 0.04, "Power benchmark correlations")
    B = []
    B.append(f"US Power is a standalone bucket and is not part of the cross-commodity book. The series are ICE monthly real-time power futures (USD per MWh), peak and off-peak, on the PJM Western Hub, ERCOT North 345KV and MISO Indiana Hub. The data files hold ten series: the four CME ones start in 2026 and carry no volume or open interest, so six are usable, "
             f"and the five whose Calendar-2025 time to trade one sigma of risk is under 5 days are included (PJM Peak {Lp['PJM_Peak']:.2f}, ERCOT Peak {Lp['ERCOT_Peak']:.2f}, PJM OffPeak {Lp['PJM_OffPeak']:.2f}, ERCOT OffPeak {Lp['ERCOT_OffPeak']:.1f}, MISO Peak {Lp['MISO_Peak']:.1f} days); MISO OffPeak, at {Lx:.1f} days, is excluded. "
             f"The data start on 2 January 2015 and Value needs two years of F3, so results run from 2017 and there is no P1; the periods are P2 (2017-2021), P3 (2022-2026) and the full window. Every delivery month is listed and its last trade date falls in the delivery month, so the generic F1 is the contract delivering now. "
             f"The usual roll (the fifth trading day of the expiry month) therefore moves into the next month on the fifth trading day of the delivery month, and the position is in the partly settled delivery-month contract for its first four or five trading days. Carry and Carry-Momentum use F1-F2 and F1-F13.")
    B.append(f"US Power earns a weak positive edge at very high volatility: Equal Weight ({lineP(ew)}) and Inverse Vol ({lineP(iv)}). The result sits in P2: Equal Weight IR is {I(ewP[0])} in P2 and {I(ewP[1])} in P3 (Inverse Vol {I(ivP[0])} and {I(ivP[1])}), and 2026 to 30 September is negative under both constructions (Equal Weight {I(y26e)}, Inverse Vol {I(y26i)}). "
             f"Each sleeve has a volatility of {V(min(sv))} to {V(max(sv))}; combining them brings it to {V(ew['vol'])}, still the highest of any bucket's portfolio, so the IRs should be read together with the drawdowns, and the Equal Weight maximum drawdown of {M(ew['mdd'])} is deeper than in any of the six buckets.")
    B.append(f"Value ({lineP(sl['Value'])}) is the best sleeve and, with Momentum, one of only two positive in both periods (P2 {I(pv[0])}, P3 {I(pv[1])}); Carry ({lineP(sl['Carry'])}) follows but is a P2 result (P2 {I(pc[0])}, P3 {I(pc[1])}); Momentum (IR {I(sl['Momentum']['ir'])}; P2 {I(pm[0])}, P3 {I(pm[1])}) and Skewness (IR {I(sl['Skewness']['ir'])}) add little; "
             f"Carry-Momentum ({lineP(sl['CarryMom'])}) is the only negative sleeve (P2 {I(pcm[0])}, P3 {I(pcm[1])}).")
    B.append(f"The weakest year is 2022: the Equal Weight portfolio loses {abs(ye[2022]):.2f} of log return because Carry loses {abs(yy['Carry'][2022]):.2f} (the largest sleeve-year in the bucket) and Carry-Momentum {abs(yy['CarryMom'][2022]):.2f} and Momentum {abs(yy['Momentum'][2022]):.2f}, while Value earns {N(yy['Value'][2022])} and Skewness {N(yy['Skewness'][2022])}. "
             f"The other very large sleeve-year is Skewness in 2024 ({N(yy['Skewness'][2024])}), against {N(yy['Skewness'][2019])} in 2019 and {N(yy['Skewness'][2023])} in 2023, which is why its full-sample IR is close to zero ({I(sl['Skewness']['ir'])}).")
    B.append(f"The five products differ materially in return, risk and capacity. Over the five sleeves combined, ERCOT Peak earns the best IR ({I(e5['ERCOT_Peak']['ir'])}) at a volatility of {V(e5['ERCOT_Peak']['vol'])} and a maximum drawdown of {M(e5['ERCOT_Peak']['mdd'])}, followed by MISO Peak ({I(e5['MISO_Peak']['ir'])}), PJM Peak ({I(e5['PJM_Peak']['ir'])}) and PJM OffPeak ({I(e5['PJM_OffPeak']['ir'])}); ERCOT OffPeak is negative ({I(e5['ERCOT_OffPeak']['ir'])}). "
             f"The products form two clusters: PJM Peak correlates {U(pcor.loc['PJM_Peak', 'MISO_Peak'])} with MISO Peak and {U(pcor.loc['PJM_Peak', 'PJM_OffPeak'])} with PJM OffPeak, and the two ERCOT series {U(pcor.loc['ERCOT_Peak', 'ERCOT_OffPeak'])} with each other, while ERCOT against PJM and MISO is at most {U(max(cross))}. "
             f"The capacity constraint is tightest for ERCOT OffPeak and MISO Peak ({Lp['ERCOT_OffPeak']:.1f} days each to trade one sigma of risk).")
    B.append(f"Carry's P2 result of {I(pc[0])} comes from every product (P2 IR {I(min(cp2.values()))} to {I(max(cp2.values()))}, with ERCOT Peak at {I(cp2['ERCOT_Peak'])}); in P3 it is negative in four of the five (only MISO Peak is positive, {I(cp3['MISO_Peak'])}). Over the full window it is positive in ERCOT Peak ({I(cp['ERCOT_Peak'])}), MISO Peak ({I(cp['MISO_Peak'])}), PJM OffPeak ({I(cp['PJM_OffPeak'])}) and PJM Peak ({I(cp['PJM_Peak'])}) and negative in ERCOT OffPeak ({I(cp['ERCOT_OffPeak'])}).")
    B.append(f"Value is positive in every product (IR {I(min(vp.values()))} to {I(max(vp.values()))}). It is also the main diversifier inside the bucket after Skewness: it correlates {N(cw.loc['Value', 'Momentum'])} with Momentum and {N(cw.loc['Value', 'Skewness'])} with Skewness and {N(cw.loc['Value', 'EW PORT'])} with the bucket's Equal Weight portfolio (Skewness {N(cw.loc['Skewness', 'EW PORT'])}), while Carry and Carry-Momentum correlate {N(cw.loc['Carry', 'EW PORT'])} and {N(cw.loc['CarryMom', 'EW PORT'])} with it and {N(cw.loc['Carry', 'CarryMom'])} with each other.")
    B.append(f"Skewness splits by product: negative in PJM Peak ({I(skp['PJM_Peak'])}) and PJM OffPeak ({I(skp['PJM_OffPeak'])}) and strongly positive in ERCOT OffPeak ({I(skp['ERCOT_OffPeak'])}; P3 {I(sk3['ERCOT_OffPeak'])}). It is negative in P2 ({I(ps[0])}) and positive in P3 ({I(ps[1])}). Adding it lifts the portfolio's IR from {I(ew4['ir'])} to {I(ew['ir'])} for Equal Weight and from {I(iv4['ir'])} to {I(iv['ir'])} for Inverse Vol.")
    B.append(f"The two portfolio constructions are close: Inverse Vol has the slightly higher IR ({I(iv['ir'])} against {I(ew['ir'])}), the lower volatility ({V(iv['vol'])} against {V(ew['vol'])}) and the shallower maximum drawdown ({M(iv['mdd'])} against {M(ew['mdd'])}) for the same return ({R(iv['ret'])}).")
    B.append(f"As a stream, US Power is close to uncorrelated with everything else in the research: its Equal Weight portfolio correlates {N(min(oc.values()))} to {N(max(oc.values()))} with the six buckets' Equal Weight portfolios over 2017 to 2026 and {N(bc['Equity'])} with equity, {N(bc['Commodity Index'])} with the Commodity Index and {N(bc['Gold'])} with gold, but at an IR of {I(ew['ir'])} and a volatility of {V(ew['vol'])} it is a weak stand-alone return stream.")
    key = (f"US Power (PJM, ERCOT and MISO real-time monthly futures; standalone, outside the cross-commodity book) earns Equal Weight IR {I(ew['ir'])} and Inverse Vol IR {I(iv['ir'])} from 2017 at {V(ew['vol'])} volatility and a {M(ew['mdd'])} maximum drawdown, with Value the best sleeve (IR {I(sl['Value']['ir'])}) and Carry-Momentum the only negative one. "
           f"It is a P2 result (Equal Weight IR {I(ewP[0])} in P2, {I(ewP[1])} in P3), 2022 is its worst year (Carry alone loses {abs(yy['Carry'][2022]):.2f} of log return), and it is uncorrelated with the six buckets ({N(min(oc.values()))} to {N(max(oc.values()))}).")
    return B, key
