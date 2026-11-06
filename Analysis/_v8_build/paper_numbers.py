import warnings; warnings.filterwarnings("ignore")
import facts, facts2, facts3
K5=["metals","petroleum","ngl","precious","agri"]
for m in (facts,facts2,facts3): m.KEYS5=K5
from facts3 import *
import datetime as dt
END="2026-09-30"
# --- Skewness IR by class and period
print("Skewness IR by class (full,p1,p2,p3):")
for v in K5: print(f"  {v:10s}",[round(st(v,'Skewness',w)['ir'],2) for w in ('full','p1','p2','p3')])
# --- share of days long
prods=[("metals",p) for p in PRODUCTS["metals"]]+[("energy",p) for p in PRODUCTS["petroleum"]]+[("ngl",p) for p in PRODUCTS["ngl"]]+[("precious",p) for p in PRODUCTS["precious"]]+[("agri",p) for p in PRODUCTS["agri"]]
print("n products",len(prods))
for w in ("p1","p2","p3","full"): print("avg long% all",w,round(np.mean([legs(a,p)[w]["long_pct"] for a,p in prods]),1))
for v in K5:
    a,ps=VARIANTS[v]; print(" class long%",v,[round(np.mean([legs(a,p)[w]["long_pct"] for p in ps]),1) for w in ("p1","p2","p3")])
# --- NGL 2020 episode
import importlib
for p in PRODUCTS["ngl"]:
    lp=importlib.import_module("ngl").load_f1_series_logret(p)["log_price"].dropna(); r=lp.diff(); sk=r.rolling(252).skew()
    sig=pd.Series(np.where(sk<0,1.0,np.where(sk>0,-1.0,0.0)),index=lp.index).where(sk.notna())
    s=sig.loc["2020-01-01":"2020-06-30"]; flips=s[s.diff().fillna(0)!=0]
    print(p,"signal on 2020-02-24:",s.loc[:"2020-02-24"].iloc[-1],"| flips:",[(i.strftime('%m-%d'),v) for i,v in flips.items()][:6])
# --- DBC correlations
bs=bystyle(False); b4=bystyle4(False)
print("by-signal strategy corr with DBC (five classes incl. Petroleum, 2012 to 30 Sep):")
for k in SER7: print("  ",k,round(bench_corr(bs[k],end=END)["Commodity Index"],2))
print("4-sleeve EW/IV vs DBC:",round(bench_corr(b4["EW PORT"],end=END)["Commodity Index"],2),round(bench_corr(b4["Inverse Vol"],end=END)["Commodity Index"],2))
print("5-sleeve EW/IV vs DBC:",round(bench_corr(bs["EW PORT"],end=END)["Commodity Index"],2),round(bench_corr(bs["Inverse Vol"],end=END)["Commodity Index"],2))
print("class Skewness sleeve vs DBC:")
for v in K5: print("  ",v,round(bench_corr(CS[v]["Skewness"].dropna(),end=END)["Commodity Index"],2))
print("EW/IV IR five-sleeve book:",round(stats(bs["EW PORT"])["ir"],2),round(stats(bs["Inverse Vol"])["ir"],2))
print("PEN not included; common start",bs.index[0].date(),"end",bs.index[-1].date())
# --- Skewness other corr within class (low correlation claim) petroleum etc
for v in K5:
    c=corr_within(v); print(v,"Skewness corr with other four:",[round(c.loc['Skewness',k],2) for k in ('Momentum','Carry','CarryMom','Value')])
