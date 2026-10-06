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
from regimes import REGIMES, REPORT_START  # noqa: E402

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


def _metrics(series: pd.Series) -> dict:
    s = series.dropna()
    if len(s) < 20 or s.std(ddof=1) == 0:
        return dict(ret=np.nan, vol=np.nan, mdd=np.nan, ir=np.nan)
    log_ret = float(s.mean() * 252)
    log_vol = float(s.std(ddof=1) * np.sqrt(252))
    # TRUE compounded annual return (fixed 2026-08-04, was log_ret*100 before --
    # same log-vs-value gap as MDD: log_ret is the continuously-compounded
    # growth rate, not literally "% you make in a year". Converted the same
    # way MDD was: true_ret = e^log_ret - 1.
    ret = (np.exp(log_ret) - 1) * 100
    # TRUE annualized volatility (fixed 2026-08-04, same family of fix):
    # log_vol describes the spread of the LOG-return distribution, not the
    # volatility of TRUE (simple) returns -- unlike ret/mdd, there's no exact
    # exp()-based identity here (volatility is a distribution's spread, not a
    # level), and a theoretical log-normal correction would require assuming
    # log returns are normally distributed, an assumption this project
    # doesn't otherwise make (these are fat-tailed commodity series). Instead,
    # computed directly and empirically from the SAME realized data: convert
    # each day's REALIZED log return to its REALIZED simple return
    # (exp(r)-1, exact, no distributional assumption), then take the std of
    # those and annualize by sqrt(252) -- the standard market convention,
    # applied to true returns instead of log returns.
    vol = float(np.expm1(s).std(ddof=1) * np.sqrt(252)) * 100
    # IR (fixed 2026-08-04, user's explicit instruction): computed from the
    # SAME true-% ret/vol above, not log_ret/log_vol -- same units in
    # numerator and denominator, so IR = ret/vol holds exactly against the
    # two displayed numbers (previously IR was kept on log_ret/log_vol
    # specifically to preserve the industry-standard log-return Sharpe
    # convention, which is defensible on its own, but it meant the displayed
    # ret and vol no longer divided to give the displayed IR once both were
    # converted to true % -- a real, valid consistency complaint since a
    # reader can and did check that division by eye).
    ir = float(ret / vol) if vol > 0 else np.nan
    # Max drawdown WITHIN this window: cumulative log-return reset to 0 at the
    # window's own start, same convention as ret/vol being independently
    # annualized per window rather than sliced off one continuous full-sample
    # equity curve -- so a regime's drawdown reflects what that regime alone
    # did, not carry-over from before it started.
    #
    # TRUE value-based drawdown (fixed 2026-08-04, was log-space peak-to-
    # trough before -- e.g. a "-114.6%" log drawdown was actually a -68.2%
    # decline in portfolio value; log returns compress large negative moves,
    # so the two diverge more the bigger the drawdown). value = exp(cum) is
    # the compounded growth factor implied by the log returns (value[0]=1);
    # (value / running-peak - 1) is the exact percentage decline in that
    # value from its own prior high, which is what "max drawdown" means
    # everywhere outside this project.
    cum = s.cumsum()
    value = np.exp(cum)
    mdd = float((value / value.cummax() - 1).min()) * 100
    return dict(ret=ret, vol=vol, mdd=mdd, ir=ir)


def build_strategy_net_series(cfg) -> tuple[dict[str, pd.Series], pd.Timestamp, pd.Timestamp]:
    """Per-strategy, per-product-combined NET log-return PnL series (shared by
    build_table() and build_window_grid() so both draw from the identical
    underlying series).

    Signal computation (moving averages, z-scores, Value's 1260-day lookback)
    runs on each product's own FULL available history -- NOT pre-truncated to
    the cross-product common window -- so every rolling calculation gets the
    maximum warm-up data available for that specific product (e.g. an NGL leg
    with an earlier own-history start than the asset class's latest-starting
    product still gets to use its own extra months of history to clear
    burn-in). Only the resulting PER-PRODUCT NET-RETURN series is aligned to
    the common cross-product window before summing into the EW combination --
    that alignment is required (you can't equal-weight a product that hasn't
    started trading yet), but it happens after burn-in has already been
    absorbed, not before. See project memory (2026-07-24 regime reporting
    revision) for the empirical NGL Value-strategy warm-up improvement this
    produced."""
    products = cfg.PRODUCTS
    logret_by_product = {p: cfg.load_f1_series_logret(p) for p in products}
    curve_by_product = {p: cfg.load_curve(p) for p in products}

    common_start = max(s.index.min() for s in logret_by_product.values())
    common_end = min(s.index.max() for s in logret_by_product.values())
    print(f"Common date range across {len(products)} products: {common_start.date()} to {common_end.date()}")

    strategy_defs = _strategy_defs(cfg)
    strategy_net_series: dict[str, pd.Series] = {}

    for label, kind in strategy_defs:
        combined = None
        for p in products:
            raw = logret_by_product[p]  # full own-history, not pre-sliced
            log_price = raw["log_price"]
            curve = curve_by_product[p]  # full own-history, not pre-sliced
            pos = _position_for(cfg, kind, raw["F1_raw"], curve)
            _, net = log_return_daily(pos, log_price, TC_BPS, raw["Phase"])
            net = net.loc[common_start:common_end].reindex(raw.loc[common_start:common_end].index).fillna(0.0)
            combined = net if combined is None else combined + net
        combined = combined / len(products)
        strategy_net_series[label] = combined

    ew_port = sum(strategy_net_series.values()) / len(strategy_net_series)
    strategy_net_series["EW PORT"] = ew_port

    return strategy_net_series, common_start, common_end


def build_table(cfg):
    strategy_net_series, common_start, common_end = build_strategy_net_series(cfg)
    strategy_defs = _strategy_defs(cfg)

    full_rows = []
    for label, _ in strategy_defs + [("EW PORT", None)]:
        m = _metrics(strategy_net_series[label].loc[REPORT_START:])
        full_rows.append(dict(name=label, **m))

    regime_rows = []
    for label, _ in strategy_defs + [("EW PORT", None)]:
        series = strategy_net_series[label]
        row = dict(name=label)
        full_m = _metrics(series.loc[REPORT_START:])
        row["full"] = full_m["ir"]
        for rname, start, end in REGIMES:
            sub = series.loc[start:end]
            row[rname] = _metrics(sub)["ir"]
        row["y26"] = _metrics(series.loc["2026-01-01":])["ir"]
        regime_rows.append(row)

    return full_rows, regime_rows, common_start, common_end


def build_window_grid(cfg) -> dict[str, list[dict]]:
    """Per-window (full + every regime + 2026 YTD) full {ret, vol, ir} rows for
    every strategy, keyed the same way the dashboard's window dropdown will
    use ('full', each REGIMES short code lowercased, 'y26'). Unlike
    build_table()'s regime_rows (which keeps IR only, for the heatmap), this
    keeps ret/vol too so the "Full sample"-style table can be redrawn for any
    selected horizon."""
    strategy_net_series, _, _ = build_strategy_net_series(cfg)
    strategy_defs = _strategy_defs(cfg)
    labels = [label for label, _ in strategy_defs] + ["EW PORT"]

    grid: dict[str, list[dict]] = {}
    grid["full"] = [dict(name=label, **_metrics(strategy_net_series[label].loc[REPORT_START:])) for label in labels]
    for rname, start, end in REGIMES:
        key = rname.split("_")[0].lower()
        grid[key] = [dict(name=label, **_metrics(strategy_net_series[label].loc[start:end])) for label in labels]
    grid["y26"] = [dict(name=label, **_metrics(strategy_net_series[label].loc["2026-01-01":])) for label in labels]
    return grid


def _js_row(r: dict) -> str:
    def fmt(v, nd):
        return "null" if pd.isna(v) else f"{v:.{nd}f}"
    return (f"{{name:{r['name']!r}, ret:{fmt(r['ret'],2)}, vol:{fmt(r['vol'],2)}, "
            f"mdd:{fmt(r['mdd'],2)}, ir:{fmt(r['ir'],3)}}}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("asset_class", choices=["energy", "ngl", "metals", "precious"])
    parser.add_argument("--window-grid", action="store_true",
                         help="Print JS-ready {window: [rows]} grid (ret/vol/ir per strategy per window) instead of the text tables.")
    args = parser.parse_args()
    cfg = importlib.import_module(args.asset_class)

    if args.window_grid:
        grid = build_window_grid(cfg)
        window_order = ["full"] + [rname.split("_")[0].lower() for rname, _, _ in REGIMES] + ["y26"]
        print(f"// {args.asset_class}")
        for key in window_order:
            print(f"  {key}: [")
            for r in grid[key]:
                print(f"    {_js_row(r)},")
            print("  ],")
        raise SystemExit(0)

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
