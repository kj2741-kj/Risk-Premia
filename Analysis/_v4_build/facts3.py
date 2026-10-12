"""Cross-commodity facts: pair statistics, benchmark (ETF) correlations, four-sleeve versus five-sleeve books."""
from facts2 import *

_px = None


def etf():
    global _px
    if _px is None:
        _px = pd.read_csv(os.path.join(S, "etf_prices_1012.csv"), index_col=0, parse_dates=True)
    return _px


def bench_returns():
    px = etf()
    r = np.log(px).diff()
    out = pd.DataFrame({"Equity": r["SPY"], "Fixed Income": r["AGG"], "Commodity Index": r["DBC"], "Gold": r["GLD"],
                        "60/40 Portfolio": np.log1p(0.6 * px["SPY"].pct_change() + 0.4 * px["AGG"].pct_change())})
    return out


def bench_corr(s, start="2012-01-01", end="2026-09-23"):
    b = bench_returns()
    s = s.loc[start:end]
    return {c: float(pd.concat([s, b[c]], axis=1, keys=["s", "b"]).dropna().corr().iloc[0, 1]) for c in b.columns}


def bystyle4(exng=False):
    keys = KEYS5X if exng else KEYS5
    sdf = pd.DataFrame({k: ew_intersection([CS4[t][k].dropna() for t in keys]) for k in CORE}).dropna()
    sdf["EW PORT"] = sdf[CORE].mean(axis=1, skipna=False)
    sdf["Inverse Vol"] = inverse_vol(sdf[CORE])
    return sdf


def pair_stats(exng=False):
    """List of dicts in v3's pair order: name, EW/IV full stats, period IRs, EW PORT correlation."""
    out = []
    ew_cc = corr_cross("EW PORT", exng)
    names = {"metals": "Metals", "energy": "Energy", "energy_exng": "Energy (ex-NatGas)", "ngl": "NGL", "precious": "Precious Metals", "agri": "Agriculture"}
    for a, b in PAIR_ORDER:
        if exng:
            if "energy" not in (a, b): continue
            a = "energy_exng" if a == "energy" else a
            b = "energy_exng" if b == "energy" else b
        nm = f"{names[a]}-{names[b]}"
        e = pair_series(a, b, "EW"); i = pair_series(a, b, "IV")
        out.append(dict(a=a, b=b, name=nm, ew=stats(e), iv=stats(i), ewp=[stats(e, w)["ir"] for w in ("p1", "p2", "p3")],
                        ivp=[stats(i, w)["ir"] for w in ("p1", "p2", "p3")], corr=float(ew_cc.loc[a, b])))
    return out
