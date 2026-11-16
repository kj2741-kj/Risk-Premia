"""Liquidity penalty for the research dashboard (2026-11-15): two market-impact cost models layered on the dashboard's flat 5 bps cost, for every product.

Inputs: products_trades.pkl (compute_products_v3.py: per product and sleeve, the trade units of each day = |change in position| plus a held-through-roll unit, the
exact quantity the 5 bps cost is charged on; and the lagged 63-day vol of the product's daily log return), and the Calendar-2025 liquidity files
(Analysis/Liquidity_Cal2025_results.csv, NGL on CME plus ICE): x = USD of one-sigma daily risk the 12-month strip trades per day; sigma = the file's 2025 daily vol, so x / sigma is the strip's daily traded notional.

Capital C (USD) is the whole book, fully invested at leverage 1x: the book's position notional is C x LEVERAGE, the same "+-1 unit of notional" the dashboard's returns assume.
Product i gets its book weight w_i = 1 / (7 x products in its bucket) (US Power is not in the book and is not penalised),
split equally over its five sleeves: one full unit of a sleeve's position is N = C x LEVERAGE x w_i / 5 dollars of notional. The market's size is its daily traded notional V = x / sigma_2025
(x = ADV x multiplier x price x sigma, so x / sigma is ADV x multiplier x price, in USD). A trade of u units is a share  P = u x N / V  of one day's strip volume (V is fixed at its Calendar-2025 value for every year).

Extra cost on a day with u trade units, ON TOP of the flat 5 bps and ZERO while the trade is below the threshold P0 = 10% of a day's volume
(a share of the unit notional, in log-return terms, subtracted from the sleeve's net return; sigma = lagged 63-day daily vol; E = max(P - P0, 0), P capped at 1):
  sqrt   : u x Y x sigma x sqrt(E)                       square-root of the excess participation, Y = 1
  linear : u x sigma x a x E,  a = Y / sqrt(P0) = 3.16   linear in the excess participation
(2026-11-15 rev: the earlier models charged below P0 as well, a square root of the whole P and a linear-plus-quadratic "convex"; replaced at the user's request.)
Both models grow with capital, shrink with market volume, and fall on turnover."""
import csv
from pathlib import Path

import numpy as np
import pandas as pd

LEVERAGE = 1.0   # position notional / capital (1x = the capital is fully invested, as in the dashboard's +-1 unit returns)
N_STYLES = 5
Y = 1.0          # impact coefficient (user decision 2026-11-15)
P0 = 0.10        # participation threshold, share of one day's strip volume: no extra cost below it
P_MAX = 1.0      # a trade cannot take more than one day's volume: above it the cost per unit traded stays at its P = 1 level (the rest would be worked over several days)
MODELS = ("sqrt", "linear")
CAPITALS_M = (100, 250, 500, 1000)          # USD millions


def daily_notional_volume(root: Path = Path(".")) -> dict:
    """product name -> USD of notional traded per day by the 12-month strip in Calendar 2025 (= x / sigma_2025)."""
    out = {}
    for r in csv.DictReader(open(root / "Analysis/Liquidity_Cal2025_results.csv", encoding="utf8")):
        out[r["product"]] = float(r["x_strip"]) * 1e6 / float(r["sigma"])
    return out


def per_unit_participation(capital_m: float, weight: float, volume_usd: float) -> float:
    """Share of one day's strip volume that one full unit of a sleeve's position trades."""
    return capital_m * 1e6 * LEVERAGE * weight / N_STYLES / volume_usd


def book_weights(buckets: dict) -> dict:
    """(module, product) -> weight of the product in the book's capital (equal buckets, equal products within a bucket)."""
    w = {}
    for _, (_, members) in buckets.items():
        for m in members:
            w[m] = 1.0 / (len(buckets) * len(members))
    return w


def impact(units: pd.Series, sigma: pd.Series, per_unit_part: float, model: str) -> pd.Series:
    """Extra log-return cost per day. per_unit_part = N / V, the share of a day's volume that one full unit of position trades."""
    P = np.minimum(units * per_unit_part, P_MAX)
    E = np.maximum(P - P0, 0.0)
    sg = sigma.reindex(units.index).ffill().bfill().fillna(float(np.nanmedian(sigma.values)))
    if model == "sqrt":
        return units * Y * sg * np.sqrt(E)
    if model == "linear":
        return units * sg * (Y / np.sqrt(P0)) * E
    raise ValueError(model)


def penalised_nets(nets: dict, trades: dict, sigs: dict, weights: dict, vol: dict, model: str, capital_m: float) -> dict:
    """nets: {(module, product): {style: net log-return series}} -> the same with the model's cost subtracted, for every key that has a weight."""
    out = {}
    for key, styles in nets.items():
        if key not in weights:
            out[key] = styles
            continue
        part = per_unit_participation(capital_m, weights[key], vol[key[1]])
        out[key] = {}
        for st, s in styles.items():
            u = trades[key][st].reindex(s.index).fillna(0.0)
            out[key][st] = s - impact(u, sigs[key], part, model)
    return out


TC_BPS = 5       # the dashboard's flat round-trip cost (research/engine.py; one directional trade pays half)


def netted_nets(nets: dict, trades: dict, sigs: dict, positions: dict, phases: dict, weights: dict, vol: dict, model: str, capital_m: float, variant: str) -> dict:
    """Penalty (and, for variant "b", the flat 5 bps) charged on the PRODUCT's net trade instead of on each sleeve's own trades (2026-11-15).
    A product's five sleeves hold positions of +-1 or 0 each, so the product holds S = sum of the sleeves' positions (in sleeve units). Its trade of the day is
    |change in S| plus, on a roll day, min(|S today|, |S yesterday|) if S keeps its sign (the net position is rolled once). Offsetting sleeves cost nothing; sleeves going the same way add up, so their
    participation, and with it the convex impact, is that of the combined trade. The product's cost (in sleeve-notional units) is
    u_net x sigma x f(E), or for the flat cost u_net x 2.5 bps, and is split back to the sleeves in proportion to their own gross trades of the day (so the sleeve tables still add up).
    variant "a": subtract the netted penalty from the nets (which already carry the per-sleeve flat cost);  variant "b": also replace the per-sleeve flat cost by the netted one.
    model "none" with variant "b" is the flat cost netted and no penalty."""
    assert variant in ("a", "b")
    tc_unit = TC_BPS / 10000.0 / 2.0
    out = {}
    for key, styles in nets.items():
        if key not in weights:
            out[key] = styles
            continue
        pos = pd.DataFrame({st: positions[key][st] for st in styles})
        S = pos.sum(axis=1)
        dS = S.diff().abs()
        dS.iloc[0] = abs(S.iloc[0])
        is_roll = phases[key].reindex(S.index).astype(str).str.startswith("Roll_LTD")
        prev = S.shift(1)
        held = is_roll & (S != 0) & (prev != 0) & (np.sign(S) == np.sign(prev))
        u_net = dS + held.astype(float) * np.minimum(S.abs(), prev.abs()).fillna(0.0)
        gross = pd.DataFrame({st: trades[key][st].reindex(S.index).fillna(0.0) for st in styles})
        G = gross.sum(axis=1)
        share = gross.div(G.where(G > 0), axis=0).fillna(0.0)
        if model == "none":
            pen_total = pd.Series(0.0, index=S.index)
        else:
            part = per_unit_participation(capital_m, weights[key], vol[key[1]])
            pen_total = impact(u_net, sigs[key], part, model)
        out[key] = {}
        for st, s in styles.items():
            adj = -(pen_total * share[st]).reindex(s.index).fillna(0.0)
            if variant == "b":
                adj = adj + (gross[st] * tc_unit - u_net * tc_unit * share[st]).reindex(s.index).fillna(0.0)
            out[key][st] = s + adj
    return out



def netted_nets_dyn(nets: dict, trades: dict, sigs: dict, positions: dict, phases: dict, unit_fn, vol: dict, model: str) -> dict:
    """Variant b with DAILY dollar weights (2026-11-15). unit_fn(key, index, styles) -> DataFrame (index x styles) of the USD millions that ONE unit of each sleeve's position holds on each day
    (= portfolio capital x the product's actual weight that day / 1; for Equal Weight a constant, for Inverse Vol the day's inverse-vol weights). The product's dollar position is
    S = sum over sleeves of (unit dollars x position); its trade of the day is |S today - S yesterday valued at TODAY's unit dollars| (a change of the weights alone is not a trade, as in the dashboard)
    plus, on a roll day, min(|S today|, |S yesterday|) if S keeps its sign. Participation P = trade dollars / daily traded notional V, capped at 1; the extra cost per dollar is sigma x f(E)
    (f as in impact()). The product's dollar cost (this plus the netted flat 5 bps) is split over the sleeves in proportion to their own dollar gross trades and divided by the sleeve's unit dollars,
    so each sleeve's net return stays per unit of its own notional. With a constant unit_fn this equals netted_nets (variant b) exactly. model "none" = the flat cost netted only."""
    tc_unit = TC_BPS / 10000.0 / 2.0
    out = {}
    for key, styles in nets.items():
        pos = pd.DataFrame({st: positions[key][st] for st in styles})
        idx = pos.index
        Nd = unit_fn(key, idx, list(styles))
        Sd = (pos * Nd).sum(axis=1)
        Sp = (pos.shift(1).fillna(0.0) * Nd).sum(axis=1)
        dS = (Sd - Sp).abs()
        is_roll = phases[key].reindex(idx).astype(str).str.startswith("Roll_LTD")
        held = is_roll & (Sd != 0) & (Sp != 0) & (np.sign(Sd) == np.sign(Sp))
        T = dS + held.astype(float) * np.minimum(Sd.abs(), Sp.abs())          # USD millions traded in the net position
        gross = pd.DataFrame({st: trades[key][st].reindex(idx).fillna(0.0) for st in styles})
        den = (gross * Nd).sum(axis=1)                                          # USD millions of gross sleeve trades
        k = (T / den.where(den > 0)).fillna(0.0)                                # netted dollars per gross dollar, same for all sleeves
        if model == "none":
            rate = pd.Series(0.0, index=idx)
        else:
            P = np.minimum(T * 1e6 / vol[key[1]], P_MAX)
            E = np.maximum(P - P0, 0.0)
            sg = sigs[key].reindex(idx).ffill().bfill().fillna(float(np.nanmedian(sigs[key].values)))
            rate = sg * Y * np.sqrt(E) if model == "sqrt" else sg * (Y / np.sqrt(P0)) * E
        out[key] = {}
        for st, s in nets[key].items():
            adj = (gross[st] * tc_unit - gross[st] * k * (tc_unit + rate)).reindex(s.index).fillna(0.0)
            out[key][st] = s + adj
    return out
