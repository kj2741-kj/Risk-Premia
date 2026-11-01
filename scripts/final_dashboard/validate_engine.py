"""Validation of the 2026-10-11 engine/config update: rebuild every product's four sleeves using ONLY the repo's own defaults (no in-memory
overrides) and compare with products_v2_nets.pkl (the series behind Final_Research_Dashboard.html, built with in-memory overrides).
Also checks cross_asset_engine.per_product_four_row(per_product_pairs=True). Run from the repo root."""
import sys, pickle, importlib
sys.path.insert(0, "research"); sys.path.insert(0, "research/configs"); sys.path.insert(0, "scripts")
import numpy as np
import pandas as pd
import rolling_continuous as rc
import run_regime_table as rrt
import cross_asset_engine as cae
from engine import log_return_daily

ref, _ = pickle.load(open("outputs/final_dashboard/products_v2_nets.pkl", "rb"))
PRODUCTS = {"metals": ["Copper", "Aluminium", "Lead", "Zinc"], "energy": ["WTI", "Brent", "RBOB", "HeatingOil", "NatGas"],
            "ngl": ["Ethane", "Propane", "Butane", "Isobutane"], "precious": ["Gold", "Silver", "Platinum", "Palladium"],
            "agri": ["Corn", "Wheat", "Soybean", "SoybeanOil", "Coffee", "Sugar"]}
worst = 0.0
for a, prods in PRODUCTS.items():
    cfg = importlib.import_module(a)
    for p in prods:
        curve = cfg.load_curve(p)
        raw = cfg.load_f1_series_logret(p)
        lp, ph = raw["log_price"], raw["Phase"]
        for label, kind in rrt._strategy_defs(cfg):
            pos = rrt._position_for(cfg, kind, raw["F1_raw"], curve, product=p)
            net = log_return_daily(pos, lp, rrt.TC_BPS, ph)[1]
            r = ref[(a, p)][label]
            idx = r.index.union(net.index)
            d = (r.reindex(idx).fillna(0) - net.reindex(idx).fillna(0)).abs().max()
            worst = max(worst, float(d))
            if d > 1e-12:
                print("DIFF", a, p, label, d)
        print("checked", a, p, "| last date", raw.index.max().date(), flush=True)
print("repo-defaults rebuild vs dashboard series: worst abs difference = %.2e" % worst)
print("roll fallbacks (contracts rolled the day before expiry):", rc.ROLL_FALLBACK_COUNT["n"])
for a in ("precious", "agri"):
    out = cae.per_product_four_row(a, per_product_pairs=True)
    w = 0.0
    for style, lab in (("Combined Carry", "Carry"), ("Combined CarryMom", "CarryMom")):
        for nm, net in zip(out[style]["names"], out[style]["net"]):
            r = ref[(a, nm)][lab]
            idx = r.index.union(net.index)
            w = max(w, float((r.reindex(idx).fillna(0) - net.reindex(idx).fillna(0)).abs().max()))
    print(f"cross_asset_engine.per_product_four_row({a!r}, per_product_pairs=True) vs dashboard Carry/CarryMom: worst abs diff {w:.2e}")
print("VALIDATION DONE")
