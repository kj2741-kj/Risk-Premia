# Carry Construction Rule: V2 Blend of Short and Long Tenor (plus Momentum: keep default)

> **UPDATE 2026-10-13 (supersedes the sign-vote below).** User decision: Carry V2 now **sums the z-scores of the tenor pairs and takes the sign of the sum**, so a day is flat only if the sum is exactly zero (the sign-vote below was flat whenever the pairs disagreed, 16-33% of days). Carry-Momentum **sums the pairs' raw 20-observation slope changes and takes the sign**. If a pair is missing on a day the last signal is kept (flat only before the first signal). Lag applied once to the combined signal. Implemented in `research/carry_zsum.py`, used by `scripts/final_dashboard/compute_products.py` (`CARRY_COMBINE=vote` reproduces the old rule). Not yet changed: `research/run_regime_table.py`, `research/cross_asset_engine.py`, `dashboard_portfolio_tab.py`, the Streamlit apps and `webapp/` still use the sign-vote / older composites. Alternatives tested and not adopted: standardised pair changes, per-month spread, z-score differences, Carry with no z-score. See `ENGINE_CHANGELOG.md` (2026-10-13).


Rules adopted 2026-10-10 (user decisions). Read this before building or changing any Carry or Momentum sleeve, or any portfolio that contains one. The Carry rule is the main body; the Momentum rule is the short section further down.

## The rule

In portfolio construction, at every level, the Carry sleeve is the **V2 (z-score on carry slope) signal only, blended across the short-tenor and long-tenor pairs**. V1 (carry slope) is not part of the Carry sleeve any more.

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

## Momentum rule: keep the default 3-crossover composite

Decision 2026-10-10 (user): in portfolio construction at every level, Momentum stays as the **current default only**. No change.

- Signal: `sign(mean of sign(MA_fast - MA_slow))` over the three crossovers `(1,20)`, `(5,60)`, `(20,250)`, computed on `F1_raw` (`engine.momentum_composite_position`, `MOMENTUM_PAIRS` in each `research/configs/*.py`), with `shift_n = 1`.
- Do not replace it with a single crossover or a pair of crossovers.
- Reason it was checked: a comparison of the three pairs of two against the default triple (2011-01 to 2026-06, 5 bps incl. roll-day cost, equal weight). The default has the highest IR in Energy (0.510) and NGL (0.896). A pair has the higher IR in Metals (best -0.260 against default -0.419) and Precious (best -0.105 against default -0.290), but Momentum is negative in every version in those two sectors, so there is no case for changing it. The gaps were not tested for significance.
- **Precious rerun on the aligned roll calendar (2026-10-11):** the figures above for Precious were on the old 12-month calendar. On `expiry_calendars_20260701_aligned.xlsx` (Gold, Silver, Platinum, Palladium; 2011-01 to 2026-06) the default is -0.277 (was -0.290), the best pair is still (1,20)+(20,250) at -0.091 (was -0.105), and Momentum is still negative in every version. Decision unchanged.
- Cross-check still open: the default row in that comparison used the same composite function as the dashboard but was not explicitly reconciled against the dashboard's Momentum row.

## What this replaces

The previous default (live in `dashboard_portfolio_tab.py` and `research/cross_asset_engine.py`) is "Combined Carry": for each tenor pair a V1+V2 composite (`sign((sign V1 + sign V2) / 2)`), the two pairs then blended at the signal level. The only change is dropping V1 from each pair.

Carry momentum (V3) is a separate sleeve and is not affected by this rule. It is under its own separate analysis.

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

## Precious on the aligned roll calendar (rerun 2026-10-11)

Dimil111's commit `0b1e8aa` replaced the Precious roll calendar with Bloomberg's contract months (Gold Feb/Apr/Jun/Aug/Oct/Dec, Silver Mar/May/Jul/Sep/Dec, Platinum Jan/Apr/Jul/Oct, Palladium Mar/Jun/Sep/Dec), removing spurious roll events (phase changes per product fell from 987 to 331-495). Same four products, F1-F3, 5 bps incl. roll-day cost, equal weight, 2011-01 to 2026-06. Signals are identical; only the continuous series and roll charges differ.

| Strategy | IR old calendar | IR aligned calendar |
|---|---|---|
| Carry V1 | 0.208 | 0.072 |
| **Carry V2 (the rule)** | 0.090 | -0.000 |
| Carry V1+V2 (old default) | 0.225 | 0.061 |
| Momentum default (3) | -0.290 | -0.277 |

Aligned-calendar Carry V2 by regime: R1 0.536, R2 0.380, R3 -0.887, R4 -0.065. Per product (V2): Gold 0.226, Silver 0.276, Platinum 0.205, Palladium -0.456.

What this shows, and what it does not:
- On Precious the V2-only rule is not better than the old V1+V2 default (0.000 against 0.061 aligned; 0.090 against 0.225 on the old calendar). Precious is the one sector where the rule's evidence is not supportive, and with a single tenor pair there is no blend to help. It was included for consistency, not because the numbers favour it. Not significance-tested.
- Carry IR fell on the aligned calendar in all three versions, even though roll charges are lower. The cause was not investigated here; it comes from the changed continuous series, so Precious Carry results are sensitive to the roll calendar and the old figures should not be quoted.
- Platinum and Palladium F3 liquidity remains the weak point noted in `research/configs/precious.py`.

## Status

**Final_Research_Dashboard.html.** `Analysis/Final_Research_Dashboard.html` (commit `0b1e8aa`) already computes the V2-only Carry rule itself (5 asset classes, equal-weight and inverse-vol, Energy with and without NatGas, combined books). It is a standalone page, not the engine. Its numbers have not been reconciled against the figures in this file or against `research/run_regime_table.py`; do that before quoting both.


**This file is the rule and its specification. The code has not been changed yet.** `research/configs/*.py`, `dashboard_portfolio_tab.py`, `research/cross_asset_engine.py`, `research/run_regime_table.py` and `webapp/` still build Carry as the V1+V2 composite. Anyone implementing the rule should change all of them, plus regenerate every reported number that touches Carry (`python research/run_regime_table.py <metals|energy|precious|ngl>`), rather than hand-patching. Check `git branch --show-current` first: the Streamlit dashboards are on `main` and the React rebuild is on `feature/react-dashboard`.

**Update 2026-10-11 (implementation).** `research/run_regime_table.py` now builds Carry and Carry-Momentum as specified here (V2 only, sign-vote across each product's tenor pairs, lag applied once) and adds an Inverse Vol row; `research/cross_asset_engine.py` has an opt-in `per_product_pairs` flag for per-product long pairs (Precious, Agriculture). Precious and Agriculture now use a short F1-F2 pair plus a long pair per product (see `research/configs/precious.py` and `agri.py`). `dashboard_portfolio_tab.py`, the Streamlit apps and `webapp/` were not changed in that update. Details and validation: `ENGINE_CHANGELOG.md`. The figures earlier in this file predate the 2026-10-11 roll-rule and data changes.

## Cost convention

Roll cost: a position held through a `Roll_LTD` day is charged `tc_bps / 2` (2.5 bp), the same as a one-way trade. A physical roll has two legs, so this is arguably half the real cost. It is the project's existing convention and was not changed. A sensitivity at the full 5 bp has not been run.
