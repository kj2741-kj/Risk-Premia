p = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia\Analysis\_v8_build\build_v8.py"
s = open(p, encoding="utf8").read()


def r(a, b, c=1):
    global s
    assert s.count(a) == c, (s.count(a), a[:90])
    s = s.replace(a, b)


r('Cross-Commodity Portfolio: Correlation vs Traditional Assets (2012 to 30 September 2026)")', 'Cross-Commodity Portfolio: Correlation vs Traditional Assets (January 2015 to 30 September 2026)")')
r('"Table A19. Cross-Commodity Portfolio: Strategy Information Ratios by Period (all six buckets)")',
  '"Table A19. Cross-Commodity Portfolio: Strategy Information Ratios by Period (all seven buckets)")\ncell_set(t19.rows[0].cells[1], "Full (2015-26)"); cell_set(t19.rows[0].cells[2], "2015-16")')
r('"Table A20. Cross-Commodity Portfolio: Construction Information Ratios by Period (all six buckets)")',
  '''"Table A20. Cross-Commodity Portfolio: Construction Information Ratios by Period (all seven buckets)")
cell_set(t20.rows[0].cells[1], "Full (2015-26)"); cell_set(t20.rows[0].cells[2], "2015-16")
_nt = copy.deepcopy(E()[find_p("Note: Calendar 2025 only")]); t20._tbl.addnext(_nt)
set_text(P(_nt), "Note: the cross-commodity book combines seven buckets on their common dates, 7 January 2015 to 30 September 2026 (the first common date follows the start of the US Power data); its P1 is 2015-2016.")''')
r('"Table A21. Cross-Pair Portfolio: Full-Sample Information Ratios, All Fifteen Bucket Pairs")',
  '''"Table A21. Cross-Pair Portfolio: Full-Sample Information Ratios, All 21 Bucket Pairs")
_nt = copy.deepcopy(E()[find_p("Note: Calendar 2025 only")]); t21._tbl.addnext(_nt)
set_text(P(_nt), "Note: the six pairs that include US Power start in January 2015 under Equal Weight and in March 2017 under Inverse Vol (which needs Power's Value sleeve, flat until December 2016, and 63 days of volatility); the other 15 pairs start in 2012. The two columns are therefore not comparable for the Power pairs.")''')
r('''[["Cross-commodity (six buckets)",''', '''[["US Power (from 2017)", I(stp(EW4_P)["ir"]), I(stp(EW_P)["ir"]), I(stp(IV4_P)["ir"]), I(stp(IV_P)["ir"])], ["Cross-commodity (seven buckets, from January 2015)",''')
r('rebuild_table(t25, [[lab] + corrrow(v) for v, lab in ORD])', 'rebuild_table(t25, [[lab] + corrrow(v) for v, lab in ORD + [("power", "US Power (from 2017)")]])')
r('"1 January 2012 to 30 September 2026 for all six buckets.")', '"1 January 2012 to 30 September 2026 for the six research buckets, and 7 January 2015 to 30 September 2026 for the cross-commodity book (seven buckets).")')
r("US Power is a standalone bucket outside the cross-commodity book and is reported from 2 January 2017 (its data start in 2015 and Value needs two years of F3), so it has no P1.",
  "US Power is the seventh bucket of the cross-commodity book, which therefore starts with the Power data; on its own it is reported from 2 January 2017 (its data start in 2015 and Value needs two years of F3), so it has no P1.")
r("The Correlation Analysis and the Cross-Commodity Portfolio cover the six buckets and all fifteen bucket pairs, so the Energy-ex-NatGas comparison no longer applies. ",
  "The Correlation Analysis and the Cross-Commodity Portfolio cover seven buckets (the six research buckets and US Power) and all 21 bucket pairs on common dates from January 2015, so the Energy-ex-NatGas comparison no longer applies and the book's figures are not comparable with those of earlier versions, which started in 2012. ")
r("is added as a standalone bucket with its own section, appendix tables and figures; it is not part of the cross-commodity book. ",
  "is added as a bucket with its own section (reported from 2017), appendix tables and figures, and as the seventh bucket of the cross-commodity book. ")
r("for the Cross-Pair Portfolios (all fifteen pairs).", "for the Cross-Pair Portfolios (all 21 pairs).")
s = s.replace("US Power (Standalone)", "US Power")
# the cross-commodity figure caption
r('swap_image("Figure 6. Cross-Commodity", os.path.join(IMG, "fig_cross_combined.png"))',
  'swap_image("Figure 6. Cross-Commodity", os.path.join(IMG, "fig_cross_combined.png"))\nset_text(P(E()[find_p("Figure 6. Cross-Commodity")]), "Figure 6. Cross-Commodity Portfolio: Combined Strategy Performance (Seven Buckets, Cumulative Return, January 2015-2026)")')
r('"Figure A26. Cross-Pair Portfolios, Equal Weight: Equity Curve by Bucket Pair (2012-2026)"', '"Figure A26. Cross-Pair Portfolios, Equal Weight: Equity Curve by Bucket Pair (2012-2026; the six pairs with US Power from January 2015)"')
r('"Figure A27. Cross-Pair Portfolios, Inverse Vol: Equity Curve by Bucket Pair (2012-2026)"', '"Figure A27. Cross-Pair Portfolios, Inverse Vol: Equity Curve by Bucket Pair (2012-2026; the six pairs with US Power from 2017)"')
r('"Petroleum-NGL is the best of fifteen pairs (+1.31, +1.38);', '"Petroleum-NGL is the best of 21 pairs (+1.31, +1.38);')
r('"Six buckets: +1.06 and +1.12 at 5.4% volatility, positive in every period; commodity-index correlation +0.19 and +0.16 (was +0.18 and +0.15)"',
  '"Seven buckets (US Power added), January 2015 to 30 September 2026: +0.99 and +1.05 at 6.5% and 6.6% volatility, positive in every period; the six-bucket book on the same window earns +1.11 and +1.15 (+1.06 and +1.12 from 2012); commodity-index correlation +0.18 and +0.18 (was +0.18 and +0.15)"')
r('"+0.42 in the six-bucket book (equity +0.16, gold +0.14)"', '"+0.35 in the seven-bucket book from January 2015 (equity +0.12, gold +0.09; +0.42, +0.16 and +0.14 in the six-bucket book from 2012)"')
r('"Rewritten on six buckets; Petroleum, Metals, Precious Metals and Agriculture findings unchanged"', '"Rewritten on seven buckets; Petroleum, Metals, Precious Metals and Agriculture findings unchanged"')
r("New standalone US Power section (outside the six-bucket book): five ICE series (PJM Peak and OffPeak, ERCOT Peak and OffPeak, MISO Peak; MISO OffPeak excluded at 9.9 days), data to 30 September 2026, reported from 2017 (no P1); Equal Weight IR +0.30, Inverse Vol +0.31",
  "New US Power section (reported from 2017, no P1) and seventh bucket of the cross-commodity book: five ICE series (PJM Peak and OffPeak, ERCOT Peak and OffPeak, MISO Peak; MISO OffPeak excluded at 9.9 days), data to 30 September 2026; Equal Weight IR +0.30, Inverse Vol +0.31 on its own window")
open(p, "w", encoding="utf8").write(s)
print("patched")
