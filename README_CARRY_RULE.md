# Carry Construction Rule: V2 Blend of Short and Long Tenor

Rule adopted 2026-10-10 (user decision). Read this before building or changing any Carry sleeve or any portfolio that contains one.

## The rule

In portfolio construction, at every level, the Carry sleeve is the **V2 (z-score) signal only, blended across the short-tenor and long-tenor pairs**. V1 (Level) is not part of the Carry sleeve any more.

"Every level" means:
- each asset-class portfolio (Metals, Energy, NGL, Precious), and
- every cross-asset combined portfolio (Cross-Commodity, Cross-Pair, and any later book).

## Definition

For each product and each tenor pair (near, far):

1. `base = (near - far) / near`
2. `z = (base - rolling_mean(base, 252)) / rolling_std(base, 252)`
3. `raw_pair = sign(z)` (this is `engine.raw_signal_carry_v2`, window = `CARRY_ZSCORE_WINDOW` = 252)

Then blend the pairs at the **signal level**:

4. `combo = sign(mean(raw_pair_short, raw_pair_long))` (this is `engine.combine_positions([...], "equal_weight")`). If the two pairs disagree, the position is flat.
5. Apply the execution shift **once** to `combo` (`exec_shift(combo, CARRY_SHIFT_N)`, `shift_n = 1`).
6. Compute log-return PnL with `log_return_daily` (5 bps round-trip, including the roll-day charge).
7. Equal-weight across products.

Do not average the two pairs' already-shifted PnL series. That is a different construction and gives different numbers.

## Tenor pairs by asset class

| Asset class | Short tenor | Long tenor | Products in portfolio |
|---|---|---|---|
| Metals | F1-F3 | F1-F13 | Copper, Aluminium, Lead, Zinc |
| Energy | F1-F3 | F1-F13 | WTI, Brent, RBOB, HeatingOil (**NatGas excluded**) |
| NGL | F2-F4 | F2-F14 | Ethane, Propane, Butane, Isobutane |
| Precious | F1-F3 | none | Gold, Silver, Platinum, Palladium |

Notes:
- **NGL** uses F2-F4 and F2-F14 (the pairs in `research/configs/ngl.py`), not F1-F3 and F1-F13. The NGL Portfolio tab caption in `ngl_dashboard/app.py` still says F4-F15 and is stale.
- **Precious** has only one tenor pair (F1-F3), so there is nothing to blend. Its Carry sleeve is V2 on F1-F3 alone.
- **Energy excludes NatGas** under this rule. The dashboards and `cross_asset_engine.DASHBOARD_PRODUCTS` currently still include it. Singapore Gasoil, Fuel Oil, Ethylene and Propylene stay excluded as before (see `CLAUDE.md`).

## What this replaces

The previous default (live in `dashboard_portfolio_tab.py` and `research/cross_asset_engine.py`) is "Combined Carry": for each tenor pair a V1+V2 composite (`sign((sign V1 + sign V2) / 2)`), the two pairs then blended at the signal level. The only change is dropping V1 from each pair.

Carry-Momentum (V3) is a separate sleeve and is not affected by this rule. It is under its own separate analysis.

## Evidence behind the rule

Run on 2011-01 to 2026-06, 5 bps including roll-day cost, `shift_n = 1`, equal weight across products. Source: the 2026-10-10 Carry decomposition (V1, V2 and blend per tenor pair, then both pairs).

| Sector | V2 both pairs: Return / Vol / MDD / IR | Old default: Return / Vol / MDD / IR |
|---|---|---|
| Metals | 1.52 / 12.2 / -40.1 / **0.124** | -0.12 / 12.3 / -47.1 / -0.010 |
| Energy (ex NatGas) | 8.20 / 29.6 / -56.9 / **0.277** | 6.54 / 28.1 / -55.2 / 0.233 |
| NGL | 15.52 / 22.7 / -41.2 / 0.683 | 16.34 / 22.9 / -44.6 / **0.714** |

Read this honestly:
- V2 beats the old default in Metals and Energy and is slightly behind in NGL (IR -0.031). By product it wins 8 of 12.
- The gaps are small and were not tested for significance, out-of-sample or after multiple-testing correction. The rule is a decision to simplify Carry, not a proven improvement.
- The edge is regime-dependent. V2 is weaker than the old default in the 2022-onward regime in Energy and NGL, and collapses in NGL during 2020-21 (IR 0.003 against 0.750).
- NGL tenors are provisional: F2 brings back the heating-season seasonality that F4 was originally chosen to avoid.

## Status

**This file is the rule and its specification. The code has not been changed yet.** `research/configs/*.py`, `dashboard_portfolio_tab.py`, `research/cross_asset_engine.py`, `research/run_regime_table.py` and `webapp/` still build Carry as the V1+V2 composite. Anyone implementing the rule should change all of them, plus regenerate every reported number that touches Carry (`python research/run_regime_table.py <metals|energy|precious|ngl>`), rather than hand-patching. Check `git branch --show-current` first: the Streamlit dashboards are on `main` and the React rebuild is on `feature/react-dashboard`.

## Cost convention

Roll cost: a position held through a `Roll_LTD` day is charged `tc_bps / 2` (2.5 bp), the same as a one-way trade. A physical roll has two legs, so this is arguably half the real cost. It is the project's existing convention and was not changed. A sensitivity at the full 5 bp has not been run.
