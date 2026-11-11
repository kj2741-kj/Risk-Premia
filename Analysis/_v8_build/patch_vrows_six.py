s = open("build_v8.py", encoding="utf8").read()
i = s.index("vrows = [")
j = s.index("]\ntmpl = copy.deepcopy(tver._tbl.findall", i)
new_rows = '''import json as _json
_Bc, _Fc = cross8(); _best, _b2 = _Fc["best"], _Fc["b2"]
_old = _json.load(open(os.path.join(REPO, "outputs", "final_dashboard_0930_pre_isobutane", "final_v3.json"), encoding="utf8"))
_oN = {r["name"]: r["ir"] for r in _old["tabs"]["ngl"]["windows"]["full"]}
_nE, _nI = st("ngl", "EW PORT"), st("ngl", "Inverse Vol")
_three = [m for m in MEMBERS["ngl"] if m[0] == "ngl"]
_cs3 = pd.DataFrame({k: ew_intersection([nets()[m][k] for m in _three]) for k in SLEEVES}); _e3, _i3 = stats(_cs3.mean(axis=1, skipna=False)), stats(inverse_vol(_cs3))
_Fe, _Fi = _Fc["ew"], _Fc["iv"]
vrows = [
    ["v7 NGL figures on the v5 basis (to 23 September 2026): Equal Weight IR +1.25, Inverse Vol +1.16", f"Now {I(_nE['ir'])} and {I(_nI['ir'])} on the 30 September data with Naphtha as the fourth product (the three Mont Belvieu products on the same data: {I(_e3['ir'])} and {I(_i3['ir'])}); Naphtha series built from the Bloomberg KI swap sheet with the Bloomberg expiry calendar, Carry on F2-F4 only", "Recomputed; 0930 dashboard dataset"],
    [f"v8 as first issued (6 November 2026): NGL of five products including Isobutane, Equal Weight IR {I(_oN['EW PORT'])}, Inverse Vol {I(_oN['Inverse Vol'])}", f"Isobutane removed from every bucket, portfolio, pair, correlation and table on 9 November 2026 because it is the least liquid of the 36 products measured (about 10 lots a day on its 12-month strip, a USD 1 million one-sigma position equals 156 days of its risk turnover): NGL {I(_nE['ir'])} and {I(_nI['ir'])}; six-bucket book {I(_Fe['ir'])} and {I(_Fi['ir'])} (26 products in the buckets)", "Recomputed; 0930 dashboard dataset; Liquidity_Cal2025_results.csv"],
    ["v7: Energy-NGL the best of ten pairs (Equal Weight +1.23, Inverse Vol +1.21; +1.28 and +1.30 without Natural Gas)", f"Petroleum-NGL is the best of fifteen pairs ({I(_best['ew']['ir'])}, {I(_best['iv']['ir'])}); Gas and Emissions-NGL second ({I(_b2['ew']['ir'])}, {I(_b2['iv']['ir'])}); the Energy-ex-NatGas comparison no longer applies because Natural Gas is in Gas and Emissions", "Recomputed; 0930 dashboard dataset"],
    ["v7: cross-commodity book Equal Weight IR +0.87, Inverse Vol +0.91 at 4.9% and 5.0% volatility (five asset classes, Energy including Natural Gas)", f"Six buckets, 2012 to 30 September 2026 (US Power is not in the book): {I(_Fe['ir'])} and {I(_Fi['ir'])} at {V(_Fe['vol'])} and {V(_Fi['vol'])} volatility, positive in every period; commodity-index correlation {N(_Fc['bE']['Commodity Index'])} and {N(_Fc['bI']['Commodity Index'])}", "Recomputed; 0930 dashboard dataset"],
    ["v7: Skewness correlation with the commodity index +0.46 in the five-class book", f"{N(_Fc['bS']['Commodity Index'])} in the six-bucket book (equity {N(_Fc['bS']['Equity'])}, gold {N(_Fc['bS']['Gold'])})", "Recomputed; ETF file cut at 30 September 2026"],
    ["v7: bucket 'Power, Emissions and Nat Gas' (Henry Hub, TTF, EUA)", "Gas and Emissions with UK Gas added (Henry Hub, TTF, UK Gas, EUA); UK Gas from the Bloomberg NBP sheet, Bloomberg expiry history", "Recomputed; 0930 dashboard dataset"],
    ["v7 liquidity section: 26 products, Power, Emissions and Natural Gas 17.1-fold spread", "33 products with UK Gas, Naphtha and the six US Power series (five in the Power results, MISO OffPeak flagged); Isobutane, the least liquid product measured, is outside the table; Gas and Emissions spread 21.3-fold (Henry Hub to UK Gas); Naphtha time to trade one sigma of risk 9.4 days (Bloomberg volume, lower bound); US Power 0.10 to 4.7 days", "Liquidity_Cal2025_results.csv; Power_Liquidity_Cal2025_results.csv"],
    ["v7 Key Findings marked 'v5 basis' (NGL, Energy-NGL pair, cross-commodity book)", "Rewritten on six buckets; Petroleum, Metals, Precious Metals and Agriculture findings unchanged", "Recomputed"],
    ["v7: no US Power coverage", "New standalone US Power section (outside the six-bucket book): five ICE series (PJM Peak and OffPeak, ERCOT Peak and OffPeak, MISO Peak; MISO OffPeak excluded at 9.9 days), data to 30 September 2026, reported from 2017 (no P1); Equal Weight IR +0.30, Inverse Vol +0.31", "Recomputed; dashboard Power tab (power_tab_0930.json); Power_Liquidity_Cal2025_results.csv"],
'''
s = s[:i] + new_rows + s[j:]
open("build_v8.py", "w", encoding="utf8").write(s); print("verification rows rewritten")
