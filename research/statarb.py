"""
research/statarb.py
=====================
StatArb sleeve: Bogorad's threshold-on-MA rule applied to 8 cross-asset-class
spreads (Ethane-NatGas, Propane-Ethane, Propane-Butane, RBOB-Butane,
RBOB-Brent, Brent-HeatingOil, HeatingOil-WTI, WTI-Brent), shared by Energy and
NGL (research/configs/energy.py's STATARB_PAIRS documents the pair list; the
actual spread/PnL construction lives here instead, since the per-pair unit
conversion and two-leg PnL convention don't fit either config file's simple
single-asset-class load_curve() pattern).

TWO SEPARATE CONCERNS, deliberately not conflated:
  1. SIGNAL (position): needs the spread LEVEL in economically comparable
     units (e.g. RBOB-Brent must both be $/bbl to represent a real crack
     margin) -- unit conversions below exist for this step only.
  2. PnL: a real pairs trade holds two separate contracts (long one, short
     the other) at unit notional each. Its log-return PnL is therefore
     position * (log-return of leg A - log-return of leg B), each leg's own
     native-unit log return -- log returns are unit-invariant
     (log(k*x_t / k*x_{t-1}) == log(x_t/x_{t-1})), so NO conversion is
     needed or applied here, only for the signal-level spread above. This
     also sidesteps the "log of a spread that can be negative" problem
     entirely: log is only ever taken of each leg's own always-positive
     price, never of the spread level itself (see project memory,
     2026-07-24 WTI-negative-price investigation, for why this matters).

TRANSACTION COSTS: charged on BOTH legs of the pair (a real pairs trade
executes two contracts), i.e. tc_bps/10000 * |position change| per day --
double the single-instrument convention used elsewhere in this pipeline
(tc_bps/10000/2), since two legs are traded simultaneously, not one.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIGS_DIR = os.path.join(_THIS_DIR, "configs")
if _CONFIGS_DIR not in sys.path:
    sys.path.insert(0, _CONFIGS_DIR)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import energy as energy_cfg  # noqa: E402
import ngl as ngl_cfg  # noqa: E402
from engine import statarb_spread_position  # noqa: E402

CFG = {"energy": energy_cfg, "ngl": ngl_cfg}

GAL_TO_BBL = 42.0
CENTS_TO_DOLLARS = 0.01
ETHANE_MMBTU_PER_GAL = 66000.0 / 1_000_000.0  # ~0.066 MMBtu per gallon of ethane (approx heating value)

SPREAD_LEGS: dict[str, tuple[tuple[str, str, str], tuple[str, str, str]]] = {
    "Ethane-NatGas":    (("ngl", "Ethane", "F1"), ("energy", "NatGas", "F1")),
    "Propane-Ethane":   (("ngl", "Propane", "F1"), ("ngl", "Ethane", "F1")),
    "Propane-Butane":   (("ngl", "Propane", "F1"), ("ngl", "Butane", "F1")),
    "RBOB-Butane":      (("energy", "RBOB", "F1"), ("ngl", "Butane", "F1")),
    "RBOB-Brent":       (("energy", "RBOB", "F1"), ("energy", "Brent", "F1")),
    "Brent-HeatingOil": (("energy", "Brent", "F1"), ("energy", "HeatingOil", "F1")),
    "HeatingOil-WTI":   (("energy", "HeatingOil", "F1"), ("energy", "WTI", "F1")),
    "WTI-Brent":        (("energy", "WTI", "F1"), ("energy", "Brent", "F1")),
}

# Pairs needing the extra $/gal -> $/bbl step (x42) on top of the cents->$
# conversion, because the OTHER leg is a $/bbl crude benchmark. RBOB-Butane
# stays in $/gal (Butane's own native unit -- a blending-economics
# comparison, not a crack-margin one) so it does NOT get this extra step.
_NEEDS_BBL_STEP: dict[str, set[str]] = {
    "RBOB-Brent": {"RBOB"},
    "Brent-HeatingOil": {"HeatingOil"},
    "HeatingOil-WTI": {"HeatingOil"},
}


def _leg_raw(asset: str, product: str, tenor: str) -> pd.Series:
    """Raw (native-sheet-unit) tenor price series for one StatArb leg."""
    curve = CFG[asset].load_curve(product)
    return curve[tenor].dropna()


def _leg_converted_for_signal(asset: str, product: str, tenor: str) -> pd.Series:
    """Same series, converted toward a like-for-like SPREAD LEVEL comparison
    (concern #1 above). RBOB/Heating Oil are quoted in cents/gallon on the
    sheet; Ethane in $/gallon needs a BTU-equivalent conversion to compare
    against Nat Gas's $/MMBtu quote."""
    s = _leg_raw(asset, product, tenor)
    if product in ("RBOB", "HeatingOil"):
        return s * CENTS_TO_DOLLARS  # cents/gal -> $/gal
    if product == "Ethane":
        return s / ETHANE_MMBTU_PER_GAL  # $/gal -> $/MMBtu
    return s


def build_spread_level(label: str) -> pd.Series:
    """Unit-consistent spread LEVEL (leg A - leg B), for signal generation only."""
    (asset_a, prod_a, ten_a), (asset_b, prod_b, ten_b) = SPREAD_LEGS[label]
    a = _leg_converted_for_signal(asset_a, prod_a, ten_a)
    b = _leg_converted_for_signal(asset_b, prod_b, ten_b)
    bbl_legs = _NEEDS_BBL_STEP.get(label, set())
    if prod_a in bbl_legs:
        a = a * GAL_TO_BBL
    if prod_b in bbl_legs:
        b = b * GAL_TO_BBL
    idx = a.index.intersection(b.index)
    return (a.reindex(idx) - b.reindex(idx)).dropna()


def build_leg_logreturns(label: str) -> tuple[pd.Series, pd.Series]:
    """Each leg's OWN native-unit log return (unit-invariant, no conversion
    needed -- see module docstring concern #2)."""
    (asset_a, prod_a, ten_a), (asset_b, prod_b, ten_b) = SPREAD_LEGS[label]
    sa = _leg_raw(asset_a, prod_a, ten_a)
    sb = _leg_raw(asset_b, prod_b, ten_b)
    ra = np.log(sa.where(sa > 0)).diff()
    rb = np.log(sb.where(sb > 0)).diff()
    return ra, rb


def statarb_position_and_pnl(label: str, lookback: int, threshold: float, shift_n: int,
                              tc_bps: int = 5) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (position, gross_logret_pnl, net_logret_pnl) for one spread."""
    spread = build_spread_level(label)
    pos = statarb_spread_position(spread, lookback, threshold, shift_n)
    ra, rb = build_leg_logreturns(label)
    idx = pos.index.intersection(ra.index).intersection(rb.index)
    pos = pos.reindex(idx).fillna(0.0)
    ra, rb = ra.reindex(idx).fillna(0.0), rb.reindex(idx).fillna(0.0)
    leg_diff = ra - rb
    gross = pos * leg_diff
    chg = pos.diff().abs()
    if len(chg):
        chg.iloc[0] = abs(pos.iloc[0])
    tc = chg * (tc_bps / 10000.0)  # both legs traded -> full tc_bps, not /2
    net = gross - tc
    return pos, gross, net


def metrics(net: pd.Series) -> dict:
    a = net.dropna()
    if len(a) < 20 or a.std(ddof=1) == 0:
        return dict(ret=np.nan, vol=np.nan, ir=np.nan)
    ret = float(a.mean() * 252)
    vol = float(a.std(ddof=1) * np.sqrt(252))
    return dict(ret=ret * 100, vol=vol * 100, ir=(ret / vol) if vol > 0 else np.nan)


def _regime_row(name: str, net: pd.Series) -> dict:
    from regimes import REGIMES  # noqa: E402
    row = {"name": name, "full": metrics(net)["ir"]}
    for rname, start, end in REGIMES:
        row[rname] = metrics(net.loc[start:end])["ir"]
    row["y26"] = metrics(net.loc["2026-01-01":])["ir"]
    return row


if __name__ == "__main__":
    from regimes import REGIMES  # noqa: E402

    LOOKBACK, THRESHOLD, SHIFT_N = 20, 0.10, 2
    net_by_label = {}
    full_rows = []
    regime_rows = []
    print(f"{'Spread':<20}{'N days':>9}{'Return%':>10}{'Vol%':>9}{'IR':>8}")
    for label in SPREAD_LEGS:
        _, _, net = statarb_position_and_pnl(label, LOOKBACK, THRESHOLD, SHIFT_N)
        net_by_label[label] = net
        m = metrics(net)
        print(f"{label:<20}{len(net.dropna()):>9}{m['ret']:>10.2f}{m['vol']:>9.2f}{m['ir']:>8.3f}")
        full_rows.append(dict(name=label, **m))
        regime_rows.append(_regime_row(label, net))

    common_idx = None
    for s in net_by_label.values():
        common_idx = s.index if common_idx is None else common_idx.union(s.index)
    ew = None
    for s in net_by_label.values():
        s2 = s.reindex(common_idx).fillna(0.0)
        ew = s2 if ew is None else ew + s2
    ew = ew / len(net_by_label)
    m = metrics(ew)
    print(f"{'EW StatArb (8)':<20}{len(ew.dropna()):>9}{m['ret']:>10.2f}{m['vol']:>9.2f}{m['ir']:>8.3f}")
    full_rows.append(dict(name="EW StatArb (8)", **m))
    regime_rows.append(_regime_row("EW StatArb (8)", ew))

    print("\n=== FDR (Benjamini-Hochberg, q=0.10) across spread x window grid ===")
    from scipy import stats as sstats  # noqa: E402
    from stats import bh_fdr  # noqa: E402

    windows = [("Full", None, None)] + list(REGIMES)
    pvals = {}
    for label, net in list(net_by_label.items()) + [("EW StatArb (8)", ew)]:
        for wname, start, end in windows:
            sub = net if start is None else net.loc[start:end]
            a = sub.dropna()
            if len(a) < 20 or a.std(ddof=1) == 0:
                continue
            _, p = sstats.ttest_1samp(a, 0.0)
            pvals[f"{label} | {wname}"] = p
    survivors = bh_fdr(pvals, q=0.10)
    print(f"Cells tested: {len(pvals)}, survivors at q=0.10: {len(survivors)}")
    for label in sorted(survivors, key=lambda l: pvals[l]):
        print(f"  SURVIVES: {label}  p={pvals[label]:.5f}")

    print("\n=== JS-ready rows ===")
    for r in full_rows:
        print(f"  {{name:{r['name']!r}, ret:{r['ret']:.2f}, vol:{r['vol']:.2f}, ir:{r['ir']:.3f}}},")
    print()
    from regimes import REGIMES  # noqa: E402
    for r in regime_rows:
        parts = [f"name:{r['name']!r}", f"full:{r['full']:.3f}"]
        for rname, _, _ in REGIMES:
            v = r[rname]
            parts.append(f"{rname.split('_')[0].lower()}:{'null' if pd.isna(v) else round(v,3)}")
        parts.append(f"y26:{'null' if pd.isna(r['y26']) else round(r['y26'],3)}")
        print("  {" + ", ".join(parts) + "},")
