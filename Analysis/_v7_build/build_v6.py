import sys, os, copy, re, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docx
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table
from docx.shared import Pt
from text_metals import metals
from text_petroleum import petroleum
from facts3 import *

SRC = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia\Analysis\Risk Premia Analysis v5_2012.docx"
OUT = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia\Analysis\Risk Premia Analysis v6_Metals and Petroleum_2012.docx"
IMG = os.path.join(S, "img")
if os.path.exists(OUT):
    sys.exit("refusing to overwrite " + OUT)
d = docx.Document(SRC)
body = d.element.body
els = list(body.iterchildren())


def P(el): return Paragraph(el, d)
def is_p(el): return el.tag == qn("w:p")
def is_tbl(el): return el.tag == qn("w:tbl")
def ptext(el): return P(el).text


def set_text(p, text):
    rs = p.runs
    rs[0].text = text
    for r in rs[1:]:
        r._r.getparent().remove(r._r)


def find_p(prefix, start=0, style=None):
    for i in range(start, len(els)):
        if is_p(els[i]) and ptext(els[i]).startswith(prefix) and (style is None or P(els[i]).style.name == style):
            return i
    raise KeyError(prefix)


def set_bullets(i0, i1, texts):
    bullets = [e for e in els[i0 + 1:i1] if is_p(e) and P(e).style.name == "List Bullet"]
    while len(bullets) < len(texts):
        c = copy.deepcopy(bullets[-1]); bullets[-1].addnext(c); bullets.append(c)
    for e in bullets[len(texts):]:
        e.getparent().remove(e)
    for e, t in zip(bullets, texts):
        set_text(P(e), t)


# ---------------- section text
im = find_p("Metals", style="Heading 2"); ie = find_p("Energy", im + 1, "Heading 2"); ip = find_p("Precious Metals", ie + 1, "Heading 2")
set_bullets(im, ie, [b[1] for b in metals() if b[0] == "b"])
set_bullets(ie, ip, [b[1] for b in petroleum() if b[0] == "b"])
set_text(P(els[ie]), "Petroleum")
set_text(P(els[find_p("Figure 2. Energy")]), "Figure 2. Petroleum: Combined Strategy Performance (Cumulative Return, 2012-2026)")


# ---------------- images
def swap_image(caption_prefix, fname):
    ci = find_p(caption_prefix)
    blip = els[ci - 1].findall(".//" + qn("a:blip"))[0]
    part = d.part.related_parts[blip.get(qn("r:embed"))]
    part._blob = open(os.path.join(IMG, fname), "rb").read()


K = ["Momentum", "Carry", "CarryMom", "Value", "Skewness"]
KN = {"Momentum": "Momentum", "Carry": "Carry", "CarryMom": "Carry-Momentum", "Value": "Value", "Skewness": "Skewness"}
swap_image("Figure 1. Metals", "fig_metals_combined.png")
swap_image("Figure 2. Petroleum", "fig_petroleum_combined.png")
for n, k in enumerate(K):
    swap_image(f"Figure A{1+n}. Metals, {KN[k]}", f"figA_metals_{k}.png")
    swap_image(f"Figure A{6+n}. Energy, {KN[k]}", f"figA_petroleum_{k}.png")
    set_text(P(els[find_p(f"Figure A{6+n}. Energy")]), f"Figure A{6+n}. Petroleum, {KN[k]}: Equity Curve by Product (2012-2026)")
for e in els:
    if is_p(e) and P(e).style.name == "Heading 3" and ptext(e) == "Energy":
        set_text(P(e), "Petroleum")


# ---------------- tables
def cell_set(c, text):
    p = c.paragraphs[0]
    if p.runs: set_text(p, text)
    else: p.add_run(text)


def table_after_caption(prefix):
    ci = find_p(prefix); t = els[ci + 1]; assert is_tbl(t), prefix
    return ci, Table(t, d)


W4 = [("Full", "full"), ("2012-16", "p1"), ("2017-21", "p2"), ("2022-26", "p3")]


def fill_period(tb, v, keys):
    for r, k in zip(tb.rows[1:], keys):
        for c, (_, w) in zip(r.cells[1:], W4):
            cell_set(c, I(st(v, k, w)["ir"]))


def fill_prod(tb, v):
    a, prods = VARIANTS[v]
    for r, k in zip(tb.rows[1:], K):
        for c, p in zip(r.cells[1:], prods):
            cell_set(c, I(pst(a, p, k)["ir"]))


def labels(tb): return [r.cells[0].text for r in tb.rows[1:]]


SLN = ["Momentum", "Carry", "Carry-Momentum", "Value", "Skewness"]
ci, t = table_after_caption("Table A1. Metals"); assert labels(t) == SLN; fill_period(t, "metals", SLEEVES)
ci, t = table_after_caption("Table A2. Metals"); assert labels(t) == ["Equal Weight", "Inverse Vol"]; fill_period(t, "metals", ["EW PORT", "Inverse Vol"])
ci, t = table_after_caption("Table A3. Metals"); assert [c.text for c in t.rows[0].cells[1:]] == ["Copper", "Aluminium", "Lead", "Zinc"]; fill_prod(t, "metals")
ci, t = table_after_caption("Table A4. Energy"); assert labels(t) == SLN; fill_period(t, "petroleum", SLEEVES)
set_text(P(els[ci]), "Table A4. Petroleum: Strategy Information Ratios by Period")
ci, t = table_after_caption("Table A5. Energy"); assert labels(t) == ["Equal Weight", "Inverse Vol"]; fill_period(t, "petroleum", ["EW PORT", "Inverse Vol"])
set_text(P(els[ci]), "Table A5. Petroleum: Portfolio Construction Information Ratios by Period")
ci, t = table_after_caption("Table A6. Energy")
assert [c.text for c in t.rows[0].cells[1:]] == ["WTI", "Brent", "RBOB", "Heating Oil", "Natural Gas"]
for r in t.rows:
    r._tr.remove(r.cells[5]._tc)
grid = t._tbl.find(qn("w:tblGrid")); grid.remove(grid.findall(qn("w:gridCol"))[-1])
fill_prod(t, "petroleum")
set_text(P(els[ci]), "Table A6. Petroleum: Individual-Product Information Ratios, All Strategies (Full Sample)")
# remove A7 (Energy ex-NatGas): caption, table, spacer
ci7 = find_p("Table A7. Energy ex-NatGas")
assert is_tbl(els[ci7 + 1]) and is_p(els[ci7 + 2]) and ptext(els[ci7 + 2]).strip() == ""
for e in (els[ci7], els[ci7 + 1], els[ci7 + 2]):
    e.getparent().remove(e)
# renumber captions A8..A26 -> A7..A25
for e in els:
    if is_p(e) and e.getparent() is body:
        m = re.match(r"Table A(\d+)\. ", ptext(e))
        if m and int(m.group(1)) >= 8:
            set_text(P(e), re.sub(r"^Table A\d+", f"Table A{int(m.group(1)) - 1}", ptext(e), 1))

PN = {"HeatingOil": "Heating Oil", "NatGas": "Natural Gas", "SoybeanOil": "Soybean Oil"}


def rowmap(tb): return {r.cells[0].text: r for r in tb.rows}


ci, t23 = table_after_caption("Table A23. Skewness: Share of Days")
rm = rowmap(t23)
for p in VARIANTS["metals"][1]:
    lg_ = legs("metals", p)["full"]
    for c, x in zip(rm[f"Metals: {p}"].cells[1:], [U(lg_["long_pct"], 0) + "%", N(lg_["long_pnl"]), N(lg_["short_pnl"]), I(pst("metals", p, "Skewness")["ir"])]):
        cell_set(c, x)
for p in VARIANTS["petroleum"][1]:
    lg_ = legs("energy", p)["full"]; r = rm[f"Energy: {PN.get(p, p)}"]
    cell_set(r.cells[0], f"Petroleum: {PN.get(p, p)}")
    for c, x in zip(r.cells[1:], [U(lg_["long_pct"], 0) + "%", N(lg_["long_pnl"]), N(lg_["short_pnl"]), I(pst("energy", p, "Skewness")["ir"])]):
        cell_set(c, x)
rm["Energy: Natural Gas"]._tr.getparent().remove(rm["Energy: Natural Gas"]._tr)


def four_five(v): return [I(st4(v, "EW PORT")["ir"]), I(st(v, "EW PORT")["ir"]), I(st4(v, "Inverse Vol")["ir"]), I(st(v, "Inverse Vol")["ir"])]


ci, t24 = table_after_caption("Table A24. Effect of Adding Skewness")
rm = rowmap(t24)
for c, x in zip(rm["Metals"].cells[1:], four_five("metals")): cell_set(c, x)
cell_set(rm["Energy"].cells[0], "Petroleum")
for c, x in zip(rm["Energy"].cells[1:], four_five("petroleum")): cell_set(c, x)
rm["Energy ex-NatGas"]._tr.getparent().remove(rm["Energy ex-NatGas"]._tr)


def corrrow(v):
    c = corr_within(v); return [N(c.loc["Skewness", k]) for k in ("Momentum", "Carry", "CarryMom", "Value", "EW PORT")]


ci, t25 = table_after_caption("Table A25. Skewness: Correlation")
rm = rowmap(t25)
for c, x in zip(rm["Metals"].cells[1:], corrrow("metals")): cell_set(c, x)
cell_set(rm["Energy"].cells[0], "Petroleum")
for c, x in zip(rm["Energy"].cells[1:], corrrow("petroleum")): cell_set(c, x)
rm["Energy ex-NatGas"]._tr.getparent().remove(rm["Energy ex-NatGas"]._tr)

NOTE = {"A23": "Note: the Metals and Petroleum rows are measured to 30 September 2026; the other rows are still measured to 23 September 2026.",
        "A24": "Note: the Metals and Petroleum rows are measured to 30 September 2026; the other rows, including both cross-commodity rows (which still include Natural Gas in Energy), are still measured to 23 September 2026.",
        "A25": "Note: the Metals and Petroleum rows are measured to 30 September 2026; the other rows are still measured to 23 September 2026."}
for key, tb in (("A23", t23), ("A24", t24), ("A25", t25)):
    sp = tb._tbl.getnext(); assert is_p(sp) and ptext(sp).strip() == ""
    note = copy.deepcopy(sp); sp.addnext(note)
    r = P(note).add_run(NOTE[key]); r.italic = True; r.font.size = Pt(9)

# ---------------- version note after the basis paragraph
bi = find_p("Basis of all results")
note = copy.deepcopy(els[bi]); els[bi].addnext(note)
set_text(P(note),
         "Version note (v6, 1 November 2026). Only the Metals and Petroleum sections have been updated in this version, together with Figures 1, 2 and A1 to A10, Tables A1 to A6 and the Metals and Petroleum rows of Tables A23 to A25. "
         "They use the data to 30 September 2026 (five further trading days than the rest of the document) and the current bucket definition: Petroleum is WTI, Brent, RBOB and Heating Oil, and Natural Gas has moved to the Power, Emissions and Nat Gas bucket, so there is no Energy ex-NatGas table any more. "
         "Everything else (the basis paragraph above, the Key Findings, the Precious Metals, NGL and Agriculture sections, Correlation Analysis, the Cross-Commodity Portfolio, the remaining tables and charts) is unchanged from v5, still ends on 23 September 2026 and still treats Energy as five products including Natural Gas, "
         "so the Key Findings and the cross-commodity figures that quote Metals or Energy numbers do not yet match the updated sections.")

d.save(OUT)
print("saved", OUT)
