"""
generate_tradebooks.py
=======================
Generates full Excel tradebooks (Performance Summary + day-by-day rows) for
every Stage 2 product x strategy, in the same visual/structural format as the
original Metals-Risk-Premia repo's scripts/momentum_signals.py,
carry_signals.py, value_signals.py: a dark-header "PERFORMANCE SUMMARY" block
followed by a copper-header "TRADEBOOK" block, one workbook per strategy
config, two sheets per workbook (Lag-1 + Same-Day).

Uses the SAME signal math as common_engine.py (the live Stage 2 dashboards),
so these tradebooks reconcile exactly with what Momentum/Carry/Value show
on-screen:
  - Momentum : MA crossover on F1_raw, 3 default benchmark pairs
               (1,20) / (5,60) / (20,250)
  - Carry    : V1 Roll Yield (F1-F2)/F1, V3 Z-score(252d) of that same raw series
  - Value    : V1 MA-reversion, default contract (F8 if available), 5yr lookback, +-10%

PnL is always Position[t] x delta(F1_continuous)[t], regardless of which raw
series the signal is derived from -- identical convention project-wide.

Output: tradebooks/{product_code}/*.xlsx
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, _SCRIPT_DIR)

from rolling_continuous import (
    get_metal_rolling_f1,
    METALS_CONFIG, METALS_FUTURES_FILE, METALS_CALENDAR_FILE,
    ENERGY_CONFIG, ENERGY_FUTURES_FILE, ENERGY_CALENDAR_FILE,
    PRECIOUS_CONFIG, PRECIOUS_FUTURES_FILE, PRECIOUS_CALENDAR_FILE,
)
from common_curve_loader import load_curve_simple, load_curve_legacy_multiheader

TRADEBOOKS_DIR = Path(_REPO_ROOT) / "tradebooks"

MOMENTUM_PAIRS = [(1, 20), (5, 60), (20, 250)]
VALUE_LOOKBACK_DAYS = 1260   # 5yr
VALUE_THRESHOLD = 0.10       # +-10%

PRODUCTS = [
    # Energy
    dict(asset_class="Energy", code="CL", name="WTI Crude (NYMEX)", unit="/bbl",
         config=ENERGY_CONFIG, futures_file=ENERGY_FUTURES_FILE, calendar_file=ENERGY_CALENDAR_FILE, loader="simple"),
    dict(asset_class="Energy", code="CO", name="Brent Crude (ICE)", unit="/bbl",
         config=ENERGY_CONFIG, futures_file=ENERGY_FUTURES_FILE, calendar_file=ENERGY_CALENDAR_FILE, loader="simple"),
    dict(asset_class="Energy", code="XB", name="RBOB Gasoline (NYMEX)", unit="/gal",
         config=ENERGY_CONFIG, futures_file=ENERGY_FUTURES_FILE, calendar_file=ENERGY_CALENDAR_FILE, loader="simple"),
    dict(asset_class="Energy", code="HO", name="Heating Oil ULSD (NYMEX)", unit="/gal",
         config=ENERGY_CONFIG, futures_file=ENERGY_FUTURES_FILE, calendar_file=ENERGY_CALENDAR_FILE, loader="simple"),
    dict(asset_class="Energy", code="NG", name="Nat Gas Henry Hub (NYMEX)", unit="/MMBtu",
         config=ENERGY_CONFIG, futures_file=ENERGY_FUTURES_FILE, calendar_file=ENERGY_CALENDAR_FILE, loader="simple"),
    dict(asset_class="Energy", code="QS", name="Singapore Gasoil (ICE)", unit="/mt",
         config=ENERGY_CONFIG, futures_file=ENERGY_FUTURES_FILE, calendar_file=ENERGY_CALENDAR_FILE, loader="simple"),
    dict(asset_class="Energy", code="FO", name="Fuel Oil 3.5pct Barges (ICE)", unit="/mt",
         config=ENERGY_CONFIG, futures_file=ENERGY_FUTURES_FILE, calendar_file=ENERGY_CALENDAR_FILE, loader="simple"),
    # Metals (LME) -- data/06-30/Metals_Futures_Curve_Updated.xlsx, through 2026-06-30
    dict(asset_class="Metals", code="LP", name="LME Copper", unit="/MT",
         config=METALS_CONFIG, futures_file=METALS_FUTURES_FILE, calendar_file=METALS_CALENDAR_FILE, loader="simple"),
    dict(asset_class="Metals", code="LA", name="LME Aluminium", unit="/MT",
         config=METALS_CONFIG, futures_file=METALS_FUTURES_FILE, calendar_file=METALS_CALENDAR_FILE, loader="simple"),
    # Precious Metals
    dict(asset_class="Precious", code="GC", name="Gold COMEX", unit="/oz",
         config=PRECIOUS_CONFIG, futures_file=PRECIOUS_FUTURES_FILE, calendar_file=PRECIOUS_CALENDAR_FILE, loader="simple"),
    dict(asset_class="Precious", code="SI", name="Silver COMEX", unit="/oz",
         config=PRECIOUS_CONFIG, futures_file=PRECIOUS_FUTURES_FILE, calendar_file=PRECIOUS_CALENDAR_FILE, loader="simple"),
    dict(asset_class="Precious", code="HG", name="Copper CME (HG)", unit="/lb",
         config=PRECIOUS_CONFIG, futures_file=PRECIOUS_FUTURES_FILE, calendar_file=PRECIOUS_CALENDAR_FILE, loader="simple"),
    dict(asset_class="Precious", code="PL", name="Platinum NYMEX", unit="/oz",
         config=PRECIOUS_CONFIG, futures_file=PRECIOUS_FUTURES_FILE, calendar_file=PRECIOUS_CALENDAR_FILE, loader="simple"),
    dict(asset_class="Precious", code="PA", name="Palladium NYMEX", unit="/oz",
         config=PRECIOUS_CONFIG, futures_file=PRECIOUS_FUTURES_FILE, calendar_file=PRECIOUS_CALENDAR_FILE, loader="simple"),
]


# ══════════════════════════════════════════════════════════════════
# EXECUTION TIMING (identical to common_engine.exec_shift)
# ══════════════════════════════════════════════════════════════════

def exec_shift(sigbin: pd.Series, same_day: bool) -> pd.Series:
    return sigbin.shift(1) if same_day else sigbin.shift(2)


# ══════════════════════════════════════════════════════════════════
# PERFORMANCE METRICS (ported from momentum_signals.py compute_performance)
# ══════════════════════════════════════════════════════════════════

def _consecutive(arr: np.ndarray, val: int) -> int:
    best = cur = 0
    for x in arr:
        if x == val:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def compute_performance(daily_pnl: pd.Series, position: pd.Series, f1_cont: pd.Series,
                         same_day: bool, unit_label: str) -> dict:
    f1_prev = f1_cont.shift(1)
    # F1_continuous (additive back-adjustment) can cross exactly zero for some
    # products (confirmed for both WTI Crude and LME Aluminium) -- dividing by
    # that turns one day's return into +-inf, which poisons mean/std for the
    # whole series. common_engine.py's own daily_returns()/pos_metrics_generic()
    # already guard against this; mirror that here.
    with np.errstate(invalid="ignore", divide="ignore"):
        daily_ret = (daily_pnl / f1_prev).replace([np.inf, -np.inf], np.nan)

    active_ret = daily_ret[position != 0].dropna()
    active_pnl = daily_pnl[position != 0].dropna()
    n = len(active_ret)

    ann_ret_pct = float(active_ret.mean() * 252 * 100) if n > 1 else np.nan
    ann_std_pct = float(active_ret.std() * np.sqrt(252) * 100) if n > 1 else np.nan
    sharpe = ann_ret_pct / ann_std_pct if (ann_std_pct and ann_std_pct > 0) else np.nan

    down_ret = active_ret[active_ret < 0]
    sortino_denom = float(down_ret.std() * np.sqrt(252) * 100) if len(down_ret) > 1 else np.nan
    sortino = ann_ret_pct / sortino_denom if (sortino_denom and sortino_denom > 0) else np.nan

    full_ret = daily_ret.fillna(0)
    cum_ret_pct = full_ret.cumsum() * 100
    running_max = cum_ret_pct.cummax()
    max_dd_pct = float((cum_ret_pct - running_max).min())
    calmar = ann_ret_pct / abs(max_dd_pct) if max_dd_pct != 0 else np.nan

    wins = active_pnl[active_pnl > 0]
    losses = active_pnl[active_pnl < 0]
    total_pnl = float(active_pnl.sum())
    avg_win = float(wins.mean()) if len(wins) > 0 else np.nan
    avg_loss = float(losses.mean()) if len(losses) > 0 else np.nan
    pf_num = float(wins.sum())
    pf_den = float(abs(losses.sum()))
    profit_factor = pf_num / pf_den if pf_den > 0 else np.nan
    hit_rate = float((active_ret > 0).mean()) if n > 0 else np.nan

    sign_arr = np.where(active_pnl > 0, 1, -1)
    max_con_w = _consecutive(sign_arr, 1)
    max_con_l = _consecutive(sign_arr, -1)

    pos_note = ("Position[t] = Signal[t-1]  (Same-Day entry, shift-1)" if same_day else
                "Position[t] = Signal[t-2]  (Lag-1 entry, shift-2)")

    # %-of-notional metrics (Ann Return/Std/Max DD) divide by F1_continuous[t-1].
    # For products whose additive back-adjusted F1_continuous crosses through
    # zero (WTI Crude in particular, both from the 2020-04-20 negative-price
    # print and from decades of compounded roll yield), that division blows up
    # on the near-zero days and distorts these three metrics. Sharpe/Sortino/
    # Calmar are ratios of the same distorted series so are far less affected,
    # but flag it rather than silently shipping a nonsensical "883% ann return".
    near_zero_days = int((f1_prev.abs() < f1_prev.abs().median() * 0.05).sum())
    pct_metrics_caveat = ("CAUTION: F1_continuous is near/below zero on "
                          f"{near_zero_days} days in this series -- Ann Return/Std Dev/Max Drawdown "
                          "(%) below can be wildly distorted on those days. Sharpe/Sortino/Calmar are "
                          "far more robust; Total PnL / Avg Win / Avg Loss ($) are unaffected."
                          if near_zero_days > 20 else "n/a -- F1_continuous stays well away from zero.")

    return {
        "Entry Convention": "Same-Day" if same_day else "Lag-1",
        "Start Date": str(daily_pnl.index[0].date()),
        "End Date": str(daily_pnl.index[-1].date()),
        "Total Calendar Days": len(daily_pnl),
        "Active Trading Days": n,
        "Warmup/Flat Days": len(daily_pnl) - n,
        f"Total PnL ({unit_label})": round(total_pnl, 2),
        "Annualized Return (%)": round(ann_ret_pct, 4),
        "Annualized Std Dev (%)": round(ann_std_pct, 4),
        "Sharpe Ratio": round(sharpe, 4),
        "Sortino Ratio": round(sortino, 4),
        "Max Drawdown (%)": round(max_dd_pct, 4),
        "Calmar Ratio": round(calmar, 4),
        "Hit Rate": f"{hit_rate*100:.2f}%",
        f"Avg Win ({unit_label})": round(avg_win, 2),
        f"Avg Loss ({unit_label})": round(avg_loss, 2),
        "Profit Factor": round(profit_factor, 4),
        "Max Consecutive Wins": max_con_w,
        "Max Consecutive Losses": max_con_l,
        "POSITION NOTE": pos_note,
        "PnL NOTE": "Daily_PnL = Position x delta_F1_continuous (roll cost in F1_cont)",
        "TC NOTE": "Not charged in this tradebook -- see dashboard TC filter for net-of-cost figures",
        "PCT_METRICS_CAVEAT": pct_metrics_caveat,
    }


# ══════════════════════════════════════════════════════════════════
# TRADEBOOK BUILDERS (same formulas as common_engine.py)
# ══════════════════════════════════════════════════════════════════

def build_ma_tradebook(f1r: pd.Series, f1c: pd.Series, m: int, n: int, same_day: bool) -> pd.DataFrame:
    ma_m = f1r.rolling(m).mean()
    ma_n = f1r.rolling(n).mean()
    crossover = ma_m - ma_n
    signal = np.sign(crossover)
    position = exec_shift(signal, same_day).fillna(0)

    delta = f1c.diff()
    daily_pnl = position * delta
    cum_pnl = daily_pnl.cumsum()
    mtm = position * f1c

    return pd.DataFrame({
        "Date": f1r.index, "F1_raw": f1r.round(4).values, "F1_continuous": f1c.round(4).values,
        f"MA_{m}": ma_m.round(4).values, f"MA_{n}": ma_n.round(4).values,
        "Crossover": crossover.round(4).values, "Signal": signal.values, "Position": position.values,
        "F1_cont_daily_change": delta.round(4).values, "Daily_PnL": daily_pnl.round(4).values,
        "MTM": mtm.round(4).values, "Cum_PnL": cum_pnl.round(4).values,
    })


def _carry_v1_raw(curve: pd.DataFrame, a: str = "F1", b: str = "F2") -> pd.Series:
    fa, fb = curve[a], curve[b]
    return ((fa - fb) / fa).replace([np.inf, -np.inf], np.nan)


def build_carry_v1_tradebook(curve: pd.DataFrame, f1r: pd.Series, f1c: pd.Series, same_day: bool) -> pd.DataFrame:
    raw = _carry_v1_raw(curve, "F1", "F2").reindex(f1c.index)
    signal = np.sign(raw)
    position = exec_shift(signal, same_day).fillna(0)

    delta = f1c.diff()
    daily_pnl = position * delta
    cum_pnl = daily_pnl.cumsum()
    mtm = position * f1c

    return pd.DataFrame({
        "Date": f1c.index, "F1_raw": f1r.reindex(f1c.index).round(4).values,
        "F1_continuous": f1c.round(4).values, "Carry_Raw_(F1-F2)/F1": raw.round(6).values,
        "Signal": signal.values, "Position": position.values,
        "F1_cont_daily_change": delta.round(4).values, "Daily_PnL": daily_pnl.round(4).values,
        "MTM": mtm.round(4).values, "Cum_PnL": cum_pnl.round(4).values,
    })


def build_carry_v3_tradebook(curve: pd.DataFrame, f1r: pd.Series, f1c: pd.Series, same_day: bool,
                              window: int = 252) -> pd.DataFrame:
    base = _carry_v1_raw(curve, "F1", "F2").reindex(f1c.index)
    z = (base - base.rolling(window).mean()) / base.rolling(window).std()
    signal = np.sign(z.replace([np.inf, -np.inf], np.nan))
    position = exec_shift(signal, same_day).fillna(0)

    delta = f1c.diff()
    daily_pnl = position * delta
    cum_pnl = daily_pnl.cumsum()
    mtm = position * f1c

    return pd.DataFrame({
        "Date": f1c.index, "F1_raw": f1r.reindex(f1c.index).round(4).values,
        "F1_continuous": f1c.round(4).values, "Carry_Raw_(F1-F2)/F1": base.round(6).values,
        f"Zscore_{window}d": z.round(4).values, "Signal": signal.values, "Position": position.values,
        "F1_cont_daily_change": delta.round(4).values, "Daily_PnL": daily_pnl.round(4).values,
        "MTM": mtm.round(4).values, "Cum_PnL": cum_pnl.round(4).values,
    })


def build_value_v1_tradebook(curve: pd.DataFrame, f1r: pd.Series, f1c: pd.Series, contract: str,
                              lookback: int, threshold: float, same_day: bool) -> pd.DataFrame:
    fk = curve[contract].reindex(f1c.index)
    ma = fk.rolling(lookback, min_periods=max(lookback // 2, 60)).mean()
    dev = ((fk - ma) / ma.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    signal = pd.Series(np.where(dev.values < -threshold, 1.0, np.where(dev.values > threshold, -1.0, 0.0)),
                        index=dev.index)
    position = exec_shift(signal, same_day).fillna(0)

    delta = f1c.diff()
    daily_pnl = position * delta
    cum_pnl = daily_pnl.cumsum()
    mtm = position * f1c

    return pd.DataFrame({
        "Date": f1c.index, "F1_raw": f1r.reindex(f1c.index).round(4).values,
        "F1_continuous": f1c.round(4).values, f"{contract}_price": fk.round(4).values,
        f"MA_{lookback}d": ma.round(4).values, "Deviation": dev.round(6).values,
        "Signal": signal.values, "Position": position.values,
        "F1_cont_daily_change": delta.round(4).values, "Daily_PnL": daily_pnl.round(4).values,
        "MTM": mtm.round(4).values, "Cum_PnL": cum_pnl.round(4).values,
    })


# ══════════════════════════════════════════════════════════════════
# EXCEL WRITER (same visual style as momentum_signals.py)
# ══════════════════════════════════════════════════════════════════

_HEADER_FILL = PatternFill("solid", fgColor="2B3A47")
_HEADER_FONT = Font(bold=True, color="FFFFFF", size=10)
_SECTION_FILL = PatternFill("solid", fgColor="4A4A4A")
_SECTION_FONT = Font(bold=True, color="F5C842", size=10)
_METRIC_FILL = PatternFill("solid", fgColor="F2F2F2")
_METRIC_FONT = Font(size=9)
_TB_HEADER_FILL = PatternFill("solid", fgColor="B87333")
_TB_HEADER_FONT = Font(bold=True, color="FFFFFF", size=9)


def _style_cell(cell, fill=None, font=None, align=None):
    if fill: cell.fill = fill
    if font: cell.font = font
    if align: cell.alignment = align


def _write_xl_sheet(wb: Workbook, tb: pd.DataFrame, metrics: dict, sheet_name: str) -> None:
    ws = wb.create_sheet(sheet_name)

    ws.append(["PERFORMANCE SUMMARY", ""])
    _style_cell(ws.cell(ws.max_row, 1), fill=_SECTION_FILL, font=_SECTION_FONT, align=Alignment(horizontal="left"))
    _style_cell(ws.cell(ws.max_row, 2), fill=_SECTION_FILL)

    ws.append(["Metric", "Value"])
    for col in (1, 2):
        _style_cell(ws.cell(ws.max_row, col), fill=_HEADER_FILL, font=_HEADER_FONT)

    for i, (k, v) in enumerate(metrics.items()):
        ws.append([k, v])
        fill = _METRIC_FILL if i % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
        _style_cell(ws.cell(ws.max_row, 1), fill=fill, font=_METRIC_FONT)
        _style_cell(ws.cell(ws.max_row, 2), fill=fill, font=_METRIC_FONT)

    ws.append(["", ""])

    ws.append(["TRADEBOOK"] + [""] * (len(tb.columns) - 1))
    _style_cell(ws.cell(ws.max_row, 1), fill=_SECTION_FILL, font=_SECTION_FONT)

    ws.append(list(tb.columns))
    hdr_row = ws.max_row
    for col_idx in range(1, len(tb.columns) + 1):
        _style_cell(ws.cell(hdr_row, col_idx), fill=_TB_HEADER_FILL, font=_TB_HEADER_FONT,
                    align=Alignment(horizontal="center"))

    for _, row in tb.iterrows():
        vals = []
        for v in row:
            if isinstance(v, float) and np.isnan(v):
                vals.append(None)
            elif hasattr(v, "item"):
                vals.append(v.item())
            else:
                vals.append(v)
        ws.append(vals)

    ws.column_dimensions["A"].width = max(20, max((len(str(k)) for k in metrics.keys()), default=20) + 2)
    for i in range(2, len(tb.columns) + 1):
        ws.column_dimensions[get_column_letter(i)].width = 16
    ws.freeze_panes = ws.cell(hdr_row + 1, 1).coordinate


def save_tradebook_excel(build_fn, f1r, f1c, unit_label, filepath: Path, **kwargs) -> dict:
    """Build both timing conventions, save a 2-sheet workbook, return both metric dicts."""
    tb_same = build_fn(f1r=f1r, f1c=f1c, same_day=True, **kwargs)
    pos_same = pd.Series(tb_same["Position"].values, index=pd.DatetimeIndex(tb_same["Date"]))
    pnl_same = pd.Series(tb_same["Daily_PnL"].values, index=pd.DatetimeIndex(tb_same["Date"]))
    met_same = compute_performance(pnl_same, pos_same, f1c.reindex(pos_same.index), True, unit_label)

    tb_lag = build_fn(f1r=f1r, f1c=f1c, same_day=False, **kwargs)
    pos_lag = pd.Series(tb_lag["Position"].values, index=pd.DatetimeIndex(tb_lag["Date"]))
    pnl_lag = pd.Series(tb_lag["Daily_PnL"].values, index=pd.DatetimeIndex(tb_lag["Date"]))
    met_lag = compute_performance(pnl_lag, pos_lag, f1c.reindex(pos_lag.index), False, unit_label)

    wb = Workbook()
    wb.remove(wb.active)
    _write_xl_sheet(wb, tb_lag, met_lag, "Lag-1 (shift-2)")
    _write_xl_sheet(wb, tb_same, met_same, "Same-Day (shift-1)")
    filepath.parent.mkdir(parents=True, exist_ok=True)
    wb.save(filepath)
    return {"lag": met_lag["Sharpe Ratio"], "same": met_same["Sharpe Ratio"]}


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    TRADEBOOKS_DIR.mkdir(exist_ok=True)
    log_rows = []

    for p in PRODUCTS:
        code, name, unit = p["code"], p["name"], p["unit"]
        print("=" * 78)
        print(f"{p['asset_class']} — {name} ({code})")
        print("=" * 78)

        f1_df = get_metal_rolling_f1(code, futures_file=p["futures_file"], calendar_file=p["calendar_file"],
                                      verbose=False, config=p["config"])
        f1_df = f1_df[f1_df.index.year >= 2006]
        f1r, f1c = f1_df["F1_raw"], f1_df["F1_continuous"]

        if p["loader"] == "simple":
            curve = load_curve_simple(p["futures_file"], p["config"][code]["price_sheet"])
        else:
            curve_data = load_curve_legacy_multiheader(p["futures_file"])
            curve = curve_data[p["config"][code]["price_sheet"]]["prices"]
        curve = curve[curve.index.year >= 2006]

        out_dir = TRADEBOOKS_DIR / code

        # ── Momentum: 3 default benchmark MA pairs ──────────────────────────
        for m, n in MOMENTUM_PAIRS:
            fpath = out_dir / f"Momentum_MA_{m}_{n}.xlsx"
            sh = save_tradebook_excel(build_ma_tradebook, f1r, f1c, unit, fpath, m=m, n=n)
            print(f"  Momentum MA({m},{n})  Lag-1={sh['lag']}  Same-Day={sh['same']}  -> {fpath.name}")
            log_rows.append({"code": code, "name": name, "strategy": f"Momentum MA({m},{n})", **sh})

        # ── Carry: V1 Roll Yield (F1-F2)/F1, V3 Z-score(252d) ───────────────
        if "F1" in curve.columns and "F2" in curve.columns:
            fpath = out_dir / "Carry_V1_RollYield.xlsx"
            sh = save_tradebook_excel(build_carry_v1_tradebook, f1r, f1c, unit, fpath, curve=curve)
            print(f"  Carry V1 (F1-F2)/F1  Lag-1={sh['lag']}  Same-Day={sh['same']}  -> {fpath.name}")
            log_rows.append({"code": code, "name": name, "strategy": "Carry V1", **sh})

            fpath = out_dir / "Carry_V3_Zscore252.xlsx"
            sh = save_tradebook_excel(build_carry_v3_tradebook, f1r, f1c, unit, fpath, curve=curve, window=252)
            print(f"  Carry V3 Z-score(252d)  Lag-1={sh['lag']}  Same-Day={sh['same']}  -> {fpath.name}")
            log_rows.append({"code": code, "name": name, "strategy": "Carry V3", **sh})
        else:
            print("  Carry skipped -- F1/F2 not found in curve.")

        # ── Value: V1 MA-reversion, default contract/lookback/threshold ────
        contracts = [c for c in curve.columns if str(c).startswith("F") and str(c)[1:].isdigit()
                     and int(str(c)[1:]) <= 15]
        if contracts:
            contract = contracts[min(7, len(contracts) - 1)]
            fpath = out_dir / f"Value_V1_{contract}.xlsx"
            sh = save_tradebook_excel(build_value_v1_tradebook, f1r, f1c, unit, fpath,
                                       curve=curve, contract=contract,
                                       lookback=VALUE_LOOKBACK_DAYS, threshold=VALUE_THRESHOLD)
            print(f"  Value V1 {contract} 5yr +-10%  Lag-1={sh['lag']}  Same-Day={sh['same']}  -> {fpath.name}")
            log_rows.append({"code": code, "name": name, "strategy": f"Value V1 {contract}", **sh})
        else:
            print("  Value skipped -- no usable Fk contracts in curve.")

    summary = pd.DataFrame(log_rows)
    summary.to_csv(TRADEBOOKS_DIR / "tradebooks_summary.csv", index=False)
    print("\n" + "=" * 78)
    print(f"Done. {len(log_rows)} tradebooks written under {TRADEBOOKS_DIR.resolve()}")
    print("Summary -> tradebooks/tradebooks_summary.csv")


if __name__ == "__main__":
    main()
