from facts3 import *

W4 = [("Full", "full"), ("2012-16", "p1"), ("2017-21", "p2"), ("2022-26", "p3")]
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
        table(f"{nm}: Individual-{unit} Information Ratios, All Strategies (Full Sample)", [""] + prods,
              [[NAME[k]] + [I(pst(a, p, k)["ir"]) for p in prods] for k in SLEEVES])
        if v == "energy":
            table("Energy ex-NatGas: Strategy and Portfolio Information Ratios by Period", H4, per_rows(sl("energy_exng"), SLEEVES + ["EW PORT", "Inverse Vol"]))
    v = "precious"; a, prods = VARIANTS[v]
    table("Precious Metals: Strategy Information Ratios by Period", H4, per_rows(sl(v), SLEEVES))
    table("Precious Metals: Portfolio Construction Information Ratios by Period", H4, per_rows(sl(v), ["EW PORT", "Inverse Vol"]))
    table("Precious Metals: Individual-Metal Information Ratios, All Strategies (Full Sample)", [""] + prods, [[NAME[k]] + [I(pst(a, p, k)["ir"]) for p in prods] for k in SLEEVES])
    tt = tenor_table(v)
    table("Precious Metals: Carry Tenor Pairs, Full-Sample Information Ratios", ["", "Previous single pair (F1-F3)", "Short pair (F1-F2)", "Long pair alone", "Two-pair blend"],
          [["Carry"] + [I(tt["Carry"][k]) for k in ("prev", "short", "long", "two")], ["Carry-Momentum"] + [I(tt["CarryMom"][k]) for k in ("prev", "short", "long", "two")]])
    v = "ngl"; a, prods = VARIANTS[v]
    table("NGL: Strategy Information Ratios by Period", H4, per_rows(sl(v), SLEEVES))
    table("NGL: Portfolio Construction Information Ratios by Period", H4, per_rows(sl(v), ["EW PORT", "Inverse Vol"]))
    table("NGL: Individual-Product Information Ratios, All Strategies (Full Sample)", [""] + prods, [[NAME[k]] + [I(pst(a, p, k)["ir"]) for p in prods] for k in SLEEVES])
    v = "agri"; a, prods = VARIANTS[v]
    table("Agriculture: Strategy Information Ratios by Period", H4, per_rows(sl(v), SLEEVES))
    table("Agriculture: Portfolio Construction Information Ratios by Period", H4, per_rows(sl(v), ["EW PORT", "Inverse Vol"]))
    table("Agriculture: Individual-Product Information Ratios, All Strategies (Full Sample)", [""] + prods, [[NAME[k]] + [I(pst(a, p, k)["ir"]) for p in prods] for k in SLEEVES])
    tt = tenor_table(v)
    table("Agriculture: Carry Tenor Pairs, Full-Sample Information Ratios", ["", "Previous single pair (F1-F2)", "Long pair alone", "Two-pair blend"],
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
            rows.append([f"{SHORT[v]}: {p}", U(lg["long_pct"], 0) + "%", N(lg["long_pnl"]), N(lg["short_pnl"]), I(pst(a, p, "Skewness")["ir"])])
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
    blocks = [("h2", "Appendix: Verification Log (v3_2012 to v4)")]
    B = blocks.append
    B(("p", "Every figure in this document was recomputed from the per-product net returns of the pipeline in scripts/final_dashboard (rebuilt locally; the embedded dataset of Final_Research_Dashboard_2012.html is reproduced exactly) and cross-checked: 3,504 numbers (asset-class tabs, all 23 products, both combined books, By Style and all cross-pair portfolios) "
            "agree with the dashboard to within 0.0005, and the Skewness sleeve agrees with Skewness_Research.html and with the Streamlit dashboards' Portfolio tabs and the hub's Cross-Asset tab. Figures are formatted from full-precision values, so a second-decimal digit can differ by 0.01 from v3, which rounded twice (for example Zinc Momentum, Energy Carry-Momentum in P3 and Corn Value in P1). "
            "External facts were re-checked against sources on 12 October 2026. Statements changed or corrected in v4:"))
    rows = [
        ["Copper 'record $14,851 on 22 Sep 2026'", "Kept as the high of our series; LME three-month record reported at about $14,875 on 10 Sep 2026", "Series check; market reports (Yahoo Finance, Discovery Alert, Erbakir)"],
        ["Aluminium peak '$3,876 on 4 Mar 2022'", "Kept as the settlement peak of our series; LME intraday record about $4,070 to $4,074 on 7 Mar 2022 added", "Series check; Harbor Aluminum, Credit Suisse via FXStreet, MetalCharts"],
        ["WTI '$105 in June 2014'", "$107 on 20 June 2014 in our series; $26 on 11 Feb 2016 confirmed", "Series check; RBN Energy (late-June high about $107)"],
        ["Energy Momentum 'March 2022 spike (a further 14% of the total)'", "14% is calendar 2022; March 2022 alone is 7%", "Recomputed from sleeve returns"],
        ["Gold 'sleeve lost 0.45 in 2025'", "It is Gold's Value position (-0.45); the Precious Metals Value sleeve lost 0.31", "Recomputed"],
        ["Producer hedge book '182 tonnes at end-2024'", "182 tonnes was the first WGC estimate; revised to about 194 tonnes. 218 tonnes in Q3 2017 confirmed", "World Gold Council Gold Demand Trends"],
        ["Mont Belvieu propane discount '$0.89/gal (Hydrocarbon Engineering)'", "Figure confirmed; source is EIA Today in Energy", "EIA"],
        ["LPG 'nearly 40% of global export supply (OPIS, 10 June 2026)'", "Not confirmed; replaced by about 30% of global LPG supply (Veson Nautical) and the record 3.3 million b/d of US LPG exports in April 2026 (S&P Global)", "Veson Nautical via OilPrice, S&P Global"],
        ["Propane exports 'record 2.011 million b/d in November'", "EIA: record 1.8 million b/d average in 2024; first month above 2 million b/d is April 2026 at a record 2.1 million b/d", "EIA Today in Energy"],
        ["Ethane 492,000 b/d vs 65,000 b/d; butane 491,000 vs 97,000", "Confirmed (normal butane)", "OPIS citing EIA"],
        ["Arabica 'lifted by 32% in a week' (July 2021)", "+34% from 19 to 26 July 2021 in our series; highest front-month since October 2014 confirmed", "Series check; Reuters, Bloomberg"],
        ["Coffee 'record $4.39/lb on 13 Feb 2025'", "Our series' high; market sources put the Feb 2025 record near $4.30 and the later all-time high at $4.38 (23 Oct 2025)", "Series check; Barchart, Bloomberg"],
        ["Gold 'fell 28% in 2013'", "Confirmed in our series (-28.3%); Reuters reported nearly 30% for the year; gold ETF holdings fell 32%", "Series check; Reuters, Bloomberg"],
        ["Gold/real-yield correlation, P3 '-0.25'; P3 real yield '1.61%'", "-0.24 and 1.60% on FRED DFII10 data downloaded 12 Oct 2026 (end date 23 Sep 2026)", "FRED"],
        ["NGL F2-F4 slope '+3.8% / -1.6%'", "+3.7% / -1.7% on the pooled product-days", "Recomputed from curves"],
        ["Henry Hub 2012 average $2.77, lowest since 1999", "Confirmed", "EIA"],
        ["IEA 'largest disruption in the history of the oil market'; war from 28 Feb 2026", "Confirmed", "IEA Oil Market Reports (March, April 2026); CNBC"],
        ["Aluminium queues of more than two years", "Confirmed: longest wait 748 days (LME, May 2014)", "LME report via Reuters"],
        ["Corn record, USDA August 2012", "Confirmed: season-average price forecast $7.50 to $8.90", "USDA WASDE, 10 Aug 2012"],
        ["FAO food price index peak March 2022 and fall in 2023", "Confirmed: 159.3 points in March 2022; 2023 average 13.7% below 2022", "FAO"],
        ["Central banks 863 tonnes in 2025 vs 473 tonnes 2010-2021 average", "Confirmed", "World Gold Council"],
        ["Page footer listed the old four regimes (R1 2011-2015 to R4 2022-2026)", "Replaced by the three periods used throughout the document (P1 2012-2016, P2 2017-2021, P3 2022-2026)", "Consistency fix (the same footer is in v2 and v3)"],
        ["Cross-commodity benchmark correlations", "Recomputed on refreshed ETF prices; unchanged four-sleeve values differ by at most 0.01 from v3", "Yahoo Finance via yfinance"],
    ]
    B(("tbl", ["v3 statement", "v4 treatment", "Source"], rows))
    return blocks


if __name__ == "__main__":
    bl = appendix()
    print(len(bl), "blocks;", sum(1 for b in bl if b[0] == "tbl"), "tables;", sum(1 for b in bl if b[0] == "fig"), "figures")
    for b in bl[:6]:
        print(b[0], b[1] if b[0] not in ("tbl",) else b[1:])
