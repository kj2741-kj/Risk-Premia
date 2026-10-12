"""Full-precision facts for the v4 text. Every figure printed in the document comes from here (own recomputation from the
per-product net returns; Dimil's dataset is only the cross-check, see verify_independent.py)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from itertools import combinations
from rp import *

CORE = ["Momentum", "Carry", "CarryMom", "Value"]
SER7 = SLEEVES + ["EW PORT", "Inverse Vol"]
KEYS5 = ["metals", "energy", "ngl", "precious", "agri"]
KEYS5X = ["metals", "energy_exng", "ngl", "precious", "agri"]
CS = {v: class_sleeves(v) for v in VARIANTS}
CS4 = {v: class_sleeves(v, CORE) for v in VARIANTS}
PORT = {v: class_portfolios(v) for v in VARIANTS}
PORT4 = {v: class_portfolios(v, CORE) for v in VARIANTS}


def series(v, k):
    if k == "EW PORT": return PORT[v][0]
    if k == "Inverse Vol": return PORT[v][1]
    return CS[v][k]


def st(v, k, w="full"):
    return stats(series(v, k), w)


def st4(v, k, w="full"):
    if k == "EW PORT": return stats(PORT4[v][0], w)
    if k == "Inverse Vol": return stats(PORT4[v][1], w)
    return stats(CS4[v][k], w)


def pst(a, p, k, w="full"):
    return stats(nets()[(a, p)][k], w)


# ---------- formatting (v3 convention: ASCII hyphen as minus, signed returns and IRs)
def _z(x, d):
    return abs(round(x, d)) == 0


def R(x):  return f"{0.0:.1f}%" if _z(x, 1) else f"{x:+.1f}%"
def V(x):  return f"{x:.1f}%"
def M(x):  return f"{x:.1f}%"
def I(x):  return "0.00" if _z(x, 2) else f"{x:+.2f}"
def N(x, d=2): return "0.00" if _z(x, d) else f"{x:+.{d}f}"
def U(x, d=2): return f"{x:.{d}f}"          # unsigned


def line(s):
    return f"Return {R(s['ret'])}, Vol {V(s['vol'])}, Max Drawdown {M(s['mdd'])}, IR {I(s['ir'])}"


def per(v, k):
    return [st(v, k, w)["ir"] for w in ("p1", "p2", "p3")]


def per3(v, k):
    a = per(v, k); return f"P1 {I(a[0])}, P2 {I(a[1])}, P3 {I(a[2])}"


def pper(a, p, k):
    return [pst(a, p, k, w)["ir"] for w in ("p1", "p2", "p3")]


def chk(cond, msg):
    if not cond:
        raise AssertionError("CLAIM FAILED: " + msg)


# ---------- correlations
def corr_within(v):
    df = pd.concat([CS[v], PORT[v][0].rename("EW PORT"), PORT[v][1].rename("Inverse Vol")], axis=1).loc["2012-01-01":].dropna()
    return df.corr()


_style_cache = {}
def bystyle(exng=False):
    if exng in _style_cache: return _style_cache[exng]
    keys = KEYS5X if exng else KEYS5
    sdf = pd.DataFrame({k: ew_intersection([CS[t][k].dropna() for t in keys]) for k in SLEEVES}).dropna()
    sdf["EW PORT"] = sdf[SLEEVES].mean(axis=1, skipna=False)
    sdf["Inverse Vol"] = inverse_vol(sdf[SLEEVES])
    _style_cache[exng] = sdf
    return sdf


def corr_cross(k, exng=False):
    keys = KEYS5X if exng else KEYS5
    ser = [series(t, k).dropna() for t in keys]
    cum = [s.cumsum() for s in ser]
    idx = cum[0].index
    for c in cum[1:]: idx = idx.intersection(c.index)
    idx = idx.sort_values()
    al = pd.DataFrame({t: c.reindex(idx).diff() for t, c in zip(keys, cum)}).loc["2012-01-01":].dropna()
    return al.corr()


def pair_series(a, b, meth):
    ix = 0 if meth == "EW" else 1
    pa, pb = PORT[a][ix], PORT[b][ix]
    cl = [pa.dropna().cumsum(), pb.dropna().cumsum()]
    idx = cl[0].index.intersection(cl[1].index).sort_values()
    al = pd.DataFrame({a: cl[0].reindex(idx).diff(), b: cl[1].reindex(idx).diff()})
    return al.mean(axis=1, skipna=False) if meth == "EW" else inverse_vol(al)


PAIR_ORDER = [("metals", "energy"), ("metals", "precious"), ("metals", "ngl"), ("metals", "agri"), ("energy", "precious"),
              ("energy", "ngl"), ("energy", "agri"), ("precious", "ngl"), ("precious", "agri"), ("ngl", "agri")]
SHORT = {"metals": "Metals", "energy": "Energy", "energy_exng": "Energy ex-NatGas", "ngl": "NGL", "precious": "Precious Metals", "agri": "Agriculture"}


def combined_book(exng=False):
    keys = KEYS5X if exng else KEYS5
    out = {}
    for s_stage in ("EW", "IV"):
        ac = {t: PORT[t][0 if s_stage == "EW" else 1].dropna() for t in keys}
        cum = [ac[t].cumsum() for t in keys]
        idx = cum[0].index
        for c in cum[1:]: idx = idx.intersection(c.index)
        idx = idx.sort_values()
        al = pd.DataFrame({t: c.reindex(idx).diff() for t, c in zip(keys, cum)})
        out[(s_stage, "EW")] = al.mean(axis=1, skipna=False)
        out[(s_stage, "IV")] = inverse_vol(al)
    return out


# ---------- Skewness legs and positions
import importlib
for p in ("", "scripts", "research", os.path.join("research", "configs")):
    sys.path.insert(0, os.path.join(REPO, p))
from engine import raw_signal_skewness, exec_shift

_legs = {}
def legs(a, p):
    if (a, p) in _legs: return _legs[(a, p)]
    lp = importlib.import_module(a).load_f1_series_logret(p)["log_price"]
    r = lp.diff(); pos = exec_shift(raw_signal_skewness(lp, 252), 1).fillna(0)
    c = (pos * r).loc["2012-01-01":]; pos = pos.loc["2012-01-01":]
    out = {}
    for nm, (s, e) in {"p1": ("2012-01-01", "2016-12-31"), "p2": ("2017-01-01", "2021-12-31"), "p3": ("2022-01-01", "2026-12-31"), "full": ("2012-01-01", "2026-12-31")}.items():
        pp, cc = pos.loc[s:e], c.loc[s:e]
        out[nm] = dict(long_pct=float((pp > 0).mean() * 100), long_pnl=float(cc[pp > 0].sum()), short_pnl=float(cc[pp < 0].sum()))
    _legs[(a, p)] = out
    return out


def class_long_pct(v, w="full"):
    a, prods = VARIANTS[v]
    return float(np.mean([legs(a, p)[w]["long_pct"] for p in prods]))


# ---------- single-pair versus two-pair Carry (Precious Metals and Agriculture)
def tenor_table(v):
    a, prods = VARIANTS[v]
    def cls(key):
        return ew_intersection([nets()[(a, p)][key] for p in prods])
    out = {
        "Carry": {"prev": stats(cls("carry_single_prev"))["ir"], "short": stats(cls("carry_short"))["ir"], "long": stats(cls("carry_long"))["ir"], "two": st(v, "Carry")["ir"]},
        "CarryMom": {"prev": stats(cls("cm_single_prev"))["ir"], "short": stats(cls("cm_short"))["ir"], "long": stats(cls("cm_long"))["ir"], "two": st(v, "CarryMom")["ir"]},
    }
    return out
