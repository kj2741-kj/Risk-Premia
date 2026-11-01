"""NGL label verification: 24-Sep NGL sheets vs EIA Mont Belvieu propane spot (FRED DPROPANEMBTX) and published ethane/propane/butane moves.
Needs the FRED csv downloaded to %TEMP%/fred_propane.csv (https://fred.stlouisfed.org/graph/fredgraph.csv?id=DPROPANEMBTX)."""
import pandas as pd, numpy as np, os
sp=pd.read_csv(os.environ["TEMP"]+"/fred_propane.csv",parse_dates=["observation_date"]).set_index("observation_date")["DPROPANEMBTX"].replace(".",np.nan).astype(float).dropna()
F="data/Prices_0924/NGL_Futures_Updated.xlsx"
S={"CAP":"Propane Argus Far East C3","BAP":"Butane Argus C4","DAE":"Ethane Argus","IBD":"Isobutane Argus"}
for r,sh in S.items():
    x=pd.read_excel(F,sheet_name=sh,header=None,skiprows=2); x=x.set_index(pd.to_datetime(x[0],errors="coerce")).drop(columns=0); f2=x[x.index.notna()].astype(float)[2].dropna()
    j=pd.concat([f2,sp],axis=1,join="inner").dropna().loc["2010":]; j.columns=["sw","sp"]
    print(r,sh,"| median swap/spot %.3f | level corr %.3f | 5d change corr %.3f | 2012 vs 2011 avg %.1f%%"%((j.sw/j.sp).median(),j.corr().iloc[0,1],np.log(j).diff(5).corr().iloc[0,1],(f2.loc['2012'].mean()/f2.loc['2011'].mean()-1)*100))
