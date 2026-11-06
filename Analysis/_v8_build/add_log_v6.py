"""Append the v6 entries to the Verification Log of the built v6 file (idempotent guard on the marker text)."""
import sys, copy, re, warnings
warnings.filterwarnings("ignore")
import docx
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table

F = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia\Analysis\Risk Premia Analysis v6_Metals and Petroleum_2012.docx"
d = docx.Document(F)
ps = d.paragraphs
if any(p.text.startswith("v6 (1 November 2026)") for p in ps):
    sys.exit("already added")
h = next(p for p in ps if p.text.startswith("Appendix: Verification Log"))
h.runs[0].text = "Appendix: Verification Log (v3_2012 to v6)"
for r in h.runs[1:]: r._r.getparent().remove(r._r)
intro = next(p for p in ps if p.text.startswith("Every figure in this document was recomputed"))
new_p = copy.deepcopy(intro._p); intro._p.addnext(new_p)
np_ = Paragraph(new_p, intro._parent)
np_.runs[0].text = ("v6 (1 November 2026) covers the Metals and Petroleum sections only. Their per-product net returns come from the pipeline run on the data cut at 30 September 2026 (tag 0930); for every Metals and Petroleum product and sleeve they are identical to the v5 series on every date to 23 September "
                    "(difference 0.0 on all 40 series, checked cell by cell including missing values), and add five trading days (24 to 30 September). The class-level statistics of the 7 series in each of the 4 windows (56 rows, four statistics each) agree with the 0930 research dashboard dataset to within 0.0005, "
                    "all 15 'Return, Vol, Max Drawdown, IR' lines of the two sections and all 96 cells of Tables A1 to A6 were found in or equal to that dataset, and the within-class correlations agree with it to within 0.0005. The Skewness signal was recomputed separately from the rolled log prices (pandas skewness, identical sign on every day for all eight products) and the leg P&L reproduces under the engine's one-day execution delay; "
                    "the contango averages and backwardation shares and the WTI and metals price levels were recomputed from the curve files. Every sentence-level claim in the two sections is asserted in code before the text is written, so a claim that fails stops the build. "
                    "External facts were re-checked on 1 November 2026 (see the last three rows below). The rest of the document keeps the v5 verification.")
for r in np_.runs[1:]: r._r.getparent().remove(r._r)
tb = Table(next(e for e in d.element.body.iterchildren() if e.tag == qn("w:tbl") and Table(e, d).rows[0].cells[0].text == "Earlier statement"), d)
ROWS = [
    ["v5: Energy section with five products (WTI, Brent, RBOB, Heating Oil, Natural Gas), plus an Energy ex-NatGas paragraph and Table A7",
     "Replaced by a Petroleum section (the four oil products). Natural Gas moved to the Power, Emissions and Nat Gas bucket, so the Natural Gas figures, the Energy ex-NatGas comparison and Table A7 are removed; tables after A6 are renumbered (old A8 to A26 are now A7 to A25)",
     "ENGINE_CHANGELOG 31 October 2026 (buckets); dashboard tab Petroleum"],
    ["v5: Metals and Energy charts show cumulative return in % starting at 0",
     "Figures 1, 2 and A1 to A10 are redrawn as the growth of 1 (geometric compounding of the daily net log returns, every curve starts at 1.0 on 3 January 2012); the other figures are unchanged",
     "Chart code make_charts_v6.py"],
    ["v5: Metals and Energy figures end on 23 September 2026",
     "Metals and Petroleum now end on 30 September 2026 (five more trading days). Metals changes: Momentum IR -0.32 to -0.33 (P3 -0.55 to -0.58), Carry +0.13 to +0.12 (P3 -0.05 to -0.07), Carry-Momentum -0.08 to -0.09, Value P3 +0.76 to +0.79, Skewness -0.08 to -0.09, Equal Weight -0.04 to -0.05, Inverse Vol +0.08 to +0.07; the four-sleeve portfolios -0.01 to -0.02 and +0.16 to +0.14; P3 by metal: Momentum Lead -1.15 to -1.17, Zinc -0.51 to -0.52, Copper -0.32 to -0.33, Aluminium +0.64 to +0.61; Value Lead +0.89 to +0.88, Zinc +0.71 to +0.73, Aluminium +0.58 to +0.61, Copper +0.13 to +0.15; Aluminium long on 23% to 24% of Skewness days",
     "Recomputed; dashboard tag 0930"],
    ["v5: Energy Momentum 'calendar years 2014, 2015, 2020 and 2021 account for 95%'",
     "95% was the five-product figure; for Petroleum these four years are 87% (2022 adds 14%, the first nine months of 2026 add 24%, previously 23%)",
     "Recomputed from sleeve returns"],
    ["v5: Energy Carry 'weakest in P3 (IR +0.20)'",
     "Petroleum Carry is close to flat in P3 (IR +0.04; WTI -0.31, Brent -0.37, RBOB +0.21, Heating Oil +0.73), still positive in every period",
     "Recomputed"],
    ["v5: Energy Value 'negative in four of the five products'; Natural Gas decomposition and Natural Gas Skewness sentences",
     "Petroleum Value is negative in three of the four products (-0.23 to -0.07) and flat in Brent (+0.02); the Natural Gas sentences are removed with the product",
     "Recomputed"],
    ["v5: Energy portfolios 'almost identical' (Equal Weight +0.76, Inverse Vol +0.78)",
     "Petroleum Equal Weight +0.84 and Inverse Vol +0.89: Inverse Vol is ahead by 0.04 with slightly lower volatility and a shallower drawdown, against 0.12 in Metals; Skewness lifts Equal Weight +0.67 to +0.84 and Inverse Vol +0.71 to +0.89",
     "Recomputed"],
    ["v5: 'the LME's first queue report, May 2014, put the longest aluminium wait at 748 days'",
     "Not confirmed in any source found on 1 November 2026 (LME and Fastmarkets figures for 2014 range from 625 days at Detroit to queues of more than two years at Vlissingen); replaced by the confirmed statement that the Vlissingen queue peaked in 2014 at more than two years",
     "Fastmarkets (Access World Vlissingen delisting article)"],
    ["Copper 'high of our series, $14,851 on 22 September 2026'",
     "Still the high of the series to 30 September. Market reports found on 1 November 2026 give LME three-month records of about $14,500 on 7 to 8 September and above $14,800 on 10 September (v5 sources); a later September LME record could not be confirmed",
     "Series check; XTB and Sentisense (7 to 8 September), v5 sources"],
    ["Iran war and Brent text ('the largest in the history of the oil market', IEA)",
     "Confirmed: the IEA described the disruption as the largest supply disruption in the history of the oil market in its March 2026 report",
     "IEA Oil Market Report, March 2026, as reported by Bloomberg and Reuters"],
]
last = tb.rows[-1]._tr
for row in ROWS:
    tr = copy.deepcopy(last); tb._tbl.append(tr)
    from docx.table import _Row
    r = _Row(tr, tb)
    for c, t in zip(r.cells, row):
        p = c.paragraphs[0]; p.runs[0].text = t
        for x in p.runs[1:]: x._r.getparent().remove(x._r)
d.save(F)
print("log added")
