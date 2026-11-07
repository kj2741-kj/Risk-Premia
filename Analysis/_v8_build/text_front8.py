from facts3 import *
from text_cross8 import corr8, cross8
from text_gasem import gasem
import importlib

W3 = ("p1", "p2", "p3")


def key_findings(old_kf):
    """Nine Key Findings. old_kf[1:4] are the v7 bullets on Petroleum, Metals and Precious Metals / Agriculture (0930 basis, unchanged); the rest is rewritten on six buckets."""
    assert len(old_kf) == 8 and old_kf[1].startswith("Petroleum's") and old_kf[2].startswith("In Metals") and old_kf[3].startswith("Precious Metals and Agriculture")
    ngl_ew, ngl_iv = st("ngl", "EW PORT"), st("ngl", "Inverse Vol")
    four = [m for m in MEMBERS["ngl"] if m[0] == "ngl"]
    cs4 = pd.DataFrame({k: ew_intersection([nets()[m][k] for m in four]) for k in SLEEVES})
    ew_4p = stats(cs4.mean(axis=1, skipna=False))
    best_other = max((st(t, "EW PORT")["ir"], t) for t in BUCKETS if t != "ngl")
    best_other_iv = max((st(t, "Inverse Vol")["ir"], t) for t in BUCKETS if t != "ngl")
    chk(best_other[1] == "petroleum" and best_other_iv[1] == "petroleum", "Petroleum is the best other bucket")
    pn, pc_, pcm, pv, ps = (per("ngl", k) for k in ("Momentum", "Carry", "CarryMom", "Value", "Skewness"))
    chk(all(x > 0 for x in pn + pc_ + pcm), "NGL Momentum, Carry and Carry-Momentum positive in every period")
    kf = []
    kf.append(f"NGL is the strongest bucket in the research: Equal Weight (IR {I(ngl_ew['ir'])}) and Inverse Vol (IR {I(ngl_iv['ir'])}) are well ahead of every other bucket (the best of the rest is Petroleum at {I(best_other[0])} and {I(best_other_iv[0])}), and Momentum, Carry, and Carry-Momentum are each positive in every period, as they are in Petroleum. "
              f"Naphtha, added as the fifth product in v8, lifts the Equal Weight IR from {I(ew_4p['ir'])} (the four Mont Belvieu products) to {I(ngl_ew['ir'])}. Value (IR {I(st('ngl', 'Value')['ir'])}) and Skewness (IR {I(st('ngl', 'Skewness')['ir'])}) are the exceptions: Value is negative in P1 ({I(pv[0])}), and Skewness is negative in P1 ({I(ps[0])}) and strongly positive in P2 ({I(ps[1])}).")
    # Gas and Emissions
    ge, gi = st("pen", "EW PORT"), st("pen", "Inverse Vol")
    gp = {p: stats(ew_intersection([nets()[(a, p)][k] for k in SLEEVES]))["ir"] for a, p in MEMBERS["pen"]}
    ewp = PORT["pen"][0].loc["2012-01-01":].dropna(); yl = yearly_log(ewp)
    mask = ~((ewp.index >= "2021-07-01") & (ewp.index <= "2023-06-30"))
    ir_ex = stats(ewp[mask])["ir"]
    chk(st("pen", "Carry")["ir"] == max(st("pen", k)["ir"] for k in SLEEVES) and st("pen", "Value")["ir"] < 0, "Carry is the strongest Gas and Emissions sleeve; Value negative")
    chk(round(yl[2021] / ewp.sum() * 100) == 42 and round(ir_ex, 2) == 0.30, "Gas and Emissions crisis concentration")
    kf.append(f"Gas and Emissions (Henry Hub, TTF, UK Gas and EUA) earns Equal Weight IR {I(ge['ir'])} and Inverse Vol IR {I(gi['ir'])} at {V(ge['vol'])} volatility, with Carry the strongest sleeve (IR {I(st('pen', 'Carry')['ir'])}) and Value (IR {I(st('pen', 'Value')['ir'])}) the only negative one. The edge sits in European gas, TTF (combined IR {I(gp['TTF'])}) and UK Gas ({I(gp['UKGas'])}), not in Henry Hub ({I(gp['NatGas'])}) or EUA ({I(gp['EUA'])}), "
              f"and in one episode: 2021 alone is {yl[2021] / ewp.sum() * 100:.0f}% of the Equal Weight log return, and excluding July 2021 to June 2023 the IR falls to {I(ir_ex)}.")
    kf.append(old_kf[1]); kf.append(old_kf[2]); kf.append(old_kf[3])
    # Skewness (six research buckets plus US Power on its own 2017 window)
    from power_facts import STY_P, stp, EW_P
    sk_ir = {t: st(t, "Skewness")["ir"] for t in BUCKETS}; sk_ir["power"] = stp(STY_P["Skewness"])["ir"]
    sk_p = {t: per(t, "Skewness") for t in BUCKETS}; sk_p["power"] = [None, stp(STY_P["Skewness"], "p2")["ir"], stp(STY_P["Skewness"], "p3")["ir"]]
    neg_full = [t for t in sk_ir if sk_ir[t] < 0]; neg_p1 = [t for t in BUCKETS if sk_p[t][0] < 0]; pos_p3 = [t for t in sk_p if sk_p[t][2] > 0]
    chk(neg_full == ["metals"] and set(neg_p1) == {"metals", "petroleum", "ngl", "precious"} and len(pos_p3) == 6 and "metals" not in pos_p3, f"Skewness signs {neg_full} {neg_p1} {pos_p3}")
    pet_long = [legs("energy", p)["p3"]["long_pct"] for p in PRODUCTS["petroleum"]]
    chk(round(min(pet_long)) == 89 and round(max(pet_long)) == 100, "four oil products long on 89% to 100% of P3 days")
    bs, bs4 = bystyle(), bystyle4(); bS = bench_corr(bs["Skewness"])
    ttf_long = legs("emissions", "TTF")["full"]["long_pct"]
    nw = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven"}
    kf.append(f"Skewness is a different kind of premium from the other four. It is positive in {nw[len(sk_ir) - len(neg_full)]} of the seven buckets (Petroleum, Gas and Emissions, NGL, Precious Metals, Agriculture and, marginally, US Power) and negative in Metals; it is negative in P1 in {nw[len(neg_p1)]} of the six buckets that have a P1 and positive in P3 in {nw[len(pos_p3)]} of the seven. "
              f"Its gains in Petroleum, NGL and Precious Metals are largely long positions held after crashes (the four oil products were long on {min(pet_long):.0f}% to {max(pet_long):.0f}% of P3 days), consistent with its {N(bS['Commodity Index'])} correlation with a passive commodity index in the seven-bucket book, unlike Momentum, Carry and Carry-Momentum. "
              f"Gas and Emissions is the exception to the long bias: Skewness is long on only {ttf_long:.0f}% of TTF days and earns its gain on the short side.")
    c8 = corr8(); B, F = cross8()
    best, b2 = F["best"], F["b2"]; ew, iv = F["ew"], F["iv"]; e6, i6 = F["e6"], F["i6"]
    cx = corr_cross("EW PORT")
    kf.append(f"Petroleum-NGL is the most correlated pair of buckets for all seven series types (EW PORT correlation {U(cx.loc['petroleum', 'ngl'])}); Gas and Emissions-NGL ({U(cx.loc['pen', 'ngl'])}), Petroleum-Gas and Emissions ({U(cx.loc['petroleum', 'pen'])}) and Metals-Precious Metals ({U(cx.loc['metals', 'precious'])}) follow, and no other pair exceeds 0.09; US Power is uncorrelated with every other bucket ({N(min(cx.loc['power', b] for b in BUCKETS))} to {N(max(cx.loc['power', b] for b in BUCKETS))}). "
              f"Yet standalone Petroleum-NGL is the best-performing of the 21 pairs (Equal Weight IR {I(best['ew']['ir'])}, Inverse Vol IR {I(best['iv']['ir'])}), proving correlation and performance are separate questions.")
    kf.append(f"The cross-commodity portfolio (each strategy equal-weighted across the seven buckets, then the five strategies combined; common dates from January 2015) delivers Equal Weight IR {I(ew['ir'])} and Inverse Vol IR {I(iv['ir'])} at a volatility of {V(ew['vol'])} and {V(iv['vol'])}, and is positive in every period under both constructions. "
              f"Adding US Power to the six research buckets lowers the Equal Weight IR on the same window from {I(e6['ir'])} to {I(ew['ir'])} but makes the maximum drawdown shallower ({M(e6['mdd'])} to {M(ew['mdd'])}), because Power, uncorrelated with the rest, carries {F['share_pw']:.0f}% of the book's variance at a weight of one seventh. "
              f"The book is negatively correlated with equity (Equal Weight {N(F['bE']['Equity'])}, Inverse Vol {N(F['bI']['Equity'])}) and a traditional 60/40 portfolio ({N(F['bE']['60/40 Portfolio'])}, {N(F['bI']['60/40 Portfolio'])}), but with Skewness included it is positively correlated with a passive commodity index ({N(F['bE']['Commodity Index'])}, {N(F['bI']['Commodity Index'])}; {N(F['b4E']['Commodity Index'])} and {N(F['b4I']['Commodity Index'])} without Skewness), so it diversifies equity and bonds but is no longer free of commodity beta.")
    kf.append(f"Diversifying across all seven buckets lowers volatility but not risk-adjusted return: the Petroleum-NGL and Gas and Emissions-NGL pairs earn more per unit of risk (IR {I(best['ew']['ir'])} and {I(best['iv']['ir'])}; {I(b2['ew']['ir'])} and {I(b2['iv']['ir'])}) than the seven-bucket book (IR {I(ew['ir'])} and {I(iv['ir'])}), at about {V(best['ew']['vol'])} volatility against {V(ew['vol'])}, "
              f"because the extra diversification comes from Metals, Precious Metals, Agriculture and US Power, where the combined signals earn little (US Power {I(stp(EW_P)['ir'])} from 2017) or nothing.")
    chk(len(kf) == 9, "nine key findings (the US Power finding is inserted by the build)")
    return kf


def liquidity_paragraph():
    liq = pd.read_csv(os.path.join(REPO, "Analysis", "Liquidity_Cal2025_results.csv")).set_index("product")
    pl = pd.read_csv(os.path.join(REPO, "Analysis", "Power_Liquidity_Cal2025_results.csv")).set_index("product")
    grp = {"Metals": ["Copper", "Aluminium", "Zinc", "Lead"], "Petroleum": ["Brent", "WTI", "HeatingOil", "RBOB"], "Gas and Emissions": ["NatGas", "TTF", "UKGas", "EUA"], "Precious Metals": ["Gold", "Silver", "Platinum", "Palladium"],
           "NGL": ["Propane", "Butane", "Ethane", "Isobutane", "Naphtha"], "Agriculture": ["Soybean", "Coffee", "Corn", "SoybeanOil", "Wheat", "Sugar"]}
    pw_ = ["PJM_Peak", "ERCOT_Peak", "PJM_OffPeak", "ERCOT_OffPeak", "MISO_Peak"]
    prod = [p for g in grp.values() for p in g]
    chk(len(prod) == 27 and len(pw_) == 5, "27 bucket products and 5 Power series")
    x = liq["x_strip"]; L = liq["L_strip"]; xp = pl["x_strip"]; Lp = pl["L_strip"]
    allx = pd.concat([x.loc[prod + ["SingaporeGasoil"]], xp])
    chk(allx.idxmax() == "Brent" and allx.idxmin() == "Isobutane", "Brent most liquid, Isobutane least liquid of the table")
    chk(len(allx) == 34, "34 products in the table")
    sp = {g: (x.loc[ps].max() / x.loc[ps].min()) for g, ps in grp.items()}
    nn = [p for p in prod if p not in grp["NGL"]]
    chk(x.loc[nn].idxmin() == "Lead", "Lead is the least liquid product outside NGL and US Power")
    chk(float(xp.loc[pw_].max()) < float(x["Lead"]) and float(xp.loc[pw_].min()) > float(x.loc[grp["NGL"]].min()), "US Power sits below Lead and above Isobutane in turnover")
    Lmax_nn = float(L.loc[nn].max()); chk(round(Lmax_nn, 2) == 0.05, "at most 0.05 days outside NGL and Power")
    sp_pw = float(xp.loc[pw_].max() / xp.loc[pw_].min()); chk(round(sp_pw, 1) == 46.8, "Power spread 46.8-fold")
    f1 = lambda v: f"{v:,.1f}"
    s = (f"Results across 34 products. Dollar risk turnover ranges from USD {f1(x['Brent'])} million per day for Brent, the most liquid, to USD {x['Isobutane']:.3f} million for Isobutane, the least liquid, a span of five orders of magnitude. "
         f"Within buckets, the spread between the most and least liquid products is narrow in Agriculture ({sp['Agriculture']:.1f}-fold; Soybean {f1(x['Soybean'])} to Sugar {f1(x['Sugar'])}) and Petroleum ({sp['Petroleum']:.1f}-fold; Brent {f1(x['Brent'])} to RBOB {f1(x['RBOB'])}), "
         f"intermediate in Metals ({sp['Metals']:.1f}-fold; Copper {f1(x['Copper'])} to Lead {f1(x['Lead'])}) and in Gas and Emissions ({sp['Gas and Emissions']:.1f}-fold; Henry Hub {f1(x['NatGas'])} to UK Gas {f1(x['UKGas'])}), and wide in Precious Metals ({sp['Precious Metals']:.1f}-fold; Gold {f1(x['Gold'])} to Palladium {f1(x['Palladium'])}). "
         f"NGL is the outlier, with a spread of {sp['NGL']:,.1f}-fold (Propane {x['Propane']:.2f} to Isobutane {x['Isobutane']:.3f}) and a level far below the other buckets: Propane, the most liquid NGL product, trades about one quarter of the risk turnover of Lead ({f1(x['Lead'])}), the least liquid product outside NGL and US Power. "
         f"The US Power series lie between the two groups: PJM Peak ({xp['PJM_Peak']:.2f}) trades about half the risk turnover of Lead, ERCOT Peak and PJM OffPeak {xp['ERCOT_Peak']:.2f} and {xp['PJM_OffPeak']:.2f}, and ERCOT OffPeak and MISO Peak {xp['ERCOT_OffPeak']:.2f} and {xp['MISO_Peak']:.2f}, below Ethane ({x['Ethane']:.2f}); the spread across the five series is {sp_pw:.1f}-fold. "
         f"In terms of the reference position, a USD 1 million one-sigma position equals at most {Lmax_nn:.2f} days of market risk turnover in any product outside NGL and US Power, against {Lp['PJM_Peak']:.2f}, {Lp['ERCOT_Peak']:.2f}, {Lp['PJM_OffPeak']:.2f}, {Lp['ERCOT_OffPeak']:.1f} and {Lp['MISO_Peak']:.1f} days in PJM Peak, ERCOT Peak, PJM OffPeak, ERCOT OffPeak and MISO Peak, "
         f"{L['Propane']:.2f} days in Propane, {L['Ethane']:.1f} in Ethane, {L['Naphtha']:.1f} in Naphtha and {L['Isobutane']:.0f} in Isobutane. "
         f"Isobutane averages {liq.loc['Isobutane', 'adv_strip']:.0f} lots per day and trades on only {liq.loc['Isobutane', 'share_days_print'] * 100:.0f}% of 2025 days, and Naphtha averages {liq.loc['Naphtha', 'adv_strip']:.0f} lots per day on the Bloomberg series and prints on {liq.loc['Naphtha', 'share_days_print'] * 100:.0f}% of days, so neither can absorb a position of meaningful size. "
         f"This bears on the main results, since NGL is the bucket in which the premium is strongest: the returns reported there may not be capturable at a scale comparable to that of the other buckets. The same limit applies to US Power, where ERCOT OffPeak and MISO Peak need {Lp['ERCOT_OffPeak']:.1f} days of market turnover per USD 1 million of one-sigma risk. "
         f"NGL volumes refer to CME only, and Naphtha volume is the Bloomberg series, a partial view of the swap market, so both are lower bounds. The product-level results are reported in Table A26.")
    chk(0.22 < x["Propane"] / x["Lead"] < 0.27 and 0.45 < xp["PJM_Peak"] / x["Lead"] < 0.55 and xp["ERCOT_OffPeak"] < x["Ethane"] and xp["MISO_Peak"] < x["Ethane"], "Propane about one quarter of Lead; PJM Peak about half; the two low Power series below Ethane")
    return s
