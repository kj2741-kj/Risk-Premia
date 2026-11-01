"""Audit the finished analysis document against the dataset embedded in Dimil's committed Final_Research_Dashboard_2012.html (dimil_D.json).
1) every 'Return x%, Vol y%, Max Drawdown z%, IR w' line in the text must equal some row of the dataset (all four values, rounding tolerance);
2) every information-ratio table of the appendix that the dataset covers is compared cell by cell with the dataset row of the same label, window and asset class.
Usage: python audit_docx.py "<docx>"."""
import sys, os, re, json
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph

S = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(S, "dimil_D.json")))
path = sys.argv[1]
d = docx.Document(path)

# ---- all stat rows in the dataset
ROWS = []
def walk(o):
    if isinstance(o, dict):
        if {"ret", "vol", "mdd", "ir"} <= set(o): ROWS.append((o["ret"], o["vol"], o["mdd"], o["ir"]))
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(D)
print("dataset rows:", len(ROWS))

body = []
for c in d.element.body:
    t = c.tag.split("}")[1]
    if t == "p": body.append(("p", Paragraph(c, d).text))
    elif t == "tbl": body.append(("t", Table(c, d)))

pat = re.compile(r"Return ([+-]?\d+\.\d)%, Vol (\d+\.\d)%, Max Drawdown (-?\d+\.\d)%, IR ([+-]?\d+\.\d\d|0\.00)")
lines = 0; bad = []
for kind, x in body:
    if kind != "p": continue
    for m in pat.finditer(x):
        lines += 1
        r, v, dd, ir = (float(g) for g in m.groups())
        if not any(abs(r - a) < 0.051 and abs(v - b) < 0.051 and abs(dd - c) < 0.051 and abs(ir - e) < 0.0051 for a, b, c, e in ROWS):
            bad.append(m.group(0))
print("statistic lines in the text:", lines, "| not found in the dataset:", len(bad)); [print("   ", b) for b in bad[:10]]

NAME = {"Momentum": "Momentum", "Carry": "Carry", "Carry-Momentum": "CarryMom", "Value": "Value", "Skewness": "Skewness", "Equal Weight": "EW PORT", "Inverse Vol": "Inverse Vol"}
CLS = {"Metals": "metals", "Energy": "energy", "Energy ex-NatGas": "energy_exng", "Precious Metals": "precious", "NGL": "ngl", "Agriculture": "agri"}
W = {"Full": "full", "2012-16": "p1", "2017-21": "p2", "2022-26": "p3"}
def fmt(x): return "0.00" if abs(round(x, 2)) == 0 else f"{x:+.2f}"
cells = 0; mism = []; tables = 0; last_cap = ""
for kind, x in body:
    if kind == "p":
        if x.startswith("Table A"): last_cap = x
        continue
    cap = last_cap; last_cap = ""
    t = x; rows = [[c.text.strip() for c in r.cells] for r in t.rows]
    m = re.match(r"Table A\d+\. (.+)", cap)
    if not m: continue
    title = m.group(1)
    def chk(label, got, exp):
        global cells
        cells += 1
        # the dataset is rounded to 3 decimals, the document to 2 from full precision: a cell is a mismatch only if it differs by more than the dataset's own rounding (0.0005) plus half a unit of the second decimal
        if abs(float(got) - exp) > 0.0055: mism.append((title, label, got, round(exp, 3)))
    mm = re.match(r"(.+?): (Strategy Information Ratios by Period|Portfolio Construction Information Ratios by Period|Strategy and Portfolio Information Ratios by Period)$", title)
    if mm and mm.group(1) in CLS:
        key = CLS[mm.group(1)]; tables += 1
        for r in rows[1:]:
            for (wl, wk), cell in zip(W.items(), r[1:]):
                row = next(z for z in D["tabs"][key]["windows"][wk] if z["name"] == NAME[r[0]])
                chk(f"{r[0]} {wl}", cell, row["ir"])
        continue
    mm = re.match(r"(.+?): Individual-(?:Metal|Product) Information Ratios, All Strategies \(Full Sample\)$", title)
    if mm:
        key = CLS[mm.group(1)]; tables += 1; prods = [{"Heating Oil": "HeatingOil", "Natural Gas": "NatGas", "Soybean Oil": "SoybeanOil"}.get(x, x) for x in rows[0][1:]]
        for r in rows[1:]:
            for p, cell in zip(prods, r[1:]):
                chk(f"{r[0]} {p}", cell, D["products"][f"{key}|{p}"][NAME[r[0]]]["full"]["ir"])
        continue
    if title.startswith("Cross-Commodity Portfolio: Strategy Information Ratios by Period"):
        tables += 1
        for r in rows[1:]:
            for (wl, wk), cell in zip(W.items(), r[1:]):
                chk(f"{r[0]} {wl}", cell, next(z for z in D["bystyle"]["with NatGas"]["windows"][wk] if z["name"] == NAME[r[0]])["ir"])
        continue
    if title.startswith("Cross-Commodity Portfolio: Construction Information Ratios by Period"):
        tables += 1
        for r in rows[1:]:
            grp = "ex-NatGas" if "ex-NatGas" in r[0] else "with NatGas"; nm = "EW PORT" if r[0].startswith("Equal") else "Inverse Vol"
            for (wl, wk), cell in zip(W.items(), r[1:]):
                chk(f"{r[0]} {wl}", cell, next(z for z in D["bystyle"][grp]["windows"][wk] if z["name"] == nm)["ir"])
        continue
    if title.startswith("Cross-Pair Portfolio: Full-Sample Information Ratios") or title.startswith("Cross-Pair Portfolio: Energy Pairs Excluding"):
        grp = "with NatGas" if "All Ten" in title else "ex-NatGas"; tables += 1
        def norm(s): return s.replace(" Metals", "").replace("(ex-NatGas)", "").replace("Energy (ex-NatGas)", "Energy").replace("-", " - ").replace("  ", " ")
        for r in rows[1:]:
            lab = r[0].replace("Precious Metals", "Precious")
            for cidx, kind_ in ((1, "EW"), (2, "Inverse Vol")):
                found = [z for z in D["crosspair"][grp][kind_]["full"] if re.sub(r"[^a-z]", "", z["name"].lower().replace("(ex-natgas)", "").replace("ex-natgas", "").replace("metals", "")) == re.sub(r"[^a-z]", "", lab.lower().replace("(ex-natgas)", "").replace("ex-natgas", "").replace("metals", ""))]
                if found: chk(f"{r[0]} {kind_}", r[cidx], found[0]["ir"])
                else: mism.append((title, r[0], "no dataset row", ""))
        continue
print("appendix tables compared:", tables, "| cells compared:", cells, "| mismatches:", len(mism))
for x in mism[:15]: print("   ", x)
