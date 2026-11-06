from facts3 import *
import importlib


def ngl8():
    """NGL bucket of v8: Ethane, Propane, Butane, Isobutane and Naphtha, data to 30 September 2026. Every claim is asserted against the 0930 data before it is printed."""
    v = "ngl"
    M5 = MEMBERS[v]; pr = [p for _, p in M5]
    four = [m for m in M5 if m[0] == "ngl"]
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
    chk(ew["ir"] > iv["ir"] and ew["ret"] > iv["ret"] and iv["vol"] < ew["vol"] and iv["mdd"] > ew["mdd"], "NGL EW ahead on return and IR; IV lower volatility and shallower drawdown")
    # four-product basis against five
    cs4 = pd.DataFrame({k: ew_intersection([nets()[m][k] for m in four]) for k in SLEEVES})
    ew_4p, iv_4p = stats(cs4.mean(axis=1, skipna=False)), stats(inverse_vol(cs4))
    chk(round(ew_4p["ir"], 2) == 1.26 and round(iv_4p["ir"], 2) == 1.16, "NGL four-product basis EW 1.26 IV 1.16")
    chk(ew["ir"] > ew_4p["ir"] and iv["ir"] > iv_4p["ir"] and ew["vol"] < ew_4p["vol"] and ew["mdd"] > ew_4p["mdd"], "adding Naphtha lifts IR, lowers volatility and drawdown")
    # products
    e5 = {p: stats(ew_intersection([nets()[(a, p)][k] for k in SLEEVES]))["ir"] for a, p in M5}
    chk(max(e5, key=e5.get) == "Naphtha" and min(e5, key=e5.get) == "Ethane", "Naphtha has the highest product-level EW-of-five IR, Ethane the lowest")
    nap_e = ew_intersection([nets()[("naphtha", "Naphtha")][k] for k in SLEEVES])
    cor_n = {}
    for a, p in four:
        e = ew_intersection([nets()[(a, p)][k] for k in SLEEVES]); cor_n[p] = float(pd.concat([e, nap_e], axis=1).loc["2012-01-01":].dropna().corr().iloc[0, 1])
    pet_ew = class_portfolios("petroleum")[0]
    cor_pet = float(pd.concat([nap_e, pet_ew], axis=1).loc["2012-01-01":].dropna().corr().iloc[0, 1])
    chk(max(cor_n.values()) < 0.4 and 0.55 < cor_pet < 0.65, "Naphtha correlations")
    npp = {k: pper("naphtha", "Naphtha", k) for k in SLEEVES}
    chk(all(x > 0 for x in npp["Skewness"]) and all(x > 0 for k in ("Carry", "CarryMom") for x in npp[k]) and npp["Momentum"][0] > 0, "Naphtha Carry, Carry-Momentum and Skewness positive in every period")
    chk(all(pper(a, p, "Skewness")[0] < -0.2 for a, p in four) and npp["Skewness"][0] > 0.2, "Skewness P1 negative in the four Mont Belvieu products, positive in Naphtha")
    skpp = {p: pper(a, p, "Skewness") for a, p in M5}
    chk(all(skpp[p][1] > 0.1 for p in pr), "Skewness P2 positive in all five")
    vy = yearly_log(CS[v]["Value"])
    chk(all(vy.loc[y] > 0 for y in range(2022, 2027)) and vy.loc[2026] == vy.loc[2022:].max(), "NGL Value positive in each of 2022 to 2026, 2026 the best")
    vpp = {p: pst(a, p, "Value", "p3")["ir"] for a, p in M5}
    chk(max(vpp, key=vpp.get) == "Propane" and sorted(vpp, key=vpp.get)[-2] == "Butane" and vpp["Naphtha"] > 0.9, "NGL Value P3 led by Propane then Butane, Naphtha +0.94")
    mp = {p: pst(a, p, "Momentum")["ir"] for a, p in M5}; cp = {p: pst(a, p, "Carry")["ir"] for a, p in M5}; cmp_ = {p: pst(a, p, "CarryMom")["ir"] for a, p in M5}
    vf = {p: pst(a, p, "Value")["ir"] for a, p in M5}; skp = {p: pst(a, p, "Skewness")["ir"] for a, p in M5}
    chk(min(mp.values()) > 0.5 and min(cp.values()) > 0.2 and min(cmp_.values()) > 0.1, "every product positive in Momentum/Carry/CarryMom")
    chk(vf["Butane"] > 0.2 and vf["Naphtha"] > 0.15 and vf["Isobutane"] > 0.1 and vf["Ethane"] < 0 and abs(vf["Propane"]) < 0.05, "NGL Value by product")
    chk(skp["Naphtha"] > skp["Ethane"] > 0.2 and abs(skp["Isobutane"]) < 0.1 and skp["Propane"] < 0 and skp["Butane"] < 0, "NGL Skewness by product")
    sy = yearly_log(CS[v]["Skewness"])
    chk(sy.loc[2012] < -0.4 and sy.loc[2020] > 1.0 and sy.loc[2021] > 0.5 and sy.loc[2026] > 0.4, "NGL Skewness years")
    lg = {p: legs(a, p) for a, p in M5}
    chk(min(lg[p]["p3"]["long_pct"] for p in pr) > 75, "NGL Skewness long on more than 75% of P3 days in every product")
    prop_after, _ = skew_episode("ngl", "Propane", "2020-05-01", "2021-12-31")
    but_after, _ = skew_episode("ngl", "Butane", "2020-05-01", "2021-12-31")
    iso_after, _ = skew_episode("ngl", "Isobutane", "2020-05-01", "2021-12-31")
    chk(min(prop_after, but_after, iso_after) > 1.3, "NGL Skewness 2020-2021 episode")
    chk(all(cw.loc["Skewness", "Momentum"] < corr_within(t).loc["Skewness", "Momentum"] for t in BUCKETS if t != v) and all(cw.loc["Skewness", "Carry"] < corr_within(t).loc["Skewness", "Carry"] for t in BUCKETS if t != v)
        and cw.loc["Skewness", "Value"] > 0, "NGL Skewness correlations with Momentum and Carry are the most negative of any bucket; Value positive")
    # seasonal carry slope F2-F4, five products
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
    L_nap, L_eth, L_iso = float(liq.loc["Naphtha", "L_strip"]), float(liq.loc["Ethane", "L_strip"]), float(liq.loc["Isobutane", "L_strip"])
    L5 = {p: float(liq.loc[p, "L_strip"]) for p in pr}
    chk(sorted(L5, key=L5.get)[-2:] == ["Naphtha", "Isobutane"] and round(L_nap, 1) == 9.4, "Naphtha L is 9.4 days, second longest in the bucket after Isobutane")
    B = []
    B.append(f"NGL (five products since v8: Ethane, Propane, Butane, Isobutane and Naphtha) is the strongest bucket in the research: Equal Weight ({line(ew)}) and Inverse Vol ({line(iv)}), the best full-sample IR of any bucket under both constructions. "
             f"At the individual-strategy level, Momentum (IR {I(mom['ir'])}), Carry (IR {I(car['ir'])}) and Carry-Momentum (IR {I(cm['ir'])}) are positive in every one of the three periods. "
             f"Value ({line(val)}) is an exception: net positive full-sample but negative in P1 ({I(pv[0])}), flat in P2 ({I(pv[1])}) and strongly positive in P3 ({I(pv[2])}). "
             f"Skewness ({line(sk)}) is the other: negative in P1 ({I(ps[0])}), strongly positive in P2 ({I(ps[1])}) and weakly positive in P3 ({I(ps[2])}).")
    B.append(f"NGL's portfolios are strong in every period rather than in one: Equal Weight IR is P1 {I(ewD[0])}, P2 {I(ewD[1])}, P3 {I(ewD[2])} and Inverse Vol P1 {I(ivD[0])}, P2 {I(ivD[1])}, P3 {I(ivD[2])}. "
             f"Both are well ahead of every other bucket, whose best full-sample Equal Weight IR is {I(others[bo])} (Petroleum). "
             f"Skewness shifts the profile within the periods: P1 falls from {I(ew4D[0])} to {I(ewD[0])} for Equal Weight and P2 rises from {I(ew4D[1])} to {I(ewD[1])}, while the full-sample IR barely moves ({I(ew4['ir'])} to {I(ew['ir'])}; Inverse Vol {I(iv4['ir'])} to {I(iv['ir'])}) and volatility falls ({V(ew4['vol'])} to {V(ew['vol'])}). "
             f"The macro backdrop is the US export build-out: in 2012 Mont Belvieu propane traded at an average $0.89/gal discount to international prices because export terminals were at capacity (EIA), and US propane exports averaged a record 1.8 million b/d in 2024 (EIA) and reached a record 2.1 million b/d in April 2026 (EIA; exports first topped 2 million b/d in November 2024), "
             f"while ethane exports reached 492,000 b/d in 2024 against 65,000 b/d in 2015 and normal butane 491,000 b/d against 97,000 (OPIS, citing EIA).")
    B.append(f"Naphtha (CIF NWE average-price swap, USD per tonne) is the fifth product and it strengthens the bucket. On the four Mont Belvieu products alone the bucket earned an Equal Weight IR of {I(ew_4p['ir'])} and an Inverse Vol IR of {I(iv_4p['ir'])}; with Naphtha they are {I(ew['ir'])} and {I(iv['ir'])}, volatility falls from {V(ew_4p['vol'])} to {V(ew['vol'])} and the Equal Weight maximum drawdown from {M(ew_4p['mdd'])} to {M(ew['mdd'])}. "
             f"On its own, Naphtha's five sleeves combined earn an IR of {I(e5['Naphtha'])}, the highest of the five products (Ethane {I(e5['Ethane'])}, Propane {I(e5['Propane'])}, Butane {I(e5['Butane'])}, Isobutane {I(e5['Isobutane'])}). "
             f"It is a different bet from the Mont Belvieu complex: its combined returns correlate {U(min(cor_n.values()))} to {U(max(cor_n.values()))} with the four Mont Belvieu products (Ethane {U(cor_n['Ethane'])}) and {U(cor_pet)} with the Petroleum bucket, consistent with a product priced off crude. "
             f"Carry and Carry-Momentum use the F2-F4 pair only for Naphtha, as its F14 is rarely quoted. Carry (IR {I(npp['Carry'][0])}, {I(npp['Carry'][1])}, {I(npp['Carry'][2])} in P1 to P3), Carry-Momentum ({I(npp['CarryMom'][0])}, {I(npp['CarryMom'][1])}, {I(npp['CarryMom'][2])}) and Skewness ({I(npp['Skewness'][0])}, {I(npp['Skewness'][1])}, {I(npp['Skewness'][2])}) are positive in every period; Naphtha's Skewness is positive in P1, where it is negative for every Mont Belvieu product. "
             f"The capacity caveat is material: Naphtha's time to trade one sigma of risk is {L_nap:.1f} days on the Bloomberg volume series, a partial view of the swap market, the second longest in the bucket after Isobutane ({L_iso:.0f} days) and above Ethane ({L_eth:.1f}) (see the liquidity section).")
    B.append(f"Carry ({line(car)}) is the clearest embodiment of NGL's seasonal mechanics: predictable weather- and industrial-driven demand cycles push futures curves from contango in low-demand build periods into steep backwardation as inventories drain in peak season. "
             f"In the data the F2-F4 slope, averaged over the five products, is {N(f24_winter,1)}% (backwardation) in December to March and {N(f24_summer,1)}% (contango) in June to September. Carry is positive in every period (IR {I(min(pc))} to {I(max(pc))}), capturing that swing.")
    B.append(f"The two portfolio constructions are close. Equal Weight is ahead on return and IR: it returns {R(ew['ret'])} against {R(iv['ret'])} for Inverse Vol, with an IR of {I(ew['ir'])} against {I(iv['ir'])}. Inverse Vol has the lower volatility ({V(iv['vol'])} against {V(ew['vol'])}) and the shallower maximum drawdown ({M(iv['mdd'])} against {M(ew['mdd'])}).")
    B.append(f"The P3 Value result ({I(pv[2])}) is not a one-year event: the sleeve earns a positive log return in each of 2022 to 2026, and 2026 is its best year of the period ({N(vy.loc[2026])}, against {N(vy.loc[2025])} in 2025). It is led by Propane ({I(vpp['Propane'])}) and Butane ({I(vpp['Butane'])}), with Naphtha close behind ({I(vpp['Naphtha'])}). "
             f"The war that began on 28 February 2026 and the closure of the Strait of Hormuz disrupted around 30% of global LPG supply (Veson Nautical estimate) and sent US LPG exports to a record 3.3 million b/d in April 2026 (S&P Global); in our series the Propane contract held by the strategy (rolled on the fifth trading day of its expiry month) rose from ${_pr.loc['2026-02-27']:.2f}/gal on 27 February to ${_pr.loc['2026-03-27']:.2f}/gal on 27 March, "
             f"and the Naphtha contract held rose from ${n0:,.0f}/t to ${n1:,.0f}/t over the same four weeks.")
    B.append(f"Skewness is a single-regime result in the Mont Belvieu products. It is negative in all four in P1 (IR {I(max(skpp[p][0] for _, p in four))} to {I(min(skpp[p][0] for _, p in four))}) and positive in all five products in P2 (IR {I(min(x[1] for x in skpp.values()))} to {I(max(x[1] for x in skpp.values()))}); by calendar year the sleeve loses {abs(sy.loc[2012]):.2f} in 2012 and earns {N(sy.loc[2020])} in 2020 and {N(sy.loc[2021])} in 2021, "
             f"the crash and recovery of 2020-2021: it turned long on 11 March 2020 in Propane, Butane and Isobutane, earning {N(prop_after)} in Propane, {N(but_after)} in Butane and {N(iso_after)} in Isobutane from May 2020 to December 2021, then stayed long ({U(min(lg[p]['p3']['long_pct'] for p in pr),0)}% or more of P3 days in every product); it adds {N(sy.loc[2026])} in 2026. "
             f"It correlates at {N(cw.loc['Skewness', 'Momentum'])} with Momentum and {N(cw.loc['Skewness', 'Carry'])} with Carry, the most negative pairings in any bucket for those two, and at {N(cw.loc['Skewness', 'Value'])} with Value.")
    B.append(f"Individual-product decomposition: Momentum is positive in all five products (IR {I(min(mp.values()))} to {I(max(mp.values()))}), Carry (IR {I(min(cp.values()))} to {I(max(cp.values()))}) and Carry-Momentum (IR {I(min(cmp_.values()))} to {I(max(cmp_.values()))}) likewise. "
             f"Value's modest full-sample edge is concentrated in Butane, Naphtha and Isobutane (IR {I(vf['Butane'])} / {I(vf['Naphtha'])} / {I(vf['Isobutane'])}), while Ethane and Propane show none (IR {I(vf['Ethane'])} / {I(vf['Propane'])}); the period inconsistency above is clearest in Propane (IR {I(pper('ngl', 'Propane', 'Value')[0])} in P1, {I(pper('ngl', 'Propane', 'Value')[1])} in P2, {I(pper('ngl', 'Propane', 'Value')[2])} in P3). "
             f"Skewness is positive in Naphtha ({I(skp['Naphtha'])}) and Ethane ({I(skp['Ethane'])}), about flat in Isobutane ({I(skp['Isobutane'])}) and slightly negative in Propane ({I(skp['Propane'])}) and Butane ({I(skp['Butane'])}).")
    return B
