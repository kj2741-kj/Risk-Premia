from facts3 import *
from power_facts import stp, EW_P

W3 = ("p1", "p2", "p3")
NW = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven"}


def _c(x):
    """Unsigned-looking correlation with a minus for negatives (v3 convention), no negative zero."""
    return "0.00" if abs(round(x, 2)) == 0 else f"{x:.2f}"


def book():
    return bystyle(), bystyle4()


def _ir(r):
    r = r.dropna(); ret = (np.exp(252 * r.mean()) - 1) * 100; vol = np.expm1(r).std(ddof=1) * np.sqrt(252) * 100
    return ret / vol


def six_bucket_book():
    """The six-bucket book (no US Power) on the SAME window as the seven-bucket book, to separate the effect of adding Power from the effect of the shorter window."""
    sdf = pd.DataFrame({k: ew_intersection([CS[t][k].dropna() for t in BUCKETS]) for k in SLEEVES}).dropna()
    sdf["EW PORT"] = ew_intersection([sdf[k] for k in SLEEVES]); sdf["Inverse Vol"] = inverse_vol(sdf[SLEEVES])
    return sdf


def corr8():
    out = {}
    cw = {t: corr_within(t) for t in BOOK}
    lab = {t: SHORT[t] for t in BOOK}
    sl = {t: cw[t].loc[SLEEVES, "EW PORT"] for t in BOOK}
    chk(all(sl[t].rank()["Value"] == 1 and sl[t].rank()["Skewness"] == 2 for t in BUCKETS), "Value lowest and Skewness second lowest correlation with EW PORT in the six research buckets")
    chk(sl["power"].rank()["Skewness"] == 1 and sl["power"].rank()["Value"] == 2, "US Power: Skewness lowest, Value second lowest")
    pos_value = [t for t in BOOK if cw[t].loc["Value", "EW PORT"] > 0]
    chk(pos_value == ["pen", "ngl", "agri", "power"], "Value positively correlated with the portfolio in Gas and Emissions, NGL, Agriculture and US Power")
    mc = {t: cw[t].loc["Momentum", "Carry"] for t in BOOK}; cc = {t: cw[t].loc["Carry", "CarryMom"] for t in BOOK}; mcm = {t: cw[t].loc["Momentum", "CarryMom"] for t in BOOK}
    top_mc = [t for t in BOOK if mc[t] > cc[t] and mc[t] > mcm[t]]; top_cc = [t for t in BOOK if cc[t] > mc[t] and cc[t] > mcm[t]]
    chk(top_mc == ["petroleum", "ngl", "agri"] and top_cc == ["metals", "pen", "precious", "power"], "closest base pair by bucket")
    vm = {t: cw[t].loc["Value", "Momentum"] for t in BOOK}
    chk(all(x < 0 for x in vm.values()), "Value negatively correlated with Momentum in every bucket")
    sv = {t: cw[t].loc["Skewness", "Value"] for t in BOOK}
    chk([t for t in BOOK if sv[t] > 0] == ["ngl"] and min(sv, key=sv.get) == "precious", "Skewness-Value negative in six buckets, most in Precious Metals, positive in NGL")
    sm = {t: cw[t].loc["Skewness", "Momentum"] for t in BOOK}; sc = {t: cw[t].loc["Skewness", "Carry"] for t in BOOK}
    chk(min(sm, key=sm.get) == "ngl" and min(sc, key=sc.get) == "ngl" and max(abs(x) for t, x in list(sm.items()) + list(sc.items()) if t != "ngl") < 0.21, "Skewness with Momentum and Carry near zero except NGL")
    ivw = [cw[t].loc["Inverse Vol", "EW PORT"] for t in BOOK]
    chk(round(min(ivw), 2) == 0.95 and round(max(ivw), 2) == 0.99, "Inverse Vol versus EW PORT 0.95 to 0.99")
    j = lambda d, ks: ", ".join(f"{N(d[t])} in {lab[t]}" for t in ks[:-1]) + f" and {N(d[ks[-1]])} in {lab[ks[-1]]}"
    vew = {t: cw[t].loc["Value", "EW PORT"] for t in BOOK}; sew = {t: cw[t].loc["Skewness", "EW PORT"] for t in BOOK}
    out["within"] = [
        f"In the six research buckets Value is the least correlated sleeve with its own EW PORT, correlating at {j(vew, BUCKETS)}, and Skewness the second least ({j(sew, BUCKETS)}). "
        f"The two sleeves with the weakest links to the portfolio are the two that are not built on trend or curve slope, which is consistent with, not a test of, their acting as diversifiers. In Gas and Emissions, NGL and Agriculture, where Value is positively correlated with the portfolio, it is still the lowest of the five. "
        f"US Power (measured from 2017, when all its sleeves are live) is the one bucket where the order is reversed: Skewness is the least correlated ({N(sew['power'])}) and Value the second least ({N(vew['power'])}).",
        f"Momentum and Carry are the most correlated pair of base strategies in Petroleum ({N(mc['petroleum'])}), NGL ({N(mc['ngl'])}) and Agriculture ({N(mc['agri'])}), consistent with a common driver behind the two signals (not tested here). Metals, Gas and Emissions, Precious Metals and US Power break this pattern: in all four, Carry and Carry-Momentum are the closest pair ({N(cc['metals'])} in Metals, {N(cc['pen'])} in Gas and Emissions, {N(cc['precious'])} in Precious Metals, {N(cc['power'])} in US Power). "
        f"Value is negatively correlated with Momentum in all seven buckets ({j(vm, BOOK)}).",
        f"Skewness pairs differently by bucket. With Value it is negative in six buckets and strongest in Precious Metals ({j(sv, BOOK)}); in NGL it is the exception. With Momentum and Carry it is near zero (no reading above 0.20 in magnitude) except in NGL, where it is {N(sm['ngl'])} and {N(sc['ngl'])}.",
        f"Inverse Vol tracks its own EW PORT closely everywhere, correlating between {U(min(ivw))} and {U(max(ivw))} across all seven buckets, expected since both portfolios are built from the same five sleeves and differ only in how they are weighted.",
    ]
    # cross-bucket (common dates from January 2015)
    ser = SLEEVES + ["EW PORT", "Inverse Vol"]; cx = {k: corr_cross(k) for k in ser}
    top = {k: max(PAIR_ORDER, key=lambda p: cx[k].loc[p[0], p[1]]) for k in ser}
    chk(all(top[k] == ("petroleum", "ngl") for k in ser), "Petroleum-NGL is the most correlated pair for all seven series")
    pn = {k: cx[k].loc["petroleum", "ngl"] for k in ser}
    ewc = cx["EW PORT"]
    order = sorted(PAIR_ORDER, key=lambda p: -ewc.loc[p[0], p[1]])
    chk({order[1], order[2], order[3]} == {("pen", "ngl"), ("petroleum", "pen"), ("metals", "precious")} and order[1] == ("pen", "ngl"), "EW PORT: Gas and Emissions-NGL second; Petroleum-Gas and Emissions and Metals-Precious Metals follow")
    sec = {k: sorted(PAIR_ORDER, key=lambda p: -cx[k].loc[p[0], p[1]])[1] for k in ser}
    thr = {k: sorted(PAIR_ORDER, key=lambda p: -cx[k].loc[p[0], p[1]])[2] for k in ser}
    chk(sec["Momentum"] == ("metals", "precious") and sec["Value"] == ("metals", "precious") and sec["Skewness"] == ("metals", "precious") and sec["Carry"] == ("petroleum", "pen") and sec["CarryMom"] == ("petroleum", "agri"), "second-place pairs")
    avg = {k: float(np.mean([abs(cx[k].loc[a, b]) for a, b in PAIR_ORDER])) for k in ser}
    chk(min(avg, key=avg.get) == "CarryMom" and sorted(avg.values())[1] > 0.065, "Carry-Momentum has the lowest average cross-bucket correlation")
    cm_vals = [cx["CarryMom"].loc[a, b] for a, b in PAIR_ORDER]
    n_small = sum(1 for x in cm_vals if abs(x) < 0.10)
    chk(max(cm_vals) == pn["CarryMom"] and round(max(cm_vals), 2) == 0.35 and n_small == len(cm_vals) - 1, f"Carry-Momentum: all but Petroleum-NGL below 0.10 ({n_small} of {len(cm_vals)})")
    pw = {b: ewc.loc["power", b] for b in BUCKETS}
    chk(max(abs(x) for x in pw.values()) < 0.06, "US Power is uncorrelated with every other bucket")
    ge = {b: ewc.loc["pen", b] for b in BOOK if b != "pen"}
    chk(abs(ge["metals"]) < 0.01 and abs(ge["precious"]) < 0.05 and abs(ge["agri"]) < 0.01 and ge["ngl"] == max(ge.values()), "Gas and Emissions is uncorrelated with Metals, Precious Metals and Agriculture")
    out["cross"] = [
        f"Petroleum and NGL are the most correlated cross-bucket pair for all seven series types tracked: Momentum ({U(pn['Momentum'])}), Carry ({U(pn['Carry'])}), Carry-Momentum ({U(pn['CarryMom'])}), Value ({U(pn['Value'])}), Skewness ({U(pn['Skewness'])}), EW PORT ({U(pn['EW PORT'])}) and Inverse Vol ({U(pn['Inverse Vol'])}), consistent with both trading the same hydrocarbon complex (the Naphtha swap, priced off crude, is part of NGL). "
        f"The cross-bucket figures use the common dates of all seven buckets, from January 2015.",
        f"Gas and Emissions and US Power are close to uncorrelated with everything except the hydrocarbon buckets: the EW PORT correlation of Gas and Emissions is {_c(ge['ngl'])} with NGL and {_c(ge['petroleum'])} with Petroleum, and {_c(ge['metals'])} with Metals, {_c(ge['precious'])} with Precious Metals and {_c(ge['agri'])} with Agriculture, while US Power stays between {_c(min(pw.values()))} and {_c(max(pw.values()))} with every other bucket. "
        f"Metals-Precious Metals is the second most correlated pair for Momentum ({U(cx['Momentum'].loc['metals', 'precious'])}), Value ({U(cx['Value'].loc['metals', 'precious'])}) and Skewness ({U(cx['Skewness'].loc['metals', 'precious'])}); for Carry the second place is Petroleum-Gas and Emissions ({U(cx['Carry'].loc['petroleum', 'pen'])}) and for Carry-Momentum Petroleum-Agriculture ({U(cx['CarryMom'].loc['petroleum', 'agri'])}).",
        f"Carry-Momentum has the lowest cross-bucket correlations of the seven series: its correlations to the same strategy in other buckets average just {U(avg['CarryMom'])} in magnitude (Carry {U(avg['Carry'])}; the other five range {U(sorted(avg.values())[1])} to {U(max(avg.values()))}), and {n_small} of its {len(cm_vals)} pairwise readings are below 0.10, the exception being Petroleum-NGL ({U(pn['CarryMom'])}).",
    ]
    ps = pair_stats()
    rows = sorted(ps, key=lambda p: -p["ew"]["ir"])
    out["pair_rows"] = [[p["name"], _c(p["corr"]), I(p["ew"]["ir"]), I(p["iv"]["ir"])] for p in rows]
    out["pairs"] = ps
    best = rows[0]
    chk(best["name"] == "Petroleum-NGL" and max(ps, key=lambda p: p["iv"]["ir"])["name"] == "Petroleum-NGL" and rows[1]["name"] == "Gas and Emissions-NGL", "Petroleum-NGL best under both, Gas and Emissions-NGL second under Equal Weight")
    worst = min(ps, key=lambda p: p["ew"]["ir"]); worst_iv = min(ps, key=lambda p: p["iv"]["ir"])
    chk(worst["name"] == "Precious Metals-Agriculture" and worst_iv["name"] == "Precious Metals-Agriculture", "Precious Metals-Agriculture lowest under both")
    pw_pairs = [p for p in ps if "US Power" in p["name"]]
    chk(len(pw_pairs) == 6 and all(p["ewp"][0] is not None and p["ivp"][0] is None for p in pw_pairs), "six Power pairs; their Inverse Vol series have no P1")
    chk(max(abs(ewc.loc[a, b]) for a, b in PAIR_ORDER if (a, b) not in (("petroleum", "ngl"), ("pen", "ngl"), ("petroleum", "pen"), ("metals", "precious"))) <= 0.095, "every other pair at or below 0.09")
    out["impl_intro"] = (f"The Cross-Pair tab shows all 21 bucket pairs. Under the EW PORT measure, Petroleum-NGL ({U(ewc.loc['petroleum', 'ngl'])}) is by far the most correlated pair; the next three are Gas and Emissions-NGL ({U(ewc.loc['pen', 'ngl'])}), Petroleum-Gas and Emissions ({U(ewc.loc['petroleum', 'pen'])}) and Metals-Precious Metals ({U(ewc.loc['metals', 'precious'])}), and every other pair is at or below 0.09 in magnitude. "
                         f"The table below sets each pair's EW PORT correlation beside its full-sample IR under Equal Weight and Inverse Vol. The six pairs that include US Power start in January 2015 under Equal Weight and in March 2017 under Inverse Vol, so their figures cover shorter windows than those of the other fifteen pairs (which start in 2012) and the two columns are not comparable for them.")
    pw_names = {p["name"]: p for p in pw_pairs}
    byn = {p["name"]: p for p in ps}
    others_ = [b for b in BOOK if b not in ("power", "ngl")]
    chk(all(byn[f"{SHORT[b]}-US Power"]["ew"]["ir"] < byn[f"{SHORT[b]}-NGL"]["ew"]["ir"] if f"{SHORT[b]}-NGL" in byn else byn[f"{SHORT[b]}-US Power"]["ew"]["ir"] < byn[f"NGL-{SHORT[b]}"]["ew"]["ir"] for b in others_), "every Power pairing earns less than the same partner paired with NGL")
    chk(pw_names["NGL-US Power"]["ew"]["ir"] < min(byn[n]["ew"]["ir"] for n in ("Petroleum-NGL", "Gas and Emissions-NGL", "Metals-NGL", "NGL-Agriculture", "NGL-Precious Metals")), "NGL-US Power earns less than NGL with any other bucket")
    out["impl_close"] = (f"Correlation and standalone performance are separate questions. Held on its own, Petroleum-NGL, the most correlated pair, produces the highest full-sample IR of the 21 pairs under both constructions (Equal Weight {I(best['ew']['ir'])}, Inverse Vol {I(best['iv']['ir'])}), "
                         f"while Precious Metals-Agriculture produces the lowest under both (Equal Weight {I(worst['ew']['ir'])}, Inverse Vol {I(worst['iv']['ir'])}). Two individually strong books can still make a poor diversification pairing simply because they move together. "
                         f"The pairs with US Power show the reverse: Power is uncorrelated with every partner (EW PORT correlation {_c(min(pw.values()))} to {_c(max(pw.values()))}) yet every Equal Weight pairing with it earns less than the same partner paired with NGL (for example Metals-US Power {I(pw_names['Metals-US Power']['ew']['ir'])} against Metals-NGL {I(byn['Metals-NGL']['ew']['ir'])}), and NGL-US Power ({I(pw_names['NGL-US Power']['ew']['ir'])}) earns less than NGL paired with any other bucket, because Power earns little per unit of its own risk (an IR of {I(stp(EW_P)['ir'])} at a volatility of {V(stp(EW_P)['vol'])} from 2017).")
    return out


def cross8():
    bs, bs4 = book()
    b6 = six_bucket_book()
    ew, iv = stats(bs["EW PORT"]), stats(bs["Inverse Vol"])
    ew4, iv4 = stats(bs4["EW PORT"]), stats(bs4["Inverse Vol"])
    sty = {k: stats(bs[k]) for k in SLEEVES}
    worst = {k: min(st(v, k)["ir"] for v in BUCKETS) for k in SLEEVES}
    ewP = [stats(bs["EW PORT"], w)["ir"] for w in W3]; ivP = [stats(bs["Inverse Vol"], w)["ir"] for w in W3]
    ew4P = [stats(bs4["EW PORT"], w)["ir"] for w in W3]; iv4P = [stats(bs4["Inverse Vol"], w)["ir"] for w in W3]
    sP = {k: [stats(bs[k], w)["ir"] for w in W3] for k in SLEEVES}
    start = bs.index[0]
    chk(str(start.date()) == "2015-01-07" and bs.index[-1] == pd.Timestamp("2026-09-30"), "the seven-bucket book runs from 2015-01-07 to 2026-09-30")
    chk(all(x > 0 for x in ewP + ivP), "book positive in every period under both constructions")
    chk(ewP[0] < min(ewP[1:]) and ewP[0] < 0.2 and ivP[2] < ivP[0] < ivP[1] and ivP[2] == min(ivP), "weakest period: P1 for Equal Weight, P3 for Inverse Vol")
    chk(all(sty[k]["ir"] > worst[k] for k in SLEEVES), "every strategy lifts above its worst individual bucket")
    chk(iv["ir"] > ew["ir"] and iv["ret"] > ew["ret"] and abs(iv["vol"] - ew["vol"]) < 0.2 and iv["mdd"] < ew["mdd"], "Inverse Vol higher return and IR at nearly the same volatility; its drawdown is slightly deeper")
    neg_p = {k: [w for w, x in zip(W3, sP[k]) if x < 0] for k in SLEEVES}
    chk(neg_p == {"Momentum": ["p1"], "Carry": ["p3"], "CarryMom": ["p3"], "Value": ["p1", "p2"], "Skewness": ["p1"]}, f"negative periods by strategy {neg_p}")
    chk(sP["Skewness"][2] == max(sP[k][2] for k in SLEEVES) and sP["Value"][2] > 0.4, "P3: Skewness and Value the best sleeves")
    chk(ew["ir"] > ew4["ir"] and iv["ir"] > iv4["ir"] and ew["vol"] < ew4["vol"] and ew["mdd"] > ew4["mdd"] and ewP[0] < ew4P[0] and ewP[2] > ew4P[2], "Skewness lifts IR, cuts volatility and drawdown, moves IR from P1 to P3")
    # US Power's effect on the book: same window, six buckets against seven
    s6 = {k: stats(b6[k].loc[start:]) if False else None for k in ()}
    def win(r):
        r = r.loc[start:].dropna(); ret = (np.exp(252 * r.mean()) - 1) * 100; vol = np.expm1(r).std(ddof=1) * np.sqrt(252) * 100
        cum = np.exp(r.cumsum()); return dict(ret=ret, vol=vol, mdd=(cum / cum.cummax() - 1).min() * 100, ir=ret / vol)
    e6, i6 = win(b6["EW PORT"]), win(b6["Inverse Vol"])
    chk(round(e6["ir"], 3) == 1.085 and round(i6["ir"], 3) == 1.135 and e6["ir"] > ew["ir"] and i6["ir"] > iv["ir"] and e6["vol"] < ew["vol"] and e6["mdd"] < ew["mdd"] and i6["mdd"] < iv["mdd"], "adding US Power lowers the IR, raises the volatility and makes the drawdown shallower")
    cum_ = [PORT[t][0].dropna().cumsum() for t in BOOK]; idx_ = cum_[0].index
    for c_ in cum_[1:]: idx_ = idx_.intersection(c_.index)
    A = pd.DataFrame({t: c_.reindex(idx_.sort_values()).diff() for t, c_ in zip(BOOK, cum_)}).dropna().loc["2017-03-01":]
    cov = A.cov().values * 252; w_ = np.ones(len(BOOK)) / len(BOOK); rc = w_ * (cov @ w_) / (w_ @ cov @ w_)
    share_pw = float(rc[BOOK.index("power")]) * 100; bvol = {t: float(np.sqrt(cov[i, i]) * 100) for i, t in enumerate(BOOK)}
    chk(round(share_pw) == 41 and round(bvol["power"]) == 30 and max(bvol[t] for t in BUCKETS) < 19.5, f"US Power carries {share_pw:.1f}% of the equal-weight bucket variance at a 1/7 weight")
    cb = combined_book()
    com = max(v.dropna().index[0] for v in cb.values())
    cbw = {k: _ir(v.loc[com:]) for k, v in cb.items()}
    chk(str(com.date()) == "2017-03-24" and round(cbw[("EW", "EW")], 2) == 1.18 and round(cbw[("EW", "IV")], 2) == 1.12 and round(cbw[("IV", "EW")], 2) == 1.23 and round(cbw[("IV", "IV")], 2) == 1.11, "two-stage combinations on their common window")
    ps = pair_stats()
    best = max(ps, key=lambda p: p["ew"]["ir"]); b2 = sorted(ps, key=lambda p: -p["ew"]["ir"])[1]
    chk(best["name"] == "Petroleum-NGL" and best["ew"]["ir"] > ew["ir"] and best["iv"]["ir"] > iv["ir"], "Petroleum-NGL beats the book on IR")
    neg = [p for p in ps if p["ew"]["ir"] < 0 or p["iv"]["ir"] < 0]
    chk([p["name"] for p in neg] == ["Metals-Agriculture", "Metals-Precious Metals", "Precious Metals-Agriculture"] or [p["name"] for p in neg] == ["Metals-Precious Metals", "Metals-Agriculture", "Precious Metals-Agriculture"], "the three negative pairs")
    neg = sorted(neg, key=lambda p: ["Metals-Precious Metals", "Metals-Agriculture", "Precious Metals-Agriculture"].index(p["name"]))
    chk(all(p["ewp"][2] < -0.4 and p["ivp"][2] < -0.4 for p in neg), "each negative pair clearly negative in P3")
    pw_pairs = {p["name"]: p for p in ps if "US Power" in p["name"]}
    chk(all(p["ew"]["ir"] > 0 for p in pw_pairs.values()) and max(p["ew"]["vol"] for p in pw_pairs.values()) < 17 and min(p["ew"]["vol"] for p in pw_pairs.values()) > 14, "every Power pair positive, volatility 14% to 17%")
    bE, bI = bench_corr(bs["EW PORT"]), bench_corr(bs["Inverse Vol"]); b4E, b4I = bench_corr(bs4["EW PORT"]), bench_corr(bs4["Inverse Vol"]); bS = bench_corr(bs["Skewness"])
    chk(bE["Equity"] < 0 and bI["Equity"] < 0 and bE["60/40 Portfolio"] < 0 and round(bE["Commodity Index"], 2) == 0.18 and round(b4E["Commodity Index"], 2) == 0.04, "benchmark correlations")
    chk(round(bS["Commodity Index"], 2) == 0.35 and round(bS["Equity"], 2) == 0.12 and round(bS["Gold"], 2) == 0.09, "Skewness benchmark correlations")
    Lbl = lambda k: {"Momentum": "Momentum", "Carry": "Carry", "CarryMom": "Carry-Momentum", "Value": "Value", "Skewness": "Skewness"}[k]
    wl = ", ".join(f"{I(worst[k])}" for k in SLEEVES)
    B = []
    B.append(f"The cross-commodity book combines seven buckets (the six research buckets and US Power) on their common dates, which start on 7 January 2015 with the US Power data, so every figure in this section covers January 2015 to 30 September 2026 and its P1 is 2015-2016. "
             f"Diversifying each individual strategy across the seven buckets first (equal-weighted), then combining strategies, lifts every strategy above its worst individual bucket showing: "
             + ", ".join(f"{Lbl(k)} ({line(sty[k])})" for k in SLEEVES[:-1]) + f" and Skewness ({line(sty['Skewness'])}). The worst bucket IRs for the same strategies, each over the bucket's own window, are {wl}.")
    B.append(f"At the top level, combining those five cross-commodity strategies gives Equal Weight ({line(ew)}) and Inverse Vol ({line(iv)}). Inverse Vol has the higher return and IR at nearly the same volatility; its maximum drawdown is slightly deeper ({M(iv['mdd'])} against {M(ew['mdd'])}).")
    B.append(f"The book is positive in every one of the three periods under both constructions (Equal Weight P1 {I(ewP[0])}, P2 {I(ewP[1])}, P3 {I(ewP[2])}; Inverse Vol P1 {I(ivP[0])}, P2 {I(ivP[1])}, P3 {I(ivP[2])}), but the profile is uneven: P2 (2017-2021) carries the result, the Equal Weight P1 (2015-2016) is close to zero, and P3 is the weakest Inverse Vol period. "
             f"Within the strategies, Momentum is negative in P1 ({I(sP['Momentum'][0])}), Carry ({I(sP['Carry'][2])}) and Carry-Momentum ({I(sP['CarryMom'][2])}) in P3, Value in P1 and P2 ({I(sP['Value'][0])} and {I(sP['Value'][1])}) and Skewness in P1 ({I(sP['Skewness'][0])}); in P3 Skewness ({I(sP['Skewness'][2])}) and Value ({I(sP['Value'][2])}) are the best sleeves.")
    B.append(f"US Power lowers the IR of the book but improves its drawdown. On the same window (from January 2015) the six-bucket book earns an Equal Weight IR of {I(e6['ir'])} and an Inverse Vol IR of {I(i6['ir'])} at a volatility of {V(e6['vol'])}; adding US Power moves them to {I(ew['ir'])} and {I(iv['ir'])}, raises the volatility to {V(ew['vol'])} and makes the maximum drawdown shallower ({M(e6['mdd'])} to {M(ew['mdd'])} for Equal Weight, {M(i6['mdd'])} to {M(iv['mdd'])} for Inverse Vol). "
             f"The reason is risk concentration rather than correlation: Power is uncorrelated with every other bucket, but with a volatility of {bvol['power']:.0f}% (the other buckets {min(bvol[t] for t in BUCKETS):.0f}% to {max(bvol[t] for t in BUCKETS):.0f}%) it accounts for {share_pw:.0f}% of the variance of an equal-bucket-weight book at a weight of one seventh (from March 2017, when all five Power sleeves are live), against an IR of {I(stp(EW_P)['ir'])}.")
    B.append(f"Skewness changes the book in three ways. It lifts the full-sample IR (Equal Weight {I(ew4['ir'])} to {I(ew['ir'])}, Inverse Vol {I(iv4['ir'])} to {I(iv['ir'])}) and cuts volatility (Equal Weight {V(ew4['vol'])} to {V(ew['vol'])}) and maximum drawdown ({M(ew4['mdd'])} to {M(ew['mdd'])}); it moves the IR from P1 to P3 (Equal Weight P1 {I(ew4P[0])} to {I(ewP[0])}, P3 {I(ew4P[2])} to {I(ewP[2])}); and it adds commodity beta (see the benchmark correlations below).")
    chk(abs(stats(cb[("EW", "EW")])["ir"] - ew["ir"]) < 0.002 and I(stats(cb[("EW", "EW")])["ir"]) == I(ew["ir"]), "the opposite order gives the same Equal Weight IR to two decimals")
    B.append(f"Combining in the opposite order, each bucket's five sleeves first and then the seven bucket portfolios, gives the same Equal Weight result (IR {I(stats(cb[('EW', 'EW')])['ir'])}). The four weighting combinations start on different dates, because the Inverse Vol series that include US Power need its Value sleeve (flat until December 2016) and 63 days of volatility; on their common window from {com.day} {com.strftime('%B %Y')} they give IRs of {I(cbw[('EW', 'EW')])} (sleeves Equal Weight, across Equal Weight), {I(cbw[('EW', 'IV')])} (sleeves Equal Weight, across Inverse Vol), {I(cbw[('IV', 'EW')])} (sleeves Inverse Vol, across Equal Weight) and {I(cbw[('IV', 'IV')])} (Inverse Vol at both stages).")
    nglpw = pw_pairs["NGL-US Power"]; ptpw = pw_pairs["Petroleum-US Power"]
    B.append(f"Across all 21 bucket pairings, Petroleum-NGL is the best-performing combination under both constructions (Equal Weight {I(best['ew']['ir'])}, Inverse Vol {I(best['iv']['ir'])}) even though it is the most correlated pair, followed by Gas and Emissions-NGL ({I(b2['ew']['ir'])} and {I(b2['iv']['ir'])}); both beat the seven-bucket book on IR (Equal Weight {I(ew['ir'])}, Inverse Vol {I(iv['ir'])}) at {V(best['ew']['vol'])} and {V(b2['ew']['vol'])} volatility against {V(ew['vol'])}. "
             f"The only pairs with a negative full-sample IR under either construction are the three built from Metals, Precious Metals and Agriculture alone: Metals-Precious Metals ({I(neg[0]['ew']['ir'])} / {I(neg[0]['iv']['ir'])}), Metals-Agriculture ({I(neg[1]['ew']['ir'])} / {I(neg[1]['iv']['ir'])}) and Precious Metals-Agriculture ({I(neg[2]['ew']['ir'])} / {I(neg[2]['iv']['ir'])}), and each is clearly negative in P3 under both constructions (Equal Weight {I(neg[0]['ewp'][2])}, {I(neg[1]['ewp'][2])}, {I(neg[2]['ewp'][2])}; Inverse Vol {I(neg[0]['ivp'][2])}, {I(neg[1]['ivp'][2])}, {I(neg[2]['ivp'][2])}). "
             f"The six pairs with US Power are all positive but modest under Equal Weight ({I(min(p['ew']['ir'] for p in pw_pairs.values()))} to {I(max(p['ew']['ir'] for p in pw_pairs.values()))}) at volatilities of {V(min(p['ew']['vol'] for p in pw_pairs.values()))} to {V(max(p['ew']['vol'] for p in pw_pairs.values()))}; the best are NGL-US Power ({I(nglpw['ew']['ir'])}) and Petroleum-US Power ({I(ptpw['ew']['ir'])}).")
    B.append(f"Benchmarked against traditional assets, the five-sleeve cross-commodity book still diversifies equity and bonds but is not free of commodity beta: it correlates negatively with Equity (Equal Weight {N(bE['Equity'])}, Inverse Vol {N(bI['Equity'])}) and with a traditional 60/40 portfolio ({N(bE['60/40 Portfolio'])}, {N(bI['60/40 Portfolio'])}), stays close to zero against Fixed Income ({N(bE['Fixed Income'])}, {N(bI['Fixed Income'])}) and Gold ({N(bE['Gold'])}, {N(bI['Gold'])}), "
             f"but is positively correlated with a passive Commodity Index ({N(bE['Commodity Index'])}, {N(bI['Commodity Index'])}; {N(b4E['Commodity Index'])} and {N(b4I['Commodity Index'])} without Skewness). The change comes from Skewness, which correlates {N(bS['Commodity Index'])} with the Commodity Index, {N(bS['Equity'])} with Equity and {N(bS['Gold'])} with Gold.")
    return B, dict(ew=ew, iv=iv, ew4=ew4, iv4=iv4, ewP=ewP, ivP=ivP, sty=sty, bE=bE, bI=bI, b4E=b4E, b4I=b4I, bS=bS, best=best, b2=b2, neg=neg, worst=worst, sP=sP, e6=e6, i6=i6, share_pw=share_pw, bvol=bvol, cbw=cbw, com=com)
