"""Audit of Risk Premia Analysis v8 against the 0930 research dashboard dataset (outputs/final_dashboard_0930/final_v3.json). Reads the finished docx only.
Usage: python audit_v8.py "<path to docx>" """
import sys, re, json, warnings
warnings.filterwarnings("ignore")
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
D = json.load(open(r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia\outputs\final_dashboard_0930\final_v3.json"))
d = docx.Document(sys.argv[1])
BK = D["meta"]["keys"]                      # metals, petroleum, pen, ngl, precious, agri, softs
LAB = {"Metals": "metals", "Petroleum": "petroleum", "Gas and Emissions": "pen", "NGL": "ngl", "Precious Metals": "precious", "Agriculture": "agri", "Softs": "softs"}
fails = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)
    if not ok: fails.append(name)

body = []
for c in d.element.body:
    t = c.tag.split("}")[1]
    if t == "p": body.append(("p", Paragraph(c, d).text, Paragraph(c, d).style.name))
    elif t == "tbl": body.append(("t", Table(c, d), None))

# A. every 'Return, Vol, Max Drawdown, IR' line of the text is a row of the dataset
ROWS = []
def walk(o):
    if isinstance(o, dict):
        if {"ret", "vol", "mdd", "ir"} <= set(o): ROWS.append((o["ret"], o["vol"], o["mdd"], o["ir"]))
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
for k in ("tabs", "products", "combined", "bystyle", "crosspair"): walk(D[k])
PJ = json.load(open(r"C:/Users/Kartavya/Desktop/NYU/Summer/Risk Premia/Analysis/_power_build/power_tab_0930.json"))
walk(PJ["tab"]); walk(PJ["products"])
pat = re.compile(r"Return ([+-]?\d+\.\d)%, Vol (\d+\.\d)%, Max Drawdown (-?\d+\.\d)%, IR ([+-]?\d+\.\d\d|0\.00)")
lines = 0; bad = []
for k, x, _ in body:
    if k != "p": continue
    for m in pat.finditer(x):
        lines += 1; r, v, dd, ir = (float(g) for g in m.groups())
        if not any(abs(r - a) < .051 and abs(v - b) < .051 and abs(dd - c) < .051 and abs(ir - e) < .0051 for a, b, c, e in ROWS): bad.append(m.group(0))
check(f"A. {lines} 'Return, Vol, Max Drawdown, IR' lines of the text are rows of the dataset", not bad and lines > 40, f"{len(bad)} not found: {bad[:3]}")

# B. appendix tables of the seven buckets
NAME = {"Momentum": "Momentum", "Carry": "Carry", "Carry-Momentum": "CarryMom", "Value": "Value", "Skewness": "Skewness", "Equal Weight": "EW PORT", "Inverse Vol": "Inverse Vol"}
W = {"Full": "full", "2012-16": "p1", "2017-21": "p2", "2022-26": "p3"}
PN = {"Heating Oil": "HeatingOil", "Soybean Oil": "SoybeanOil", "Henry Hub": "NatGas", "UK Gas": "UKGas", "Live Cattle": "LiveCattle", "Natural Gasoline": "NatGasoline"}
cells = 0; mism = []; last = ""
def cmp(tag, got, exp):
    global cells; cells += 1
    if abs(float(got) - exp) > 0.0055: mism.append((tag, got, round(exp, 3)))
for k, x, _ in body:
    if k == "p":
        if x.startswith("Table A"): last = x
        continue
    cap = last; last = ""
    m = re.match(r"Table A\d+\. (Metals|Petroleum|Gas and Emissions|Precious Metals|NGL|Agriculture|Softs): (.+)", cap)
    if not m: continue
    b = LAB[m.group(1)]; rows = [[c.text.strip() for c in r.cells] for r in x.rows]
    if "by Period" in m.group(2):
        for r in rows[1:]:
            for (wl, wk), cell in zip(W.items(), r[1:]):
                row = next(z for z in D["tabs"][b]["windows"][wk] if z["name"] == NAME[r[0]]); cmp(f"{cap[:24]} {r[0]} {wl}", cell, row["ir"])
    elif "Tenor" in m.group(2): continue
    else:
        keymap = dict(zip(D["tabs"][b]["products"], D["tabs"][b]["pkeys"]))
        prods = [PN.get(p, p) for p in rows[0][1:]]
        check(f"B. {cap[:22]} lists the products of the bucket", prods == D["tabs"][b]["products"], f"{prods}")
        for r in rows[1:]:
            for p, cell in zip(prods, r[1:]): cmp(f"{cap[:22]} {r[0]} {p}", cell, D["products"][keymap[p]][NAME[r[0]]]["full"]["ir"])
check(f"B. {cells} cells of the bucket appendix tables equal the dataset", not mism and cells == 341, f"{len(mism)}: {mism[:4]}")      # 7 buckets x 28 period cells + 29 products x 5 sleeves (298 for six buckets and 26 products)

# C. cross-commodity tables
def table_after(prefix):
    for i, (k, x, _) in enumerate(body):
        if k == "p" and x.startswith(prefix):
            t = body[i + 1][1]; return [[c.text.strip() for c in r.cells] for r in t.rows]
    raise KeyError(prefix)
def table_after_kw(kw):
    for i, (k, x, _) in enumerate(body):
        if k == "p" and re.match(r"Table A\d+\. ", x) and kw in x:
            return [[c.text.strip() for c in r.cells] for r in body[i + 1][1].rows]
    raise KeyError(kw)
rows = table_after_kw("Cross-Commodity Portfolio: Strategy Information")
mm = 0; n = 0
for r in rows[1:]:
    for (wl, wk), cell in zip(W.items(), r[1:]):
        row = next(z for z in D["bystyle"]["windows"][wk] if z["name"] == NAME[r[0]]); n += 1; mm += abs(float(cell) - row["ir"]) > 0.0055
check(f"C. cross-commodity strategies by period table == dataset ({n} cells)", mm == 0)
rows = table_after_kw("Cross-Commodity Portfolio: Construction Information")
mm = 0; n = 0
for r in rows[1:3]:
    for (wl, wk), cell in zip(W.items(), r[1:]):
        row = next(z for z in D["bystyle"]["windows"][wk] if z["name"] == NAME[r[0]]); n += 1; mm += abs(float(cell) - row["ir"]) > 0.0055
check(f"C. cross-commodity construction table, Equal Weight and Inverse Vol rows == dataset ({n} cells)", mm == 0)
rows = table_after_kw("Cross-Pair Portfolio: Full-Sample")
mm = 0
_nm = lambda n: n.replace(" - ", "-").replace("Precious", "Precious Metals")
EWd = {_nm(z["name"]): z["ir"] for z in D["crosspair"]["EW"]["full"]}; IVd = {_nm(z["name"]): z["ir"] for z in D["crosspair"]["Inverse Vol"]["full"]}
for r in rows[1:]:
    mm += abs(float(r[1]) - EWd[r[0]]) > 0.0055 or abs(float(r[2]) - IVd[r[0]]) > 0.0055
check(f"C. twenty-one-pair table == dataset ({len(rows) - 1} pairs, both constructions)", mm == 0 and len(rows) == 22)
# correlation section table: pair, EW PORT correlation, IRs
corr_tab = None
for i, (k, x, _) in enumerate(body):
    if k == "t" and [c.text for c in x.rows[0].cells][:2] == ["Pair", "EW PORT correlation"]: corr_tab = [[c.text.strip() for c in r.cells] for r in x.rows]
M = D["corr"]["cross"]["EW PORT"]; idx = {b: i for i, b in enumerate(BK)}
SHORT = {"Metals": "metals", "Petroleum": "petroleum", "Gas and Emissions": "pen", "NGL": "ngl", "Precious Metals": "precious", "Agriculture": "agri", "Softs": "softs"}
mm = 0
for r in corr_tab[1:]:
    a, b = None, None
    for la in SHORT:
        if r[0].startswith(la + "-") and r[0][len(la) + 1:] in SHORT: a, b = SHORT[la], SHORT[r[0][len(la) + 1:]]
    assert a, r[0]
    mm += abs(float(r[1]) - M[idx[a]][idx[b]]) > 0.0055 or abs(float(r[2]) - EWd[r[0]]) > 0.0055 or abs(float(r[3]) - IVd[r[0]]) > 0.0055
check(f"C. correlation-section pair table (EW PORT correlation and both IRs) == dataset ({len(corr_tab) - 1} pairs)", mm == 0 and len(corr_tab) == 22)
# D. Skewness correlations within bucket (Table A27)
rows = table_after_kw("Skewness: Correlation with the Other Sleeves")
order = ["Momentum", "Carry", "CarryMom", "Value", "EW PORT"]; R = D["corr"]["rows"]
mm = 0
for r in rows[1:]:
    b = LAB[r[0]]; mat = D["corr"]["within"][b]
    for nm, cell in zip(order, r[1:]): mm += abs(float(cell) - mat[R.index("Skewness")][R.index(nm)]) > 0.0055
check(f"D. Skewness correlation table correlations (seven buckets) == dataset ({(len(rows) - 1) * 5} cells)", mm == 0)
# E. no stale wording, no unnumbered captions
text = "\n".join(x for k, x, _ in body if k == "p")
logt = text[text.index("Appendix: Verification Log"):]
main = text[:text.index("Appendix: Verification Log")]
stale = [s for s in ("Power, Emissions", "23 September", "v5 basis", "Energy-NGL", "ten asset", "five asset", "Table A?", "Figure A?", "Figure ?", "PLACEHOLDER", "five-class", "Energy including", "all six buckets", "six bucket portfolios", "six-bucket", "six products", "fifteen", "Soybean Oil, Coffee") if s in main]
check("E. no stale wording in the main text and appendices", not stale, str(stale))
check("E. every caption is numbered", "A?." not in text and "Figure ?" not in text)
caps = re.findall(r"^(Table A|Figure A|Figure )(\d+)\.", text, re.M)
for kind in ("Table A", "Figure A", "Figure "):
    nums = [int(n) for kd, n in caps if kd == kind]
    check(f"E. {kind.strip()} captions run 1..{len(nums)} in order", nums == list(range(1, len(nums) + 1)))
# G. independent recomputation of the class-level and cross-commodity numbers from the per-product net returns (separate code path from the dataset)
sys.path.insert(0, "C:/Users/Kartavya/Desktop/NYU/Summer/Risk Premia/Analysis/_v8_build")
from facts3 import *
W4k = ("full", "p1", "p2", "p3"); bad_ = 0; n_ = 0
for b in BUCKETS:
    cs = class_sleeves(b); ew, iv = class_portfolios(b)
    ser = {**{k: cs[k] for k in SLEEVES}, "EW PORT": ew, "Inverse Vol": iv}
    for row_i, row in enumerate(D["tabs"][b]["windows"]["full"]):
        for w in W4k:
            n_ += 1; bad_ += abs(D["tabs"][b]["windows"][w][row_i]["ir"] - stats(ser[row["name"]], w)["ir"]) > 0.0011
check(f"G. class statistics of all seven buckets recomputed from the product returns equal the dataset ({n_} cells)", bad_ == 0, f"{bad_} differ")
bs = bystyle(); bad_ = 0; n_ = 0
for row_i, row in enumerate(D["bystyle"]["windows"]["full"]):
    for w in W4k:
        n_ += 1; bad_ += abs(D["bystyle"]["windows"][w][row_i]["ir"] - stats(bs[row["name"]], w)["ir"]) > 0.0011
cb = combined_book(); kk = [("EW", "EW"), ("EW", "IV"), ("IV", "EW"), ("IV", "IV")]
for row_i, key in enumerate(kk):
    for w in W4k:
        n_ += 1; bad_ += abs(D["combined"]["windows"][w][row_i]["ir"] - stats(cb[key], w)["ir"]) > 0.0011
check(f"G. cross-commodity by-style and two-stage books recomputed equal the dataset ({n_} cells)", bad_ == 0, f"{bad_} differ")
ps = pair_stats(); bad_ = 0
for p_ in ps:
    nm = (SHORT[p_["a"]] + " - " + SHORT[p_["b"]]).replace("Precious Metals", "Precious")
    e = next(z for z in D["crosspair"]["EW"]["full"] if z["name"] == nm); i_ = next(z for z in D["crosspair"]["Inverse Vol"]["full"] if z["name"] == nm)
    bad_ += abs(e["ir"] - p_["ew"]["ir"]) > 0.0011 or abs(i_["ir"] - p_["iv"]["ir"]) > 0.0011
check("G. twenty-one pair series recomputed equal the dataset (both constructions)", bad_ == 0 and len(ps) == 21, f"{bad_} differ")
mat = D["corr"]["cross"]["EW PORT"]; ix = {b: i for i, b in enumerate(BK)}; cc = corr_cross("EW PORT")
check("G. EW PORT cross-bucket correlation matrix recomputed equals the dataset", max(abs(mat[ix[a]][ix[b]] - cc.loc[a, b]) for a in BK for b in BK) < 0.0011)

# H. US Power (standalone) tables against the dashboard's Power tab, and independent recomputation
PWK = {"Full": "full", "2017-21": "p2", "2022-26": "p3"}
cells_p = 0; mm_p = []
for i, (k, x, _) in enumerate(body):
    if k == "p" and re.match(r"Table A\d+\. US Power \(Standalone\): ", x):
        rows_ = [[c.text.strip() for c in r.cells] for r in body[i + 1][1].rows]
        if "Strategy Information" in x or "Portfolio Construction" in x:
            assert rows_[0][1:] == list(PWK), rows_[0]
            for r in rows_[1:]:
                for wl, cell in zip(PWK, r[1:]):
                    row = next(z for z in PJ["tab"]["windows"][PWK[wl]] if z["name"] == NAME[r[0]]); cells_p += 1; mm_p.append((x[:30], r[0], wl)) if abs(float(cell) - row["ir"]) > 0.0055 else None
        else:
            labs = {"PJM Peak": "power|PJM_Peak", "PJM OffPeak": "power|PJM_OffPeak", "ERCOT Peak": "power|ERCOT_Peak", "ERCOT OffPeak": "power|ERCOT_OffPeak", "MISO Peak": "power|MISO_Peak"}
            check("H. Power individual-product table lists the five series", [labs[h_] for h_ in rows_[0][1:]] == PJ["tab"]["pkeys"])
            for r in rows_[1:]:
                for h_, cell in zip(rows_[0][1:], r[1:]):
                    cells_p += 1; mm_p.append((r[0], h_)) if abs(float(cell) - PJ["products"][labs[h_]][NAME[r[0]]]["full"]["ir"]) > 0.0055 else None
check(f"H. {cells_p} cells of the three US Power appendix tables equal the dashboard's Power tab", not mm_p and cells_p == 15 + 6 + 25, f"{mm_p[:3]} {cells_p}")
sys.path.insert(0, "C:/Users/Kartavya/Desktop/NYU/Summer/Risk Premia/Analysis/_v8_build")
from power_facts import *
bad_ = 0; n_ = 0
for ri, row in enumerate(PJ["tab"]["windows"]["full"]):
    for w in ("full", "p2", "p3", "y26"):
        h_ = PJ["tab"]["windows"][w][ri]; m_ = stp(ROWS_P[row["name"]], w)
        for kk in ("ir", "ret", "vol", "mdd"): n_ += 1; bad_ += abs(h_[kk] - m_[kk]) > 0.0011
check(f"H. US Power bucket statistics recomputed from the product returns equal the dashboard's Power tab ({n_} values)", bad_ == 0, f"{bad_} differ")
# I. liquidity table against the two liquidity result files
import pandas as pd
lq = pd.read_csv("C:/Users/Kartavya/Desktop/NYU/Summer/Risk Premia/Analysis/Liquidity_Cal2025_results.csv").set_index("product")
pq = pd.read_csv("C:/Users/Kartavya/Desktop/NYU/Summer/Risk Premia/Analysis/Power_Liquidity_Cal2025_results.csv").set_index("product").rename(columns={"price_usd_mwh": "price_usd_unit", "mult_mwh": "mult"})
LQ = pd.concat([lq, pq[[c for c in lq.columns if c in pq.columns]]])
NMAP = {"Henry Hub (Nat Gas)": "NatGas", "UK Gas (NBP)": "UKGas", "Singapore Gasoil\u2020": "SingaporeGasoil", "Heating Oil": "HeatingOil", "Soybean Oil": "SoybeanOil", "Live Cattle": "LiveCattle", "Natural Gasoline": "NatGasoline", "MISO OffPeak\u2021": "MISO_OffPeak",
        "PJM Peak": "PJM_Peak", "PJM OffPeak": "PJM_OffPeak", "ERCOT Peak": "ERCOT_Peak", "ERCOT OffPeak": "ERCOT_OffPeak", "MISO Peak": "MISO_Peak"}
liq_rows = None
for i, (k, x, _) in enumerate(body):
    if k == "p" and re.match(r"Table A\d+\. Dollar Risk Turnover by Product", x): liq_rows = [[c.text.strip() for c in r.cells] for r in body[i + 1][1].rows]
prow = [r for r in liq_rows[1:] if r[1].startswith("F1")]
keys_ = [NMAP.get(r[0].rstrip("*"), r[0].rstrip("*")) if r[0].rstrip("*") in NMAP else NMAP.get(r[0], r[0].rstrip("*")) for r in prow]
rk = {p: i + 1 for i, p in enumerate(sorted(keys_, key=lambda q: -LQ.loc[q, "x_strip"]))}
badl = 0
for r, p in zip(prow, keys_):
    c_ = LQ.loc[p]; num = lambda t: float(t.replace(",", "").replace("%", ""))
    _b = badl
    badl += abs(num(r[2]) - round(c_["adv_strip"])) > 0.5 or abs(num(r[7]) - c_["x_strip"]) > 0.5 * 10 ** -(len(r[7].split(".")[1]) if "." in r[7] else 0) + 1e-9 or abs(num(r[8]) - c_["L_strip"]) > 0.5 * 10 ** -(len(r[8].split(".")[1]) if "." in r[8] else 0) + 1e-9 or int(r[9]) != rk[p] or abs(num(r[10]) - round(c_["share_days_print"] * 100)) > 0.5 or abs(num(r[4]) - c_["sigma"] * 100) > 0.0051 or abs(num(r[5]) - c_["mult"]) > 0.51
    if badl > _b: print("   liquidity row differs:", r, dict(adv=round(c_["adv_strip"]), x=round(c_["x_strip"], 4), L=round(c_["L_strip"], 4), rank=rk[p], days=round(c_["share_days_print"] * 100), sigma=round(c_["sigma"] * 100, 3), mult=c_["mult"]))
check(f"I. liquidity table: {len(prow)} products, ADV, x, L, rank, days traded, sigma and multiplier equal the two result files", badl == 0 and len(prow) == 36, f"{badl} differ")
# J. text hygiene of the whole document
allt = [x for k, x, _ in body if k == "p"] + [c.text for k, x, _ in body if k == "t" for r in x.rows for c in r.cells]
iss = [t[:80] for t in allt if "  " in t.replace("\u00a0", " ").strip() and not t.startswith("\t") and not t.startswith("\u2022")]
bal = [t[:80] for t in allt if t.count("(") != t.count(")")]
punc = [t[:80] for t in allt if re.search(r" ,|(?<!\.)\.\.(?!\.)|,,| \.(?![\d.])|\(\s|\s\)", t)]
check("J. no double spaces, unbalanced brackets or stray punctuation in the document", not (iss or bal or punc), f"spaces {iss[:2]} brackets {bal[:2]} punct {punc[:2]}")
# F. 29 products named in the seven buckets (26 in six buckets before the 10 November 2026 split and Natural Gasoline)
check("F. the dataset has 29 products in seven buckets", sum(len(D["tabs"][b]["products"]) for b in BK) == 29)
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
