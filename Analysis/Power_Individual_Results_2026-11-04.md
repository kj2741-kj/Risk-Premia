# US Power: individual results for the series with L < 5 days (2026-11-04)

Selection: Calendar-2025 L = K / x below 5 days with K = USD 1M, F1-F12 ADV (the table in `Power_Bucket_Analysis_2026-11-04.md`). Contract size confirmed on ice.com: all six monthly contracts are 1 MW (1 MW for every hour of the contract period), so the multipliers, and the liquidity, are unchanged. MISO Off-peak (L = 9.9) is out. No cross-product combination: each table is one product.

| Product | L (days, F1-F12) | L held contract (days) | x (USD m/day) |
|---|---|---|---|
| PJM Western Hub, peak | 0.10 | 0.4 | 9.96 |
| ERCOT North, peak | 0.36 | 1.5 | 2.80 |
| PJM Western Hub, off-peak | 0.47 | 2.1 | 2.12 |
| ERCOT North, off-peak | 4.67 | 31.7 | 0.21 |
| MISO Indiana Hub, peak | 4.70 | 15.3 | 0.21 |

On the held contract (the one the strategy trades) only PJM Peak, ERCOT Peak and PJM Off-peak stay under 5 days; ERCOT Off-peak (31.7) and MISO Peak (15.3) do not.

Window: Full = 2017-01-01 to 2026-09-30 (the data start 2015-01-02 and Value needs two years of F3). Return = compounded annual return %, Vol = annualised volatility of simple returns %, Max DD = value-based maximum drawdown %, IR = Return / Vol (the dashboard's convention), Sharpe = mean / std x sqrt 252 of the daily log returns.

## PJM Western Hub, peak

| | Ret % | Vol % | Max DD % | IR Full | Sharpe Full | IR P2 | IR P3 | IR 2026 |
|---|---|---|---|---|---|---|---|---|
| Momentum | 33.4 | 76.9 | -78.6 | 0.43 | 0.38 | 0.23 | 0.63 | -0.14 |
| Carry | 5.8 | 76.8 | -96.2 | 0.08 | 0.07 | 1.27 | -0.42 | -0.00 |
| Carry-Momentum | 20.3 | 78.6 | -81.5 | 0.26 | 0.24 | 0.18 | 0.33 | 0.36 |
| Value | 24.6 | 68.2 | -80.2 | 0.36 | 0.34 | 0.15 | 0.54 | 2.02 |
| Skewness | -33.6 | 75.9 | -98.2 | -0.44 | -0.54 | -0.67 | -0.30 | -0.63 |
| EW PORT (5 sleeves) | 7.0 | 37.4 | -46.9 | 0.19 | 0.19 | 0.27 | 0.14 | -0.07 |
| Inverse Vol (5 sleeves) | 6.5 | 37.2 | -46.4 | 0.17 | 0.17 | 0.23 | 0.15 | -0.03 |

## ERCOT North, peak

| | Ret % | Vol % | Max DD % | IR Full | Sharpe Full | IR P2 | IR P3 | IR 2026 |
|---|---|---|---|---|---|---|---|---|
| Momentum | 45.0 | 125.2 | -97.6 | 0.36 | 0.30 | 0.20 | 0.55 | 3.13 |
| Carry | 84.6 | 125.5 | -99.4 | 0.67 | 0.50 | 3.84 | -0.33 | 2.11 |
| Carry-Momentum | -12.2 | 123.9 | -99.9 | -0.10 | -0.11 | 0.66 | -0.45 | 3.53 |
| Value | 39.4 | 119.8 | -98.6 | 0.33 | 0.29 | 1.21 | -0.15 | -0.71 |
| Skewness | 14.6 | 126.6 | -97.9 | 0.12 | 0.11 | -0.17 | 0.50 | -0.49 |
| EW PORT (5 sleeves) | 30.3 | 66.9 | -84.7 | 0.45 | 0.40 | 1.46 | -0.15 | 0.90 |
| Inverse Vol (5 sleeves) | 29.2 | 66.4 | -84.6 | 0.44 | 0.39 | 1.32 | -0.12 | 0.78 |

## PJM Western Hub, off-peak

| | Ret % | Vol % | Max DD % | IR Full | Sharpe Full | IR P2 | IR P3 | IR 2026 |
|---|---|---|---|---|---|---|---|---|
| Momentum | 5.9 | 69.5 | -92.0 | 0.08 | 0.09 | 0.38 | -0.08 | -0.58 |
| Carry | 13.9 | 69.1 | -82.0 | 0.20 | 0.19 | 0.98 | -0.17 | 0.19 |
| Carry-Momentum | 11.2 | 69.6 | -80.0 | 0.16 | 0.16 | -0.03 | 0.31 | -0.40 |
| Value | 21.2 | 59.1 | -76.4 | 0.36 | 0.33 | -0.05 | 0.76 | 6.92 |
| Skewness | -27.6 | 65.9 | -97.9 | -0.42 | -0.48 | -0.64 | -0.27 | -0.71 |
| EW PORT (5 sleeves) | 3.3 | 34.7 | -46.4 | 0.10 | 0.09 | 0.13 | 0.09 | -0.39 |
| Inverse Vol (5 sleeves) | 3.3 | 34.1 | -46.4 | 0.10 | 0.10 | 0.07 | 0.12 | -0.12 |

## ERCOT North, off-peak

| | Ret % | Vol % | Max DD % | IR Full | Sharpe Full | IR P2 | IR P3 | IR 2026 |
|---|---|---|---|---|---|---|---|---|
| Momentum | -18.7 | 92.2 | -97.5 | -0.20 | -0.22 | -0.26 | -0.17 | -0.66 |
| Carry | -12.5 | 92.0 | -98.6 | -0.14 | -0.14 | 0.29 | -0.33 | -0.38 |
| Carry-Momentum | -44.4 | 91.5 | -99.8 | -0.49 | -0.62 | -0.16 | -0.60 | -0.84 |
| Value | 17.0 | 88.8 | -83.2 | 0.19 | 0.18 | 0.78 | -0.05 | -0.35 |
| Skewness | 85.7 | 97.4 | -89.9 | 0.88 | 0.66 | 0.08 | 1.97 | -0.46 |
| EW PORT (5 sleeves) | -3.0 | 51.7 | -78.0 | -0.06 | -0.06 | 0.16 | -0.18 | -1.22 |
| Inverse Vol (5 sleeves) | -2.8 | 51.2 | -78.1 | -0.06 | -0.05 | 0.20 | -0.19 | -1.21 |

## MISO Indiana Hub, peak

| | Ret % | Vol % | Max DD % | IR Full | Sharpe Full | IR P2 | IR P3 | IR 2026 |
|---|---|---|---|---|---|---|---|---|
| Momentum | 0.5 | 68.5 | -78.9 | 0.01 | 0.01 | -0.29 | 0.21 | -0.39 |
| Carry | 26.6 | 71.9 | -75.1 | 0.37 | 0.34 | 0.93 | 0.11 | 0.27 |
| Carry-Momentum | 3.7 | 68.7 | -77.4 | 0.05 | 0.05 | -0.23 | 0.25 | -0.12 |
| Value | 10.9 | 61.6 | -80.8 | 0.18 | 0.17 | 0.47 | 0.06 | 0.12 |
| Skewness | 2.2 | 69.6 | -97.7 | 0.03 | 0.03 | 0.14 | -0.03 | 0.99 |
| EW PORT (5 sleeves) | 8.4 | 36.3 | -40.6 | 0.23 | 0.23 | 0.26 | 0.23 | 0.14 |
| Inverse Vol (5 sleeves) | 12.1 | 36.6 | -40.4 | 0.33 | 0.32 | 0.56 | 0.23 | 0.20 |
