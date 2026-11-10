"""Writes the v8 paragraph of the verification log (counts come from audit_v8.py, which must pass first). Run once after build_v8.py."""
import docx, sys
from docx.text.paragraph import Paragraph
PATH = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia\Analysis\Risk Premia Analysis v8_2012.docx"
d = docx.Document(PATH)
TEXT = ("v8 (10 November 2026) extends the verification to all six buckets, the Correlation Analysis, the Cross-Commodity Portfolio and the liquidity table. The per-product net returns come from the 0930 pipeline (scripts/final_dashboard, tag 0930), "
        "which now includes UK Gas and Naphtha and no longer includes Isobutane (removed on 9 November 2026 for lack of liquidity); the 0930 dashboard dataset (final_v3.json) is the reference. Recomputed with separate code from the per-product returns and equal to the dataset to within rounding (0.001): the class-level statistics of the 7 series in each of the 4 windows "
        "for all six buckets (168 cells), the cross-commodity by-style books and the four two-stage combinations (44 cells), the IRs of all fifteen bucket pairs under both constructions, and the EW PORT cross-bucket correlation matrix. "
        "All 54 'Return, Vol, Max Drawdown, IR' lines of the text are rows of the dataset; all 298 cells of the bucket appendix tables (Tables A1 to A20), the 28 cells of the cross-commodity strategy and construction tables (A25 and A26), the 15 pair rows (Table A27 and the table in the Correlation Analysis, including each pair's EW PORT correlation) "
        "and the 30 Skewness correlations of Table A30 equal the dataset. The benchmark correlations (Table A24), the without-Skewness rows, the Skewness leg table (A28) and the liquidity table (A31) are not in the dataset; they are computed in the build from the same net returns, the ETF file cut at 30 September 2026 and the two liquidity result files (Liquidity_Cal2025_results.csv and Power_Liquidity_Cal2025_results.csv), and the 33 rows of the liquidity table were checked cell by cell against those files (ADV, risk turnover, time to trade, rank, days traded, volatility and multiplier). "
        "Every sentence-level claim in the new and rewritten sections and in the Key Findings is asserted in code before the text is written; two drafting claims failed those assertions and were corrected (the 2020-2021 Momentum log return of Gas and Emissions is 1.66, not 1.67; Skewness is negative in P1 in four buckets, Agriculture not among them). "
        "No new external facts were added: the NGL facts (EIA, OPIS, Veson Nautical, S&P Global) keep their v5 and v6 verification, and the Gas and Emissions price levels (TTF EUR 19.84/MWh on 4 January 2021, EUR 339.2 on 26 August 2022 and EUR 72.36 on 30 September 2026; the UK Gas and Naphtha levels) are read from our own series. "
        "The US Power section (standalone, from 2017) was recomputed from the Power pipeline's per-product returns with the dashboard's own bucket construction: all 112 bucket values (IR, return, volatility and maximum drawdown of the 7 series in the 4 windows) equal the dashboard's Power tab (power_tab_0930.json) and the 46 cells of its three appendix tables (A21 to A23) equal that file; its Calendar-2025 times to trade one sigma of risk come from Power_Liquidity_Cal2025_results.csv. "
        "Table and figure numbers changed because Gas and Emissions was inserted and Table A22 of v7 (Energy pairs excluding Natural Gas) was removed; references in the text were renumbered with them.")
done = False
for p in d.paragraphs:
    if p.text.startswith("v8 (10 November 2026)"):
        rs = p.runs; rs[0].text = TEXT
        for r in rs[1:]: r._r.getparent().remove(r._r)
        done = True
assert done
d.save(PATH)
print("verification paragraph written")
