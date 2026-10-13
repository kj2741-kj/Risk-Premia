"""Per-product sleeve net returns for the rebuilt final dashboard.
Data: data/Prices_0924 (through 2026-09-23). Roll: 5th trading day of the last-trade-date month (research configs' ROLL_RULE). 5 bps costs (roll days charged).
Sleeves: Momentum (3-way MA composite), Carry = V2 SUMMED z-scores of the tenor pairs then sign (the earlier sign-vote was replaced on 2026-10-13), CarryMom = SUMMED raw slope changes then sign, Value,
Skewness (added 2026-10-12: sign of minus the skewness of the continuous series' daily log returns over 252 observations; long if negative; 2-day lag).
Tenor pairs:
  Metals / Energy : F1-F3 + F1-F13           NGL : F2-F4 + F2-F14
  Precious        : F1-F2 + long (Gold F7, Silver F6, Platinum F5, Palladium F5)
  Agriculture     : F1-F2 + long (Corn F6, Wheat F6, Soybean F8, Soybean Oil F8, Coffee F6, Sugar F5)
Also stores per-product single-pair legs for Precious/Agriculture (short, long, previous single-pair baseline). Run from the repo root."""
import sys, pickle
from pathlib import Path

sys.path.insert(0, "research"); sys.path.insert(0, "research/configs"); sys.path.insert(0, "scripts")
import importlib
import os
import numpy as np
import pandas as pd
from engine import (raw_signal_carry_v2, raw_signal_carrymom, combine_positions, exec_shift, log_return_daily,
                    momentum_composite_position, value_v1_position)

OUT = Path("outputs/final_dashboard")
TC = 5
SKEW_WINDOW, SKEW_SHIFT_N = 252, 1
cfgs = {a: importlib.import_module(a) for a in ("metals", "energy", "ngl", "precious", "agri")}   # repo defaults: data, roll rule, pairs
import rolling_continuous as rc
from carry_zsum import carry_z, carry_slope_change, summed_signal
OUT.mkdir(parents=True, exist_ok=True)

LONG = {"precious": {"Gold": "F7", "Silver": "F6", "Platinum": "F5", "Palladium": "F5"},
        "agri": {"Corn": "F6", "Wheat": "F6", "Soybean": "F8", "SoybeanOil": "F8", "Coffee": "F6", "Sugar": "F5"}}
PRODUCTS = {"metals": ["Copper", "Aluminium", "Lead", "Zinc"], "energy": ["WTI", "Brent", "RBOB", "HeatingOil", "NatGas"],
            "ngl": ["Ethane", "Propane", "Butane", "Isobutane"], "precious": list(LONG["precious"]), "agri": list(LONG["agri"])}
BASELINE_SINGLE = {"precious": ("F1", "F3"), "agri": ("F1", "F2")}   # the previous single-pair Carry settings


def pairs_for(a, p):
    if a in ("metals", "energy"):
        return [("F1", "F3"), ("F1", "F13")]
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
        W, H = cfg.CARRY_ZSCORE_WINDOW, cfg.CARRY_MOMENTUM_HORIZON
        pr = pairs_for(a, p)
        run = lambda pos: log_return_daily(pos, lp, TC, ph)[1]
        v = {}
        v["Momentum"] = run(momentum_composite_position(f1r, cfg.MOMENTUM_PAIRS, shift_n=cfg.MOMENTUM_SHIFT_N))
        zs = [raw_signal_carry_v2(curve, n, f, window=W) for n, f in pr]
        # Carry V2: SUM the pairs' z-scores, then the sign; last signal kept if a z-score is missing (since 2026-10-13; earlier: sign-vote, see ENGINE_CHANGELOG)
        v["Carry"] = run(exec_shift(summed_signal([carry_z(curve, n, f, W) for n, f in pr], lp.index), cfg.CARRY_SHIFT_N).fillna(0))
        ds = [raw_signal_carrymom(curve, n, f, H) for n, f in pr]
        # Carry-Momentum: SUM the pairs' raw 20-observation slope changes, then the sign
        v["CarryMom"] = run(exec_shift(summed_signal([carry_slope_change(curve, n, f, H) for n, f in pr], lp.index), cfg.CARRY_MOMENTUM_SHIFT_N).fillna(0))
        v["Value"] = run(value_v1_position(curve, cfg.VALUE_CONTRACT, cfg.VALUE_LOOKBACK_DAYS, cfg.VALUE_THRESHOLD, shift_n=cfg.VALUE_SHIFT_N))
        v["Skewness"] = run(exec_shift(np.sign(-lp.diff().rolling(SKEW_WINDOW).skew()), SKEW_SHIFT_N).fillna(0))
        if a in ("precious", "agri"):
            v["carry_short"] = run(exec_shift(zs[0], cfg.CARRY_SHIFT_N).fillna(0))
            v["carry_long"] = run(exec_shift(zs[1], cfg.CARRY_SHIFT_N).fillna(0))
            v["cm_short"] = run(exec_shift(ds[0], cfg.CARRY_MOMENTUM_SHIFT_N).fillna(0))
            v["cm_long"] = run(exec_shift(ds[1], cfg.CARRY_MOMENTUM_SHIFT_N).fillna(0))
            n0, f0 = BASELINE_SINGLE[a]
            v["carry_single_prev"] = run(exec_shift(raw_signal_carry_v2(curve, n0, f0, window=W), cfg.CARRY_SHIFT_N).fillna(0))
            v["cm_single_prev"] = run(exec_shift(raw_signal_carrymom(curve, n0, f0, H), cfg.CARRY_MOMENTUM_SHIFT_N).fillna(0))
        nets[(a, p)] = v
        meta[(a, p)] = dict(first=str(f1r.index.min().date()), last=str(f1r.index.max().date()), rolls=int(raw["is_roll_date"].sum()),
                            pairs=pr, f2_track_share=round(float((ph == "F2_Tracking").mean()), 3))
        print("done", a, p, meta[(a, p)], flush=True)
print("roll fallbacks (roll day not before last trade date):", rc.ROLL_FALLBACK_COUNT["n"])
pickle.dump((nets, meta), open(OUT / (sys.argv[1] if len(sys.argv) > 1 else "products_v2_nets.pkl"), "wb"))
print("saved")
