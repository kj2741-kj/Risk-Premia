"""One-off patch of text_cross8.py for seven buckets (2026-11-10). Every replacement must match exactly once."""
p = "text_cross8.py"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)


# ---- corr8: within-bucket
rep('''    pos_value = [t for t in BUCKETS if cw[t].loc["Value", "EW PORT"] > 0]
    chk(pos_value == ["pen", "ngl", "agri"], "Value positively correlated with the portfolio in Gas and Emissions, NGL and Agriculture")''',
    '''    pos_value = [t for t in BUCKETS if cw[t].loc["Value", "EW PORT"] > 0.01]
    chk(pos_value == ["pen", "agri", "softs"] and abs(cw["ngl"].loc["Value", "EW PORT"]) < 0.01, "Value positively correlated with the portfolio in Gas and Emissions, Agriculture and Softs, zero in NGL")''')
rep('''    top_mc = [t for t in BUCKETS if mc[t] > cc[t] and mc[t] > mcm[t]]; top_cc = [t for t in BUCKETS if cc[t] > mc[t] and cc[t] > mcm[t]]
    chk(top_mc == ["petroleum", "ngl", "agri"] and top_cc == ["metals", "pen", "precious"], "closest base pair by bucket")''',
    '''    top_mc = [t for t in BUCKETS if mc[t] > cc[t] and mc[t] > mcm[t]]; top_cc = [t for t in BUCKETS if cc[t] > mc[t] and cc[t] > mcm[t]]; top_mcm = [t for t in BUCKETS if mcm[t] > mc[t] and mcm[t] > cc[t]]
    chk(top_mc == ["petroleum", "ngl"] and top_cc == ["metals", "pen", "precious"] and top_mcm == ["agri", "softs"], "closest base pair by bucket")''')
rep('''    chk(min(sm, key=sm.get) == "ngl" and min(sc, key=sc.get) == "ngl" and max(abs(x) for t, x in list(sm.items()) + list(sc.items()) if t != "ngl") < 0.21, "Skewness with Momentum and Carry near zero except NGL")''',
    '''    chk(min(sm, key=sm.get) == "ngl" and min(sc, key=sc.get) == "ngl" and max(abs(x) for t, x in list(sm.items()) + list(sc.items()) if t != "ngl") < 0.21, "Skewness with Momentum and Carry near zero except NGL")
    chk(sorted(sv, key=sv.get)[:1] == ["precious"] and len([t for t in BUCKETS if sv[t] < 0]) == 6, "Skewness-Value negative in six buckets")''')
rep("In Gas and Emissions, NGL and Agriculture, where Value is positively correlated with the portfolio, it is still the lowest of the five.\",",
    "In Gas and Emissions, Agriculture and Softs, where Value is positively correlated with the portfolio (in NGL the correlation is zero), it is still the lowest of the five.\",")
rep('''        f"Momentum and Carry are the most correlated pair of base strategies in Petroleum ({N(mc['petroleum'])}), NGL ({N(mc['ngl'])}) and Agriculture ({N(mc['agri'])}), consistent with a common driver behind the two signals (not tested here). Metals, Gas and Emissions and Precious Metals break this pattern: in all three, Carry and Carry-Momentum are the closest pair ({N(cc['metals'])} in Metals, {N(cc['pen'])} in Gas and Emissions, {N(cc['precious'])} in Precious Metals). Value is negatively correlated with Momentum in all six buckets ({j(vm)}).",''',
    '''        f"Momentum and Carry are the most correlated pair of base strategies in Petroleum ({N(mc['petroleum'])}) and NGL ({N(mc['ngl'])}), consistent with a common driver behind the two signals (not tested here). Metals, Gas and Emissions and Precious Metals break this pattern: in all three, Carry and Carry-Momentum are the closest pair ({N(cc['metals'])} in Metals, {N(cc['pen'])} in Gas and Emissions, {N(cc['precious'])} in Precious Metals), and in Agriculture and Softs it is Momentum and Carry-Momentum ({N(mcm['agri'])} and {N(mcm['softs'])}). Value is negatively correlated with Momentum in all seven buckets ({j(vm)}).",''')
rep('''With Value it is negative in five buckets and strongest in Precious Metals''', '''With Value it is negative in six buckets and strongest in Precious Metals''')
rep("correlating between {U(min(ivw))} and {U(max(ivw))} across all six buckets", "correlating between {U(min(ivw))} and {U(max(ivw))} across all seven buckets")

# ---- corr8: cross-bucket
rep('''chk(sec["Momentum"] == ("metals", "precious") and sec["Value"] == ("metals", "precious") and sec["Skewness"] == ("metals", "precious") and sec["Carry"] == ("petroleum", "pen") and sec["CarryMom"] == ("petroleum", "agri"), "second-place pairs")''',
    '''chk(sec["Momentum"] == ("metals", "precious") and sec["Value"] == ("metals", "precious") and sec["Skewness"] == ("metals", "precious") and sec["Carry"] == ("petroleum", "pen") and sec["CarryMom"] == ("pen", "ngl"), "second-place pairs")
    third_cm = sorted(PAIR_ORDER, key=lambda p: -cx["CarryMom"].loc[p[0], p[1]])[2]
    chk(third_cm == ("petroleum", "agri") and cx["CarryMom"].loc["pen", "ngl"] - cx["CarryMom"].loc["petroleum", "agri"] < 0.02, "Carry-Momentum: Gas and Emissions-NGL second, narrowly ahead of Petroleum-Agriculture")''')
rep('''chk(min(avg, key=avg.get) == "CarryMom" and sorted(avg.values())[1] > 0.07, "Carry-Momentum has the lowest average cross-bucket correlation")''',
    '''chk(min(avg, key=avg.get) == "CarryMom" and sorted(avg.values())[1] > 0.06, "Carry-Momentum has the lowest average cross-bucket correlation")''')
rep('''chk(max(cm_vals) == pn["CarryMom"] and round(max(cm_vals), 2) == 0.34 and n_small == 14, f"Carry-Momentum: 14 of 15 pairs below 0.10, maximum Petroleum-NGL 0.34 ({n_small})")''',
    '''chk(max(cm_vals) == pn["CarryMom"] and n_small == len(cm_vals) - 1 == 20, f"Carry-Momentum: 20 of 21 pairs below 0.10, maximum Petroleum-NGL ({n_small})")''')
rep('''chk(abs(ge["metals"]) < 0.01 and abs(ge["precious"]) < 0.05 and abs(ge["agri"]) < 0.01 and ge["ngl"] == max(ge.values()), "Gas and Emissions is uncorrelated with Metals, Precious Metals and Agriculture")''',
    '''chk(abs(ge["metals"]) < 0.01 and abs(ge["precious"]) < 0.05 and abs(ge["agri"]) < 0.05 and abs(ge["softs"]) < 0.05 and ge["ngl"] == max(ge.values()), "Gas and Emissions is uncorrelated with Metals, Precious Metals, Agriculture and Softs")''')
rep('''and {_c(ge['metals'])} with Metals, {_c(ge['precious'])} with Precious Metals and {_c(ge['agri'])} with Agriculture. Metals-Precious Metals''', '''and {_c(ge['metals'])} with Metals, {_c(ge['precious'])} with Precious Metals, {_c(ge['agri'])} with Agriculture and {_c(ge['softs'])} with Softs. Metals-Precious Metals''')
rep('''and for Carry-Momentum Petroleum-Agriculture ({U(cx['CarryMom'].loc['petroleum', 'agri'])}).",''', '''and for Carry-Momentum Gas and Emissions-NGL ({U(cx['CarryMom'].loc['pen', 'ngl'])}), narrowly ahead of Petroleum-Agriculture ({U(cx['CarryMom'].loc['petroleum', 'agri'])}).",''')
rep("and {n_small} of its fifteen pairwise readings are below 0.10", "and {n_small} of its twenty-one pairwise readings are below 0.10")

# ---- corr8: pairs
rep('''    chk(best["name"] == "Petroleum-NGL" and max(ps, key=lambda p: p["iv"]["ir"])["name"] == "Petroleum-NGL" and rows[1]["name"] == "Gas and Emissions-NGL", "Petroleum-NGL best under both, Gas and Emissions-NGL second under Equal Weight")
    worst = min(ps, key=lambda p: p["ew"]["ir"]); worst_iv = min(ps, key=lambda p: p["iv"]["ir"])
    chk(worst["name"] == "Precious Metals-Agriculture" and worst_iv["name"] == "Precious Metals-Agriculture", "Precious Metals-Agriculture lowest under both")''',
    '''    best_iv = max(ps, key=lambda p: p["iv"]["ir"]); iv_rows = sorted(ps, key=lambda p: -p["iv"]["ir"])
    chk(best["name"] == "Petroleum-NGL" and rows[1]["name"] == "Gas and Emissions-NGL" and best_iv["name"] == "Gas and Emissions-NGL" and iv_rows[1]["name"] == "Petroleum-NGL", "Petroleum-NGL best under Equal Weight, Gas and Emissions-NGL best under Inverse Vol, the two swap places")
    worst = min(ps, key=lambda p: p["ew"]["ir"]); worst_iv = min(ps, key=lambda p: p["iv"]["ir"])
    chk(worst["name"] == "Agriculture-Softs" and worst_iv["name"] == "Agriculture-Softs", "Agriculture-Softs lowest under both")''')
rep('''f"The Cross-Pair tab shows all fifteen bucket pairs.''', '''f"The Cross-Pair tab shows all twenty-one bucket pairs.''')
rep('''and every other pair is at or below 0.08 in magnitude. "''', '''and every other pair is at or below 0.08 in magnitude. "''')
rep('''    out["impl_close"] = (f"Correlation and standalone performance are separate questions. Held on its own, Petroleum-NGL, the most correlated pair, produces the highest full-sample IR of the fifteen pairs under both constructions (Equal Weight {I(best['ew']['ir'])}, Inverse Vol {I(best['iv']['ir'])}), "
                         f"while Precious Metals-Agriculture produces the lowest under both (Equal Weight {I(worst['ew']['ir'])}, Inverse Vol {I(worst['iv']['ir'])}). Two individually strong books can still make a poor diversification pairing simply because they move together.")''',
    '''    out["impl_close"] = (f"Correlation and standalone performance are separate questions. Held on its own, Petroleum-NGL, the most correlated pair, produces the highest full-sample Equal Weight IR of the twenty-one pairs ({I(best['ew']['ir'])}) and the second highest under Inverse Vol ({I(best['iv']['ir'])}, behind Gas and Emissions-NGL at {I(best_iv['iv']['ir'])}), "
                         f"while Agriculture-Softs produces the lowest under both (Equal Weight {I(worst['ew']['ir'])}, Inverse Vol {I(worst['iv']['ir'])}). Two individually strong books can still make a poor diversification pairing simply because they move together.")
    out["best_iv"] = best_iv''')

# ---- cross8
rep('''    chk(sP["Momentum"][2] < 0 and sP["Carry"][2] > 0 and sP["CarryMom"][2] > 0 and set(sorted(SLEEVES, key=lambda k: -sP[k][2])[:2]) == {"Skewness", "Value"} and sP["Value"][2] > sP["Carry"][2], "P3 strategy ranking: Skewness and Value the two best sleeves")''',
    '''    chk(sP["Momentum"][2] < 0 and sP["CarryMom"][2] < 0 and 0 < sP["Carry"][2] < 0.2 and set(sorted(SLEEVES, key=lambda k: -sP[k][2])[:2]) == {"Skewness", "Value"}, "P3 strategy ranking: Momentum and Carry-Momentum negative, Carry barely positive, Skewness and Value the two best sleeves")''')
rep('''    best = max(ps, key=lambda p: p["ew"]["ir"]); b2 = sorted(ps, key=lambda p: -p["ew"]["ir"])[1]
    chk(best["name"] == "Petroleum-NGL" and best["ew"]["ir"] > ew["ir"] and best["iv"]["ir"] > iv["ir"], "Petroleum-NGL beats the book on IR")
    neg = [p for p in ps if p["ew"]["ir"] < 0 or p["iv"]["ir"] < 0]
    chk([p["name"] for p in neg] == ["Metals-Precious Metals", "Metals-Agriculture", "Precious Metals-Agriculture"] and all(p["ewp"][2] < -0.4 and p["ivp"][2] < -0.4 for p in neg), "the three negative pairs, each clearly negative in P3")''',
    '''    best = max(ps, key=lambda p: p["ew"]["ir"]); b2 = sorted(ps, key=lambda p: -p["ew"]["ir"])[1]
    best_iv = max(ps, key=lambda p: p["iv"]["ir"]); b2_iv = sorted(ps, key=lambda p: -p["iv"]["ir"])[1]
    chk(best["name"] == "Petroleum-NGL" and best["ew"]["ir"] > ew["ir"] and best["iv"]["ir"] > iv["ir"], "Petroleum-NGL beats the book on IR")
    chk(best_iv["name"] == "Gas and Emissions-NGL" and b2_iv["name"] == "Petroleum-NGL" and b2["name"] == "Gas and Emissions-NGL" and best_iv["iv"]["ir"] > iv["ir"] and best_iv["ew"]["ir"] > ew["ir"], "Gas and Emissions-NGL best under Inverse Vol and beats the book")
    neg = [p for p in ps if p["ew"]["ir"] < 0 or p["iv"]["ir"] < 0]
    chk([p["name"] for p in neg] == ["Metals-Precious Metals", "Metals-Agriculture", "Metals-Softs", "Precious Metals-Agriculture", "Precious Metals-Softs", "Agriculture-Softs"] and all(p["ewp"][2] < -0.4 and p["ivp"][2] < -0.25 for p in neg), "the six negative pairs, each clearly negative in P3")
    chk(len([p for p in ps if p["ew"]["ir"] > ew["ir"]]) == 7 and len([p for p in ps if p["iv"]["ir"] > iv["ir"]]) == 4, "seven pairs beat the book under Equal Weight, four under Inverse Vol")''')
rep('''chk(bE["Equity"] < 0 and bI["Equity"] < 0 and bE["60/40 Portfolio"] < 0 and bE["Commodity Index"] > 0.15 and abs(b4E["Commodity Index"]) < 0.02 and abs(b4I["Commodity Index"]) < 0.02, "benchmark correlations")
    chk(round(bS["Commodity Index"], 2) == 0.42 and round(bS["Equity"], 2) == 0.15 and round(bS["Gold"], 2) == 0.15, "Skewness benchmark correlations")''',
    '''chk(bE["Equity"] < 0 and bI["Equity"] < 0 and bE["60/40 Portfolio"] < 0 and bE["Commodity Index"] > 0.15 and abs(b4E["Commodity Index"]) < 0.03 and abs(b4I["Commodity Index"]) < 0.03 and abs(bE["Gold"]) < 0.05 and abs(bE["Fixed Income"]) < 0.1, "benchmark correlations")
    chk(round(bS["Commodity Index"], 2) == 0.41 and round(bS["Equity"], 2) == 0.16 and round(bS["Gold"], 2) == 0.14, "Skewness benchmark correlations")''')
rep('''B.append("Diversifying each individual strategy across all six buckets first''', '''B.append("Diversifying each individual strategy across all seven buckets first''')
rep('''Within the strategies, P3 is the period in which Momentum turns negative ({I(sP['Momentum'][2])}) while Carry ({I(sP['Carry'][2])}) and Carry-Momentum ({I(sP['CarryMom'][2])}) are only modestly positive; Skewness ({I(sP['Skewness'][2])}) and Value ({I(sP['Value'][2])}) are the best sleeves.''',
    '''Within the strategies, P3 is the period in which Momentum ({I(sP['Momentum'][2])}) and Carry-Momentum ({I(sP['CarryMom'][2])}) turn negative and Carry is barely positive ({I(sP['Carry'][2])}); Skewness ({I(sP['Skewness'][2])}) and Value ({I(sP['Value'][2])}) are the best sleeves.''')
rep('''each bucket's five sleeves first and then the six bucket portfolios''', '''each bucket's five sleeves first and then the seven bucket portfolios''')
rep('''    B.append(f"Across all fifteen bucket pairings, Petroleum-NGL is the best-performing combination under both constructions (Equal Weight {I(best['ew']['ir'])}, Inverse Vol {I(best['iv']['ir'])}) even though it is the most correlated pair, followed by Gas and Emissions-NGL ({I(b2['ew']['ir'])} and {I(b2['iv']['ir'])}); both beat the six-bucket book on IR (Equal Weight {I(ew['ir'])}, Inverse Vol {I(iv['ir'])}) at {V(best['ew']['vol'])} and {V(b2['ew']['vol'])} volatility against {V(ew['vol'])}. "
             f"The only pairs with a negative full-sample IR under either construction are the three built from Metals, Precious Metals and Agriculture alone: Metals-Precious Metals ({I(neg[0]['ew']['ir'])} / {I(neg[0]['iv']['ir'])}), Metals-Agriculture ({I(neg[1]['ew']['ir'])} / {I(neg[1]['iv']['ir'])}) and Precious Metals-Agriculture ({I(neg[2]['ew']['ir'])} / {I(neg[2]['iv']['ir'])}), and each is clearly negative in P3 under both constructions (Equal Weight {I(neg[0]['ewp'][2])}, {I(neg[1]['ewp'][2])}, {I(neg[2]['ewp'][2])}; Inverse Vol {I(neg[0]['ivp'][2])}, {I(neg[1]['ivp'][2])}, {I(neg[2]['ivp'][2])}).")''',
    '''    B.append(f"Across all twenty-one bucket pairings, Petroleum-NGL is the best-performing combination under Equal Weight (IR {I(best['ew']['ir'])}, Inverse Vol {I(best['iv']['ir'])}) even though it is the most correlated pair, and Gas and Emissions-NGL is the best under Inverse Vol (Inverse Vol {I(best_iv['iv']['ir'])}, Equal Weight {I(best_iv['ew']['ir'])}); both beat the seven-bucket book on IR under both constructions (Equal Weight {I(ew['ir'])}, Inverse Vol {I(iv['ir'])}) at {V(best['ew']['vol'])} and {V(b2['ew']['vol'])} Equal Weight volatility against {V(ew['vol'])}. "
             f"Seven pairs beat the book under Equal Weight and four under Inverse Vol, every one of them containing NGL, Petroleum or Gas and Emissions. "
             f"The only pairs with a negative full-sample IR under either construction are the six built from Metals, Precious Metals, Agriculture and Softs alone: " + "; ".join(f"{q['name']} ({I(q['ew']['ir'])} / {I(q['iv']['ir'])})" for q in neg) + f", and each is clearly negative in P3 under both constructions (Equal Weight {', '.join(I(q['ewp'][2]) for q in neg)}; Inverse Vol {', '.join(I(q['ivp'][2]) for q in neg)}).")''')
rep("return B, dict(ew=ew, iv=iv, ew4=ew4, iv4=iv4, ewP=ewP, ivP=ivP, sty=sty, bE=bE, bI=bI, b4E=b4E, b4I=b4I, bS=bS, oth=oth, best=best, b2=b2, neg=neg, worst=worst, sP=sP)", "return B, dict(ew=ew, iv=iv, ew4=ew4, iv4=iv4, ewP=ewP, ivP=ivP, sty=sty, bE=bE, bI=bI, b4E=b4E, b4I=b4I, bS=bS, oth=oth, best=best, b2=b2, best_iv=best_iv, b2_iv=b2_iv, neg=neg, worst=worst, sP=sP)")
open(p, "w", encoding="utf-8").write(s)
print("patched")
