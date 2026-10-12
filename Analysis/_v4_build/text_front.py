from facts3 import *


def front():
    ngl_ew, ngl_iv = st("ngl", "EW PORT"), st("ngl", "Inverse Vol")
    en_ew, en_iv = st("energy", "EW PORT"), st("energy", "Inverse Vol")
    enx_ew, enx_iv = st("energy_exng", "EW PORT"), st("energy_exng", "Inverse Vol")
    me_ew, me_iv = st("metals", "EW PORT"), st("metals", "Inverse Vol")
    pm_ew, pm_iv = st("precious", "EW PORT"), st("precious", "Inverse Vol")
    ag_ew, ag_iv = st("agri", "EW PORT"), st("agri", "Inverse Vol")
    cm_en = st("energy", "CarryMom"); val_en = st("energy", "Value"); val_me = st("metals", "Value")
    sk = {v: st(v, "Skewness") for v in VARIANTS}
    bs = bystyle(False); bx = bystyle(True)
    ew, iv = stats(bs["EW PORT"]), stats(bs["Inverse Vol"])
    ps = {d["name"]: d for d in pair_stats(False)}
    psx = {d["name"]: d for d in pair_stats(True)}
    en = ps["Energy-NGL"]
    c5 = {k: bench_corr(bs[k]) for k in ("EW PORT", "Inverse Vol")}
    cc_ew = corr_cross("EW PORT")
    cs = {k: bench_corr(bs[k]) for k in ("Skewness",)}
    b4 = bystyle4(False); c4 = {k: bench_corr(b4[k]) for k in ("EW PORT", "Inverse Vol")}
    oil = [legs("energy", p)["p3"]["long_pct"] for p in ("WTI", "Brent", "RBOB", "HeatingOil")]
    chk(sk["metals"]["ir"] < 0 and all(sk[v]["ir"] > 0 for v in ("energy", "energy_exng", "ngl", "precious", "agri")), "Skewness sign by class")
    chk(all(st(v, "Skewness", "p1")["ir"] < 0 for v in ("metals", "energy", "ngl", "precious")) and st("agri", "Skewness", "p1")["ir"] > 0, "Skewness P1 negative in four classes")
    chk(all(st(v, "Skewness", "p3")["ir"] > 0 for v in ("energy", "ngl", "precious", "agri")) and st("metals", "Skewness", "p3")["ir"] < 0, "Skewness P3 positive in four classes")
    chk(ngl_ew["ir"] > max(en_ew["ir"], me_ew["ir"], pm_ew["ir"], ag_ew["ir"]) * 1.5, "NGL ahead")
    blocks = [
        ("h1", "Multi-Asset Commodity Risk Premia: Research Summary"),
        ("sub", "Metals, Energy, Precious Metals, NGL, Agriculture, Correlation Analysis, and Cross-Commodity Portfolio"),
        ("sub", "Basis of all results: daily returns net of 5 bp round-trip transaction costs, 1 January 2012 to 23 September 2026. Return is the annualised compound return, Vol the annualised volatility and IR their ratio (no risk-free rate). "
                "Each asset class has five sleeves: Momentum, Carry, Carry-Momentum, Value and Skewness (minus the skewness of the product's daily log returns over the past 252 observations; long if negative, short if positive). "
                "Equal Weight (EW PORT) averages the five sleeves equally; Inverse Vol weights each sleeve by the inverse of its trailing 63-day volatility, lagged one day. Periods (regimes): P1 2012-2016, P2 2017-2021, P3 2022-2026. "
                "Signals are those of the main analysis, except that Value starts after 504 observations of F3 (two years), so that NGL Value is live before 2012. Energy includes Natural Gas unless stated. "
                "Relative to the previous version (v3_2012) the Skewness sleeve is new and is included in every portfolio; the four core sleeves are unchanged, so every portfolio, ranking and cross-commodity figure is re-derived."),
        ("h2", "Key Findings"),
    ]
    B = blocks.append
    B(("b", f"NGL is the strongest sleeve in the research: Equal Weight (IR {I(ngl_ew['ir'])}) and Inverse Vol (IR {I(ngl_iv['ir'])}) are well ahead of every other asset class (the best of the rest is Energy at {I(en_ew['ir'])} and {I(en_iv['ir'])}, or {I(enx_ew['ir'])} and {I(enx_iv['ir'])} without Natural Gas), "
            f"and Momentum, Carry, and Carry-Momentum are each positive in every period, as they are in Energy. Value (IR {I(st('ngl', 'Value')['ir'])}) and Skewness (IR {I(st('ngl', 'Skewness')['ir'])}) are the exceptions: Value is negative in P1 ({I(st('ngl', 'Value', 'p1')['ir'])}), and Skewness is negative in P1 ({I(st('ngl', 'Skewness', 'p1')['ir'])}) and strongly positive in P2 ({I(st('ngl', 'Skewness', 'p2')['ir'])})."))
    B(("b", f"Energy's Carry-Momentum is its strongest strategy (IR {I(cm_en['ir'])}) and Value (IR {I(val_en['ir'])}) is the only core Energy strategy with a negative full-sample IR; excluding Natural Gas improves every sleeve and lifts the Equal Weight portfolio from IR {I(en_ew['ir'])} to {I(enx_ew['ir'])}. "
            f"Skewness is positive in Energy (IR {I(sk['energy']['ir'])}, {I(sk['energy_exng']['ir'])} without Natural Gas), but mostly because it stayed long oil after the 2020 collapse."))
    B(("b", f"In Metals, Value is the only strategy with a clear edge (IR {I(val_me['ir'])}); both portfolio constructions (Equal Weight {I(me_ew['ir'])}, Inverse Vol {I(me_iv['ir'])}) underperform simply holding Value alone, since blending four sleeves with little or no edge dilutes the one signal that works."))
    B(("b", f"Precious Metals and Agriculture are the two asset classes where portfolio construction fails: neither earns a positive IR (Precious Metals Equal Weight {I(pm_ew['ir'])}, Inverse Vol {I(pm_iv['ir'])}; Agriculture {I(ag_ew['ir'])} and {I(ag_iv['ir'])}), and in both every core strategy is net negative full-sample. "
            f"Skewness is the only positive sleeve in each (IR {I(sk['precious']['ir'])} and {I(sk['agri']['ir'])}); it trims the loss but does not reverse it."))
    B(("b", f"Skewness is a different kind of premium from the other four. It is positive in Energy, NGL, Precious Metals and Agriculture and negative in Metals, and it is negative in P1 in four of the five asset classes and positive in P3 in four of the five. Its P2 and P3 gains are largely long positions held after crashes "
            f"(the four oil products were long on {min(oil):.0f}% to {max(oil):.0f}% of P3 days), which is why it correlates {N(cs['Skewness']['Commodity Index'])} with a passive commodity index, unlike Momentum, Carry and Carry-Momentum."))
    B(("b", f"Energy-NGL is the most correlated pair of asset classes for all seven series types (EW PORT correlation {U(cc_ew.loc['energy', 'ngl'])}) and Metals-Precious Metals the second most correlated under EW PORT ({U(cc_ew.loc['metals', 'precious'])}), yet standalone Energy-NGL is the best-performing of the ten pairs "
            f"(Equal Weight IR {I(en['ew']['ir'])}, Inverse Vol {I(en['iv']['ir'])}), proving correlation and performance are separate questions."))
    B(("b", f"The cross-commodity portfolio (each strategy equal-weighted across the five asset classes, then the five strategies combined) delivers Equal Weight IR {I(ew['ir'])} and Inverse Vol IR {I(iv['ir'])} at a volatility of {V(ew['vol'])} and {V(iv['vol'])}, and is positive in every period under both constructions. "
            f"It is negatively correlated with equity (Equal Weight {N(c5['EW PORT']['Equity'])}, Inverse Vol {N(c5['Inverse Vol']['Equity'])}) and a traditional 60/40 portfolio ({N(c5['EW PORT']['60/40 Portfolio'])}, {N(c5['Inverse Vol']['60/40 Portfolio'])}), but with Skewness included it is positively correlated with a passive commodity index "
            f"({N(c5['EW PORT']['Commodity Index'])}, {N(c5['Inverse Vol']['Commodity Index'])}; {N(c4['EW PORT']['Commodity Index'])} and {N(c4['Inverse Vol']['Commodity Index'])} without Skewness), so it diversifies equity and bonds but is no longer free of commodity beta."))
    B(("b", f"Diversifying across all five asset classes lowers volatility but not risk-adjusted return: the Energy-NGL pair earns more per unit of risk (IR {I(en['ew']['ir'])} and {I(en['iv']['ir'])}; {I(psx['Energy (ex-NatGas)-NGL']['ew']['ir'])} and {I(psx['Energy (ex-NatGas)-NGL']['iv']['ir'])} without Natural Gas) than the five-class book (IR {I(ew['ir'])} and {I(iv['ir'])}), "
            f"at {V(en['ew']['vol'])} volatility against {V(ew['vol'])}, because the extra diversification comes from Metals, Precious Metals and Agriculture, where the core signals earn little or nothing."))
    return blocks


if __name__ == "__main__":
    for b in front():
        print(b[0], b[1]); print()
