"""Roll / expiry alignment checks for the US Power bucket (2026-11-04). Run from the repo root: python scripts/power/power_validate.py
(1) every roll falls on the 5th trading day of the contract's last-trade-date month, (2) every bridge on the trading day after the last trade date,
(3) data-based test: does the generic F1 switch contract the day after the last trade date? (4) no roll fallbacks."""
import os, sys
os.environ.setdefault("RP_PRICES_DIR", "Prices_0930")
sys.path[:0] = ["research", "research/configs", "scripts"]
import numpy as np, pandas as pd
import power as pw
import rolling_continuous as rc

rows = []
for p in pw.PRODUCTS:
    raw = pw.load_f1_series_logret(p).loc[:"2026-09-30"]
    cal = rc.load_metal_calendar(pw.CALENDAR_FILE, pw.METAL_CODES[p])
    idx = raw.index; pos = {t: i for i, t in enumerate(idx)}
    ltds = [pd.Timestamp(d).normalize() for d in cal["roll_date"] if idx[0] <= pd.Timestamp(d) <= idx[-1]]
    roll_days = list(idx[raw["is_roll_date"].astype(bool)]); bridge_days = list(idx[raw["is_bridge_date"].astype(bool)])
    ok_roll = ok_bridge = n = 0
    for l in ltds:
        if l not in pos: continue
        i = pos[l]; m = idx[(idx.year == l.year) & (idx.month == l.month)]
        fifth = m[4] if len(m) >= 5 else m[-1]
        n += 1
        ok_roll += fifth in roll_days
        ok_bridge += (i + 1 < len(idx) and idx[i + 1] in bridge_days)
    # data test: F1 on the day after the LTD sits at the old F2 (day-after switch) rather than the old F1
    px = pw.load_curve(p).loc[:"2026-09-30"]
    best = {"before": 0, "LTD": 0, "after": 0, "n": 0}
    for l in ltds:
        if l not in pos or pos[l] < 3 or pos[l] + 3 >= len(idx): continue
        i = pos[l]; errs = {}
        for off in range(-2, 4):   # candidate switch day = LTD + off: F1(day) vs F2(day-1)
            d = idx[i + off]; e = abs(np.log(px["F1"].get(d) / px["F2"].get(idx[i + off - 1])))
            errs[off] = e
        if any(np.isnan(v) for v in errs.values()): continue
        b = min(errs, key=errs.get); best["n"] += 1
        best["after" if b == 1 else ("LTD" if b == 0 else "before")] += (b in (1, 0)) or (b < 0)
    rows.append(dict(product=p, contracts_in_sample=n, rolls=len(roll_days), bridges=len(bridge_days),
                     roll_on_5th_TD_of_expiry_month=f"{ok_roll}/{n}", bridge_day_after_LTD=f"{ok_bridge}/{n}",
                     splice_error_minimal_day_after_LTD=f"{best['after']}/{best['n']}"))
print(pd.DataFrame(rows).to_string(index=False))
print("roll fallbacks:", rc.ROLL_FALLBACK_COUNT["n"])
