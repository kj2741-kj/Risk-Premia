"""One-off patch (2026-11-10): v8 liquidity section, table A35 notes and NGL text follow the CME plus ICE liquidity file."""
import re

NEW_LIQ = '''def liquidity_paragraph():
    liq = pd.read_csv(os.path.join(REPO, "Analysis", "Liquidity_Cal2025_results.csv")).set_index("product")
    pl = pd.read_csv(os.path.join(REPO, "Analysis", "Power_Liquidity_Cal2025_results.csv")).set_index("product")
    ng = pd.read_csv(os.path.join(REPO, "Analysis", "NGL_Liquidity_CME_ICE_Cal2025_products.csv")).set_index("family")
    grp = {"Metals": ["Copper", "Aluminium", "Zinc", "Lead"], "Petroleum": ["Brent", "WTI", "HeatingOil", "RBOB"], "Gas and Emissions": ["NatGas", "TTF", "UKGas", "EUA"], "Precious Metals": ["Gold", "Silver", "Platinum", "Palladium"],
           "NGL": ["Propane", "Butane", "Ethane", "Naphtha", "NatGasoline"], "Agriculture": ["Soybean", "Corn", "Wheat", "LiveCattle"], "Softs": ["Sugar", "Cocoa", "Coffee", "Cotton"]}
    pw_ = ["PJM_Peak", "ERCOT_Peak", "PJM_OffPeak", "ERCOT_OffPeak", "MISO_Peak"]
    prod = [p for g in grp.values() for p in g]
    chk(len(prod) == 29 and len(pw_) == 5, "29 bucket products and 5 Power series")
    x = liq["x_strip"]; L = liq["L_strip"]; xp = pl["x_strip"]; Lp = pl["L_strip"]
    allx = pd.concat([x.loc[prod + ["SingaporeGasoil"]], xp])
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
         f"ICE is a large part of the NGL market: it accounts for {ng.loc['Propane', 'ice_share_x'] * 100:.0f}% of Propane's turnover, {ng.loc['Butane', 'ice_share_x'] * 100:.0f}% of Butane's and {ng.loc['Ethane', 'ice_share_x'] * 100:.0f}% of Ethane's, and almost none of Natural Gasoline's, whose ICE contracts printed no volume in 2025 apart from about {float(ng.loc['Natural Gasoline', 'adv_ice']):.0f} lots a day at Conway. "
         f"The US Power series lie within the NGL range: PJM Peak ({xp['PJM_Peak']:.2f}) trades about {r_pjm * 100:.0f}% of the risk turnover of Cotton and just below Propane, ERCOT Peak and PJM OffPeak ({xp['ERCOT_Peak']:.2f} and {xp['PJM_OffPeak']:.2f}) lie between Butane and Ethane, and ERCOT OffPeak and MISO Peak ({xp['ERCOT_OffPeak']:.2f} and {xp['MISO_Peak']:.2f}) are below Natural Gasoline; the spread across the five series is {sp_pw:.1f}-fold. "
         f"In terms of the reference position, a USD 1 million one-sigma position equals at most {Lmax_nn:.2f} days of market risk turnover in any product outside NGL and US Power, against {Lp['PJM_Peak']:.2f}, {Lp['ERCOT_Peak']:.2f}, {Lp['PJM_OffPeak']:.2f}, {Lp['ERCOT_OffPeak']:.1f} and {Lp['MISO_Peak']:.1f} days in PJM Peak, ERCOT Peak, PJM OffPeak, ERCOT OffPeak and MISO Peak, "
         f"and {L['Propane']:.2f} days in Propane, {L['Butane']:.2f} in Butane, {L['Ethane']:.2f} in Ethane, {L['NatGasoline']:.2f} in Natural Gasoline and {L['Naphtha']:.1f} in Naphtha. "
         f"Naphtha averages {liq.loc['Naphtha', 'adv_strip']:.0f} lots per day on the Bloomberg series and prints on {liq.loc['Naphtha', 'share_days_print'] * 100:.0f}% of days, so it cannot absorb a position of meaningful size. "
         f"Isobutane, outside the table, is the least liquid of the 40 products measured: its 12-month strip averages {liq.loc['Isobutane', 'adv_strip']:.0f} lots per day ({iso_cme:.0f} on CME and {iso_ice:.0f} on ICE) and prints on {liq.loc['Isobutane', 'share_days_print'] * 100:.0f}% of days, so a USD 1 million one-sigma position equals {L['Isobutane']:.0f} days of its risk turnover (156 days on CME volume alone, the basis on which it was removed on 9 November 2026). It is removed from every bucket, portfolio and table of this report for that reason. "
         f"The same capacity limit applies to the thinnest series. Returns in Naphtha and US Power may not be capturable at a scale comparable to that of the other buckets: Naphtha needs {L['Naphtha']:.1f} days, and ERCOT OffPeak and MISO Peak {Lp['ERCOT_OffPeak']:.1f} days, of market turnover per USD 1 million of one-sigma risk. "
         f"NGL volumes are CME plus ICE for Ethane, Propane, Butane, Isobutane and Natural Gasoline (the ICE contracts of the 10 November 2026 download, each valued at its own price and volatility), while Naphtha volume is the Bloomberg series, a partial view of the swap market, so its figure is a lower bound. The product-level results are reported in Table A26.")
    return s
'''


def patch_front():
    p = "text_front8.py"
    s = open(p, encoding="utf-8").read()
    i = s.index("def liquidity_paragraph():")
    open(p, "w", encoding="utf-8").write(s[:i] + NEW_LIQ)


def patch_ngl():
    p = "text_ngl8.py"
    s = open(p, encoding="utf-8").read()

    def rep(a, b):
        nonlocal s
        assert s.count(a) == 1, (s.count(a), a[:90])
        s = s.replace(a, b)
    rep('''chk(sorted(L5, key=L5.get)[-3:] == ["NatGasoline", "Ethane", "Naphtha"] and round(L_nap, 1) == 9.4 and 1.0 < L_mmb < 1.5, "Naphtha L is 9.4 days, the longest in the bucket, then Ethane, then Natural Gasoline")''',
        '''chk(sorted(L5, key=L5.get)[-3:] == ["Ethane", "NatGasoline", "Naphtha"] and round(L_nap, 1) == 9.4 and 1.0 < L_mmb < 1.5 and 0.7 < L_eth < 0.85, "Naphtha L is 9.4 days, the longest in the bucket, then Natural Gasoline 1.2, then Ethane 0.8 (CME plus ICE)")''')
    rep('''f"It is far more liquid than Naphtha and Ethane: its time to trade one sigma of risk is {L_mmb:.2f} days, with about {adv_m:,.0f} lots a day on a 12-month strip and a print on {days_m * 100:.0f}% of days (CME volume; see the liquidity section).")''',
        '''f"Its time to trade one sigma of risk is {L_mmb:.2f} days, with about {adv_m:,.0f} lots a day on a 12-month strip and a print on {days_m * 100:.0f}% of days, almost all of it on CME (the ICE natural gasoline contracts printed no volume in 2025 apart from the Conway contract). With ICE volume counted, it is much more liquid than Naphtha ({L_nap:.1f} days) but less liquid than Ethane ({L_eth:.2f}), Butane and Propane (see the liquidity section).")''')
    rep("the longest in the bucket and above Ethane ({L_eth:.1f}) (see the liquidity section).", "the longest in the bucket and well above Ethane ({L_eth:.2f}, CME plus ICE) (see the liquidity section).")
    open(p, "w", encoding="utf-8").write(s)


def patch_build():
    p = "build_v8.py"
    s = open(p, encoding="utf-8").read()

    def rep(a, b):
        nonlocal s
        assert s.count(a) == 1, (s.count(a), a[:90])
        s = s.replace(a, b)
    rep('"Propane": "Propane*", "Butane": "Butane*", "Ethane": "Ethane*", "Naphtha": "Naphtha*", "NatGasoline": "Natural Gasoline*",', '"Propane": "Propane", "Butane": "Butane", "Ethane": "Ethane", "Naphtha": "Naphtha*", "NatGasoline": "Natural Gasoline",')
    rep('"* NGL volumes are the CME contracts only (ICE is not included) and Naphtha volume is the Bloomberg series, a partial view of the swap market, so these figures are lower bounds.")',
        '"* Naphtha volume is the Bloomberg series, a partial view of the swap market, so its figure is a lower bound. NGL volumes of Ethane, Propane, Butane and Natural Gasoline are CME plus ICE (the ICE contracts of the 10 November 2026 download; Natural Gasoline also includes the CME and ICE Conway contracts), each venue valued at its own price and volatility, and the P\\u0304 and \\u03c3 shown are strip-volume-weighted averages; ICE lots are 1,000 barrels, the 42,000 gallons of the CME swaps.")')
    # methodology bullet: volumes of two venues are added
    rep('''# ----------------------------------------------------------------------------------------------------------------------------- front matter''', '''iadv_ = find_p("\\u2022  ADV"); tadv_ = ptext(E()[iadv_])
set_text(P(E()[iadv_]), tadv_.rstrip() + " For a product traded on two exchanges (Ethane, Propane, Butane, Isobutane and Natural Gasoline: CME and ICE) the strip volumes of the venues are added, each venue valued at its own risk per lot, so that x is the sum over venues.")

# ----------------------------------------------------------------------------------------------------------------------------- front matter''')
    # verification row
    rep('''    ["v7 Key Findings marked 'v5 basis' (NGL, Energy-NGL pair, cross-commodity book)"''', '''    ["v8 liquidity table: NGL volumes on CME only (ICE not included)", f"CME plus ICE for Ethane, Propane, Butane, Isobutane and Natural Gasoline (ICE download of 10 November 2026, 1,000-barrel lots, each venue at its own price and volatility): x {liq.loc['Ethane', 'x_strip']:.2f}, {liq.loc['Propane', 'x_strip']:.2f}, {liq.loc['Butane', 'x_strip']:.2f}, {liq.loc['Isobutane', 'x_strip']:.3f} and {liq.loc['NatGasoline', 'x_strip']:.2f} USD million a day; time to trade one sigma {liq.loc['Ethane', 'L_strip']:.2f}, {liq.loc['Propane', 'L_strip']:.2f}, {liq.loc['Butane', 'L_strip']:.2f}, {liq.loc['Isobutane', 'L_strip']:.0f} and {liq.loc['NatGasoline', 'L_strip']:.2f} days (CME only: 2.86, 0.21, 0.55, 156 and 1.25); the code reproduces the CME-only rows exactly before ICE is added", "Liquidity_Cal2025_results.csv; Liquidity_Cal2025_results_CME_only.csv; scripts/liquidity_ngl_ice_1110.py"],
    ["v7 Key Findings marked 'v5 basis' (NGL, Energy-NGL pair, cross-commodity book)"''')
    open(p, "w", encoding="utf-8").write(s)


patch_front(); patch_ngl(); patch_build()
print("patched text_front8, text_ngl8, build_v8")
