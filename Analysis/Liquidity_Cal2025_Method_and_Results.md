# Liquidity metric, Calendar 2025: method and results (2026-10-31)

Prof. Bouchouev's request (25 Oct): a one-time snapshot on Calendar 2025 only, x(i) = ADV x average price x volatility x multiplier, test whether NGL liquidity is too small against other commodities or at least comparable to the less liquid non-energy products, add CME and ICE for NGL, never mix ADV and open interest. This note records the method as run and the first result. NGL here is the CME half only; ICE is to be added.

## Method, step by step (per product)

1. Window: calendar 2025, each market's own trading days (about 251 to 258).
2. Price P: mean 2025 unadjusted price of the contract we hold (F1 before our roll day, F2 after; for the NGL swaps the sheet's second generic, third after the roll, as in the engine). Converted to USD per unit: cents divided by 100 where the data are in cents (RBOB, Heating Oil, grains and softs); EUR converted at 1.1300, the mean of the 255 ECB daily euro reference fixes of 2025.
3. Volatility sigma: standard deviation of the daily log returns of the roll-adjusted engine series over 2025.
4. Multiplier m: units per lot from the exchange specification (table below).
5. Dollar risk per contract c = m x P x sigma.
6. ADV (lots per day): mean over the 2025 trading days of the volume summed over the contracts of a 12-month strip; a day with no print counts as zero. Volume only, open interest is never substituted.
7. x = ADV x c, in USD of one-sigma daily risk traded per day (shown in USD millions).
8. K / x with K = $10M of one-sigma daily risk: the size of a $10M position as a multiple of one day of the market's risk turnover. A value of 0.05 is 5% of a day, 29 is 29 days of the entire market's flow. The ranking by x does not depend on K.

12-month strip: the number of tenors that spans 12 months depends on the contract chain. Monthly products (LME metals, petroleum, Gasoil, Henry Hub, TTF, NGL) use F1-F12. Gold F1-F6 (even-month chain), Silver F1-F5, Platinum and Palladium F1-F4, Corn, Wheat and Coffee F1-F5, Soybean F1-F7, Soybean Oil F1-F8, Sugar F1-F4, EUA F1-F4 (quarterly). These are the same chains that fix the Carry long pairs (about 12 months out).

Sensitivities kept in the CSV: ADV of the held contract only (strictest), F1-F3 ADV, all-tenor ADV, median ADV.

## Multipliers (checked against the exchange pages on 2026-10-31)

CME: WTI 1,000 bbl; RBOB and NY Harbor ULSD 42,000 gal; Henry Hub 10,000 MMBtu; Gold 100 oz; Silver 5,000 oz; Platinum 50 oz; Palladium 100 oz; Corn, Wheat, Soybean 5,000 bu; Soybean Oil 60,000 lb; Mont Belvieu TET Propane, Non-TET Ethane, Non-TET Normal Butane, Non-TET Isobutane (OPIS) 42,000 gal each. ICE: Brent 1,000 bbl; Low Sulphur Gasoil 100 t; Coffee C 37,500 lb; Sugar No. 11 112,000 lb; EUA 1,000 allowances; TTF 1 MW x hours of the delivery month (730.5 used, the average month). LME Copper, Aluminium, Zinc, Lead 25 t. Our Bloomberg NGL tickers map to CME contracts as: BAP = TET Propane, DAE = Non-TET Normal Butane, CAP = Non-TET Ethane, IBD = Non-TET Isobutane.

Data check: our all-tenor volume equals CME's published final volume for 26 to 28 Oct 2026 within about 1% for RBOB, ULSD, Butane, Isobutane, Henry Hub, WTI and TET Propane. Ethane is the exception (60 to 65% of CME on two days). The Gasoil series (Bloomberg root QS) is ICE Low Sulphur Gasoil, not Singapore Gasoil as the engine config name suggests.

## Result (K = $10M)

| # | Product | Bucket | Strip | ADV (lots/day) | Risk per contract ($) | x ($m/day) | K/x | x held ($m/day) |
|---|---|---|---|---|---|---|---|---|
| 1 | Brent | petroleum | F1-F12 | 1,116,127 | 1,187 | 1,324.9 | 0.008 | 394.56 |
| 2 | Gold | precious | F1-F6 | 254,407 | 4,486 | 1,141.2 | 0.009 | 729.84 |
| 3 | WTI | petroleum | F1-F12 | 837,025 | 1,242 | 1,039.9 | 0.010 | 341.34 |
| 4 | Henry Hub | pen | F1-F12 | 515,680 | 1,296 | 668.3 | 0.015 | 185.98 |
| 5 | Gasoil (ICE) | petroleum | F1-F12 | 351,370 | 1,418 | 498.3 | 0.020 | 113.37 |
| 6 | Silver | precious | F1-F5 | 86,216 | 4,777 | 411.8 | 0.024 | 314.98 |
| 7 | Heating Oil | petroleum | F1-F12 | 195,204 | 1,801 | 351.5 | 0.028 | 117.75 |
| 8 | RBOB | petroleum | F1-F12 | 188,064 | 1,362 | 256.1 | 0.039 | 91.46 |
| 9 | Copper | metals | F1-F12 | 83,063 | 2,947 | 244.8 | 0.041 | 53.81 |
| 10 | TTF | pen | F1-F12 | 270,092 | 784 | 211.9 | 0.047 | 45.25 |
| 11 | Soybean | agri | F1-F7 | 288,372 | 545 | 157.1 | 0.064 | 55.91 |
| 12 | Coffee | agri | F1-F5 | 34,914 | 3,207 | 112.0 | 0.089 | 37.98 |
| 13 | Corn | agri | F1-F5 | 425,628 | 258 | 109.8 | 0.091 | 44.33 |
| 14 | Aluminium | metals | F1-F12 | 157,841 | 640 | 101.0 | 0.099 | 22.60 |
| 15 | Soybean Oil | agri | F1-F8 | 178,724 | 495 | 88.4 | 0.113 | 26.70 |
| 16 | Platinum | precious | F1-F4 | 38,905 | 1,694 | 65.9 | 0.152 | 48.66 |
| 17 | Zinc | metals | F1-F12 | 64,414 | 904 | 58.3 | 0.172 | 10.56 |
| 18 | Wheat | agri | F1-F5 | 135,652 | 377 | 51.1 | 0.196 | 22.08 |
| 19 | EUA | pen | F1-F4 | 30,103 | 1,300 | 39.1 | 0.255 | 11.24 |
| 20 | Sugar | agri | F1-F4 | 122,500 | 283 | 34.7 | 0.288 | 17.12 |
| 21 | Palladium | precious | F1-F4 | 7,094 | 3,374 | 23.9 | 0.418 | 18.72 |
| 22 | Lead | metals | F1-F12 | 42,887 | 449 | 19.3 | 0.519 | 3.36 |
| 23 | Propane | ngl | F1-F12 | 8,273 | 586 | 4.8 | 2.062 | 1.19 |
| 24 | Butane | ngl | F1-F12 | 2,907 | 624 | 1.8 | 5.510 | 0.46 |
| 25 | Ethane | ngl | F1-F12 | 1,203 | 290 | 0.3492 | 29 | 0.10 |
| 26 | Isobutane | ngl | F1-F12 | 10 | 642 | 0.0064 | 1,562 | 0.00 |

Least liquid non-energy products: Lead x = 19.3, Palladium x = 23.9, Sugar 34.7 (USD millions of one-sigma risk per day).

NGL against the least liquid non-energy product (Lead): Propane 0.25x, Butane 0.09x, Ethane 0.018x, Isobutane 0.0003x. Against Palladium: Propane 0.20x, Butane 0.08x, Ethane 0.015x. A $10M position in Propane is about two days of its entire CME market flow, in Ethane about 29 days.

## Caveats and open items

- ICE half of NGL is not included. Bogorad's Figure 10 implies ICE roughly doubles NGL volume in 2025; even doubled, Propane would be about half of Lead. Per-product ICE volume to be added when available.
- CME Non-TET Propane (about 1,400 lots a day in late October 2026) is not in our data; it would add roughly 20% to Propane.
- Ethane volume may be understated (see data check above).
- Isobutane prints on only 13% of days (Bogorad excludes it); kept in this analysis by decision.
- EUA and TTF strips capture 85% and 81% of their all-tenor volume; the rest sits in far tenors.
- The Gold chain (even months) and the Silver, Platinum and Palladium chains are inferred from curve-shift tests, not documented by Bloomberg.
- One year only, as requested; no annual or dynamic filter.

Reproduce: `python scripts/liquidity_cal2025.py` from the repo root writes `Analysis/Liquidity_Cal2025_results.csv`.
