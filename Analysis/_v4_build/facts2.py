"""Extra facts: real yields against gold (FRED DFII10, downloaded 2026-10-12) and tenor-pair tables."""
from facts import *


def real_yield_stats():
    glp = importlib.import_module("precious").load_f1_series_logret("Gold")["log_price"]
    ry = pd.to_numeric(pd.read_csv(os.path.join(S, "dfii10.csv"), parse_dates=["observation_date"]).set_index("observation_date")["DFII10"], errors="coerce").dropna()
    out = {}
    for nm, (s, e) in {"full": ("2012-01-01", "2026-09-23"), "p1": ("2012-01-01", "2016-12-31"), "p2": ("2017-01-01", "2021-12-31"), "p3": ("2022-01-01", "2026-09-23")}.items():
        gw = glp.loc[s:e].resample("W-FRI").last().diff().dropna()
        rw = ry.loc[s:e].resample("W-FRI").last().diff().dropna()
        j = pd.concat([gw, rw], axis=1, keys=["g", "r"]).dropna()
        out[nm] = dict(corr=float(j.g.corr(j.r)), avg=float(ry.loc[s:e].mean()))
    return out


def skew_episode(a, p, start, end):
    """Log P&L (gross of costs) of the Skewness position of one product between two dates, plus its first long day after `start`."""
    lp = importlib.import_module(a).load_f1_series_logret(p)["log_price"]
    r = lp.diff(); pos = exec_shift(raw_signal_skewness(lp, 252), 1).fillna(0)
    c = (pos * r).loc[start:end].sum()
    after = pos.loc[start:]
    first_long = after[after > 0].index[0].date() if (after > 0).any() else None
    return float(c), first_long


if "tenor_table" not in globals():
    def tenor_table(v):
        a, prods = VARIANTS[v]
        cls = lambda key: ew_intersection([nets()[(a, p)][key] for p in prods])
        return {
            "Carry": {"prev": stats(cls("carry_single_prev"))["ir"], "short": stats(cls("carry_short"))["ir"], "long": stats(cls("carry_long"))["ir"], "two": st(v, "Carry")["ir"]},
            "CarryMom": {"prev": stats(cls("cm_single_prev"))["ir"], "short": stats(cls("cm_short"))["ir"], "long": stats(cls("cm_long"))["ir"], "two": st(v, "CarryMom")["ir"]},
        }

def slope_stats(a, p, near="F1", far="F13"):
    """Average carry slope (near - far) / near and the share of days with a positive slope (backwardation), by period, on the product's own price dates."""
    import importlib
    for q in ("research", os.path.join("research", "configs")):
        pth = os.path.join(REPO, q)
        if pth not in sys.path: sys.path.insert(0, pth)
    from engine import _carry_base
    s = _carry_base(importlib.import_module(a).load_curve(p), near, far)
    out = {}
    for w in ("p1", "p2", "p3"):
        x = s.loc[WINDOWS[w][0]:WINDOWS[w][1]] if WINDOWS[w][1] else s.loc[WINDOWS[w][0]:]
        out[w] = (100 * x.mean(), 100 * (x > 0).mean())
    return out
