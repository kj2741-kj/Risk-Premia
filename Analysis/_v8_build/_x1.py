import os; os.environ["CHK_SOFT"]="1"
from facts3 import *
v,a="petroleum","energy"; pr=VARIANTS[v][1]
R=lambda x:[round(float(i),3) for i in x]
for k in SLEEVES: print(k, round(st(v,k)["ir"],3), R(per(v,k)))
for k in ("EW PORT","Inverse Vol"): print(k, {x:round(float(y),3) for x,y in st(v,k).items()}, R(per(v,k)))
print("EW4",st4(v,"EW PORT")["ir"],st4(v,"Inverse Vol")["ir"])
print("EW4D",[round(stats(PORT4[v][0],w)["ir"],3) for w in ("p1","p2","p3")],"IV4D",[round(stats(PORT4[v][1],w)["ir"],3) for w in ("p1","p2","p3")])
for k in ("Carry","Momentum","CarryMom","Value","Skewness"): print(k,{p:round(pst(a,p,k)["ir"],3) for p in pr}, "p3",{p:round(pst(a,p,k,"p3")["ir"],3) for p in pr})
print("legs p3 long%",{p:round(legs(a,p)["p3"]["long_pct"],1) for p in pr}, "p1",{p:round(legs(a,p)["p1"]["long_pct"],1) for p in pr},{p:round(legs(a,p)["p1"]["long_pnl"],2) for p in pr})
ms=CS[v]["Momentum"].loc["2012-01-01":].dropna(); tot=ms.sum(); yl=yearly_log(ms)
print("mom shares", yl.loc[[2014,2015,2020,2021]].sum()/tot*100, yl.loc[2022]/tot*100, ms.loc["2026-01-01":].sum()/tot*100, yl.round(2).to_dict())
sk=CS[v]["Skewness"].loc["2012-01-01":].dropna(); ylx=yearly_log(sk); print("skew yrs",ylx.round(2).to_dict(), sk.sum())
print("slope p3 etc", {p:[round(slope_stats(a,p,"F1","F3")[w][0],3) for w in ("p1","p2","p3")] for p in pr})
cw=corr_within(v); print(cw.round(2))
print("metals gap", st("metals","Inverse Vol")["ir"]-st("metals","EW PORT")["ir"])
