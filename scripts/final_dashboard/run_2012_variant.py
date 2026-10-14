"""2012-start variant of the Final Research Dashboard (2026-10-12): three periods only, kept separate from the original research.

Reads the same per-product sleeve returns (outputs/final_dashboard/products_v2_nets.pkl, so signals, rolls, costs and warm-up are exactly the
original ones) and re-cuts the reporting window: full sample 2012-01-01 to date, P1 2012-2016, P2 2017-2021, P3 2022 onwards (no 2026 YTD column).
Writes outputs/final_dashboard_2012/*.json and Analysis/Final_Research_Dashboard_2012.html. Does not touch research/regimes.py or any original output.
The only change to the sleeves: Value needs 504 observations (two years) of F3 instead of 630 before its signal starts, for every product, so that
NGL Value and the NGL Inverse Vol series are defined before the 2012 reporting start. Run from the repo root after compute_products.py: python scripts/final_dashboard/run_2012_variant.py"""
import sys
from pathlib import Path

D = Path("scripts/final_dashboard")
import os
_MODE = os.environ.get("ZSUM", "")   # "1": sum raw pair values; "2": Carry-Momentum slope changes standardised before summing
ZSUM, STD, PM, RAWC = _MODE in ("2", "3", "4", "5"), _MODE == "2", _MODE == "3", _MODE == "4"   # since 2026-10-13 the DEFAULT (no ZSUM) already uses summed z-scores / summed raw slope changes (compute_products.py); modes 2-5 are the sandbox alternatives
ZDIFF = _MODE == "5"   # "5": Carry-Momentum = sum over pairs of (z-score today - z-score 20 observations ago), Carry as in "1"   # "4": Carry = sign of the sum of the pairs' raw slopes (no z-score), Carry-Momentum as in "1"
#   # "3": Carry-Momentum on the per-month price spread (research/contract_months.py)
SFX = "_zdiff" if ZDIFF else "_rawcarry" if RAWC else ("_zsum_pm" if PM else "_zsum_std")
# research variant: Carry and Carry-Momentum sum the pairs' z-scores / slope changes before the sign (research/carry_zsum.py)
VTHR = float(os.environ["VALUE_THR"]) if os.environ.get("VALUE_THR") else None   # sandbox: Value band (e.g. 0.01 for +/-1%) instead of the config's 0.10
OUT = "outputs/final_dashboard_2012" + SFX if ZSUM else "outputs/final_dashboard_2012"
if VTHR is not None:
    OUT = "outputs/final_dashboard_2012_valthr%g" % (VTHR * 100)
HTML = f"Analysis/Final_Research_Dashboard_2012{SFX}.html" if ZSUM else "Analysis/Final_Research_Dashboard_2012.html"
if VTHR is not None:
    HTML = "Analysis/Final_Research_Dashboard_2012_valthr%g.html" % (VTHR * 100)
Path(OUT).mkdir(parents=True, exist_ok=True)


VALUE_MIN = 504
import pickle
import pandas as pd
sys.path[:0] = ["research", "research/configs", "scripts"]
import importlib
from engine import exec_shift, log_return_daily, value_v1_position
if ZSUM:
    from carry_zsum import carry_z, carry_slope_change, carry_slope_change_std, carry_pm_change, carry_slope, carry_z_diff, summed_signal
    from contract_months import months_between

nets, meta = pickle.load(open("outputs/final_dashboard/products_v2_nets.pkl", "rb"))
for (a, p) in list(nets):
    cfg = importlib.import_module(a)
    raw = cfg.load_f1_series_logret(p)
    pos = value_v1_position(cfg.load_curve(p), cfg.VALUE_CONTRACT, cfg.VALUE_LOOKBACK_DAYS, cfg.VALUE_THRESHOLD if VTHR is None else VTHR, shift_n=cfg.VALUE_SHIFT_N, min_periods=VALUE_MIN)
    new = log_return_daily(pos, raw["log_price"], 5, raw["Phase"])[1]
    d = (new - nets[(a, p)]["Value"]).abs().loc["2012-01-01":].max()
    print(f"Value min {VALUE_MIN}: {a} {p} max change since 2012 = {0 if pd.isna(d) else round(float(d), 4)}", flush=True)
    nets[(a, p)]["Value"] = new
    if ZSUM:
        lp, ph, curve, pr = raw["log_price"], raw["Phase"], cfg.load_curve(p), meta[(a, p)]["pairs"]
        sc = summed_signal([carry_slope(curve, n, f_) if RAWC else carry_z(curve, n, f_, cfg.CARRY_ZSCORE_WINDOW) for n, f_ in pr], lp.index)
        sm = summed_signal([carry_z_diff(curve, n, f_, cfg.CARRY_ZSCORE_WINDOW, cfg.CARRY_MOMENTUM_HORIZON) if ZDIFF else carry_pm_change(curve, n, f_, months_between(a, p, n, f_, curve.index), cfg.CARRY_MOMENTUM_HORIZON) if PM else (carry_slope_change_std if STD else carry_slope_change)(curve, n, f_, cfg.CARRY_MOMENTUM_HORIZON) for n, f_ in pr], lp.index)
        for nm, sg, sh in (("Carry", sc, cfg.CARRY_SHIFT_N), ("CarryMom", sm, cfg.CARRY_MOMENTUM_SHIFT_N)):
            nets[(a, p)][nm] = log_return_daily(exec_shift(sg, sh).fillna(0), lp, 5, ph)[1]
            flat = float((exec_shift(sg, sh).fillna(0).loc["2012-01-01":] == 0).mean())
            print(f"  zsum {nm}: {a} {p} flat share since 2012 = {flat:.3f}", flush=True)
pickle.dump((nets, meta), open(f"{OUT}/products_2012_nets.pkl", "wb"))


def transform(name, pairs):
    import re
    s = (D / name).read_text(encoding="utf8")
    # the main pipeline imports REPORT_START from regimes.py and REGIMES from final_regimes.py (three-regime scheme of 2026-10-12)
    s = re.sub(r"^from final_regimes import REGIMES[^\n]*\n", "", s, flags=re.M)
    s = s.replace("from regimes import REPORT_START", "from regimes import REGIMES, REPORT_START")
    for a, b in pairs:
        assert a in s, (name, a[:60])
        s = s.replace(a, b)
    return s


REG = ('REPORT_START = "2012-01-01"\nREGIMES = [("P1_2012_2016", "2012-01-01", "2016-12-31"), ("P2_2017_2021", "2017-01-01", "2021-12-31"), '
       '("P3_2022_onwards", "2022-01-01", "2026-12-31")]')
common = [("from regimes import REGIMES, REPORT_START", REG),
          ('OUT = Path("outputs/final_dashboard")', f'OUT = Path("{OUT}"); IN = Path("outputs/final_dashboard")')]   # the 2026 year-to-date window of the main pipeline is kept (P4, 2026 only)
srcs = {
    "analyze_v2.py": transform("analyze_v2.py", common + [('open(OUT / "products_v2_nets.pkl", "rb")', 'open(OUT / "products_2012_nets.pkl", "rb")')]),
    "analyze_twopair.py": transform("analyze_twopair.py", [
        ("from regimes import REGIMES, REPORT_START", REG),
        ('OUT=Path("outputs/final_dashboard")', f'OUT=Path("{OUT}"); IN=Path("outputs/final_dashboard")'),
        ('open(OUT/"products_v2_nets.pkl","rb")', 'open(OUT/"products_2012_nets.pkl","rb")')]),
    "build_final_dashboard_v2.py": transform("build_final_dashboard_v2.py", [
        ('res = json.load(open(R / "outputs/final_dashboard/final_v2.json"))', f'res = json.load(open(R / "{OUT}/final_v2.json"))'),
        ('two = json.load(open(R / "outputs/final_dashboard/twopair_v2.json"))', f'two = json.load(open(R / "{OUT}/twopair_v2.json"))'),
        ('COLS = [("full", "Full", "2011-2026"), ("r1", "R1", "2011-2016"), ("r2", "R2", "2017-2021"),\n        ("r3", "R3", "2022-2026"), ("y26", "2026", "YTD")]',
         'COLS = [("full", "Full", "2012-2026"), ("p1", "P1", "2012-2016"), ("p2", "P2", "2017-2021"), ("p3", "P3", "2022-2026"), ("y26", "2026", "YTD")]'),
        ('const EQ_STARTS=[["2011-01-01","From 2011"],["2016-01-01","From 2016"],["2020-01-01","From 2020"],["2022-01-01","From 2022"],["2026-01-01","From 2026"]];',
         'const EQ_STARTS=[["2012-01-01","From 2012"],["2017-01-01","From 2017"],["2022-01-01","From 2022"],["2026-01-01","From 2026"]];'),
        ("reporting from 2011-01-01. All price data", "reporting from 2012-01-01 in three periods (P1 2012-2016, P2 2017-2021, P3 2022 onwards) plus a 2026 year-to-date column. All price data"),
        ("Reporting still starts 2011-01-01, so 2026 year-to-date now covers nearly nine months.", "This variant reports from 2012-01-01; signals, rolls and costs are identical to the main dashboard except that Value needs 504 F3 observations (two years) instead of 630 before it starts, so NGL Value and NGL Inverse Vol are defined from before 2012."),
        ("Three regimes (set 2026-10-12, replacing the earlier four): <b>R1</b> 1 Jan 2011 to 31 Dec 2016, <b>R2</b> 1 Jan 2017 to 31 Dec 2021, <b>R3</b> 1 Jan 2022 to the last price date, 23 Sep 2026. The windows do not overlap. The 2026 column (year to date) lies inside R3.",
         "Three periods in this variant: <b>P1</b> 1 Jan 2012 to 31 Dec 2016, <b>P2</b> 1 Jan 2017 to 31 Dec 2021, <b>P3</b> 1 Jan 2022 to the last price date, 23 Sep 2026. The windows do not overlap. The 2026 column (year to date) lies inside P3."),
        ("), 2011-2026. Within-asset-class", "), 2012-2026. Within-asset-class"),
        ("2011 onward. Blue is positive", "2012 onward. Blue is positive"),
        ('out = R / "Analysis/Final_Research_Dashboard.html"', f'out = R / "{HTML}"'),
        ("Risk Premia: Final Research Dashboard", "Risk Premia: Final Research Dashboard (2012 start, three periods" + (", Value band +/-%g%%" % (VTHR * 100) if VTHR is not None else "") + (", Carry: summed raw slopes (no z-score)" if RAWC else ", Carry-Momentum standardised" if STD else ", Carry-Momentum per-month spread" if PM else ", Carry-Momentum z-score difference" if ZDIFF else "") + ")")]
        + ([("F3 price against its own 1,260-day average, long below -10%, short above +10%.", "F3 price against its own 1,260-day average, long below -%g%%, short above +%g%%." % (VTHR * 100, VTHR * 100))] if VTHR is not None else [])
        + ([("z-score of the carry slope, (near - far) / near, against its own trailing 252 days. With two tenor pairs, the z-scores of the pairs are summed",
             "raw carry slope, (near - far) / near, with no z-score. With two tenor pairs, the raw slopes of the pairs are summed")] if RAWC else [])
        + ([("change of the carry slope over 20 observations, summed across the tenor pairs (raw changes, not standardised) and signed",
             "the 20-day change of each pair's Carry z-score (z-score today minus the z-score 20 observations ago), summed across the pairs and signed" if ZDIFF else
             "the 20-day change of each pair's per-month spread, (near price - far price) divided by the exact months between the two legs on that date, summed across the pairs and signed" if PM else
             "the 20-day change of each pair's carry slope divided by its own trailing 252-day standard deviation, summed across the pairs and signed")] if (STD or PM or ZDIFF) else [])),
}
for name in ("analyze_v2.py", "analyze_twopair.py", "build_final_dashboard_v2.py"):
    print("==", name, flush=True)
    sys.argv = [name]
    exec(compile(srcs[name], name, "exec"), {"__name__": "__main__", "__file__": name})
