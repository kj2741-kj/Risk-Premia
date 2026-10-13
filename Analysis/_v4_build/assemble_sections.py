"""Assemble Sections 4, 5 and 7 of the paper into Paper_Draft_1_Intro_and_Methodology_v2.docx from the modules the drafting agents save (paper_s4a.py, paper_s4b.py, paper_s4c.py, paper_s5.py).
Idempotent: any earlier insertion (from the heading '4. Empirical Results' up to the page break that precedes the drafting notes) is removed and rebuilt from whatever is saved now.
A module that fails to import or run (for example because it is mid-edit) is skipped and reported. Every run also writes a timestamped checkpoint copy to Analysis/_checkpoints/.
The Word file is never opened; if it is locked (open in Word) nothing is written and the script says so."""
import os, sys, copy, shutil, time, importlib, traceback, re
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.text.paragraph import Paragraph

S = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(S, "..")
F = os.path.join(A, "Paper_Draft_1_Intro_and_Methodology_v2.docx")
IMG = os.path.join(S, "v5img")
sys.path.insert(0, S)

MODULES = [("paper_s4a", "blocks"), ("paper_s4b", "blocks"), ("paper_s4c", "blocks"), ("paper_s5", "blocks"), ("paper_s5", "conclusion")]
blocks, report = [], []
for mod, fn in MODULES:
    try:
        if mod in sys.modules:
            del sys.modules[mod]
        m = importlib.import_module(mod)
        b = getattr(m, fn)()
        blocks += b
        words = sum(len(x[1].split()) for x in b if x[0] in ("p", "note"))
        report.append(f"OK    {mod}.{fn}: {len(b)} blocks, {words} words")
    except ModuleNotFoundError:
        report.append(f"WAIT  {mod}.{fn}: not saved yet")
    except Exception as e:
        report.append(f"SKIP  {mod}.{fn}: {type(e).__name__}: {str(e)[:150]}")
print("\n".join(report))
if not blocks:
    sys.exit("nothing to insert")

d = Document(F)
ps = d.paragraphs
i1 = next(i for i, p in enumerate(ps) if p.text.startswith("Drafting notes"))
k = i1 - 1
while k > 0 and not ps[k]._p.xpath('.//w:br[@w:type="page"]'):
    k -= 1
assert i1 - k <= 4, "page break before the drafting notes not found"
stop_el = ps[k]._p
# remove an earlier insertion
start = next((p for p in ps if p.text.strip() == "4. Empirical Results"), None)
if start is not None:
    el = start._p
    while el is not stop_el:
        nxt = el.getnext(); el.getparent().remove(el); el = nxt
tmpl = copy.deepcopy(ps[i1 - 1]._p)
for r in list(tmpl):
    if r.tag.endswith("}r"):
        tmpl.remove(r)
base = ps[0]._parent


def par(text="", bold=False, italic=False, size=None, align=None, keep=False, space_before=None):
    p = Paragraph(copy.deepcopy(tmpl), base)
    if text:
        r = p.add_run(text); r.bold = bold or None; r.italic = italic or None
        if size: r.font.size = Pt(size)
    if align is not None: p.alignment = align
    if keep: p.paragraph_format.keep_with_next = True
    if space_before is not None: p.paragraph_format.space_before = Pt(space_before)
    return p


def table(header, rows, widths=None):
    t = d.add_table(rows=len(rows) + 1, cols=len(header)); t.style = "Table Grid"; t.autofit = False
    for ri, row in enumerate([header] + rows):
        for ci, txt in enumerate(row):
            c = t.cell(ri, ci); pp = c.paragraphs[0]
            for r in list(pp.runs): r._element.getparent().remove(r._element)
            run = pp.add_run(str(txt)); run.font.size = Pt(9.5); run.bold = (ri == 0) or None
            pp.paragraph_format.space_after = Pt(0)
            if widths: c.width = Inches(widths[ci])
            if ci > 0 and ri > 0 and re.fullmatch(r"[+\-]?\d[\d.,]*%?|0\.00", str(txt).strip()):
                pp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    return t


put = stop_el.addprevious
for b in blocks:
    k = b[0]
    if k == "h1": put(par(b[1], bold=True, size=14, keep=True, space_before=10)._p)
    elif k == "h2": put(par(b[1], bold=True, size=12, keep=True, space_before=8)._p)
    elif k == "h3": put(par(b[1], bold=True, italic=True, size=11, keep=True, space_before=6)._p)
    elif k == "p": put(par(b[1])._p)
    elif k == "cap": put(par(b[1], bold=True, size=11, keep=True)._p)
    elif k == "note": put(par(b[1], italic=True, size=9.5)._p)
    elif k == "tbl":
        t = table(b[1], b[2], b[3] if len(b) > 3 else None)
        put(t._tbl); put(par()._p)
    elif k == "fig":
        pth = os.path.join(IMG, b[1]); assert os.path.exists(pth), pth
        p = par(align=WD_ALIGN_PARAGRAPH.CENTER, keep=True); p.add_run().add_picture(pth, width=Inches(6.0)); put(p._p)
        put(par(b[2], bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER)._p)
    else:
        raise ValueError("unknown block kind " + str(k))

try:
    d.save(F)
except PermissionError:
    sys.exit("LOCKED: the draft is open in Word; nothing written")
ck = os.path.join(A, "_checkpoints"); os.makedirs(ck, exist_ok=True)
cp = os.path.join(ck, "Paper_v2_checkpoint_" + time.strftime("%Y%m%d_%H%M%S") + ".docx")
shutil.copy(F, cp)
print("saved", F, "\ncheckpoint", cp)
