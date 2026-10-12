"""Single-pair (previous setup) vs two-pair comparison at asset-class level for Precious and Agriculture -> twopair_v2.json
Same data/roll rule as the rebuilt dashboard. Previous setup = Precious F1-F3, Agriculture F1-F2 (single pair)."""
import sys, json, pickle
from pathlib import Path
sys.path.insert(0,"research"); sys.path.insert(0,"research/configs"); sys.path.insert(0,"scripts")
import pandas as pd
from engine import combine_returns
from cross_asset_engine import combine_cross_asset
from run_regime_table import _metrics
from regimes import REPORT_START
from final_regimes import REGIMES
OUT=Path("outputs/final_dashboard")
nets,meta=pickle.load(open(OUT/"products_v2_nets.pkl","rb"))
P={"precious":["Gold","Silver","Platinum","Palladium"],"agri":["Corn","Wheat","Soybean","SoybeanOil","Coffee","Sugar"]}
W=[("full",REPORT_START,None)]+[(n.split("_")[0].lower(),s,e) for n,s,e in REGIMES]+[("y26","2026-01-01",None)]
f3=lambda d:{k:(None if pd.isna(v) else round(float(v),3)) for k,v in d.items()}
win=lambda rows:{w:{k:f3(_metrics(v.loc[s:e] if e else v.loc[s:])) for k,v in rows.items()} for w,s,e in W}
res={}
for a,prods in P.items():
    def ac(key): return combine_cross_asset([nets[(a,p)][key] for p in prods])
    legs={"Carry single (previous)":ac("carry_single_prev"),"Carry short F1-F2":ac("carry_short"),"Carry long":ac("carry_long"),"Carry two-pair":ac("Carry"),
          "CarryMom single (previous)":ac("cm_single_prev"),"CarryMom short F1-F2":ac("cm_short"),"CarryMom long":ac("cm_long"),"CarryMom two-pair":ac("CarryMom")}
    mom,val=ac("Momentum"),ac("Value")
    port={}
    for tag,(c,m) in {"single":("Carry single (previous)","CarryMom single (previous)"),"two":("Carry two-pair","CarryMom two-pair")}.items():
        lst=[mom,legs[c],legs[m],val]
        port[f"EW PORT {tag}"]=combine_returns(lst,"equal_weight"); port[f"Inverse Vol {tag}"]=combine_returns(lst,"inverse_vol",vol_window=63)
    res[a]=win({**legs,**port})
    print(a,{k:res[a]["full"][k]["ir"] for k in res[a]["full"]})
json.dump(res,open(OUT/"twopair_v2.json","w"))
