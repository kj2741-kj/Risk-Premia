"""Add the v7 entries to the Verification Log of the built v7 file."""
import sys, copy, warnings
warnings.filterwarnings("ignore")
import docx
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table, _Row

F = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia\Analysis\Risk Premia Analysis v7_2012.docx"
d = docx.Document(F)
ps = d.paragraphs
if any(p.text.startswith("v7 (1 November 2026)") for p in ps):
    sys.exit("already added")


def set_text(p, t):
    p.runs[0].text = t
    for r in p.runs[1:]: r._r.getparent().remove(r._r)


h = next(p for p in ps if p.text.startswith("Appendix: Verification Log"))
set_text(h, "Appendix: Verification Log (v3_2012 to v7)")
v6 = next(p for p in ps if p.text.startswith("v6 (1 November 2026)"))
new_p = copy.deepcopy(v6._p); v6._p.addnext(new_p)
set_text(Paragraph(new_p, v6._parent),
         "v7 (1 November 2026) extends the v6 verification to Precious Metals and Agriculture and to the Key Findings of the four updated classes. The 0930 pipeline (scripts/final_dashboard, tag 0930) was re-run after Dimil Patel's commit 5ebe183 (Value on the F2 contract for Precious Metals and Agriculture); it reproduces the committed Final_Research_Dashboard_2012_0930.html exactly "
         "(3,072 numbers, maximum difference 0.0). Against the run used for v6 only the Value sleeves of the ten Precious Metals and Agriculture products changed; every Metals, Petroleum, NGL, Power, Emissions and Nat Gas series is identical (difference 0.0), so the v6 sections stand. "
         "The class-level statistics of the 7 series in each of the 4 windows for the four updated classes agree with the dashboard dataset to within 0.0005; all 30 'Return, Vol, Max Drawdown, IR' lines in the four sections and all 202 cells of the appendix tables for the four classes (Tables A1 to A9 and A14 to A16) were found in or equal to that dataset. "
         "The single-pair Carry tables (A10, A17) come from a separate run of compute_products.py on Prices_0930, and the two-pair sums in them equal the dashboard's Carry. The gold real-yield correlations use FRED DFII10 downloaded on 1 November 2026 and cut at 30 September 2026. "
         "As in v6, every sentence-level claim in the sections and in the Key Findings is asserted in code before the text is written. External facts re-checked on 1 November 2026: central bank gold purchases of 863 tonnes in 2025 against a 2010-2021 average of 473 tonnes (World Gold Council), FAO Food Price Index 159.3 in March 2022 and a 2023 average 13.7% below 2022, the USDA August 2012 corn price projection of $7.50 to $8.90. "
         "Facts not listed here keep their v5 verification of 13 October 2026.")
tb = Table(next(e for e in d.element.body.iterchildren() if e.tag == qn("w:tbl") and Table(e, d).rows[0].cells[0].text == "Earlier statement"), d)
# update the v6 chart row
for r in tb.rows:
    if r.cells[0].text.startswith("v5: Metals and Energy charts show cumulative return"):
        set_text(r.cells[0].paragraphs[0], "v5 and v6: charts show cumulative return in % starting at 0 (v6: growth of 1)")
        set_text(r.cells[1].paragraphs[0], "All figures (1 to 6 and A1 to A27) are redrawn as a cumulative return index starting at 100% on 3 January 2012 (geometric: the exponential of the cumulative daily net log return). Charts of the sections not updated (NGL, cross-commodity, cross-pair) show the v5 data to 23 September 2026 in the new style")
        break
else:
    raise SystemExit("chart row not found")
ROWS = [
    ["v5: Precious Metals and Agriculture Value on the F3 contract",
     "Value is on the F2 contract from 1 November 2026 (sparse contract cycles put F3 four to six months from the front; commit 5ebe183). Only the Value sleeves of the ten products change. Precious Metals Value IR -0.06 to -0.05 (P1 +0.05 to +0.01, P2 -0.07 to -0.05, P3 -0.13 to -0.08); Platinum +0.11 to +0.08, Gold -0.23 to -0.22, Gold P3 -0.61 to -0.56. "
     "Agriculture Value IR -0.10 to -0.14 (P1 -0.01 to -0.11, P2 -0.24 to -0.26, P3 -0.07 to -0.06); Corn -0.30 to -0.36, Wheat +0.09 to +0.17. The basis paragraph now states the Value contract",
     "ENGINE_CHANGELOG 1 November 2026; pipeline re-run, dashboard reproduced exactly"],
    ["v5: Agriculture Value 'flat in P1 (IR -0.01)', 'the class is flat only because Coffee offsets it'; Corn P1 -0.50",
     "Value is negative in every period (P1 -0.11, P2 -0.26, P3 -0.06); Corn P1 is -0.54 and Wheat -0.24, with Coffee (+0.53, previously +0.58) the offset; Corn loses in every year 2012 to 2016 (log returns -0.13, -0.16, -0.07, -0.19, -0.12, previously -0.03, -0.20, -0.05, -0.19, -0.12)",
     "Recomputed"],
    ["v5: Precious Metals and Agriculture figures end on 23 September 2026",
     "Now 30 September 2026. Precious Metals: Momentum IR -0.24 to -0.22, Carry -0.08 to -0.07 (P3 -0.02 to 0.00), Skewness +0.10 to +0.09, Equal Weight -0.23 to -0.22, Inverse Vol -0.29 to -0.28; Silver Skewness 2026 +0.52 to +0.45 and Gold and Silver long-leg P3 log returns +0.51 and +0.91 to +0.47 and +0.84. "
     "Agriculture: Momentum -0.12 to -0.14, Carry +0.01 to -0.01 (still flat), Carry-Momentum -0.34 to -0.35, Skewness +0.25 to +0.24, Equal Weight -0.15 to -0.19, Inverse Vol -0.18 to -0.20",
     "Recomputed; dashboard tag 0930"],
    ["v5: price levels at 23 September 2026 (Wheat $7.09/bu, Corn $5.29, Soybean Oil 67.3 cents/lb, Coffee $2.76/lb)",
     "At 30 September 2026 in our series: Wheat $6.76, Corn $5.01, Soybean Oil 67.85 cents, Coffee $2.91",
     "Series check"],
    ["v5: Gold F1-F7 curve 'averaged -4.5% in P3'",
     "-4.6% to 30 September 2026 (Silver F1-F6 -4.5%); the real-yield correlations (full sample -0.39, P2 -0.64, P3 -0.24) and the P3 average real yield (1.60%) are unchanged on the data to 30 September",
     "Recomputed from curves; FRED DFII10 downloaded 1 November 2026"],
    ["v5 Key Findings: Energy at +0.76 and +0.78, 'excluding Natural Gas ... improves Momentum, Value and above all Skewness'; Metals Equal Weight -0.04; Precious Metals -0.23 and -0.29; Agriculture -0.15 and -0.18",
     "Key Findings rewritten for Metals, Petroleum, Precious Metals and Agriculture on the 30 September data (Petroleum +0.84 and +0.89; Metals -0.05 and +0.07; Precious Metals -0.22 and -0.28; Agriculture -0.19 and -0.20). The NGL bullet and the Skewness bullet carry a note where they use v5-basis figures, and the Energy-NGL, cross-commodity and diversification bullets are unchanged and marked as v5 basis",
     "Recomputed"],
    ["v5: subtitle 'Metals, Energy, ...' and basis paragraph 'Value starts after 504 observations of F3'",
     "Subtitle names Petroleum; the basis paragraph states the end dates (30 September for the four updated classes, 23 September for the rest) and the Value contract (F3, F2 for Precious Metals and Agriculture)",
     "Consistency fix"],
]
last = tb.rows[-1]._tr
for row in ROWS:
    tr = copy.deepcopy(last); tb._tbl.append(tr)
    r = _Row(tr, tb)
    for c, t in zip(r.cells, row):
        set_text(c.paragraphs[0], t)
d.save(F)
print("log added")
