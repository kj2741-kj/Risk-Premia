p = "text_ngl8.py"
s = open(p, encoding="utf8").read()


def r(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:80])
    s = s.replace(a, b)


r('"""NGL bucket of v8: Ethane, Propane, Butane, Isobutane and Naphtha, data to 30 September 2026.', '"""NGL bucket of v8: Ethane, Propane, Butane and Naphtha (Isobutane removed on 9 November 2026), data to 30 September 2026.')
r("    M5 = MEMBERS[v]; pr = [p for _, p in M5]\n    four = [m for m in M5 if m[0] == \"ngl\"]", "    M5 = MEMBERS[v]; pr = [p for _, p in M5]\n    four = [m for m in M5 if m[0] == \"ngl\"]      # the three Mont Belvieu products (the name is kept from the five-product version)")
r('# four-product basis against five', '# three-product (Mont Belvieu) basis against four')
r('chk(round(ew_4p["ir"], 2) == 1.26 and round(iv_4p["ir"], 2) == 1.16, "NGL four-product basis EW 1.26 IV 1.16")', 'chk(round(ew_4p["ir"], 2) == 1.20 and round(iv_4p["ir"], 2) == 1.12, "NGL three-product basis EW 1.20 IV 1.12")')
r('chk(vf["Butane"] > 0.2 and vf["Naphtha"] > 0.15 and vf["Isobutane"] > 0.1 and vf["Ethane"] < 0 and abs(vf["Propane"]) < 0.05, "NGL Value by product")', 'chk(vf["Butane"] > 0.2 and vf["Naphtha"] > 0.15 and vf["Ethane"] < 0 and abs(vf["Propane"]) < 0.05, "NGL Value by product")')
r('chk(skp["Naphtha"] > skp["Ethane"] > 0.2 and abs(skp["Isobutane"]) < 0.1 and skp["Propane"] < 0 and skp["Butane"] < 0, "NGL Skewness by product")', 'chk(skp["Naphtha"] > skp["Ethane"] > 0.2 and skp["Propane"] < 0 and skp["Butane"] < 0, "NGL Skewness by product")')
r('    iso_after, _ = skew_episode("ngl", "Isobutane", "2020-05-01", "2021-12-31")\n    chk(min(prop_after, but_after, iso_after) > 1.3, "NGL Skewness 2020-2021 episode")', '    chk(min(prop_after, but_after) > 1.3, "NGL Skewness 2020-2021 episode")')
r('L_nap, L_eth, L_iso = float(liq.loc["Naphtha", "L_strip"]), float(liq.loc["Ethane", "L_strip"]), float(liq.loc["Isobutane", "L_strip"])', 'L_nap, L_eth = float(liq.loc["Naphtha", "L_strip"]), float(liq.loc["Ethane", "L_strip"])')
r('chk(sorted(L5, key=L5.get)[-2:] == ["Naphtha", "Isobutane"] and round(L_nap, 1) == 9.4, "Naphtha L is 9.4 days, second longest in the bucket after Isobutane")', 'chk(sorted(L5, key=L5.get)[-2:] == ["Ethane", "Naphtha"] and round(L_nap, 1) == 9.4, "Naphtha L is 9.4 days, the longest in the bucket, Ethane second")')
r('B.append(f"NGL (five products since v8: Ethane, Propane, Butane, Isobutane and Naphtha) is the strongest bucket', 'B.append(f"NGL (four products: Ethane, Propane, Butane and Naphtha; Isobutane, the least liquid product in the data set, is excluded) is the strongest bucket')
r('B.append(f"Naphtha (CIF NWE average-price swap, USD per tonne) is the fifth product and it strengthens the bucket. On the four Mont Belvieu products alone', 'B.append(f"Naphtha (CIF NWE average-price swap, USD per tonne) is the fourth product and it strengthens the bucket. On the three Mont Belvieu products alone')
r("the highest of the five products (Ethane {I(e5['Ethane'])}, Propane {I(e5['Propane'])}, Butane {I(e5['Butane'])}, Isobutane {I(e5['Isobutane'])}). ", "the highest of the four products (Ethane {I(e5['Ethane'])}, Propane {I(e5['Propane'])}, Butane {I(e5['Butane'])}). ")
r("combined returns correlate {U(min(cor_n.values()))} to {U(max(cor_n.values()))} with the four Mont Belvieu products (Ethane {U(cor_n['Ethane'])})", "combined returns correlate {U(min(cor_n.values()))} to {U(max(cor_n.values()))} with the three Mont Belvieu products (Ethane {U(cor_n['Ethane'])})")
r("a partial view of the swap market, the second longest in the bucket after Isobutane ({L_iso:.0f} days) and above Ethane ({L_eth:.1f}) (see the liquidity section).", "a partial view of the swap market, the longest in the bucket and above Ethane ({L_eth:.1f}) (see the liquidity section).")
r("In the data the F2-F4 slope, averaged over the five products,", "In the data the F2-F4 slope, averaged over the four products,")
r("Skewness is a single-regime result in the Mont Belvieu products. It is negative in all four in P1", "Skewness is a single-regime result in the Mont Belvieu products. It is negative in all three in P1")
r("and positive in all five products in P2", "and positive in all four products in P2")
r("it turned long on 11 March 2020 in Propane, Butane and Isobutane, earning {N(prop_after)} in Propane, {N(but_after)} in Butane and {N(iso_after)} in Isobutane from May 2020 to December 2021,", "it turned long on 11 March 2020 in Propane and Butane, earning {N(prop_after)} in Propane and {N(but_after)} in Butane from May 2020 to December 2021,")
r("Momentum is positive in all five products", "Momentum is positive in all four products")
r("Value's modest full-sample edge is concentrated in Butane, Naphtha and Isobutane (IR {I(vf['Butane'])} / {I(vf['Naphtha'])} / {I(vf['Isobutane'])}), while Ethane and Propane show none", "Value's modest full-sample edge is concentrated in Butane and Naphtha (IR {I(vf['Butane'])} / {I(vf['Naphtha'])}), while Ethane and Propane show none")
r("Skewness is positive in Naphtha ({I(skp['Naphtha'])}) and Ethane ({I(skp['Ethane'])}), about flat in Isobutane ({I(skp['Isobutane'])}) and slightly negative in Propane ({I(skp['Propane'])}) and Butane ({I(skp['Butane'])}).", "Skewness is positive in Naphtha ({I(skp['Naphtha'])}) and Ethane ({I(skp['Ethane'])}) and slightly negative in Propane ({I(skp['Propane'])}) and Butane ({I(skp['Butane'])}).")
r('chk(all(pper(a, p, "Skewness")[0] < -0.2 for a, p in four) and npp["Skewness"][0] > 0.2, "Skewness P1 negative in the four Mont Belvieu products, positive in Naphtha")', 'chk(all(pper(a, p, "Skewness")[0] < -0.2 for a, p in four) and npp["Skewness"][0] > 0.2, "Skewness P1 negative in the three Mont Belvieu products, positive in Naphtha")')
r('chk(all(skpp[p][1] > 0.1 for p in pr), "Skewness P2 positive in all five")', 'chk(all(skpp[p][1] > 0.1 for p in pr), "Skewness P2 positive in all four")')
r('chk(min(lg[p]["p3"]["long_pct"] for p in pr) > 75, "NGL Skewness long on more than 75% of P3 days in every product")', 'chk(min(lg[p]["p3"]["long_pct"] for p in pr) > 75, "NGL Skewness long on more than 75% of P3 days in every product")')
assert "Isobutane" not in s.replace("Isobutane removed on 9 November 2026", "").replace("Isobutane, the least liquid product in the data set, is excluded", ""), [l for l in s.split("\n") if "Isobutane" in l][:3]
open(p, "w", encoding="utf8").write(s); print("ngl text patched")
