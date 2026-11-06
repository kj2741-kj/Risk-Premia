import json, re, sys, warnings
warnings.filterwarnings("ignore")
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
R = r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia"
h = open(R + r"\Analysis\Final_Research_Dashboard_2012_0930.html", encoding="utf-8").read()
i = h.index("const D"); D, _ = json.JSONDecoder().raw_decode(h[h.index("{", i):])
d = docx.Document(R + r"\Analysis\Risk Premia Analysis v7_2012.docx")
CLS = {"Metals": "metals", "Petroleum": "petroleum", "Precious Metals": "precious", "Agriculture": "agri"}
NAME = {"Momentum": "Momentum", "Carry": "Carry", "Carry-Momentum": "CarryMom", "Value": "Value", "Skewness": "Skewness", "Equal Weight": "EW PORT", "Inverse Vol": "Inverse Vol"}
W = {"Full": "full", "2012-16": "p1", "2017-21": "p2", "2022-26": "p3"}
PM = {"Heating Oil": "HeatingOil", "Soybean Oil": "SoybeanOil"}
PKEY = {"metals": "metals", "petroleum": "energy", "precious": "precious", "agri": "agri"}
body = []
for c in d.element.body:
    t = c.tag.split("}")[1]
    if t == "p": body.append(("p", Paragraph(c, d)))
    elif t == "tbl": body.append(("t", Table(c, d)))
out = {"lines": 0, "lines_bad": [], "cells": 0, "cells_bad": [], "corr": 0, "corr_bad": []}
# ---------- 1. statistic lines (all four values) for the four sections
pat = re.compile(r"Return ([+-]?\d+\.\d)%, Vol (\d+\.\d)%, Max Drawdown (-?\d+\.\d)%, IR ([+-]?\d+\.\d\d|0\.00)")
sec = None
def rows_of(cls):
    rs = []
    for w in ("full", "p1", "p2", "p3"):
        for r in D["tabs"][cls]["windows"][w]: rs.append((r["ret"], r["vol"], r["mdd"], r["ir"], r["name"], w))
    return rs
for k, p in body:
    if k != "p": continue
    if p.style.name == "Heading 2": sec = p.text
    if sec in CLS:
        for m in pat.finditer(p.text):
            out["lines"] += 1; r, v, dd, ir = (float(g) for g in m.groups()); cls = CLS[sec]
            hit = [x for x in rows_of(cls) if abs(r - x[0]) < .051 and abs(v - x[1]) < .051 and abs(dd - x[2]) < .051 and abs(ir - x[3]) < .0051]
            if not hit: out["lines_bad"].append((sec, m.group(0)))
# ---------- 2. appendix tables
last = ""
for k, x in body:
    if k == "p":
        if x.text.startswith("Table A"): last = x.text
        continue
    cap = last; last = ""
    m = re.match(r"Table A\d+\. (Metals|Petroleum|Precious Metals|Agriculture): (.+)", cap)
    if not m or "Tenor" in m.group(2): continue
    cls = CLS[m.group(1)]; rows = [[c.text.strip() for c in r.cells] for r in x.rows]
    def chk(lbl, got, exp):
        out["cells"] += 1
        if abs(float(got) - exp) > 0.0055: out["cells_bad"].append((cap[:34], lbl, got, round(exp, 3)))
    if "by Period" in m.group(2):
        for r in rows[1:]:
            for (wl, wk), c in zip(W.items(), r[1:]):
                chk(f"{r[0]} {wl}", c, next(z for z in D["tabs"][cls]["windows"][wk] if z["name"] == NAME[r[0]])["ir"])
    else:
        prods = [PM.get(p, p) for p in rows[0][1:]]
        for r in rows[1:]:
            for p, c in zip(prods, r[1:]): chk(f"{r[0]} {p}", c, D["products"][f"{PKEY[cls]}|{p}"][NAME[r[0]]]["full"]["ir"])
# ---------- 3. Table A25 (Skewness correlations) against the dashboard's within-class matrix
ORDER = ["Momentum", "Carry", "CarryMom", "Value", "Skewness", "EW PORT", "Inverse Vol"]
for k, x in body:
    if k == "t" and x.rows[0].cells[0].text == "" and [c.text for c in x.rows[0].cells][1:] == ["Momentum", "Carry", "Carry-Momentum", "Value", "EW PORT"]:
        for r in x.rows[1:]:
            if r.cells[0].text in CLS:
                M = D["corr"]["within"][CLS[r.cells[0].text]]
                for c, o in zip(r.cells[1:], ["Momentum", "Carry", "CarryMom", "Value", "EW PORT"]):
                    out["corr"] += 1; e = M[ORDER.index("Skewness")][ORDER.index(o)]
                    if abs(float(c.text) - e) > 0.0055: out["corr_bad"].append((r.cells[0].text, o, c.text, round(e, 3)))
# ---------- 4. every signed 2-decimal number in the four sections' bullets: is it a dashboard IR/correlation of that class (any window, class or product)?
num = re.compile(r"(?<![\d.])([+-]\d\.\d\d|0\.00)(?![\d%.])")
unmatched = {}
sec = None
for k, p in body:
    if k != "p": continue
    if p.style.name == "Heading 2": sec = p.text
    if sec in CLS and p.style.name == "List Bullet":
        cls = CLS[sec]; vals = set()
        for w in ("full", "p1", "p2", "p3", "y26"):
            for r in D["tabs"][cls]["windows"][w]: vals.add(round(r["ir"], 2))
        for pk in D["tabs"][cls]["pkeys"]:
            for s in D["products"][pk].values():
                for w in ("full", "p1", "p2", "p3", "y26"):
                    if w in s: vals.add(round(s[w]["ir"], 2))
        for row in D["corr"]["within"][cls]:
            for v in row: vals.add(round(v, 2))
        for m in num.finditer(p.text):
            v = float(m.group(1))
            if not any(abs(v - q) < 0.0101 for q in vals):
                unmatched.setdefault(sec, []).append((m.group(1), p.text[max(0, m.start() - 55):m.end() + 10].replace("\n", " ")))
print(json.dumps({k: (v if not isinstance(v, list) else v[:12]) for k, v in out.items()}, indent=1, default=str))
for s, l in unmatched.items():
    print("\n== numbers not found among dashboard IRs/correlations:", s, len(l))
    for a, b in l: print("   ", a, "|", b)
