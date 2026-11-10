"""Reinstates the Carry tenor-pair table (single short pair, long pair alone, two-pair sum) for Agriculture and Softs on the pairs chosen on 10 November 2026."""
p = "build_v8.py"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:100])
    s = s.replace(a, b)


rep("from text_softs import softs, softs_narr\n", "from text_softs import softs, softs_narr\nfrom facts_tenor import tenor_table\n")
# the Agriculture tenor-pair table is kept and refilled instead of removed
rep('''els = E(); i17_ = find_p("Table A17. Agriculture: Carry Tenor Pairs"); assert is_tbl(els[i17_ + 1])
for e in els[i17_:i17_ + 3]: body.remove(e)
''', '''TEN_HDR = ["", "Short pair alone (F1-F2)", "Long pair alone", "Two-pair sum"]


def fill_tenor(tb, bucket):
    res_, _, _ = tenor_table(bucket)
    assert [c.text for c in tb.rows[0].cells] in (["", "Previous single pair (F1-F2)", "Long pair alone", "Two-pair sum"], TEN_HDR), [c.text for c in tb.rows[0].cells]
    for c, x in zip(tb.rows[0].cells, TEN_HDR): cell_set(c, x)
    assert labels(tb) == ["Carry", "Carry-Momentum"]
    for r, sl_ in zip(tb.rows[1:], ("Carry", "CarryMom")):
        for c, nm_ in zip(r.cells[1:], ("short", "long", "two")): cell_set(c, I(res_[sl_][nm_]["ir"]))


_, t17 = tbl_after("Table A17. Agriculture: Carry Tenor Pairs"); fill_tenor(t17, "agri")
set_text(P(E()[find_p("Table A17. Agriculture: Carry Tenor Pairs")]), "Table A17. Agriculture: Carry Tenor Pairs, Full-Sample Information Ratios (long pair F1-F6 for Corn and Wheat, F1-F7 for Soybean and Live Cattle)")
els = E(); i17_ = find_p("Table A17. Agriculture: Carry Tenor Pairs"); assert is_tbl(els[i17_ + 1])
''')
rep('''blk_a = els[i14_:i16_ + 3]; assert len(blk_a) == 9 and [is_tbl(e) for e in blk_a] == [False, True, False] * 3''', '''blk_a = els[i14_:i17_ + 3]; assert len(blk_a) == 12 and [is_tbl(e) for e in blk_a] == [False, True, False] * 4''')
rep('''sa_, sb_, sc_ = Table(softs_tbl[1], d), Table(softs_tbl[4], d), Table(softs_tbl[7], d)''', '''set_text(P(softs_tbl[9]), "Table A?. Softs: Carry Tenor Pairs, Full-Sample Information Ratios (long pair F1-F6 for all four products)")
fill_tenor(Table(softs_tbl[10], d), "softs")
sa_, sb_, sc_ = Table(softs_tbl[1], d), Table(softs_tbl[4], d), Table(softs_tbl[7], d)''')
# version note
rep(" The comparison table of single and two-pair Carry in the earlier Agriculture section is not reproduced, because the pairs were fixed by decision. ", " The single-pair, long-pair and two-pair Carry comparison of the Agriculture section is recomputed for the new pairs, in Agriculture and in Softs. ")
# verification row
rep('''    ["v8 Agriculture section: table of single-pair, long-pair and two-pair Carry and Carry-Momentum IRs", "Not reproduced: the Carry pairs were fixed by decision on 10 November 2026 (F1-F2 plus F1-F6; F1-F7 for Soybean and Live Cattle), so the comparison no longer informs a choice", "Decision of 10 November 2026"],''',
    '''    ["v8 Agriculture section: table of single-pair, long-pair and two-pair Carry and Carry-Momentum IRs (six products)", f"Recomputed for the pairs fixed on 10 November 2026 (F1-F2 plus F1-F6; F1-F7 for Soybean and Live Cattle), in Agriculture and in the new Softs bucket; the two-pair series are equal to the reported bucket sleeves (difference below 1e-9). Agriculture Carry {I(_tenA['Carry']['short']['ir'])} / {I(_tenA['Carry']['long']['ir'])} / {I(_tenA['Carry']['two']['ir'])} (short / long / sum); Softs {I(_tenS['Carry']['short']['ir'])} / {I(_tenS['Carry']['long']['ir'])} / {I(_tenS['Carry']['two']['ir'])}", "Recomputed; facts_tenor.py"],''')
rep('''_bi = _Fc["best_iv"]\n''', '''_bi = _Fc["best_iv"]\n_tenA = tenor_table("agri")[0]; _tenS = tenor_table("softs")[0]\n''')
open(p, "w", encoding="utf-8").write(s)
print("patched build for tenor tables")
