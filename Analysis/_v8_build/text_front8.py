from facts3 import *
from text_cross8 import corr8, cross8
from text_gasem import gasem
import importlib

W3 = ("p1", "p2", "p3")


def key_findings(old_kf):
    """Nine Key Findings. old_kf[1:3] are the v7 bullets on Petroleum and Metals (0930 basis, unchanged); old_kf[3] (Precious Metals and Agriculture) is replaced by a bullet on Precious Metals, Agriculture and Softs;
    the rest is rewritten on the seven buckets (Agriculture split into Agriculture and Softs, Natural Gasoline in NGL, 10 November 2026)."""
    assert len(old_kf) == 8 and old_kf[1].startswith("Petroleum's") and old_kf[2].startswith("In Metals") and old_kf[3].startswith("Precious Metals and Agriculture")
    ngl_ew, ngl_iv = st("ngl", "EW PORT"), st("ngl", "Inverse Vol")
    M5 = MEMBERS["ngl"]
    def basis(members):
        cs = pd.DataFrame({k: ew_intersection([nets()[m][k] for m in members]) for k in SLEEVES})
        return stats(cs.mean(axis=1, skipna=False)), stats(inverse_vol(cs))
    e3, i3 = basis(M5[:3]); e4, i4 = basis(M5[:4])
    best_other = max((st(t, "EW PORT")["ir"], t) for t in BUCKETS if t != "ngl")
    best_other_iv = max((st(t, "Inverse Vol")["ir"], t) for t in BUCKETS if t != "ngl")
    chk(best_other[1] == "petroleum" and best_other_iv[1] == "petroleum", "Petroleum is the best other bucket")
    pn, pc_, pcm, pv, ps = (per("ngl", k) for k in ("Momentum", "Carry", "CarryMom", "Value", "Skewness"))
    chk(all(x > 0 for x in pn + pc_ + pcm), "NGL Momentum, Carry and Carry-Momentum positive in every period")
    chk(round(e3["ir"], 2) == 1.20 and round(e4["ir"], 2) == 1.43 and e4["ir"] > ngl_ew["ir"] and i4["ir"] > ngl_iv["ir"], "NGL: three-product 1.20, four-product 1.43, five-product lower than the four-product")
    kf = []
    kf.append(f"NGL is the strongest bucket in the research: Equal Weight (IR {I(ngl_ew['ir'])}) and Inverse Vol (IR {I(ngl_iv['ir'])}) are well ahead of every other bucket (the best of the rest is Petroleum at {I(best_other[0])} and {I(best_other_iv[0])}), and Momentum, Carry, and Carry-Momentum are each positive in every period, as they are in Petroleum. "
              f"Naphtha, added as the fourth product in v8, lifted the Equal Weight IR from {I(e3['ir'])} (the three Mont Belvieu products) to {I(e4['ir'])}; Natural Gasoline (CME MMB), added as the fifth product on 10 November 2026, lowers it to {I(ngl_ew['ir'])} (Inverse Vol {I(i4['ir'])} to {I(ngl_iv['ir'])}) because its Momentum and Carry are close to zero, while the Equal Weight volatility and maximum drawdown are lower. Value (IR {I(st('ngl', 'Value')['ir'])}) and Skewness (IR {I(st('ngl', 'Skewness')['ir'])}) are the exceptions: Value is negative in P1 ({I(pv[0])}), and Skewness is negative in P1 ({I(ps[0])}) and strongly positive in P2 ({I(ps[1])}).")
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
    pm_ = {k: st('petroleum', k)['ir'] for k in SLEEVES}; pew, piv = st('petroleum', 'EW PORT'), st('petroleum', 'Inverse Vol')
    chk(max(pm_, key=pm_.get) == 'CarryMom' and [k for k in SLEEVES if pm_[k] < 0] == ['Value'], 'Petroleum: Carry-Momentum strongest sleeve, Value the only negative')
    _sk = CS['petroleum']['Skewness'].loc['2012-01-01':].dropna(); _yl = yearly_log(_sk).loc[[2020, 2021, 2022, 2026]].sum(); _tt = _sk.sum()
    chk(_yl > _tt, 'Petroleum Skewness: four years add more than the full-sample total')
    kf.append(f"Petroleum's Carry-Momentum is its strongest strategy (IR {I(pm_['CarryMom'])}) and Value (IR {I(pm_['Value'])}) is the only core Petroleum strategy with a negative full-sample IR; the Equal Weight and Inverse Vol portfolios earn IR {I(pew['ir'])} and {I(piv['ir'])}. "
              f"Skewness is positive in Petroleum (IR {I(pm_['Skewness'])}), but mostly because it stayed long oil after the 2020 collapse: calendar years 2020, 2021, 2022 and 2026 add {_yl:.2f} of log return against a full-sample total of {_tt:.2f}."); kf.append(old_kf[2])
    # Precious Metals, Agriculture and Softs
    pe, pi = st("precious", "EW PORT"), st("precious", "Inverse Vol"); ae, ai = st("agri", "EW PORT"), st("agri", "Inverse Vol"); se, si = st("softs", "EW PORT"), st("softs", "Inverse Vol")
    neg_both = [t for t in BUCKETS if st(t, "EW PORT")["ir"] < 0 and st(t, "Inverse Vol")["ir"] < 0]
    chk(neg_both == ["precious", "agri", "softs"], f"buckets where neither portfolio earns a positive IR {neg_both}")
    chk(all(st(t, k)["ir"] < 0 for t in ("precious", "agri") for k in ("Momentum", "Carry", "CarryMom", "Value")) and st("softs", "Value")["ir"] > 0 and all(st("softs", k)["ir"] < 0 for k in ("Momentum", "Carry", "CarryMom")), "Precious Metals and Agriculture core strategies all negative; Softs only Value positive")
    chk(st("precious", "Skewness")["ir"] > 0 and st("agri", "Skewness")["ir"] > 0.4 and st("softs", "Skewness")["ir"] < -0.3, "Skewness positive in Precious Metals and Agriculture, clearly negative in Softs")
    chk(st("softs", "EW PORT")["ir"] < st4("softs", "EW PORT")["ir"] and st("agri", "EW PORT")["ir"] > st4("agri", "EW PORT")["ir"] and st("precious", "EW PORT")["ir"] > st4("precious", "EW PORT")["ir"], "Skewness trims the loss in Precious Metals and Agriculture and deepens it in Softs")
    kf.append(f"Precious Metals, Agriculture and Softs are the three buckets where portfolio construction fails: neither earns a positive IR (Precious Metals Equal Weight {I(pe['ir'])}, Inverse Vol {I(pi['ir'])}; Agriculture {I(ae['ir'])} and {I(ai['ir'])}; Softs {I(se['ir'])} and {I(si['ir'])}), and in Precious Metals and Agriculture every core strategy is net negative full-sample, "
              f"while in Softs only Value is positive (IR {I(st('softs', 'Value')['ir'])}). Skewness is the only sleeve with a positive full-sample IR in Precious Metals ({I(st('precious', 'Skewness')['ir'])}) and Agriculture ({I(st('agri', 'Skewness')['ir'])}), where it trims the loss but does not reverse it; in Softs it is the weakest sleeve ({I(st('softs', 'Skewness')['ir'])}) and lowers the portfolio IR (Equal Weight {I(st4('softs', 'EW PORT')['ir'])} to {I(se['ir'])}).")
    # Skewness
    sk_ir = {t: st(t, "Skewness")["ir"] for t in BUCKETS}
    sk_p = {t: per(t, "Skewness") for t in BUCKETS}
    neg_full = [t for t in BUCKETS if sk_ir[t] < 0]; neg_p1 = [t for t in BUCKETS if sk_p[t][0] < 0]; pos_p3 = [t for t in BUCKETS if sk_p[t][2] > 0]
    chk(neg_full == ["metals", "softs"] and set(neg_p1) == {"metals", "petroleum", "ngl", "precious", "softs"} and set(pos_p3) == {"petroleum", "pen", "ngl", "precious", "agri"}, f"Skewness by bucket: negative full {neg_full}, P1 negative {neg_p1}, P3 positive {pos_p3}")
    n_p1, n_p3 = len(neg_p1), len(pos_p3)
    pet_long = [legs("energy", p)["p3"]["long_pct"] for p in PRODUCTS["petroleum"]]
    chk(len(pet_long) == 5 and round(min(pet_long)) == 89 and round(max(pet_long)) == 100, "five oil products long on 89% to 100% of P3 days")
    bs = bystyle(); bS = bench_corr(bs["Skewness"])
    ttf_long = legs("emissions", "TTF")["full"]["long_pct"]
    nw = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven"}
    kf.append(f"Skewness is a different kind of premium from the other four. It is positive in {nw[len(BUCKETS) - len(neg_full)]} of the seven buckets (Petroleum, Gas and Emissions, NGL, Precious Metals and Agriculture) and negative in Metals and Softs, it is negative in P1 in {nw[n_p1]} buckets and positive in P3 in {nw[n_p3]}. "
              f"Its gains in Petroleum, NGL and Precious Metals are largely long positions held after crashes (the five oil products were long on {min(pet_long):.0f}% to {max(pet_long):.0f}% of P3 days), consistent with its {N(bS['Commodity Index'])} correlation with a passive commodity index in the seven-bucket book, unlike Momentum, Carry and Carry-Momentum. "
              f"Gas and Emissions is the exception to the long bias: Skewness is long on only {ttf_long:.0f}% of TTF days and earns its gain on the short side.")
    # pairs
    c8 = corr8(); B, F = cross8()
    best, b2 = F["best"], F["b2"]; best_iv = F["best_iv"]; ew, iv = F["ew"], F["iv"]
    cx = corr_cross("EW PORT")
    chk(best["name"] == best_iv["name"] == "Petroleum-NGL" and b2["name"] == "Gas and Emissions-NGL", "Petroleum-NGL is first and Gas and Emissions-NGL second under Equal Weight; Petroleum-NGL also first under Inverse Vol")
    kf.append(f"Petroleum-NGL is the most correlated pair of buckets for all seven series types (EW PORT correlation {U(cx.loc['petroleum', 'ngl'])}); Gas and Emissions-NGL ({U(cx.loc['pen', 'ngl'])}), Petroleum-Gas and Emissions ({U(cx.loc['petroleum', 'pen'])}) and Metals-Precious Metals ({U(cx.loc['metals', 'precious'])}) follow, and no other pair exceeds 0.08. "
              f"Yet standalone Petroleum-NGL is the best-performing of the twenty-one pairs under both Equal Weight (IR {I(best['ew']['ir'])}) and Inverse Vol (IR {I(best['iv']['ir'])}), narrowly ahead of Gas and Emissions-NGL ({I(b2['ew']['ir'])} and {I(b2['iv']['ir'])}), proving correlation and performance are separate questions.")
    kf.append(f"The cross-commodity portfolio (each strategy equal-weighted across the seven buckets, then the five strategies combined) delivers Equal Weight IR {I(ew['ir'])} and Inverse Vol IR {I(iv['ir'])} at a volatility of {V(ew['vol'])} and {V(iv['vol'])}, and is positive in every period under both constructions. "
              f"It is negatively correlated with equity (Equal Weight {N(F['bE']['Equity'])}, Inverse Vol {N(F['bI']['Equity'])}) and a traditional 60/40 portfolio ({N(F['bE']['60/40 Portfolio'])}, {N(F['bI']['60/40 Portfolio'])}), but with Skewness included it is positively correlated with a passive commodity index ({N(F['bE']['Commodity Index'])}, {N(F['bI']['Commodity Index'])}; {N(F['b4E']['Commodity Index'])} and {N(F['b4I']['Commodity Index'])} without Skewness), so it diversifies equity and bonds but is no longer free of commodity beta.")
    kf.append(f"Diversifying across all seven buckets lowers volatility but not risk-adjusted return: the Petroleum-NGL and Gas and Emissions-NGL pairs earn more per unit of risk (IR {I(best['ew']['ir'])} and {I(best['iv']['ir'])}; {I(b2['ew']['ir'])} and {I(b2['iv']['ir'])}) than the seven-bucket book (IR {I(ew['ir'])} and {I(iv['ir'])}), at about {V(best['ew']['vol'])} volatility against {V(ew['vol'])}, "
              f"because the extra diversification comes from Metals, Precious Metals, Agriculture and Softs, where the core signals earn little or nothing.")
    chk(len(kf) == 9, "nine key findings")
    return kf


def liquidity_paragraph():
    liq = pd.read_csv(os.path.join(REPO, "Analysis", "Liquidity_Cal2025_results.csv")).set_index("product")
    pl = pd.read_csv(os.path.join(REPO, "Analysis", "Power_Liquidity_Cal2025_results.csv")).set_index("product")
    ng = pd.read_csv(os.path.join(REPO, "Analysis", "NGL_Liquidity_CME_ICE_Cal2025_products.csv")).set_index("family")
    grp = {"Metals": ["Copper", "Aluminium", "Zinc", "Lead"], "Petroleum": ["Brent", "WTI", "SingaporeGasoil", "HeatingOil", "RBOB"], "Gas and Emissions": ["NatGas", "TTF", "UKGas", "EUA"], "Precious Metals": ["Gold", "Silver", "Platinum", "Palladium"],
           "NGL": ["Propane", "Butane", "Ethane", "Naphtha", "NatGasoline"], "Agriculture": ["Soybean", "Corn", "Wheat", "LiveCattle"], "Softs": ["Sugar", "Cocoa", "Coffee", "Cotton"]}
    pw_ = ["PJM_Peak", "ERCOT_Peak", "PJM_OffPeak", "ERCOT_OffPeak", "MISO_Peak"]
    prod = [p for g in grp.values() for p in g]
    chk(len(prod) == 30 and len(pw_) == 5, "30 bucket products and 5 Power series")
    x = liq["x_strip"]; L = liq["L_strip"]; xp = pl["x_strip"]; Lp = pl["L_strip"]
    allx = pd.concat([x.loc[prod], xp])
    chk(allx.idxmax() == "Brent" and allx.idxmin() == "MISO_OffPeak", "Brent most liquid, MISO OffPeak least liquid of the table")
    chk(len(allx) == 36, "36 products in the table")
    chk(x.loc[prod].idxmin() == "Naphtha", "Naphtha is the least liquid product of the seven research buckets")
    chk(3.5 < np.log10(float(allx.max() / allx.min())) < 4.5, "four orders of magnitude between Brent and MISO OffPeak")
    allm = pd.concat([x, xp]); chk(len(allm) == 40 and allm.idxmin() == "Isobutane" and float(allm.min()) < float(allx.min()), "Isobutane is the least liquid of the 40 products measured and lies outside the table")
    sp = {g: (x.loc[ps].max() / x.loc[ps].min()) for g, ps in grp.items()}
    nn = [p for p in prod if p not in grp["NGL"]]
    chk(x.loc[nn].idxmin() == "Cotton" and float(x["Cotton"]) < float(x["Lead"]), "Cotton is the least liquid product outside NGL and US Power (Lead the second)")
    chk(float(xp.loc[pw_].max()) < float(x["Propane"]) and float(xp.loc[pw_].min()) > float(x["Naphtha"]), "US Power sits between Naphtha and Propane in turnover")
    Lmax_nn = float(L.loc[nn].max()); chk(round(Lmax_nn, 2) == 0.06, "at most 0.06 days outside NGL and Power")
    sp_pw = float(xp.loc[pw_].max() / xp.loc[pw_].min()); chk(round(sp_pw, 1) == 46.8, "Power spread 46.8-fold")
    r_prop = float(x["Propane"] / x["Cotton"]); r_pjm = float(xp["PJM_Peak"] / x["Cotton"])
    chk(0.68 < r_prop < 0.76 and 0.6 < r_pjm < 0.7 and xp["PJM_Peak"] < x["Propane"] and x["Butane"] > xp["ERCOT_Peak"] > xp["PJM_OffPeak"] > x["Ethane"] and xp["ERCOT_OffPeak"] < x["NatGasoline"] and xp["MISO_Peak"] < x["NatGasoline"], "Propane about 72% of Cotton; PJM Peak about 64% and just below Propane; ERCOT Peak and PJM OffPeak between Butane and Ethane; the two low Power series below Natural Gasoline")
    chk(sp["Agriculture"] < sp["Petroleum"] < sp["Softs"] < sp["Metals"] < sp["Gas and Emissions"] < sp["Precious Metals"] < sp["NGL"], "spreads order: Agriculture, Petroleum, Softs, Metals, Gas and Emissions, Precious Metals, NGL")
    chk(float(x["Propane"]) > float(x["Butane"]) > float(x["Ethane"]) > float(x["NatGasoline"]) > float(x["Naphtha"]), "NGL order by turnover: Propane, Butane, Ethane, Natural Gasoline, Naphtha")
    chk(0.5 < ng.loc["Propane", "ice_share_x"] < 0.6 and 0.45 < ng.loc["Butane", "ice_share_x"] < 0.5 and 0.7 < ng.loc["Ethane", "ice_share_x"] < 0.75 and ng.loc["Natural Gasoline", "ice_share_x"] < 0.01, "ICE share of NGL turnover: Propane 57%, Butane 48%, Ethane 73%, Natural Gasoline under 1%")
    chk(float(L["Isobutane"]) > 30 and float(liq.loc["Isobutane", "adv_strip"]) > 40 and abs(float(ng.loc["Isobutane", "adv_cme"]) - 10) < 1 and abs(float(ng.loc["Isobutane", "adv_ice"]) - 36.5) < 1, "Isobutane CME 10 and ICE 36 lots a day, about 34 days")
    chk(abs(float(ng.loc["Propane", "x_total"]) - float(x["Propane"])) < 1e-6 and abs(float(ng.loc["Ethane", "x_total"]) - float(x["Ethane"])) < 1e-6, "the NGL summary file equals the liquidity file")
    f1 = lambda v: f"{v:,.1f}"
    iso_cme, iso_ice = float(ng.loc["Isobutane", "adv_cme"]), float(ng.loc["Isobutane", "adv_ice"])
    s = (f"Results across 36 products. Dollar risk turnover ranges from USD {f1(x['Brent'])} million per day for Brent, the most liquid, to USD {xp['MISO_OffPeak']:.3f} million for MISO OffPeak, the least liquid and the series excluded from the Power bucket on that ground, a span of four orders of magnitude. Naphtha (USD {x['Naphtha']:.3f} million) is the least liquid product inside the seven research buckets. "
         f"Within buckets, the spread between the most and least liquid products is narrow in Agriculture ({sp['Agriculture']:.1f}-fold; Soybean {f1(x['Soybean'])} to Wheat {f1(x['Wheat'])}), Petroleum ({sp['Petroleum']:.1f}-fold; Brent {f1(x['Brent'])} to RBOB {f1(x['RBOB'])}) and Softs ({sp['Softs']:.1f}-fold; Coffee {f1(x['Coffee'])} to Cotton {f1(x['Cotton'])}), "
         f"intermediate in Metals ({sp['Metals']:.1f}-fold; Copper {f1(x['Copper'])} to Lead {f1(x['Lead'])}) and in Gas and Emissions ({sp['Gas and Emissions']:.1f}-fold; Henry Hub {f1(x['NatGas'])} to UK Gas {f1(x['UKGas'])}), and wide in Precious Metals ({sp['Precious Metals']:.1f}-fold; Gold {f1(x['Gold'])} to Palladium {f1(x['Palladium'])}). "
         f"NGL has the widest spread, {sp['NGL']:,.1f}-fold (Propane {x['Propane']:.2f} to Naphtha {x['Naphtha']:.3f}), with CME and ICE volume added for Ethane, Propane, Butane and Natural Gasoline: Propane, the most liquid NGL product, trades about {r_prop * 100:.0f}% of the risk turnover of Cotton ({f1(x['Cotton'])}), the least liquid product outside NGL and US Power, and Butane ({x['Butane']:.2f}), Ethane ({x['Ethane']:.2f}), Natural Gasoline ({x['NatGasoline']:.2f}) and Naphtha ({x['Naphtha']:.3f}) are far below it. "
         f"ICE is a large part of measured NGL turnover: it accounts for {ng.loc['Propane', 'ice_share_x'] * 100:.0f}% of Propane's turnover, {ng.loc['Butane', 'ice_share_x'] * 100:.0f}% of Butane's and {ng.loc['Ethane', 'ice_share_x'] * 100:.0f}% of Ethane's, and almost none of Natural Gasoline's, whose ICE contracts printed no volume in 2025 apart from about {float(ng.loc['Natural Gasoline', 'adv_ice']):.0f} lots a day at Conway. "
         f"The US Power series lie within the NGL range: PJM Peak ({xp['PJM_Peak']:.2f}) trades about {r_pjm * 100:.0f}% of the risk turnover of Cotton and just below Propane, ERCOT Peak and PJM OffPeak ({xp['ERCOT_Peak']:.2f} and {xp['PJM_OffPeak']:.2f}) lie between Butane and Ethane, and ERCOT OffPeak and MISO Peak ({xp['ERCOT_OffPeak']:.2f} and {xp['MISO_Peak']:.2f}) are below Natural Gasoline; the spread across the five series is {sp_pw:.1f}-fold. "
         f"In terms of the reference position, a USD 1 million one-sigma position equals at most {Lmax_nn:.2f} days of market risk turnover in any product outside NGL and US Power, against {Lp['PJM_Peak']:.2f}, {Lp['ERCOT_Peak']:.2f}, {Lp['PJM_OffPeak']:.2f}, {Lp['ERCOT_OffPeak']:.1f} and {Lp['MISO_Peak']:.1f} days in PJM Peak, ERCOT Peak, PJM OffPeak, ERCOT OffPeak and MISO Peak, "
         f"and {L['Propane']:.2f} days in Propane, {L['Butane']:.2f} in Butane, {L['Ethane']:.2f} in Ethane, {L['NatGasoline']:.2f} in Natural Gasoline and {L['Naphtha']:.1f} in Naphtha. "
         f"Naphtha averages {liq.loc['Naphtha', 'adv_strip']:.0f} lots per day on the Bloomberg series and prints on {liq.loc['Naphtha', 'share_days_print'] * 100:.0f}% of days, so it cannot absorb a position of meaningful size. "
         f"Isobutane, outside the table, is the least liquid of the 40 products measured: its 12-month strip averages {liq.loc['Isobutane', 'adv_strip']:.0f} lots per day ({iso_cme:.0f} on CME and {iso_ice:.0f} on ICE) and prints on {liq.loc['Isobutane', 'share_days_print'] * 100:.0f}% of days, so a USD 1 million one-sigma position equals {L['Isobutane']:.0f} days of its risk turnover (156 days on CME volume alone, the basis on which it was removed on 9 November 2026). It is removed from every bucket, portfolio and table of this report for that reason. "
         f"The same capacity limit applies to the thinnest series. Returns in Naphtha and US Power may not be capturable at a scale comparable to that of the other buckets: Naphtha needs {L['Naphtha']:.1f} days, and ERCOT OffPeak and MISO Peak {Lp['ERCOT_OffPeak']:.1f} days, of market turnover per USD 1 million of one-sigma risk. "
         f"NGL volumes are CME plus ICE for Ethane, Propane, Butane, Isobutane and Natural Gasoline (the ICE contracts of the 10 November 2026 download, each valued at its own price and volatility), while Naphtha volume is the Bloomberg series, a partial view of the swap market, so its figure is a lower bound. The product-level results are reported in Table A26.")
    return s
