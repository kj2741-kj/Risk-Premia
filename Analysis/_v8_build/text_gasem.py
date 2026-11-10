from facts3 import *
import importlib


def gasem():
    """Gas and Emissions bucket: Henry Hub, TTF, UK Gas, EUA. Every claim is asserted against the 0930 data before it is printed."""
    v = "pen"
    M4 = MEMBERS[v]; pr = [p for _, p in M4]
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol")
    ew4, iv4 = st4(v, "EW PORT"), st4(v, "Inverse Vol")
    ewD, ivD = per(v, "EW PORT"), per(v, "Inverse Vol")
    ew4D = [st4(v, "EW PORT", w)["ir"] for w in ("p1", "p2", "p3")]
    cw = corr_within(v)
    chk(pr == ["NatGas", "TTF", "UKGas", "EUA"], "Gas and Emissions has the four products")
    chk(car["ir"] > cm["ir"] > sk["ir"] > mom["ir"] > 0 > val["ir"], "Carry strongest sleeve, then Carry-Momentum, Skewness, Momentum; Value the only negative")
    chk(all(x > 0 for x in ewD + ivD), "portfolios positive in every period")
    chk(ewD[1] > 1.3 and ewD[1] > 3 * max(ewD[0], ewD[2]) * 0.99 or (ewD[1] > ewD[0] and ewD[1] > ewD[2]), "P2 is the strongest period")
    # product level
    e5 = {p: stats(ew_intersection([nets()[(a, p)][k] for k in SLEEVES]))["ir"] for a, p in M4}
    chk(e5["TTF"] > e5["UKGas"] > 0 > e5["NatGas"] > e5["EUA"], "TTF and UK Gas positive, Henry Hub flat, EUA negative")
    chk(abs(e5["NatGas"]) < 0.05, "Henry Hub is flat")
    pe = {p: ew_intersection([nets()[(a, p)][k] for k in SLEEVES]).loc["2012-01-01":] for a, p in M4}
    pc_ = pd.DataFrame(pe).dropna().corr()
    others = [abs(pc_.loc[a, b]) for a, b in combinations(pr, 2) if (a, b) != ("TTF", "UKGas")]
    chk(0.75 < pc_.loc["TTF", "UKGas"] < 0.8 and max(others) < 0.07, "TTF and UK Gas correlate 0.77, every other pair below 0.07")
    sleeve_vol = [st(v, k)["vol"] for k in SLEEVES]
    chk(min(sleeve_vol) > 33 and max(sleeve_vol) < 37 and 16 < ew["vol"] < 17, "sleeve volatilities 33 to 37%, bucket 16.5%")
    # gas crisis concentration
    ewp = PORT[v][0].loc["2012-01-01":].dropna(); tot = ewp.sum(); yl = yearly_log(ewp)
    share21 = yl[2021] / tot * 100; share2023 = yl.loc[2020:2023].sum() / tot * 100
    chk(round(share21) == 42 and round(share2023) == 89, f"2021 share {share21:.1f} and 2020-2023 share {share2023:.1f}")
    mask = ~((ewp.index >= "2021-07-01") & (ewp.index <= "2023-06-30"))
    ir_ex, ir_cr = stats(ewp[mask])["ir"], stats(ewp[~mask])["ir"]
    chk(round(ir_ex, 2) == 0.30 and round(ir_cr, 2) == 2.03 and ir_ex > 0, "excluding July 2021 to June 2023 the EW IR is +0.30; the window alone +2.03")
    # prices of the contracts held (F1_raw of the strategy series)
    ttf = importlib.import_module("emissions").load_f1_series_logret("TTF")["F1_raw"].dropna()
    ukg = importlib.import_module("emissions").load_f1_series_logret("UKGas")["F1_raw"].dropna()
    t0, tmax, tl = float(ttf.loc["2021-01-04":].iloc[0]), float(ttf.max()), float(ttf.iloc[-1])
    u0, umax, ul = float(ukg.loc["2021-01-04":].iloc[0]), float(ukg.max()), float(ukg.iloc[-1])
    chk(ttf.idxmax() == pd.Timestamp("2022-08-26") and ukg.idxmax() == pd.Timestamp("2022-08-26") and round(t0, 2) == 19.84 and round(tmax, 1) == 339.2 and round(tl, 2) == 72.36 and round(u0, 2) == 59.45 and round(umax, 2) == 640.36 and round(ul, 2) == 183.08, "TTF and UK Gas price path")
    # Carry
    cpp = {p: pper(a, p, "Carry") for a, p in M4}
    chk(cpp["TTF"][1] > 2.5 and cpp["UKGas"][1] > 2.5 and cpp["UKGas"][2] < 0 and pc[1] > 1.5 and pc[2] < 0.1, "Carry P2 strong in TTF and UK Gas, UK Gas negative in P3, bucket P3 flat")
    cp = {p: pst(a, p, "Carry")["ir"] for a, p in M4}
    chk(cp["TTF"] > cp["UKGas"] > cp["NatGas"] > 0 > cp["EUA"], "Carry by product")
    cy = yearly_log(CS[v]["Carry"])
    chk(round(cy.loc[2021], 2) == 1.68 and cy.loc[2021] == cy.max(), "Carry 2021 is its best year")
    cur = importlib.import_module("emissions").load_curve("TTF")
    slope = (cur["F1"] - cur["F13"]) / cur["F1"]
    s_crisis, s_p1, s_p2 = 100 * slope.loc["2021-07":"2022-12"].mean(), 100 * slope.loc["2012":"2016"].mean(), 100 * slope.loc["2017":"2021"].mean()
    chk(round(s_crisis, 1) == 24.2 and round(s_p1, 1) == -8.8 and round(s_p2, 1) == -10.4, "TTF F1-F13 slope")
    chk(all(x > 0 for x in pcm) and all(x > 0 for x in pper("emissions", "TTF", "Carry")), "Carry-Momentum positive in every period")
    # Momentum
    mp = {p: pst(a, p, "Momentum")["ir"] for a, p in M4}
    chk(mp["TTF"] > mp["UKGas"] > mp["NatGas"] > 0 > mp["EUA"] and abs(mp["NatGas"]) < 0.05, "Momentum by product")
    my = yearly_log(CS[v]["Momentum"]); m_tot = my.sum()
    chk(pm[0] < 0 < pm[1] and pm[2] < 0 and (my.loc[2020] + my.loc[2021]) > m_tot and round(my.loc[2020] + my.loc[2021], 2) == 1.66, "Momentum earns more than its total in 2020-2021 and is negative in P1 and P3")
    # Value
    vy = yearly_log(CS[v]["Value"]); allmin = min(yearly_log(CS[v][k]).min() for k in SLEEVES)
    chk(round(vy.loc[2021], 2) == -0.76 and vy.loc[2021] == allmin, "Value 2021 is the worst sleeve-year of the bucket")
    vpp = {p: pper(a, p, "Value") for a, p in M4}
    chk(vpp["TTF"][1] < -0.5 and vpp["UKGas"][1] < -0.5 and vpp["EUA"][1] < -0.5 and vpp["NatGas"][1] > 0 and vpp["TTF"][2] > 0.4 and vpp["UKGas"][2] > 0.6 and vpp["EUA"][2] > 0.4 and vpp["NatGas"][2] < 0, "Value by product and period")
    rk = cw.loc[SLEEVES, "EW PORT"].rank()
    chk(rk["Value"] == 1 and cw.loc["Value", "EW PORT"] > 0 and cw.loc["Value", "Momentum"] < -0.4, "Value least correlated with EW PORT, positive; -0.41 with Momentum")
    # Skewness
    lg = {p: legs(a, p) for a, p in M4}
    chk(all(x > 0 for x in ps) and lg["TTF"]["full"]["short_pnl"] > lg["TTF"]["full"]["long_pnl"] > 0 and lg["UKGas"]["full"]["short_pnl"] > 3 and lg["UKGas"]["full"]["long_pnl"] < 0, "Skewness legs in TTF and UK Gas")
    skp = {p: pst(a, p, "Skewness")["ir"] for a, p in M4}
    chk(skp["TTF"] > skp["UKGas"] > skp["EUA"] > 0 > skp["NatGas"] and lg["NatGas"]["full"]["long_pnl"] < -3, "Skewness by product; Henry Hub long leg loses")
    chk(ew["ir"] > ew4["ir"] and iv["ir"] > iv4["ir"] and ewD[0] > ew4D[0] and ewD[2] > ew4D[2], "Skewness lifts the bucket")
    chk(ew["ret"] > iv["ret"] and ew["ir"] > iv["ir"] and iv["vol"] < ew["vol"] and iv["mdd"] > ew["mdd"], "EW ahead on return and IR; IV lower volatility and shallower drawdown")
    dd = sorted(((st(t, "EW PORT")["mdd"], t) for t in BUCKETS))
    chk([x[1] for x in dd[:4]] == ["softs", "agri", "pen", "precious"] or [x[1] for x in dd[:4]] == ["softs", "agri", "precious", "pen"], "Softs and Agriculture have the deepest Equal Weight drawdowns, then Gas and Emissions and Precious Metals")
    cs_ = CS[v][SLEEVES].loc["2012-01-01":].dropna().corr().values; cmin, cmax = float(np.min(cs_[np.triu_indices(5, 1)])), float(np.max(cs_[np.triu_indices(5, 1)]))
    chk(round(cmin, 2) == -0.41 and round(cmax, 2) == 0.44, "pairwise sleeve correlations -0.41 to +0.44")
    B = []
    B.append(f"Gas and Emissions combines four products: Henry Hub natural gas (NYMEX), TTF natural gas (ICE Endex, Europe), UK Gas (NBP, ICE Futures Europe) and EUA carbon allowances (ICE Endex). Henry Hub was part of Energy in earlier versions. "
             f"Carry and Carry-Momentum use Henry Hub F1-F3 and F1-F13, TTF and UK Gas F1-F2 and F1-F13, and EUA F1-F2 and F1-F5 (EUA is a quarterly chain, so F5 is twelve months out). The bucket's data start in April 2008 (EUA's first Phase II day; Henry Hub, TTF and UK Gas start in January 2006) and results are reported from 1 January 2012.")
    B.append(f"Gas and Emissions is a high-volatility bucket with a real but uneven edge: Equal Weight ({line(ew)}) and Inverse Vol ({line(iv)}). Both are positive in every period but concentrated in P2 (Equal Weight IR P1 {I(ewD[0])}, P2 {I(ewD[1])}, P3 {I(ewD[2])}; Inverse Vol P1 {I(ivD[0])}, P2 {I(ivD[1])}, P3 {I(ivD[2])}). "
             f"Carry (IR {I(car['ir'])}) is the strongest sleeve, followed by Carry-Momentum ({I(cm['ir'])}), Skewness ({I(sk['ir'])}) and Momentum ({I(mom['ir'])}); Value (IR {I(val['ir'])}) is the only negative one. Each sleeve has a volatility of {V(min(sleeve_vol))} to {V(max(sleeve_vol))}, and combining them halves it to {V(ew['vol'])} because the sleeves are far from perfectly correlated (pairwise correlations {N(cmin)} to {N(cmax)}).")
    B.append(f"The result is concentrated in the 2021-2022 gas crisis. The Equal Weight portfolio earned {share21:.0f}% of its full-sample log return in 2021 alone and {share2023:.0f}% in 2020 to 2023. Excluding 1 July 2021 to 30 June 2023 its IR falls from {I(ew['ir'])} to {I(ir_ex)}, still positive, while that two-year window alone earns an IR of {I(ir_cr)}. "
             f"In our series the TTF contract held by the strategy rose from EUR {t0:.2f}/MWh on 4 January 2021 to a peak of EUR {tmax:.1f} on 26 August 2022 and stood at EUR {tl:.2f} on 30 September 2026; UK Gas rose from {u0:.2f} to {umax:.2f} pence per therm on the same dates and stood at {ul:.2f}.")
    B.append(f"The edge is in European gas, not in US gas or carbon allowances. Over the five sleeves combined, TTF earns an IR of {I(e5['TTF'])} and UK Gas {I(e5['UKGas'])}, against {I(e5['NatGas'])} for Henry Hub and {I(e5['EUA'])} for EUA. "
             f"TTF and UK Gas are close to one bet (their combined returns correlate {U(pc_.loc['TTF', 'UKGas'])}), while Henry Hub and EUA are uncorrelated with every other product (no pair above {U(max(others))} in magnitude), which is why the bucket diversifies even though two of its four products carry the whole edge.")
    B.append(f"Carry ({line(car)}) is the clearest source of the bucket's return: IR {I(pc[0])} in P1, {I(pc[1])} in P2 and {I(pc[2])} in P3, and {N(cy.loc[2021])} of log return in 2021, its best year. It is positive in TTF ({I(cp['TTF'])}), UK Gas ({I(cp['UKGas'])}) and Henry Hub ({I(cp['NatGas'])}) and slightly negative in EUA ({I(cp['EUA'])}). "
             f"TTF and UK Gas Carry reach {I(cpp['TTF'][1])} and {I(cpp['UKGas'][1])} in P2, then fade (TTF {I(cpp['TTF'][2])} in P3; UK Gas {I(cpp['UKGas'][2])}). The TTF F1-F13 slope explains why: it averaged {N(s_crisis,1)}% (backwardation) from July 2021 to December 2022, against {N(s_p1,1)}% in 2012-2016 and {N(s_p2,1)}% in 2017-2021 (contango). "
             f"Carry-Momentum ({line(cm)}) is positive in every period (IR {I(pcm[0])}, {I(pcm[1])}, {I(pcm[2])}).")
    B.append(f"Momentum ({line(mom)}) is a crisis strategy here: IR {I(pm[0])} in P1, {I(pm[1])} in P2 and {I(pm[2])} in P3. Calendar years 2020 and 2021 add {my.loc[2020] + my.loc[2021]:.2f} of log return against a full-sample total of {m_tot:.2f}, so the other thirteen years net to a loss. "
             f"By product it is positive in TTF ({I(mp['TTF'])}) and UK Gas ({I(mp['UKGas'])}), flat in Henry Hub ({I(mp['NatGas'])}) and negative in EUA ({I(mp['EUA'])}).")
    B.append(f"Value ({line(val)}) is the only negative core sleeve, and 2021 is its worst year ({N(vy.loc[2021])} of log return, the largest single-year loss of any sleeve in the bucket). Its P2 IR is {I(pv[1])}: TTF ({I(vpp['TTF'][1])}), UK Gas ({I(vpp['UKGas'][1])}) and EUA ({I(vpp['EUA'][1])}) lost, consistent with Value being short markets that kept rising above their five-year averages, while Henry Hub was flat ({I(vpp['NatGas'][1])}). "
             f"In P3 the sign reverses in the three of them (TTF {I(vpp['TTF'][2])}, UK Gas {I(vpp['UKGas'][2])}, EUA {I(vpp['EUA'][2])}; Henry Hub {I(vpp['NatGas'][2])}) and the bucket's P3 IR is {I(pv[2])}. Value is the least correlated sleeve with the bucket's EW PORT ({N(cw.loc['Value', 'EW PORT'])}) and correlates {N(cw.loc['Value', 'Momentum'])} with Momentum and {N(cw.loc['Value', 'Skewness'])} with Skewness.")
    B.append(f"Skewness ({line(sk)}) is positive in every period (IR {I(ps[0])}, {I(ps[1])}, {I(ps[2])}) and, unlike oil, is mostly short in European gas: the sleeve is long on only {U(lg['TTF']['full']['long_pct'],0)}% of TTF days and {U(lg['UKGas']['full']['long_pct'],0)}% of UK Gas days, and the short leg earns {N(lg['TTF']['full']['short_pnl'])} of log return in TTF against {N(lg['TTF']['full']['long_pnl'])} for the long leg, and {N(lg['UKGas']['full']['short_pnl'])} against {N(lg['UKGas']['full']['long_pnl'])} in UK Gas. "
             f"It is positive in TTF ({I(skp['TTF'])}), UK Gas ({I(skp['UKGas'])}) and EUA ({I(skp['EUA'])}) and negative in Henry Hub ({I(skp['NatGas'])}), where the long leg loses {abs(lg['NatGas']['full']['long_pnl']):.2f}. "
             f"Adding it lifts the bucket's Equal Weight IR from {I(ew4['ir'])} to {I(ew['ir'])} (Inverse Vol {I(iv4['ir'])} to {I(iv['ir'])}), with P1 rising from {I(ew4D[0])} to {I(ewD[0])} and P3 from {I(ew4D[2])} to {I(ewD[2])}.")
    B.append(f"The two portfolio constructions are close. Equal Weight is ahead on return and IR: it returns {R(ew['ret'])} against {R(iv['ret'])} for Inverse Vol, with an IR of {I(ew['ir'])} against {I(iv['ir'])}. Inverse Vol has the lower volatility ({V(iv['vol'])} against {V(ew['vol'])}) and the shallower maximum drawdown ({M(iv['mdd'])} against {M(ew['mdd'])}); "
             f"its Equal Weight maximum drawdown of {M(ew['mdd'])} is, with Precious Metals ({M(st('precious', 'EW PORT')['mdd'])}), the third deepest of the seven buckets, behind Softs ({M(st('softs', 'EW PORT')['mdd'])}) and Agriculture ({M(st('agri', 'EW PORT')['mdd'])}).")
    return B
