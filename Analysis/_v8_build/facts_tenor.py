"""Single-pair versus two-pair Carry and Carry-Momentum for the Agriculture and Softs buckets (10 November 2026).
Same construction as scripts/final_dashboard/compute_products_v3.py: V2 z-score (window 252) and the 20-observation slope change, pairs summed at the signal level, sign taken, one-day execution lag,
5 bps costs with the roll charge, products equally weighted on common dates. The two-pair column must equal the bucket's reported Carry and Carry-Momentum sleeves exactly (asserted)."""
import os, sys
import numpy as np, pandas as pd
from facts3 import *
for _q in ("research", os.path.join("research", "configs"), "scripts"):
    _p = os.path.join(REPO, _q)
    if _p not in sys.path: sys.path.insert(0, _p)
import importlib
from engine import exec_shift, log_return_daily
from carry_zsum import carry_z, carry_slope_change, summed_signal

TC = 5
_cache = {}


def _product_nets(bucket, product):
    key = (bucket, product)
    if key in _cache:
        return _cache[key]
    cfg = importlib.import_module(bucket)
    curve = cfg.load_curve(product); raw = cfg.load_f1_series_logret(product)
    lp, ph = raw["log_price"], raw["Phase"]
    W, H = cfg.CARRY_ZSCORE_WINDOW, cfg.CARRY_MOMENTUM_HORIZON
    pairs = {"short": [("F1", "F2")], "long": [("F1", cfg.CARRY_LONG_FAR_BY_PRODUCT[product])]}
    pairs["two"] = pairs["short"] + pairs["long"]
    run = lambda pos: log_return_daily(pos, lp, TC, ph)[1]
    out = {}
    for name, pr in pairs.items():
        out[("Carry", name)] = run(exec_shift(summed_signal([carry_z(curve, n, f, W) for n, f in pr], lp.index), cfg.CARRY_SHIFT_N).fillna(0))
        out[("CarryMom", name)] = run(exec_shift(summed_signal([carry_slope_change(curve, n, f, H) for n, f in pr], lp.index), cfg.CARRY_MOMENTUM_SHIFT_N).fillna(0))
    out["pairs"] = pairs
    _cache[key] = out
    return out


def bucket_tenor_table(bucket_key):
    """{sleeve: {short, long, two}} full-sample bucket statistics (IR, return, volatility, drawdown), plus the per-product IRs and the pairs used."""
    mod = {"agri": "agri", "softs": "softs"}[bucket_key]
    members = MEMBERS[bucket_key]
    res, per_product, pairs = {}, {}, {}
    for sleeve in ("Carry", "CarryMom"):
        res[sleeve] = {}
        for name in ("short", "long", "two"):
            series = [_product_nets(mod, p)[(sleeve, name)] for _, p in members]
            res[sleeve][name] = stats(ew_intersection(series))
            for (_, p), s_ in zip(members, series):
                per_product.setdefault(p, {}).setdefault(sleeve, {})[name] = stats(s_)["ir"]
    for _, p in members:
        pairs[p] = _product_nets(mod, p)["pairs"]
    # the two-pair series must equal the sleeve of the bucket tab exactly
    for sleeve in ("Carry", "CarryMom"):
        mine = ew_intersection([_product_nets(mod, p)[(sleeve, "two")] for _, p in members])
        ref = CS[bucket_key][sleeve]
        idx = mine.index.intersection(ref.index)
        chk(float((mine.loc[idx] - ref.loc[idx]).abs().loc["2012-01-01":].max()) < 1e-9, f"{bucket_key} {sleeve}: two-pair series equals the reported bucket sleeve")
    return res, per_product, pairs
