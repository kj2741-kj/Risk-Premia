import sys, re, json, warnings
warnings.filterwarnings("ignore")
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
D = json.load(open(r"C:\Users\Kartavya\Desktop\NYU\Summer\Risk Premia\outputs\final_dashboard_0930\final_v3.json"))
d = docx.Document(sys.argv[1])
ROWS = []
def walk(o):
    if isinstance(o, dict):
        if {"ret","vol","mdd","ir"} <= set(o): ROWS.append((o["ret"],o["vol"],o["mdd"],o["ir"]))
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(D["tabs"]); walk(D["products"])
body=[]
for c in d.element.body:
    t=c.tag.split("}")[1]
    if t=="p": body.append(("p",Paragraph(c,d).text))
    elif t=="tbl": body.append(("t",Table(c,d)))
# statistic lines in Metals/Petroleum sections only
sec=None; lines=0; bad=[]
pat=re.compile(r"Return ([+-]?\d+\.\d)%, Vol (\d+\.\d)%, Max Drawdown (-?\d+\.\d)%, IR ([+-]?\d+\.\d\d|0\.00)")
for k,x in body:
    if k!="p": continue
    if x in ("Metals","Petroleum","Energy","Precious Metals","NGL","Agriculture","Correlation Analysis"): sec=x
    if sec in("Metals","Petroleum"):
        for m in pat.finditer(x):
            lines+=1; r,v,dd,ir=(float(g) for g in m.groups())
            if not any(abs(r-a)<.051 and abs(v-b)<.051 and abs(dd-c)<.051 and abs(ir-e)<.0051 for a,b,c,e in ROWS): bad.append(m.group(0))
print("stat lines in Metals+Petroleum:",lines,"not in dataset:",len(bad),bad)
NAME={"Momentum":"Momentum","Carry":"Carry","Carry-Momentum":"CarryMom","Value":"Value","Skewness":"Skewness","Equal Weight":"EW PORT","Inverse Vol":"Inverse Vol"}
W={"Full":"full","2012-16":"p1","2017-21":"p2","2022-26":"p3"}
cells=0; mism=[]; last=""
for k,x in body:
    if k=="p":
        if x.startswith("Table A"): last=x
        continue
    cap=last; last=""
    m=re.match(r"Table A\d+\. (Metals|Petroleum): (.+)",cap)
    if not m: continue
    key={"Metals":"metals","Petroleum":"petroleum"}[m.group(1)]; rows=[[c.text.strip() for c in r.cells] for r in x.rows]
    def chk(lbl,got,exp):
        global cells; cells+=1
        if abs(float(got)-exp)>0.0055: mism.append((cap[:30],lbl,got,round(exp,3)))
    if "by Period" in m.group(2):
        for r in rows[1:]:
            for (wl,wk),cell in zip(W.items(),r[1:]):
                row=next(z for z in D["tabs"][key]["windows"][wk] if z["name"]==NAME[r[0]]); chk(f"{r[0]} {wl}",cell,row["ir"])
    else:
        prods=[{"Heating Oil":"HeatingOil"}.get(p,p) for p in rows[0][1:]]; a="metals" if key=="metals" else "energy"
        for r in rows[1:]:
            for p,cell in zip(prods,r[1:]): chk(f"{r[0]} {p}",cell,D["products"][f"{a}|{p}"][NAME[r[0]]]["full"]["ir"])
print("tables cells compared:",cells,"mismatches:",len(mism),mism[:10])
