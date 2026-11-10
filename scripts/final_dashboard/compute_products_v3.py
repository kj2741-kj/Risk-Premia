"""Per-product sleeve net returns for the 2012 research dashboard with the new buckets (2026-10-31) -> outputs/final_dashboard_0930/products_nets.pkl
Data: data/Prices_0930 (merged 29-Oct pull, every sheet cut at 2026-09-30) or data/Prices_1029_merged (nothing cut, latest data); set RP_PRICES_DIR to one of them, this script refuses to run otherwise.
Same sleeves, signals, roll rule (5th trading day of the last-trade-date month), tenor-pair rule and 5 bps costs (roll days charged) as compute_products.py, plus:
  * the Emissions class (EUA from the first Phase II day 2008-04-01, TTF from 2006; research/configs/emissions.py; Carry F1-F2 plus a 12-month pair for both (TTF F1-F13, EUA F1-F5; TTF has no Carry signal before 2014-09-25); own calendars in Emissions_Expiry_Calendars.xlsx);
  * Value needs 504 observations of F3 (not 630), as in the 2012 variant, so that every product's Value is defined before the 2012 reporting start.
Tenor pairs: Metals / Energy: F1-F3 + F1-F13;  NGL: F2-F4 + F2-F14 (Naphtha F2-F4 only);  Emissions: TTF F1-F2 + F1-F13, EUA F1-F2 + F1-F5;  Precious / Agriculture: F1-F2 + long (as compute_products.py).
Run from the repo root:  RP_PRICES_DIR=Prices_0930 (or Prices_1029_merged) python scripts/final_dashboard/compute_products_v3.py   (tag 0930 / 1029, see fd_config.py)"""
import os
import sys
import pickle
from pathlib import Path

import json
sys.path.insert(0, "scripts/final_dashboard")
from fd_config import TAGS, tag_from_prices_dir, out_dir   # RP_PRICES_DIR must be Prices_0930 or Prices_1029_merged (scripts/rolling_continuous.py reads the data folder from it)
TAG = tag_from_prices_dir()
os.environ["RP_POWER_CUTOFF"] = TAGS[TAG]["cutoff"]     # the Power files run to 2026-11-02; the run ends on the tag's cutoff like every other series (research/configs/power.py reads this variable)
sys.path.insert(0, "research"); sys.path.insert(0, "research/configs"); sys.path.insert(0, "scripts")
import importlib
import numpy as np
import pandas as pd
from engine import (raw_signal_carry_v2, raw_signal_carrymom, combine_positions, exec_shift, log_return_daily,
                    momentum_composite_position, value_v1_position)

OUT = out_dir(TAG)
CUTOFF = pd.Timestamp(TAGS[TAG]["cutoff"])
TC = 5
SKEW_WINDOW, SKEW_SHIFT_N = 252, 1
VALUE_MIN = 504
cfgs = {a: importlib.import_module(a) for a in ("metals", "energy", "emissions", "ngl", "naphtha", "mmb", "precious", "agri", "softs", "power")}
import rolling_continuous as rc
from carry_zsum import carry_z, carry_slope_change, summed_signal
OUT.mkdir(parents=True, exist_ok=True)

LONG = {"precious": {"Gold": "F7", "Silver": "F6", "Platinum": "F5", "Palladium": "F5"},
        "agri": {"Corn": "F6", "Wheat": "F6", "Soybean": "F7", "LiveCattle": "F7"},                       # user decision 2026-11-10 (F1-F2 short pair for all)
        "softs": {"Sugar": "F6", "Cocoa": "F6", "Coffee": "F6", "Cotton": "F6"}}
PRODUCTS = {"metals": ["Copper", "Aluminium", "Lead", "Zinc"], "energy": ["WTI", "Brent", "RBOB", "HeatingOil", "NatGas"], "emissions": ["EUA", "TTF", "UKGas"],
            "ngl": ["Ethane", "Propane", "Butane"], "naphtha": ["Naphtha"], "mmb": ["NatGasoline"], "precious": list(LONG["precious"]), "agri": list(LONG["agri"]), "softs": list(LONG["softs"]),
            "power": ["PJM_Peak", "PJM_OffPeak", "ERCOT_Peak", "ERCOT_OffPeak", "MISO_Peak"]}      # US Power: the five series with Calendar-2025 L below 5 days (MISO OffPeak, 9.9 days, is out)


def pairs_for(a, p):
    if a in ("metals", "energy"):
        return [("F1", "F3"), ("F1", "F13")]
    if a in ("emissions", "naphtha", "mmb", "power"):
        return cfgs[a].carry_pairs(p)
    if a == "ngl":
        return [("F2", "F4"), ("F2", "F14")]
    return [("F1", "F2"), ("F1", LONG[a][p])]


nets, meta = {}, {}
for a, prods in PRODUCTS.items():
    cfg = cfgs[a]
    for p in prods:
        curve = cfg.load_curve(p)
        raw = cfg.load_f1_series_logret(p)
        lp, ph, f1r = raw["log_price"], raw["Phase"], raw["F1_raw"]
        assert f1r.index.max() <= CUTOFF, (a, p, f1r.index.max())
        W, H = cfg.CARRY_ZSCORE_WINDOW, cfg.CARRY_MOMENTUM_HORIZON
        pr = pairs_for(a, p)
        run = lambda pos: log_return_daily(pos, lp, TC, ph)[1]
        v = {}
        v["Momentum"] = run(momentum_composite_position(f1r, cfg.MOMENTUM_PAIRS, shift_n=cfg.MOMENTUM_SHIFT_N))
        v["Carry"] = run(exec_shift(summed_signal([carry_z(curve, n, f, W) for n, f in pr], lp.index), cfg.CARRY_SHIFT_N).fillna(0))
        v["CarryMom"] = run(exec_shift(summed_signal([carry_slope_change(curve, n, f, H) for n, f in pr], lp.index), cfg.CARRY_MOMENTUM_SHIFT_N).fillna(0))
        v["Value"] = run(value_v1_position(curve, cfg.VALUE_CONTRACT, cfg.VALUE_LOOKBACK_DAYS, cfg.VALUE_THRESHOLD, shift_n=cfg.VALUE_SHIFT_N, min_periods=VALUE_MIN))
        v["Skewness"] = run(exec_shift(np.sign(-lp.diff().rolling(SKEW_WINDOW).skew()), SKEW_SHIFT_N).fillna(0))
        nets[(a, p)] = v
        meta[(a, p)] = dict(first=str(f1r.index.min().date()), last=str(f1r.index.max().date()), rolls=int(raw["is_roll_date"].sum()),
                            pairs=pr, f2_track_share=round(float((ph == "F2_Tracking").mean()), 3))
        print("done", a, p, meta[(a, p)], flush=True)
print("roll fallbacks (roll day not before last trade date):", rc.ROLL_FALLBACK_COUNT["n"])
pickle.dump((nets, meta), open(OUT / "products_nets.pkl", "wb"))
json.dump(dict(tag=TAG, cutoff=TAGS[TAG]["cutoff"], prices_dir=TAGS[TAG]["prices_dir"], products=len(nets)), open(OUT / "run_info.json", "w"))
print("saved", OUT / "products_nets.pkl")
