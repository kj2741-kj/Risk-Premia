import os; os.environ["CHK_SOFT"]="1"
from facts3 import *
from text_cross8 import *
bs,bs4=book(); ew,iv=stats(bs["EW PORT"]),stats(bs["Inverse Vol"])
print("book ew",{k:round(v,3) for k,v in ew.items()},"iv",{k:round(v,3) for k,v in iv.items()})
print("ewP",[round(stats(bs["EW PORT"],w)["ir"],3) for w in W3],"ivP",[round(stats(bs["Inverse Vol"],w)["ir"],3) for w in W3])
ps=pair_stats()
for p in sorted(ps,key=lambda p:-p["ew"]["ir"]): print("%-28s corr %.2f ew %.3f iv %.3f ewp %s"%(p["name"],p["corr"],p["ew"]["ir"],p["iv"]["ir"],[round(x,2) for x in p["ewp"]]))
print("iv order",[ (p["name"],round(p["iv"]["ir"],3)) for p in sorted(ps,key=lambda p:-p["iv"]["ir"])[:5]])
bS=bench_corr(bs["Skewness"]); print({k:round(v,3) for k,v in bS.items()})
bE=bench_corr(bs["EW PORT"]); print({k:round(v,3) for k,v in bE.items()}); print({k:round(v,3) for k,v in bench_corr(bs4["EW PORT"]).items()})
sP={k:[round(stats(bs[k],w)["ir"],3) for w in W3] for k in SLEEVES}; print(sP)
print("beat book ew",[p["name"] for p in ps if p["ew"]["ir"]>ew["ir"]],"iv",[p["name"] for p in ps if p["iv"]["ir"]>iv["ir"]])
cx=corr_cross("EW PORT"); print(cx.round(2))
