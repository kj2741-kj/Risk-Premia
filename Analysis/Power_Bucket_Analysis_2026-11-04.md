# US Power bucket: data, expiry and roll alignment, liquidity, risk-premia sleeves (2026-11-04)

Files: `data/Emissions_1029/PJM_Power_Futures.xlsx`, `US_Power_Futures.xlsx` (Bloomberg pull 2026-11-03). Code: `research/configs/power.py`, `scripts/make_power_calendars.py`, `scripts/power/` (`power_validate.py`, `power_pipeline.py`, `power_liquidity.py`, `power_report.py`). Prices cut at 2026-09-30 (the dashboard's tag 0930).

## 1. How many series are possible

| Family | Series | History | Tenors | Usable for the strategies |
|---|---|---|---|---|
| ICE PJM Western Hub RT, peak and off-peak | 2 | 2015-01-02 to 2026-11-02 | F1-F122 | Yes |
| ICE ERCOT North 345KV RT, peak and off-peak | 2 | 2015-01-02 to 2026-11-02 | F1-F48 | Yes |
| ICE MISO Indiana Hub RT, peak and off-peak | 2 | 2015-01-02 to 2026-11-02 | F1-F48 | Yes |
| CME PJM Western Hub RT, peak and off-peak | 2 | 2026-05-11 (122 days) | F1-F110 / F1-F72 | No: too short, and volume and open interest are empty |
| CME ERCOT North RT, peak and off-peak | 2 | 2026-08-31 (45 days) | F1-F48 | No: same |
| 'Active contract' series (single continuation, 10 columns) | 10 | from 2017-01-23 | one price | Not used: no curve, so no Carry or Value |

**Ten generic families are in the files and six are usable: the ICE series, all from 2015-01-02, every tenor quoted from the first day (no gaps in F1).** About 11.7 years of data to 2026-09-30, against 14.7 years for the other buckets, so the dashboard's Full window (from 2012) cannot be reproduced; Section 4 uses 2017 onwards.

**Independent bets.** Daily log-return correlation of the six roll-adjusted series (2017 onwards):

| | PJM Peak | PJM Off-peak | ERCOT Peak | ERCOT Off-peak | MISO Peak | MISO Off-peak |
|---|---|---|---|---|---|---|
| PJM Peak | 1.00 | 0.88 | 0.37 | 0.45 | 0.92 | 0.84 |
| PJM Off-peak | 0.88 | 1.00 | 0.37 | 0.46 | 0.82 | 0.91 |
| ERCOT Peak | 0.37 | 0.37 | 1.00 | 0.73 | 0.38 | 0.37 |
| ERCOT Off-peak | 0.45 | 0.46 | 0.73 | 1.00 | 0.46 | 0.46 |
| MISO Peak | 0.92 | 0.82 | 0.38 | 0.46 | 1.00 | 0.82 |
| MISO Off-peak | 0.84 | 0.91 | 0.37 | 0.46 | 0.82 | 1.00 |

PJM and MISO are near duplicates (0.82 to 0.92) and peak and off-peak of one hub are 0.73 to 0.92, so the six series are about two independent bets (PJM/MISO and ERCOT, correlation about 0.4 between the two).

## 2. Expiry and roll alignment

- **Contract cycle checked (2026-11-04): every series is monthly, not bimonthly.** All ten calendars list every delivery month with no gaps and no duplicates (264 PJM ICE contracts for 2015-2036, 204 ERCOT and MISO ICE for 2015-2031), each year of 2015-2026 has exactly 12 last trade dates, and in the 2026-11-03 snapshot consecutive generics are exactly one month apart (F1 = Nov-2026, F2 = Dec-2026, F13 = Nov-2027). So F2 is the next month, F13 is the same month a year later, and the F1-F12 volume strip is twelve consecutive months. (The snapshot carries one extra trailing row per product, a repeat of the front month.)
- All ICE contracts are monthly and their **last trade date falls inside the delivery month** (the last business day, at most four days before month end, every contract checked). The generic F1 is therefore the contract delivering now, partly settled against realised prices.
- Calendar: `Power_Expiry_Calendars.xlsx` (one sheet per root) built from the EXPIRY_HISTORY sheets in the format `rolling_continuous` reads. Rule: the repo-wide research rule, roll on the **5th trading day of the month in which the last trade date falls**, which here is the 5th trading day of the delivery month; bridge on the day after the last trade date.
- Result: **every roll on the 5th trading day** of the expiry month (141 of 141 for PJM Peak and ERCOT Peak, 140 of 140 for the others), every bridge on the trading day after the last trade date (one per series is missing: the 30-Sep-2026 contract, whose bridge is after the cut), **0 roll fallbacks**.
- Data test of the Bloomberg generic: F1 moves to the next contract the day after the last trade date in 82 to 87% of contracts (3 to 7% on the last trade date itself); it is the best-fitting switch day among six candidates in 49 to 63% (chance 17%).
- Effect: a position holds the next-month contract from the 5th trading day of the previous month, through the last trade date, and is on F1 (the same contract, now in delivery) for the first 4 to 5 trading days of its delivery month, so those days are in a partly settled contract. Rolling on the 2nd trading day instead is tested in Section 4 (the 1st trading day is not usable: the roll lands on the bridge day and the engine then skips it).

## 3. Liquidity, Calendar 2025 (K = USD 1M, 2025 data only)

Same method as the 30-product table (x = ADV x price x sigma x multiplier, USD millions of one-sigma daily risk traded per day; L = K / x in days). ADV is volume summed over F1-F12; 'held' uses only the contract the strategy holds.

| Series | ADV F1-F12 (lots/day) | Days traded | Price (USD/MWh) | Sigma (daily) | Multiplier (MWh) | x (USD m/day) | L (days) | x held (USD m/day) | L held (days) | Rank among 36 |
|---|---|---|---|---|---|---|---|---|---|---|
| PJM Peak | 14,010 | 100% | 59.4 | 3.52% | 340 | 9.96 | 0.100 | 2.79 | 0.36 | 24 |
| ERCOT Peak | 2,627 | 99% | 52.4 | 5.97% | 340 | 2.80 | 0.358 | 0.659 | 1.52 | 26 |
| PJM Off-peak | 3,881 | 99% | 41.7 | 3.37% | 390 | 2.12 | 0.471 | 0.471 | 2.13 | 27 |
| ERCOT Off-peak | 292 | 73% | 39.2 | 4.80% | 390 | 0.214 | 4.667 | 0.032 | 31.68 | 30 |
| MISO Peak | 386 | 98% | 53.2 | 3.05% | 340 | 0.213 | 4.696 | 0.065 | 15.30 | 31 |
| MISO Off-peak | 201 | 86% | 38.0 | 3.38% | 390 | 0.101 | 9.907 | 0.024 | 42.32 | 33 |

For reference (same method): Lead x = 19.3, Palladium 23.9, Propane 4.85, Ethane 0.35, Isobutane 0.006. **Only PJM Peak (x = 10.0) is near the least liquid non-energy products; ERCOT Peak and PJM Off-peak (2.8, 2.1) sit between Butane (1.8) and Propane (4.85); ERCOT Off-peak, MISO Peak and MISO Off-peak (0.21, 0.21, 0.10) are below Ethane (0.35).** On the held contract the figures are lower still (PJM Peak 2.8, MISO Off-peak 0.02). 33 to 68% of the 2025 volume sits beyond F12 (calendar strips), which the strategies do not trade.

Contract size, checked on ice.com on 2026-11-04: all six monthly contracts are 1 MW (1 MW for every hour of the contract period, so 304-368 MWh a lot for peak and 352-417 for off-peak in 2025, as used). The 800 and 50 in the Bloomberg size field are the daily contracts (800 MWh peak, 50 MWh off-peak), which is why the field is inconsistent; the multipliers and the liquidity above are unchanged.

Not measurable: the four CME series. Their VOLUME and OPEN INTEREST sheets contain no values at all (0 non-null cells), although prices are quoted (118 distinct F1 prices in 122 days for PJM Peak).

## 4. Risk-premia sleeves, dashboard parameters

Momentum (1,20)/(5,60)/(20,250), shift 1, on the raw F1; Carry V2: sign of the summed z-scores of F1-F2 and F1-F13 (252 days); Carry-Momentum: summed 20-observation slope changes; Value: F3, 1,260-day average, +-10%, 504 observations minimum; Skewness: 252 days; 5 bps costs, roll days charged; 5th trading day roll; EW across the six series, then EW PORT and Inverse Vol (63 days). **Window: Full = 2017-01-01 to 2026-09-30**, because the data start 2015-01-02 and Value needs two years of F3 (first Value positions 2016-12); P2 2017-2021, P3 2022-2026, 2026 YTD. Information ratio on the full span of each window, as in the dashboard.

**IR, Full 2017-2026**

| | Momentum | Carry | Carry-Mom. | Value | Skewness |
|---|---|---|---|---|---|
| PJM Peak | 0.43 | 0.08 | 0.26 | 0.36 | -0.44 |
| PJM Off-peak | 0.09 | 0.20 | 0.16 | 0.36 | -0.42 |
| ERCOT Peak | 0.36 | 0.67 | -0.10 | 0.33 | 0.12 |
| ERCOT Off-peak | -0.20 | -0.14 | -0.48 | 0.19 | 0.88 |
| MISO Peak | 0.01 | 0.37 | 0.05 | 0.18 | 0.03 |
| MISO Off-peak | -0.10 | -0.03 | 0.05 | 0.57 | -0.47 |
| **EW bucket** | **0.13** | **0.28** | **-0.12** | **0.45** | **-0.11** |

**IR, P2 2017-2021**

| | Momentum | Carry | Carry-Mom. | Value | Skewness |
|---|---|---|---|---|---|
| PJM Peak | 0.23 | 1.27 | 0.18 | 0.15 | -0.67 |
| PJM Off-peak | 0.38 | 0.98 | -0.03 | -0.05 | -0.64 |
| ERCOT Peak | 0.20 | 3.84 | 0.67 | 1.21 | -0.17 |
| ERCOT Off-peak | -0.26 | 0.29 | -0.16 | 0.78 | 0.08 |
| MISO Peak | -0.29 | 0.93 | -0.23 | 0.47 | 0.14 |
| MISO Off-peak | 0.39 | 0.67 | -0.21 | 0.26 | -0.50 |
| **EW bucket** | **0.14** | **2.07** | **0.14** | **0.80** | **-0.58** |

**IR, P3 2022-2026**

| | Momentum | Carry | Carry-Mom. | Value | Skewness |
|---|---|---|---|---|---|
| PJM Peak | 0.63 | -0.42 | 0.33 | 0.54 | -0.30 |
| PJM Off-peak | -0.08 | -0.17 | 0.31 | 0.76 | -0.27 |
| ERCOT Peak | 0.55 | -0.33 | -0.46 | -0.15 | 0.50 |
| ERCOT Off-peak | -0.17 | -0.33 | -0.60 | -0.05 | 1.97 |
| MISO Peak | 0.21 | 0.11 | 0.26 | 0.06 | -0.03 |
| MISO Off-peak | -0.34 | -0.34 | 0.23 | 0.86 | -0.46 |
| **EW bucket** | **0.14** | **-0.43** | **-0.28** | **0.29** | **0.19** |

**IR, 2026 YTD**

| | Momentum | Carry | Carry-Mom. | Value | Skewness |
|---|---|---|---|---|---|
| PJM Peak | -0.14 | -0.00 | 0.36 | 2.02 | -0.64 |
| PJM Off-peak | -0.58 | 0.19 | -0.40 | 6.92 | -0.71 |
| ERCOT Peak | 3.13 | 2.11 | 3.53 | -0.71 | -0.49 |
| ERCOT Off-peak | -0.66 | -0.38 | -0.84 | -0.35 | -0.46 |
| MISO Peak | -0.39 | 0.27 | -0.12 | 0.12 | 0.99 |
| MISO Off-peak | -0.53 | -0.35 | -0.37 | 4.14 | -0.55 |
| **EW bucket** | **-0.42** | **0.23** | **-0.12** | **0.95** | **-0.62** |

**Bucket sleeves and portfolios, Full 2017-2026** (annual return %, volatility %, max drawdown %, IR)

| | Return | Vol | Max DD | IR | P2 IR | P3 IR | 2026 IR |
|---|---|---|---|---|---|---|---|
| Momentum | 7.1 | 53.2 | -71.4 | 0.13 | 0.14 | 0.14 | -0.42 |
| Carry | 14.9 | 53.0 | -87.8 | 0.28 | 2.07 | -0.43 | 0.23 |
| Carry-Mom. | -6.5 | 51.8 | -84.5 | -0.12 | 0.14 | -0.28 | -0.12 |
| Value | 24.1 | 53.4 | -74.8 | 0.45 | 0.80 | 0.29 | 0.95 |
| Skewness | -5.2 | 48.9 | -88.2 | -0.11 | -0.58 | 0.19 | -0.62 |
| EW PORT | 6.2 | 27.7 | -44.0 | 0.23 | 0.82 | -0.09 | -0.29 |
| Inverse Vol | 5.7 | 26.6 | -42.8 | 0.22 | 0.73 | -0.05 | -0.52 |

**Log-return Sharpe of the bucket sleeves** (mean / standard deviation x sqrt 252 of the daily log returns). The dashboard's IR divides the compounded annual return by volatility, which exaggerates large up-years when volatility is 50% or more; this is the plain measure.

| | Full 2017-2026 | P2 | P3 | 2026 YTD |
|---|---|---|---|---|
| Momentum | 0.13 | 0.14 | 0.13 | -0.52 |
| Carry | 0.26 | 1.54 | -0.51 | 0.23 |
| Carry-Mom. | -0.13 | 0.14 | -0.31 | -0.14 |
| Value | 0.42 | 0.71 | 0.28 | 0.78 |
| Skewness | -0.11 | -0.65 | 0.18 | -0.94 |
| EW PORT | 0.22 | 0.76 | -0.09 | -0.32 |
| Inverse Vol | 0.21 | 0.69 | -0.05 | -0.58 |

Average pairwise correlation of the six products' returns within a sleeve: Momentum 0.34, Carry 0.32, Carry-Mom. 0.30, Value 0.44, Skewness 0.25.

**Sensitivities (EW bucket IR; Full / P2 / P3 / 2026)**

| Variant | Full | P2 | P3 | 2026 |
|---|---|---|---|---|
| Roll on the 2nd trading day, Momentum (5th: 0.13) | 0.16 | 0.15 | 0.17 | -0.31 |
| Roll on the 2nd trading day, Carry (5th: 0.28) | 0.52 | 2.27 | -0.24 | 0.54 |
| Roll on the 2nd trading day, Carry-Mom. (5th: -0.12) | 0.10 | 0.40 | -0.07 | 0.03 |
| Roll on the 2nd trading day, Value (5th: 0.45) | 0.46 | 0.91 | 0.23 | 0.80 |
| Roll on the 2nd trading day, Skewness (5th: -0.11) | -0.20 | -0.69 | 0.07 | -0.60 |
| Roll on the 2nd trading day, EW PORT (5th: 0.23) | 0.36 | 0.99 | 0.04 | -0.10 |
| Momentum (continuous series) | 0.47 | 1.07 | 0.16 | -0.70 |
| Carry F1-F2 only | -0.04 | 0.79 | -0.43 | 2.36 |
| Carry F1-F13 only | 0.34 | 1.69 | -0.30 | -0.33 |

Seasonality of the positions (R-squared of the position on calendar-month dummies, 2017 onwards): Momentum 0.11-0.18, Carry 0.14-0.18, Carry-Momentum 0.10-0.16, Value 0.18-0.39, Skewness 0.01-0.04. The signals are partly, not mainly, calendar rules.
