import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from doc_lib import *
from text_front import front
from text_metals import metals
from text_energy import energy
from text_precious import precious
from text_ngl import ngl
from text_agri import agri
from text_corr import correlation, crosscommodity
from text_appendix import appendix, verification

OUT = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia\Analysis\Risk Premia Analysis v5_2012.docx"
if os.path.exists(OUT):
    sys.exit("refusing to overwrite " + OUT)
blocks = []
for f in (front, metals, energy, precious, ngl, agri, correlation, crosscommodity, appendix, verification):
    blocks += f()

# ---- automatic checks on the text before writing
txt = []
for b in blocks:
    if b[0] in ("tbl",):
        for r in [b[1]] + b[2]: txt += [str(c) for c in r]
    elif b[0] == "fig":
        txt.append(b[2])
    else:
        txt.append(b[1])
full = "\n".join(txt)
problems = []
for pat, why in ((r"\bnan\b", "nan"), (r"-0\.00\b", "-0.00"), (r"\u2014|\u2013", "em/en dash"), (r"\bNone\b", "None"), (r"\{|\}", "unformatted brace"), (r"\+\+|--(?!-)", "double sign")):
    for m in re.finditer(pat, full):
        problems.append((why, full[max(0, m.start() - 40): m.end() + 40].replace("\n", " ")))
print("text problems:", len(problems))
for p in problems[:15]: print("  ", p)
figs = [b[2] for b in blocks if b[0] == "fig"]
print("figures:", len(figs), "| tables:", sum(1 for b in blocks if b[0] == "tbl"), "| bullets:", sum(1 for b in blocks if b[0] == "b"))
nums = [int(re.match(r"Figure (\d+)\.", f).group(1)) for f in figs if re.match(r"Figure \d+\.", f)]
chk_a = [int(re.match(r"Figure A(\d+)\.", f).group(1)) for f in figs if re.match(r"Figure A\d+\.", f)]
assert nums == list(range(1, 7)) and chk_a == list(range(1, 28)), (nums, chk_a)
if problems:
    sys.exit("fix text problems first")

d = new_doc()
render(d, blocks)
ft = d.sections[0].footer.paragraphs[0]
ft.runs[0].text = "Periods -- P1 (2012-2016)  |  P2 (2017-2021)  |  P3 (2022-2026)  |  Prof. Ilia Bouchouev, Kartavya Joshi, Dimil Patel, Multi-Asset Commodity Risk Premia"
for r in ft.runs[1:]: r.text = ""
d.save(OUT)
print("saved", OUT)
