"""US Power (standalone) facts: per-product nets of scripts/power/power_pipeline.py (tag 0930), the dashboard's own bucket construction (combine_cross_asset, then combine_returns), windows from 2017."""
import os, sys, json, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facts3 import *
from engine import combine_returns
from cross_asset_engine import combine_cross_asset

MEMBERS_P = ["PJM_Peak", "PJM_OffPeak", "ERCOT_Peak", "ERCOT_OffPeak", "MISO_Peak"]
LABEL_P = {"PJM_Peak": "PJM Peak", "PJM_OffPeak": "PJM OffPeak", "ERCOT_Peak": "ERCOT Peak", "ERCOT_OffPeak": "ERCOT OffPeak", "MISO_Peak": "MISO Peak"}
PW = {"full": ("2017-01-01", None), "p2": ("2017-01-01", "2021-12-31"), "p3": ("2022-01-01", None), "y26": ("2026-01-01", None)}
PJ = json.load(open(os.path.join(REPO, "Analysis", "_power_build", "power_tab_0930.json")))
NETS_P = pickle.load(open(os.path.join(REPO, "outputs", "power_0930", "power_nets.pkl"), "rb"))["nets"]


def stp(r, w="full"):
    s, e = PW[w]
    r = (r.loc[s:e] if e else r.loc[s:]).dropna()
    ret = (np.exp(252 * r.mean()) - 1) * 100; vol = np.expm1(r).std(ddof=1) * np.sqrt(252) * 100
    cum = np.exp(r.cumsum()); mdd = (cum / cum.cummax() - 1).min() * 100
    return dict(ret=ret, vol=vol, mdd=mdd, ir=ret / vol)


STY_P = {k: combine_cross_asset([NETS_P[p][k] for p in MEMBERS_P]) for k in SLEEVES}
_lst = list(STY_P.values())
EW_P = combine_returns(_lst, "equal_weight"); IV_P = combine_returns(_lst, "inverse_vol", vol_window=63)
ROWS_P = {**STY_P, "EW PORT": EW_P, "Inverse Vol": IV_P}
_c4 = [STY_P[k] for k in CORE]
EW4_P = combine_returns(_c4, "equal_weight"); IV4_P = combine_returns(_c4, "inverse_vol", vol_window=63)


def yl_p(r):
    r = r.loc["2017-01-01":].dropna(); return r.groupby(r.index.year).sum()


def lineP(s):
    return f"Return {R(s['ret'])}, Vol {V(s['vol'])}, Max Drawdown {M(s['mdd'])}, IR {I(s['ir'])}"
