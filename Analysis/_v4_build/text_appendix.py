from facts3 import *

W4 = [("Full", "full"), ("2012-16", "p1"), ("2017-21", "p2"), ("2022-26", "p3")]
PNAME = {"HeatingOil": "Heating Oil", "NatGas": "Natural Gas", "SoybeanOil": "Soybean Oil"}
NAME = {"Momentum": "Momentum", "Carry": "Carry", "CarryMom": "Carry-Momentum", "Value": "Value", "Skewness": "Skewness", "EW PORT": "Equal Weight", "Inverse Vol": "Inverse Vol"}


def per_rows(fn, keys):
    return [[NAME[k]] + [I(fn(k, w)["ir"]) for _, w in W4] for k in keys]


def appendix():
    blocks = [("h2", "Appendix: Period-Level Detail")]
    B = blocks.append
    n = [0]

    def table(title, header, rows):
        n[0] += 1
        B(("cap", f"Table A{n[0]}. {title}"))
        B(("tbl", header, rows))

    H4 = ["", "Full", "2012-16", "2017-21", "2022-26"]
    sl = lambda v: (lambda k, w: st(v, k, w))
    for v, nm, unit in (("metals", "Metals", "Metal"), ("energy", "Energy", "Product")):
        a, prods = VARIANTS[v]
        table(f"{nm}: Strategy Information Ratios by Period", H4, per_rows(sl(v), SLEEVES))
        table(f"{nm}: Portfolio Construction Information Ratios by Period", H4, per_rows(sl(v), ["EW PORT", "Inverse Vol"]))
        table(f"{nm}: Individual-{unit} Information Ratios, All Strategies (Full Sample)", [""] + [PNAME.get(p, p) for p in prods],
              [[NAME[k]] + [I(pst(a, p, k)["ir"]) for p in prods] for k in SLEEVES])
        if v == "energy":
            table("Energy ex-NatGas: Strategy and Portfolio Information Ratios by Period", H4, per_rows(sl("energy_exng"), SLEEVES + ["EW PORT", "Inverse Vol"]))
    v = "precious"; a, prods = VARIANTS[v]
    table("Precious Metals: Strategy Information Ratios by Period", H4, per_rows(sl(v), SLEEVES))
    table("Precious Metals: Portfolio Construction Information Ratios by Period", H4, per_rows(sl(v), ["EW PORT", "Inverse Vol"]))
    table("Precious Metals: Individual-Metal Information Ratios, All Strategies (Full Sample)", [""] + [PNAME.get(p, p) for p in prods], [[NAME[k]] + [I(pst(a, p, k)["ir"]) for p in prods] for k in SLEEVES])
    tt = tenor_table(v)
    table("Precious Metals: Carry Tenor Pairs, Full-Sample Information Ratios", ["", "Previous single pair (F1-F3)", "Short pair (F1-F2)", "Long pair alone", "Two-pair sum"],
          [["Carry"] + [I(tt["Carry"][k]) for k in ("prev", "short", "long", "two")], ["Carry-Momentum"] + [I(tt["CarryMom"][k]) for k in ("prev", "short", "long", "two")]])
    v = "ngl"; a, prods = VARIANTS[v]
    table("NGL: Strategy Information Ratios by Period", H4, per_rows(sl(v), SLEEVES))
    table("NGL: Portfolio Construction Information Ratios by Period", H4, per_rows(sl(v), ["EW PORT", "Inverse Vol"]))
    table("NGL: Individual-Product Information Ratios, All Strategies (Full Sample)", [""] + [PNAME.get(p, p) for p in prods], [[NAME[k]] + [I(pst(a, p, k)["ir"]) for p in prods] for k in SLEEVES])
    v = "agri"; a, prods = VARIANTS[v]
    table("Agriculture: Strategy Information Ratios by Period", H4, per_rows(sl(v), SLEEVES))
    table("Agriculture: Portfolio Construction Information Ratios by Period", H4, per_rows(sl(v), ["EW PORT", "Inverse Vol"]))
    table("Agriculture: Individual-Product Information Ratios, All Strategies (Full Sample)", [""] + [PNAME.get(p, p) for p in prods], [[NAME[k]] + [I(pst(a, p, k)["ir"]) for p in prods] for k in SLEEVES])
    tt = tenor_table(v)
    table("Agriculture: Carry Tenor Pairs, Full-Sample Information Ratios", ["", "Previous single pair (F1-F2)", "Long pair alone", "Two-pair sum"],
          [["Carry"] + [I(tt["Carry"][k]) for k in ("prev", "long", "two")], ["Carry-Momentum"] + [I(tt["CarryMom"][k]) for k in ("prev", "long", "two")]])
    bs = bystyle(False); bx = bystyle(True)
    cb = {k: bench_corr(bs[k]) for k in SER7}
    cols = ["Equity", "Fixed Income", "Commodity Index", "Gold", "60/40 Portfolio"]
    nm2 = dict(NAME); nm2["EW PORT"] = "EW Portfolio"
    table("Cross-Commodity Portfolio: Correlation vs Traditional Assets (2012 to 23 September 2026)", [""] + cols, [[nm2[k]] + [N(cb[k][c]) for c in cols] for k in SER7])
    table("Cross-Commodity Portfolio: Strategy Information Ratios by Period (all 5 asset classes)", H4, [[NAME[k]] + [I(stats(bs[k], w)["ir"]) for _, w in W4] for k in SLEEVES])
    rows = []
    for lab, df, key in (("Equal Weight", bs, "EW PORT"), ("Inverse Vol", bs, "Inverse Vol"), ("Equal Weight (ex-NatGas)", bx, "EW PORT"), ("Inverse Vol (ex-NatGas)", bx, "Inverse Vol")):
        rows.append([lab] + [I(stats(df[key], w)["ir"]) for _, w in W4])
    table("Cross-Commodity Portfolio: Construction Information Ratios by Period (all 5 asset classes)", H4, rows)
    ps = pair_stats(False); psx = pair_stats(True)
    table("Cross-Pair Portfolio: Full-Sample Information Ratios, All Ten Asset-Class Pairs", ["", "Equal Weight", "Inverse Vol"], [[d["name"], I(d["ew"]["ir"]), I(d["iv"]["ir"])] for d in ps])
    table("Cross-Pair Portfolio: Energy Pairs Excluding Natural Gas, Full-Sample Information Ratios", ["", "Equal Weight", "Inverse Vol"], [[d["name"], I(d["ew"]["ir"]), I(d["iv"]["ir"])] for d in psx])
    # new tables
    rows = []
    for v in ("metals", "energy", "precious", "ngl", "agri"):
        a, prods = VARIANTS[v]
        for p in prods:
            lg = legs(a, p)["full"]
            rows.append([f"{SHORT[v]}: {PNAME.get(p, p)}", U(lg["long_pct"], 0) + "%", N(lg["long_pnl"]), N(lg["short_pnl"]), I(pst(a, p, "Skewness")["ir"])])
    table("Skewness: Share of Days Long and Log Return of the Long and Short Legs, by Product (Full Sample, Gross of Costs)", ["Product", "Days long", "Long-leg log return", "Short-leg log return", "IR (net)"], rows)
    rows = []
    for v in ("metals", "energy", "energy_exng", "precious", "ngl", "agri"):
        rows.append([SHORT[v], I(st4(v, "EW PORT")["ir"]), I(st(v, "EW PORT")["ir"]), I(st4(v, "Inverse Vol")["ir"]), I(st(v, "Inverse Vol")["ir"])])
    b4 = bystyle4(False); b4x = bystyle4(True)
    rows.append(["Cross-commodity (with NatGas)", I(stats(b4["EW PORT"])["ir"]), I(stats(bs["EW PORT"])["ir"]), I(stats(b4["Inverse Vol"])["ir"]), I(stats(bs["Inverse Vol"])["ir"])])
    rows.append(["Cross-commodity (ex-NatGas)", I(stats(b4x["EW PORT"])["ir"]), I(stats(bx["EW PORT"])["ir"]), I(stats(b4x["Inverse Vol"])["ir"]), I(stats(bx["Inverse Vol"])["ir"])])
    table("Effect of Adding Skewness: Full-Sample Portfolio Information Ratios with Four and Five Sleeves", ["", "Equal Weight, 4 sleeves", "Equal Weight, 5 sleeves", "Inverse Vol, 4 sleeves", "Inverse Vol, 5 sleeves"], rows)
    rows = []
    for v in ("metals", "energy", "energy_exng", "precious", "ngl", "agri"):
        c = corr_within(v)
        rows.append([SHORT[v]] + [N(c.loc["Skewness", k]) for k in ("Momentum", "Carry", "CarryMom", "Value", "EW PORT")])
    table("Skewness: Correlation with the Other Sleeves and with the Equal Weight Portfolio, within Each Asset Class", ["", "Momentum", "Carry", "Carry-Momentum", "Value", "EW PORT"], rows)
    # equity-curve appendix
    B(("h2", "Appendix: Equity-Curve Charts"))
    B(("p", "Individual equity curves underlying the combined-strategy figures above, decomposed by instrument for each strategy within each asset class, and by asset-class pair, one chart per construction method, for the Cross-Pair Portfolios (Energy including Natural Gas). "
            "Skewness charts are new in this version."))
    cnt = [0]
    for v, nm, unit in (("metals", "Metals", "Metal"), ("energy", "Energy", "Product"), ("precious", "Precious Metals", "Metal"), ("ngl", "NGL", "Product"), ("agri", "Agriculture", "Product")):
        B(("h3", nm))
        for k in SLEEVES:
            cnt[0] += 1
            B(("fig", f"figA_{v}_{k}.png", f"Figure A{cnt[0]}. {nm}, {NAME[k] if k != 'EW PORT' else k}: Equity Curve by {unit} (2012-2026)"))
    B(("h3", "Cross-Pair Portfolios"))
    cnt[0] += 1; B(("fig", "figA_pairs_EW.png", f"Figure A{cnt[0]}. Cross-Pair Portfolios, Equal Weight: Equity Curve by Asset-Class Pair (2012-2026)"))
    cnt[0] += 1; B(("fig", "figA_pairs_IV.png", f"Figure A{cnt[0]}. Cross-Pair Portfolios, Inverse Vol: Equity Curve by Asset-Class Pair (2012-2026)"))
    return blocks


def verification():
    blocks = [("h2", "Appendix: Verification Log (v3_2012 to v5)")]
    B = blocks.append
    B(("p", "Every figure in this document was recomputed from the per-product net returns of the pipeline in scripts/final_dashboard (rebuilt locally with the Carry rule adopted on 13 October 2026; the embedded dataset of Final_Research_Dashboard_2012.html is reproduced exactly) and cross-checked: 3,504 numbers "
            "(every asset-class tab, all 23 products, both combined books, the by-style portfolios and all Cross-Pair portfolios) were recomputed with separate code and agree with the dashboard to within 0.0005, and the Skewness sleeve agrees with Skewness_Research.html and with the Streamlit dashboards' Portfolio tabs and the hub's Cross-Asset tab. "
            "Figures are formatted from full-precision values, so a second-decimal digit can differ from the dashboard's three-decimal rounding. External facts were re-checked against sources on 13 October 2026. "
            "Statements changed or corrected in v4 and carried into v5, and the statements changed by the 13 October 2026 Carry rule, are listed below."))
    rows = [
        ["Copper 'record $14,851 on 22 Sep 2026'", "Kept as the high of our series; market sources put the LME three-month record at about $14,800 to $14,875 on 9 to 10 Sep 2026 (sources differ by contract and time of day)", "Series check; Bloomberg (record $14,802.50, reported 10 Sep), Erbakir and Discovery Alert ($14,875 on 10 Sep)"],
        ["Aluminium peak '$3,876 on 4 Mar 2022'", "Kept as the settlement peak of our series; LME intraday record of about $4,070 to $4,073 in March 2022 added (the exact day is not confirmed)", "Series check; Harbor Aluminum, MetalCharts"],
        ["WTI '$105 in June 2014'", "$107 on 20 June 2014 in our series; $26 on 11 Feb 2016", "Series check"],
        ["Energy Momentum 'March 2022 spike (a further 14% of the total)'", "14% is calendar 2022; March 2022 alone is 7%", "Recomputed from sleeve returns"],
        ["Gold 'sleeve lost 0.45 in 2025'", "It is Gold's Value position (-0.45); the Precious Metals Value sleeve lost 0.31", "Recomputed"],
        ["Producer hedge book '182 tonnes at end-2024'", "182 tonnes was the first WGC estimate; with the end-2025 estimate of about 120 tonnes after a fall of 74 tonnes, the implied revised end-2024 figure is about 194 tonnes. 218 tonnes in Q3 2017 confirmed", "World Gold Council Gold Demand Trends Q3 2017, full-year 2024 and full-year 2025 (supply pages)"],
        ["Mont Belvieu propane discount '$0.89/gal (Hydrocarbon Engineering)'", "Figure confirmed; source is EIA Today in Energy (November 2015)", "EIA Today in Energy, id 23612"],
        ["LPG 'nearly 40% of global export supply (OPIS, 10 June 2026)'", "Not confirmed as worded; replaced by about 30% of global LPG supply (Veson Nautical; Argus gives 30% of seaborne exports, Drewry 40%) and the record 3.3 million b/d of US LPG exports in April 2026 (S&P Global Commodities at Sea; Vortexa puts it at 2.8 million b/d)", "Veson Nautical via Naftemporiki, Argus, S&P Global"],
        ["Propane exports 'record 2.011 million b/d in November'", "EIA: record 1.8 million b/d average in 2024; exports first topped 2 million b/d in November 2024; record 2.1 million b/d in April 2026 (the October 2026 EIA note also says April 2026 was the first month above 2 million b/d, which conflicts with the 2025 note, so the document states only the April 2026 record)", "EIA Today in Energy, id 64724 and id 68244"],
        ["Arabica 'lifted by 32% in a week' (July 2021)", "+34% from 19 to 26 July 2021 in our series; highest front-month since October 2014 confirmed", "Series check; Reuters, 26 July 2021"],
        ["Coffee 'record $4.39/lb on 13 Feb 2025'; later 'all-time high $4.38 on 23 Oct 2025'", "Our series is the front-month (March) contract, settle $4.389 on 13 Feb 2025; the most active contract set its record at about $4.30 that month (Barchart $4.2995 intraday, Reuters above $4.30). The $4.38 record of 23 Oct 2025 could not be confirmed and was removed", "Series check; Barchart; Reuters"],
        ["Henry Hub 2012 'mild winter, record storage'", "EIA describes high, not record, storage; the text now says high storage", "EIA Today in Energy, id 9490"],
        ["Gold 'fell 28% in 2013'", "Confirmed in our series (-28.3%); Reuters reported a 28% fall, the largest since 1981; gold ETF holdings fell about 33%", "Series check; Reuters, Bloomberg"],
        ["Gold/real-yield correlation, P3 '-0.25'; P3 real yield '1.61%'", "-0.24 and 1.60% on FRED DFII10 data downloaded 12 Oct 2026 (end date 23 Sep 2026)", "FRED"],
        ["NGL F2-F4 slope '+3.8% / -1.6%'", "+3.7% / -1.7% on the pooled product-days", "Recomputed from curves"],
        ["Page footer listed the old four regimes (R1 2011-2015 to R4 2022-2026)", "Replaced by the three periods used throughout the document (P1 2012-2016, P2 2017-2021, P3 2022-2026)", "Consistency fix (the same footer is in v2 and v3)"],
        ["Cross-commodity benchmark correlations", "Recomputed on refreshed ETF prices; unchanged four-sleeve values differ by at most 0.01 from v3", "Yahoo Finance via yfinance"],
        ["v4: Carry and Carry-Momentum combine the two tenor pairs by a sign vote", "Replaced on 13 October 2026 by the sign of the summed z-scores (Carry) and of the summed raw 20-observation slope changes (Carry-Momentum); the last signal is kept when a value is missing. Every Carry, Carry-Momentum, portfolio, ranking, correlation and cross-commodity figure is re-derived", "Pipeline commit 446b360; reproduced locally, dataset identical, 3,504 numbers verified"],
        ["v4: Energy ex-NatGas 'improves every sleeve'", "No longer true: it improves Momentum, Value and Skewness but lowers Carry (+0.46 to +0.40) and Carry-Momentum (+0.78 to +0.72)", "Recomputed"],
        ["v4: Agriculture 'every core strategy is net negative'", "Carry is now flat (+0.01); Momentum, Carry-Momentum and Value remain negative", "Recomputed"],
        ["v4: NGL 'Inverse Vol has the shallower drawdown'", "Equal Weight now has the shallower drawdown (-20.9% against -21.5%); Inverse Vol keeps the marginally lower volatility", "Recomputed"],
        ["v4: Metals Carry P1 'concentrated in Aluminium and Zinc'", "Aluminium, Zinc and Lead all earn it (IR +0.62, +0.36, +0.36); Copper loses (-0.29)", "Recomputed; slopes from the curves"],
        ["v4: negative asset-class pairs 'negative in both P2 and P3 under Equal Weight'", "Negative in P3 under both constructions; P2 is close to zero or slightly positive for two of the three", "Recomputed"],
        ["v4: Inverse Vol pulls Precious Metals-NGL down most", "NGL-Agriculture is now the pair it pulls down most (+1.02 to +0.72)", "Recomputed"],
        ["Cross-commodity correlation text: 'joint lowest under Equal Weight'; Value/Skewness 'because'; Carry-Momentum 'most genuinely diversifying'", "Reworded: the same pair is the lowest under both constructions; interpretations stated as consistent with the results, not a test; Value and Skewness positions in Precious Metals measured (daily position correlation -0.81 in Palladium, -0.33 in Gold)", "Recomputed from positions"],
    ]
    B(("tbl", ["Earlier statement", "Treatment", "Source"], rows))
    return blocks


if __name__ == "__main__":
    bl = appendix()
    print(len(bl), "blocks;", sum(1 for b in bl if b[0] == "tbl"), "tables;", sum(1 for b in bl if b[0] == "fig"), "figures")
    for b in bl[:6]:
        print(b[0], b[1] if b[0] not in ("tbl",) else b[1:])
