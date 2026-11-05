```
Baseline reproduces products_nets.pkl: worst abs difference 0.0e+00

Common dates for paired tests: 3687 days, 2012-01-04 to 2026-10-29

1. Sharpe by calendar year, equal-weight portfolio of the five sleeves
      Henry Hub   TTF  UK Gas
Date                         
2012      -0.81 -1.87   -0.56
2013      -0.03  0.44    0.14
2014       1.34  0.64    1.76
2015      -0.96  1.27    0.89
2016       0.87  2.09    1.03
2017      -1.45  0.17    0.26
2018       0.37  1.37    0.80
2019      -0.47  1.24    1.44
2020      -0.51  1.61    1.59
2021       0.24  3.03    2.63
2022       0.97  0.39    0.68
2023      -0.85  1.67   -0.33
2024       0.51  0.14   -0.84
2025       0.19 -1.79   -0.67
2026      -1.12  0.96   -0.25
   TTF beats Henry Hub in 10 of 15 years
   UK Gas beats Henry Hub in 12 of 15 years

2. Paired stationary block bootstrap (mean block 20 days, 4000 resamples), Sharpe of EW PORT
   Henry Hub Sharpe 0.01
   TTF: Sharpe 0.80 (bootstrap 95% CI 0.26 to 1.33); difference vs Henry Hub +0.80, 95% CI +0.06 to +1.53, share of resamples with difference <= 0: 0.019
   UK Gas: Sharpe 0.54 (bootstrap 95% CI 0.03 to 1.04); difference vs Henry Hub +0.53, 95% CI -0.09 to +1.15, share of resamples with difference <= 0: 0.044

3. Excluding the 2021-07-01 to 2023-06-30 gas crisis (Sharpe of EW PORT on common dates)
   Henry Hub  all dates  0.01 | without crisis -0.18 | crisis only  0.78
   TTF        all dates  0.80 | without crisis  0.62 | crisis only  1.54
   UK Gas     all dates  0.54 | without crisis  0.38 | crisis only  1.13

4. Parameter variations, Sharpe of EW PORT from 2012 (each product's own series, same settings for all three)
                          Henry Hub   TTF  UK Gas  TTF>HH  UK>HH
variant                                                         
baseline                       0.01  0.78    0.53    True   True
costs 10 bps                  -0.03  0.75    0.50    True   True
costs 20 bps                  -0.11  0.70    0.45    True   True
Carry F1-F2 only              -0.35  0.22   -0.05    True   True
Carry F1-F3 only              -0.40  0.21   -0.14    True   True
Carry F1-F2 + F1-F6           -0.47  0.58    0.31    True   True
Carry F1-F3 + F1-F13           0.01  0.70    0.44    True   True
Momentum (5,60),(20,250)      -0.03  0.86    0.56    True   True
Momentum (1,20) only           0.01  0.81    0.52    True   True
   TTF beats Henry Hub in 9 of 9 variants; UK Gas in 9 of 9

5. Sleeve Sharpe from 2012 (baseline)
          Henry Hub   TTF  UK Gas
Momentum       0.03  0.48    0.32
Carry          0.26  0.79    0.37
CarryMom       0.28  0.33    0.20
Value         -0.12 -0.12   -0.01
Skewness      -0.46  0.51    0.31

6. Correlation of daily EW PORT returns (common dates)
           Henry Hub   TTF  UK Gas
Henry Hub       1.00  0.06    0.06
TTF             0.06  1.00    0.77
UK Gas          0.06  0.77    1.00
```
