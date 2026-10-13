"""Paper draft, Section 4 (opening, Tables 6 and 7, 4.1 intro, 4.1.1 Metals, 4.1.2 Energy). Agent A.
Every number comes from the fact functions (full precision, two decimals); every qualitative claim is wrapped in chk()."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facts3 import *

# --- number format of the paper: hyphen as the minus sign, no plus signs
def I(x):
    return "0.00" if abs(round(x, 2)) == 0 else f"{x:.2f}"


def N(x, d=2):
    return f"{0:.{d}f}" if abs(round(x, d)) == 0 else f"{x:.{d}f}"


def R(x):
    return "0.0%" if abs(round(x, 1)) == 0 else f"{x:.1f}%"



CLASSES = ["metals", "energy", "precious", "ngl", "agri"]
CNAME = {"metals": "Metals", "energy": "Energy", "precious": "Precious Metals", "ngl": "NGL", "agri": "Agriculture"}
ROWS6 = [("Momentum", "Momentum"), ("Carry", "Carry"), ("CarryMom", "Carry-Momentum"), ("Value", "Value"), ("Skewness", "Skewness"),
         ("EW PORT", "Equal Weight"), ("Inverse Vol", "Inverse Vol")]


def T(x, d=2):
    """Unsigned-positive, hyphen-minus, two decimals; no negative zero."""
    return f"{0:.{d}f}" if abs(round(x, d)) == 0 else f"{x:.{d}f}"


def Q(x, d=1):
    return f"{x:.{d}f}%"


def P(x, d=1):
    return f"{x:.{d}f}"


def ir(v, k, w="full"):
    return st(v, k, w)["ir"]


def opening():
    B = []
    S = lambda v, k, w="full": st(v, k, w)
    # ---- claims used in the opening
    for v in ("energy", "ngl"):
        for k in ("Momentum", "Carry", "CarryMom"):
            for w in ("p1", "p2", "p3"):
                chk(ir(v, k, w) > 0, f"{v} {k} positive in {w}")
    chk(all(ir("ngl", k) > ir("energy", k) for k in ("Momentum", "Carry")) and ir("energy", "CarryMom") > ir("ngl", "CarryMom"), "NGL ahead of Energy in Momentum and Carry, Energy ahead in Carry-Momentum")
    chk(ir("ngl", "EW PORT") > ir("energy", "EW PORT") > 0 and ir("ngl", "Inverse Vol") > ir("energy", "Inverse Vol") > 0, "NGL above Energy above zero in both portfolios")
    chk(all(ir("metals", k, w) > 0 for k in ("Value",) for w in ("full", "p1", "p2", "p3")), "metals Value positive in every window")
    chk(all(any(ir("metals", k, w) <= 0 for w in ("p1", "p2", "p3")) and any(ir("metals", k, w) > 0 for w in ("p1", "p2", "p3")) for k in ("Momentum", "Carry", "CarryMom", "Skewness")), "metals: each other sleeve positive in some periods and not in others")
    chk(all(ir("precious", k) < 0 for k in ("Momentum", "Carry", "CarryMom", "Value")), "precious: four core signals negative full sample")
    chk(all(ir("agri", k) < 0 for k in ("Momentum", "CarryMom", "Value")) and abs(ir("agri", "Carry")) < 0.05, "agri: Momentum, Carry-Momentum, Value negative, Carry flat")
    chk(all(ir(v, "EW PORT") < 0 and ir(v, "Inverse Vol") < 0 for v in ("precious", "agri")), "precious and agri portfolios negative")
    chk(all(ir(v, "Skewness") > 0 for v in ("energy", "precious", "ngl", "agri")) and ir("metals", "Skewness") < 0, "Skewness sign by class")
    chk(all(ir(v, "Skewness", "p1") < 0 for v in ("metals", "energy", "precious", "ngl")) and ir("agri", "Skewness", "p1") > 0, "Skewness P1 sign")
    chk(all(ir(v, "Skewness", "p3") > 0 for v in ("energy", "precious", "ngl", "agri")) and ir("metals", "Skewness", "p3") < 0, "Skewness P3 sign")
    chk(max(ir(v, "Skewness") for v in CLASSES) < 0.3, "no Skewness full-sample IR above 0.30")

    B.append(("h1", "4. Empirical Results"))
    B.append(("p",
        "This section reports what the five signals earn in each asset class. All statistics are computed from net daily log returns over the sample window, 1 January 2012 to 23 September 2026, "
        "after the 5 basis point round-trip cost of Section 2.4. For every sleeve and portfolio we report the annualised return, the annualised volatility, the information ratio (IR) and the maximum drawdown, "
        "defined in Section 3.7. The IR is the annualised return divided by the annualised volatility, with no risk-free rate because the positions are unfunded. "
        "Each statistic is given for the full sample and for the subperiods P1 to P3 (Table 4), so that a result can be read against its stability over time. "
        "Table 5 collects the full-sample IRs of the five signals and of the two asset-class portfolios, Equal Weight (EW PORT) and Inverse Vol, in each of the five classes, "
        "and Table 6 gives the IRs of the portfolios by subperiod. Returns and drawdowns are quoted in the text where they change the reading of an IR."))
    B.append(("p",
        "Two cautions apply to every number below. The results are an in-sample historical backtest of fixed rules, and we have run no significance tests. "
        "Design choices, in particular the combination of the two tenor pairs in Carry and Carry-Momentum (Sections 3.3 and 3.4), were compared on this same sample, "
        "and the concentration of the premium in NGL and Energy reported below was also found in this sample, among 23 products, five signals, two weighting schemes and ten pairs of asset classes. "
        "We therefore describe patterns and do not claim that any of them is statistically distinguishable from zero, and the subperiods are a check on stability and not an out-of-sample test. "
        "Wherever we link a result to a market event or to an economic mechanism, the link is worded as consistent with the result. It is an interpretation and not a test of the mechanism."))
    e = {k: ir("energy", k) for k in ("Momentum", "Carry", "CarryMom", "Value", "Skewness", "EW PORT", "Inverse Vol")}
    n = {k: ir("ngl", k) for k in ("Momentum", "Carry", "CarryMom", "Value", "Skewness", "EW PORT", "Inverse Vol")}
    m = {k: ir("metals", k) for k in ("Value", "Momentum", "Carry", "CarryMom")}
    B.append(("p",
        f"The pattern in Table 5 is concentrated. The premium measured by the four core signals, Momentum, Carry, Carry-Momentum and Value, sits in NGL and Energy. "
        f"In both classes Momentum, Carry and Carry-Momentum earn a positive IR over the full sample and in each of P1, P2 and P3 (full-sample IRs of {T(e['Momentum'])}, {T(e['Carry'])} and {T(e['CarryMom'])} in Energy and {T(n['Momentum'])}, {T(n['Carry'])} and {T(n['CarryMom'])} in NGL). "
        f"The Equal Weight portfolios reach {T(n['EW PORT'])} in NGL and {T(e['EW PORT'])} in Energy and are positive in every subperiod (Table 6). "
        f"Metals has a Value edge only: Value is the one Metals sleeve with a positive IR in every period ({T(m['Value'])} over the full sample), while the other four sleeves are positive in some periods and negative in others. "
        f"Precious Metals and Agriculture earn no clear premium from the core signals: in Precious Metals all four are negative over the full sample, and in Agriculture Momentum, Carry-Momentum and Value are negative and Carry is close to zero ({T(ir('agri', 'Carry'))}). "
        f"Skewness follows a different pattern. Its full-sample IR is positive in four of the five classes but never above {T(max(ir(v, 'Skewness') for v in CLASSES))}, and it is negative in P1 in four classes and positive in P3 in four, which we show below to be episodic."))
    B.append(("p",
        "Section 4.1 takes the five asset classes in turn and reports the five sleeves, their product-level decomposition where it explains the class result, and the Skewness sleeve. "
        "Section 4.2 evaluates the asset-class portfolios of Tables 6 and 7. "
        "Section 4.3 combines the five asset classes into cross-commodity portfolios and examines all ten pairs of classes, and Section 4.4 reports the correlations among sleeves, portfolios and asset classes. "
        "The interpretation of the concentration in terms of storage, hedging pressure and market structure is left to Section 5, and the checks on the design to Section 6."))
    # ---- Table 5
    B.append(("cap", "Table 5: Information ratios by asset class and signal, full sample"))
    rows = [[lab] + [T(ir(v, k)) for v in CLASSES] for k, lab in ROWS6]
    B.append(("tbl", ["Signal / portfolio"] + [CNAME[v] for v in CLASSES], rows, [1.7, 0.9, 0.9, 1.1, 0.9, 1.1]))
    B.append(("note", "Source: authors' calculations. IR is the annualised return divided by the annualised volatility of net daily log returns, 1 January 2012 to 23 September 2026, "
                      "after 5 basis points of round-trip costs, with no risk-free rate. Equal Weight and Inverse Vol are the asset-class portfolios of Section 3.9. Energy includes Natural Gas."))
    # ---- Table 6
    B.append(("cap", "Table 6: Information ratios of the asset-class portfolios by subperiod"))
    rows = []
    for v in CLASSES:
        rows.append([CNAME[v]] + [T(x) for x in per(v, "EW PORT")] + [T(x) for x in per(v, "Inverse Vol")])
    B.append(("tbl", ["Asset class", "Equal Weight P1", "Equal Weight P2", "Equal Weight P3", "Inverse Vol P1", "Inverse Vol P2", "Inverse Vol P3"], rows, [1.5, 0.85, 0.85, 0.85, 0.85, 0.85, 0.85]))
    B.append(("note", "Source: authors' calculations. IR as in Table 5. P1 is 1 January 2012 to 31 December 2016, P2 is 1 January 2017 to 31 December 2021 and P3 is 1 January 2022 to 23 September 2026 (Table 4)."))
    # ---- 4.1 opening
    B.append(("h2", "4.1 Signals by Asset Class"))
    B.append(("p",
        "The five subsections that follow take the asset classes in the column order of Table 5: Metals, Energy, Precious Metals, NGL and Agriculture. "
        "Each reports the sleeves of the class one signal at a time, with the full-sample statistics and the pattern across P1 to P3. "
        "Where the class result is carried by a few products, we decompose the sleeve by product, and the IR of a product is that of its own single-product sleeve. "
        "We then describe the Skewness sleeve, which behaves differently from the other four, and add one sentence on the two asset-class portfolios, which are evaluated in Section 4.2. "
        "The market context is taken from the events and price levels in our own series and is offered as consistent with the results, not as an explanation that we test. "
        "A figure closes each subsection and plots the cumulative return of the five sleeves and of the two portfolios over the sample window."))
    return B


def cum_final(v):
    """Final cumulative return (%) of each plotted curve, as in make_charts.cum (compounded from the log returns)."""
    df = CS[v].loc["2012-01-01":].fillna(0)
    out = {k: float((np.exp(df[k].cumsum()) - 1).iloc[-1] * 100) for k in SLEEVES}
    ew, ivp = PORT[v]
    out["EW PORT"] = float((np.exp(ew.loc["2012-01-01":].fillna(0).cumsum()) - 1).iloc[-1] * 100)
    out["Inverse Vol"] = float((np.exp(ivp.loc["2012-01-01":].fillna(0).cumsum()) - 1).iloc[-1] * 100)
    return out


def metals():
    v, a = "metals", "metals"
    pr = VARIANTS[v][1]
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol")
    cw = corr_within(v)
    cf = cum_final(v)
    amom = {p: pst(a, p, "Momentum")["ir"] for p in pr}
    p3m = {p: pst(a, p, "Momentum", "p3")["ir"] for p in pr}
    cp1 = {p: pst(a, p, "Carry", "p1")["ir"] for p in pr}
    sl = {p: slope_stats(a, p) for p in pr}
    avir = {p: pst(a, p, "Value")["ir"] for p in pr}
    vp3 = {p: pst(a, p, "Value", "p3")["ir"] for p in pr}
    sk_p = {p: pst(a, p, "Skewness")["ir"] for p in pr}
    sk_pp = {p: pper(a, p, "Skewness") for p in pr}
    lg = {p: legs(a, p)["full"] for p in pr}
    avg_vol = float(np.mean([pst(a, p, "Value")["vol"] for p in pr]))
    # ---- claims
    chk(val["ir"] > max(mom["ir"], car["ir"], cm["ir"], sk["ir"]) and all(x > 0 for x in pv), "metals Value is the strongest sleeve and positive in every period")
    chk(pv[1] < 0.1, "metals Value P2 is small")
    chk(pm[0] < 0 and pm[2] < 0 and abs(pm[1]) < 0.1, "metals Momentum P1/P3 negative, P2 flat")
    chk(p3m["Lead"] < p3m["Zinc"] < p3m["Copper"] < 0 < p3m["Aluminium"], "metals Momentum P3 product ordering")
    chk(amom["Aluminium"] > 0 and all(amom[p] < 0 for p in ("Copper", "Zinc", "Lead")), "metals Momentum: only Aluminium positive")
    chk(pc[0] > 0.3 and abs(pc[1]) < 0.05 and pc[2] <= 0 and pcm[0] > 0.5 and pcm[1] < 0 and pcm[2] < 0 and car["ir"] > 0 > cm["ir"], "metals Carry/Carry-Momentum pattern")
    chk(min(cp1["Aluminium"], cp1["Zinc"], cp1["Lead"]) > 0.3 and cp1["Copper"] < 0, "metals Carry P1: three metals positive, Copper negative")
    chk(max(sl[p]["p1"][1] for p in ("Aluminium", "Zinc", "Lead")) < 5 and sl["Copper"]["p1"][0] > -0.5 and sl["Aluminium"]["p1"][0] < sl["Zinc"]["p1"][0] < sl["Lead"]["p1"][0] < -1, "metals P1 slopes")
    chk(sl["Lead"]["p3"][0] < sl["Lead"]["p1"][0] and sl["Aluminium"]["p2"][0] > sl["Aluminium"]["p1"][0] and sl["Zinc"]["p2"][0] > 0 and sl["Zinc"]["p3"][0] > 0 and sl["Lead"]["p2"][0] > sl["Lead"]["p1"][0], "metals later slopes")
    chk(all(x > 0 for x in avir.values()) and vp3["Copper"] < vp3["Aluminium"] < vp3["Zinc"] < vp3["Lead"], "metals Value positive in every metal; P3 ordering")
    chk(cw.loc["Value", "Momentum"] < -0.45 and cw.loc["Value", "Momentum"] == cw.loc[SLEEVES, SLEEVES].min().min(), "metals Value-Momentum most negative pairing")
    chk(val["vol"] < avg_vol, "metals Value sleeve volatility below the average single metal")
    chk(max(abs(x) for x in sk_p.values()) < 0.2 and abs(sk["ir"]) < 0.1 and ps[1] > 0 > ps[0] and ps[2] < 0, "metals Skewness pattern")
    chk(all(sk_pp[p_][0] * sk_pp[p_][1] < 0 for p_ in pr), "metals Skewness: every metal changes sign between P1 and P2")
    chk(lg["Copper"]["short_pnl"] < 0 and lg["Zinc"]["short_pnl"] < 0 and lg["Lead"]["short_pnl"] > 0 and lg["Aluminium"]["short_pnl"] > 0 and lg["Aluminium"]["long_pct"] < 30 and min(lg[p]["long_pct"] for p in ("Copper", "Zinc", "Lead")) > 40, "metals Skewness legs")
    chk(ew["ir"] < 0 and iv["ir"] < 0.1 and val["ir"] > ew["ir"] and val["ir"] > iv["ir"], "metals portfolios below Value")
    chk(cf["Value"] == max(cf.values()) and cf["Momentum"] == min(cf.values()) and abs(cf["EW PORT"]) < 10 and abs(cf["Inverse Vol"]) < 10, "metals figure: Value ends highest, Momentum lowest, portfolios near zero")
    vs = (np.exp(CS[v]["Value"].loc["2012-01-01":].fillna(0).cumsum()) - 1)
    chk(vs.idxmax().year == 2025 and vs.iloc[-1] < vs.max(), "metals Value cumulative peaks in 2025 and gives back part")
    _mc = {p_: importlib.import_module("metals").load_curve(p_)["F1"] for p_ in ("Copper", "Aluminium", "Zinc")}
    chk(round(_mc["Aluminium"].loc["2022-03-04"]) == 3876 and _mc["Aluminium"].idxmax() == pd.Timestamp("2022-03-04") and round(_mc["Aluminium"].loc["2023-12-11"]) == 2076 and round(_mc["Zinc"].loc["2022-04-19"]) == 4523 and round(_mc["Zinc"].loc["2023-05-31"]) == 2240 and round(_mc["Copper"].loc["2026-09-22"]) == 14851 and _mc["Copper"].idxmax() == pd.Timestamp("2026-09-22") and round(_mc["Copper"].loc["2022-03-01":"2023-12-31"].min()) == 7162 and _mc["Copper"].loc["2022-03-01":"2023-12-31"].idxmin().month == 7, "metals price levels in the F1 series")
    B = []
    B.append(("h3", "4.1.1 Metals"))
    B.append(("p",
        f"Metals is the asset class in which Value, and only Value, has an edge. The Value sleeve earns an IR of {T(val['ir'])} (return {Q(val['ret'])}, volatility {Q(val['vol'])}, maximum drawdown {Q(val['mdd'])}) and is positive in each subperiod: {T(pv[0])} in P1, {T(pv[1])} in P2 and {T(pv[2])} in P3, the P2 figure being small. "
        f"None of the other four sleeves has a comparable record (Table 5). Momentum has an IR of {T(mom['ir'])} and a maximum drawdown of {Q(mom['mdd'])}, Carry earns {T(car['ir'])}, Carry-Momentum {T(cm['ir'])} and Skewness {T(sk['ir'])}, "
        f"and each of these is positive in at least one subperiod and not positive in another. "
        f"Figure 1 shows the same ordering in cumulative terms: the Value sleeve finishes the window far above its starting level, Momentum finishes furthest below, and the two portfolio lines stay close to zero. "
        f"The paragraphs below take the sleeves in turn, starting with Momentum and then the two curve-based rules."))
    B.append(("p",
        f"Momentum loses in two of the three subperiods, with an IR of {T(pm[0])} in P1 and {T(pm[2])} in P3, and is roughly flat in P2 ({T(pm[1])}). "
        f"The loss is not spread evenly across the four metals. Over the full sample only Aluminium has a positive Momentum IR ({T(amom['Aluminium'])}), against {T(amom['Copper'])} in Copper, {T(amom['Zinc'])} in Zinc and {T(amom['Lead'])} in Lead. "
        f"In P3 the IR is {T(p3m['Aluminium'])} in Aluminium but {T(p3m['Lead'])} in Lead, {T(p3m['Zinc'])} in Zinc and {T(p3m['Copper'])} in Copper. "
        f"The P3 losses are consistent with the price path of 2021 to 2023. Aluminium peaked at ${_mc['Aluminium'].loc['2022-03-04']:,.0f} on 4 March 2022 in our series (the LME intraday record, about $4,073 in March, followed fears for European smelters under the energy crisis and for Russian supply) and was down to ${_mc['Aluminium'].loc['2023-12-11']:,.0f} by December 2023. "
        f"Zinc fell from ${_mc['Zinc'].loc['2022-04-19']:,.0f} in April 2022 to ${_mc['Zinc'].loc['2023-05-31']:,.0f} in May 2023. "
        f"A trend rule that follows a sharp rise is exposed to losses when the rise reverses at this speed."))
    B.append(("p",
        f"Carry and Carry-Momentum earn a positive IR only in P1. Carry has an IR of {T(car['ir'])} over the full sample (return {Q(car['ret'])}, volatility {Q(car['vol'])}) and Carry-Momentum {T(cm['ir'])} (return {Q(cm['ret'])}, maximum drawdown {Q(cm['mdd'])}). "
        f"In P1 they earn {T(pc[0])} and {T(pcm[0])}. In P2 Carry is flat ({T(pc[1])}) and Carry-Momentum is negative ({T(pcm[1])}), and in P3 both are negative ({T(pc[2])} and {T(pcm[2])}). "
        f"The P1 Carry result comes from three metals: Aluminium ({T(cp1['Aluminium'])}), Zinc ({T(cp1['Zinc'])}) and Lead ({T(cp1['Lead'])}). Their curves were in persistent contango, with an average F1-F13 slope of {N(sl['Aluminium']['p1'][0], 1)}%, {N(sl['Zinc']['p1'][0], 1)}% and {N(sl['Lead']['p1'][0], 1)}% "
        f"and backwardation on only {P(sl['Aluminium']['p1'][1], 0)}%, {P(sl['Zinc']['p1'][1], 0)}% and {P(sl['Lead']['p1'][1], 0)}% of days. "
        f"This is consistent with the years of large LME stocks, aluminium financing deals and warehouse queues of more than two years reported by Reuters and the LME, whose first queue report in May 2014 put the longest aluminium wait at 748 days. "
        f"Copper, whose curve was close to flat (backwardated on {P(sl['Copper']['p1'][1], 0)}% of days), lost in P1 ({T(cp1['Copper'])})."))
    B.append(("p",
        f"After P1 the curves changed, and the Carry record did not follow. Contango in Aluminium eased (average slope {N(sl['Aluminium']['p1'][0], 1)}% in P1, {N(sl['Aluminium']['p2'][0], 1)}% in P2 and {N(sl['Aluminium']['p3'][0], 1)}% in P3). "
        f"Zinc moved into backwardation ({N(sl['Zinc']['p2'][0], 1)}% in P2 and {N(sl['Zinc']['p3'][0], 1)}% in P3), and the contango in Lead first eased and then deepened again ({N(sl['Lead']['p1'][0], 1)}% in P1, {N(sl['Lead']['p2'][0], 1)}% in P2 and {N(sl['Lead']['p3'][0], 1)}% in P3). "
        f"Carry-Momentum, which responds to changes in the slope, is negative in both later subperiods ({T(pcm[1])} and {T(pcm[2])}), and none of these changes brought back the P1 result. The pattern is consistent with a class in which curve signals paid off while a few metals sat in a persistent and extreme contango, and then lost that edge. "
        f"It does not support a claim that term-structure information is stable in Metals."))
    B.append(("p",
        f"Value is the sleeve that works, and it works in every metal: the product-level IRs run from {T(min(avir.values()))} to {T(max(avir.values()))}, all positive. "
        f"Blending the four metals reduces risk, since the sleeve has a volatility of {Q(val['vol'])} against an average of {Q(avg_vol)} for the single-metal Value sleeves. "
        f"The P3 result of {T(pv[2])} comes from the metals that rose far above their five-year averages and then fell back, Lead ({T(vp3['Lead'])}), Zinc ({T(vp3['Zinc'])}) and Aluminium ({T(vp3['Aluminium'])}), "
        f"the same declines from the 2022 peaks described above. Copper is the exception with {T(vp3['Copper'])}, and its price path ran the other way. After falling to ${_mc['Copper'].loc['2022-03-01':'2023-12-31'].min():,.0f} in July 2022, its price rose to ${_mc['Copper'].loc['2026-09-22']:,.0f} on 22 September 2026, the highest value in our series "
        f"(market sources report an LME three-month record of about $14,800 to $14,875 on 9 and 10 September), which market reports tie to US tariff turmoil, tight concentrate supply and demand from electrification and data centres. "
        f""
        f"Value also diversifies the other sleeves: its correlation with Momentum is {N(cw.loc['Value', 'Momentum'])}, the most negative among the five Metals sleeves (Section 4.4)."))
    B.append(("p",
        f"Skewness has no stable edge in Metals. Its IR is {T(sk['ir'])} over the full sample (return {Q(sk['ret'])}, volatility {Q(sk['vol'])}), negative in P1 ({T(ps[0])}) and P3 ({T(ps[2])}) and positive in P2 ({T(ps[1])}). "
        f"No single metal carries a lasting signal: the full-sample IRs are {T(sk_p['Copper'])} in Copper, {T(sk_p['Aluminium'])} in Aluminium, {T(sk_p['Lead'])} in Lead and {T(sk_p['Zinc'])} in Zinc, and every metal changes sign between P1 and P2 "
        f"(Aluminium {T(sk_pp['Aluminium'][0])}, {T(sk_pp['Aluminium'][1])} and {T(sk_pp['Aluminium'][2])} in P1, P2 and P3; Zinc {T(sk_pp['Zinc'][0])}, {T(sk_pp['Zinc'][1])} and {T(sk_pp['Zinc'][2])}). "
        f"The sleeve is long on {P(lg['Copper']['long_pct'], 0)}% of days in Copper, {P(lg['Zinc']['long_pct'], 0)}% in Zinc and {P(lg['Lead']['long_pct'], 0)}% in Lead but on only {P(lg['Aluminium']['long_pct'], 0)}% in Aluminium. "
        f"Before costs, the short legs lose in Copper ({N(lg['Copper']['short_pnl'])} in log return) and Zinc ({N(lg['Zinc']['short_pnl'])}) and earn in Lead ({N(lg['Lead']['short_pnl'])}) and Aluminium ({N(lg['Aluminium']['short_pnl'])}). "
        f"Its returns in Metals therefore come from episodes and not from a premium that persists."))
    B.append(("p",
        f"The two asset-class portfolios do not improve on the best sleeve. Equal Weight has an IR of {T(ew['ir'])} and Inverse Vol {T(iv['ir'])}, both below the Value sleeve alone ({T(val['ir'])}), and Section 4.2 examines the portfolios. "
        f"The Metals result is consistent in direction with the observation in Virtual Barrels (2023, p. 86) that in a diversified commodity risk premia book the sectors other than energy mainly serve to diversify. "
        f"The comparison has limits. That statement concerns the contribution of each sector to the profits of a combined portfolio, whereas Table 5 measures each class on its own, and whether Metals diversifies the other classes is a question for Sections 4.3 and 4.4. "
        f"Energy, to which we turn next, is the class in which the same rules earn the positive IRs that Metals lacks."))
    B.append(("fig", "fig_metals_combined.png", "Figure 1. Metals: combined strategy performance (cumulative return, 2012 to 2026)"))
    return B



def energy():
    import datetime as _dt
    v, a = "energy", "energy"
    pr = VARIANTS[v][1]
    four = [p for p in pr if p != "NatGas"]
    mom, car, cm, val, sk = (st(v, k) for k in SLEEVES)
    pm, pc, pcm, pv, ps = (per(v, k) for k in SLEEVES)
    ew, iv = st(v, "EW PORT"), st(v, "Inverse Vol")
    ewD, ivD = per(v, "EW PORT"), per(v, "Inverse Vol")
    cw = corr_within(v)
    cf = cum_final(v)
    mp = {p: pst(a, p, "Momentum")["ir"] for p in pr}
    cmp_ = {p: pst(a, p, "CarryMom")["ir"] for p in pr}
    cpp = {p: pst(a, p, "Carry", "p3")["ir"] for p in pr}
    vp = {p: pst(a, p, "Value")["ir"] for p in pr}
    skp = {p: pst(a, p, "Skewness")["ir"] for p in pr}
    ngcm = pper(a, "NatGas", "CarryMom")
    lg = {p: legs(a, p) for p in pr}
    lpct3 = {p: lg[p]["p3"]["long_pct"] for p in pr}
    sl_wti = slope_stats(a, "WTI", "F1", "F3"); sl_ng = slope_stats(a, "NatGas", "F1", "F3")
    # ---- claims
    chk(all(x > 0 for x in pm + pc + pcm), "energy Momentum/Carry/Carry-Momentum positive in every period")
    chk(cm["ir"] > mom["ir"] > car["ir"] > 0 > val["ir"], "energy Carry-Momentum strongest, then Momentum, then Carry; Value negative")
    chk(pm[2] < min(pm[0], pm[1]) and pc[2] < min(pc[0], pc[1]) and pc[2] < 0.3, "energy Momentum and Carry weakest in P3")
    chk(min(abs(x) for x in (mom["vol"], car["vol"], cm["vol"])) > 24 and mom["mdd"] < -50 and car["mdd"] < -45, "energy sleeves volatile with deep drawdowns")
    mseries = CS[v]["Momentum"].loc["2012-01-01":].dropna()
    tot = mseries.sum(); yl = yearly_log(mseries)
    share4 = float(yl.loc[[2014, 2015, 2020, 2021]].sum() / tot * 100)
    share22 = float(yl.loc[2022] / tot * 100)
    share26 = float(mseries.loc["2026-01-01":].sum() / tot * 100)
    chk(round(share4) == 95 and round(share22) == 14 and round(share26) == 23, f"energy Momentum concentration {share4:.1f} {share22:.1f} {share26:.1f}")
    rest = 100 - share4 - share22 - share26
    chk(rest < 0, "energy Momentum: remaining years net negative")
    _e = importlib.import_module("energy")
    _f1 = {p_: _e.load_curve(p_)["F1"] for p_ in ("WTI", "Brent")}
    chk(round(_f1["WTI"].loc["2014-06-20"]) == 107 and round(_f1["WTI"].loc["2016-02-11"]) == 26 and _f1["WTI"].loc["2014":"2016"].idxmax() == pd.Timestamp("2014-06-20") and _f1["WTI"].loc["2014":"2016"].idxmin() == pd.Timestamp("2016-02-11"), "energy WTI 2014-2016 levels in the F1 series")
    chk(round(_f1["WTI"].loc["2022-03"].max()) == 124 and _f1["WTI"].loc["2022-03"].idxmax().day == 8, "energy WTI March 2022 high")
    chk(round(_f1["Brent"].loc["2026-02-27"]) == 72 and round(_f1["Brent"].loc["2026-03-31"]) == 118 and _f1["Brent"].loc["2026"].idxmax() == pd.Timestamp("2026-03-31"), "energy Brent 2026 levels")
    wti_apr20 = float(_f1["WTI"].loc["2020-04-20"])
    chk(wti_apr20 > 0, "energy WTI 20 April 2020 imputed in our series")
    chk(cpp["WTI"] < 0 and cpp["Brent"] < 0 and cpp["HeatingOil"] > 0.7, "energy Carry P3 by product")
    chk(round(sl_wti["p3"][1]) == 87 and round(sl_wti["p1"][1]) == 24 and round(sl_wti["p2"][1]) == 46, "energy WTI F1-F3 backwardation shares")
    chk(sl_wti["p3"][1] > max(sl_wti["p1"][1], sl_wti["p2"][1]), "energy WTI most backwardated in P3")
    chk(pv[0] < 0 and pv[2] < 0 and pv[1] > 0 and pv[1] < 0.15, "energy Value period pattern")
    neg = [vp[p] for p in pr if vp[p] < 0]
    chk(len(neg) == 4 and abs(vp["Brent"]) < 0.05 and all(vp[p] > -0.25 for p in pr), "energy Value negative in four of five products, flat in Brent, all small")
    chk(cw.loc["Value", "Momentum"] < -0.45 and cw.loc["Value", "Carry"] < -0.45, "energy Value negative correlation with Momentum and Carry")
    lo = min(min(mp[p], cmp_[p]) for p in four); hi = max(max(mp[p], cmp_[p]) for p in four)
    chk(lo > 0.25, "energy: Momentum and Carry-Momentum positive in all four oil products")
    chk(abs(mp["NatGas"]) < 0.05 and 0.2 < cmp_["NatGas"] < 0.4 and ngcm[2] > 0.8 and ngcm[0] < 0.1 and ngcm[1] < 0.1, "energy NatGas: Momentum no edge, Carry-Momentum modest and all in P3")
    chk([round(100 - sl_ng[w][1]) for w in ("p1", "p2", "p3")] == [87, 75, 74], "energy NatGas contango shares")
    chk(all(skp[p] > 0.2 for p in four) and skp["NatGas"] < -0.3, "energy Skewness by product")
    chk(min(lpct3[p] for p in ("WTI", "Brent", "RBOB")) >= 98 and lpct3["HeatingOil"] > 85, "energy Skewness long almost all of P3")
    chk(lg["WTI"]["p1"]["long_pnl"] < -0.5 and lg["Brent"]["p1"]["long_pnl"] < -0.3, "energy Skewness P1 long legs lose")
    chk(ps[0] < 0 < ps[1] < ps[2], "energy Skewness: negative P1, positive and rising P2, P3")
    wti_pi = pst(a, "WTI", "Skewness", "p3")["ir"]; rb_pi = pst(a, "RBOB", "Skewness", "p3")["ir"]
    natgas_path = (np.exp(nets()[(a, "NatGas")]["Skewness"].loc["2012-01-01":].dropna().sum()) - 1) * 100
    chk(natgas_path < -90, "energy NatGas Skewness path")
    wti_crash, wti_flip = skew_episode(a, "WTI", "2020-03-01", "2020-04-30")
    wti_after, _ = skew_episode(a, "WTI", "2020-05-01", "2021-12-31")
    chk(wti_flip == _dt.date(2020, 3, 11) and wti_crash < -0.4 and wti_after > 1.0, "energy Skewness 2020 episode")
    chk(all(x > 0 for x in ewD + ivD) and abs(iv["ir"] - ew["ir"]) < 0.05, "energy portfolios positive in every period and almost identical")
    chk(cf["CarryMom"] == max(cf.values()) and cf["Value"] == min(cf.values()) and cf["Value"] < 0 and abs(cf["EW PORT"] - cf["Inverse Vol"]) < 0.1 * cf["EW PORT"], "energy figure: Carry-Momentum ends highest, Value lowest and negative, portfolio lines close")
    chk(ir("ngl", "EW PORT") > ew["ir"] and all(ew["ir"] > ir(x, "EW PORT") for x in ("metals", "precious", "agri")), "Energy second to NGL on Equal Weight IR")
    B = []
    B.append(("h3", "4.1.2 Energy"))
    B.append(("p",
        f"Energy is the first of the two classes in which the core signals earn a premium. Carry-Momentum has the highest IR of the five sleeves ({T(cm['ir'])}, return {Q(cm['ret'])}, volatility {Q(cm['vol'])}, maximum drawdown {Q(cm['mdd'])}), followed by Momentum ({T(mom['ir'])}) and Carry ({T(car['ir'])}), and all three are positive in each subperiod "
        f"(Carry-Momentum {T(pcm[0])}, {T(pcm[1])} and {T(pcm[2])} in P1, P2 and P3; Momentum {T(pm[0])}, {T(pm[1])} and {T(pm[2])}; Carry {T(pc[0])}, {T(pc[1])} and {T(pc[2])}). "
        f"Value is the exception, with a full-sample IR of {T(val['ir'])}. The premium is large but not smooth: the three positive sleeves have volatilities of {P(min(mom['vol'], car['vol'], cm['vol']))}% to {P(max(mom['vol'], car['vol'], cm['vol']))}%, and the Momentum and Carry sleeves have maximum drawdowns of {Q(mom['mdd'])} and {Q(car['mdd'])}. "
        f"Momentum and Carry are also weakest in P3, the most recent subperiod. "
        f"Figure 2 shows the ordering in cumulative terms, with Carry-Momentum finishing highest, Value below its starting level, and the Equal Weight and Inverse Vol portfolio lines almost on top of each other."))
    B.append(("p",
        f"The Momentum return was earned in a few years. Calendar years 2014, 2015, 2020 and 2021 account for {P(share4, 0)}% of the sleeve's cumulative log return. "
        f"They coincide with the fall in WTI from ${_f1['WTI'].loc['2014-06-20']:,.0f} on 20 June 2014 to ${_f1['WTI'].loc['2016-02-11']:,.0f} on 11 February 2016 in our series, which followed OPEC's decision of 27 November 2014 to hold output against rising US shale supply, with the demand collapse of 2020 and with the recovery of 2021. "
        f"P3 is the weakest subperiod ({T(pm[2])}) even though it contains the March 2022 spike to ${_f1['WTI'].loc['2022-03'].max():,.0f} after Russia's invasion of Ukraine, a year that adds a further {P(share22, 0)}% of the total. "
        f"The war between the United States, Israel and Iran that began on 28 February 2026 then disrupted Gulf supply on a scale that the International Energy Agency calls the largest in the history of the oil market, and Brent rose from ${_f1['Brent'].loc['2026-02-27']:,.0f} on 27 February to ${_f1['Brent'].loc['2026-03-31']:,.0f} on 31 March. "
        f"The first nine months of 2026 alone account for {P(share26, 0)}% of the cumulative log return, and the remaining years together subtract {P(abs(rest), 0)}%. The shares exceed 100% for that reason."))
    B.append(("p",
        f"Carry is weakest in P3, at {T(pc[2])}, and the weakness is in crude oil: the P3 IR is {T(cpp['WTI'])} in WTI and {T(cpp['Brent'])} in Brent, against {T(cpp['HeatingOil'])} in Heating Oil. "
        f"This occurs although the WTI curve was at its most backwardated in P3, with the first contract above the third on {P(sl_wti['p3'][1], 0)}% of days, against {P(sl_wti['p1'][1], 0)}% in P1 and {P(sl_wti['p2'][1], 0)}% in P2. "
        f"The rule of Section 3.3 explains why a steep curve is not enough. Each pair's slope is compared with its own trailing 252 observations, so a curve that stays backwardated for a long time ceases to look unusual, and the signal can turn short in the middle of a long backwardation. "
        f"Carry is therefore a measure of how backwardated the curve is relative to its recent past and not of the level of backwardation. "
        f"This reading of the P3 weakness is consistent with the product results but is not tested separately."))
    B.append(("p",
        f"Value is the one core sleeve with a negative full-sample IR ({T(val['ir'])}, return {Q(val['ret'])}, maximum drawdown {Q(val['mdd'])}). It is negative in P1 ({T(pv[0])}) and P3 ({T(pv[2])}) and marginally positive in P2 ({T(pv[1])}). "
        f"The failure is broad. Value is negative in four of the five products, with IRs from {T(min(neg))} to {T(max(neg))}, and flat in Brent ({T(vp['Brent'])}), so no single product accounts for it. "
        f"The P1 loss is consistent with the price path of 2014 to 2016. The fall of WTI from ${_f1['WTI'].loc['2014-06-20']:,.0f} to ${_f1['WTI'].loc['2016-02-11']:,.0f} behaved as a trend and not as a cycle that reverts, which is the environment in which a rule that buys cheap and sells dear loses. "
        f"Value is also strongly negatively correlated with the two sleeves that work: {N(cw.loc['Value', 'Momentum'])} with Momentum and {N(cw.loc['Value', 'Carry'])} with Carry, the same sign as in Metals ({N(corr_within('metals').loc['Value', 'Momentum'])} with Momentum)."))
    B.append(("p",
        f"The decomposition by product shows that the Energy result is carried by the four oil products. Momentum and Carry-Momentum both have positive IRs in WTI, Brent, RBOB Gasoline and Heating Oil, between {T(lo)} and {T(hi)}. "
        f"Natural Gas is the outlier. Its Momentum has no edge ({T(mp['NatGas'])}) and its Carry-Momentum earns {T(cmp_['NatGas'])}, almost all of it in P3 ({T(ngcm[0])} in P1, {T(ngcm[1])} in P2 and {T(ngcm[2])} in P3). "
        f"The Natural Gas curve between the first and third contracts was in contango on {P(100 - sl_ng['p1'][1], 0)}%, {P(100 - sl_ng['p2'][1], 0)}% and {P(100 - sl_ng['p3'][1], 0)}% of days in the three subperiods, and Henry Hub averaged $2.77 in 2012, the lowest since 1999, on a mild winter, high storage and rising shale output (US Energy Information Administration). "
        f"The Natural Gas result is consistent with a market whose price moves are driven by weather and regional basis more than by the term-structure logic that works in the oil products. "
        f"It also suggests that the oil products and not the class as a whole are the better description of the sleeves above."))
    B.append(("p",
        f"Skewness earns an IR of {T(sk['ir'])} in Energy (return {Q(sk['ret'])}, volatility {Q(sk['vol'])}, maximum drawdown {Q(sk['mdd'])}), negative in P1 ({T(ps[0])}) and positive in P2 ({T(ps[1])}) and P3 ({T(ps[2])}). "
        f"It works in the four oil products (WTI {T(skp['WTI'])}, Brent {T(skp['Brent'])}, RBOB Gasoline {T(skp['RBOB'])} and Heating Oil {T(skp['HeatingOil'])}) and fails in Natural Gas ({T(skp['NatGas'])}). "
        f"The P2 and P3 results are largely one long position. The signal turned long in WTI on {wti_flip.day} {wti_flip.strftime('%B %Y')}, in the middle of the 2020 collapse (the May contract settled at -$37.63 on 20 April, a value that our series replaces with an imputed ${wti_apr20:.2f}, Section 2.3). "
        f"Before costs, the position lost {abs(wti_crash):.2f} in log return over March and April 2020 and then earned {wti_after:.2f} from May 2020 to December 2021 as prices recovered. "
        f"The trailing-year skewness of oil returns then stayed negative for years, so the sleeve was long on {P(lpct3['WTI'], 0)}% of P3 days in WTI, {P(lpct3['Brent'], 0)}% in Brent and {P(lpct3['RBOB'], 0)}% in RBOB, and it captured both the 2022 spike and the 2026 rally (P3 IR of {T(wti_pi)} in WTI and {T(rb_pi)} in RBOB). "
        f"In P1 the same rule was long on {P(lg['WTI']['p1']['long_pct'], 0)}% of WTI days and lost on those days ({N(lg['WTI']['p1']['long_pnl'])} in log return) as oil fell."))
    B.append(("p",
        f"Natural Gas offsets part of this gain. The long leg of its Skewness position loses {abs(lg['NatGas']['full']['long_pnl']):.2f} in log return over the sample before costs, and the sleeve ends {P(abs(natgas_path), 0)}% below its starting value. "
        f"The Energy Skewness sleeve has low correlations with the other four sleeves ({N(cw.loc['Skewness', 'Momentum'])} with Momentum, {N(cw.loc['Skewness', 'Carry'])} with Carry, {N(cw.loc['Skewness', 'CarryMom'])} with Carry-Momentum and {N(cw.loc['Skewness', 'Value'])} with Value). "
        f"Taken together, the Skewness result is that of a rule that happened to hold the right side of one extended oil recovery, and it differs in kind from the Momentum, Carry and Carry-Momentum results, which are positive in each subperiod. "
        f"We therefore read it as episodic and do not count it as a premium of the same standing."))
    B.append(("p",
        f"Two earlier studies allow a comparison, with differences in method and sample that limit it. Fernandez-Perez, Fuertes and Miffre (2021) sort energy futures contracts each month and hold long-short portfolios on seven signals over July 2001 to March 2019, in the cross-section and not, as here, with one position per product. "
        f"They report premia from the slope of the term structure, hedging pressure, speculative pressure and momentum, and none from value, liquidity or skewness. "
        f"Our Energy results agree in direction on the positive record of Momentum and of the curve-based signals and on the absence of a reliable result for Value or Skewness (their Value premium is positive but statistically insignificant, whereas our Energy Value IR is negative), but our sample is later and our design differs, so we do not compare the size of the premia."))
    B.append(("p",
        f"Bogorad (2025a) applies momentum, carry and value rules to a six-contract energy universe that includes Gasoil, over January 2015 to December 2025, with short-horizon momentum crossovers and carry measured on later tenors. "
        f"Its portfolio of these contracts has a Momentum IR of {T(-0.08)} and a Carry IR of {T(0.31)}, the latter positive in both of its subsamples. Our Carry agrees in sign, but our Momentum is positive. "
        f"The sample start, the universe, the crossover horizons and the tenors differ, and our Momentum return is concentrated in 2014, 2015, 2020 and 2021 while Bogorad's window opens in January 2015, so we cannot attribute the difference to one of these."))
    B.append(("p",
        f"The Energy result is also in line in direction with Virtual Barrels (2023, p. 86), who notes that the largest share of the profits of a diversified commodity risk premia book typically comes from energy futures. "
        f"In Table 5 Energy is second only to NGL, which we treat as a separate class, on the Equal Weight IR. "
        f"The record of Carry-Momentum in all three subperiods is consistent with changes in the slope of the curve carrying information in oil markets, as the theory of storage and the hedging pressure hypothesis of Section 1 would suggest, "
        f"but our design cannot separate these explanations, and Section 5 returns to the question. "
        f"The Equal Weight and Inverse Vol portfolios earn {T(ew['ir'])} and {T(iv['ir'])}, almost the same, and both are positive in every subperiod (Equal Weight {T(ewD[0])}, {T(ewD[1])} and {T(ewD[2])}; Inverse Vol {T(ivD[0])}, {T(ivD[1])} and {T(ivD[2])}), as Section 4.2 discusses. "
        f"Precious Metals, which we take next, is a class in which the same four rules produce a very different record."))
    B.append(("fig", "fig_energy_combined.png", "Figure 2. Energy: combined strategy performance (cumulative return, 2012 to 2026)"))
    return B



def blocks():
    return opening() + metals() + energy()


def words(bl):
    return sum(len(b[1].split()) for b in bl if b[0] == "p")


if __name__ == "__main__":
    bl = blocks()
    for b in bl:
        if b[0] == "p":
            print(f"[{len(b[1].split())} words]", b[1], "\n")
        else:
            print(b[0], b[1:], "\n")
    print("TOTAL PROSE WORDS:", words(bl))
