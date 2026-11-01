from facts2 import *


def ngl():
    v, a = "ngl", "ngl"
    pr = VARIANTS[v][1]
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol")
    ew4, iv4 = st4(v, "EW PORT"), st4(v, "Inverse Vol")
    ewD, ivD = per(v, "EW PORT"), per(v, "Inverse Vol")
    ew4D, iv4D = [st4(v, "EW PORT", w)["ir"] for w in ("p1", "p2", "p3")], [st4(v, "Inverse Vol", w)["ir"] for w in ("p1", "p2", "p3")]
    cw = corr_within(v)
    others = {t: st(t, "EW PORT")["ir"] for t in ("metals", "energy", "precious", "agri")}
    others_iv = {t: st(t, "Inverse Vol")["ir"] for t in ("metals", "energy", "precious", "agri")}
    bo = max(others, key=others.get); bo_iv = max(others_iv, key=others_iv.get)
    chk(bo == "energy" and bo_iv == "energy", "energy is the best other class")
    chk(ew["ir"] > 1.5 * max(others.values()) and iv["ir"] > 1.4 * max(others_iv.values()), "NGL well ahead of every other class")
    chk(all(x > 0 for x in pm + pc + pcm), "NGL Momentum/Carry/CarryMom positive every period")
    chk(pv[0] < 0 and abs(pv[1]) < 0.1 and pv[2] > 0.8 and val["ir"] > 0, "NGL Value pattern")
    chk(ps[0] < -0.5 and ps[1] > 0.5 and ps[2] > 0, "NGL Skewness pattern")
    chk(all(x > 0 for x in ewD + ivD), "NGL portfolios positive every period")
    chk(ew["ir"] > iv["ir"] and ew["ret"] > iv["ret"] and ew["mdd"] > iv["mdd"] and iv["vol"] < ew["vol"], "NGL EW ahead on return, IR and drawdown; IV marginally lower volatility")
    vy = yearly_log(CS[v]["Value"])
    chk(all(vy.loc[y] > 0 for y in range(2022, 2027)) and vy.loc[2026] == vy.loc[2022:].max() and round(vy.loc[2026], 2) == 0.36 and round(vy.loc[2025], 2) == 0.09, "NGL Value 2022-2026")
    vpp = {p: pst(a, p, "Value", "p3")["ir"] for p in pr}
    chk(round(vpp["Propane"], 2) == 1.47 and round(vpp["Butane"], 2) == 1.09, "NGL Value P3 by product")
    mp = {p: pst(a, p, "Momentum")["ir"] for p in pr}; cp = {p: pst(a, p, "Carry")["ir"] for p in pr}; cmp_ = {p: pst(a, p, "CarryMom")["ir"] for p in pr}
    vf = {p: pst(a, p, "Value")["ir"] for p in pr}
    chk(min(mp.values()) > 0.6 and min(cp.values()) > 0.2 and min(cmp_.values()) > 0.05, "NGL every product positive in Momentum/Carry/CarryMom")
    allmins = {(c, k): min(pst(c, q, k)["ir"] for q in PRODUCTS[c]) for c in ("metals", "energy", "ngl", "precious", "agri") for k in SLEEVES}
    chk(max(allmins, key=allmins.get) == ("ngl", "Momentum"), "NGL Momentum has the highest weakest-product IR of any strategy in any asset class")
    chk(vf["Butane"] > 0.2 and vf["Isobutane"] > 0.1 and vf["Ethane"] < 0 and abs(vf["Propane"]) < 0.05, "NGL Value by product")
    carry_p = [pper(a, p, "Carry") for p in pr]; cmin = min(min(x) for x in [per(v, "Carry")]); cmax = max(per(v, "Carry"))
    skp = {p: pst(a, p, "Skewness")["ir"] for p in pr}; skpp = {p: pper(a, p, "Skewness") for p in pr}
    chk(all(skpp[p][0] < -0.2 for p in pr) and all(skpp[p][1] > 0.1 for p in pr), "NGL Skewness P1 negative and P2 positive in every product")
    sy = yearly_log(CS[v]["Skewness"])
    chk(round(sy.loc[2020], 2) > 1.0 and sy.loc[2012] < -0.6 and sy.loc[2021] > 0.5, "NGL Skewness years")
    lg = {p: legs(a, p) for p in pr}
    eth_crash, _ = skew_episode(a, "Ethane", "2020-03-01", "2020-04-30")
    prop_after, _ = skew_episode(a, "Propane", "2020-05-01", "2021-12-31")
    but_after, _ = skew_episode(a, "Butane", "2020-05-01", "2021-12-31")
    iso_after, _ = skew_episode(a, "Isobutane", "2020-05-01", "2021-12-31")
    chk(eth_crash > 1.0 and min(prop_after, but_after, iso_after) > 1.3, "NGL Skewness 2020 episode")
    chk(all(lg[p]["p3"]["long_pct"] > 75 for p in ("Ethane", "Propane", "Butane", "Isobutane")), "NGL Skewness long in P3")
    # checks added in the final verification pass
    from engine import _carry_base
    _ng = importlib.import_module("ngl")
    _sl = pd.concat([_carry_base(_ng.load_curve(p_), "F2", "F4").loc["2012-01-01":].dropna() for p_ in pr])
    _m = _sl.index.month
    f24_winter = 100 * _sl[(_m == 12) | (_m <= 3)].mean(); f24_summer = 100 * _sl[(_m >= 6) & (_m <= 9)].mean()
    chk(round(f24_winter, 1) == 3.7 and round(f24_summer, 1) == -1.7, "NGL F2-F4 seasonal slope")
    _pr = _ng.load_f1_series_logret("Propane")["F1_raw"]
    chk(round(_pr.loc["2026-02-27"], 2) == 0.67 and round(_pr.loc["2026-03-27"], 2) == 0.90, "NGL Propane contract held by the strategy on 27 Feb and 27 Mar 2026 (F1_raw; the first-listed generic F1 column reads 0.64 and 0.80 because the expiring contract is still listed)")
    sk1 = [skpp[p_][0] for p_ in pr]
    chk(all(x < 0 for x in sk1) and min(sk1) == skpp["Isobutane"][0] and max(sk1) == skpp["Ethane"][0], "NGL Skewness P1 range: Ethane least negative, Isobutane most")
    flip = {}; leg20 = {}; short_feb = {}
    for p_ in pr:
        lp_ = _ng.load_f1_series_logret(p_)["log_price"]; pos_ = exec_shift(raw_signal_skewness(lp_, 252), 1).fillna(0); r_ = lp_.diff()
        w_ = pos_.loc["2020-03-01":"2020-04-30"]; c_ = (pos_ * r_).loc["2020-03-01":"2020-04-30"]
        short_feb[p_] = float(pos_.loc["2020-02-24"]); flip[p_] = w_[w_ > 0].index[0]; leg20[p_] = (float(c_[w_ < 0].sum()), float(c_[w_ > 0].sum()))
    chk(all(pd.Timestamp("2020-03-01") <= flip[p_] <= pd.Timestamp("2020-03-31") for p_ in pr) and flip["Ethane"] == pd.Timestamp("2020-03-20") and all(flip[p_] == pd.Timestamp("2020-03-11") for p_ in ("Propane", "Butane", "Isobutane")), "NGL Skewness turned long in March 2020 (Ethane 20 March, others 11 March)")
    chk(all(v_ == -1 for v_ in short_feb.values()), "NGL Skewness short in all four products on 24 February 2020")
    chk(leg20["Ethane"][0] > 0.4 and leg20["Ethane"][1] > 0.6, "NGL Ethane March-April 2020 legs")
    cwc = {v_: corr_within(v_) for v_ in ("metals", "energy", "ngl", "precious", "agri")}
    chk(all(cw.loc["Skewness", "Momentum"] < cwc[v_].loc["Skewness", "Momentum"] for v_ in ("metals", "energy", "precious", "agri")) and all(cw.loc["Skewness", "Carry"] < cwc[v_].loc["Skewness", "Carry"] for v_ in ("metals", "energy", "precious", "agri")) and cw.loc["Skewness", "Value"] > 0, "NGL Skewness correlations with Momentum and Carry are the most negative of any class; Value positive")
    vprod = {p_: pper(a, p_, "Value") for p_ in pr}
    chk(vprod["Propane"][0] < 0 and vprod["Propane"][1] < 0 and vprod["Propane"][2] > 1.4 and vprod["Ethane"][0] < -0.3, "NGL Value by product and period: Propane negative in P1 and P2, large in P3")
    chk(skp["Ethane"] > 0.2 and abs(skp["Isobutane"]) < 0.1 and skp["Propane"] < 0 and skp["Butane"] < 0, "NGL Skewness by product")
    blocks = [("h2", "NGL")]; B = blocks.append
    B(("b", f"NGL is the strongest sleeve in the research: Equal Weight ({line(ew)}) and Inverse Vol ({line(iv)}), the best full-sample IR of any asset class under both constructions. "
            f"At the individual-strategy level, Momentum (IR {I(mom['ir'])}), Carry (IR {I(car['ir'])}) and Carry-Momentum (IR {I(cm['ir'])}) are positive in every one of the three periods. "
            f"Value ({line(val)}) is an exception: net positive full-sample but negative in P1 ({I(pv[0])}), flat in P2 ({I(pv[1])}) and strongly positive in P3 ({I(pv[2])}). "
            f"Skewness ({line(sk)}) is the other: negative in P1 ({I(ps[0])}), strongly positive in P2 ({I(ps[1])}) and weakly positive in P3 ({I(ps[2])})."))
    B(("b", f"NGL's portfolios are strong in every period rather than in one: Equal Weight IR is P1 {I(ewD[0])}, P2 {I(ewD[1])}, P3 {I(ewD[2])} and Inverse Vol P1 {I(ivD[0])}, P2 {I(ivD[1])}, P3 {I(ivD[2])}. "
            f"Both are well ahead of every other asset class, whose best full-sample Equal Weight IR is {I(others[bo])} (Energy; {I(st('energy_exng', 'EW PORT')['ir'])} without Natural Gas). "
            f"Skewness shifts the profile within the periods: P1 falls from {I(ew4D[0])} to {I(ewD[0])} for Equal Weight and P2 rises from {I(ew4D[1])} to {I(ewD[1])}, while the full-sample IR barely moves ({I(ew4['ir'])} to {I(ew['ir'])}; Inverse Vol {I(iv4['ir'])} to {I(iv['ir'])}) and volatility falls ({V(ew4['vol'])} to {V(ew['vol'])}). "
            f"The macro backdrop is the US export build-out: in 2012 Mont Belvieu propane traded at an average $0.89/gal discount to international prices because export terminals were at capacity (EIA), and US propane exports averaged a record 1.8 million b/d in 2024 (EIA) and reached a record 2.1 million b/d in April 2026 (EIA; exports first topped 2 million b/d in November 2024), "
            f"while ethane exports reached 492,000 b/d in 2024 against 65,000 b/d in 2015 and normal butane 491,000 b/d against 97,000 (OPIS, citing EIA)."))
    B(("b", f"Carry ({line(car)}) is the clearest embodiment of NGL's seasonal mechanics: predictable weather- and industrial-driven demand cycles push futures curves from contango in low-demand build periods into steep backwardation as inventories drain in peak season. "
            f"In the data the F2-F4 slope, averaged over the four products, is {N(f24_winter,1)}% (backwardation) in December to March and {N(f24_summer,1)}% (contango) in June to September. Carry is positive in every period (IR {I(min(pc))} to {I(max(pc))}), capturing that swing."))
    B(("b", f"The two portfolio constructions are close, with Equal Weight ahead on return, IR and drawdown: Equal Weight returns {R(ew['ret'])} against {R(iv['ret'])} for Inverse Vol, with an IR of {I(ew['ir'])} against {I(iv['ir'])} and a maximum drawdown of {M(ew['mdd'])} against {M(iv['mdd'])}, while Inverse Vol has marginally lower volatility ({V(iv['vol'])} against {V(ew['vol'])})."))
    B(("b", f"The P3 Value result ({I(pv[2])}) is not a one-year event: the sleeve earns a positive log return in each of 2022 to 2026, and 2026 is its best year of the period ({N(vy.loc[2026])}, against {N(vy.loc[2025])} in 2025). It is led by Propane ({I(vpp['Propane'])}) and Butane ({I(vpp['Butane'])}). "
            f"The war that began on 28 February 2026 and the closure of the Strait of Hormuz disrupted around 30% of global LPG supply (Veson Nautical estimate) and sent US LPG exports to a record 3.3 million b/d in April 2026 (S&P Global); in our series the Propane contract held by the strategy (rolled on the fifth trading day of its expiry month) rose from ${_pr.loc['2026-02-27']:.2f}/gal on 27 February to ${_pr.loc['2026-03-27']:.2f}/gal on 27 March."))
    B(("b", f"Skewness is a single-regime result in NGL. It is negative in all four products in P1 (IR {I(max(sk1))} to {I(min(sk1))}) and positive in all four in P2 (IR {I(min(x[1] for x in skpp.values()))} to {I(max(x[1] for x in skpp.values()))}); by calendar year it loses {abs(sy.loc[2012]):.2f} in 2012 and earns {N(sy.loc[2020])} in 2020 and {N(sy.loc[2021])} in 2021, "
            f"the crash and recovery of 2020-2021: the sleeve was short into the collapse (all four products had been short since mid-February; Ethane's position earned {N(leg20['Ethane'][0])} short and {N(leg20['Ethane'][1])} long in March and April 2020, turning long on 20 March) and in the other three products turned long on 11 March 2020, earning {N(prop_after)} in Propane, {N(but_after)} in Butane and {N(iso_after)} in Isobutane from May 2020 to December 2021, "
            f"then stayed long ({U(min(lg[p]['p3']['long_pct'] for p in pr),0)}% or more of P3 days in every product); it adds {N(sy.loc[2026])} in 2026. "
            f"It correlates at {N(cw.loc['Skewness', 'Momentum'])} with Momentum and {N(cw.loc['Skewness', 'Carry'])} with Carry, the most negative pairings in any asset class for those two, and at {N(cw.loc['Skewness', 'Value'])} with Value."))
    B(("b", f"Individual-product decomposition: Momentum works uniformly across all four products (IR {I(min(mp.values()))} to {I(max(mp.values()))}), the highest weakest-product result of any strategy in any asset class in the research. Carry (IR {I(min(cp.values()))} to {I(max(cp.values()))}) and Carry-Momentum (IR {I(min(cmp_.values()))} to {I(max(cmp_.values()))}) are also positive in every product. "
            f"Value's modest full-sample edge is concentrated in Butane and Isobutane (IR {I(vf['Butane'])} / {I(vf['Isobutane'])}), while Ethane and Propane show none (IR {I(vf['Ethane'])} / {I(vf['Propane'])}); the period inconsistency above is clearest in Propane (IR {I(vprod['Propane'][0])} in P1, {I(vprod['Propane'][1])} in P2, {I(vprod['Propane'][2])} in P3). "
            f"Skewness is positive in Ethane ({I(skp['Ethane'])}), about flat in Isobutane ({I(skp['Isobutane'])}) and slightly negative in Propane ({I(skp['Propane'])}) and Butane ({I(skp['Butane'])})."))
    B(("fig", "fig_ngl_combined.png", "Figure 4. NGL: Combined Strategy Performance (Cumulative Return, 2012-2026)"))
    return blocks


if __name__ == "__main__":
    for b in ngl():
        print(b[0], b[1] if b[0] != "fig" else b[1:])
        print()
