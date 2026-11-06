from facts3 import *

V5TAG = "(v5 basis: to 23 September 2026, Energy including Natural Gas, not yet updated)"


def key_findings(v6_bullets, ngl):
    """v6_bullets: the eight Key Findings bullets of the v6 document (used verbatim for the three cross-class bullets that are not updated).
    ngl: dict of NGL figures as printed in the (unchanged) NGL section: ew, iv, value, skew, value_p1, skew_p1, skew_p2."""
    pe = {k: st("petroleum", k) for k in SER7}
    me_ew, me_iv, me_val = st("metals", "EW PORT"), st("metals", "Inverse Vol"), st("metals", "Value")
    pm_ew, pm_iv = st("precious", "EW PORT"), st("precious", "Inverse Vol")
    ag_ew, ag_iv = st("agri", "EW PORT"), st("agri", "Inverse Vol")
    sk = {v: st(v, "Skewness") for v in ("metals", "petroleum", "precious", "agri")}
    oil = [legs("energy", p)["p3"]["long_pct"] for p in ("WTI", "Brent", "RBOB", "HeatingOil")]
    sky = yearly_log(CS["petroleum"]["Skewness"].loc["2012-01-01":].dropna())
    big4 = sky.loc[[2020, 2021, 2022, 2026]].sum(); tot = sky.sum()
    # claims
    chk(float(ngl["ew"]) > max(pe["EW PORT"]["ir"], me_ew["ir"], pm_ew["ir"], ag_ew["ir"]) and float(ngl["iv"]) > max(pe["Inverse Vol"]["ir"], me_iv["ir"], pm_iv["ir"], ag_iv["ir"]), "NGL ahead of the four updated classes")
    chk(all(st("petroleum", k, w)["ir"] > 0 for k in ("Momentum", "Carry", "CarryMom") for w in ("p1", "p2", "p3")), "Petroleum Momentum/Carry/CarryMom positive in every period")
    chk(pe["CarryMom"]["ir"] == max(pe[k]["ir"] for k in SLEEVES) and pe["Value"]["ir"] < 0 and all(pe[k]["ir"] > 0 for k in ("Momentum", "Carry", "CarryMom", "Skewness")), "Petroleum CarryMom strongest, Value only negative sleeve")
    chk(big4 > tot, "Petroleum Skewness: four big calendar years exceed the full-sample total")
    chk(me_val["ir"] == max(st("metals", k)["ir"] for k in SLEEVES) and me_val["ir"] > 0.3 and me_ew["ir"] < me_val["ir"] and me_iv["ir"] < me_val["ir"], "Metals: Value the only clear edge, portfolios below it")
    chk(all(st("metals", k)["ir"] < 0.2 for k in ("Momentum", "Carry", "CarryMom", "Skewness")), "Metals: other four sleeves little or no edge")
    chk(all(st("precious", k)["ir"] < 0 for k in ("Momentum", "Carry", "CarryMom", "Value")) and all(st("agri", k)["ir"] < 0 for k in ("Momentum", "CarryMom", "Value")) and abs(st("agri", "Carry")["ir"]) < 0.05, "Precious all core negative; Agri core negative except flat Carry")
    chk(pm_ew["ir"] < 0 and pm_iv["ir"] < 0 and ag_ew["ir"] < 0 and ag_iv["ir"] < 0 and sk["precious"]["ir"] > 0 and sk["agri"]["ir"] > sk["precious"]["ir"], "Precious and Agri portfolios negative; Skewness the only positive sleeve, clearer in Agri")
    chk(sk["metals"]["ir"] < 0 and all(sk[v]["ir"] > 0 for v in ("petroleum", "precious", "agri")) and float(ngl["skew"]) > 0, "Skewness sign by class")
    chk(all(st(v, "Skewness", "p1")["ir"] < 0 for v in ("metals", "petroleum", "precious")) and float(ngl["skew_p1"]) < 0 and st("agri", "Skewness", "p1")["ir"] > 0, "Skewness P1 negative in four classes")
    chk(all(st(v, "Skewness", "p3")["ir"] > 0 for v in ("petroleum", "precious", "agri")) and st("metals", "Skewness", "p3")["ir"] < 0, "Skewness P3 positive in Petroleum, Precious, Agriculture, negative in Metals (NGL positive, v5)")
    chk(min(oil) > 85, "oil products long on more than 85% of P3 days")
    B = []
    B.append(f"NGL is the strongest sleeve in the research (NGL figures are on the v5 basis, to 23 September 2026): Equal Weight (IR {ngl['ew']}) and Inverse Vol (IR {ngl['iv']}) are well ahead of every other asset class (the best of the rest is Petroleum at {I(pe['EW PORT']['ir'])} and {I(pe['Inverse Vol']['ir'])}, to 30 September), "
             f"and Momentum, Carry, and Carry-Momentum are each positive in every period, as they are in Petroleum. Value (IR {ngl['value']}) and Skewness (IR {ngl['skew']}) are the exceptions: Value is negative in P1 ({ngl['value_p1']}), and Skewness is negative in P1 ({ngl['skew_p1']}) and strongly positive in P2 ({ngl['skew_p2']}).")
    B.append(f"Petroleum's Carry-Momentum is its strongest strategy (IR {I(pe['CarryMom']['ir'])}) and Value (IR {I(pe['Value']['ir'])}) is the only core Petroleum strategy with a negative full-sample IR; the Equal Weight and Inverse Vol portfolios earn IR {I(pe['EW PORT']['ir'])} and {I(pe['Inverse Vol']['ir'])}. "
             f"Skewness is positive in Petroleum (IR {I(pe['Skewness']['ir'])}), but mostly because it stayed long oil after the 2020 collapse: calendar years 2020, 2021, 2022 and 2026 add {big4:.2f} of log return against a full-sample total of {tot:.2f}.")
    B.append(f"In Metals, Value is the only strategy with a clear edge (IR {I(me_val['ir'])}); both portfolio constructions (Equal Weight {I(me_ew['ir'])}, Inverse Vol {I(me_iv['ir'])}) underperform simply holding Value alone, since blending four sleeves with little or no edge dilutes the one signal that works.")
    B.append(f"Precious Metals and Agriculture are the two asset classes where portfolio construction fails: neither earns a positive IR (Precious Metals Equal Weight {I(pm_ew['ir'])}, Inverse Vol {I(pm_iv['ir'])}; Agriculture {I(ag_ew['ir'])} and {I(ag_iv['ir'])}), and in Precious Metals every core strategy is net negative full-sample, as they are in Agriculture apart from a flat Carry (IR {I(st('agri', 'Carry')['ir'])}). "
             f"Skewness is the only sleeve with a positive full-sample IR in each, small in Precious Metals ({I(sk['precious']['ir'])}) and clearer in Agriculture ({I(sk['agri']['ir'])}); it trims the loss but does not reverse it.")
    B.append(f"Skewness is a different kind of premium from the other four. It is positive in Petroleum, NGL, Precious Metals and Agriculture and negative in Metals, and it is negative in P1 in four of the five asset classes and positive in P3 in four of the five. "
             f"Its gains in Petroleum, NGL and Precious Metals are largely long positions held after crashes (the four oil products were long on {min(oil):.0f}% to {max(oil):.0f}% of P3 days), consistent with its +0.46 correlation with a passive commodity index in the five-class book (that correlation is on the v5 basis), unlike Momentum, Carry and Carry-Momentum.")
    for b in v6_bullets[5:8]:
        B.append(f"{V5TAG} " + b)
    return B

