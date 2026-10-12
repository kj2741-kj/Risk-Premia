from facts3 import *

CLS5 = ["metals", "energy", "ngl", "precious", "agri"]


def correlation():
    cw = {v: corr_within(v) for v in CLS5}
    blocks = [("h2", "Correlation Analysis"), ("h3", "Within-Asset-Class Correlation")]
    B = blocks.append
    vew = {v: cw[v].loc["Value", "EW PORT"] for v in CLS5}
    for v in CLS5:
        chk(vew[v] == min(cw[v].loc[k, "EW PORT"] for k in SLEEVES), f"Value least correlated with EW in {v}")
        second = sorted(SLEEVES, key=lambda k: cw[v].loc[k, "EW PORT"])[1]
        chk(second == "Skewness", f"Skewness second least correlated with EW in {v}")
    sew = {v: cw[v].loc["Skewness", "EW PORT"] for v in CLS5}
    chk(vew["agri"] > 0 and vew["ngl"] > 0, "Value positive with EW in NGL and Agri")
    top = {}
    for v in CLS5:
        pairs = {(x, y): cw[v].loc[x, y] for i, x in enumerate(SLEEVES) for y in SLEEVES[i + 1:]}
        top[v] = max(pairs, key=pairs.get)
    chk(all(top[v] == ("Momentum", "Carry") for v in ("energy", "ngl", "agri")) and all(top[v] == ("Carry", "CarryMom") for v in ("metals", "precious")), "closest base pairs")
    vm = {v: cw[v].loc["Value", "Momentum"] for v in CLS5}
    chk(all(x < 0 for x in vm.values()), "Value negative with Momentum everywhere")
    ivew = [cw[v].loc["Inverse Vol", "EW PORT"] for v in CLS5]
    sv = {v: cw[v].loc["Skewness", "Value"] for v in CLS5}
    chk(sv["precious"] == min(sv.values()) and sv["ngl"] > 0 and all(sv[v] < 0 for v in ("metals", "energy", "precious", "agri")), "Skewness-Value pattern")
    smom = {v: cw[v].loc["Skewness", "Momentum"] for v in CLS5}; scar = {v: cw[v].loc["Skewness", "Carry"] for v in CLS5}
    chk(smom["ngl"] == min(smom.values()) and scar["ngl"] == min(scar.values()), "Skewness most negative with Momentum and Carry in NGL")
    L = lambda d: f"{N(d['metals'])} in Metals, {N(d['energy'])} in Energy, {N(d['ngl'])} in NGL, {N(d['precious'])} in Precious Metals and {N(d['agri'])} in Agriculture"
    B(("b", f"Value is the least correlated sleeve with its own EW PORT in every asset class, correlating at {L(vew)}. Skewness is the second least correlated in every class ({L(sew)}), so the two sleeves with the weakest links to the portfolio are the two that are not driven by trend or curve slope. "
            f"In NGL and Agriculture, where Value is positively correlated with the portfolio, it is still the lowest of the five."))
    B(("b", f"Momentum and Carry are the most correlated pair of base strategies in Energy ({N(cw['energy'].loc['Momentum', 'Carry'])}), NGL ({N(cw['ngl'].loc['Momentum', 'Carry'])}) and Agriculture ({N(cw['agri'].loc['Momentum', 'Carry'])}), both moving with the same underlying trend signal. "
            f"Metals and Precious Metals each break this pattern: in both, Carry and Carry-Momentum are the closest pair ({N(cw['metals'].loc['Carry', 'CarryMom'])} in Metals, {N(cw['precious'].loc['Carry', 'CarryMom'])} in Precious Metals). "
            f"Value is negatively correlated with Momentum in all five asset classes ({L(vm).replace('in Metals', 'Metals').replace('in Energy', 'Energy').replace('in NGL', 'NGL').replace('in Precious Metals', 'Precious Metals').replace('in Agriculture', 'Agriculture')})."))
    B(("b", f"Skewness pairs differently by asset class. With Value it is negative in four classes and strongest in Precious Metals ({L(sv)}); in Precious Metals this is because Value shorts the metals that have rallied while Skewness stays long them. "
            f"With Momentum and Carry it is mostly near zero or mildly negative, and most negative in NGL ({N(smom['ngl'])} and {N(scar['ngl'])}); in Precious Metals it is positive with Carry ({N(scar['precious'])})."))
    B(("b", f"Inverse Vol tracks its own EW PORT closely everywhere, correlating between {U(min(ivew))} and {U(max(ivew))} across all five asset classes, expected since both portfolios are built from the same five sleeves and differ only in how they are weighted."))
    B(("h3", "Cross-Commodity Correlation"))
    cc = {k: corr_cross(k) for k in SER7}
    pr = lambda k: sorted(((a, b) for a, b in combinations(CLS5, 2)), key=lambda ab: -cc[k].loc[ab[0], ab[1]])
    for k in SER7:
        chk(pr(k)[0] == ("energy", "ngl"), f"Energy-NGL most correlated for {k}")
    chk(all(pr(k)[1] == ("metals", "precious") for k in ("Momentum", "Value", "Skewness", "EW PORT", "Inverse Vol")), "Metals-Precious second")
    chk(pr("Carry")[1] == ("metals", "ngl") and pr("CarryMom")[1] == ("energy", "agri"), "second places for Carry and CarryMom")
    g = lambda k, a, b: cc[k].loc[a, b]
    avgabs = {k: float(np.mean([abs(cc[k].loc[a, b]) for a, b in combinations(CLS5, 2)])) for k in SER7}
    chk(min(avgabs, key=avgabs.get) == "CarryMom" and sorted(avgabs, key=avgabs.get)[1] == "Carry", "CarryMom most diversifying, Carry next")
    mxcm = max(abs(cc["CarryMom"].loc[a, b]) for a, b in combinations(CLS5, 2))
    others = sorted(v for k, v in avgabs.items() if k not in ("CarryMom", "Carry"))
    B(("b", f"Energy and NGL are the most correlated cross-commodity pair for all seven series types tracked: Momentum ({U(g('Momentum', 'energy', 'ngl'))}), Carry ({U(g('Carry', 'energy', 'ngl'))}), Carry-Momentum ({U(g('CarryMom', 'energy', 'ngl'))}), Value ({U(g('Value', 'energy', 'ngl'))}), Skewness ({U(g('Skewness', 'energy', 'ngl'))}), "
            f"EW PORT ({U(g('EW PORT', 'energy', 'ngl'))}) and Inverse Vol ({U(g('Inverse Vol', 'energy', 'ngl'))}), both trading the same underlying hydrocarbon complex."))
    B(("b", f"Metals-Precious Metals is the second most correlated pair for Momentum ({U(g('Momentum', 'metals', 'precious'))}), Value ({U(g('Value', 'metals', 'precious'))}), Skewness ({U(g('Skewness', 'metals', 'precious'))}), EW PORT ({U(g('EW PORT', 'metals', 'precious'))}) and Inverse Vol ({U(g('Inverse Vol', 'metals', 'precious'))}), "
            f"despite the two asset classes having different fundamental drivers. For the other two series the pairs behind Energy-NGL are weaker still (second place is Metals-NGL for Carry at {U(g('Carry', 'metals', 'ngl'))} and Energy-Agriculture for Carry-Momentum at {U(g('CarryMom', 'energy', 'agri'))}), "
            f"and Metals-Precious Metals is essentially uncorrelated for Carry-Momentum ({N(g('CarryMom', 'metals', 'precious'))})."))
    B(("b", f"Carry-Momentum is the most genuinely diversifying strategy across commodities: its correlations to the same strategy in other asset classes average just {U(avgabs['CarryMom'])} in magnitude, the lowest of the seven series (Carry {U(avgabs['Carry'])}; the other five range {U(others[0])} to {U(others[-1])}), and none of its ten pairwise readings exceeds {U(mxcm)}."))
    B(("h3", "Portfolio Construction Implication"))
    ps = pair_stats(False)
    ps_sorted = sorted(ps, key=lambda d: -d["ew"]["ir"])
    byname = {d["name"]: d for d in ps}
    chk(max(ps, key=lambda d: d["corr"])["name"] == "Energy-NGL" and sorted(ps, key=lambda d: -d["corr"])[1]["name"] == "Metals-Precious Metals", "most correlated pairs by EW PORT")
    sc = sorted(ps, key=lambda d: -d["corr"])
    others_corr = [d["corr"] for d in sc[2:]]
    chk(ps_sorted[0]["name"] == "Energy-NGL" and max(ps, key=lambda d: d["iv"]["ir"])["name"] == "Energy-NGL", "Energy-NGL best pair under both constructions")
    low_ew = min(ps, key=lambda d: d["ew"]["ir"]); low_iv = min(ps, key=lambda d: d["iv"]["ir"])
    B(("b", f"The Cross-Pair tab shows all ten asset-class pairs. Under the EW PORT measure, Energy-NGL ({U(sc[0]['corr'])}) and Metals-Precious Metals ({U(sc[1]['corr'])}) are the two most correlated pairs; every other pair is at or below {U(max(others_corr))}. "
            f"The table below sets each pair's EW PORT correlation beside its full-sample IR under Equal Weight and Inverse Vol (Energy including Natural Gas)."))
    tbl_rows = [[d["name"], U(d["corr"]), I(d["ew"]["ir"]), I(d["iv"]["ir"])] for d in ps_sorted]
    B(("tbl", ["Pair", "EW PORT correlation", "Equal Weight IR", "Inverse Vol IR"], tbl_rows))
    B(("b", f"Correlation and standalone performance are separate questions. Held on its own, Energy-NGL, the most correlated pair, produces the highest full-sample IR of the ten pairs under both constructions (Equal Weight {I(byname['Energy-NGL']['ew']['ir'])}, Inverse Vol {I(byname['Energy-NGL']['iv']['ir'])}), "
            f"while {low_iv['name']} produces the lowest under Inverse Vol ({I(low_iv['iv']['ir'])}) and {low_ew['name']} is joint lowest under Equal Weight ({I(low_ew['ew']['ir'])}). Two individually strong books can still make a poor diversification pairing simply because they move together."))
    return blocks


def crosscommodity():
    bs = bystyle(False); bx = bystyle(True); b4 = bystyle4(False); b4x = bystyle4(True)
    S_ = lambda df, k, w="full": stats(df[k], w)
    ew, iv = S_(bs, "EW PORT"), S_(bs, "Inverse Vol")
    ew4, iv4 = S_(b4, "EW PORT"), S_(b4, "Inverse Vol")
    ewx, ivx = S_(bx, "EW PORT"), S_(bx, "Inverse Vol")
    wP = ("p1", "p2", "p3")
    worst = {k: min(st(v, k)["ir"] for v in ("metals", "energy", "ngl", "precious", "agri")) for k in SLEEVES}
    sty = {k: S_(bs, k) for k in SLEEVES}
    chk(all(sty[k]["ir"] > worst[k] for k in SLEEVES), "each cross-commodity strategy above its worst asset-class showing")
    chk(all(S_(bs, x, w)["ir"] > 0 for x in ("EW PORT", "Inverse Vol") for w in wP), "cross-commodity book positive every period")
    chk(iv["ir"] > ew["ir"] and iv["ret"] > ew["ret"] and iv["mdd"] > ew["mdd"], "Inverse Vol stronger than Equal Weight")
    only = [v for v in ("metals", "energy", "ngl", "precious", "agri") if all(st(v, "EW PORT", w)["ir"] > 0 for w in wP) and all(st(v, "Inverse Vol", w)["ir"] > 0 for w in wP)]
    chk(set(only) == {"energy", "ngl"}, f"only Energy and NGL positive in every period {only}")
    chk(st("energy", "EW PORT")["vol"] > 2 * ew["vol"] and st("ngl", "EW PORT")["vol"] > 2 * ew["vol"], "single-class vol more than twice")
    p3 = {k: S_(bs, k, "p3")["ir"] for k in SLEEVES}
    chk(max(p3, key=p3.get) == "Skewness" and p3["Momentum"] < 0 and 0 < p3["Carry"] < 0.1, "P3 strategy ordering")
    books = combined_book(False); booksx = combined_book(True)
    chk(round(stats(books[("EW", "EW")])["ir"], 2) == round(ew["ir"], 2), "opposite order equals By Style EW")
    oth = [stats(books[k])["ir"] for k in (("EW", "IV"), ("IV", "EW"), ("IV", "IV"))]
    ps = pair_stats(False); psx = pair_stats(True)
    byname = {d["name"]: d for d in ps}
    neg = [d for d in ps if d["ew"]["ir"] < 0 or d["iv"]["ir"] < 0]
    chk({d["name"] for d in neg} == {"Metals-Precious Metals", "Metals-Agriculture", "Precious Metals-Agriculture"}, "negative pairs")
    chk(all(d["ewp"][1] < 0 and d["ewp"][2] < 0 for d in neg), "negative pairs negative in P2 and P3 under EW")
    gap = sorted(ps, key=lambda d: abs(d["ew"]["ir"] - d["iv"]["ir"]))
    chk(gap[0]["name"] == "Energy-NGL", "Energy-NGL most construction robust")
    drop = max(ps, key=lambda d: d["ew"]["ir"] - d["iv"]["ir"])
    chk(drop["name"] == "Precious Metals-NGL", "Inverse Vol pulls Precious-NGL down most")
    lift = []
    for d in ps:
        if "energy" in (d["a"], d["b"]):
            x = next(z for z in psx if {z["a"].replace("energy_exng", "energy"), z["b"].replace("energy_exng", "energy")} == {d["a"], d["b"]})
            lift.append(x["ew"]["ir"] > d["ew"]["ir"])
    chk(len(lift) == 4 and all(lift), "ex-NatGas lifts all four Energy pairs under EW")
    corr4 = {k: bench_corr(b4[k]) for k in ("EW PORT", "Inverse Vol")}; corr5 = {k: bench_corr(bs[k]) for k in SER7 if k in bs}
    chk(all(corr5[k]["Commodity Index"] > 0.1 for k in ("EW PORT", "Inverse Vol")) and corr5["Skewness"]["Commodity Index"] > 0.4, "five-sleeve book now positively correlated with commodity index")
    chk(corr5["EW PORT"]["Equity"] < 0 and corr5["Inverse Vol"]["Equity"] < 0 and corr5["EW PORT"]["60/40 Portfolio"] < 0, "book still negative to equity and 60/40")
    chk(corr5["Value"]["Equity"] > 0 and corr5["Skewness"]["Equity"] > 0 and all(corr5[k]["Equity"] < 0 for k in ("Momentum", "Carry", "CarryMom")), "equity correlation signs by strategy")
    oil = [legs("energy", p)["p3"]["long_pct"] for p in ("WTI", "Brent", "RBOB", "HeatingOil")]
    nglp = [legs("ngl", p)["p3"]["long_pct"] for p in ("Ethane", "Propane", "Butane", "Isobutane")]
    oil_lo, oil_hi, ngl_lo, ngl_hi = min(oil), max(oil), min(nglp), max(nglp)
    chk(oil_lo > 85 and ngl_lo > 75, "oil and NGL long-biased in P3")
    B = []
    blocks = [("h2", "Cross-Commodity Portfolio")]; B = blocks.append
    B(("b", f"Diversifying each individual strategy across all five asset classes first (equal-weighted), then combining strategies, lifts every strategy above its worst individual asset-class showing: Momentum ({line(sty['Momentum'])}), Carry ({line(sty['Carry'])}), Carry-Momentum ({line(sty['CarryMom'])}), Value ({line(sty['Value'])}) and Skewness ({line(sty['Skewness'])}). "
            f"The worst asset-class IRs for the same strategies are {I(worst['Momentum'])}, {I(worst['Carry'])}, {I(worst['CarryMom'])}, {I(worst['Value'])} and {I(worst['Skewness'])}."))
    B(("b", f"At the top level, combining those five cross-commodity strategies gives Equal Weight ({line(ew)}) and Inverse Vol ({line(iv)}). Inverse Vol is the stronger construction, with the higher return and IR and the shallower drawdown at nearly the same volatility."))
    B(("b", f"The cross-commodity book is positive in every one of the three periods under both constructions (Equal Weight P1 {I(S_(bs, 'EW PORT', 'p1')['ir'])}, P2 {I(S_(bs, 'EW PORT', 'p2')['ir'])}, P3 {I(S_(bs, 'EW PORT', 'p3')['ir'])}; Inverse Vol P1 {I(S_(bs, 'Inverse Vol', 'p1')['ir'])}, P2 {I(S_(bs, 'Inverse Vol', 'p2')['ir'])}, P3 {I(S_(bs, 'Inverse Vol', 'p3')['ir'])}). "
            f"Among the single asset classes only Energy and NGL do the same, and both do so at more than twice the cross-commodity volatility (Equal Weight {V(st('energy', 'EW PORT')['vol'])} and {V(st('ngl', 'EW PORT')['vol'])} against {V(ew['vol'])})."))
    B(("b", f"The weakest period for the cross-commodity book is P3 (Equal Weight IR {I(S_(bs, 'EW PORT', 'p3')['ir'])}, Inverse Vol {I(S_(bs, 'Inverse Vol', 'p3')['ir'])}), still positive but a fraction of the strength shown in P2. Within the strategies, P3 is the period in which Momentum turns negative ({I(p3['Momentum'])}) while Carry ({I(p3['Carry'])}) and Carry-Momentum ({I(p3['CarryMom'])}) are barely positive; "
            f"Skewness ({I(p3['Skewness'])}) and Value ({I(p3['Value'])}) are the best sleeves, and Skewness is also the weakest in P1 ({I(S_(bs, 'Skewness', 'p1')['ir'])})."))
    B(("b", f"Skewness changes the book in three ways. It lifts the full-sample IR (Equal Weight {I(ew4['ir'])} to {I(ew['ir'])}, Inverse Vol {I(iv4['ir'])} to {I(iv['ir'])}) and cuts volatility (Equal Weight {V(ew4['vol'])} to {V(ew['vol'])}) and maximum drawdown ({M(ew4['mdd'])} to {M(ew['mdd'])}); it moves the IR from P1 to P3 "
            f"(Equal Weight P1 {I(S_(b4, 'EW PORT', 'p1')['ir'])} to {I(S_(bs, 'EW PORT', 'p1')['ir'])}, P3 {I(S_(b4, 'EW PORT', 'p3')['ir'])} to {I(S_(bs, 'EW PORT', 'p3')['ir'])}); and it adds commodity beta (see the benchmark correlations below)."))
    B(("b", f"Excluding Natural Gas from Energy lifts the book to Equal Weight ({line(ewx)}) and Inverse Vol ({line(ivx)}). Combining in the opposite order, each asset class's five sleeves first and then the five asset-class portfolios, gives the identical Equal Weight result (IR {I(stats(books[('EW', 'EW')])['ir'])}); "
            f"the three other weighting combinations give IRs of {I(oth[0])}, {I(oth[1])} and {I(oth[2])} (sleeves Equal Weight / across Inverse Vol; sleeves Inverse Vol / across Equal Weight; Inverse Vol at both stages)."))
    en = byname["Energy-NGL"]; enx = next(d for d in psx if d["a"] == "energy_exng" and d["b"] == "ngl")
    B(("b", f"Across all ten asset-class pairings, Energy-NGL is the best-performing combination under both constructions (Equal Weight {I(en['ew']['ir'])}, Inverse Vol {I(en['iv']['ir'])}; {I(enx['ew']['ir'])} and {I(enx['iv']['ir'])} without Natural Gas) even though it is the most correlated pair, and it beats the five-class book (Equal Weight {I(ew['ir'])}, Inverse Vol {I(iv['ir'])}) at {V(en['ew']['vol'])} volatility against {V(ew['vol'])}. "
            f"The only pairs with a negative full-sample IR under either construction are the three built from Metals, Precious Metals and Agriculture alone: Metals-Precious Metals ({I(byname['Metals-Precious Metals']['ew']['ir'])} / {I(byname['Metals-Precious Metals']['iv']['ir'])}), Metals-Agriculture ({I(byname['Metals-Agriculture']['ew']['ir'])} / {I(byname['Metals-Agriculture']['iv']['ir'])}) and Precious Metals-Agriculture ({I(byname['Precious Metals-Agriculture']['ew']['ir'])} / {I(byname['Precious Metals-Agriculture']['iv']['ir'])}), "
            f"and each is negative in both P2 and P3 under Equal Weight, consistent with those three asset classes' own EW PORT IRs of {I(st('metals', 'EW PORT')['ir'])}, {I(st('precious', 'EW PORT')['ir'])} and {I(st('agri', 'EW PORT')['ir'])}. "
            f"Energy-NGL is the most construction-robust pair (Equal Weight {I(en['ew']['ir'])}, Inverse Vol {I(en['iv']['ir'])}), while Inverse Vol's effect is otherwise uneven: it pulls down Precious Metals-NGL most ({I(drop['ew']['ir'])} to {I(drop['iv']['ir'])}), consistent with inverse-vol weighting dialing down NGL's higher-volatility portfolio ({V(st('ngl', 'EW PORT')['vol'])} against {V(st('precious', 'EW PORT')['vol'])} for Precious Metals). "
            f"Replacing Energy with Energy ex-NatGas lifts all four Energy pairs under Equal Weight."))
    c5e, c5i = corr5["EW PORT"], corr5["Inverse Vol"]; c4e, c4i = corr4["EW PORT"], corr4["Inverse Vol"]
    B(("b", f"Benchmarked against traditional assets, the five-sleeve cross-commodity book still diversifies equity and bonds but is no longer free of commodity beta: it correlates negatively with Equity (Equal Weight {N(c5e['Equity'])}, Inverse Vol {N(c5i['Equity'])}) and with a traditional 60/40 portfolio ({N(c5e['60/40 Portfolio'])}, {N(c5i['60/40 Portfolio'])}), "
            f"stays close to zero against Fixed Income ({N(c5e['Fixed Income'])}, {N(c5i['Fixed Income'])}) and Gold ({N(c5e['Gold'])}, {N(c5i['Gold'])}), but is positively correlated with a passive Commodity Index ({N(c5e['Commodity Index'])}, {N(c5i['Commodity Index'])}; {N(c4e['Commodity Index'])} and {N(c4i['Commodity Index'])} without Skewness). "
            f"The change comes from Skewness, which correlates {N(corr5['Skewness']['Commodity Index'])} with the Commodity Index, {N(corr5['Skewness']['Equity'])} with Equity and {N(corr5['Skewness']['Gold'])} with Gold because it is long-biased after crashes (the four oil products were long on {oil_lo:.0f}% to {oil_hi:.0f}% of P3 days and the four NGL products on {ngl_lo:.0f}% to {ngl_hi:.0f}%). "
            f"Momentum, Carry and Carry-Momentum remain negatively correlated with Equity and essentially uncorrelated with Gold ({N(corr5['Momentum']['Gold'])}, {N(corr5['Carry']['Gold'])}, {N(corr5['CarryMom']['Gold'])}); Value ({N(corr5['Value']['Equity'])}) and Skewness are the two strategies positively correlated with Equity. "
            f"The correlations use daily returns of the SPY, AGG, DBC and GLD ETFs (adjusted prices from Yahoo Finance, downloaded 12 October 2026) on the days they share with the strategy series, from 2012 to 23 September 2026. Full detail in the Appendix."))
    B(("fig", "fig_cross_combined.png", "Figure 6. Cross-Commodity Portfolio: Combined Strategy Performance (Cumulative Return, 2012-2026)"))
    return blocks


if __name__ == "__main__":
    for f in (correlation, crosscommodity):
        for b in f():
            print(b[0], (b[1] if b[0] not in ("fig", "tbl") else b[1:]))
            print()
