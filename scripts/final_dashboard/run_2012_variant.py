"""2012-start variant of the Final Research Dashboard (2026-10-12): three periods only, kept separate from the original research.

Reads the same per-product sleeve returns (outputs/final_dashboard/products_v2_nets.pkl, so signals, rolls, costs and warm-up are exactly the
original ones) and re-cuts the reporting window: full sample 2012-01-01 to date, P1 2012-2016, P2 2017-2021, P3 2022 onwards (no 2026 YTD column).
Writes outputs/final_dashboard_2012/*.json and Analysis/Final_Research_Dashboard_2012.html. Does not touch research/regimes.py or any original output.
The only change to the sleeves: Value needs 504 observations (two years) of F3 instead of 630 before its signal starts, for every product, so that
NGL Value and the NGL Inverse Vol series are defined before the 2012 reporting start. Run from the repo root after compute_products.py: python scripts/final_dashboard/run_2012_variant.py"""
import sys
from pathlib import Path

D = Path("scripts/final_dashboard")
OUT = "outputs/final_dashboard_2012"
Path(OUT).mkdir(parents=True, exist_ok=True)


VALUE_MIN = 504
import pickle
import pandas as pd
sys.path[:0] = ["research", "research/configs", "scripts"]
import importlib
from engine import log_return_daily, value_v1_position

nets, meta = pickle.load(open("outputs/final_dashboard/products_v2_nets.pkl", "rb"))
for (a, p) in list(nets):
    cfg = importlib.import_module(a)
    raw = cfg.load_f1_series_logret(p)
    pos = value_v1_position(cfg.load_curve(p), cfg.VALUE_CONTRACT, cfg.VALUE_LOOKBACK_DAYS, cfg.VALUE_THRESHOLD, shift_n=cfg.VALUE_SHIFT_N, min_periods=VALUE_MIN)
    new = log_return_daily(pos, raw["log_price"], 5, raw["Phase"])[1]
    d = (new - nets[(a, p)]["Value"]).abs().loc["2012-01-01":].max()
    print(f"Value min {VALUE_MIN}: {a} {p} max change since 2012 = {0 if pd.isna(d) else round(float(d), 4)}", flush=True)
    nets[(a, p)]["Value"] = new
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
          ('OUT = Path("outputs/final_dashboard")', f'OUT = Path("{OUT}"); IN = Path("outputs/final_dashboard")'),
          (' + [("y26", "2026-01-01", None)]', "")]
srcs = {
    "analyze_v2.py": transform("analyze_v2.py", common + [('open(OUT / "products_v2_nets.pkl", "rb")', 'open(OUT / "products_2012_nets.pkl", "rb")')]),
    "analyze_twopair.py": transform("analyze_twopair.py", [
        ("from regimes import REGIMES, REPORT_START", REG),
        ('OUT=Path("outputs/final_dashboard")', f'OUT=Path("{OUT}"); IN=Path("outputs/final_dashboard")'),
        ('open(OUT/"products_v2_nets.pkl","rb")', 'open(OUT/"products_2012_nets.pkl","rb")'),
        ('+[("y26","2026-01-01",None)]', "")]),
    "build_final_dashboard_v2.py": transform("build_final_dashboard_v2.py", [
        ('res = json.load(open(R / "outputs/final_dashboard/final_v2.json"))', f'res = json.load(open(R / "{OUT}/final_v2.json"))'),
        ('two = json.load(open(R / "outputs/final_dashboard/twopair_v2.json"))', f'two = json.load(open(R / "{OUT}/twopair_v2.json"))'),
        ('COLS = [("full", "Full", "2011-2026"), ("r1", "R1", "2011-2016"), ("r2", "R2", "2017-2021"),\n        ("r3", "R3", "2022-2026"), ("y26", "2026", "YTD")]',
         'COLS = [("full", "Full", "2012-2026"), ("p1", "P1", "2012-2016"), ("p2", "P2", "2017-2021"), ("p3", "P3", "2022-2026")]'),
        ('const EQ_STARTS=[["2011-01-01","From 2011"],["2016-01-01","From 2016"],["2020-01-01","From 2020"],["2022-01-01","From 2022"],["2026-01-01","From 2026"]];',
         'const EQ_STARTS=[["2012-01-01","From 2012"],["2017-01-01","From 2017"],["2022-01-01","From 2022"]];'),
        ("reporting from 2011-01-01. All price data", "reporting from 2012-01-01 in three periods (P1 2012-2016, P2 2017-2021, P3 2022 onwards). All price data"),
        ("Reporting still starts 2011-01-01, so 2026 year-to-date now covers nearly nine months.", "This variant reports from 2012-01-01; signals, rolls and costs are identical to the main dashboard except that Value needs 504 F3 observations (two years) instead of 630 before it starts, so NGL Value and NGL Inverse Vol are defined from before 2012."),
        ("Three regimes (set 2026-10-12, replacing the earlier four): <b>R1</b> 1 Jan 2011 to 31 Dec 2016, <b>R2</b> 1 Jan 2017 to 31 Dec 2021, <b>R3</b> 1 Jan 2022 to the last price date, 23 Sep 2026. The windows do not overlap. The 2026 column (year to date) lies inside R3.",
         "Three periods in this variant: <b>P1</b> 1 Jan 2012 to 31 Dec 2016, <b>P2</b> 1 Jan 2017 to 31 Dec 2021, <b>P3</b> 1 Jan 2022 to the last price date, 23 Sep 2026. The windows do not overlap."),
        ("), 2011-2026. Within-asset-class", "), 2012-2026. Within-asset-class"),
        ("2011 onward. Blue is positive", "2012 onward. Blue is positive"),
        ('out = R / "Analysis/Final_Research_Dashboard.html"', 'out = R / "Analysis/Final_Research_Dashboard_2012.html"'),
        ("Risk Premia: Final Research Dashboard", "Risk Premia: Final Research Dashboard (2012 start, three periods)")]),
}
for name in ("analyze_v2.py", "analyze_twopair.py", "build_final_dashboard_v2.py"):
    print("==", name, flush=True)
    sys.argv = [name]
    exec(compile(srcs[name], name, "exec"), {"__name__": "__main__", "__file__": name})
