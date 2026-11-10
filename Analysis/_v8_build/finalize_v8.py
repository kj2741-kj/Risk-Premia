"""Writes the v8 paragraph of the verification log (counts come from audit_v8.py, which must pass first; table numbers are read from the finished document). Run once after build_v8.py."""
import docx, re, sys
from docx.text.paragraph import Paragraph
PATH = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia\Analysis\Risk Premia Analysis v8_2012.docx"
d = docx.Document(PATH)
caps = [p.text for p in d.paragraphs if re.match(r"Table A\d+\. ", p.text)]


def tab(kw):
    hit = [c for c in caps if kw in c]
    assert len(hit) == 1, (kw, hit)
    return "A" + re.match(r"Table A(\d+)\.", hit[0]).group(1)


pw = [re.match(r"Table (A\d+)\.", c).group(1) for c in caps if "US Power (Standalone)" in c]
assert len(pw) == 3
TEXT = ("v8 (10 November 2026) extends the verification to all seven buckets, the Correlation Analysis, the Cross-Commodity Portfolio and the liquidity table. The per-product net returns come from the 0930 pipeline (scripts/final_dashboard, tag 0930), "
        "which includes UK Gas, Naphtha, Natural Gasoline and the Agriculture and Softs products of the 10 November 2026 Bloomberg pull and no longer includes Isobutane (removed on 9 November 2026 for lack of liquidity) or Soybean Oil; the 0930 dashboard dataset (final_v3.json) is the reference. "
        "Recomputed with separate code from the per-product returns and equal to the dataset to within rounding (0.001): the class-level statistics of the 7 series in each of the 4 windows "
        "for all seven buckets (196 cells), the cross-commodity by-style books and the four two-stage combinations (44 cells), the IRs of all twenty-one bucket pairs under both constructions, and the EW PORT cross-bucket correlation matrix. "
        f"All 62 'Return, Vol, Max Drawdown, IR' lines of the text are rows of the dataset; all 341 cells of the Strategy, Portfolio Construction and Individual-Product tables of the seven buckets, the 28 cells of the cross-commodity strategy and construction tables ({tab('Cross-Commodity Portfolio: Strategy Information')} and {tab('Cross-Commodity Portfolio: Construction Information')}), the 21 pair rows (Table {tab('Cross-Pair Portfolio: Full-Sample')} and the table in the Correlation Analysis, including each pair's EW PORT correlation) "
        f"and the 35 Skewness correlations of Table {tab('Skewness: Correlation with the Other Sleeves')} equal the dataset. The two Carry tenor-pair tables (Tables {tab('Agriculture: Carry Tenor Pairs')} and {tab('Softs: Carry Tenor Pairs')}) were recomputed with separate code from the curves and the roll calendars; their two-pair columns equal the bucket Carry and Carry-Momentum sleeves of the dataset and all 16 comparisons agree. The benchmark correlations (Table {tab('Correlation vs Traditional')}), the without-Skewness rows, the Skewness leg table ({tab('Share of Days Long')}) and the liquidity table ({tab('Dollar Risk Turnover')}) are not in the dataset; they are computed in the build from the same net returns, the ETF file cut at 30 September 2026 and the two liquidity result files (Liquidity_Cal2025_results.csv, whose NGL rows are CME plus ICE since 10 November 2026, and Power_Liquidity_Cal2025_results.csv), and the 36 rows of the liquidity table were checked cell by cell against those files (ADV, risk turnover, time to trade, rank, days traded, volatility and multiplier). "
        "Every sentence-level claim in the new and rewritten sections and in the Key Findings is asserted in code before the text is written; several drafting claims of the 10 November 2026 update failed those assertions in a trial run and were corrected (adding Natural Gasoline lowers the NGL Equal Weight IR in every period, including P2; Petroleum-NGL is the best pair under Equal Weight but Gas and Emissions-NGL under Inverse Vol; with Agriculture and Softs, Gas and Emissions has the third deepest Equal Weight drawdown, not the deepest). "
        "No new external facts were added: the NGL facts (EIA, OPIS, Veson Nautical, S&P Global) keep their v5 and v6 verification, the Coffee episodes in Softs (the July 2021 frost and the February 2025 high) are those verified in v7, and the Gas and Emissions price levels (TTF EUR 19.84/MWh on 4 January 2021, EUR 339.2 on 26 August 2022 and EUR 72.36 on 30 September 2026; the UK Gas and Naphtha levels) and the Cocoa high (USD 12,565 per tonne on 18 December 2024) are read from our own series. "
        f"The US Power section (standalone, from 2017) was recomputed from the Power pipeline's per-product returns with the dashboard's own bucket construction: all 112 bucket values (IR, return, volatility and maximum drawdown of the 7 series in the 4 windows) equal the dashboard's Power tab (power_tab_0930.json) and the 46 cells of its three appendix tables ({pw[0]} to {pw[2]}) equal that file; its Calendar-2025 times to trade one sigma of risk come from Power_Liquidity_Cal2025_results.csv. "
        "Table and figure numbers changed because Gas and Emissions and Softs were inserted and Table A22 of v7 (Energy pairs excluding Natural Gas) was removed; references in the text were renumbered with them.")
done = False
for p in d.paragraphs:
    if p.text.startswith("v8 (10 November 2026)"):
        rs = p.runs; rs[0].text = TEXT
        for r in rs[1:]: r._r.getparent().remove(r._r)
        done = True
assert done
d.save(PATH)
print("verification paragraph written")
