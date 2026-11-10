from facts3 import *
import importlib


def _basis(members):
    cs = pd.DataFrame({k: ew_intersection([nets()[m][k] for m in members]) for k in SLEEVES})
    return stats(cs.mean(axis=1, skipna=False)), stats(inverse_vol(cs)), [stats(cs.mean(axis=1, skipna=False), w)["ir"] for w in ("p1", "p2", "p3")]


def ngl8():
    """NGL bucket of v8 after 10 November 2026: Ethane, Propane, Butane, Naphtha and Natural Gasoline (CME MMB); Isobutane removed on 9 November 2026. Every claim is asserted against the 0930 data before it is printed."""
    v = "ngl"
    M5 = MEMBERS[v]; pr = [p for _, p in M5]
    assert pr == ["Ethane", "Propane", "Butane", "Naphtha", "NatGasoline"], pr
    mb = [m for m in M5 if m[0] == "ngl"]           # the three Mont Belvieu products
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol")
    ew4, iv4 = st4(v, "EW PORT"), st4(v, "Inverse Vol")
    ewD, ivD = per(v, "EW PORT"), per(v, "Inverse Vol")
    ew4D = [st4(v, "EW PORT", w)["ir"] for w in ("p1", "p2", "p3")]
    cw = corr_within(v)
    others = {t: st(t, "EW PORT")["ir"] for t in BUCKETS if t != v}
    others_iv = {t: st(t, "Inverse Vol")["ir"] for t in BUCKETS if t != v}
    bo = max(others, key=others.get); bo_iv = max(others_iv, key=others_iv.get)
    chk(bo == "petroleum" and bo_iv == "petroleum", "petroleum is the best other bucket")
    chk(ew["ir"] > 1.5 * max(others.values()) and iv["ir"] > 1.4 * max(others_iv.values()), "NGL well ahead of every other bucket")
    chk(all(x > 0 for x in pm + pc + pcm), "NGL Momentum/Carry/CarryMom positive every period")
    chk(pv[0] < 0 and abs(pv[1]) < 0.1 and pv[2] > 0.8 and val["ir"] > 0, "NGL Value pattern")
    chk(ps[0] < -0.5 and ps[1] > 0.5 and ps[2] > 0 and sk["ir"] > 0, "NGL Skewness pattern")
    chk(all(x > 0 for x in ewD + ivD), "NGL portfolios positive every period")
    chk(abs(ew["ir"] - iv["ir"]) < 0.02 and abs(ew["ret"] - iv["ret"]) < 0.1 and iv["vol"] < ew["vol"] and iv["mdd"] > ew["mdd"], "NGL EW and IV essentially equal; IV slightly lower volatility and shallower drawdown")
    # bases: three Mont Belvieu products, plus Naphtha (four products, v8 as of 9 November), plus Natural Gasoline (five)
    e3, i3, _ = _basis(mb); e4, i4, p4 = _basis(M5[:4])
    chk(round(e3["ir"], 2) == 1.20 and round(i3["ir"], 2) == 1.12, "NGL three-product basis EW 1.20 IV 1.12")
    chk(round(e4["ir"], 2) == 1.43 and round(i4["ir"], 2) == 1.41, "NGL four-product basis EW 1.43 IV 1.41")
    chk(e4["ir"] > ew["ir"] > e3["ir"] and i4["ir"] > iv["ir"] > i3["ir"], "five-product IR between the three- and the four-product basis")
    chk(ew["vol"] < e4["vol"] and ew["mdd"] > e4["mdd"] and all(p4[i] > ewD[i] for i in range(3)) and p4[0] - ewD[0] > 0.15 and p4[1] - ewD[1] < 0.05, "adding Natural Gasoline: lower volatility and drawdown, lower Equal Weight IR in every period (clearly in P1)")
    chk(ew4D[0] > ewD[0] and ew4D[1] < ewD[1] and ew["vol"] < ew4["vol"], "Skewness: P1 falls, P2 rises, volatility falls")
    # products
    e5p = {p: stats(ew_intersection([nets()[(a, p)][k] for k in SLEEVES]))["ir"] for a, p in M5}
    chk(max(e5p, key=e5p.get) == "Naphtha" and min(e5p, key=e5p.get) == "Ethane" and sorted(e5p, key=e5p.get)[1] == "NatGasoline", "Naphtha has the highest product-level EW-of-five IR, Ethane the lowest, Natural Gasoline the second lowest")
    nap_e = ew_intersection([nets()[("naphtha", "Naphtha")][k] for k in SLEEVES]); mmb_e = ew_intersection([nets()[("mmb", "NatGasoline")][k] for k in SLEEVES])
    cor_n = {}; cor_m = {}
    for a, p in mb:
        e = ew_intersection([nets()[(a, p)][k] for k in SLEEVES])
        cor_n[p] = float(pd.concat([e, nap_e], axis=1).loc["2012-01-01":].dropna().corr().iloc[0, 1]); cor_m[p] = float(pd.concat([e, mmb_e], axis=1).loc["2012-01-01":].dropna().corr().iloc[0, 1])
    pet_ew = class_portfolios("petroleum")[0]
    cor_pet = float(pd.concat([nap_e, pet_ew], axis=1).loc["2012-01-01":].dropna().corr().iloc[0, 1])
    cor_mpet = float(pd.concat([mmb_e, pet_ew], axis=1).loc["2012-01-01":].dropna().corr().iloc[0, 1])
    cor_mn = float(pd.concat([mmb_e, nap_e], axis=1).loc["2012-01-01":].dropna().corr().iloc[0, 1])
    chk(max(cor_n.values()) < 0.4 and 0.55 < cor_pet < 0.65, "Naphtha correlations")
    chk(0.05 < min(cor_m.values()) and max(cor_m.values()) < 0.4 and 0.6 < cor_mpet < 0.7 and 0.6 < cor_mn < 0.7, "Natural Gasoline correlations: low with the Mont Belvieu products, high with Petroleum and Naphtha")
    npp = {k: pper("naphtha", "Naphtha", k) for k in SLEEVES}; gpp = {k: pper("mmb", "NatGasoline", k) for k in SLEEVES}
    chk(all(x > 0 for x in npp["Skewness"]) and all(x > 0 for k in ("Carry", "CarryMom") for x in npp[k]) and npp["Momentum"][0] > 0, "Naphtha Carry, Carry-Momentum and Skewness positive in every period")
    chk(all(pper(a, p, "Skewness")[0] < -0.2 for a, p in mb) and gpp["Skewness"][0] < 0 and npp["Skewness"][0] > 0.2, "Skewness P1 negative in the three Mont Belvieu products and Natural Gasoline, positive in Naphtha")
    skpp = {p: pper(a, p, "Skewness") for a, p in M5}
    chk(all(skpp[p][1] > 0.1 for p in pr), "Skewness P2 positive in all five")
    vy = yearly_log(CS[v]["Value"])
    chk(all(vy.loc[y] > 0 for y in range(2022, 2027)) and vy.loc[2026] == vy.loc[2022:].max(), "NGL Value positive in each of 2022 to 2026, 2026 the best")
    vpp = {p: pst(a, p, "Value", "p3")["ir"] for a, p in M5}
    srt = sorted(vpp, key=vpp.get)
    chk(srt[-1] == "Propane" and srt[-2] == "Butane" and srt[-3] == "Naphtha" and vpp["Naphtha"] > 0.9 and vpp["NatGasoline"] > 0.5, "NGL Value P3 led by Propane, then Butane and Naphtha")
    mp = {p: pst(a, p, "Momentum")["ir"] for a, p in M5}; cp = {p: pst(a, p, "Carry")["ir"] for a, p in M5}; cmp_ = {p: pst(a, p, "CarryMom")["ir"] for a, p in M5}
    vf = {p: pst(a, p, "Value")["ir"] for a, p in M5}; skp = {p: pst(a, p, "Skewness")["ir"] for a, p in M5}
    chk(min(mp.values()) > 0 and min(cp.values()) > 0.2 and min(cmp_.values()) > 0.1 and min(mp, key=mp.get) == "NatGasoline" and mp["NatGasoline"] < 0.1, "every product positive in Momentum/Carry/CarryMom; Natural Gasoline the weakest in Momentum, close to zero")
    chk(max(gpp["CarryMom"]) < 1.3 and all(x > 0 for x in gpp["CarryMom"]) and cmp_["NatGasoline"] > 0.7 and gpp["Carry"][0] < 0 < gpp["Carry"][1] and 0.15 < cp["NatGasoline"] < 0.3, "Natural Gasoline: Carry-Momentum its best sleeve and positive in every period; Carry small")
    chk(vf["Butane"] > 0.2 and vf["Naphtha"] > 0.15 and vf["Ethane"] < 0 and abs(vf["Propane"]) < 0.05 and 0 < vf["NatGasoline"] < 0.1, "NGL Value by product")
    chk(skp["Naphtha"] > skp["Ethane"] > 0.2 and 0.2 < skp["NatGasoline"] < 0.3 and skp["Propane"] < 0 and skp["Butane"] < 0, "NGL Skewness by product")
    sy = yearly_log(CS[v]["Skewness"])
    chk(sy.loc[2012] < -0.4 and sy.loc[2020] > 1.0 and sy.loc[2021] > 0.5 and sy.loc[2026] > 0.4, "NGL Skewness years")
    lg = {p: legs(a, p) for a, p in M5}
    chk(min(lg[p]["p3"]["long_pct"] for p in pr) > 75, "NGL Skewness long on more than 75% of P3 days in every product")
    prop_after, _ = skew_episode("ngl", "Propane", "2020-05-01", "2021-12-31")
    but_after, _ = skew_episode("ngl", "Butane", "2020-05-01", "2021-12-31")
    chk(min(prop_after, but_after) > 1.3, "NGL Skewness 2020-2021 episode")
    chk(all(cw.loc["Skewness", "Momentum"] < corr_within(t).loc["Skewness", "Momentum"] for t in BUCKETS if t != v) and all(cw.loc["Skewness", "Carry"] < corr_within(t).loc["Skewness", "Carry"] for t in BUCKETS if t != v)
        and cw.loc["Skewness", "Value"] > 0, "NGL Skewness correlations with Momentum and Carry are the most negative of any bucket; Value positive")
    from engine import _carry_base
    sl = pd.concat([_carry_base(importlib.import_module(a).load_curve(p), "F2", "F4").loc["2012-01-01":].dropna() for a, p in M5])
    m_ = sl.index.month
    f24_winter = 100 * sl[(m_ == 12) | (m_ <= 3)].mean(); f24_summer = 100 * sl[(m_ >= 6) & (m_ <= 9)].mean()
    chk(f24_winter > 2 and f24_summer < -1, f"NGL F2-F4 seasonal slope {f24_winter:.2f} {f24_summer:.2f}")
    _pr = importlib.import_module("ngl").load_f1_series_logret("Propane")["F1_raw"]
    chk(round(_pr.loc["2026-02-27"], 2) == 0.67 and round(_pr.loc["2026-03-27"], 2) == 0.90, "Propane held contract on 27 Feb and 27 Mar 2026")
    _nf = importlib.import_module("naphtha").load_f1_series_logret("Naphtha")["F1_raw"]
    n0, n1 = float(_nf.loc[:"2026-02-27"].iloc[-1]), float(_nf.loc[:"2026-03-27"].iloc[-1])
    chk(round(n0) == 588 and round(n1) == 942, "Naphtha held contract on 27 Feb and 27 Mar 2026")
    liq = pd.read_csv(os.path.join(REPO, "Analysis", "Liquidity_Cal2025_results.csv")).set_index("product")
    L_nap, L_eth, L_mmb = float(liq.loc["Naphtha", "L_strip"]), float(liq.loc["Ethane", "L_strip"]), float(liq.loc["NatGasoline", "L_strip"])
    L5 = {p: float(liq.loc[p, "L_strip"]) for p in pr}
    chk(sorted(L5, key=L5.get)[-3:] == ["NatGasoline", "Ethane", "Naphtha"] and round(L_nap, 1) == 9.4 and 1.0 < L_mmb < 1.5, "Naphtha L is 9.4 days, the longest in the bucket, then Ethane, then Natural Gasoline")
    adv_m, days_m = float(liq.loc["NatGasoline", "adv_strip"]), float(liq.loc["NatGasoline", "share_days_print"])
    chk(700 < adv_m < 900 and days_m > 0.95, "Natural Gasoline volume")
    B = []
    B.append(f"NGL (five products: Ethane, Propane, Butane, Naphtha and Natural Gasoline; Isobutane, the least liquid product in the data set, is excluded) is the strongest bucket in the research: Equal Weight ({line(ew)}) and Inverse Vol ({line(iv)}), the best full-sample IR of any bucket under both constructions. "
             f"At the individual-strategy level, Momentum (IR {I(mom['ir'])}), Carry (IR {I(car['ir'])}) and Carry-Momentum (IR {I(cm['ir'])}) are positive in every one of the three periods. "
             f"Value ({line(val)}) is an exception: net positive full-sample but negative in P1 ({I(pv[0])}), flat in P2 ({I(pv[1])}) and strongly positive in P3 ({I(pv[2])}). "
             f"Skewness ({line(sk)}) is the other: negative in P1 ({I(ps[0])}), strongly positive in P2 ({I(ps[1])}) and weakly positive in P3 ({I(ps[2])}).")
    B.append(f"NGL's portfolios are strong in every period rather than in one: Equal Weight IR is P1 {I(ewD[0])}, P2 {I(ewD[1])}, P3 {I(ewD[2])} and Inverse Vol P1 {I(ivD[0])}, P2 {I(ivD[1])}, P3 {I(ivD[2])}. "
             f"Both are well ahead of every other bucket, whose best full-sample Equal Weight IR is {I(others[bo])} (Petroleum). "
             f"Skewness shifts the profile within the periods: P1 falls from {I(ew4D[0])} to {I(ewD[0])} for Equal Weight and P2 rises from {I(ew4D[1])} to {I(ewD[1])}, while the full-sample IR changes little ({I(ew4['ir'])} to {I(ew['ir'])}; Inverse Vol {I(iv4['ir'])} to {I(iv['ir'])}) and volatility falls ({V(ew4['vol'])} to {V(ew['vol'])}). "
             f"The macro backdrop is the US export build-out: in 2012 Mont Belvieu propane traded at an average $0.89/gal discount to international prices because export terminals were at capacity (EIA), and US propane exports averaged a record 1.8 million b/d in 2024 (EIA) and reached a record 2.1 million b/d in April 2026 (EIA; exports first topped 2 million b/d in November 2024), "
             f"while ethane exports reached 492,000 b/d in 2024 against 65,000 b/d in 2015 and normal butane 491,000 b/d against 97,000 (OPIS, citing EIA).")
    B.append(f"Naphtha (CIF NWE average-price swap, USD per tonne) strengthens the bucket. On the three Mont Belvieu products alone it earned an Equal Weight IR of {I(e3['ir'])} and an Inverse Vol IR of {I(i3['ir'])}; with Naphtha, as a four-product bucket, they were {I(e4['ir'])} and {I(i4['ir'])}, volatility fell from {V(e3['vol'])} to {V(e4['vol'])} and the Equal Weight maximum drawdown from {M(e3['mdd'])} to {M(e4['mdd'])}. "
             f"On its own, Naphtha's five sleeves combined earn an IR of {I(e5p['Naphtha'])}, the highest of the five products (Butane {I(e5p['Butane'])}, Propane {I(e5p['Propane'])}, Natural Gasoline {I(e5p['NatGasoline'])}, Ethane {I(e5p['Ethane'])}). "
             f"It is a different bet from the Mont Belvieu complex: its combined returns correlate {U(min(cor_n.values()))} to {U(max(cor_n.values()))} with the three Mont Belvieu products (Ethane {U(cor_n['Ethane'])}) and {U(cor_pet)} with the Petroleum bucket, consistent with a product priced off crude. "
             f"Carry and Carry-Momentum use the F2-F4 pair only for Naphtha, as its F14 is rarely quoted. Carry (IR {I(npp['Carry'][0])}, {I(npp['Carry'][1])}, {I(npp['Carry'][2])} in P1 to P3), Carry-Momentum ({I(npp['CarryMom'][0])}, {I(npp['CarryMom'][1])}, {I(npp['CarryMom'][2])}) and Skewness ({I(npp['Skewness'][0])}, {I(npp['Skewness'][1])}, {I(npp['Skewness'][2])}) are positive in every period; Naphtha's Skewness is positive in P1, where it is negative for every Mont Belvieu product and for Natural Gasoline. "
             f"The capacity caveat is material: Naphtha's time to trade one sigma of risk is {L_nap:.1f} days on the Bloomberg volume series, a partial view of the swap market, the longest in the bucket and above Ethane ({L_eth:.1f}) (see the liquidity section).")
    B.append(f"Natural Gasoline (the CME Mont Belvieu 5-decimal OPIS swap, Bloomberg MMB, USD per gallon, added to the bucket on 10 November 2026) is the fifth product and it does not strengthen the bucket. With it the Equal Weight IR is {I(ew['ir'])} and the Inverse Vol IR {I(iv['ir'])}, against {I(e4['ir'])} and {I(i4['ir'])} for the four products without it; "
             f"Equal Weight IR falls in every period (P1 from {I(p4[0])} to {I(ewD[0])}, P2 from {I(p4[1])} to {I(ewD[1])}, P3 from {I(p4[2])} to {I(ewD[2])}), while the Equal Weight volatility ({V(e4['vol'])} to {V(ew['vol'])}) and maximum drawdown ({M(e4['mdd'])} to {M(ew['mdd'])}) are lower. "
             f"The reason is the product itself: its five sleeves combined earn an IR of {I(e5p['NatGasoline'])}, the second lowest of the five (Ethane {I(e5p['Ethane'])}), because Momentum ({I(mp['NatGasoline'])}) and Carry ({I(cp['NatGasoline'])}; {I(gpp['Carry'][0])} in P1, {I(gpp['Carry'][1])} in P2, {I(gpp['Carry'][2])} in P3) are close to zero. "
             f"Carry-Momentum is its one strong sleeve ({I(cmp_['NatGasoline'])}, positive in every period: {I(gpp['CarryMom'][0])}, {I(gpp['CarryMom'][1])}, {I(gpp['CarryMom'][2])}); Value ({I(vf['NatGasoline'])}) and Skewness ({I(skp['NatGasoline'])}) are small. "
             f"It uses the same Carry pairs as the Mont Belvieu products (F2-F4 and F2-F14). Its combined returns correlate {U(cor_mn)} with Naphtha and {U(cor_mpet)} with the Petroleum bucket but only {U(min(cor_m.values()))} to {U(max(cor_m.values()))} with the three Mont Belvieu products (Ethane {U(cor_m['Ethane'])}, Propane {U(cor_m['Propane'])}, Butane {U(cor_m['Butane'])}), so in these results it behaves more like Naphtha than like the other Mont Belvieu swaps. "
             f"It is far more liquid than Naphtha and Ethane: its time to trade one sigma of risk is {L_mmb:.2f} days, with about {adv_m:,.0f} lots a day on a 12-month strip and a print on {days_m * 100:.0f}% of days (CME volume; see the liquidity section).")
    B.append(f"Carry ({line(car)}) is the clearest embodiment of NGL's seasonal mechanics: predictable weather- and industrial-driven demand cycles push futures curves from contango in low-demand build periods into steep backwardation as inventories drain in peak season. "
             f"In the data the F2-F4 slope, averaged over the five products, is {N(f24_winter,1)}% (backwardation) in December to March and {N(f24_summer,1)}% (contango) in June to September. Carry is positive in every period (IR {I(min(pc))} to {I(max(pc))}), capturing that swing.")
    B.append(f"The two portfolio constructions are essentially the same: Equal Weight returns {R(ew['ret'])} against {R(iv['ret'])} for Inverse Vol, with an IR of {I(ew['ir'])} against {I(iv['ir'])}. Inverse Vol has the slightly lower volatility ({V(iv['vol'])} against {V(ew['vol'])}) and the shallower maximum drawdown ({M(iv['mdd'])} against {M(ew['mdd'])}).")
    B.append(f"The P3 Value result ({I(pv[2])}) is not a one-year event: the sleeve earns a positive log return in each of 2022 to 2026, and 2026 is its best year of the period ({N(vy.loc[2026])}, against {N(vy.loc[2025])} in 2025). It is led by Propane ({I(vpp['Propane'])}), Butane ({I(vpp['Butane'])}) and Naphtha ({I(vpp['Naphtha'])}), with Natural Gasoline at {I(vpp['NatGasoline'])}. "
             f"The war that began on 28 February 2026 and the closure of the Strait of Hormuz disrupted around 30% of global LPG supply (Veson Nautical estimate) and sent US LPG exports to a record 3.3 million b/d in April 2026 (S&P Global); in our series the Propane contract held by the strategy (rolled on the fifth trading day of its expiry month) rose from ${_pr.loc['2026-02-27']:.2f}/gal on 27 February to ${_pr.loc['2026-03-27']:.2f}/gal on 27 March, "
             f"and the Naphtha contract held rose from ${n0:,.0f}/t to ${n1:,.0f}/t over the same four weeks.")
    B.append(f"Skewness is a single-regime result in the Mont Belvieu products. It is negative in all three in P1 (IR {I(max(skpp[p][0] for _, p in mb))} to {I(min(skpp[p][0] for _, p in mb))}) and in Natural Gasoline ({I(skpp['NatGasoline'][0])}), and positive in all five products in P2 (IR {I(min(x[1] for x in skpp.values()))} to {I(max(x[1] for x in skpp.values()))}); by calendar year the sleeve loses {abs(sy.loc[2012]):.2f} in 2012 and earns {N(sy.loc[2020])} in 2020 and {N(sy.loc[2021])} in 2021, "
             f"the crash and recovery of 2020-2021: it turned long on 11 March 2020 in Propane and Butane, earning {N(prop_after)} in Propane and {N(but_after)} in Butane from May 2020 to December 2021, then stayed long ({U(min(lg[p]['p3']['long_pct'] for p in pr),0)}% or more of P3 days in every product); it adds {N(sy.loc[2026])} in 2026. "
             f"It correlates at {N(cw.loc['Skewness', 'Momentum'])} with Momentum and {N(cw.loc['Skewness', 'Carry'])} with Carry, the most negative pairings in any bucket for those two, and at {N(cw.loc['Skewness', 'Value'])} with Value.")
    B.append(f"Individual-product decomposition: Momentum is positive in all five products (IR {I(min(mp.values()))} to {I(max(mp.values()))}; Natural Gasoline is the weakest at {I(mp['NatGasoline'])}), Carry (IR {I(min(cp.values()))} to {I(max(cp.values()))}) and Carry-Momentum (IR {I(min(cmp_.values()))} to {I(max(cmp_.values()))}) likewise. "
             f"Value's modest full-sample edge is concentrated in Butane and Naphtha (IR {I(vf['Butane'])} / {I(vf['Naphtha'])}), while Ethane, Propane and Natural Gasoline show little or none (IR {I(vf['Ethane'])} / {I(vf['Propane'])} / {I(vf['NatGasoline'])}); the period inconsistency above is clearest in Propane (IR {I(pper('ngl', 'Propane', 'Value')[0])} in P1, {I(pper('ngl', 'Propane', 'Value')[1])} in P2, {I(pper('ngl', 'Propane', 'Value')[2])} in P3). "
             f"Skewness is positive in Naphtha ({I(skp['Naphtha'])}), Ethane ({I(skp['Ethane'])}) and Natural Gasoline ({I(skp['NatGasoline'])}) and slightly negative in Propane ({I(skp['Propane'])}) and Butane ({I(skp['Butane'])}).")
    return B
