"""Paper Section 4.2 to 4.4 (agent C). blocks() returns the blocks in document order.
Every number comes from the fact functions (facts3 / facts / rp); every qualitative claim is wrapped in chk()."""
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



CLS = ["metals", "energy", "ngl", "precious", "agri"]
NM = {"metals": "Metals", "energy": "Energy", "ngl": "NGL", "precious": "Precious Metals", "agri": "Agriculture"}
SL = {"Momentum": "Momentum", "Carry": "Carry", "CarryMom": "Carry-Momentum", "Value": "Value", "Skewness": "Skewness"}
PW = ("p1", "p2", "p3")


def DD(a, b):
    """Unsigned difference of two IRs as the reader computes it from the displayed two-decimal values."""
    return f"{abs(round(a, 2) - round(b, 2)):.2f}"


def avg_sleeve_weights(v):
    """Average Inverse Vol weight on each sleeve of an asset class over the sample window (weights of equation (12))."""
    df = CS[v]
    sig = df.rolling(63).std(ddof=1).shift(1).replace(0, np.nan)
    inv = 1 / sig
    w = inv.div(inv.sum(axis=1, skipna=False), axis=0).loc["2012-01-01":]
    return w.mean()


def s42():
    B = []
    A = B.append
    ew = {v: st(v, "EW PORT") for v in CLS}
    iv = {v: st(v, "Inverse Vol") for v in CLS}
    ew4 = {v: st4(v, "EW PORT") for v in CLS}
    iv4 = {v: st4(v, "Inverse Vol") for v in CLS}
    ewp = {v: per(v, "EW PORT") for v in CLS}
    ivp = {v: per(v, "Inverse Vol") for v in CLS}
    ew4p = {v: [st4(v, "EW PORT", w)["ir"] for w in PW] for v in CLS}
    iv4p = {v: [st4(v, "Inverse Vol", w)["ir"] for w in PW] for v in CLS}
    sl = {v: {k: st(v, k) for k in SLEEVES} for v in CLS}
    dif = {v: iv[v]["ir"] - ew[v]["ir"] for v in CLS}

    # ---- claims behind paragraph 1
    order_ew = sorted(CLS, key=lambda v: -ew[v]["ir"]); order_iv = sorted(CLS, key=lambda v: -iv[v]["ir"])
    chk(order_ew == order_iv == ["ngl", "energy", "metals", "agri", "precious"], "same class ranking under both constructions")
    chk(ew["agri"]["ir"] < 0 and iv["agri"]["ir"] < 0 and ew["precious"]["ir"] < 0 and iv["precious"]["ir"] < 0, "Agriculture and Precious Metals negative under both")
    chk(ew["energy"]["ir"] > 0.7 and iv["energy"]["ir"] > 0.7 and ew["ngl"]["ir"] > 1.1 and iv["ngl"]["ir"] > 1.1 and abs(ew["metals"]["ir"]) < 0.1 and abs(iv["metals"]["ir"]) < 0.1, "NGL and Energy clearly positive, Metals near zero")
    chk(abs(ew["ngl"]["vol"] - ew["energy"]["vol"]) < 1 and abs(iv["ngl"]["vol"] - iv["energy"]["vol"]) < 1, "NGL and Energy volatility within one point")
    A(("h2", "4.2 Asset-Class Portfolios"))
    A(("p", f"Section 4.1 examined the five sleeves of each asset class one at a time. We now combine them into asset-class portfolios, under Equal Weight (EW PORT) and under Inverse Vol as defined in Section 3.9, and ask how the construction changes the picture. Table 7 gives the full-sample statistics and Table 6 the IR in each subperiod. The ranking of the classes does not depend on the construction. NGL is first (IR {I(ew['ngl']['ir'])} under Equal Weight and {I(iv['ngl']['ir'])} under Inverse Vol), followed by Energy ({I(ew['energy']['ir'])} and {I(iv['energy']['ir'])}), Metals ({I(ew['metals']['ir'])} and {I(iv['metals']['ir'])}), Agriculture ({I(ew['agri']['ir'])} and {I(iv['agri']['ir'])}) and Precious Metals ({I(ew['precious']['ir'])} and {I(iv['precious']['ir'])}). "
           f"Only NGL and Energy are clearly positive. Their volatilities are close ({V(ew['ngl']['vol'])} for NGL and {V(ew['energy']['vol'])} for Energy under Equal Weight), so the lead of NGL comes from return ({R(ew['ngl']['ret'])} against {R(ew['energy']['ret'])})."))
    A(("cap", "Table 7: Asset-class portfolios: return, volatility, maximum drawdown and IR, full sample"))
    rows = []
    for v in CLS:
        for nm, s in (("Equal Weight", ew[v]), ("Inverse Vol", iv[v])):
            rows.append([NM[v], nm, R(s["ret"]), V(s["vol"]), M(s["mdd"]), I(s["ir"])])
    A(("tbl", ["Asset class", "Construction", "Return", "Vol", "Max Drawdown", "IR"], rows, [1.5, 1.3, 0.9, 0.8, 1.2, 0.8]))
    A(("note", "Note: Statistics for the sample window, 1 January 2012 to 23 September 2026, net of 5 bp round-trip costs, as defined in Section 3.7. Each portfolio combines the five sleeves of the asset class. Energy includes Natural Gas."))

    # ---- paragraph 2: Equal Weight versus Inverse Vol
    chk(dif["metals"] > 0.1 and dif["energy"] > 0 and dif["energy"] < 0.05 and all(dif[v] < 0 for v in ("ngl", "precious", "agri")), "Inverse Vol ahead in Metals and Energy, Equal Weight in the other three")
    chk(dif["metals"] == max(dif.values()) and abs(dif["ngl"]) < 0.1 and abs(dif["precious"]) < 0.1 and abs(dif["agri"]) < 0.05, "size of the differences")
    gaps = [ew[v]["vol"] - iv[v]["vol"] for v in CLS]
    chk(all(g > 0 for g in gaps) and max(gaps) < 1, "Inverse Vol volatility lower in every class by less than one point")
    chk(max(gaps) == ew["metals"]["vol"] - iv["metals"]["vol"], "largest volatility gap in Metals")
    shal = [v for v in CLS if iv[v]["mdd"] > ew[v]["mdd"]]
    chk(set(shal) == {"metals", "energy", "agri"}, "Inverse Vol drawdown shallower in Metals, Energy, Agriculture only")
    chk(ew["ngl"]["mdd"] == max(s["mdd"] for s in ew.values()), "NGL has the shallowest Equal Weight drawdown")
    chk(ew["precious"]["mdd"] == min(s["mdd"] for s in ew.values()) and iv["precious"]["mdd"] == min(s["mdd"] for s in iv.values()), "Precious Metals deepest drawdown under both")
    A(("p", f"The two constructions are close in four of the five classes. Inverse Vol is ahead in Metals ({I(iv['metals']['ir'])} against {I(ew['metals']['ir'])}, a difference of {DD(iv['metals']['ir'], ew['metals']['ir'])}, the largest of the five) and marginally in Energy ({DD(iv['energy']['ir'], ew['energy']['ir'])}), while Equal Weight is ahead in NGL ({DD(iv['ngl']['ir'], ew['ngl']['ir'])}), Precious Metals ({DD(iv['precious']['ir'], ew['precious']['ir'])}) and Agriculture ({DD(iv['agri']['ir'], ew['agri']['ir'])}). Inverse Vol lowers volatility in every class, but by no more than {U(max(gaps), 1)} percentage points (Metals {V(ew['metals']['vol'])} against {V(iv['metals']['vol'])}), so the differences in IR come mostly from return; in NGL, for example, Equal Weight returns {R(ew['ngl']['ret'])} against {R(iv['ngl']['ret'])}. "
           f"Drawdowns split in the same way. Inverse Vol is shallower in Metals ({M(iv['metals']['mdd'])} against {M(ew['metals']['mdd'])}), Energy ({M(iv['energy']['mdd'])} against {M(ew['energy']['mdd'])}) and Agriculture ({M(iv['agri']['mdd'])} against {M(ew['agri']['mdd'])}), and deeper in NGL ({M(iv['ngl']['mdd'])} against {M(ew['ngl']['mdd'])}) and Precious Metals ({M(iv['precious']['mdd'])} against {M(ew['precious']['mdd'])}). "
           f"Precious Metals has the deepest drawdown of the five classes under both constructions despite a volatility of only {V(ew['precious']['vol'])}, while NGL, the most volatile class, has the shallowest under Equal Weight."))

    # ---- paragraph 3: why close; literature
    aw = {v: avg_sleeve_weights(v) for v in CLS}
    oth4 = [v for v in CLS if v != "metals"]
    wmin = min(aw[v].min() for v in oth4); wmax = max(aw[v].max() for v in oth4)
    chk(wmin > 0.17 and wmax < 0.24, "Inverse Vol sleeve weights stay near one fifth outside Metals")
    chk(aw["metals"].idxmax() == "Value" and aw["metals"]["Value"] > wmax + 0.04 and aw["metals"].idxmin() == "Momentum", "Value has the highest average weight, in Metals, and Momentum the lowest")
    vols_lo = {v: min(sl[v][k]["vol"] for k in SLEEVES) for v in CLS}; vols_hi = {v: max(sl[v][k]["vol"] for k in SLEEVES) for v in CLS}
    chk(max(vols_hi[v] / vols_lo[v] for v in CLS) == vols_hi["metals"] / vols_lo["metals"], "sleeve volatility range widest (relative) in Metals")
    chk(sl["metals"]["Value"]["vol"] == vols_lo["metals"] and sl["metals"]["Momentum"]["vol"] == vols_hi["metals"], "Metals: Value has the lowest and Momentum the highest sleeve volatility")
    A(("p", f"The reason is that the five sleeves of a class have similar volatilities, so Inverse Vol stays close to equal weights: in Energy, NGL, Precious Metals and Agriculture the average weight on a sleeve lies between {U(wmin)} and {U(wmax)}, against one fifth under Equal Weight. Metals has the widest spread of sleeve volatilities (Value {V(sl['metals']['Value']['vol'])} against Momentum {V(sl['metals']['Momentum']['vol'])}), and the average weights range from {U(aw['metals']['Momentum'])} on Momentum to {U(aw['metals']['Value'])} on Value, its only sleeve with a clearly positive IR, which is consistent with Metals gaining most from Inverse Vol. "
           f"The small differences accord with Fernandez-Perez, Fuertes and Miffre (2021), who find in energy futures that equal-weight integration of styles ranks first among their integration methods, which include a weighting by inverse variance. Bogorad (2025a), by contrast, reports a modestly higher IR (1.03 against 0.91) for dynamic risk parity, which scales the exposures to the underlying commodities by their 20-day volatilities, than for equal weights in a portfolio of energy strategies. Both samples and methods differ from ours (long-short portfolios formed monthly across energy contracts, and energy strategies including statistical arbitrage), and we run no test, so we read the evidence only as showing that the weighting matters little here, with Metals the exception."))

    # ---- paragraph 4: subperiod pattern (Table 7)
    for v in ("ngl", "energy"):
        chk(all(x > 0 for x in ewp[v] + ivp[v]), f"{v} positive in every subperiod under both")
        chk(ewp[v][1] == max(ewp[v]) and ivp[v][1] == max(ivp[v]) and ewp[v][0] == min(ewp[v]) and ivp[v][0] == min(ivp[v]), f"{v} P2 strongest, P1 weakest")
    chk(all(x > 0 for x in ewp["metals"][:1] + ivp["metals"][:1]) and ewp["metals"][2] < 0 and ivp["metals"][2] < 0 and abs(ewp["metals"][1]) < 0.1 and abs(ivp["metals"][1]) < 0.1, "Metals positive in P1, about zero in P2, negative in P3")
    chk(all(x < 0 for x in ewp["precious"] + ivp["precious"]), "Precious Metals negative in every subperiod under both")
    chk(ewp["agri"][1] > 0 and ivp["agri"][1] > 0 and ewp["agri"][1] < 0.2 and ewp["agri"][2] < 0 and ivp["agri"][2] < 0 and ivp["agri"][0] < 0 and ewp["agri"][0] < 0, "Agriculture positive only in P2, and only slightly")
    A(("p", f"Table 6 shows how stable these results are across the subperiods. NGL and Energy are the only classes whose portfolios are positive in all three, under both constructions, and in both P2 is the strongest period and P1 the weakest. For NGL the IR runs from {I(ewp['ngl'][0])} in P1 to {I(ewp['ngl'][1])} in P2 and {I(ewp['ngl'][2])} in P3 under Equal Weight (Inverse Vol {I(ivp['ngl'][0])}, {I(ivp['ngl'][1])} and {I(ivp['ngl'][2])}), and for Energy from {I(ewp['energy'][0])} to {I(ewp['energy'][1])} and {I(ewp['energy'][2])} (Inverse Vol {I(ivp['energy'][0])}, {I(ivp['energy'][1])} and {I(ivp['energy'][2])}). "
           f"The other three classes do not hold up. Metals is positive in P1 ({I(ewp['metals'][0])} and {I(ivp['metals'][0])}), close to zero in P2 and negative in P3 ({I(ewp['metals'][2])} and {I(ivp['metals'][2])}). Precious Metals is negative in every subperiod under both constructions. Agriculture is slightly positive only in P2 ({I(ewp['agri'][1])} and {I(ivp['agri'][1])}) and clearly negative in P3 ({I(ewp['agri'][2])} and {I(ivp['agri'][2])}). The full-sample ranking therefore does not rest on one window: NGL and Energy are positive throughout, and Precious Metals is negative throughout."))

    # ---- paragraph 5: Skewness as fifth sleeve, full sample
    chk(all(ew[v]["vol"] < ew4[v]["vol"] and iv[v]["vol"] < iv4[v]["vol"] for v in CLS), "fifth sleeve lowers volatility in every class under both")
    chk(all(ew[v]["ir"] > ew4[v]["ir"] and iv[v]["ir"] > iv4[v]["ir"] for v in ("energy", "precious", "agri")), "Skewness raises IR in Energy, Precious Metals, Agriculture under both")
    chk(ew["metals"]["ir"] < ew4["metals"]["ir"] and iv["metals"]["ir"] < iv4["metals"]["ir"], "Skewness lowers Metals IR under both")
    chk(ew["ngl"]["ir"] < ew4["ngl"]["ir"] and iv["ngl"]["ir"] < iv4["ngl"]["ir"] and ew4["ngl"]["ir"] - ew["ngl"]["ir"] < 0.05 and iv4["ngl"]["ir"] - iv["ngl"]["ir"] < 0.05, "NGL IR essentially unchanged, slightly lower")
    chk(all(ew[v]["ret"] < ew4[v]["ret"] for v in ("energy", "ngl")) and all(ew[v]["ret"] > ew4[v]["ret"] for v in ("precious", "agri")), "return falls in Energy and NGL, rises in Precious Metals and Agriculture (Equal Weight)")
    chk(ew["precious"]["mdd"] > ew4["precious"]["mdd"] + 5 and ew["agri"]["mdd"] > ew4["agri"]["mdd"] + 5, "drawdown much shallower in Precious Metals and Agriculture")
    A(("p", f"Skewness is the fifth sleeve of every portfolio in Table 7. Compared with portfolios built from the four core sleeves alone, adding it lowers volatility in every class under both constructions. Under Equal Weight the fall is from {V(ew4['metals']['vol'])} to {V(ew['metals']['vol'])} in Metals, {V(ew4['energy']['vol'])} to {V(ew['energy']['vol'])} in Energy, {V(ew4['ngl']['vol'])} to {V(ew['ngl']['vol'])} in NGL, {V(ew4['precious']['vol'])} to {V(ew['precious']['vol'])} in Precious Metals and {V(ew4['agri']['vol'])} to {V(ew['agri']['vol'])} in Agriculture. "
           f"The effect on the IR depends on the class. It rises in Energy ({I(ew4['energy']['ir'])} to {I(ew['energy']['ir'])} under Equal Weight, {I(iv4['energy']['ir'])} to {I(iv['energy']['ir'])} under Inverse Vol), Precious Metals ({I(ew4['precious']['ir'])} to {I(ew['precious']['ir'])}; {I(iv4['precious']['ir'])} to {I(iv['precious']['ir'])}) and Agriculture ({I(ew4['agri']['ir'])} to {I(ew['agri']['ir'])}; {I(iv4['agri']['ir'])} to {I(iv['agri']['ir'])}). It is slightly lower in NGL ({I(ew4['ngl']['ir'])} to {I(ew['ngl']['ir'])}; {I(iv4['ngl']['ir'])} to {I(iv['ngl']['ir'])}) and lower in Metals ({I(ew4['metals']['ir'])} to {I(ew['metals']['ir'])}; {I(iv4['metals']['ir'])} to {I(iv['metals']['ir'])}). "
           f"In Energy and NGL the return falls with the volatility (Energy {R(ew4['energy']['ret'])} to {R(ew['energy']['ret'])}, NGL {R(ew4['ngl']['ret'])} to {R(ew['ngl']['ret'])} under Equal Weight), whereas in Precious Metals and Agriculture the loss shrinks and the maximum drawdown is much shallower (Precious Metals {M(ew4['precious']['mdd'])} to {M(ew['precious']['mdd'])}, Agriculture {M(ew4['agri']['mdd'])} to {M(ew['agri']['mdd'])})."))

    # ---- paragraph 6: Skewness by period
    for tag, a4, a5 in (("ew", ew4p, ewp), ("iv", iv4p, ivp)):
        for v in ("metals", "energy", "ngl", "precious"):
            chk(a5[v][0] < a4[v][0] and a5[v][1] > a4[v][1], f"Skewness lowers P1 and raises P2 IR in {v} ({tag})")
        chk(a5["agri"][0] > a4["agri"][0] and a5["agri"][1] < a4["agri"][1], f"Skewness raises P1 and lowers P2 IR in Agriculture ({tag})")
        chk(all(a5[v][2] > a4[v][2] for v in ("energy", "precious", "agri")), f"Skewness raises P3 IR in Energy, Precious Metals, Agriculture ({tag})")
        chk(abs(a5["ngl"][2] - a4["ngl"][2]) < 0.06 and a5["metals"][2] < a4["metals"][2], f"P3: NGL flat, Metals lower ({tag})")
    A(("p", f"The period pattern of the effect is more uniform than the full-sample one. In four of the five classes, Metals, Energy, NGL and Precious Metals, Skewness lowers the P1 IR and raises the P2 IR under both constructions. In NGL, for example, the Equal Weight IR falls from {I(ew4p['ngl'][0])} to {I(ewp['ngl'][0])} in P1 and rises from {I(ew4p['ngl'][1])} to {I(ewp['ngl'][1])} in P2; in Energy it falls from {I(ew4p['energy'][0])} to {I(ewp['energy'][0])} in P1 and rises from {I(ew4p['energy'][1])} to {I(ewp['energy'][1])} in P2. "
           f"Agriculture is the reverse, with a gain in P1 ({I(ew4p['agri'][0])} to {I(ewp['agri'][0])}) and a loss in P2 ({I(ew4p['agri'][1])} to {I(ewp['agri'][1])}). In P3 the sleeve raises the IR in Energy ({I(ew4p['energy'][2])} to {I(ewp['energy'][2])}), Precious Metals ({I(ew4p['precious'][2])} to {I(ewp['precious'][2])}) and Agriculture ({I(ew4p['agri'][2])} to {I(ewp['agri'][2])}), leaves NGL almost unchanged ({I(ew4p['ngl'][2])} to {I(ewp['ngl'][2])}) and lowers it in Metals ({I(ew4p['metals'][2])} to {I(ewp['metals'][2])}). "
           f"Skewness therefore shifts the profile of the portfolios across periods more than it lifts their level, in line with the episodic gains of the Skewness sleeve described in Section 4.1."))

    # ---- paragraph 7: blending where several sleeves carry an edge
    chk(ew["ngl"]["ir"] > max(sl["ngl"][k]["ir"] for k in SLEEVES) and iv["ngl"]["ir"] > max(sl["ngl"][k]["ir"] for k in SLEEVES), "NGL portfolio above every NGL sleeve")
    chk(sorted(SLEEVES, key=lambda k: -sl["ngl"][k]["ir"])[:3] == ["Momentum", "Carry", "CarryMom"] and all(sl["ngl"][k]["ir"] > 0.7 for k in ("Momentum", "Carry", "CarryMom")), "three NGL sleeves above 0.7")
    chk(max(sl["energy"][k]["ir"] for k in SLEEVES) == sl["energy"]["CarryMom"]["ir"] and abs(ew["energy"]["ir"] - sl["energy"]["CarryMom"]["ir"]) < 0.05 and abs(iv["energy"]["ir"] - sl["energy"]["CarryMom"]["ir"]) < 0.05, "Energy portfolio matches best sleeve (Carry-Momentum)")
    chk(sl["energy"]["Momentum"]["ir"] < ew["energy"]["ir"] and sl["energy"]["Carry"]["ir"] < ew["energy"]["ir"], "Energy Momentum and Carry below portfolio")
    chk(all(ew[v]["vol"] < 0.5 * min(sl[v][k]["vol"] for k in SLEEVES) for v in ("ngl", "energy")) and all(iv[v]["vol"] < 0.5 * min(sl[v][k]["vol"] for k in SLEEVES) for v in ("ngl", "energy")), "portfolio volatility below half of any sleeve in NGL and Energy")
    chk(sorted(SLEEVES, key=lambda k: sl["energy"][k]["ir"])[:2] == ["Value", "Skewness"] and set(sorted(SLEEVES, key=lambda k: sl["ngl"][k]["ir"])[:2]) == {"Value", "Skewness"}, "Value and Skewness are the two weakest sleeves in Energy and NGL")
    A(("p", f"Blending helps most where several sleeves carry an edge. In NGL, Momentum ({I(sl['ngl']['Momentum']['ir'])}), Carry ({I(sl['ngl']['Carry']['ir'])}) and Carry-Momentum ({I(sl['ngl']['CarryMom']['ir'])}) all earn a clearly positive IR on their own, and the portfolio is above each of the five sleeves under both constructions (Equal Weight {I(ew['ngl']['ir'])}, Inverse Vol {I(iv['ngl']['ir'])}). Its volatility ({V(ew['ngl']['vol'])}) is less than half that of any single sleeve ({V(vols_lo['ngl'])} to {V(vols_hi['ngl'])}), which is what one expects when the sleeves are far from perfectly correlated (Section 4.4). "
           f"In Energy the portfolio matches the best sleeve, Carry-Momentum ({I(sl['energy']['CarryMom']['ir'])}; portfolio {I(ew['energy']['ir'])} and {I(iv['energy']['ir'])}), and is above Momentum ({I(sl['energy']['Momentum']['ir'])}) and Carry ({I(sl['energy']['Carry']['ir'])}), again at less than half the volatility of any sleeve ({V(ew['energy']['vol'])} against {V(vols_lo['energy'])} to {V(vols_hi['energy'])}). The two weakest sleeves in both classes, Value and Skewness, do not prevent this; their IRs ({I(sl['energy']['Value']['ir'])} and {I(sl['energy']['Skewness']['ir'])} in Energy, {I(sl['ngl']['Value']['ir'])} and {I(sl['ngl']['Skewness']['ir'])} in NGL) are well below those of the leading sleeves, and each carries about a fifth of the weight."))

    # ---- paragraph 8: Metals, Precious Metals, Agriculture
    chk(sl["metals"]["Value"]["ir"] == max(sl["metals"][k]["ir"] for k in SLEEVES) and sl["metals"]["Value"]["ir"] > 0.3 and sl["metals"]["Value"]["ir"] > iv["metals"]["ir"] + 0.25, "Value alone beats both Metals portfolios by a wide margin")
    chk(sl["metals"]["Carry"]["ir"] < 0.15 and all(sl["metals"][k]["ir"] < 0 for k in ("Momentum", "CarryMom", "Skewness")), "other Metals sleeves marginal or negative")
    for v in ("precious", "agri"):
        chk(all(sl[v][k]["ir"] < 0.05 for k in CORE), f"no core sleeve above 0.05 in {v}")
    chk(sl["precious"]["Skewness"]["ir"] > 0 and sl["agri"]["Skewness"]["ir"] > 0 and sl["agri"]["Skewness"]["ir"] == max(sl["agri"][k]["ir"] for k in SLEEVES) and sl["precious"]["Skewness"]["ir"] == max(sl["precious"][k]["ir"] for k in SLEEVES), "Skewness the best (positive) sleeve in Precious Metals and Agriculture")
    chk(sl["precious"]["Skewness"]["ir"] < 0.15 and sl["agri"]["Skewness"]["ir"] < 0.3 and sum(1 for v in ("precious", "agri") for k in SLEEVES if sl[v][k]["ir"] > 0.02) == 2, "Skewness weak and the only sleeve above 0.02 in either class")
    A(("p", f"Where one sleeve carries the edge, blending dilutes it. In Metals, Value alone has an IR of {I(sl['metals']['Value']['ir'])} (return {R(sl['metals']['Value']['ret'])}, volatility {V(sl['metals']['Value']['vol'])}), far above both portfolios ({I(ew['metals']['ir'])} and {I(iv['metals']['ir'])}), because the other four sleeves are at best marginal (Carry {I(sl['metals']['Carry']['ir'])}; Momentum {I(sl['metals']['Momentum']['ir'])}, Carry-Momentum {I(sl['metals']['CarryMom']['ir'])} and Skewness {I(sl['metals']['Skewness']['ir'])}). Equal weights give Value a fifth of the portfolio, and Inverse Vol gives it {U(aw['metals']['Value'])} on average. "
           f"Where no sleeve carries an edge, blending cannot create one. In Precious Metals and Agriculture none of the four core sleeves has an IR above {U(max(sl[v][k]['ir'] for v in ('precious', 'agri') for k in CORE))}. Skewness is the only sleeve with a positive IR in either class ({I(sl['precious']['Skewness']['ir'])} in Precious Metals and {I(sl['agri']['Skewness']['ir'])} in Agriculture), but it is too weak to carry four sleeves with no edge, and both portfolios stay negative (Precious Metals {I(ew['precious']['ir'])} and {I(iv['precious']['ir'])}; Agriculture {I(ew['agri']['ir'])} and {I(iv['agri']['ir'])}). "
           "The portfolios therefore reproduce at asset-class level the concentration seen in the sleeves: the combination of five signals produces a premium of any size only in NGL and Energy, whichever of the two weightings is used. Section 4.3 asks whether combining the five classes preserves, dilutes or improves on that result."))
    return B


def across_weights(stage):
    """Average Inverse Vol weight on each asset class when the five class portfolios (stage 0 Equal Weight, 1 Inverse Vol within) are combined."""
    ac = {t: PORT[t][stage].dropna() for t in CLS}
    cum = [ac[t].cumsum() for t in CLS]
    idx = cum[0].index
    for c in cum[1:]:
        idx = idx.intersection(c.index)
    idx = idx.sort_values()
    al = pd.DataFrame({t: c.reindex(idx).diff() for t, c in zip(CLS, cum)})
    inv = 1 / al.rolling(63).std(ddof=1).shift(1).replace(0, np.nan)
    return inv.div(inv.sum(axis=1, skipna=False), axis=0).loc["2012-01-01":].mean()


def pair_iv_weight(a, b):
    """Average Inverse Vol weight on class a in the pair (a, b)."""
    cl = [PORT[a][1].dropna().cumsum(), PORT[b][1].dropna().cumsum()]
    idx = cl[0].index.intersection(cl[1].index).sort_values()
    al = pd.DataFrame({a: cl[0].reindex(idx).diff(), b: cl[1].reindex(idx).diff()})
    inv = 1 / al.rolling(63).std(ddof=1).shift(1).replace(0, np.nan)
    return float((inv[a] / (inv[a] + inv[b])).loc["2012-01-01":].mean())


def s43():
    B = []
    A = B.append
    bs = bystyle(); b4 = bystyle4(); bk = combined_book()
    ps = pair_stats(False); byn = {d["name"]: d for d in ps}
    ew5 = stats(bs["EW PORT"]); ivb = stats(bs["Inverse Vol"])
    K = {k: stats(bk[k]) for k in bk}
    Kp = {k: [stats(bk[k], w)["ir"] for w in PW] for k in bk}
    ew_p = [stats(bs["EW PORT"], w)["ir"] for w in PW]; ivb_p = [stats(bs["Inverse Vol"], w)["ir"] for w in PW]
    sg = {k: stats(bs[k]) for k in SLEEVES}; sgp = {k: [stats(bs[k], w)["ir"] for w in PW] for k in SLEEVES}
    en, ng, me, pm, ag = (st(v, "EW PORT") for v in ("energy", "ngl", "metals", "precious", "agri"))
    enI, ngI = st("energy", "Inverse Vol"), st("ngl", "Inverse Vol")
    EE, EI, IE, II = ("EW", "EW"), ("EW", "IV"), ("IV", "EW"), ("IV", "IV")
    chk(round(K[EE]["ir"], 6) == round(ew5["ir"], 6) and abs(K[EE]["ret"] - ew5["ret"]) < 1e-6, "by-signal Equal Weight identical to Equal Weight at both stages")

    A(("h2", "4.3 Cross-Commodity Portfolio and Best Pairs"))
    # ---- P1 levels
    chk(K[EE]["ir"] > K[IE]["ir"] > K[EI]["ir"] > K[II]["ir"], "ordering of the four books")
    chk(K[EI]["vol"] < K[EE]["vol"] and K[II]["vol"] < K[IE]["vol"] and K[EI]["ret"] < K[EE]["ret"] * 0.65 and K[II]["ret"] < K[IE]["ret"] * 0.65, "Inverse Vol across lowers volatility but cuts return by more")
    chk(abs(K[EE]["ir"] - K[IE]["ir"]) < 0.03 and abs(K[EI]["ir"] - K[II]["ir"]) < 0.07, "within-class choice matters little")
    chk(K[EI]["mdd"] < K[EE]["mdd"] and K[II]["mdd"] < K[IE]["mdd"], "Inverse Vol across has deeper drawdown")
    A(("p", f"The asset-class portfolios are next combined across classes. Section 3.9 defines four cross-commodity portfolios, according to whether Equal Weight or Inverse Vol is used within each class and across the five classes, and a by-signal construction that first equal-weights each signal across classes and then combines the five resulting strategies. Table 8 reports the four portfolios, the by-signal Inverse Vol portfolio and the five strategies. The by-signal Equal Weight portfolio is identical to the portfolio with Equal Weight at both stages and is not listed twice. "
           f"The weighting across classes matters more than the weighting within them. With Equal Weight across classes the IR is {I(K[EE]['ir'])} (Equal Weight within) and {I(K[IE]['ir'])} (Inverse Vol within); with Inverse Vol across classes it is {I(K[EI]['ir'])} and {I(K[II]['ir'])}. Inverse Vol across classes lowers volatility (from {V(K[EE]['vol'])} to {V(K[EI]['vol'])} when classes are equal-weighted within) but lowers return by more (from {R(K[EE]['ret'])} to {R(K[EI]['ret'])}), and the maximum drawdown is no shallower ({M(K[EE]['mdd'])} against {M(K[EI]['mdd'])})."))
    rows = []
    nm4 = {EE: "Equal Weight within, Equal Weight across", EI: "Equal Weight within, Inverse Vol across", IE: "Inverse Vol within, Equal Weight across", II: "Inverse Vol within, Inverse Vol across"}
    for k in (EE, EI, IE, II):
        s = K[k]; rows.append([nm4[k], R(s["ret"]), V(s["vol"]), M(s["mdd"]), I(s["ir"])] + [I(x) for x in Kp[k]])
    rows.append(["By signal, Inverse Vol", R(ivb["ret"]), V(ivb["vol"]), M(ivb["mdd"]), I(ivb["ir"])] + [I(x) for x in ivb_p])
    for k in SLEEVES:
        s = sg[k]; rows.append([f"{SL[k]}, equal-weighted across classes", R(s["ret"]), V(s["vol"]), M(s["mdd"]), I(s["ir"])] + [I(x) for x in sgp[k]])
    A(("cap", "Table 8: Cross-commodity portfolios"))
    A(("tbl", ["Portfolio", "Return", "Vol", "Max Drawdown", "IR", "IR P1", "IR P2", "IR P3"], rows, [2.5, 0.7, 0.6, 0.9, 0.6, 0.6, 0.6, 0.6]))
    A(("note", "Note: Full-sample statistics (1 January 2012 to 23 September 2026, net of 5 bp round-trip costs) and IR by subperiod. The first four rows are the portfolios of Section 3.9; the fifth combines the five by-signal strategies by Inverse Vol, and the by-signal Equal Weight portfolio equals the first row. The last five rows are the strategies that the by-signal construction combines. Energy includes Natural Gas."))

    # ---- P2 why across-class Inverse Vol costs return; by-signal
    w0 = across_weights(0)
    chk(w0["ngl"] < 0.2 and w0["energy"] < 0.2 and all(w0[v] > 0.2 for v in ("metals", "precious", "agri")) and w0["metals"] == max(w0), "Inverse Vol across shifts weight to Metals, Precious Metals, Agriculture")
    chk(max(st(v, "EW PORT")["ir"] for v in ("metals", "precious", "agri")) < 0, "Metals, Precious Metals and Agriculture Equal Weight portfolios have no positive IR")
    chk(abs(ivb["vol"] - ew5["vol"]) < 0.3 and ivb["ir"] > ew5["ir"] and ivb["ret"] > ew5["ret"] and ivb["mdd"] > ew5["mdd"], "by-signal Inverse Vol slightly ahead of Equal Weight")
    sv = [sg[k]["vol"] for k in SLEEVES]
    chk(min(sv) > 9 and max(sv) < 13, "strategy volatilities between 9 and 13")
    cv = [st(v, "EW PORT")["vol"] for v in CLS]
    A(("p", f"The reason lies in the weights. The class portfolios differ widely in volatility ({V(min(cv))} in Agriculture to {V(max(cv))} in NGL under Equal Weight), so Inverse Vol across classes gives the two classes with a premium an average weight of {U(w0['energy'])} for Energy and {U(w0['ngl'])} for NGL, against one fifth, and gives more to the classes without one ({U(w0['metals'])} for Metals, {U(w0['agri'])} for Agriculture and {U(w0['precious'])} for Precious Metals). This is consistent with the loss of return, which we do not test. "
           f"The by-signal Inverse Vol portfolio behaves differently because the five strategies it combines have similar volatilities ({V(min(sv))} to {V(max(sv))}), so its weights stay close to equal. It is marginally ahead of the Equal Weight portfolio on every measure except volatility (return {R(ivb['ret'])} against {R(ew5['ret'])}, IR {I(ivb['ir'])} against {I(ew5['ir'])}, maximum drawdown {M(ivb['mdd'])} against {M(ew5['mdd'])}). We take the Equal Weight portfolio and this by-signal Inverse Vol portfolio as the two reference cross-commodity portfolios in what follows."))

    # ---- P3 period pattern
    allp = {**{k: Kp[k] for k in (EE, EI, IE, II)}, "bsIV": ivb_p}
    chk(all(p[1] == max(p) for p in allp.values()), "P2 strongest for every book")
    chk(all(p[2] == min(p) for k, p in allp.items() if k != IE) and Kp[IE][2] < Kp[IE][0] and Kp[IE][0] - Kp[IE][2] < 0.02, "P3 weakest for all but Inverse Vol within / Equal Weight across, where it is level with P1")
    posp = [k for k, p in allp.items() if all(x > 0 for x in p)]
    chk(set(posp) == {EE, IE, II, "bsIV"} and Kp[EI][2] < 0 and abs(Kp[EI][2]) < 0.1 and 0 < Kp[II][2] < 0.1, "positive in every period for four of the five books; Equal Weight within / Inverse Vol across slightly negative in P3, Inverse Vol at both stages barely positive")
    chk(all(ew_p[i] > 0 for i in range(3)) and all(ivb_p[i] > 0 for i in range(3)), "reference books positive in every period")
    only = [v for v in CLS if all(st(v, "EW PORT", w)["ir"] > 0 for w in PW) and all(st(v, "Inverse Vol", w)["ir"] > 0 for w in PW)]
    chk(set(only) == {"energy", "ngl"}, "only Energy and NGL positive in every period under both constructions")
    chk(en["vol"] > 2 * ew5["vol"] and ng["vol"] > 2 * ew5["vol"], "Energy and NGL volatility more than twice the book")
    A(("p", f"The pattern across subperiods is the same for all of them. Each of the first five portfolios in Table 8 is strongest in P2 (IR {I(min(p[1] for p in allp.values()))} to {I(max(p[1] for p in allp.values()))}) and weakest in P3, except for Inverse Vol within and Equal Weight across, where P3 ({I(Kp[IE][2])}) is level with P1 ({I(Kp[IE][0])}). The two reference portfolios are positive in every subperiod (Equal Weight P1 {I(ew_p[0])}, P2 {I(ew_p[1])}, P3 {I(ew_p[2])}; by-signal Inverse Vol {I(ivb_p[0])}, {I(ivb_p[1])} and {I(ivb_p[2])}), as are the portfolio with Inverse Vol within and Equal Weight across and the one with Inverse Vol at both stages (the latter barely, {I(Kp[II][2])} in P3). The only exception is Equal Weight within with Inverse Vol across, which is slightly negative in P3 ({I(Kp[EI][2])}). "
           f"Among the single asset classes, only Energy and NGL are positive in every subperiod under both constructions, but they run at more than twice the volatility of the cross-commodity portfolio ({V(en['vol'])} and {V(ng['vol'])} under Equal Weight against {V(ew5['vol'])}). The cross-commodity portfolio is thus steadier than most of its parts without matching the two that carry the premium."))

    # ---- P4 strategies and Figure 6
    worst = {k: min(st(v, k)["ir"] for v in CLS) for k in SLEEVES}
    chk(all(sg[k]["ir"] > worst[k] for k in SLEEVES), "each strategy above its weakest asset-class IR")
    chk(sorted(SLEEVES, key=lambda k: -sg[k]["ir"]) == ["Carry", "CarryMom", "Momentum", "Skewness", "Value"], "full-sample strategy ordering")
    chk(max(sgp, key=lambda k: sgp[k][0]) == "Carry" and max(sgp, key=lambda k: sgp[k][1]) == "Carry" and min(sgp, key=lambda k: sgp[k][0]) == "Skewness" and sorted(SLEEVES, key=lambda k: sgp[k][0])[1] == "Value", "P1: Carry first, Skewness and Value last")
    chk(sorted(SLEEVES, key=lambda k: -sgp[k][2]) == ["Skewness", "Value", "Carry", "CarryMom", "Momentum"] and sgp["Momentum"][2] < 0 and 0 < sgp["CarryMom"][2] < sgp["Carry"][2] < 0.3, "P3 ordering of strategies")
    chk(all(sgp[k][1] > 0.8 for k in ("Momentum", "Carry", "CarryMom")), "Momentum, Carry, Carry-Momentum above 0.8 in P2")
    cs = {k: bs[k].loc["2012-01-01":].cumsum() for k in list(SLEEVES) + ["EW PORT", "Inverse Vol"]}
    chk(cs["EW PORT"].idxmax().year == 2024 and cs["Inverse Vol"].idxmax().year == 2024 and cs["EW PORT"].iloc[-1] < cs["EW PORT"].max() and cs["Inverse Vol"].iloc[-1] < cs["Inverse Vol"].max(), "both reference books peak in 2024 and end lower")
    chk(max(cs[k].iloc[-1] for k in SLEEVES) == cs["Carry"].iloc[-1] and cs["Value"].iloc[-1] < cs["Skewness"].iloc[-1] < cs["EW PORT"].iloc[-1], "Carry ends highest; Value lowest")
    cE = cs["EW PORT"]; cI = cs["Inverse Vol"]
    chk(all(c.loc[:"2022-12-31"].iloc[-1] > c.loc[:"2021-12-31"].iloc[-1] > c.loc[:"2019-12-31"].iloc[-1] > c.loc[:"2016-12-31"].iloc[-1] > 0 for c in (cE, cI)), "both reference books rise through 2022")
    chk(cs["Skewness"].loc["2013-01-01":"2019-12-31"].max() < 0 and cs["Skewness"].iloc[-1] > 0, "Skewness cumulative below zero 2013 to 2019 and positive at the end")
    A(("p", f"The strategies show where the pattern comes from. Combined across the five classes, Carry has the highest full-sample IR ({I(sg['Carry']['ir'])}), followed by Carry-Momentum ({I(sg['CarryMom']['ir'])}), Momentum ({I(sg['Momentum']['ir'])}), Skewness ({I(sg['Skewness']['ir'])}) and Value ({I(sg['Value']['ir'])}), and each is above the IR of its weakest asset class in Table 5. Carry, Carry-Momentum and Momentum carry the book in P1 and P2 (P2 IRs {I(sgp['Carry'][1])}, {I(sgp['CarryMom'][1])} and {I(sgp['Momentum'][1])}) and fade in P3. "
           f"The order then reverses. In P3 Skewness ({I(sgp['Skewness'][2])}) and Value ({I(sgp['Value'][2])}) lead, followed by Carry ({I(sgp['Carry'][2])}) and Carry-Momentum ({I(sgp['CarryMom'][2])}), and Momentum is negative ({I(sgp['Momentum'][2])}); in P1, Skewness ({I(sgp['Skewness'][0])}) and Value ({I(sgp['Value'][0])}) were the two weakest. Skewness and Value therefore hold the book in P3 while the three signals built on trend and curve shape fade, as Figure 6 shows: both reference portfolios rise through 2022 and peak in 2024, and give back part of the gain afterwards, Carry ends the sample highest of the five strategies, and the Skewness curve is below its starting level from 2013 to 2019 and ends above it."))
    A(("fig", "fig_cross_combined.png", "Figure 6. Cross-commodity portfolio: combined strategy performance (cumulative return, 2012 to 2026)"))

    # ---- P5 Skewness effect on the book
    e4, i4 = stats(b4["EW PORT"]), stats(b4["Inverse Vol"])
    e4p = [stats(b4["EW PORT"], w)["ir"] for w in PW]; i4p = [stats(b4["Inverse Vol"], w)["ir"] for w in PW]
    chk(ew5["ir"] > e4["ir"] and ivb["ir"] > i4["ir"] and ew5["vol"] < e4["vol"] and ew5["mdd"] > e4["mdd"] and ew5["ret"] < e4["ret"], "Skewness lifts IR, lowers volatility and return, shallower drawdown in the book")
    chk(ew_p[0] < e4p[0] and ivb_p[0] < i4p[0] and ew_p[2] > e4p[2] and ivb_p[2] > i4p[2], "Skewness lowers P1 and raises P3 IR of the book")
    chk(all(x > 0 for x in e4p + i4p), "four-sleeve book positive in every period")
    A(("p", f"Skewness changes the book in three ways. It lifts the full-sample IR (Equal Weight {I(e4['ir'])} to {I(ew5['ir'])}, by-signal Inverse Vol {I(i4['ir'])} to {I(ivb['ir'])}), and it lowers volatility ({V(e4['vol'])} to {V(ew5['vol'])} under Equal Weight) and maximum drawdown ({M(e4['mdd'])} to {M(ew5['mdd'])}), with a lower return ({R(e4['ret'])} to {R(ew5['ret'])}). It also shifts the IR from P1 to P3: under Equal Weight P1 falls from {I(e4p[0])} to {I(ew_p[0])} and P3 rises from {I(e4p[2])} to {I(ew_p[2])} (by-signal Inverse Vol P1 {I(i4p[0])} to {I(ivb_p[0])}, P3 {I(i4p[2])} to {I(ivb_p[2])}). "
           f"The book without Skewness is already positive in every subperiod, so the sleeve changes the profile of the book more than its sign. It also adds commodity beta, which Section 4.4 documents."))

    # ---- P6 pairs, best
    ewr = sorted(ps, key=lambda d: -d["ew"]["ir"]); ivr = sorted(ps, key=lambda d: -d["iv"]["ir"])
    nglp = [d["name"] for d in ps if "NGL" in d["name"]]
    chk(ewr[0]["name"] == "Energy-NGL" and ivr[0]["name"] == "Energy-NGL", "Energy-NGL best under both constructions")
    chk(set(d["name"] for d in ewr[:4]) == set(nglp) and set(d["name"] for d in ivr[:4]) == set(nglp), "the four NGL pairs are the four best under both constructions")
    sc = sorted(ps, key=lambda d: -d["corr"])
    chk(sc[0]["name"] == "Energy-NGL" and sc[1]["name"] == "Metals-Precious Metals" and sc[2]["corr"] < 0.1, "Energy-NGL and Metals-Precious Metals most correlated")
    chk(all(byn["Energy-NGL"]["ew"]["vol"] < x["vol"] for x in (en, ng)) and byn["Energy-NGL"]["ew"]["ir"] > en["ir"] and byn["Energy-NGL"]["iv"]["ir"] > enI["ir"] and byn["Energy-NGL"]["iv"]["ir"] > ngI["ir"] and byn["Energy-NGL"]["ew"]["ir"] < ng["ir"] and ng["ir"] - byn["Energy-NGL"]["ew"]["ir"] < 0.05, "Energy-NGL IR vs the single classes")
    A(("cap", "Table 9: Asset-class pairs"))
    A(("tbl", ["Pair", "EW PORT correlation", "Equal Weight IR", "Inverse Vol IR"], [[d["name"], U(d["corr"]), I(d["ew"]["ir"]), I(d["iv"]["ir"])] for d in ewr], [2.4, 1.6, 1.5, 1.5]))
    A(("note", "Note: The ten two-class pairs are formed as in Section 3.9: Equal Weight is Equal Weight within and across the two classes, Inverse Vol is Inverse Vol at both stages. IR is for the sample window, 1 January 2012 to 23 September 2026, net of 5 bp round-trip costs. The EW PORT correlation is the correlation of the two classes' Equal Weight portfolios (Section 4.4). Rows are sorted by Equal Weight IR. Energy includes Natural Gas."))
    A(("p", f"Table 9 turns to the ten pairs of asset classes. Energy-NGL is the best pair under both constructions (IR {I(byn['Energy-NGL']['ew']['ir'])} under Equal Weight and {I(byn['Energy-NGL']['iv']['ir'])} under Inverse Vol), even though it is the most correlated pair, with an EW PORT correlation of {U(byn['Energy-NGL']['corr'])}; the second most correlated pair, Metals-Precious Metals, is at {U(byn['Metals-Precious Metals']['corr'])} and no other pair exceeds {U(sc[2]['corr'])}. High correlation therefore does not make Energy-NGL a poor combination. "
           f"Its IR is close to that of NGL alone under Equal Weight ({I(ng['ir'])}) and above it under Inverse Vol ({I(byn['Energy-NGL']['iv']['ir'])} against {I(ngI['ir'])}), and it is well above Energy alone ({I(en['ir'])} and {I(enI['ir'])}), at a volatility of {V(byn['Energy-NGL']['ew']['vol'])} against {V(ng['vol'])} for NGL and {V(en['vol'])} for Energy. The four best pairs under both constructions are the four that contain NGL, so every pair that includes the class with the strongest premium ranks above every pair that does not. The mechanism is the one in Section 4.2: the combination is as good as the classes in it."))

    # ---- P7 weakest pairs and NGL-Agriculture
    neg = [d for d in ps if d["ew"]["ir"] < 0 or d["iv"]["ir"] < 0]
    chk({d["name"] for d in neg} == {"Metals-Precious Metals", "Metals-Agriculture", "Precious Metals-Agriculture"} and all(d["ew"]["ir"] < 0 and d["iv"]["ir"] < 0 for d in neg), "three negative pairs under both constructions")
    chk(all(d["ewp"][2] < 0 and d["ivp"][2] < 0 for d in neg), "negative pairs negative in P3 under both")
    chk(min(ps, key=lambda d: d["ew"]["ir"])["name"] == "Precious Metals-Agriculture" and min(ps, key=lambda d: d["iv"]["ir"])["name"] == "Precious Metals-Agriculture", "Precious Metals-Agriculture lowest under both")
    chk(set(d["name"] for d in sorted(ps, key=lambda d: d["ew"]["vol"])[:3]) == {d["name"] for d in neg}, "the three weakest pairs are the three lowest-volatility pairs under Equal Weight")
    chk(max(d["corr"] for d in neg) < 0.13, "weak pairs have correlation below 0.13")
    drop = max(ps, key=lambda d: d["ew"]["ir"] - d["iv"]["ir"])
    chk(drop["name"] == "NGL-Agriculture", "Inverse Vol pulls NGL-Agriculture down most")
    wn = pair_iv_weight("ngl", "agri")
    chk(wn < 0.5 and abs(wn - 0.5) > 0.05, "Inverse Vol puts less than half the weight on NGL in NGL-Agriculture")
    nm_ = lambda n: byn[n]
    A(("p", f"The three weakest pairs are Metals-Precious Metals ({I(nm_('Metals-Precious Metals')['ew']['ir'])} under Equal Weight, {I(nm_('Metals-Precious Metals')['iv']['ir'])} under Inverse Vol), Metals-Agriculture ({I(nm_('Metals-Agriculture')['ew']['ir'])}, {I(nm_('Metals-Agriculture')['iv']['ir'])}) and Precious Metals-Agriculture ({I(nm_('Precious Metals-Agriculture')['ew']['ir'])}, {I(nm_('Precious Metals-Agriculture')['iv']['ir'])}, the lowest of the ten under both constructions). They are the only pairs with a negative IR under either construction, and each is negative in P3 under both (Equal Weight {', '.join(I(d['ewp'][2]) for d in neg)}; Inverse Vol {', '.join(I(d['ivp'][2]) for d in neg)} for the three pairs in the order above). "
           f"They are built from the three classes with no positive full-sample IR of their own (Metals {I(me['ir'])}, Precious Metals {I(pm['ir'])}, Agriculture {I(ag['ir'])} under Equal Weight), and their EW PORT correlations are low ({U(min(d['corr'] for d in neg))} to {U(max(d['corr'] for d in neg))}). Low correlation reduces their volatility, which is the lowest of the ten pairs ({V(max(d['ew']['vol'] for d in neg))} or less under Equal Weight), but there is no premium to diversify. "
           f"Inverse Vol pulls one pair down more than any other, NGL-Agriculture ({I(drop['ew']['ir'])} to {I(drop['iv']['ir'])}). This is consistent with the weighting: NGL's portfolio is more than twice as volatile as Agriculture's ({V(ng['vol'])} against {V(ag['vol'])}), and Inverse Vol gives NGL an average weight of only {U(wn)} in the pair."))

    # ---- P8 central finding
    ewc = {"NGL": ng, "Energy": en, "Energy-NGL": byn["Energy-NGL"]["ew"]}
    ivc = {"NGL": ngI, "Energy": enI, "Energy-NGL": byn["Energy-NGL"]["iv"]}
    chk(all(ew5["ir"] < ewc[k]["ir"] for k in ("NGL", "Energy-NGL")) and all(x["ir"] < ivc[k]["ir"] for x in (ivb, K[II]) for k in ("NGL", "Energy-NGL")), "no five-class book beats NGL alone or Energy-NGL on IR")
    chk(ew5["ir"] > en["ir"] and ivb["ir"] > enI["ir"] and K[II]["ir"] < enI["ir"], "five-class books vs Energy alone")
    chk(all(x["ret"] < ewc[k]["ret"] for x in (ew5,) for k in ewc) and all(x["ret"] < ivc[k]["ret"] for x in (ivb, K[II]) for k in ivc), "five-class return below NGL, Energy and Energy-NGL")
    chk(max(ew5["vol"], ivb["vol"], K[II]["vol"]) < min(st(v, "EW PORT")["vol"] for v in CLS) and K[II]["vol"] < min(st(v, "Inverse Vol")["vol"] for v in CLS), "five-class volatility below every single class")
    A(("p", f"The central result of the section is that diversifying across all five classes lowers volatility but does not beat concentration. The five-class portfolios have a volatility of {V(K[II]['vol'])} to {V(ivb['vol'])}, below that of every single class (Agriculture, the lowest, is at {V(ag['vol'])}). Their return, however, is {R(ew5['ret'])} for Equal Weight and {R(ivb['ret'])} for by-signal Inverse Vol, against {R(ng['ret'])} for NGL, {R(en['ret'])} for Energy and {R(byn['Energy-NGL']['ew']['ret'])} for Energy-NGL under Equal Weight. "
           f"On IR, no five-class portfolio beats NGL alone ({I(ng['ir'])} under Equal Weight, {I(ngI['ir'])} under Inverse Vol) or the Energy-NGL pair ({I(byn['Energy-NGL']['ew']['ir'])} and {I(byn['Energy-NGL']['iv']['ir'])}), whereas the Equal Weight and by-signal Inverse Vol portfolios ({I(ew5['ir'])} and {I(ivb['ir'])}) are ahead of Energy alone ({I(en['ir'])} and {I(enI['ir'])}) and the portfolio with Inverse Vol at both stages ({I(K[II]['ir'])}) is not. "
           f"These comparisons use the same sample on which the concentration was found, so they describe the data and are not a test. The results are consistent with Virtual Barrels (2023, p. 86), who observes for practitioner commodity risk premia books that the largest share of the profit typically comes from energy futures and that the other sectors mostly provide diversification and reduce the denominator of the risk-adjusted return; his statement refers to diversified cross-sectional factor portfolios and gives no figures comparable to ours."))
    A(("p", f"Bogorad (2025a) finds, in an energy-only study, that low correlations across economically distinct strategies give strong risk-adjusted performance under simple aggregation. Our classes are also weakly correlated (Table 9), yet aggregation does not lift the IR above that of NGL alone, which is consistent with most of the classes added having no premium of their own. Equal Weight across classes also beats Inverse Vol across classes in this sample (Table 8), which parallels the finding of Fernandez-Perez, Fuertes and Miffre (2021) that equal-weight integration of styles is hard to beat in energy futures, although their comparison concerns styles and not asset classes. The universe, signals and period differ between the studies, so we compare only the pattern. Section 4.4 turns from performance to correlations."))
    return B


def s44():
    from text_corr import value_skew_positions
    B = []
    A = B.append
    cw = {v: corr_within(v) for v in CLS}
    cc = {k: corr_cross(k) for k in SER7}
    bs = bystyle(); b4 = bystyle4()
    L = lambda d, f=N: ", ".join(f"{f(d[v])} in {NM[v]}" for v in CLS[:-1]) + f" and {f(d['agri'])} in Agriculture"

    A(("h2", "4.4 Correlations"))
    A(("p", "This section looks at how the signals and portfolios move together. Correlations are Pearson correlations of daily net log returns over the sample window (Section 3.9). We report them to complement the performance results of Section 4.3, because they show which sleeves and classes add diversification, and because they bear on the interpretation of the Skewness sleeve in Section 5.3. We look first within each asset class, among its five sleeves and two portfolios, then across asset classes for each series type, and finally between the cross-commodity portfolio and traditional assets. The correlation matrices themselves are not reproduced here. The correlations describe co-movement in this sample and the explanations we offer for them are consistent with the patterns, not tests of them."))

    # ---- within
    vew = {v: cw[v].loc["Value", "EW PORT"] for v in CLS}; sew = {v: cw[v].loc["Skewness", "EW PORT"] for v in CLS}
    for v in CLS:
        chk(vew[v] == min(cw[v].loc[k, "EW PORT"] for k in SLEEVES), f"Value least correlated with EW PORT in {v}")
        chk(sorted(SLEEVES, key=lambda k: cw[v].loc[k, "EW PORT"])[1] == "Skewness", f"Skewness second least correlated in {v}")
    chk(vew["agri"] > 0 and vew["ngl"] > 0 and all(vew[v] < 0 for v in ("metals", "energy", "precious")), "Value negative with EW PORT in Metals, Energy, Precious Metals; positive in NGL, Agriculture")
    chk(all(0.2 < sew[v] < 0.45 for v in CLS), "Skewness correlation with EW PORT between 0.2 and 0.45")
    mine = min(min(cw[v].loc[k, "EW PORT"] for k in ("Momentum", "Carry", "CarryMom")) for v in CLS)
    chk(mine > 0.5, "Momentum, Carry and Carry-Momentum correlate above 0.5 with the portfolio in every class")
    A(("p", f"Within each class, the two sleeves that are not built on trend or curve shape are the least correlated with the portfolio. Value has the lowest correlation with the Equal Weight portfolio (EW PORT) of the five sleeves in every class: {L(vew)}. Skewness has the second lowest in every class ({L(sew)}). Momentum, Carry and Carry-Momentum all correlate at {U(mine)} or more with the portfolio in every class. "
           f"Value is negative in Metals, Energy and Precious Metals, and positive in NGL and Agriculture, where it is still the lowest of the five. This is consistent with Value and Skewness acting as diversifiers inside the portfolio, and it agrees with Section 4.2, where adding Skewness cuts volatility in every class."))

    vm = {v: cw[v].loc["Value", "Momentum"] for v in CLS}
    chk(all(x < 0 for x in vm.values()), "Value negative with Momentum everywhere")
    top = {}
    for v in CLS:
        pr = {(x, y): cw[v].loc[x, y] for i, x in enumerate(SLEEVES) for y in SLEEVES[i + 1:]}
        top[v] = max(pr, key=pr.get)
    chk(all(top[v] == ("Momentum", "Carry") for v in ("energy", "ngl", "agri")) and all(top[v] == ("Carry", "CarryMom") for v in ("metals", "precious")), "closest base pairs")
    A(("p", f"Value is negatively correlated with Momentum in all five classes ({L(vm)}). This is consistent with a rule that buys products far below their five-year average opposing one that follows the recent trend. "
            f"Among the other pairs, Momentum and Carry are the most correlated in Energy ({N(cw['energy'].loc['Momentum', 'Carry'])}), NGL ({N(cw['ngl'].loc['Momentum', 'Carry'])}) and Agriculture ({N(cw['agri'].loc['Momentum', 'Carry'])}), consistent with a common driver behind the two signals that we do not test. In Metals and Precious Metals the closest pair is instead Carry and Carry-Momentum ({N(cw['metals'].loc['Carry', 'CarryMom'])} and {N(cw['precious'].loc['Carry', 'CarryMom'])})."))

    # ---- Skewness pairing
    sv = {v: cw[v].loc["Skewness", "Value"] for v in CLS}
    smom = {v: cw[v].loc["Skewness", "Momentum"] for v in CLS}; scar = {v: cw[v].loc["Skewness", "Carry"] for v in CLS}
    chk(sv["precious"] == min(sv.values()) and sv["ngl"] > 0 and all(sv[v] < 0 for v in ("metals", "energy", "precious", "agri")), "Skewness-Value pattern")
    chk(smom["ngl"] == min(smom.values()) and scar["ngl"] == min(scar.values()) and scar["precious"] > 0.1, "Skewness most negative with Momentum and Carry in NGL; positive with Carry in Precious Metals")
    chk(all(abs(smom[v]) < 0.1 for v in ("metals", "precious", "agri")) and all(abs(scar[v]) < 0.1 for v in ("metals", "energy", "agri")), "Skewness near zero with Momentum and Carry outside NGL and Precious Metals")
    pc, vs_lo, vs_hi = value_skew_positions()
    chk(pc["Palladium"] < pc["Gold"] < -0.3 and vs_lo > 65, "Value and Skewness hold opposite positions in Precious Metals")
    A(("p", f"Skewness pairs differently from class to class. Its correlation with Value is negative in four classes and strongest in Precious Metals ({L(sv)}); NGL is the exception, where it is positive. In Precious Metals the two sleeves tend to hold opposite positions (daily position correlation {N(pc['Palladium'])} in Palladium and {N(pc['Gold'])} in Gold): Value is short when a metal trades well above its five-year average, and Skewness is then long on {U(vs_lo, 0)}% to {U(vs_hi, 0)}% of those days across the four metals, which is consistent with Value shorting rallies that Skewness stays long. "
           f"With Momentum and Carry, Skewness is close to zero in Metals and Agriculture, and most negative in NGL ({N(smom['ngl'])} with Momentum and {N(scar['ngl'])} with Carry); in Precious Metals it is positive with Carry ({N(scar['precious'])}). Finally, Inverse Vol tracks its own EW PORT closely in every class, with correlations between {U(min(cw[v].loc['Inverse Vol', 'EW PORT'] for v in CLS))} and {U(max(cw[v].loc['Inverse Vol', 'EW PORT'] for v in CLS))}, as expected for two weightings of the same five sleeves."))

    # ---- across classes
    pr = lambda k: sorted(combinations(CLS, 2), key=lambda ab: -cc[k].loc[ab[0], ab[1]])
    for k in SER7:
        chk(pr(k)[0] == ("energy", "ngl"), f"Energy-NGL most correlated for {k}")
    chk(all(pr(k)[1] == ("metals", "precious") for k in ("Momentum", "Value", "Skewness", "EW PORT", "Inverse Vol")), "Metals-Precious Metals second")
    chk(pr("Carry")[1] == ("metals", "ngl") and pr("CarryMom")[1] == ("energy", "agri"), "second places for Carry and Carry-Momentum")
    g = lambda k, a, b: cc[k].loc[a, b]
    avgabs = {k: float(np.mean([abs(cc[k].loc[a, b]) for a, b in combinations(CLS, 2)])) for k in SER7}
    chk(min(avgabs, key=avgabs.get) == "CarryMom" and sorted(avgabs, key=avgabs.get)[1] == "Carry", "Carry-Momentum lowest, Carry next")
    mxcm = max(abs(cc["CarryMom"].loc[a, b]) for a, b in combinations(CLS, 2))
    en_ngl = {k: g(k, "energy", "ngl") for k in SER7}
    chk(min(en_ngl.values()) == en_ngl["CarryMom"] and max(en_ngl.values()) == en_ngl["Value"], "Energy-NGL range from Carry-Momentum to Value")
    sec = {k: g(k, "metals", "precious") for k in ("Momentum", "Value", "Skewness", "EW PORT", "Inverse Vol")}
    # largest correlation outside the top two for each series, to state that the rest are small
    rest = max(cc[k].loc[a, b] for k in SER7 for a, b in combinations(CLS, 2) if (a, b) not in (("energy", "ngl"),) and not ((a, b) == ("metals", "precious") and k in sec) and not (k == "Carry" and (a, b) == ("metals", "ngl")) and not (k == "CarryMom" and (a, b) == ("energy", "agri")))
    chk(rest < 0.25, "all other cross-class correlations below 0.25")
    A(("p", f"Across asset classes, Energy and NGL are the most correlated pair for all seven series: Momentum ({U(en_ngl['Momentum'])}), Carry ({U(en_ngl['Carry'])}), Carry-Momentum ({U(en_ngl['CarryMom'])}), Value ({U(en_ngl['Value'])}), Skewness ({U(en_ngl['Skewness'])}), EW PORT ({U(en_ngl['EW PORT'])}) and Inverse Vol ({U(en_ngl['Inverse Vol'])}), consistent with both classes trading the same hydrocarbon complex. "
           f"Metals and Precious Metals are the second most correlated pair for Momentum ({U(sec['Momentum'])}), Value ({U(sec['Value'])}), Skewness ({U(sec['Skewness'])}), EW PORT ({U(sec['EW PORT'])}) and Inverse Vol ({U(sec['Inverse Vol'])}), a link between the two metal groups that we do not explain; for Carry the second place is Metals-NGL ({U(g('Carry', 'metals', 'ngl'))}) and for Carry-Momentum Energy-Agriculture ({U(g('CarryMom', 'energy', 'agri'))}), with Metals-Precious Metals essentially uncorrelated in Carry-Momentum ({N(g('CarryMom', 'metals', 'precious'))}). "
           f"Every other pairwise correlation is below {U(rest)}. Carry-Momentum has the lowest cross-commodity correlations of the seven series: its correlations with the same strategy in other classes average {U(avgabs['CarryMom'])} in magnitude (Carry {U(avgabs['Carry'])}), and none of its ten pairwise readings exceeds {U(mxcm)}. In Section 4.3 the pair with the highest correlation, Energy-NGL, was also the best pair, so a low correlation is not what makes a combination work."))

    # ---- traditional assets
    bm = {k: bench_corr(bs[k]) for k in SER7}; b4m = {k: bench_corr(b4[k]) for k in ("EW PORT", "Inverse Vol")}
    chk(all(bm[k]["Equity"] < 0 for k in ("Momentum", "Carry", "CarryMom", "EW PORT", "Inverse Vol")) and bm["Value"]["Equity"] > 0 and bm["Skewness"]["Equity"] > 0, "equity correlation signs by strategy")
    chk(bm["EW PORT"]["60/40 Portfolio"] < 0 and bm["Inverse Vol"]["60/40 Portfolio"] < 0, "negative to 60/40")
    chk(bm["EW PORT"]["Commodity Index"] > 0.1 and bm["Inverse Vol"]["Commodity Index"] > 0.1 and bm["Skewness"]["Commodity Index"] > 0.4 and all(abs(b4m[k]["Commodity Index"]) < 0.1 for k in b4m), "commodity index correlation positive with Skewness, near zero without")
    chk(all(abs(bm[k]["Fixed Income"]) < 0.06 for k in SER7) and all(abs(bm[k]["Gold"]) < 0.2 for k in SER7), "Fixed Income and Gold correlations small")
    chk(all(abs(bm[k]["Gold"]) < 0.03 for k in ("Momentum", "Carry", "CarryMom")), "Momentum, Carry, Carry-Momentum essentially uncorrelated with Gold")
    bdr = bench_returns()
    nobs = int(pd.concat([bs["EW PORT"].loc["2012-01-01":"2026-09-23"], bdr["Equity"], bdr["Fixed Income"], bdr["Commodity Index"], bdr["Gold"]], axis=1).dropna().shape[0])
    chk(3000 < nobs < 3800, "number of shared days")
    A(("p", f"The last comparison is with traditional assets. We use daily returns of four exchange-traded funds as proxies: SPY for Equity, AGG for Fixed Income, DBC for a Commodity Index and GLD for Gold, and a 60/40 portfolio of SPY and AGG rebalanced daily. Prices are adjusted closing prices from Yahoo Finance, downloaded on 12 October 2026, and correlations use the days on which the ETF series and the strategy series are both available, {nobs:,} days from 2012 to 23 September 2026. Table 10 gives the correlations of the five by-signal strategies and of the two reference cross-commodity portfolios."))
    rows = [[SL[k]] + [N(bm[k][c]) for c in ("Equity", "Fixed Income", "Commodity Index", "Gold", "60/40 Portfolio")] for k in SLEEVES]
    rows += [["Equal Weight (EW PORT)"] + [N(bm["EW PORT"][c]) for c in ("Equity", "Fixed Income", "Commodity Index", "Gold", "60/40 Portfolio")]]
    rows += [["Inverse Vol"] + [N(bm["Inverse Vol"][c]) for c in ("Equity", "Fixed Income", "Commodity Index", "Gold", "60/40 Portfolio")]]
    A(("cap", "Table 10: Correlation of the cross-commodity portfolio and its signals with traditional assets"))
    A(("tbl", ["Series", "Equity", "Fixed Income", "Commodity Index", "Gold", "60/40"], rows, [2.2, 0.9, 1.1, 1.3, 0.8, 0.9]))
    A(("note", "Note: Pearson correlations of daily returns. Equity is SPY, Fixed Income AGG, Commodity Index DBC, Gold GLD and 60/40 a daily-rebalanced portfolio of 60% SPY and 40% AGG (adjusted prices, Yahoo Finance, downloaded 12 October 2026). The first five rows are the strategies of Table 8 equal-weighted across the five asset classes; Equal Weight and Inverse Vol are the two reference cross-commodity portfolios (the by-signal portfolios). Energy includes Natural Gas."))

    oil = [legs("energy", p)["p3"]["long_pct"] for p in ("WTI", "Brent", "RBOB", "HeatingOil")]
    nglp = [legs("ngl", p)["p3"]["long_pct"] for p in ("Ethane", "Propane", "Butane", "Isobutane")]
    chk(min(oil) > 85 and min(nglp) > 75, "oil and NGL products long-biased in P3")
    c5e, c5i, c4e, c4i = bm["EW PORT"], bm["Inverse Vol"], b4m["EW PORT"], b4m["Inverse Vol"]
    A(("p", f"The cross-commodity portfolios diversify equity and bonds but are not free of commodity beta. Both correlate negatively with Equity (Equal Weight {N(c5e['Equity'])}, Inverse Vol {N(c5i['Equity'])}) and with the 60/40 portfolio ({N(c5e['60/40 Portfolio'])} and {N(c5i['60/40 Portfolio'])}), and are close to zero against Fixed Income ({N(c5e['Fixed Income'])} and {N(c5i['Fixed Income'])}) and Gold ({N(c5e['Gold'])} and {N(c5i['Gold'])}). Against the Commodity Index they are positive ({N(c5e['Commodity Index'])} and {N(c5i['Commodity Index'])}). Momentum, Carry and Carry-Momentum are negatively correlated with Equity and essentially uncorrelated with Gold ({N(bm['Momentum']['Gold'])}, {N(bm['Carry']['Gold'])} and {N(bm['CarryMom']['Gold'])}), whereas Value ({N(bm['Value']['Equity'])}) and Skewness ({N(bm['Skewness']['Equity'])}) are the two strategies positively correlated with Equity. "
           f"The positive link to the Commodity Index comes from Skewness, which correlates {N(bm['Skewness']['Commodity Index'])} with it ({N(bm['Skewness']['Gold'])} with Gold). Without Skewness the correlations of the portfolios with the Commodity Index are {N(c4e['Commodity Index'])} and {N(c4i['Commodity Index'])}. This is consistent with a Skewness sleeve that is mostly long, as the four oil products (long on {min(oil):.0f}% to {max(oil):.0f}% of P3 days) and the four NGL products ({min(nglp):.0f}% to {max(nglp):.0f}%) show, and that therefore moves with the commodity market, which bears on how the Skewness gains are read."))
    A(("p", "Taken together, the correlations relate to two features of the results above. The sleeves with the weakest ties to their portfolios, Value and Skewness, are the ones that lift the portfolio in the periods in which Momentum, Carry and Carry-Momentum fade, and the high correlation between Energy and NGL, the two classes with a premium, does not prevent them from forming the best pair. They also show what the cross-commodity portfolio gives up: it offers diversification against equity and bonds, but with Skewness it carries some exposure to the commodity market itself. Section 5 discusses why the premium is concentrated in NGL and Energy."))
    return B


def blocks():
    out = []
    out += s42()
    out += s43()
    out += s44()
    return out


def _print(bl):
    for b in bl:
        if b[0] == "tbl":
            print("TBL", b[1])
            for r in b[2]:
                print("   ", r)
        elif b[0] == "fig":
            print("FIG", b[1], b[2])
        else:
            print(b[0].upper(), b[1])
            print()


def words(bl):
    return sum(len(b[1].split()) for b in bl if b[0] in ("p", "note", "cap", "h2", "h3")) + sum(len(" ".join(" ".join(r) for r in b[2]).split()) for b in bl if b[0] == "tbl")


if __name__ == "__main__":
    bl = blocks()
    _print(bl)
    print("PARAGRAPH WORDS", [len(b[1].split()) for b in bl if b[0] == "p"])
    print("TOTAL WORDS", words(bl))
