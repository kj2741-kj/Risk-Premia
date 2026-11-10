"""Build Risk Premia Analysis v8 from the v7 file: all six buckets on the 30 September 2026 data. New Gas and Emissions section (Henry Hub, TTF, UK Gas, EUA), NGL with Naphtha,
Correlation Analysis and Cross-Commodity Portfolio on six buckets (fifteen pairs), Key Findings, liquidity table with UK Gas and Naphtha, appendix tables and figures, caption renumbering.
Refuses to overwrite an existing output file."""
import sys, os, copy, re, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docx
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table
from docx.shared import Emu
from text_gasem import gasem
from text_ngl8 import ngl8
from text_cross8 import corr8, cross8, _c
from text_front8 import key_findings, liquidity_paragraph
from text_power import power
from text_agri import agri, agri_narr
from text_softs import softs, softs_narr
from facts_tenor import bucket_tenor_table
from power_facts import *
from facts3 import *
B_POWER, KEY_POWER = power()

SRC = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia\Analysis\Risk Premia Analysis v7_2012.docx"
OUT = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia\Analysis\Risk Premia Analysis v8_2012.docx"
IMG = os.path.join(S, "img8")
if os.path.exists(OUT):
    sys.exit("refusing to overwrite " + OUT)
d = docx.Document(SRC)
body = d.element.body


def E(): return list(body.iterchildren())
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
    els = E()
    for i in range(start, len(els)):
        if is_p(els[i]) and ptext(els[i]).startswith(prefix) and (style is None or P(els[i]).style.name == style):
            return i
    raise KeyError(prefix)


def cell_set(c, text):
    p = c.paragraphs[0]
    if p.runs: set_text(p, text)
    else: p.add_run(text)


def tbl_after(prefix):
    els = E(); ci = find_p(prefix); t = els[ci + 1]; assert is_tbl(t), prefix
    return ci, Table(t, d)


def labels(tb): return [r.cells[0].text for r in tb.rows[1:]]


def bullets_after(head_el):
    out = []; e = head_el.getnext()
    while e is not None and is_p(e) and P(e).style.name == "List Bullet":
        out.append(e); e = e.getnext()
    return out


def set_bullets_run(head_el, texts):
    """Set the contiguous bullet run right after head_el to `texts`, cloning or removing bullets as needed."""
    bl = bullets_after(head_el); assert bl, ptext(head_el)
    while len(bl) < len(texts):
        n = copy.deepcopy(bl[-1]); bl[-1].addnext(n); bl.append(n)
    for e in bl[len(texts):]:
        e.getparent().remove(e)
    for e, t in zip(bl, texts):
        set_text(P(e), t)
    return bl[:len(texts)]


def make_figure_para(template_el, img_path):
    n = copy.deepcopy(template_el)
    cx = n.findall(".//" + qn("wp:extent"))[0].get("cx")
    for r in n.findall(qn("w:r")): n.remove(r)
    p = Paragraph(n, d); r = p.add_run(); r.add_picture(img_path, width=Emu(int(cx)))
    return n


def swap_image(caption_prefix, path):
    ci = find_p(caption_prefix)
    blip = E()[ci - 1].findall(".//" + qn("a:blip"))[0]
    part = d.part.related_parts[blip.get(qn("r:embed"))]
    part._blob = open(path, "rb").read()


def rebuild_table(tb, rows_data, tmpl_idx=1, tmpl_rows=None):
    """Keep the header row(s), replace the body by deep copies of template rows filled with rows_data (list of lists)."""
    rows = list(tb._tbl.findall(qn("w:tr")))
    tmpl = tmpl_rows if tmpl_rows is not None else [copy.deepcopy(rows[min(tmpl_idx, len(rows) - 1)])]
    for r in rows[1:]: tb._tbl.remove(r)
    for k, data in enumerate(rows_data):
        r = copy.deepcopy(tmpl[min(k, len(tmpl) - 1)])
        tb._tbl.append(r)
        row = tb.rows[-1]
        for c, x in zip(row.cells, data): cell_set(c, x)


def delete_column(tb, idx):
    tbl = tb._tbl; grid = tbl.tblGrid; cols = grid.findall(qn("w:gridCol")); total = sum(int(c.get(qn("w:w"))) for c in cols)
    grid.remove(cols[idx]); cols = grid.findall(qn("w:gridCol")); n = len(cols)
    first = int(cols[0].get(qn("w:w"))); other = (total - first) // (n - 1)
    for c in cols[1:]: c.set(qn("w:w"), str(other))
    for tr in tbl.findall(qn("w:tr")):
        tcs = tr.findall(qn("w:tc")); tr.remove(tcs[idx])
        for t in tr.findall(qn("w:tc"))[1:]:
            pr = t.find(qn("w:tcPr")); w = pr.find(qn("w:tcW")) if pr is not None else None
            if w is not None: w.set(qn("w:w"), str(other)); w.set(qn("w:type"), "dxa")


def add_column(tb, header, values):
    tbl = tb._tbl; grid = tbl.tblGrid; cols = grid.findall(qn("w:gridCol")); total = sum(int(c.get(qn("w:w"))) for c in cols)
    grid.append(copy.deepcopy(cols[-1])); cols = grid.findall(qn("w:gridCol")); n = len(cols)
    first = int(cols[0].get(qn("w:w"))); other = (total - first) // (n - 1)
    for c in cols[1:]: c.set(qn("w:w"), str(other))
    for ri, tr in enumerate(tbl.findall(qn("w:tr"))):
        tcs = tr.findall(qn("w:tc")); tc = copy.deepcopy(tcs[-1]); tcs[-1].addnext(tc)
        for t in tr.findall(qn("w:tc"))[1:]:
            pr = t.find(qn("w:tcPr")); w = pr.find(qn("w:tcW")) if pr is not None else None
            if w is not None: w.set(qn("w:w"), str(other)); w.set(qn("w:type"), "dxa")
    tb2 = Table(tbl, d)
    for ri, row in enumerate(tb2.rows):
        cell_set(row.cells[-1], header if ri == 0 else values[ri - 1])


# ----------------------------------------------------------------------------------------------------------------------------- numbers
K = ["Momentum", "Carry", "CarryMom", "Value", "Skewness"]
KN = {"Momentum": "Momentum", "Carry": "Carry", "CarryMom": "Carry-Momentum", "Value": "Value", "Skewness": "Skewness"}
W4 = [("Full", "full"), ("2012-16", "p1"), ("2017-21", "p2"), ("2022-26", "p3")]
SLN = ["Momentum", "Carry", "Carry-Momentum", "Value", "Skewness"]
PNM = {"HeatingOil": "Heating Oil", "NatGas": "Henry Hub", "SoybeanOil": "Soybean Oil", "UKGas": "UK Gas", "EUA": "EUA", "LiveCattle": "Live Cattle", "NatGasoline": "Natural Gasoline"}
BS, BS4 = bystyle(), bystyle4()
CB = combined_book()

els = E()
# ----------------------------------------------------------------------------------------------------------------------------- images of the existing figures (old numbering)
OLDMAIN = {1: ("Metals", "metals"), 2: ("Petroleum", "petroleum"), 3: ("Precious Metals", "precious"), 4: ("NGL", "ngl"), 5: ("Agriculture", "agri")}
for n, (nm_, key) in OLDMAIN.items():
    swap_image(f"Figure {n}. {nm_}", os.path.join(IMG, f"fig_{key}_combined.png"))
swap_image("Figure 6. Cross-Commodity", os.path.join(IMG, "fig_cross_combined.png"))
for ci_, (nm_, key) in enumerate([("Metals", "metals"), ("Petroleum", "petroleum"), ("Precious Metals", "precious"), ("NGL", "ngl"), ("Agriculture", "agri")]):
    for j, k in enumerate(K):
        swap_image(f"Figure A{ci_ * 5 + j + 1}. {nm_}, {KN[k]}", os.path.join(IMG, f"figA_{key}_{k}.png"))
swap_image("Figure A26.", os.path.join(IMG, "figA_pairs_EW.png"))
swap_image("Figure A27.", os.path.join(IMG, "figA_pairs_IV.png"))

# ----------------------------------------------------------------------------------------------------------------------------- appendix tables of existing buckets (old numbering): NGL
def st_cells(v, keys): return [[I(st(v, k, w)["ir"]) for _, w in W4] for k in keys]
_, t11 = tbl_after("Table A11. NGL: Strategy"); assert labels(t11) == SLN
for r, vals in zip(t11.rows[1:], st_cells("ngl", SLEEVES)):
    for c, x in zip(r.cells[1:], vals): cell_set(c, x)
_, t12 = tbl_after("Table A12. NGL: Portfolio"); assert labels(t12) == ["Equal Weight", "Inverse Vol"]
for r, vals in zip(t12.rows[1:], st_cells("ngl", ["EW PORT", "Inverse Vol"])):
    for c, x in zip(r.cells[1:], vals): cell_set(c, x)
_, t13 = tbl_after("Table A13. NGL: Individual-Product"); assert [c.text for c in t13.rows[0].cells[1:]] == ["Ethane", "Propane", "Butane", "Isobutane"]
delete_column(t13, 4)      # Isobutane is removed from every output (2026-11-09)
add_column(t13, "Naphtha", [""] * 5)
add_column(t13, "Natural Gasoline", [""] * 5)
for r, k in zip(t13.rows[1:], K):
    for c, (a, p) in zip(r.cells[1:], MEMBERS["ngl"]): cell_set(c, I(pst(a, p, k)["ir"]))

# ----------------------------------------------------------------------------------------------------------------------------- Cross-commodity appendix tables (A18 to A25, old numbering)
# ---- Agriculture (four products) and Softs (new) appendix tables; the carry tenor-pair table A17 is not reproduced (the pairs were fixed by decision on 10 November 2026)
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
TEN_HDR = ["", "Short pair alone (F1-F2)", "Long pair alone", "Two-pair sum"]


def fill_tenor(tb, bucket):
    res_, _, _ = bucket_tenor_table(bucket)
    assert [c.text for c in tb.rows[0].cells] in (["", "Previous single pair (F1-F2)", "Long pair alone", "Two-pair sum"], TEN_HDR), [c.text for c in tb.rows[0].cells]
    for c, x in zip(tb.rows[0].cells, TEN_HDR): cell_set(c, x)
    assert labels(tb) == ["Carry", "Carry-Momentum"]
    for r, sl_ in zip(tb.rows[1:], ("Carry", "CarryMom")):
        for c, nm_ in zip(r.cells[1:], ("short", "long", "two")): cell_set(c, I(res_[sl_][nm_]["ir"]))


_, t17 = tbl_after("Table A17. Agriculture: Carry Tenor Pairs"); fill_tenor(t17, "agri")
set_text(P(E()[find_p("Table A17. Agriculture: Carry Tenor Pairs")]), "Table A17. Agriculture: Carry Tenor Pairs, Full-Sample Information Ratios (long pair F1-F6 for Corn and Wheat, F1-F7 for Soybean and Live Cattle)")
els = E(); i17_ = find_p("Table A17. Agriculture: Carry Tenor Pairs"); assert is_tbl(els[i17_ + 1])
els = E(); i14_ = find_p("Table A14. Agriculture: Strategy"); i16_ = find_p("Table A16. Agriculture: Individual-Product")
blk_a = els[i14_:i17_ + 3]; assert len(blk_a) == 12 and [is_tbl(e) for e in blk_a] == [False, True, False] * 4
anchor = blk_a[-1]; softs_tbl = []
for e in blk_a:
    n_ = copy.deepcopy(e); anchor.addnext(n_); anchor = n_; softs_tbl.append(n_)
SOFTS_TABLE_ANCHOR = softs_tbl[-1]
set_text(P(softs_tbl[0]), "Table A?. Softs: Strategy Information Ratios by Period")
set_text(P(softs_tbl[3]), "Table A?. Softs: Portfolio Construction Information Ratios by Period")
set_text(P(softs_tbl[6]), "Table A?. Softs: Individual-Product Information Ratios, All Strategies (Full Sample)")
set_text(P(softs_tbl[9]), "Table A?. Softs: Carry Tenor Pairs, Full-Sample Information Ratios (long pair F1-F6 for all four products)")
fill_tenor(Table(softs_tbl[10], d), "softs")
sa_, sb_, sc_ = Table(softs_tbl[1], d), Table(softs_tbl[4], d), Table(softs_tbl[7], d)
for r, vals in zip(sa_.rows[1:], st_cells("softs", SLEEVES)):
    for c, x in zip(r.cells[1:], vals): cell_set(c, x)
for r, vals in zip(sb_.rows[1:], st_cells("softs", ["EW PORT", "Inverse Vol"])):
    for c, x in zip(r.cells[1:], vals): cell_set(c, x)
for c, (a, p) in zip(sc_.rows[0].cells[1:], MEMBERS["softs"]): cell_set(c, PNM.get(p, p))
for r, k in zip(sc_.rows[1:], K):
    for c, (a, p) in zip(r.cells[1:], MEMBERS["softs"]): cell_set(c, I(pst(a, p, k)["ir"]))

# ----------------------------------------------------------------------------------------------------------------------------- Cross-commodity appendix tables below
_, t18 = tbl_after("Table A18."); BC = {k: bench_corr(BS[k]) for k in SLEEVES + ["EW PORT", "Inverse Vol"]}
BCOL = ["Equity", "Fixed Income", "Commodity Index", "Gold", "60/40 Portfolio"]
rebuild_table(t18, [[lab] + [N(BC[k][c]) for c in BCOL] for lab, k in [("Momentum", "Momentum"), ("Carry", "Carry"), ("Carry-Momentum", "CarryMom"), ("Value", "Value"), ("Skewness", "Skewness"), ("EW Portfolio", "EW PORT"), ("Inverse Vol", "Inverse Vol")]])
set_text(P(E()[find_p("Table A18.")]), "Table A18. Cross-Commodity Portfolio: Correlation vs Traditional Assets (2012 to 30 September 2026)")
_, t19 = tbl_after("Table A19."); assert labels(t19) == SLN
for r, k in zip(t19.rows[1:], SLEEVES):
    for c, (_, w) in zip(r.cells[1:], W4): cell_set(c, I(stats(BS[k], w)["ir"]))
set_text(P(E()[find_p("Table A19.")]), "Table A19. Cross-Commodity Portfolio: Strategy Information Ratios by Period (all seven buckets)")
_, t20 = tbl_after("Table A20.")
rows20 = [("Equal Weight", BS["EW PORT"]), ("Inverse Vol", BS["Inverse Vol"]), ("Equal Weight (without Skewness)", BS4["EW PORT"]), ("Inverse Vol (without Skewness)", BS4["Inverse Vol"])]
rebuild_table(t20, [[lab] + [I(stats(s, w)["ir"]) for _, w in W4] for lab, s in rows20])
set_text(P(E()[find_p("Table A20.")]), "Table A20. Cross-Commodity Portfolio: Construction Information Ratios by Period (all seven buckets)")
_, t21 = tbl_after("Table A21.")
ps_all = pair_stats()
rebuild_table(t21, [[p["name"], I(p["ew"]["ir"]), I(p["iv"]["ir"])] for p in ps_all])
set_text(P(E()[find_p("Table A21.")]), "Table A21. Cross-Pair Portfolio: Full-Sample Information Ratios, All Twenty-One Bucket Pairs")
# A22 (Energy pairs ex-NatGas) is removed: caption, table, trailing blank
els = E(); i22 = find_p("Table A22."); assert is_tbl(els[i22 + 1])
for e in els[i22:i22 + 3]: body.remove(e)
# A23 Skewness legs
_, t23 = tbl_after("Table A23.")
ORD = [("metals", "Metals"), ("petroleum", "Petroleum"), ("pen", "Gas and Emissions"), ("precious", "Precious Metals"), ("ngl", "NGL"), ("agri", "Agriculture"), ("softs", "Softs")]
rows23 = []
for v, lab in ORD:
    for a, p in MEMBERS[v]:
        lg_ = legs(a, p)["full"]
        rows23.append([f"{lab}: {PNM.get(p, p)}", U(lg_["long_pct"], 0) + "%", N(lg_["long_pnl"]), N(lg_["short_pnl"]), I(pst(a, p, "Skewness")["ir"])])
rebuild_table(t23, rows23)
# A24 effect of adding Skewness
_, t24 = tbl_after("Table A24.")
def four_five(v):
    return [I(st4(v, "EW PORT")["ir"]), I(st(v, "EW PORT")["ir"]), I(st4(v, "Inverse Vol")["ir"]), I(st(v, "Inverse Vol")["ir"])]
rows24 = [[lab] + four_five(v) for v, lab in ORD] + [["Cross-commodity (seven buckets)", I(stats(BS4["EW PORT"])["ir"]), I(stats(BS["EW PORT"])["ir"]), I(stats(BS4["Inverse Vol"])["ir"]), I(stats(BS["Inverse Vol"])["ir"])]]
rebuild_table(t24, rows24)
# A25 correlations of Skewness
_, t25 = tbl_after("Table A25.")
def corrrow(v):
    c = corr_within(v); return [N(c.loc["Skewness", k]) for k in ("Momentum", "Carry", "CarryMom", "Value", "EW PORT")]
rebuild_table(t25, [[lab] + corrrow(v) for v, lab in ORD])
set_text(P(E()[find_p("Table A25.")]), "Table A25. Skewness: Correlation with the Other Sleeves and with the Equal Weight Portfolio, within Each Bucket")
# the three "Note: ... still measured to 23 September" paragraphs are no longer true: every row is on the 30 September data
for e in list(E()):
    if is_p(e) and ptext(e).startswith("Note: the Metals, Petroleum, Precious Metals and Agriculture rows are measured to 30 September 2026"):
        body.remove(e)

# ----------------------------------------------------------------------------------------------------------------------------- liquidity table A26 and paragraph
ci26, t26 = tbl_after("Table A26.")
liq = pd.read_csv(os.path.join(REPO, "Analysis", "Liquidity_Cal2025_results.csv")).set_index("product")
_pl = pd.read_csv(os.path.join(REPO, "Analysis", "Power_Liquidity_Cal2025_results.csv")).set_index("product").rename(columns={"price_usd_mwh": "price_usd_unit", "mult_mwh": "mult"})
liq = pd.concat([liq, _pl[[c for c in liq.columns if c in _pl.columns]]])
GRP = [("Metals", ["Copper", "Aluminium", "Zinc", "Lead"]), ("Petroleum", ["Brent", "WTI", "SingaporeGasoil", "HeatingOil", "RBOB"]), ("Gas and Emissions", ["NatGas", "TTF", "UKGas", "EUA"]),
       ("Precious Metals", ["Gold", "Silver", "Platinum", "Palladium"]), ("NGL", ["Propane", "Butane", "Ethane", "Naphtha", "NatGasoline"]), ("Agriculture", ["Soybean", "Corn", "Wheat", "LiveCattle"]), ("Softs", ["Sugar", "Cocoa", "Coffee", "Cotton"]), ("US Power (Standalone)", ["PJM_Peak", "ERCOT_Peak", "PJM_OffPeak", "ERCOT_OffPeak", "MISO_Peak", "MISO_OffPeak"])]
LN = {"SingaporeGasoil": "Singapore Gasoil†", "HeatingOil": "Heating Oil", "NatGas": "Henry Hub (Nat Gas)", "UKGas": "UK Gas (NBP)", "SoybeanOil": "Soybean Oil", "Propane": "Propane*", "Butane": "Butane*", "Ethane": "Ethane*", "Naphtha": "Naphtha*", "NatGasoline": "Natural Gasoline*", "LiveCattle": "Live Cattle", "Isobutane": "Isobutane*", "PJM_Peak": "PJM Peak", "ERCOT_Peak": "ERCOT Peak", "PJM_OffPeak": "PJM OffPeak", "ERCOT_OffPeak": "ERCOT OffPeak", "MISO_Peak": "MISO Peak", "MISO_OffPeak": "MISO OffPeak‡"}
allp = [p for _, ps in GRP for p in ps]
rank = {p: i + 1 for i, p in enumerate(sorted(allp, key=lambda q: -liq.loc[q, "x_strip"]))}
chk(len(allp) == 36, "36 liquidity products")
def fx(v): return f"{v:,.1f}" if v >= 1 else (f"{v:.3f}")
def fx2(v): return f"{v:,.1f}" if v >= 10 else (f"{v:.2f}" if v >= 1 else f"{v:.3f}")
def fL(v): return f"{v:.0f}" if v >= 10 else (f"{v:.1f}" if v >= 1 else (f"{v:.3f}" if v >= 0.01 else f"{v:.4f}"))
def fP(v, p): return f"{v:,.3f}" if p in ("Propane", "Butane", "Ethane", "Isobutane", "SoybeanOil", "Sugar", "LiveCattle", "Cotton", "NatGasoline") and v < 10 else f"{v:,.2f}"
def fm(v): return f"{v:,.1f}" if abs(v - round(v)) > 1e-9 and v < 1000 and v != int(v) else f"{v:,.0f}"
rows_xml = list(t26._tbl.findall(qn("w:tr")))
hdr_tmpl, prod_tmpl = copy.deepcopy(rows_xml[1]), copy.deepcopy(rows_xml[2])
for r in rows_xml[1:]: t26._tbl.remove(r)
def add_row(tmpl, data):
    r = copy.deepcopy(tmpl); t26._tbl.append(r); row = t26.rows[-1]
    for c, x in zip(row.cells, data): cell_set(c, x)
for g, ps in GRP:
    add_row(hdr_tmpl, [g] * 11)
    for p in sorted(ps, key=lambda q: -liq.loc[q, "x_strip"]):
        r_ = liq.loc[p]
        add_row(prod_tmpl, [LN.get(p, p), r_["strip"], f"{r_['adv_strip']:,.0f}", fP(r_["price_usd_unit"], p), f"{r_['sigma'] * 100:.2f}", fm(r_["mult"]), f"{r_['risk_per_contract']:,.0f}", fx2(r_["x_strip"]), fL(r_["L_strip"]), str(rank[p]), f"{r_['share_days_print'] * 100:.0f}%"])
set_text(P(E()[ci26]), "Table A26. Dollar Risk Turnover by Product, Calendar 2025 (36 Products, Seven Buckets and US Power)")
i118 = find_p("Results across 26 products."); _p = P(E()[i118]); _rs = _p.runs; _full = liquidity_paragraph(); _lab = "Results across 36 products."
assert _full.startswith(_lab) and _rs[0].bold and _rs[3].bold is None
_rs[0].text = _lab + " "
for _r in _rs[1:3]: _r._r.getparent().remove(_r._r)
_rs = _p.runs; _rs[0].text = _lab + " "; _rs[1].text = _full[len(_lab) + 1:]
for _r in _rs[2:]: _r._r.getparent().remove(_r._r)
inote = find_p("Note: Calendar 2025 only")
nt = ptext(E()[inote])
nt = nt.replace("The table covers 26 products: the 25 of the research universe plus Singapore Gasoil†", "The table covers 36 products: the 29 of the seven buckets, the five US Power series of the standalone Power section, Singapore Gasoil† and MISO OffPeak‡")
nt = nt.replace("* NGL volumes are the CME contracts only (ICE is not included), so NGL figures are lower bounds.", "* NGL volumes are the CME contracts only (ICE is not included) and Naphtha volume is the Bloomberg series, a partial view of the swap market, so these figures are lower bounds.")
nt = nt.replace("Isobutane printed on only 13% of days with a median daily volume of zero, which is what its very low x reflects. ", "")
nt = nt.replace("EUA and TTF are converted from EUR at 1.1300", "EUA and TTF are converted from EUR at 1.1300 and UK Gas from pence per therm at 1.3184 USD/GBP (the 2025 mean of the ECB crosses; its lot is 1,000 therms a day over an average month, 30,417 therms)")
nt = nt.replace("† The series is ICE Low Sulphur Gasoil", "‡ MISO OffPeak (time to trade one sigma of risk 9.9 days) is not in the Power results. US Power lots are 1 MW for every hour of the delivery month (ICE), taken as 340 MWh for peak and 390 MWh for off-peak contracts (304 to 368 and 352 to 417 MWh across the 2025 months). † The series is ICE Low Sulphur Gasoil")
assert "36 products" in nt and "Bloomberg series" in nt and "MISO OffPeak (time" in nt
set_text(P(E()[inote]), nt)

# ----------------------------------------------------------------------------------------------------------------------------- front matter
set_text(P(E()[1]), "Metals, Petroleum, Gas and Emissions, Precious Metals, NGL, Agriculture, Softs, US Power (Standalone), Correlation Analysis, and Cross-Commodity Portfolio")
ib = find_p("Basis of all results"); bt = ptext(E()[ib])
a1 = "1 January 2012 to 30 September 2026 for Metals, Petroleum, Precious Metals and Agriculture (the sections updated in v7) and to 23 September 2026 for everything else (see the version note)."
a2 = " Energy includes Natural Gas unless stated."
a3 = "Each asset class has five sleeves:"
for a in (a1, a2, a3): assert a in bt, a
bt = bt.replace(a1, "1 January 2012 to 30 September 2026 for all seven buckets.").replace(a2, " Naphtha is part of NGL, with Carry and Carry-Momentum on the F2-F4 pair only. US Power is a standalone bucket outside the cross-commodity book and is reported from 2 January 2017 (its data start in 2015 and Value needs two years of F3), so it has no P1.").replace(a3, "Each bucket has five sleeves:")
set_text(P(E()[ib]), bt)
iv_ = find_p("Version note (v7")
set_text(P(E()[iv_]), "Version note (v8, 10 November 2026). All seven buckets are on the data to 30 September 2026 and the current bucket definitions. Gas and Emissions (Henry Hub, TTF, UK Gas and EUA) is a new section, with its own appendix tables and figures; "
         "Henry Hub, previously part of Energy, is in it and UK Gas is new. NGL has five products (Ethane, Propane, Butane, Naphtha and Natural Gasoline): Naphtha is added to the three Mont Belvieu products, the CME Mont Belvieu natural gasoline swap (MMB) is added as the fifth on 10 November 2026, and Isobutane, the least liquid product in the data set, is removed from every bucket, pair, correlation and table. "
         "Agriculture is split in two on 10 November 2026: Agriculture (Corn, Wheat, Soybean and Live Cattle) and Softs (Sugar, Cocoa, Coffee and Cotton), a new section with its own appendix tables and figures; Soybean Oil is dropped, Live Cattle, Cocoa and Cotton are new, and the Carry tenor pairs are F1-F2 plus F1-F6 (F1-F7 for Soybean and Live Cattle). The single-pair, long-pair and two-pair Carry comparison of the Agriculture section is recomputed for the new pairs, in Agriculture and in Softs. "
         "The Correlation Analysis and the Cross-Commodity Portfolio cover the seven buckets and all twenty-one bucket pairs, so the Energy-ex-NatGas comparison no longer applies. "
         "US Power (PJM, ERCOT and MISO real-time monthly futures) is added as a standalone bucket with its own section, appendix tables and figures; it is not part of the cross-commodity book. The Key Findings, the liquidity section and table (36 products, with UK Gas, Naphtha, Natural Gasoline, Live Cattle, Cocoa, Cotton and the US Power series) and every appendix table and figure are redrawn on this basis, all figures as a cumulative return index starting at 100%, and tables and figures are renumbered.")
ipet = find_p("Petroleum is the four oil products")
tp = ptext(E()[ipet]); assert "Power, Emissions and Nat Gas" in tp
set_text(P(E()[ipet]), tp.replace("Natural Gas has moved to the Power, Emissions and Nat Gas bucket and is not covered here", "Natural Gas has moved to the Gas and Emissions bucket, which has its own section").replace(" (five further trading days, 24 to 30 September, than the previous version)", ""))

ipm_ = find_p("Portfolio construction: Equal Weight (Return -1.8%, Vol 7.8%"); tpm_ = ptext(E()[ipm_])
a_pm = "Precious Metals is, with Agriculture, one of the two asset classes where no core strategy earns a worthwhile IR (here every core strategy is net negative full-sample) and neither construction earns a positive IR."
assert a_pm in tpm_
set_text(P(E()[ipm_]), tpm_.replace(a_pm, "Precious Metals is, with Agriculture, one of the two buckets where every core strategy is net negative full-sample, and with Agriculture and Softs one of the three buckets where neither construction earns a positive IR."))

# ----------------------------------------------------------------------------------------------------------------------------- Key Findings
els = E(); ik = find_p("Key Findings", style="Heading 2")
old_kf = [ptext(e) for e in bullets_after(els[ik])]
new_kf = key_findings(old_kf)
new_kf[4] = new_kf[4].replace("asset classes", "buckets")
new_kf.insert(2, KEY_POWER)
set_bullets_run(els[ik], new_kf)

# ----------------------------------------------------------------------------------------------------------------------------- NGL section
els = E(); ing = find_p("NGL", find_p("Precious Metals", ik + 1, "Heading 2") + 1, "Heading 2")
set_bullets_run(E()[ing], ngl8())

# ----------------------------------------------------------------------------------------------------------------------------- Correlation Analysis
# ----------------------------------------------------------------------------------------------------------------------------- Agriculture section (four products) and the new Softs section
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
els = E(); icor = find_p("Correlation Analysis", style="Heading 2")
iw = find_p("Within-Asset-Class Correlation", icor, "Heading 3"); set_bullets_run(E()[iw], c8["within"])
ic = find_p("Cross-Commodity Correlation", iw, "Heading 3"); set_bullets_run(E()[ic], c8["cross"])
ip_ = find_p("Portfolio Construction Implication", ic, "Heading 3"); els = E()
bl = bullets_after(els[ip_]); assert len(bl) == 1
set_text(P(bl[0]), c8["impl_intro"])
tpair = els[els.index(bl[0]) + 1]; assert is_tbl(tpair)
rebuild_table(Table(tpair, d), c8["pair_rows"])
after = els[els.index(tpair) + 1:]
close = next(e for e in after if is_p(e) and P(e).style.name == "List Bullet")
set_text(P(close), c8["impl_close"])

# ----------------------------------------------------------------------------------------------------------------------------- Cross-Commodity Portfolio
Bx, _F = cross8()
els = E(); icp = find_p("Cross-Commodity Portfolio", style="Heading 2")
set_bullets_run(els[icp], Bx)

# ----------------------------------------------------------------------------------------------------------------------------- Gas and Emissions section (cloned from the Petroleum block)
els = E(); ipe = find_p("Petroleum", find_p("Metals", find_p("Key Findings", style="Heading 2") + 1, "Heading 2") + 1, "Heading 2")
cap_pet = find_p("Figure 2. Petroleum")
head_t = els[ipe]; bullet_t = bullets_after(head_t)[0]; img_t = els[cap_pet - 1]; cap_t = els[cap_pet]
anchor = els[cap_pet]
new_h = copy.deepcopy(head_t); set_text(P(new_h), "Gas and Emissions"); anchor.addnext(new_h); anchor = new_h
for t in gasem():
    nb = copy.deepcopy(bullet_t); set_text(P(nb), t); anchor.addnext(nb); anchor = nb
fig = make_figure_para(img_t, os.path.join(IMG, "fig_pen_combined.png")); anchor.addnext(fig); anchor = fig
nc = copy.deepcopy(cap_t); set_text(P(nc), "Figure ?. Gas and Emissions: Combined Strategy Performance (Cumulative Return, 2012-2026)"); anchor.addnext(nc)

# appendix tables of Gas and Emissions (cloned from Table A4 to A6)
els = E(); i4 = find_p("Table A4. Petroleum"); i6 = find_p("Table A6. Petroleum")
blk = els[i4:i6 + 3]; assert len(blk) == 9 and [is_tbl(e) for e in blk] == [False, True, False] * 3, [is_tbl(e) for e in blk]
anchor = blk[-1]; news = []
for e in blk:
    n = copy.deepcopy(e); anchor.addnext(n); anchor = n; news.append(n)
set_text(P(news[0]), "Table A?. Gas and Emissions: Strategy Information Ratios by Period")
set_text(P(news[3]), "Table A?. Gas and Emissions: Portfolio Construction Information Ratios by Period")
set_text(P(news[6]), "Table A?. Gas and Emissions: Individual-Product Information Ratios, All Strategies (Full Sample)")
ta, tb_, tc_ = Table(news[1], d), Table(news[4], d), Table(news[7], d)
for r, vals in zip(ta.rows[1:], st_cells("pen", SLEEVES)):
    for c, x in zip(r.cells[1:], vals): cell_set(c, x)
for r, vals in zip(tb_.rows[1:], st_cells("pen", ["EW PORT", "Inverse Vol"])):
    for c, x in zip(r.cells[1:], vals): cell_set(c, x)
hdr = [c.text for c in tc_.rows[0].cells[1:]]; assert len(hdr) == 4
for c, (a, p) in zip(tc_.rows[0].cells[1:], MEMBERS["pen"]): cell_set(c, PNM.get(p, p))
for r, k in zip(tc_.rows[1:], K):
    for c, (a, p) in zip(r.cells[1:], MEMBERS["pen"]): cell_set(c, I(pst(a, p, k)["ir"]))

# appendix charts of Gas and Emissions (cloned from the Petroleum group)
els = E(); ih = find_p("Petroleum", find_p("Appendix: Equity-Curve Charts", style="Heading 2"), "Heading 3")
grp = els[ih:ih + 11]; assert is_p(grp[0]) and all(is_p(e) for e in grp)
anchor = grp[-1]
hn = copy.deepcopy(grp[0]); set_text(P(hn), "Gas and Emissions"); anchor.addnext(hn); anchor = hn
for j, k in enumerate(K):
    f_ = make_figure_para(grp[1 + 2 * j], os.path.join(IMG, f"figA_pen_{k}.png")); anchor.addnext(f_); anchor = f_
    cn = copy.deepcopy(grp[2 + 2 * j]); set_text(P(cn), f"Figure A?. Gas and Emissions, {KN[k]}: Equity Curve by Product (2012-2026)"); anchor.addnext(cn); anchor = cn
iin = find_p("Individual equity curves underlying")
set_text(P(E()[iin]), "Individual equity curves underlying the combined-strategy figures above, decomposed by instrument for each strategy within each bucket, and by bucket pair, one chart per construction method, for the Cross-Pair Portfolios (all twenty-one pairs). Skewness charts are included for every bucket.")
for e in E():
    if is_p(e) and ptext(e).startswith("Figure A26. Cross-Pair Portfolios, Equal Weight"): set_text(P(e), "Figure A26. Cross-Pair Portfolios, Equal Weight: Equity Curve by Bucket Pair (2012-2026)")
    if is_p(e) and ptext(e).startswith("Figure A27. Cross-Pair Portfolios, Inverse Vol"): set_text(P(e), "Figure A27. Cross-Pair Portfolios, Inverse Vol: Equity Curve by Bucket Pair (2012-2026)")

# ----------------------------------------------------------------------------------------------------------------------------- verification log
# ----------------------------------------------------------------------------------------------------------------------------- US Power (standalone): section after Agriculture, appendix tables, appendix charts
anchor = SOFTS_CAP
hp = copy.deepcopy(head_t); set_text(P(hp), "US Power (Standalone)"); anchor.addnext(hp); anchor = hp
for t in B_POWER:
    nb = copy.deepcopy(bullet_t); set_text(P(nb), t); anchor.addnext(nb); anchor = nb
fg = make_figure_para(img_t, os.path.join(IMG, "fig_power_combined.png")); anchor.addnext(fg); anchor = fg
ncp = copy.deepcopy(cap_t); set_text(P(ncp), "Figure ?. US Power (Standalone): Combined Strategy Performance (Cumulative Return, 2017-2026)"); anchor.addnext(ncp)
# appendix tables: after the Softs tables
anchor = SOFTS_TABLE_ANCHOR      # the last element of the Softs appendix tables (inserted above)
i13n = find_p("Table A13. NGL: Individual-Product"); ngl_blk = E()[i13n:i13n + 3]
blocks = [news[0:3], news[3:6], ngl_blk]
caps = ["Table A?. US Power (Standalone): Strategy Information Ratios by Period (2017 onwards)", "Table A?. US Power (Standalone): Portfolio Construction Information Ratios by Period (2017 onwards)", "Table A?. US Power (Standalone): Individual-Product Information Ratios, All Strategies (Full Sample from 2017)"]
pnew = []
for blk_, cap_ in zip(blocks, caps):
    for e in blk_:
        n = copy.deepcopy(e); anchor.addnext(n); anchor = n; pnew.append(n)
    set_text(P(pnew[-3]), cap_)
tps, tpp, tpi = Table(pnew[1], d), Table(pnew[4], d), Table(pnew[7], d)
for t_ in (tps, tpp):
    assert [c.text for c in t_.rows[0].cells][2] == "2012-16"; delete_column(t_, 2)
PWIN = [("Full", "full"), ("2017-21", "p2"), ("2022-26", "p3")]
for r, k in zip(tps.rows[1:], SLEEVES):
    for c, (_, w) in zip(r.cells[1:], PWIN): cell_set(c, I(stp(STY_P[k], w)["ir"]))
for r, k in zip(tpp.rows[1:], ["EW PORT", "Inverse Vol"]):
    for c, (_, w) in zip(r.cells[1:], PWIN): cell_set(c, I(stp(ROWS_P[k], w)["ir"]))
assert [c.text for c in tpi.rows[0].cells[1:]] == ["Ethane", "Propane", "Butane", "Naphtha", "Natural Gasoline"]      # the NGL product table the Power table is cloned from has five products since Natural Gasoline joined
# the five NGL columns are exactly what the five Power series need
for c, p in zip(tpi.rows[0].cells[1:], MEMBERS_P): cell_set(c, LABEL_P[p])
for r, k in zip(tpi.rows[1:], K):
    for c, p in zip(r.cells[1:], MEMBERS_P): cell_set(c, I(stp(NETS_P[p][k])["ir"]))
# appendix charts of Softs: a copy of the Agriculture group, right after it
els = E(); ia_ = find_p("Agriculture", find_p("Appendix: Equity-Curve Charts", style="Heading 2"), "Heading 3")
grp_a = els[ia_:ia_ + 11]; assert is_p(grp_a[0]) and all(is_p(e) for e in grp_a)
anchor = grp_a[-1]
hs_ = copy.deepcopy(grp_a[0]); set_text(P(hs_), "Softs"); anchor.addnext(hs_); anchor = hs_
for j, k in enumerate(K):
    f_ = make_figure_para(grp_a[1 + 2 * j], os.path.join(IMG, f"figA_softs_{k}.png")); anchor.addnext(f_); anchor = f_
    cn_ = copy.deepcopy(grp_a[2 + 2 * j]); set_text(P(cn_), f"Figure A?. Softs, {KN[k]}: Equity Curve by Product (2012-2026)"); anchor.addnext(cn_); anchor = cn_
# appendix charts of US Power: after the Softs group, before the Cross-Pair group
els = E(); icpg = find_p("Cross-Pair Portfolios", find_p("Appendix: Equity-Curve Charts", style="Heading 2"), "Heading 3")
anchor = E()[icpg - 1]
hn2 = copy.deepcopy(grp[0]); set_text(P(hn2), "US Power (Standalone)"); anchor.addnext(hn2); anchor = hn2
for j, k in enumerate(K):
    f_ = make_figure_para(grp[1 + 2 * j], os.path.join(IMG, f"figA_power_{k}.png")); anchor.addnext(f_); anchor = f_
    cn = copy.deepcopy(grp[2 + 2 * j]); set_text(P(cn), f"Figure A?. US Power (Standalone), {KN[k]}: Equity Curve by Product (2017-2026)"); anchor.addnext(cn); anchor = cn
set_text(P(E()[find_p("Individual equity curves underlying")]), ptext(E()[find_p("Individual equity curves underlying")]).replace("within each bucket, and by bucket pair", "within each bucket and for the standalone US Power bucket (from 2017), and by bucket pair"))

iver = find_p("Appendix: Verification Log"); set_text(P(E()[iver]), "Appendix: Verification Log (v3_2012 to v8)")
iv7 = find_p("v7 (1 November 2026) extends")
nv = copy.deepcopy(E()[iv7]); E()[iv7].addnext(nv)
set_text(P(nv), "v8 (10 November 2026) VERIFICATION_PLACEHOLDER")
els = E(); itab = None
for k in range(iv7, len(els)):
    if is_tbl(els[k]): itab = els[k]; break
tver = Table(itab, d)
import json as _json
_Bc, _Fc = cross8(); _best, _b2 = _Fc["best"], _Fc["b2"]
_old = _json.load(open(os.path.join(REPO, "outputs", "final_dashboard_0930_pre_isobutane", "final_v3.json"), encoding="utf8"))
_oN = {r["name"]: r["ir"] for r in _old["tabs"]["ngl"]["windows"]["full"]}
_nE, _nI = st("ngl", "EW PORT"), st("ngl", "Inverse Vol")
_three = [m for m in MEMBERS["ngl"] if m[0] == "ngl"]
_cs3 = pd.DataFrame({k: ew_intersection([nets()[m][k] for m in _three]) for k in SLEEVES}); _e3, _i3 = stats(_cs3.mean(axis=1, skipna=False)), stats(inverse_vol(_cs3))
_Fe, _Fi = _Fc["ew"], _Fc["iv"]
_old2 = _json.load(open(os.path.join(REPO, "outputs", "final_dashboard_0930_pre_agri_split", "final_v3.json"), encoding="utf8"))
_o2 = lambda tab, name: next(z for z in tab["windows"]["full"] if z["name"] == name)
_o2_book = {n: _o2(_old2["bystyle"], n)["ir"] for n in ("EW PORT", "Inverse Vol")}
_o2_agri = {n: _o2(_old2["tabs"]["agri"], n)["ir"] for n in ("EW PORT", "Inverse Vol")}
_o2_ngl = {n: _o2(_old2["tabs"]["ngl"], n)["ir"] for n in ("EW PORT", "Inverse Vol")}
_four = MEMBERS["ngl"][:4]
_cs4 = pd.DataFrame({k: ew_intersection([nets()[m][k] for m in _four]) for k in SLEEVES}); _e4, _i4 = stats(_cs4.mean(axis=1, skipna=False)), stats(inverse_vol(_cs4))
_aE, _aI, _sE, _sI = st("agri", "EW PORT"), st("agri", "Inverse Vol"), st("softs", "EW PORT"), st("softs", "Inverse Vol")
_bi = _Fc["best_iv"]
_tenA = bucket_tenor_table("agri")[0]; _tenS = bucket_tenor_table("softs")[0]
vrows = [
    ["v7 NGL figures on the v5 basis (to 23 September 2026): Equal Weight IR +1.25, Inverse Vol +1.16", f"Now {I(_nE['ir'])} and {I(_nI['ir'])} on the 30 September data with five products (the three Mont Belvieu products on the same data: {I(_e3['ir'])} and {I(_i3['ir'])}; with Naphtha as the fourth product: {I(_e4['ir'])} and {I(_i4['ir'])}; Natural Gasoline, the CME MMB swap, is the fifth and lowers the bucket IR); Naphtha series from the Bloomberg KI swap sheet with the Bloomberg expiry calendar, Carry on F2-F4 only; Natural Gasoline from the Bloomberg MMB sheet with the Bloomberg expiry history, Carry on F2-F4 and F2-F14", "Recomputed; 0930 dashboard dataset"],
    [f"v8 as first issued (6 November 2026): NGL of five products including Isobutane, Equal Weight IR {I(_oN['EW PORT'])}, Inverse Vol {I(_oN['Inverse Vol'])}", f"Isobutane removed from every bucket, portfolio, pair, correlation and table on 9 November 2026 because it is the least liquid of the 36 products then measured (about 10 lots a day on its 12-month strip, a USD 1 million one-sigma position equals 156 days of its risk turnover): NGL {I(_e4['ir'])} and {I(_i4['ir'])} with four products; six-bucket book {I(_o2_book['EW PORT'])} and {I(_o2_book['Inverse Vol'])} (26 products in the buckets)", "Recomputed; 0930 dashboard dataset; Liquidity_Cal2025_results.csv"],
    [f"v8 before 10 November 2026: Agriculture of six products (Corn, Wheat, Soybean, Soybean Oil, Coffee, Sugar), Equal Weight IR {I(_o2_agri['EW PORT'])}, Inverse Vol {I(_o2_agri['Inverse Vol'])}; NGL of four products, {I(_o2_ngl['EW PORT'])} and {I(_o2_ngl['Inverse Vol'])}", f"Agriculture split in two on 10 November 2026: Agriculture (Corn, Wheat, Soybean, Live Cattle) {I(_aE['ir'])} and {I(_aI['ir'])}; Softs (Sugar, Cocoa, Coffee, Cotton) {I(_sE['ir'])} and {I(_sI['ir'])}; NGL with Natural Gasoline {I(_nE['ir'])} and {I(_nI['ir'])}. Soybean Oil is dropped. Corn, Wheat and Coffee sleeves are equal to the previous ones to 1e-15 on the new data, Soybean and Sugar differ only in Carry and Carry-Momentum (new long legs F1-F7 and F1-F6)", "Recomputed; 0930 dashboard dataset; ENGINE_CHANGELOG 2026-11-10"],
    ["v7: Energy-NGL the best of ten pairs (Equal Weight +1.23, Inverse Vol +1.21; +1.28 and +1.30 without Natural Gas)", f"Petroleum-NGL is the best of twenty-one pairs under Equal Weight ({I(_best['ew']['ir'])}, {I(_best['iv']['ir'])}); Gas and Emissions-NGL is the best under Inverse Vol ({I(_bi['iv']['ir'])}, {I(_bi['ew']['ir'])}); the Energy-ex-NatGas comparison no longer applies because Natural Gas is in Gas and Emissions; the only negative pairs are the six built from Metals, Precious Metals, Agriculture and Softs", "Recomputed; 0930 dashboard dataset"],
    ["v7: cross-commodity book Equal Weight IR +0.87, Inverse Vol +0.91 at 4.9% and 5.0% volatility (five asset classes, Energy including Natural Gas)", f"Seven buckets, 29 products, 2012 to 30 September 2026 (US Power is not in the book): {I(_Fe['ir'])} and {I(_Fi['ir'])} at {V(_Fe['vol'])} and {V(_Fi['vol'])} volatility, positive in every period; commodity-index correlation {N(_Fc['bE']['Commodity Index'])} and {N(_Fc['bI']['Commodity Index'])}; the six-bucket book before the split was {I(_o2_book['EW PORT'])} and {I(_o2_book['Inverse Vol'])}", "Recomputed; 0930 dashboard dataset"],
    ["v7: Skewness correlation with the commodity index +0.46 in the five-class book", f"{N(_Fc['bS']['Commodity Index'])} in the seven-bucket book (equity {N(_Fc['bS']['Equity'])}, gold {N(_Fc['bS']['Gold'])})", "Recomputed; ETF file cut at 30 September 2026"],
    ["v7: bucket 'Power, Emissions and Nat Gas' (Henry Hub, TTF, EUA)", "Gas and Emissions with UK Gas added (Henry Hub, TTF, UK Gas, EUA); UK Gas from the Bloomberg NBP sheet, Bloomberg expiry history", "Recomputed; 0930 dashboard dataset"],
    ["v7 liquidity section: 26 products, Power, Emissions and Natural Gas 17.1-fold spread", f"36 products with UK Gas, Naphtha, Natural Gasoline, Live Cattle, Cocoa, Cotton and the six US Power series (five in the Power results, MISO OffPeak flagged); Isobutane, the least liquid product measured (of 40), is outside the table; Cotton ({fx2(liq.loc['Cotton', 'x_strip'])}) is now the least liquid product outside NGL and US Power, ahead of Lead ({fx2(liq.loc['Lead', 'x_strip'])}); Natural Gasoline {liq.loc['NatGasoline', 'L_strip']:.2f} days to trade one sigma of risk; Gas and Emissions spread 21.3-fold (Henry Hub to UK Gas); Naphtha 9.4 days (Bloomberg volume, lower bound); US Power 0.10 to 4.7 days", "Liquidity_Cal2025_results.csv; Power_Liquidity_Cal2025_results.csv; scripts/liquidity_cal2025_1110.py"],
    ["v7 Key Findings marked 'v5 basis' (NGL, Energy-NGL pair, cross-commodity book)", "Rewritten on seven buckets; the Petroleum and Metals findings are unchanged and the Precious Metals and Agriculture finding is replaced by one on Precious Metals, Agriculture and Softs", "Recomputed"],
    ["v7: no US Power coverage", "New standalone US Power section (outside the seven-bucket book): five ICE series (PJM Peak and OffPeak, ERCOT Peak and OffPeak, MISO Peak; MISO OffPeak excluded at 9.9 days), data to 30 September 2026, reported from 2017 (no P1); Equal Weight IR +0.30, Inverse Vol +0.31", "Recomputed; dashboard Power tab (power_tab_0930.json); Power_Liquidity_Cal2025_results.csv"],
    ["v8 Agriculture section: table of single-pair, long-pair and two-pair Carry and Carry-Momentum IRs (six products)", f"Recomputed for the pairs fixed on 10 November 2026 (F1-F2 plus F1-F6; F1-F7 for Soybean and Live Cattle), in Agriculture and in the new Softs bucket; the two-pair series are equal to the reported bucket sleeves (difference below 1e-9). Agriculture Carry {I(_tenA['Carry']['short']['ir'])} / {I(_tenA['Carry']['long']['ir'])} / {I(_tenA['Carry']['two']['ir'])} (short / long / sum); Softs {I(_tenS['Carry']['short']['ir'])} / {I(_tenS['Carry']['long']['ir'])} / {I(_tenS['Carry']['two']['ir'])}", "Recomputed; facts_tenor.py"],
    ["v8 data: Agriculture prices from the 24 September and 29 October pulls (six products)", "Agriculture, Softs and Natural Gasoline from the Bloomberg pull of 10 November 2026, cut at 30 September. Prices of Corn, Wheat, Soybean, Coffee and Sugar equal the earlier files on every overlapping cell (except the 29 October row, an intraday print in the old file, and Soybean F18); calendar last trade dates equal the validated calendars on every overlapping contract; exchange-holiday rows with a blank front month are removed (Wheat 25 May 2009, Soybean 26 November 2009, Cocoa 4 September 2017, Cotton 2007); Cotton rolls about one day before expiry because its last trade date falls on the 6th to 9th of the month", "data/Prices_1110; ENGINE_CHANGELOG 2026-11-10"],
]
tmpl = copy.deepcopy(tver._tbl.findall(qn("w:tr"))[-1])
for vr in vrows:
    r = copy.deepcopy(tmpl); tver._tbl.append(r)
    for c, x in zip(tver.rows[-1].cells, vr): cell_set(c, x)

# ----------------------------------------------------------------------------------------------------------------------------- renumber captions and references
CAP = re.compile(r"^(Table A|Figure A|Figure )(\d+|\?)\.")
maps = {"Table A": {}, "Figure A": {}, "Figure ": {}}
counter = {"Table A": 0, "Figure A": 0, "Figure ": 0}
for e in E():
    if is_p(e):
        t = ptext(e); m = CAP.match(t)
        if m:
            kind, num = m.group(1), m.group(2)
            counter[kind] += 1
            if num != "?":
                assert int(num) not in maps[kind], (kind, num); maps[kind][int(num)] = counter[kind]
            set_text(P(e), f"{kind}{counter[kind]}." + t[m.end():])
REF = re.compile(r"(Tables? A|Figures? A|Figures? )(\d+)\b")
def fix_refs(text):
    def rep(m):
        kind = "Table A" if m.group(1).startswith("Table") else ("Figure A" if m.group(1).startswith("Figure A") else "Figure ")
        n = int(m.group(2))
        return m.group(1) + str(maps[kind].get(n, n))
    return REF.sub(rep, text)
nfix = 0
for e in E():
    if is_p(e):
        t = ptext(e)
        if CAP.match(t): continue
        t2 = fix_refs(t)
        if t2 != t and P(e).runs: set_text(P(e), t2); nfix += 1
print("captions renumbered:", {k: v for k, v in counter.items()}, "| references fixed in", nfix, "paragraphs")
d.save(OUT)
print("saved", OUT)

import facts as _f
if _f.SOFT_FAILS:
    print("TRIAL BUILD: failing claims:"); [print("  -", m) for m in _f.SOFT_FAILS]
