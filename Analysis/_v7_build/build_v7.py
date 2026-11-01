"""Build Risk Premia Analysis v7 from the v6 file: Precious Metals and Agriculture rewritten on the 30 September 2026 data (Value on F2, Dimil Patel's 1 November change),
appendix tables of Metals, Petroleum, Precious Metals and Agriculture refreshed, Key Findings updated for those four classes, all charts redrawn as a return index starting at 100%."""
import sys, os, copy, re, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docx
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table, _Row
from docx.shared import Pt
from text_precious import precious
from text_agri import agri
from text_front_v7 import key_findings
from facts3 import *

SRC = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia\Analysis\Risk Premia Analysis v6_Metals and Petroleum_2012.docx"
OUT = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia\Analysis\Risk Premia Analysis v7_2012.docx"
IMG, IMGO = os.path.join(S, "img"), os.path.join(S, "img_old")
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
    assert len(bullets) == len(texts), (ptext(els[i0]), len(bullets), len(texts))
    for e, t in zip(bullets, texts):
        set_text(P(e), t)


def cell_set(c, text):
    p = c.paragraphs[0]
    if p.runs: set_text(p, text)
    else: p.add_run(text)


def table_after_caption(prefix):
    ci = find_p(prefix); t = els[ci + 1]; assert is_tbl(t), prefix
    return ci, Table(t, d)


def labels(tb): return [r.cells[0].text for r in tb.rows[1:]]
def rowmap(tb): return {r.cells[0].text: r for r in tb.rows}


# ---------------------------------------------------------------- NGL figures as printed in the unchanged v6 NGL section (used in Key Findings)
_, t_ngl = table_after_caption("Table A11. NGL: Strategy")
_, t_ngl_p = table_after_caption("Table A12. NGL: Portfolio")
nm = rowmap(t_ngl); npf = rowmap(t_ngl_p)
NGL = dict(ew=npf["Equal Weight"].cells[1].text, iv=npf["Inverse Vol"].cells[1].text, value=nm["Value"].cells[1].text, skew=nm["Skewness"].cells[1].text,
           value_p1=nm["Value"].cells[2].text, skew_p1=nm["Skewness"].cells[2].text, skew_p2=nm["Skewness"].cells[3].text)
assert NGL == dict(ew="+1.25", iv="+1.16", value="+0.08", skew="+0.06", value_p1="-0.41", skew_p1="-0.89", skew_p2="+0.93"), NGL

# ---------------------------------------------------------------- Key Findings
ik = find_p("Key Findings", style="Heading 2"); im = find_p("Metals", ik + 1, "Heading 2")
old_kf = [ptext(e) for e in els[ik + 1:im] if is_p(e) and P(e).style.name == "List Bullet"]
assert len(old_kf) == 8
new_kf = key_findings(old_kf, NGL)
set_bullets(ik, im, new_kf)

# ---------------------------------------------------------------- Precious Metals and Agriculture sections
ip = find_p("Precious Metals", im + 1, "Heading 2"); ing = find_p("NGL", ip + 1, "Heading 2"); iag = find_p("Agriculture", ing + 1, "Heading 2"); ic = find_p("Correlation Analysis", iag + 1, "Heading 2")
set_bullets(ip, ing, [b[1] for b in precious() if b[0] == "b"])
set_bullets(iag, ic, [b[1] for b in agri() if b[0] == "b"])

# ---------------------------------------------------------------- images: every figure redrawn (index in %, start 100%)
K = ["Momentum", "Carry", "CarryMom", "Value", "Skewness"]
KN = {"Momentum": "Momentum", "Carry": "Carry", "CarryMom": "Carry-Momentum", "Value": "Value", "Skewness": "Skewness"}


def swap_image(caption_prefix, path):
    ci = find_p(caption_prefix)
    blip = els[ci - 1].findall(".//" + qn("a:blip"))[0]
    part = d.part.related_parts[blip.get(qn("r:embed"))]
    part._blob = open(path, "rb").read()


MAIN = {1: ("Metals", "metals"), 2: ("Petroleum", "petroleum"), 3: ("Precious Metals", "precious"), 4: ("NGL", "ngl"), 5: ("Agriculture", "agri")}
for n, (nm_, key) in MAIN.items():
    swap_image(f"Figure {n}. {nm_}", os.path.join(IMGO if key == "ngl" else IMG, f"fig_{key}_combined.png"))
swap_image("Figure 6. Cross-Commodity", os.path.join(IMGO, "fig_cross_combined.png"))
for ci_, (nm_, key) in enumerate([("Metals", "metals"), ("Petroleum", "petroleum"), ("Precious Metals", "precious"), ("NGL", "ngl"), ("Agriculture", "agri")]):
    for j, k in enumerate(K):
        swap_image(f"Figure A{ci_ * 5 + j + 1}. {nm_}, {KN[k]}", os.path.join(IMGO if key == "ngl" else IMG, f"figA_{key}_{k}.png"))
swap_image("Figure A26.", os.path.join(IMGO, "figA_pairs_EW.png"))
swap_image("Figure A27.", os.path.join(IMGO, "figA_pairs_IV.png"))

# ---------------------------------------------------------------- appendix tables
W4 = [("Full", "full"), ("2012-16", "p1"), ("2017-21", "p2"), ("2022-26", "p3")]
SLN = ["Momentum", "Carry", "Carry-Momentum", "Value", "Skewness"]


def fill_period(tb, v, keys):
    for r, k in zip(tb.rows[1:], keys):
        for c, (_, w) in zip(r.cells[1:], W4):
            cell_set(c, I(st(v, k, w)["ir"]))


def fill_prod(tb, v):
    a, prods = VARIANTS[v]
    for r, k in zip(tb.rows[1:], K):
        for c, p in zip(r.cells[1:], prods):
            cell_set(c, I(pst(a, p, k)["ir"]))


for n0, nm_, v in ((7, "Precious Metals", "precious"), (14, "Agriculture", "agri")):
    ci, t = table_after_caption(f"Table A{n0}. {nm_}: Strategy"); assert labels(t) == SLN; fill_period(t, v, SLEEVES)
    ci, t = table_after_caption(f"Table A{n0+1}. {nm_}: Portfolio"); assert labels(t) == ["Equal Weight", "Inverse Vol"]; fill_period(t, v, ["EW PORT", "Inverse Vol"])
for pre, v, hdr in (("Table A9. Precious Metals", "precious", ["Gold", "Silver", "Platinum", "Palladium"]), ("Table A16. Agriculture", "agri", ["Corn", "Wheat", "Soybean", "Soybean Oil", "Coffee", "Sugar"])):
    ci, t = table_after_caption(pre + ": Individual"); assert [c.text for c in t.rows[0].cells[1:]] == hdr; fill_prod(t, v)
# tenor-pair tables
ci, t = table_after_caption("Table A10. Precious Metals: Carry Tenor Pairs"); tt = tenor_table("precious")
assert labels(t) == ["Carry", "Carry-Momentum"]
for r, key in zip(t.rows[1:], ("Carry", "CarryMom")):
    for c, k in zip(r.cells[1:], ("prev", "short", "long", "two")): cell_set(c, I(tt[key][k]))
ci, t = table_after_caption("Table A17. Agriculture: Carry Tenor Pairs"); tt = tenor_table("agri")
for r, key in zip(t.rows[1:], ("Carry", "CarryMom")):
    for c, k in zip(r.cells[1:], ("prev", "long", "two")): cell_set(c, I(tt[key][k]))

# A23: Skewness legs
PN = {"HeatingOil": "Heating Oil", "NatGas": "Natural Gas", "SoybeanOil": "Soybean Oil"}
ci, t23 = table_after_caption("Table A23. Skewness: Share of Days"); rm = rowmap(t23)
for cls, a, v, prods in (("Metals", "metals", "metals", VARIANTS["metals"][1]), ("Petroleum", "energy", "petroleum", VARIANTS["petroleum"][1]),
                         ("Precious Metals", "precious", "precious", VARIANTS["precious"][1]), ("Agriculture", "agri", "agri", VARIANTS["agri"][1])):
    for p in prods:
        lg_ = legs(a, p)["full"]; r = rm[f"{cls}: {PN.get(p, p)}"]
        for c, x in zip(r.cells[1:], [U(lg_["long_pct"], 0) + "%", N(lg_["long_pnl"]), N(lg_["short_pnl"]), I(pst(a, p, "Skewness")["ir"])]): cell_set(c, x)


def four_five(v): return [I(st4(v, "EW PORT")["ir"]), I(st(v, "EW PORT")["ir"]), I(st4(v, "Inverse Vol")["ir"]), I(st(v, "Inverse Vol")["ir"])]


ci, t24 = table_after_caption("Table A24. Effect of Adding Skewness"); rm = rowmap(t24)
for lbl, v in (("Metals", "metals"), ("Petroleum", "petroleum"), ("Precious Metals", "precious"), ("Agriculture", "agri")):
    for c, x in zip(rm[lbl].cells[1:], four_five(v)): cell_set(c, x)


def corrrow(v):
    c = corr_within(v); return [N(c.loc["Skewness", k]) for k in ("Momentum", "Carry", "CarryMom", "Value", "EW PORT")]


ci, t25 = table_after_caption("Table A25. Skewness: Correlation"); rm = rowmap(t25)
for lbl, v in (("Metals", "metals"), ("Petroleum", "petroleum"), ("Precious Metals", "precious"), ("Agriculture", "agri")):
    for c, x in zip(rm[lbl].cells[1:], corrrow(v)): cell_set(c, x)

# table notes
for key, tb in (("A23", t23), ("A24", t24), ("A25", t25)):
    nxt = tb._tbl.getnext().getnext(); assert is_p(nxt) and ptext(nxt).startswith("Note:")
    extra = " The two cross-commodity rows (which still include Natural Gas in Energy) are also on that earlier basis." if key == "A24" else ""
    set_text(P(nxt), "Note: the Metals, Petroleum, Precious Metals and Agriculture rows are measured to 30 September 2026; the NGL row" + ("s" if key == "A23" else "") + " ("
             + ("NGL products" if key == "A23" else "NGL") + ") is still measured to 23 September 2026." + extra)

# ---------------------------------------------------------------- front matter
set_text(P(els[find_p("Metals, Energy, Precious Metals, NGL")]), "Metals, Petroleum, Precious Metals, NGL, Agriculture, Correlation Analysis, and Cross-Commodity Portfolio")
bi = find_p("Basis of all results"); bt = ptext(els[bi])
a = "except that Value starts after 504 observations of F3 (two years), so that NGL Value is live before 2012."
assert a in bt
bt = bt.replace(a, "except that Value starts after 504 observations of the Value contract (two years), so that NGL Value is live before 2012; the Value contract is F3, except F2 for Precious Metals and Agriculture (changed on 1 November 2026).")
a = "1 January 2012 to 23 September 2026."
assert a in bt
bt = bt.replace(a, "1 January 2012 to 30 September 2026 for Metals, Petroleum, Precious Metals and Agriculture (the sections updated in v7) and to 23 September 2026 for everything else (see the version note).")
set_text(P(els[bi]), bt)
vi = find_p("Version note (v6")
set_text(P(els[vi]),
         "Version note (v7, 1 November 2026). Updated in this version: the Metals, Petroleum, Precious Metals and Agriculture sections and the Key Findings that concern them, Figures 1 to 3, 5 and A1 to A15, A21 to A25, "
         "Tables A1 to A10 and A14 to A17, and the Metals, Petroleum, Precious Metals and Agriculture rows of Tables A23 to A25. They use data to 30 September 2026 (five further trading days than v5) and the current bucket definitions: "
         "Petroleum is WTI, Brent, RBOB and Heating Oil (Natural Gas has moved to the Power, Emissions and Nat Gas bucket, so there is no Energy ex-NatGas table), and Value is measured on the F2 contract for Precious Metals and Agriculture (F3 before 1 November 2026). "
         "Not updated, and still on the v5 basis (data to 23 September 2026, Energy as five products including Natural Gas): the NGL section and its tables and figures, the Correlation Analysis, the Cross-Commodity Portfolio, Tables A18 to A22, and the Key Findings bullets about NGL figures, the Energy-NGL pair and the cross-commodity book, which are marked as such. "
         "All figures in the document are redrawn as a cumulative return index starting at 100%; the unchanged sections' charts show the same data as in v5.")

d.save(OUT)
print("saved", OUT)
