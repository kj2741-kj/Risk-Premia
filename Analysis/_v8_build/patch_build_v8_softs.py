"""One-off patch of build_v8.py for the 10 November 2026 changes (Agriculture split into Agriculture and Softs, Natural Gasoline in NGL, seven buckets, 29 products, 21 pairs).
Every replacement must match exactly once. The original is kept in ../_v8_build_backup_pre_agri_split/."""
p = "build_v8.py"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:100])
    s = s.replace(a, b)


# ---------------------------------------------------------------- imports
rep("from text_power import power\n", "from text_power import power\nfrom text_agri import agri, agri_narr\nfrom text_softs import softs, softs_narr\n")

# ---------------------------------------------------------------- Power tables anchor (must be done before the Agriculture block below is inserted) and the Power product table
rep('# appendix tables: after the Agriculture carry tenor-pair table', '# appendix tables: after the Softs tables')
rep('''els = E(); i17 = find_p("Table A17. Agriculture: Carry Tenor Pairs"); assert is_tbl(els[i17 + 1])
anchor = els[i17 + 2]''', '''anchor = SOFTS_TABLE_ANCHOR      # the last element of the Softs appendix tables (inserted above)''')
rep('''== ["Ethane", "Propane", "Butane", "Naphtha"]      # the NGL product table the Power table is cloned from has four products since Isobutane was removed''',
    '''== ["Ethane", "Propane", "Butane", "Naphtha", "Natural Gasoline"]      # the NGL product table the Power table is cloned from has five products since Natural Gasoline joined''')
rep('''add_column(tpi, "", [""] * 5)      # the five Power series need five columns\n''', '''# the five NGL columns are exactly what the five Power series need\n''')

# ---------------------------------------------------------------- NGL table A13: five products
rep('''add_column(t13, "Naphtha", [""] * 5)\n''', '''add_column(t13, "Naphtha", [""] * 5)\nadd_column(t13, "Natural Gasoline", [""] * 5)\n''')

# ---------------------------------------------------------------- Agriculture and Softs appendix tables (v7 numbering A14 to A17)
rep('''_, t18 = tbl_after("Table A18."); BC = {k: bench_corr(BS[k]) for k in SLEEVES + ["EW PORT", "Inverse Vol"]}''',
    '''# ---- Agriculture (four products) and Softs (new) appendix tables; the carry tenor-pair table A17 is not reproduced (the pairs were fixed by decision on 10 November 2026)
_, t14 = tbl_after("Table A14. Agriculture: Strategy"); assert labels(t14) == SLN
for r, vals in zip(t14.rows[1:], st_cells("agri", SLEEVES)):
    for c, x in zip(r.cells[1:], vals): cell_set(c, x)
_, t15 = tbl_after("Table A15. Agriculture: Portfolio"); assert labels(t15) == ["Equal Weight", "Inverse Vol"]
for r, vals in zip(t15.rows[1:], st_cells("agri", ["EW PORT", "Inverse Vol"])):
    for c, x in zip(r.cells[1:], vals): cell_set(c, x)
_, t16 = tbl_after("Table A16. Agriculture: Individual-Product"); assert [c.text for c in t16.rows[0].cells[1:]] == ["Corn", "Wheat", "Soybean", "Soybean Oil", "Coffee", "Sugar"]
delete_column(t16, 6); delete_column(t16, 5); delete_column(t16, 4)      # Sugar, Coffee, Soybean Oil
add_column(t16, "Live Cattle", [""] * 5)
for r, k in zip(t16.rows[1:], K):
    for c, (a, p) in zip(r.cells[1:], MEMBERS["agri"]): cell_set(c, I(pst(a, p, k)["ir"]))
els = E(); i17_ = find_p("Table A17. Agriculture: Carry Tenor Pairs"); assert is_tbl(els[i17_ + 1])
for e in els[i17_:i17_ + 3]: body.remove(e)
els = E(); i14_ = find_p("Table A14. Agriculture: Strategy"); i16_ = find_p("Table A16. Agriculture: Individual-Product")
blk_a = els[i14_:i16_ + 3]; assert len(blk_a) == 9 and [is_tbl(e) for e in blk_a] == [False, True, False] * 3
anchor = blk_a[-1]; softs_tbl = []
for e in blk_a:
    n_ = copy.deepcopy(e); anchor.addnext(n_); anchor = n_; softs_tbl.append(n_)
SOFTS_TABLE_ANCHOR = softs_tbl[-1]
set_text(P(softs_tbl[0]), "Table A?. Softs: Strategy Information Ratios by Period")
set_text(P(softs_tbl[3]), "Table A?. Softs: Portfolio Construction Information Ratios by Period")
set_text(P(softs_tbl[6]), "Table A?. Softs: Individual-Product Information Ratios, All Strategies (Full Sample)")
sa_, sb_, sc_ = Table(softs_tbl[1], d), Table(softs_tbl[4], d), Table(softs_tbl[7], d)
for r, vals in zip(sa_.rows[1:], st_cells("softs", SLEEVES)):
    for c, x in zip(r.cells[1:], vals): cell_set(c, x)
for r, vals in zip(sb_.rows[1:], st_cells("softs", ["EW PORT", "Inverse Vol"])):
    for c, x in zip(r.cells[1:], vals): cell_set(c, x)
for c, (a, p) in zip(sc_.rows[0].cells[1:], MEMBERS["softs"]): cell_set(c, PNM.get(p, p))
for r, k in zip(sc_.rows[1:], K):
    for c, (a, p) in zip(r.cells[1:], MEMBERS["softs"]): cell_set(c, I(pst(a, p, k)["ir"]))

# ----------------------------------------------------------------------------------------------------------------------------- Cross-commodity appendix tables below
_, t18 = tbl_after("Table A18."); BC = {k: bench_corr(BS[k]) for k in SLEEVES + ["EW PORT", "Inverse Vol"]}''')

# ---------------------------------------------------------------- cross-commodity tables
rep('"Table A19. Cross-Commodity Portfolio: Strategy Information Ratios by Period (all six buckets)"', '"Table A19. Cross-Commodity Portfolio: Strategy Information Ratios by Period (all seven buckets)"')
rep('"Table A20. Cross-Commodity Portfolio: Construction Information Ratios by Period (all six buckets)"', '"Table A20. Cross-Commodity Portfolio: Construction Information Ratios by Period (all seven buckets)"')
rep('"Table A21. Cross-Pair Portfolio: Full-Sample Information Ratios, All Fifteen Bucket Pairs"', '"Table A21. Cross-Pair Portfolio: Full-Sample Information Ratios, All Twenty-One Bucket Pairs"')
rep('("ngl", "NGL"), ("agri", "Agriculture")]\nrows23 = []', '("ngl", "NGL"), ("agri", "Agriculture"), ("softs", "Softs")]\nrows23 = []')
rep('["Cross-commodity (six buckets)"', '["Cross-commodity (seven buckets)"')
rep('"SoybeanOil": "Soybean Oil", "UKGas": "UK Gas", "EUA": "EUA"}', '"SoybeanOil": "Soybean Oil", "UKGas": "UK Gas", "EUA": "EUA", "LiveCattle": "Live Cattle", "NatGasoline": "Natural Gasoline"}')

# ---------------------------------------------------------------- liquidity table A26
rep('("NGL", ["Propane", "Butane", "Ethane", "Naphtha"]), ("Agriculture", ["Soybean", "Coffee", "Corn", "SoybeanOil", "Wheat", "Sugar"]),', '("NGL", ["Propane", "Butane", "Ethane", "Naphtha", "NatGasoline"]), ("Agriculture", ["Soybean", "Corn", "Wheat", "LiveCattle"]), ("Softs", ["Sugar", "Cocoa", "Coffee", "Cotton"]),')
rep('chk(len(allp) == 33, "33 liquidity products")', 'chk(len(allp) == 36, "36 liquidity products")')
rep('"Naphtha": "Naphtha*", "Isobutane": "Isobutane*",', '"Naphtha": "Naphtha*", "NatGasoline": "Natural Gasoline*", "LiveCattle": "Live Cattle", "Isobutane": "Isobutane*",')
rep('p in ("Propane", "Butane", "Ethane", "Isobutane", "SoybeanOil", "Sugar") and v < 10', 'p in ("Propane", "Butane", "Ethane", "Isobutane", "SoybeanOil", "Sugar", "LiveCattle", "Cotton", "NatGasoline") and v < 10')
rep('(33 Products, Six Buckets and US Power)', '(36 Products, Seven Buckets and US Power)')
rep('_lab = "Results across 33 products."', '_lab = "Results across 36 products."')
rep('"The table covers 33 products: the 26 of the six buckets,', '"The table covers 36 products: the 29 of the seven buckets,')
rep('assert "33 products" in nt and "Bloomberg series" in nt and "MISO OffPeak (time" in nt', 'assert "36 products" in nt and "Bloomberg series" in nt and "MISO OffPeak (time" in nt')

# ---------------------------------------------------------------- front matter
rep('"Metals, Petroleum, Gas and Emissions, Precious Metals, NGL, Agriculture, US Power (Standalone), Correlation Analysis, and Cross-Commodity Portfolio"', '"Metals, Petroleum, Gas and Emissions, Precious Metals, NGL, Agriculture, Softs, US Power (Standalone), Correlation Analysis, and Cross-Commodity Portfolio"')
rep('"1 January 2012 to 30 September 2026 for all six buckets."', '"1 January 2012 to 30 September 2026 for all seven buckets."')
i0 = s.index('set_text(P(E()[iv_]), "Version note (v8')
i1 = s.index('ipet = find_p("Petroleum is the four oil products")')
VERSION = '''set_text(P(E()[iv_]), "Version note (v8, 10 November 2026). All seven buckets are on the data to 30 September 2026 and the current bucket definitions. Gas and Emissions (Henry Hub, TTF, UK Gas and EUA) is a new section, with its own appendix tables and figures; "
         "Henry Hub, previously part of Energy, is in it and UK Gas is new. NGL has five products (Ethane, Propane, Butane, Naphtha and Natural Gasoline): Naphtha is added to the three Mont Belvieu products, the CME Mont Belvieu natural gasoline swap (MMB) is added as the fifth on 10 November 2026, and Isobutane, the least liquid product in the data set, is removed from every bucket, pair, correlation and table. "
         "Agriculture is split in two on 10 November 2026: Agriculture (Corn, Wheat, Soybean and Live Cattle) and Softs (Sugar, Cocoa, Coffee and Cotton), a new section with its own appendix tables and figures; Soybean Oil is dropped, Live Cattle, Cocoa and Cotton are new, and the Carry tenor pairs are F1-F2 plus F1-F6 (F1-F7 for Soybean and Live Cattle). The comparison table of single and two-pair Carry in the earlier Agriculture section is not reproduced, because the pairs were fixed by decision. "
         "The Correlation Analysis and the Cross-Commodity Portfolio cover the seven buckets and all twenty-one bucket pairs, so the Energy-ex-NatGas comparison no longer applies. "
         "US Power (PJM, ERCOT and MISO real-time monthly futures) is added as a standalone bucket with its own section, appendix tables and figures; it is not part of the cross-commodity book. The Key Findings, the liquidity section and table (36 products, with UK Gas, Naphtha, Natural Gasoline, Live Cattle, Cocoa, Cotton and the US Power series) and every appendix table and figure are redrawn on this basis, all figures as a cumulative return index starting at 100%, and tables and figures are renumbered.")
'''
s = s[:i0] + VERSION + s[i1:]
# Precious Metals bullet: the sentence on Agriculture
rep('''# ----------------------------------------------------------------------------------------------------------------------------- Key Findings
els = E(); ik = find_p("Key Findings", style="Heading 2")''', '''ipm_ = find_p("Portfolio construction: Equal Weight (Return -1.8%, Vol 7.8%"); tpm_ = ptext(E()[ipm_])
a_pm = "Precious Metals is, with Agriculture, one of the two asset classes where no core strategy earns a worthwhile IR (here every core strategy is net negative full-sample) and neither construction earns a positive IR."
assert a_pm in tpm_
set_text(P(E()[ipm_]), tpm_.replace(a_pm, "Precious Metals is, with Agriculture, one of the two buckets where every core strategy is net negative full-sample, and with Agriculture and Softs one of the three buckets where neither construction earns a positive IR."))

# ----------------------------------------------------------------------------------------------------------------------------- Key Findings
els = E(); ik = find_p("Key Findings", style="Heading 2")''')

# ---------------------------------------------------------------- Agriculture section text, Softs section (cloned), before the Correlation Analysis
rep('c8 = corr8()\n', '''# ----------------------------------------------------------------------------------------------------------------------------- Agriculture section (four products) and the new Softs section
els = E(); iag_n = find_p("Agriculture (Corn, Wheat, Soybean, Soybean Oil, Coffee and Sugar) shows no premium")
set_text(P(E()[iag_n]), agri_narr())
ibl_ = find_p("Agriculture (six products: Corn, Wheat, Soybean, Soybean Oil, Coffee, Sugar) has no edge")
set_bullets_run(E()[ibl_ - 1], [b_[1] for b_ in agri() if b_[0] == "b"])
els = E(); iag_h = find_p("Agriculture", style="Heading 2"); cap_ag_ = find_p("Figure 5. Agriculture")
rng = els[iag_h:cap_ag_ + 1]
anchor = rng[-1]; cl = []
for e in rng:
    n_ = copy.deepcopy(e); anchor.addnext(n_); anchor = n_; cl.append(n_)
set_text(P(cl[0]), "Softs")
narr_i = next(i for i, e in enumerate(cl) if is_p(e) and len(ptext(e)) > 300 and P(e).style.name == "Normal")
set_text(P(cl[narr_i]), softs_narr())
bl_ = [e for e in cl if is_p(e) and P(e).style.name == "List Bullet"]
set_bullets_run(bl_[0].getprevious(), [b_[1] for b_ in softs() if b_[0] == "b"])
cl = [e for e in cl if e.getparent() is not None]
new_fig = make_figure_para(cl[-2], os.path.join(IMG, "fig_softs_combined.png")); cl[-2].addnext(new_fig); cl[-2].getparent().remove(cl[-2])
SOFTS_CAP = cl[-1]
set_text(P(SOFTS_CAP), "Figure ?. Softs: Combined Strategy Performance (Cumulative Return, 2012-2026)")

c8 = corr8()
''')
rep('''els = E(); cap_ag = find_p("Figure 5. Agriculture")
anchor = E()[cap_ag]''', '''anchor = SOFTS_CAP''')

# ---------------------------------------------------------------- appendix charts of Softs (cloned from the Agriculture group), before the Power group
rep('''# appendix charts: after the Agriculture group, before the Cross-Pair group
''', '''# appendix charts of Softs: a copy of the Agriculture group, right after it
els = E(); ia_ = find_p("Agriculture", find_p("Appendix: Equity-Curve Charts", style="Heading 2"), "Heading 3")
grp_a = els[ia_:ia_ + 11]; assert is_p(grp_a[0]) and all(is_p(e) for e in grp_a)
anchor = grp_a[-1]
hs_ = copy.deepcopy(grp_a[0]); set_text(P(hs_), "Softs"); anchor.addnext(hs_); anchor = hs_
for j, k in enumerate(K):
    f_ = make_figure_para(grp_a[1 + 2 * j], os.path.join(IMG, f"figA_softs_{k}.png")); anchor.addnext(f_); anchor = f_
    cn_ = copy.deepcopy(grp_a[2 + 2 * j]); set_text(P(cn_), f"Figure A?. Softs, {KN[k]}: Equity Curve by Product (2012-2026)"); anchor.addnext(cn_); anchor = cn_
# appendix charts of US Power: after the Softs group, before the Cross-Pair group
''')
rep("for the Cross-Pair Portfolios (all fifteen pairs).", "for the Cross-Pair Portfolios (all twenty-one pairs).")
open(p, "w", encoding="utf-8").write(s)
print("patched build_v8.py")
