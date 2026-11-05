"""Checks of the UK Gas and Naphtha expiry calendars (2026-11-04). Run from the repo root:  python scripts/final_dashboard/check_new_calendars.py
 1 the calendar sheets in every price folder equal Bloomberg's workbook (data/Prices_1103/Expiry_Calendars_naphtha_UK_Gas.xlsx) on last trade and last delivery dates
 2 Bloomberg's last trade dates identify the day the Bloomberg generic series rolls: curve-shift statistic on the first data day after each date, against the neighbouring business days
 3 the engine's rolls and bridges: one roll and one bridge per contract, the bridge on the first data day after the last trade date
 4 the rule-derived dates (exchange rule on a UK business-day calendar) differ from Bloomberg's only where listed"""
import os, sys, warnings
warnings.filterwarnings("ignore")
os.environ.setdefault("RP_PRICES_DIR", "Prices_1029_merged")
sys.path[:0] = ["research", "research/configs", "scripts", "."]
import numpy as np, pandas as pd
import new_products as npd
fails = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)
    if not ok:
        fails.append(name)

# 1 files vs Bloomberg
for prod, sheet, fname, folders in (("UK Gas", npd.UKGAS_CAL_SHEET, "Emissions_Expiry_Calendars.xlsx", ("Prices_1029_merged", "Prices_0930")),
                                    ("Naphtha", npd.NAPHTHA_CAL_SHEET, "Naphtha_Expiry_Calendars.xlsx", ("Prices_1029_merged", "Prices_0930", "Prices_0924"))):
    b = npd.bloomberg_calendar(prod)
    for fo in folders:
        c = pd.read_excel(f"data/{fo}/{fname}", sheet_name=sheet)
        ok = (len(c) == len(b)) and (pd.to_datetime(c.LAST_TRADEABLE_DT).values == b.LAST_TRADEABLE_DT.values).all() and (pd.to_datetime(c.FUT_DLV_DT_LAST).values == b.FUT_DLV_DT_LAST.values).all()
        check(f"1. {prod}: {fo}/{fname} == Bloomberg workbook ({len(c)} contracts)", ok)

# 2 roll-day identification
def load(sheet):
    d = npd.read_drop(sheet); return d
def shift_stat(d, K=8):
    cols = [f"F{k}" for k in range(1, K + 1)]; X = np.log(d[cols].where(d[cols] > 0))
    num = sum((X[cols[k]] - X[cols[k + 1]].shift(1)).abs() for k in range(K - 1)); den = sum((X[cols[k]] - X[cols[k]].shift(1)).abs() for k in range(K - 1))
    return (num / den).replace([np.inf, -np.inf], np.nan)
bd = npd.business_days()
for prod, sheet in (("UK Gas", "UK Gas - Price"), ("Naphtha", "Naphtha - Price")):
    d = load(sheet); r = shift_stat(d); idx = d.index
    ltd = npd.bloomberg_calendar(prod).LAST_TRADEABLE_DT
    ltd = [l for l in ltd if l > idx[0] + pd.Timedelta(days=90) and l < idx[-1] - pd.Timedelta(days=5)]
    res = {}
    for lag in range(-3, 4):
        vals = []
        for l in ltd:
            l2 = bd[bd.get_loc(l) + lag] if l in bd else l + pd.Timedelta(days=lag)
            nd = idx[idx > l2]
            if len(nd): vals.append(r.get(nd[0], np.nan))
        res[lag] = float(pd.Series(vals).dropna().median())
    best = min(res, key=res.get)
    check(f"2. {prod}: Bloomberg last trade dates -> generic rolls on the next data day (median curve-shift statistic by lag: " + ", ".join(f"{k:+d}:{v:.2f}" for k, v in res.items()) + ")",
          best == 0, f"minimum at lag {best}; all-days median {r.median():.2f}")

# 3 engine rolls and bridges
import emissions as em, naphtha as nap
for prod, mod, name, sheetcal, folder_file in (("UK Gas", em, "UKGas", None, None), ("Naphtha", nap, "Naphtha", None, None)):
    raw = mod.load_f1_series_logret(name); idx = raw.index
    ltd = npd.bloomberg_calendar(prod).LAST_TRADEABLE_DT
    ltd = ltd[(ltd > idx[0]) & (ltd < idx[-1])]
    nxt = [idx[idx > l][0] for l in ltd]
    br = raw.index[raw.is_bridge_date.astype(bool)]
    exp_roll = []
    for l in npd.bloomberg_calendar(prod).LAST_TRADEABLE_DT:        # every contract whose last-trade month has a 5th trading day in the data (includes the one expiring at the data end)
        if l < idx[0]:
            continue
        mm = idx[(idx.year == l.year) & (idx.month == l.month)]
        if len(mm) >= 5: exp_roll.append(mm[4])
    ro = raw.index[raw.is_roll_date.astype(bool)]
    check(f"3. {prod}: bridge days == first data day after each Bloomberg last trade date ({len(br)} of {len(nxt)})", set(br) == set(nxt), f"missing {len(set(nxt) - set(br))}, extra {len(set(br) - set(nxt))}")
    check(f"3. {prod}: roll days == 5th trading day of each last-trade-date month ({len(ro)} of {len(exp_roll)})", set(ro) == set(exp_roll), f"missing {len(set(exp_roll) - set(ro))}, extra {len(set(ro) - set(exp_roll))}")

# 4 rule-derived vs Bloomberg
for prod, n_ok in (("UK Gas", 1), ("Naphtha", 2)):
    d = npd.compare_with_derived(prod)
    check(f"4. {prod}: rule-derived dates differ from Bloomberg on {len(d)} contract(s)", len(d) == n_ok, ", ".join(f"{y}-{m:02d}: Bloomberg {r.bloomberg:%Y-%m-%d} vs rule {r.derived:%Y-%m-%d}" for (y, m), r in d.iterrows()))
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
