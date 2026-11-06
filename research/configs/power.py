"""
research/configs/power.py
===========================
Config for the US POWER bucket (added 2026-11-04), run separately from the "Power, Emissions and Nat Gas" bucket: monthly real-time power futures on the PJM Western Hub,
ERCOT North 345KV and MISO Indiana Hub, peak and off-peak, ICE. Mirrors configs/emissions.py: same signal forms, same engine, nothing new in the shared engine.

DATA: data/Emissions_1029/PJM_Power_Futures.xlsx and US_Power_Futures.xlsx (Bloomberg pull of 2026-11-03; sheets <HUB>_ICE_<PK|OFF>_PX / _VOL / _OI, F1..Fn) and
data/Emissions_1029/Power_Expiry_Calendars.xlsx (built by scripts/make_power_calendars.py from the EXPIRY_HISTORY sheets). Prices are USD/MWh.

SERIES. Ten generic families are in the files; six are usable: the ICE PJM, ERCOT and MISO peak and off-peak series, all from 2015-01-02 (F1..F122 for PJM, F1..F48 for ERCOT and MISO,
every tenor quoted from the first day). The four CME series (PJM peak and off-peak from 2026-05-11, ERCOT peak and off-peak from 2026-08-31) have 122 and 45 days of history, too short for
any strategy (Momentum needs 250 days, Carry 252 plus a lag, Value 504 plus 1,260 for the full lookback); they are listed in CME_SERIES for the liquidity table only.

CONTRACTS AND ROLLS. Monthly contracts whose LAST TRADE DATE FALLS IN THE DELIVERY MONTH itself (the last business day, or within four days of month end, every contract checked). Bloomberg's
generic F1 is therefore the contract delivering in the current month, partly realised; it moves to the next contract on the trading day after the last trade date (82 to 87% of the contract
switches test as the day after, 3 to 7% as the last trade date itself, see scripts/power/power_pipeline.py). The repo-wide research rule (roll on the 5th trading day of the month in which each
contract's last trade date falls, ROLL_N = 5) then rolls out of the delivery-month contract on the 5th trading day of its own delivery month: a position always holds the next-month contract
from the 5th trading day of the previous month, through the last trade date, and is back on F1 (the same contract) for the first five trading days of the delivery month. No position is held in a
partly settled contract after its 5th delivery-month trading day.

CARRY: short pair F1-F2 plus the pair 12 months out, F1-F13 (monthly chain, the same convention as TTF); summed z-scores, 252-day window (research/carry_zsum.py).
OTHER SETTINGS as every other bucket: Momentum (1,20)/(5,60)/(20,250), shift 1; Carry-Momentum horizon 20; Value F3, 1260-day average, +-10%, 504 observations minimum; Skewness 252 days; 5 bps costs
with roll days charged (log_return_daily).
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_RESEARCH_DIR = os.path.dirname(_THIS_DIR)
_REPO_ROOT = os.path.dirname(_RESEARCH_DIR)
_SCRIPTS_DIR = os.path.join(_REPO_ROOT, "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from rolling_continuous import DATA_DIR, get_metal_rolling_f1  # noqa: E402
from ratio_continuous import get_metal_rolling_f1_ratio, reanchor_f1_continuous_ratio  # noqa: E402
from rolling_continuous import reanchor_f1_continuous  # noqa: E402

ASSET_CLASS = "Power"

POWER_DIR = os.path.join(DATA_DIR, "Emissions_1029")
PJM_FILE = os.path.join(POWER_DIR, "PJM_Power_Futures.xlsx")
US_FILE = os.path.join(POWER_DIR, "US_Power_Futures.xlsx")
CALENDAR_FILE = os.path.join(POWER_DIR, "Power_Expiry_Calendars.xlsx")

PRODUCTS = ["PJM_Peak", "PJM_OffPeak", "ERCOT_Peak", "ERCOT_OffPeak", "MISO_Peak", "MISO_OffPeak"]
LABELS = {"PJM_Peak": "PJM Western Hub, real-time peak (ICE)", "PJM_OffPeak": "PJM Western Hub, real-time off-peak (ICE)",
          "ERCOT_Peak": "ERCOT North 345KV, real-time peak (ICE)", "ERCOT_OffPeak": "ERCOT North 345KV, real-time off-peak (ICE)",
          "MISO_Peak": "MISO Indiana Hub, real-time peak (ICE)", "MISO_OffPeak": "MISO Indiana Hub, real-time off-peak (ICE)"}
METAL_CODES = {"PJM_Peak": "ZLS", "PJM_OffPeak": "ZLL", "ERCOT_Peak": "YVY", "ERCOT_OffPeak": "YVW", "MISO_Peak": "ZJD", "MISO_OffPeak": "ZJB"}
# per series: workbook, price sheet prefix (the _VOL and _OI sheets share it)
SHEETS = {"PJM_Peak": (PJM_FILE, "ICE_PK"), "PJM_OffPeak": (PJM_FILE, "ICE_OFF"),
          "ERCOT_Peak": (US_FILE, "ERC_ICE_PK"), "ERCOT_OffPeak": (US_FILE, "ERC_ICE_OFF"),
          "MISO_Peak": (US_FILE, "MISO_ICE_PK"), "MISO_OffPeak": (US_FILE, "MISO_ICE_OFF")}
# too short for any strategy (see the docstring); used by the liquidity table only
CME_SERIES = {"PJM_Peak_CME": (PJM_FILE, "CME_PK", "OXW"), "PJM_OffPeak_CME": (PJM_FILE, "CME_OFF", "QWO"),
              "ERCOT_Peak_CME": (US_FILE, "ERC_CME_PK", "UQL"), "ERCOT_OffPeak_CME": (US_FILE, "ERC_CME_OFF", "UIW")}

POWER_CONFIG = {code: {"name": LABELS[p], "price_sheet": SHEETS[p][1] + "_PX", "calendar_sheet": code, "f1_col": 1, "f2_col": 2, "data_start_row": 2}
                for p, code in METAL_CODES.items()}
METALS_CONFIG = POWER_CONFIG   # same name as energy.py/emissions.py for uniformity

ANALYSIS_START = "2015-01-02"   # first day of the data, every tenor quoted from it

MOMENTUM_PAIRS: tuple[tuple[int, int], ...] = ((1, 20), (5, 60), (20, 250))
MOMENTUM_SHIFT_N = 1

CARRY_TENOR_PAIRS: list[tuple[str, str]] = [("F1", "F2")]
CARRY_LONG_FAR_BY_PRODUCT: dict[str, str] = {p: "F13" for p in PRODUCTS}   # 12 months out on a monthly chain
CARRY_ZSCORE_WINDOW = 252
CARRY_SHIFT_N = 1

ROLL_RULE = "expiry_month_nth_td"
ROLL_N = 5


def carry_pairs(product: str) -> list[tuple[str, str]]:
    """Carry / Carry-Momentum tenor pairs (summed z-scores): F1-F2 plus F1-F13."""
    _check(product)
    pairs = list(CARRY_TENOR_PAIRS)
    far = CARRY_LONG_FAR_BY_PRODUCT.get(product)
    if far is not None and ("F1", far) not in pairs:
        pairs.append(("F1", far))
    return pairs


CARRY_MOMENTUM_HORIZON = 20
CARRY_MOMENTUM_SHIFT_N = 1

VALUE_CONTRACT = "F3"
VALUE_LOOKBACK_DAYS = 1260
VALUE_THRESHOLD = 0.10
VALUE_SHIFT_N = 1

STATARB_ENABLED = False

_SHEET_CACHE: dict = {}


def _check(product: str) -> None:
    if product not in METAL_CODES:
        raise ValueError(f"Unknown power product {product!r}; valid: {PRODUCTS}")


def load_sheet(product: str, kind: str = "PX", file: str | None = None, prefix: str | None = None) -> pd.DataFrame:
    """One sheet of the product's workbook (kind PX, VOL or OI) as a Date-indexed frame with columns F1..Fn; cached."""
    if file is None:
        _check(product)
        file, prefix = SHEETS[product]
    key = (file, prefix, kind)
    if key not in _SHEET_CACHE:
        raw = pd.read_excel(file, sheet_name=f"{prefix}_{kind}", header=None, skiprows=2)
        dates = pd.to_datetime(raw[0], errors="coerce")
        cols = {f"F{t + 1}": pd.to_numeric(raw[t + 1], errors="coerce").values for t in range(raw.shape[1] - 1)}
        df = pd.DataFrame(cols, index=dates.values)
        _SHEET_CACHE[key] = df[df.index.notna()].sort_index()
    return _SHEET_CACHE[key].copy()


def _cutoff():
    """Optional last date (env RP_POWER_CUTOFF, e.g. 2026-10-29). The Streamlit Power app sets it so that it ends on the same day as the other apps (data/Prices_1029_merged);
    the research scripts leave it unset and cut at their own date (scripts/power/power_pipeline.py)."""
    return os.environ.get("RP_POWER_CUTOFF") or None


def load_curve(product: str) -> pd.DataFrame:
    """Full raw price curve (PJM F1..F122, ERCOT / MISO F1..F48) from 2015-01-02 (to RP_POWER_CUTOFF when set)."""
    df = load_sheet(product, "PX").loc[ANALYSIS_START:]
    c = _cutoff()
    return df.loc[:c] if c else df


def load_f1_series(product: str) -> pd.DataFrame:
    """F1_raw / F1_continuous / Phase, additive (dollar-PnL) convention; kept for parity, not used by the log-return research pipeline."""
    _check(product)
    df = get_metal_rolling_f1(METAL_CODES[product], futures_file=SHEETS[product][0], calendar_file=CALENDAR_FILE, config=POWER_CONFIG,
                               verbose=False, roll_day=ROLL_N, roll_rule=ROLL_RULE)
    df = reanchor_f1_continuous(df.loc[ANALYSIS_START:])
    c = _cutoff()
    return df.loc[:c] if c else df


def load_f1_series_logret(product: str, roll_n: int = ROLL_N) -> pd.DataFrame:
    """F1_raw / F2_raw / F1_continuous_ratio / log_price / Phase / is_roll_date / is_bridge_date: the log-return series used by the research pipeline.
    `roll_n` (default 5, the research rule) is the trading day of the expiry month on which the roll happens; the pipeline also runs 2 as a sensitivity (1 is not usable: the roll then falls on the bridge day)."""
    _check(product)
    df = get_metal_rolling_f1_ratio(METAL_CODES[product], futures_file=SHEETS[product][0], calendar_file=CALENDAR_FILE, config=POWER_CONFIG,
                                     verbose=False, roll_day=roll_n, roll_rule=ROLL_RULE)
    df = reanchor_f1_continuous_ratio(df.loc[ANALYSIS_START:])
    c = _cutoff()
    if c: df = df.loc[:c]
    price = df["F1_continuous_ratio"].where(df["F1_continuous_ratio"] > 0)
    df["log_price"] = np.log(price)
    return df
