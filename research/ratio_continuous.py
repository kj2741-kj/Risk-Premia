"""
research/ratio_continuous.py
==============================
Ratio (multiplicative) back-adjusted continuous F1 price series, for LOG-
RETURN based research (portfolio construction, cross-asset comparison) --
per the user's decision (2026-07-23) to switch the research pipeline to
Bogorad's own log-return methodology so Metals/Precious/Energy/NGL results
can be combined cross-asset without a price-level-scale distortion (raw
dollar PnL is dominated by whichever product has the highest price level --
demonstrated empirically: Copper's PnL swing was ~3x Aluminium/Lead/Zinc's
in a naive equal-weight combination, corr 0.90 vs 0.56-0.63).

This is a SEPARATE series from the dashboards' own F1_continuous
(scripts/rolling_continuous.py), which is ADDITIVELY back-adjusted (built
for dollar PnL via .diff()) and confirmed by its own docstring to go
negative for a majority of history on several products (Aluminium 75%,
Nat Gas 88%, Fuel Oil 65%, WTI 42%) -- fatal for log returns, which are
undefined on a non-positive price. Reuses the SAME roll-date/calendar
machinery (_compute_roll_dates, load_metal_prices, load_metal_calendar --
pure calendar logic, not the risky additive-vs-ratio part), replacing only
the stitching loop: every "+delta" additive splice becomes a "*ratio"
multiplicative splice. This preserves PERCENTAGE continuity across rolls
instead of DOLLAR continuity, and stays positive throughout as long as the
underlying raw price itself never goes non-positive.

Known open edge case, not solved here: WTI traded briefly negative on
2020-04-20 (a real, famous event) -- ratio adjustment breaks on a zero/
negative raw price the same way log returns do. Not an issue for Metals
(physical metal prices don't go negative); to be handled explicitly when
Energy is built, not assumed away.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
_SCRIPTS_DIR = os.path.join(_REPO_ROOT, "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from rolling_continuous import (DEFAULT_CALENDAR_FILE, DEFAULT_ROLL_DAY,  # noqa: E402
                                 METAL_CONFIG, _compute_roll_dates,
                                 load_metal_calendar, load_metal_prices)


def build_rolling_f1_ratio(prices: pd.DataFrame, calendar: pd.DataFrame,
                            roll_day: int = DEFAULT_ROLL_DAY) -> pd.DataFrame:
    """Ratio-adjusted analog of rolling_continuous.build_rolling_f1() -- same
    roll/bridge/F1-F2-tracking phase structure, multiplicative instead of
    additive splicing. Returns columns: F1_raw, F2_raw, F1_continuous_ratio,
    Phase, is_roll_date, is_bridge_date, active_contract."""
    if not 1 <= roll_day <= 10:
        raise ValueError(f"roll_day must be 1-10, got {roll_day}")

    trading_dates = prices.index.normalize()
    price_date_set = set(trading_dates)
    sorted_trading = sorted(price_date_set)

    roll_map, ltd_set, ltd_to_contract = _compute_roll_dates(
        calendar, sorted_trading, price_date_set, n_days_before=roll_day,
    )
    roll_set = set(roll_map.keys())

    f1_arr = prices["F1_raw"].values
    f2_arr = prices["F2_raw"].values
    n = len(trading_dates)

    f1_cont = np.full(n, np.nan)
    phase_labels = np.full(n, "", dtype=object)
    is_roll = np.zeros(n, dtype=bool)
    is_bridge = np.zeros(n, dtype=bool)
    active_cont = np.full(n, "", dtype=object)

    in_f2_phase = False
    prev_f1 = np.nan
    prev_f2 = np.nan
    current_contract = "-"

    def _safe_ratio(numer, denom):
        if np.isnan(numer) or np.isnan(denom) or denom == 0:
            return np.nan
        return numer / denom

    for i, d in enumerate(trading_dates):
        f1v = f1_arr[i]
        f2v = f2_arr[i]

        if in_f2_phase:
            yesterday = trading_dates[i - 1] if i > 0 else None
            if yesterday is not None and yesterday in ltd_set:
                f1_prev = f1_cont[i - 1] if i > 0 else np.nan
                r = _safe_ratio(f1v, prev_f2)
                if not np.isnan(f1_prev) and not np.isnan(r):
                    f1_cont[i] = f1_prev * r
                else:
                    r2 = _safe_ratio(f1v, prev_f1)
                    if not np.isnan(f1_prev) and not np.isnan(r2):
                        f1_cont[i] = f1_prev * r2
                    elif not np.isnan(f1_prev):
                        f1_cont[i] = f1_prev
                    else:
                        f1_cont[i] = f1v if not np.isnan(f1v) else np.nan

                phase_labels[i] = "Bridge"
                is_bridge[i] = True
                if yesterday in ltd_to_contract:
                    current_contract = ltd_to_contract[yesterday]
                active_cont[i] = current_contract
                prev_f1, prev_f2 = f1v, f2v
                in_f2_phase = False
                continue

        if d in roll_set:
            f1_prev = f1_cont[i - 1] if i > 0 else np.nan
            if i == 0 or np.isnan(f1_prev):
                f1_cont[i] = f1v
            else:
                r = _safe_ratio(f2v, prev_f2)
                if not np.isnan(r):
                    f1_cont[i] = f1_prev * r
                else:
                    r2 = _safe_ratio(f1v, prev_f1)
                    f1_cont[i] = f1_prev * r2 if not np.isnan(r2) else f1_prev

            phase_labels[i] = f"Roll_LTD-{roll_day}"
            is_roll[i] = True
            active_cont[i] = roll_map[d]
            current_contract = roll_map[d]
            prev_f1, prev_f2 = f1v, f2v
            in_f2_phase = True
            continue

        if in_f2_phase:
            f1_prev = f1_cont[i - 1] if i > 0 else np.nan
            r = _safe_ratio(f2v, prev_f2)
            if not np.isnan(f1_prev) and not np.isnan(r):
                f1_cont[i] = f1_prev * r
            elif not np.isnan(f1_prev):
                f1_cont[i] = f1_prev
            else:
                f1_cont[i] = f1v
            phase_labels[i] = "F2_Tracking"
            active_cont[i] = current_contract
            prev_f1, prev_f2 = f1v, f2v
            continue

        if i == 0 or np.isnan(f1_cont[i - 1]):
            f1_cont[i] = f1v
        else:
            r = _safe_ratio(f1v, prev_f1)
            f1_cont[i] = f1_cont[i - 1] * r if not np.isnan(r) else f1_cont[i - 1]

        phase_labels[i] = "F1_Tracking"
        active_cont[i] = current_contract
        prev_f1, prev_f2 = f1v, f2v

    out = prices[["F1_raw", "F2_raw"]].copy()
    out["F1_continuous_ratio"] = f1_cont
    out["Phase"] = phase_labels
    out["is_roll_date"] = is_roll
    out["is_bridge_date"] = is_bridge
    out["active_contract"] = active_cont
    return out


def get_metal_rolling_f1_ratio(metal_code: str, futures_file: str, calendar_file: str = DEFAULT_CALENDAR_FILE,
                                config: dict | None = None, roll_day: int = DEFAULT_ROLL_DAY,
                                verbose: bool = False) -> pd.DataFrame:
    """End-to-end ratio-adjusted loader+builder, same call signature as
    rolling_continuous.get_metal_rolling_f1() (additive version)."""
    if config is None:
        config = METAL_CONFIG
    if metal_code not in config:
        raise ValueError(f"Unknown code {metal_code!r}; available: {list(config)}")
    cfg = config[metal_code]
    prices = load_metal_prices(filepath=futures_file, sheet_name=cfg["price_sheet"],
                                f1_col=cfg["f1_col"], f2_col=cfg["f2_col"],
                                data_start_row=cfg["data_start_row"])
    cal = load_metal_calendar(filepath=calendar_file, sheet_name=cfg["calendar_sheet"])
    result = build_rolling_f1_ratio(prices, cal, roll_day=roll_day)
    if verbose:
        rolls = result["is_roll_date"].sum()
        print(f"[{metal_code}] ratio-continuous built: {rolls} roll events, "
              f"{(result['F1_continuous_ratio'] <= 0).sum()} non-positive days")
    return result


def reanchor_f1_continuous_ratio(f1_df: pd.DataFrame) -> pd.DataFrame:
    """Ratio analog of rolling_continuous.reanchor_f1_continuous(): rescales
    F1_continuous_ratio (multiplicatively) so its first valid row equals
    F1_raw's first valid row -- cosmetic only, log-returns (diffs of log
    levels) are invariant to a constant multiplicative rescaling, same as
    the additive version being invariant to a constant additive shift."""
    f1_df = f1_df.copy()
    valid = f1_df["F1_continuous_ratio"].notna() & f1_df["F1_raw"].notna() & (f1_df["F1_continuous_ratio"] > 0)
    if not valid.any():
        return f1_df
    anchor = f1_df.loc[valid].iloc[0]
    scale = anchor["F1_raw"] / anchor["F1_continuous_ratio"]
    f1_df["F1_continuous_ratio"] = f1_df["F1_continuous_ratio"] * scale
    return f1_df
