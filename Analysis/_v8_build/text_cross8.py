from facts3 import *

W3 = ("p1", "p2", "p3")


def _c(x):
    """Unsigned-looking correlation with a minus for negatives (v3 convention), no negative zero."""
    return "0.00" if abs(round(x, 2)) == 0 else f"{x:.2f}"


def book():
    bs = bystyle(); bs4 = bystyle4()
    return bs, bs4


def corr8():
    out = {}
    cw = {t: corr_within(t) for t in BUCKETS}
    lab = {t: SHORT[t] for t in BUCKETS}
    sl = {t: cw[t].loc[SLEEVES, "EW PORT"] for t in BUCKETS}
    chk(all(sl[t].rank()["Value"] == 1 and sl[t].rank()["Skewness"] == 2 for t in BUCKETS), "Value lowest and Skewness second lowest correlation with EW PORT in every bucket")
    pos_value = [t for t in BUCKETS if cw[t].loc["Value", "EW PORT"] > 0.01]
    chk(pos_value == ["pen", "agri", "softs"] and abs(cw["ngl"].loc["Value", "EW PORT"]) < 0.01, "Value positively correlated with the portfolio in Gas and Emissions, Agriculture and Softs, zero in NGL")
    mc = {t: cw[t].loc["Momentum", "Carry"] for t in BUCKETS}; cc = {t: cw[t].loc["Carry", "CarryMom"] for t in BUCKETS}; mcm = {t: cw[t].loc["Momentum", "CarryMom"] for t in BUCKETS}
    top_mc = [t for t in BUCKETS if mc[t] > cc[t] and mc[t] > mcm[t]]; top_cc = [t for t in BUCKETS if cc[t] > mc[t] and cc[t] > mcm[t]]; top_mcm = [t for t in BUCKETS if mcm[t] > mc[t] and mcm[t] > cc[t]]
    chk(top_mc == ["petroleum", "ngl"] and top_cc == ["metals", "pen", "precious"] and top_mcm == ["agri", "softs"], "closest base pair by bucket")
    vm = {t: cw[t].loc["Value", "Momentum"] for t in BUCKETS}
    chk(all(x < 0 for x in vm.values()), "Value negatively correlated with Momentum in every bucket")
    sv = {t: cw[t].loc["Skewness", "Value"] for t in BUCKETS}
    chk([t for t in BUCKETS if sv[t] > 0] == ["ngl"] and min(sv, key=sv.get) == "precious", "Skewness-Value negative in five buckets, most in Precious Metals, positive in NGL")
    sm = {t: cw[t].loc["Skewness", "Momentum"] for t in BUCKETS}; sc = {t: cw[t].loc["Skewness", "Carry"] for t in BUCKETS}
    chk(min(sm, key=sm.get) == "ngl" and min(sc, key=sc.get) == "ngl" and max(abs(x) for t, x in list(sm.items()) + list(sc.items()) if t != "ngl") < 0.21, "Skewness with Momentum and Carry near zero except NGL")
    chk(sorted(sv, key=sv.get)[:1] == ["precious"] and len([t for t in BUCKETS if sv[t] < 0]) == 6, "Skewness-Value negative in six buckets")
    ivw = [cw[t].loc["Inverse Vol", "EW PORT"] for t in BUCKETS]
    chk(round(min(ivw), 2) == 0.95 and round(max(ivw), 2) == 0.99, "Inverse Vol versus EW PORT 0.95 to 0.99")
    j = lambda d: ", ".join(f"{N(d[t])} in {lab[t]}" for t in BUCKETS[:-1]) + f" and {N(d[BUCKETS[-1]])} in {lab[BUCKETS[-1]]}"
    out["within"] = [
        f"Value is the least correlated sleeve with its own EW PORT in every bucket, correlating at {j({t: cw[t].loc['Value', 'EW PORT'] for t in BUCKETS})}. Skewness is the second least correlated in every bucket ({j({t: cw[t].loc['Skewness', 'EW PORT'] for t in BUCKETS})}), so the two sleeves with the weakest links to the portfolio are the two that are not built on trend or curve slope, which is consistent with, not a test of, their acting as diversifiers. In Gas and Emissions, Agriculture and Softs, where Value is positively correlated with the portfolio (in NGL the correlation is zero), it is still the lowest of the five.",
        f"Momentum and Carry are the most correlated pair of base strategies in Petroleum ({N(mc['petroleum'])}) and NGL ({N(mc['ngl'])}), consistent with a common driver behind the two signals (not tested here). Metals, Gas and Emissions and Precious Metals break this pattern: in all three, Carry and Carry-Momentum are the closest pair ({N(cc['metals'])} in Metals, {N(cc['pen'])} in Gas and Emissions, {N(cc['precious'])} in Precious Metals), and in Agriculture and Softs it is Momentum and Carry-Momentum ({N(mcm['agri'])} and {N(mcm['softs'])}). Value is negatively correlated with Momentum in all seven buckets ({j(vm)}).",
        f"Skewness pairs differently by bucket. With Value it is negative in six buckets and strongest in Precious Metals ({j(sv)}); in NGL it is the exception. With Momentum and Carry it is near zero (no reading above 0.20 in magnitude) except in NGL, where it is {N(sm['ngl'])} and {N(sc['ngl'])}.",
        f"Inverse Vol tracks its own EW PORT closely everywhere, correlating between {U(min(ivw))} and {U(max(ivw))} across all seven buckets, expected since both portfolios are built from the same five sleeves and differ only in how they are weighted.",
    ]
    # cross-bucket
    ser = SLEEVES + ["EW PORT", "Inverse Vol"]; cx = {k: corr_cross(k) for k in ser}
    top = {k: max(PAIR_ORDER, key=lambda p: cx[k].loc[p[0], p[1]]) for k in ser}
    chk(all(top[k] == ("petroleum", "ngl") for k in ser), "Petroleum-NGL is the most correlated pair for all seven series")
    pn = {k: cx[k].loc["petroleum", "ngl"] for k in ser}
    ewc = cx["EW PORT"]
    order = sorted(PAIR_ORDER, key=lambda p: -ewc.loc[p[0], p[1]])
    chk([order[1], order[2], order[3]] == [("pen", "ngl"), ("petroleum", "pen"), ("metals", "precious")], "EW PORT: second Gas and Emissions-NGL, third Petroleum-Gas and Emissions, fourth Metals-Precious")
    sec = {k: sorted(PAIR_ORDER, key=lambda p: -cx[k].loc[p[0], p[1]])[1] for k in ser}
    chk(sec["Momentum"] == ("metals", "precious") and sec["Value"] == ("metals", "precious") and sec["Skewness"] == ("metals", "precious") and sec["Carry"] == ("petroleum", "pen") and sec["CarryMom"] == ("pen", "ngl"), "second-place pairs")
    third_cm = sorted(PAIR_ORDER, key=lambda p: -cx["CarryMom"].loc[p[0], p[1]])[2]
    chk(third_cm == ("petroleum", "agri") and cx["CarryMom"].loc["pen", "ngl"] - cx["CarryMom"].loc["petroleum", "agri"] < 0.02, "Carry-Momentum: Gas and Emissions-NGL second, narrowly ahead of Petroleum-Agriculture")
    avg = {k: float(np.mean([abs(cx[k].loc[a, b]) for a, b in PAIR_ORDER])) for k in ser}
    chk(min(avg, key=avg.get) == "CarryMom" and sorted(avg.values())[1] > 0.06, "Carry-Momentum has the lowest average cross-bucket correlation")
    cm_vals = [cx["CarryMom"].loc[a, b] for a, b in PAIR_ORDER]
    n_small = sum(1 for x in cm_vals if abs(x) < 0.10)
    chk(max(cm_vals) == pn["CarryMom"] and n_small == len(cm_vals) - 1 == 20, f"Carry-Momentum: 20 of 21 pairs below 0.10, maximum Petroleum-NGL ({n_small})")
    ge = {b: ewc.loc["pen", b] for b in BUCKETS if b != "pen"}
    chk(abs(ge["metals"]) < 0.01 and abs(ge["precious"]) < 0.05 and abs(ge["agri"]) < 0.05 and abs(ge["softs"]) < 0.05 and ge["ngl"] == max(ge.values()), "Gas and Emissions is uncorrelated with Metals, Precious Metals, Agriculture and Softs")
    out["cross"] = [
        f"Petroleum and NGL are the most correlated cross-bucket pair for all seven series types tracked: Momentum ({U(pn['Momentum'])}), Carry ({U(pn['Carry'])}), Carry-Momentum ({U(pn['CarryMom'])}), Value ({U(pn['Value'])}), Skewness ({U(pn['Skewness'])}), EW PORT ({U(pn['EW PORT'])}) and Inverse Vol ({U(pn['Inverse Vol'])}), consistent with both trading the same hydrocarbon complex (the Naphtha swap, priced off crude, is part of NGL).",
        f"Gas and Emissions is close to uncorrelated with everything except the hydrocarbon buckets: its EW PORT correlation is {_c(ge['ngl'])} with NGL and {_c(ge['petroleum'])} with Petroleum, and {_c(ge['metals'])} with Metals, {_c(ge['precious'])} with Precious Metals, {_c(ge['agri'])} with Agriculture and {_c(ge['softs'])} with Softs. Metals-Precious Metals is the second most correlated pair for Momentum ({U(cx['Momentum'].loc['metals', 'precious'])}), Value ({U(cx['Value'].loc['metals', 'precious'])}) and Skewness ({U(cx['Skewness'].loc['metals', 'precious'])}) and fourth for EW PORT ({U(ewc.loc['metals', 'precious'])}); for Carry the second place is Petroleum-Gas and Emissions ({U(cx['Carry'].loc['petroleum', 'pen'])}) and for Carry-Momentum Gas and Emissions-NGL ({U(cx['CarryMom'].loc['pen', 'ngl'])}), narrowly ahead of Petroleum-Agriculture ({U(cx['CarryMom'].loc['petroleum', 'agri'])}).",
        f"Carry-Momentum has the lowest cross-bucket correlations of the seven series: its correlations to the same strategy in other buckets average just {U(avg['CarryMom'])} in magnitude (Carry {U(avg['Carry'])}; the other five range {U(sorted(avg.values())[1])} to {U(max(avg.values()))}), and {n_small} of its twenty-one pairwise readings are below 0.10, the exception being Petroleum-NGL ({U(pn['CarryMom'])}).",
    ]
    # pairs
    ps = pair_stats()
    rows = sorted(ps, key=lambda p: -p["ew"]["ir"])
    out["pair_rows"] = [[p["name"], _c(p["corr"]), I(p["ew"]["ir"]), I(p["iv"]["ir"])] for p in rows]
    out["pairs"] = ps
    best = rows[0]
    best_iv = max(ps, key=lambda p: p["iv"]["ir"]); iv_rows = sorted(ps, key=lambda p: -p["iv"]["ir"])
    chk(best["name"] == "Petroleum-NGL" and rows[1]["name"] == "Gas and Emissions-NGL" and best_iv["name"] == "Petroleum-NGL" and iv_rows[1]["name"] == "Gas and Emissions-NGL" and best_iv["iv"]["ir"] - iv_rows[1]["iv"]["ir"] < 0.02, "Petroleum-NGL best under Equal Weight and (narrowly) under Inverse Vol, Gas and Emissions-NGL second under both")
    worst = min(ps, key=lambda p: p["ew"]["ir"]); worst_iv = min(ps, key=lambda p: p["iv"]["ir"])
    chk(worst["name"] == "Agriculture-Softs" and worst_iv["name"] == "Agriculture-Softs", "Agriculture-Softs lowest under both")
    out["impl_intro"] = (f"The Cross-Pair tab shows all twenty-one bucket pairs. Under the EW PORT measure, Petroleum-NGL ({U(ewc.loc['petroleum', 'ngl'])}) is by far the most correlated pair; the next three are Gas and Emissions-NGL ({U(ewc.loc['pen', 'ngl'])}), Petroleum-Gas and Emissions ({U(ewc.loc['petroleum', 'pen'])}) and Metals-Precious Metals ({U(ewc.loc['metals', 'precious'])}), and every other pair is at or below 0.08 in magnitude. "
                         f"The table below sets each pair's EW PORT correlation beside its full-sample IR under Equal Weight and Inverse Vol.")
    chk(max(abs(ewc.loc[a, b]) for a, b in PAIR_ORDER if (a, b) not in (("petroleum", "ngl"), ("pen", "ngl"), ("petroleum", "pen"), ("metals", "precious"))) <= 0.081, "every other pair at or below 0.08")
    out["impl_close"] = (f"Correlation and standalone performance are separate questions. Held on its own, Petroleum-NGL, the most correlated pair, produces the highest full-sample Equal Weight IR of the twenty-one pairs ({I(best['ew']['ir'])}) and the highest under Inverse Vol as well ({I(best['iv']['ir'])}, narrowly ahead of Gas and Emissions-NGL at {I(iv_rows[1]['iv']['ir'])}), "
                         f"while Agriculture-Softs produces the lowest under both (Equal Weight {I(worst['ew']['ir'])}, Inverse Vol {I(worst['iv']['ir'])}). Two individually strong books can still make a poor diversification pairing simply because they move together.")
    out["best_iv"] = best_iv
    return out


def cross8():
    bs, bs4 = book()
    ew, iv = stats(bs["EW PORT"]), stats(bs["Inverse Vol"])
    ew4, iv4 = stats(bs4["EW PORT"]), stats(bs4["Inverse Vol"])
    sty = {k: stats(bs[k]) for k in SLEEVES}
    worst = {k: min(st(v, k)["ir"] for v in BUCKETS) for k in SLEEVES}
    ewP = [stats(bs["EW PORT"], w)["ir"] for w in W3]; ivP = [stats(bs["Inverse Vol"], w)["ir"] for w in W3]
    ew4P = [stats(bs4["EW PORT"], w)["ir"] for w in W3]; iv4P = [stats(bs4["Inverse Vol"], w)["ir"] for w in W3]
    sP = {k: [stats(bs[k], w)["ir"] for w in W3] for k in SLEEVES}
    chk(all(x > 0 for x in ewP + ivP), "book positive in every period under both constructions")
    chk(all(sty[k]["ir"] > worst[k] for k in SLEEVES), "every strategy lifts above its worst bucket")
    chk(iv["ir"] > ew["ir"] and iv["ret"] > ew["ret"] and iv["mdd"] > ew["mdd"] and abs(iv["vol"] - ew["vol"]) < 0.1, "Inverse Vol is the stronger construction at nearly the same volatility")
    allpos = [t for t in BUCKETS if all(x > 0 for x in per(t, "EW PORT") + per(t, "Inverse Vol"))]
    chk(allpos == ["petroleum", "pen", "ngl"] and all(st(t, "EW PORT")["vol"] > 2 * ew["vol"] for t in allpos), "only Petroleum, Gas and Emissions and NGL are positive in every period, at more than twice the book volatility")
    chk(ewP[0] < ewP[2] < ewP[1] and ewP[2] - ewP[0] < 0.05 and ivP[2] < ivP[0] < ivP[1] and max(ewP[0], ewP[2], ivP[2]) < 0.5 * min(ewP[1], ivP[1]), "weakest periods of the book: P1 under Equal Weight (P3 just above), P3 under Inverse Vol; P2 more than twice as strong as either")
    chk(sP["Momentum"][2] < 0 and sP["CarryMom"][2] < 0 and 0 < sP["Carry"][2] < 0.2 and set(sorted(SLEEVES, key=lambda k: -sP[k][2])[:2]) == {"Skewness", "Value"}, "P3 strategy ranking: Momentum and Carry-Momentum negative, Carry barely positive, Skewness and Value the two best sleeves")
    chk(sP["Value"][0] < 0 and sP["Skewness"][0] < 0 and min(sP[k][0] for k in ("Momentum", "Carry", "CarryMom")) > 0, "Value and Skewness are the only sleeves negative in P1")
    chk(ew["ir"] > ew4["ir"] and iv["ir"] > iv4["ir"] and ew["vol"] < ew4["vol"] and ew["mdd"] > ew4["mdd"] and ewP[0] < ew4P[0] and ewP[2] > ew4P[2], "Skewness lifts IR, cuts volatility and drawdown, moves IR from P1 to P3")
    cb = combined_book()
    chk(abs(stats(cb[("EW", "EW")])["ir"] - ew["ir"]) < 1e-12, "opposite order gives the identical Equal Weight result")
    oth = [stats(cb[k])["ir"] for k in (("EW", "IV"), ("IV", "EW"), ("IV", "IV"))]
    ps = pair_stats()
    best = max(ps, key=lambda p: p["ew"]["ir"]); b2 = sorted(ps, key=lambda p: -p["ew"]["ir"])[1]
    best_iv = max(ps, key=lambda p: p["iv"]["ir"]); b2_iv = sorted(ps, key=lambda p: -p["iv"]["ir"])[1]
    chk(best["name"] == "Petroleum-NGL" and best["ew"]["ir"] > ew["ir"] and best["iv"]["ir"] > iv["ir"], "Petroleum-NGL beats the book on IR")
    chk(best_iv["name"] == "Petroleum-NGL" and b2_iv["name"] == "Gas and Emissions-NGL" and b2["name"] == "Gas and Emissions-NGL" and b2["ew"]["ir"] > ew["ir"] and b2["iv"]["ir"] > iv["ir"], "Petroleum-NGL best under both constructions, Gas and Emissions-NGL second under both and also beats the book")
    neg = [p for p in ps if p["ew"]["ir"] < 0 or p["iv"]["ir"] < 0]
    chk([p["name"] for p in neg] == ["Metals-Precious Metals", "Metals-Agriculture", "Metals-Softs", "Precious Metals-Agriculture", "Precious Metals-Softs", "Agriculture-Softs"] and all(p["ewp"][2] < -0.4 and p["ivp"][2] < -0.25 for p in neg), "the six negative pairs, each clearly negative in P3")
    chk(len([p for p in ps if p["ew"]["ir"] > ew["ir"]]) == 7 and len([p for p in ps if p["iv"]["ir"] > iv["ir"]]) == 4, "seven pairs beat the book under Equal Weight, four under Inverse Vol")
    chk(all({p["a"], p["b"]} & {"ngl", "petroleum", "pen"} for p in ps if p["ew"]["ir"] > ew["ir"] or p["iv"]["ir"] > iv["ir"]), "every pair that beats the book contains NGL, Petroleum or Gas and Emissions")
    bE, bI = bench_corr(bs["EW PORT"]), bench_corr(bs["Inverse Vol"]); b4E, b4I = bench_corr(bs4["EW PORT"]), bench_corr(bs4["Inverse Vol"]); bS = bench_corr(bs["Skewness"])
    chk(bE["Equity"] < 0 and bI["Equity"] < 0 and bE["60/40 Portfolio"] < 0 and bE["Commodity Index"] > 0.15 and abs(b4E["Commodity Index"]) < 0.03 and abs(b4I["Commodity Index"]) < 0.03 and abs(bE["Gold"]) < 0.05 and abs(bE["Fixed Income"]) < 0.1, "benchmark correlations")
    chk(round(bS["Commodity Index"], 2) == 0.41 and round(bS["Equity"], 2) == 0.16 and round(bS["Gold"], 2) == 0.15, "Skewness benchmark correlations")
    Lbl = lambda k: {"Momentum": "Momentum", "Carry": "Carry", "CarryMom": "Carry-Momentum", "Value": "Value", "Skewness": "Skewness"}[k]
    wl = lambda k: ", ".join(f"{I(x)}" for x in [worst[kk] for kk in SLEEVES])
    B = []
    B.append("Diversifying each individual strategy across all seven buckets first (equal-weighted), then combining strategies, lifts every strategy above its worst individual bucket showing: "
             + ", ".join(f"{Lbl(k)} ({line(sty[k])})" for k in SLEEVES[:-1]) + f" and Skewness ({line(sty['Skewness'])}). The worst bucket IRs for the same strategies are {wl(0)}.")
    B.append(f"At the top level, combining those five cross-commodity strategies gives Equal Weight ({line(ew)}) and Inverse Vol ({line(iv)}). Inverse Vol is the stronger construction, with the higher return and IR and the shallower drawdown at nearly the same volatility.")
    B.append(f"The cross-commodity book is positive in every one of the three periods under both constructions (Equal Weight P1 {I(ewP[0])}, P2 {I(ewP[1])}, P3 {I(ewP[2])}; Inverse Vol P1 {I(ivP[0])}, P2 {I(ivP[1])}, P3 {I(ivP[2])}). Among the single buckets only Petroleum, Gas and Emissions and NGL do the same, and all three do so at more than twice the cross-commodity volatility (Equal Weight {V(st('petroleum', 'EW PORT')['vol'])}, {V(st('pen', 'EW PORT')['vol'])} and {V(st('ngl', 'EW PORT')['vol'])} against {V(ew['vol'])}).")
    B.append(f"The weakest periods for the cross-commodity book are P1 under Equal Weight (IR {I(ewP[0])}, with P3 just above at {I(ewP[2])}) and P3 under Inverse Vol (IR {I(ivP[2])}, against {I(ivP[0])} in P1), all still positive but a fraction of the strength shown in P2 ({I(ewP[1])} and {I(ivP[1])}). Within the strategies, P3 is the period in which Momentum ({I(sP['Momentum'][2])}) and Carry-Momentum ({I(sP['CarryMom'][2])}) turn negative and Carry is barely positive ({I(sP['Carry'][2])}); Skewness ({I(sP['Skewness'][2])}) and Value ({I(sP['Value'][2])}) are the best sleeves. In P1 Value ({I(sP['Value'][0])}) and Skewness ({I(sP['Skewness'][0])}) are the only negative ones.")
    B.append(f"Skewness changes the book in three ways. It lifts the full-sample IR (Equal Weight {I(ew4['ir'])} to {I(ew['ir'])}, Inverse Vol {I(iv4['ir'])} to {I(iv['ir'])}) and cuts volatility (Equal Weight {V(ew4['vol'])} to {V(ew['vol'])}) and maximum drawdown ({M(ew4['mdd'])} to {M(ew['mdd'])}); it moves the IR from P1 to P3 (Equal Weight P1 {I(ew4P[0])} to {I(ewP[0])}, P3 {I(ew4P[2])} to {I(ewP[2])}); and it adds commodity beta (see the benchmark correlations below).")
    B.append(f"Combining in the opposite order, each bucket's five sleeves first and then the seven bucket portfolios, gives the identical Equal Weight result (IR {I(ew['ir'])}); the three other weighting combinations give IRs of {I(oth[0])}, {I(oth[1])} and {I(oth[2])} (sleeves Equal Weight / across Inverse Vol; sleeves Inverse Vol / across Equal Weight; Inverse Vol at both stages).")
    B.append(f"Across all twenty-one bucket pairings, Petroleum-NGL is the best-performing combination under both Equal Weight (IR {I(best['ew']['ir'])}) and Inverse Vol (IR {I(best['iv']['ir'])}) even though it is the most correlated pair, with Gas and Emissions-NGL second under both (Equal Weight {I(b2['ew']['ir'])}, Inverse Vol {I(b2['iv']['ir'])}); both beat the seven-bucket book on IR under both constructions (Equal Weight {I(ew['ir'])}, Inverse Vol {I(iv['ir'])}) at {V(best['ew']['vol'])} and {V(b2['ew']['vol'])} Equal Weight volatility against {V(ew['vol'])}. "
             f"Seven pairs beat the book under Equal Weight and four under Inverse Vol, every one of them containing NGL, Petroleum or Gas and Emissions. "
             f"The only pairs with a negative full-sample IR under either construction are the six built from Metals, Precious Metals, Agriculture and Softs alone: " + "; ".join(f"{q['name']} ({I(q['ew']['ir'])} / {I(q['iv']['ir'])})" for q in neg) + f", and each is clearly negative in P3 under both constructions (Equal Weight {', '.join(I(q['ewp'][2]) for q in neg)}; Inverse Vol {', '.join(I(q['ivp'][2]) for q in neg)}).")
    B.append(f"Benchmarked against traditional assets, the five-sleeve cross-commodity book still diversifies equity and bonds but is not free of commodity beta: it correlates negatively with Equity (Equal Weight {N(bE['Equity'])}, Inverse Vol {N(bI['Equity'])}) and with a traditional 60/40 portfolio ({N(bE['60/40 Portfolio'])}, {N(bI['60/40 Portfolio'])}), stays close to zero against Fixed Income ({N(bE['Fixed Income'])}, {N(bI['Fixed Income'])}) and Gold ({N(bE['Gold'])}, {N(bI['Gold'])}), "
             f"but is positively correlated with a passive Commodity Index ({N(bE['Commodity Index'])}, {N(bI['Commodity Index'])}; {N(b4E['Commodity Index'])} and {N(b4I['Commodity Index'])} without Skewness). The change comes from Skewness, which correlates {N(bS['Commodity Index'])} with the Commodity Index, {N(bS['Equity'])} with Equity and {N(bS['Gold'])} with Gold.")
    return B, dict(ew=ew, iv=iv, ew4=ew4, iv4=iv4, ewP=ewP, ivP=ivP, sty=sty, bE=bE, bI=bI, b4E=b4E, b4I=b4I, bS=bS, oth=oth, best=best, b2=b2, best_iv=best_iv, b2_iv=b2_iv, neg=neg, worst=worst, sP=sP)
