# Liquidity metric (VaR-linked): research note

Status: design agreed 2026-10-18, nothing implemented yet. Intended for the published paper, so the logic and the data handling must be consistent and verifiable.

## 1. What the metric answers

If we hold a fixed amount of risk in a product, how large is that position compared with what the market normally trades in a day? Raw volume cannot compare products (a gold contract and a tin contract carry different dollar risk), so position size is first converted to a common unit, risk, and only then compared with market volume.

## 2. Definition

For each product i, over a window W:

1. Dollar risk of one contract: `c_i = m_i * P_i * sigma_i`
   - `m_i` contract multiplier (units per lot), `P_i` unadjusted price level, `sigma_i` standard deviation of daily log returns over W.
2. Risk budget `R`, defined through VaR (section 3): `R = VaR / z_alpha`.
3. Contracts needed: `N_i = R / c_i`
4. Liquidity metric: `L_i = N_i / ADV_i`, the position as a share of one average day of volume. Lower is more liquid.

Derived quantities:
- Capacity: `R*_i = p * ADV_i * c_i`, the largest 1-sigma risk the product absorbs at participation `p` (default 10%). Convert to a VaR budget with `z_alpha`.
- Days to exit: `h_i = N_i / (p * ADV_i) = L_i / p`.
- Portfolio ceiling: the smallest `R*_i` across the book is the AUM ceiling, and the product behind it is the binding constraint.

Ranking of products by `L_i` does not depend on `R`, because `N_i` is linear in `R`. `R` only decides where the "too illiquid" line falls. Thresholds (for example below 1% easy, above 10% not tradable quickly) are conventions and must be justified in the paper.

## 3. Link to VaR

Under parametric (normal) VaR, `VaR_alpha = z_alpha * sigma_dollar`, so `R = VaR / z_alpha` and

`N_i = VaR / (z_alpha * m_i * P_i * sigma_i)`

with `z = 1.645` (95%) and `z = 2.326` (99%). Headline definition proposed: a **99% one-day VaR budget** per commodity. Example: a 1,000,000 USD budget gives `R` of about 430,000 USD of 1-sigma risk. This replaces the earlier ambiguity between "100k" and "1M" in the working notes (those differ by about 16x if one reads daily versus annualised risk).

Points to get right:
1. **Fat tails.** Normal VaR understates tail risk for commodities, especially NGL, Tin and Natural Gas. Report normal VaR as the headline and historical simulation (or Cornish-Fisher) as a check, replacing `z` by the empirical quantile ratio per product.
2. **Horizon.** A one-day VaR assumes exit in a day. Where `L` is high, use the liquidation horizon `h` and scale VaR by about `sqrt(h)` (liquidity-adjusted VaR).
3. **Standalone, not portfolio, VaR.** Diversification does not help exit a single market, so this check uses each product's standalone VaR. Portfolio VaR with correlations is the tool for allocating the budget across products.
4. **Volatility estimate.** Same window as ADV (2025 headline). State whether equal-weighted or EWMA; EWMA is closer to desk practice.

## 4. Link to portfolio construction

- Cap a product's weight so `L` stays under a limit, instead of weighting by inverse vol alone.
- Product contract counts in the inverse-vol and equal-weight books equal weight times portfolio VaR budget divided by per-contract risk, so the book's AUM ceiling is the largest portfolio VaR for which every product stays under `p`.
- Group products into liquidity tiers and test whether the flat 5 bps cost assumption is fair for the illiquid ones.
- Use `L` as a basis for dropping or down-weighting thin products (the NGL swaps).

## 5. Data and what is missing

Volume file: `data/Prices_0924/Volume_OpenInterest_F1F3_Updated.xlsx` (to 2026-09-23). One sheet per product, daily since 2005, columns F1/F2/F3 Volume and OpenInt.

Gaps found on 2025 data:
1. **F1 volume is not the contract we hold.** F1 is Bloomberg's nearest contract. The engine rolls on the 5th trading day of the expiry month (`ROLL_RULE` in `research/configs/*.py`). Correct ADV = F1 volume before our roll date and F2 volume from our roll date to Bloomberg's F1 switch, built from the roll calendars. Evidence of the distortion: Gold 2025 F1 mean 87.8k vs median 12.5k; Soybean F1 is small while F2 is large. Only F1 to F3 exists, so whole-curve volume is understated (WTI F1-F3 about 580k a day). Roll-day trading of two legs is a separate roll-liquidity cost.
2. **NGL has almost no exchange volume** (Argus OTC or cleared swaps). 2025 days with a volume print: Isobutane 2 (10 lots), Propane Far East 1, Ethane 19, Butane 19, Propane CIF ARA 7. NaN versus zero is ambiguous (the file has no zeros at all). For NGL use open interest as the denominator and report both versions.
3. **No contract multipliers or price units in the repo.** A verified spec table is needed per product (lot size, price units, currency), sourced from exchange documents. Cents-versus-dollars quoting (sugar, coffee, grains, cattle) is a 100x trap.
4. **Suspect rows.** Fuel Oil 3.5pct Barges (2025 F1 mean 75k, median 2.2k, F1-F3 611k: likely unit or lot mismatch); ICE Gasoil London (about 15 lots a day, looks dead); Singapore Jet Kerosene (data ends 2018); Naphtha (empty sheet).
5. **Not yet checked:** whether the engine's continuous price series is unadjusted (the metric needs the price level).
6. **Universe:** the notes mention "top 15 energy contracts by liquidity". The volume file has 10 energy and 6 NGL sheets, so the source of any further candidates is unresolved.

Treatment decisions to make: NaN as zero versus missing in ADV (report both); mean ADV as headline with median as robustness (roll-day spikes distort the mean); trading-day denominator per market, not a common calendar.

## 6. Extensions

- 2025 snapshot as today's capacity, plus a rolling 252-day point-in-time version aligned to each backtest year (applying 2025 liquidity to a 2012 backtest is anachronistic).
- Flow participation per sleeve: `N * turnover / ADV` (Momentum trades rarely, Skewness more).
- Test the flat 5 bps cost against liquidity tiers.

## 7. Next steps

1. Fix the headline definition (99% one-day VaR budget, normal and historical side by side).
2. Build and verify the contract specification table.
3. Build held-contract ADV from the roll calendars.
4. Confirm the price series is unadjusted for `P`.
5. Pilot on 2025 for all products, then the rolling version.
6. Resolve the NGL treatment and the suspect rows.
