"""
research/run_regime_table.py
===============================
Generic full-sample + regime-conditional IR table builder, for any asset
class config module (metals/precious/energy/ngl) that exposes: PRODUCTS,
load_f1_series_logret(product), load_curve(product), MOMENTUM_PAIRS,
MOMENTUM_SHIFT_N, CARRY_TENOR_PAIRS, CARRY_ZSCORE_WINDOW, CARRY_SHIFT_N,
CARRY_MOMENTUM_HORIZON, CARRY_MOMENTUM_SHIFT_N, VALUE_CONTRACT,
VALUE_LOOKBACK_DAYS, VALUE_THRESHOLD, VALUE_SHIFT_N.

Mirrors exactly the construction already used for Metals/Precious Metals
(hand-built in earlier sessions): per product, per strategy, compute the
NET log-return PnL series over that asset class's own common date range;
equal-weight across products for a strategy-level EW series; equal-weight
across strategies for the EW PORT row. Regime slicing uses the locked
7-regime scheme (regimes.py). IR = mean/std*sqrt(252) computed on the
EW-combined series over its FULL span in each window (not active-day-only
-- once combined across products, "active" is no longer a clean concept,
matching how the existing Metals/PM EW PORT rows were computed).
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
sys.path.insert(0, str(_THIS_DIR))
sys.path.insert(0, str(_THIS_DIR / "configs"))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from engine import (carry_v1v2_composite_position, carry_v4_position,  # noqa: E402
                     log_return_daily, momentum_composite_position,
                     value_v1_position)
from regimes import REGIMES  # noqa: E402

TC_BPS = 5


def _strategy_defs(cfg):
    defs = [("Momentum", None)]
    for near, far in cfg.CARRY_TENOR_PAIRS:
        defs.append((f"Carry (F{near[1:]}-F{far[1:]})", ("carry", near, far)))
    for near, far in cfg.CARRY_TENOR_PAIRS:
        defs.append((f"CarryMom (F{near[1:]}-F{far[1:]})", ("carrymom", near, far)))
    defs.append(("Value", "value"))
    return defs


def _position_for(cfg, kind, raw_f1, curve):
    if kind is None:
        return momentum_composite_position(raw_f1, cfg.MOMENTUM_PAIRS, cfg.MOMENTUM_SHIFT_N)
    if kind == "value":
        return value_v1_position(curve, cfg.VALUE_CONTRACT, cfg.VALUE_LOOKBACK_DAYS,
                                  cfg.VALUE_THRESHOLD, cfg.VALUE_SHIFT_N)
    tag, near, far = kind
    if tag == "carry":
        return carry_v1v2_composite_position(curve, near, far, cfg.CARRY_ZSCORE_WINDOW, cfg.CARRY_SHIFT_N)
    if tag == "carrymom":
        return carry_v4_position(curve, cfg.CARRY_MOMENTUM_HORIZON, cfg.CARRY_MOMENTUM_SHIFT_N, near, far)
    raise ValueError(kind)


def build_table(cfg):
    products = cfg.PRODUCTS
    logret_by_product = {p: cfg.load_f1_series_logret(p) for p in products}
    curve_by_product = {p: cfg.load_curve(p) for p in products}

    common_start = max(s.index.min() for s in logret_by_product.values())
    common_end = min(s.index.max() for s in logret_by_product.values())
    print(f"Common date range across {len(products)} products: {common_start.date()} to {common_end.date()}")

    for p in products:
        logret_by_product[p] = logret_by_product[p].loc[common_start:common_end]

    strategy_defs = _strategy_defs(cfg)
    strategy_net_series: dict[str, pd.Series] = {}

    for label, kind in strategy_defs:
        combined = None
        for p in products:
            raw = logret_by_product[p]
            log_price = raw["log_price"]
            curve = curve_by_product[p].loc[common_start:common_end]
            pos = _position_for(cfg, kind, raw["F1_raw"], curve)
            _, net = log_return_daily(pos, log_price, TC_BPS, raw["Phase"])
            net = net.reindex(raw.index).fillna(0.0)
            combined = net if combined is None else combined + net
        combined = combined / len(products)
        strategy_net_series[label] = combined

    ew_port = sum(strategy_net_series.values()) / len(strategy_net_series)
    strategy_net_series["EW PORT"] = ew_port

    def _metrics(series: pd.Series) -> dict:
        s = series.dropna()
        if len(s) < 20 or s.std(ddof=1) == 0:
            return dict(ret=np.nan, vol=np.nan, ir=np.nan)
        ret = float(s.mean() * 252)
        vol = float(s.std(ddof=1) * np.sqrt(252))
        ir = float(ret / vol) if vol > 0 else np.nan
        return dict(ret=ret * 100, vol=vol * 100, ir=ir)

    full_rows = []
    for label, _ in strategy_defs + [("EW PORT", None)]:
        m = _metrics(strategy_net_series[label])
        full_rows.append(dict(name=label, **m))

    regime_rows = []
    for label, _ in strategy_defs + [("EW PORT", None)]:
        series = strategy_net_series[label]
        row = dict(name=label)
        full_m = _metrics(series)
        row["full"] = full_m["ir"]
        for rname, start, end in REGIMES:
            sub = series.loc[start:end]
            row[rname] = _metrics(sub)["ir"]
        row["y26"] = _metrics(series.loc["2026-01-01":])["ir"]
        regime_rows.append(row)

    return full_rows, regime_rows, common_start, common_end


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("asset_class", choices=["energy", "ngl", "metals", "precious"])
    args = parser.parse_args()
    cfg = importlib.import_module(args.asset_class)

    full_rows, regime_rows, cs, ce = build_table(cfg)

    print("\n=== FULL SAMPLE ===")
    for r in full_rows:
        print(f"{r['name']:<20} Return={r['ret']:>7.2f}%  Vol={r['vol']:>7.2f}%  IR={r['ir']:>7.3f}")

    print("\n=== REGIME TABLE (IR) ===")
    header = f"{'Strategy':<20}" + "".join(f"{n.split('_')[0]:>9}" for n, _, _ in REGIMES) + f"{'2026':>9}" + f"{'Full':>9}"
    print(header)
    for r in regime_rows:
        line = f"{r['name']:<20}"
        for rname, _, _ in REGIMES:
            v = r.get(rname)
            line += f"{v:>9.3f}" if pd.notna(v) else f"{'n/a':>9}"
        line += f"{r['y26']:>9.3f}" if pd.notna(r['y26']) else f"{'n/a':>9}"
        line += f"{r['full']:>9.3f}" if pd.notna(r['full']) else f"{'n/a':>9}"
        print(line)
