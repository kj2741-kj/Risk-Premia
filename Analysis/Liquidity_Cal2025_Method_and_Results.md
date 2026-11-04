# Liquidity metric, Calendar 2025: method and results (2026-10-31, updated 2026-11-04)

Prof. Bouchouev's request (25 Oct): a one-time snapshot on Calendar 2025 only, x(i) = ADV x average price x volatility x multiplier, test whether NGL liquidity is too small against other commodities or at least comparable to the less liquid non-energy products, add CME and ICE for NGL, never mix ADV and open interest. This note records the method as run and the first result. NGL here is the CME half only; ICE is to be added.

## Method, step by step (per product)

1. Window: calendar 2025, each market's own trading days (about 251 to 258).
2. Price P: mean 2025 unadjusted price of the contract we hold (F1 before our roll day, F2 after; for the NGL swaps the sheet's second generic, third after the roll, as in the engine). Converted to USD per unit: cents divided by 100 where the data are in cents (RBOB, Heating Oil, grains and softs); EUR converted at 1.1300, the mean of the 255 ECB daily euro reference fixes of 2025.
3. Volatility sigma: standard deviation of the daily log returns of the roll-adjusted engine series over 2025.
4. Multiplier m: units per lot from the exchange specification (table below).
5. Dollar risk per contract c = m x P x sigma.
6. ADV (lots per day): mean over the 2025 trading days of the volume summed over the contracts of a 12-month strip; a day with no print counts as zero. Volume only, open interest is never substituted.
7. x = ADV x c, in USD of one-sigma daily risk traded per day (shown in USD millions).
8. K / x with K = $1M of one-sigma daily risk (changed from $10M on 2026-11-01; K is a risk budget, not a notional, and every L is ten times smaller): the size of a $1M position as a multiple of one day of the market's risk turnover. A value of 0.05 is 5% of a day, 3 is 3 days of the entire market's flow. The ranking by x does not depend on K.

12-month strip: the number of tenors that spans 12 months depends on the contract chain. Monthly products (LME metals, petroleum, Gasoil, Henry Hub, TTF, NGL) use F1-F12. Gold F1-F6 (even-month chain), Silver F1-F5, Platinum and Palladium F1-F4, Corn, Wheat and Coffee F1-F5, Soybean F1-F7, Soybean Oil F1-F8, Sugar F1-F4, EUA F1-F4 (quarterly). These are the same chains that fix the Carry long pairs (about 12 months out).

Sensitivities kept in the CSV: ADV of the held contract only (strictest), F1-F3 ADV, all-tenor ADV, median ADV.

## Multipliers (checked against the exchange pages on 2026-10-31)

CME: WTI 1,000 bbl; RBOB and NY Harbor ULSD 42,000 gal; Henry Hub 10,000 MMBtu; Gold 100 oz; Silver 5,000 oz; Platinum 50 oz; Palladium 100 oz; Corn, Wheat, Soybean 5,000 bu; Soybean Oil 60,000 lb; Mont Belvieu TET Propane, Non-TET Ethane, Non-TET Normal Butane, Non-TET Isobutane (OPIS) 42,000 gal each. ICE: Brent 1,000 bbl; Low Sulphur Gasoil 100 t; Coffee C 37,500 lb; Sugar No. 11 112,000 lb; EUA 1,000 allowances; TTF 1 MW x hours of the delivery month (730.5 used, the average month). LME Copper, Aluminium, Zinc, Lead 25 t. Added 2026-11-04: Mont Belvieu Ethylene (OPIS PCW) and Polymer Grade Propylene (PGP) 100,000 lb each, price in $/lb (CME rulebook chapters 602 and 711 and the ICE Futures U.S. specifications give the same size; the CME contract-specs page itself could not be opened, so confirm the unit once on the page); UK Gas (ICE NBP) 1,000 therms a day over the delivery month = 30,417 therms for an average month, price in pence per therm converted at USD 1.3184 per GBP (mean of the 255 ECB daily crosses EURUSD/EURGBP of 2025); Naphtha CIF NWE swap 1,000 t on both ICE (NEC) and CME, USD per t. Our Bloomberg NGL roots PCW and PGP are the CME Ethylene and Propylene contracts (product names in the expiry workbook). Our Bloomberg NGL tickers map to CME contracts as: BAP = TET Propane, DAE = Non-TET Normal Butane, CAP = Non-TET Ethane, IBD = Non-TET Isobutane. The "Summary" sheet of Volume_NGL.xlsx carries the cyclically shifted names (CAP "Propane Argus Far East", BAP "Butane Argus", DAE "Ethane Argus", PCW "Propane CIF ARA"); the roots are right, the names are not.

Data check: our all-tenor volume equals CME's published final volume for 26 to 28 Oct 2026 within about 1% for RBOB, ULSD, Butane, Isobutane, Henry Hub, WTI and TET Propane. Ethane is the exception (60 to 65% of CME on two days). The Gasoil series (Bloomberg root QS) is ICE Low Sulphur Gasoil, not Singapore Gasoil as the engine config name suggests.

## Result (K = $1M), 2026-11-04 update: all six NGL, UK Gas and the Naphtha candidate added

The 26 products of the 2026-10-31 run are reproduced exactly (maximum absolute difference 0.0 on every column); four rows are new: Ethylene and Propylene (so all six NGL are in), UK Gas and Naphtha.

| # | Product | Bucket | Strip | ADV (lots/day) | Risk per contract ($) | x ($m/day) | K/x | x held ($m/day) |
|---|---|---|---|---|---|---|---|---|
| 1 | Brent | petroleum | F1-F12 | 1,116,127 | 1,187 | 1,324.9 | 0.00075 | 394.6 |
| 2 | Gold | precious | F1-F6 | 254,407 | 4,486 | 1,141.2 | 0.00088 | 729.8 |
| 3 | WTI | petroleum | F1-F12 | 837,025 | 1,242 | 1,039.9 | 0.00096 | 341.3 |
| 4 | Henry Hub | gas & emissions | F1-F12 | 515,680 | 1,296 | 668.3 | 0.0015 | 186 |
| 5 | Gasoil (ICE) | petroleum | F1-F12 | 351,370 | 1,418 | 498.3 | 0.00201 | 113.4 |
| 6 | Silver | precious | F1-F5 | 86,216 | 4,777 | 411.8 | 0.00243 | 315 |
| 7 | Heating Oil | petroleum | F1-F12 | 195,204 | 1,801 | 351.5 | 0.00284 | 117.7 |
| 8 | RBOB | petroleum | F1-F12 | 188,064 | 1,362 | 256.1 | 0.00391 | 91.46 |
| 9 | Copper | metals | F1-F12 | 83,063 | 2,947 | 244.8 | 0.00408 | 53.81 |
| 10 | TTF | gas & emissions | F1-F12 | 270,092 | 784 | 211.9 | 0.00472 | 45.25 |
| 11 | Soybean | agri | F1-F7 | 288,372 | 545 | 157.1 | 0.00636 | 55.91 |
| 12 | Coffee | agri | F1-F5 | 34,914 | 3,207 | 112.0 | 0.00893 | 37.98 |
| 13 | Corn | agri | F1-F5 | 425,628 | 258 | 109.8 | 0.00911 | 44.33 |
| 14 | Aluminium | metals | F1-F12 | 157,841 | 640 | 101.0 | 0.0099 | 22.6 |
| 15 | Soybean Oil | agri | F1-F8 | 178,724 | 495 | 88.4 | 0.01131 | 26.7 |
| 16 | Platinum | precious | F1-F4 | 38,905 | 1,694 | 65.9 | 0.01517 | 48.66 |
| 17 | Zinc | metals | F1-F12 | 64,414 | 904 | 58.3 | 0.01717 | 10.56 |
| 18 | Wheat | agri | F1-F5 | 135,652 | 377 | 51.1 | 0.01956 | 22.08 |
| 19 | EUA | gas & emissions | F1-F4 | 30,103 | 1,300 | 39.1 | 0.02555 | 11.24 |
| 20 | Sugar | agri | F1-F4 | 122,500 | 283 | 34.7 | 0.0288 | 17.12 |
| 21 | UK Gas (NBP) | gas & emissions | F1-F12 | 31,979 | 982 | 31.4 | 0.03185 | 9.012 |
| 22 | Palladium | precious | F1-F4 | 7,094 | 3,374 | 23.9 | 0.04178 | 18.72 |
| 23 | Lead | metals | F1-F12 | 42,887 | 449 | 19.3 | 0.05193 | 3.361 |
| 24 | Propane | ngl | F1-F12 | 8,273 | 586 | 4.8 | 0.2062 | 1.187 |
| 25 | Butane | ngl | F1-F12 | 2,907 | 624 | 1.8 | 0.551 | 0.4572 |
| 26 | Ethane | ngl | F1-F12 | 1,203 | 290 | 0.3492 | 2.864 | 0.09974 |
| 27 | Naphtha | candidate (not in a bucket) | F1-F12 | 12 | 9,354 | 0.1082 | 9.241 | 0.0218 |
| 28 | Propylene | ngl | F1-F12 | 123 | 614 | 0.0753 | 13.28 | 0.01351 |
| 29 | Ethylene | ngl | F1-F12 | 105 | 498 | 0.0525 | 19.03 | 0.01057 |
| 30 | Isobutane | ngl | F1-F12 | 10 | 642 | 0.0064 | 156.2 | 0.0006 |

Least liquid non-energy products: Lead x = 19.3, Palladium x = 23.9, Sugar 34.7 (USD millions of one-sigma risk per day).

NGL against the least liquid non-energy product (Lead): Propane 0.25x, Butane 0.09x, Ethane 0.018x, Propylene 0.004x, Ethylene 0.003x, Isobutane 0.0003x. UK Gas (x = 31.4) sits above Lead and Palladium, between Sugar and Palladium. Naphtha (x = 0.108) is 0.006x Lead, about a third of Ethane and above Propylene, Ethylene and Isobutane.

## Caveats and open items

- 2026-11-04 volume check: the new `Volume_NGL.xlsx` (2026-11-03 drop) equals `Prices_1029/Volume_NGL.xlsx` cell for cell on all 14 sheets (same dates, same values, last dates 10-29 and 10-28); only the file hash differs. No merge was needed.
- Ethylene and Propylene print on 71% and 73% of days; PCW and PGP volumes were not cross-checked against CME's published volume (CME's public page keeps only five trade dates). The NGL dashboards still show four NGL products; the metric covers all six.
- Naphtha (Bloomberg KI generic): volume comes from the 2026-11-03 drop, whose volume sheet has rows only on days with a print (139 rows in 2025), missing days are counted as zero as everywhere. The ADV of 11.6 lots a day (median 5) is what Bloomberg reports for the generic; OTC-cleared swap volume that Bloomberg does not see is not in it, so x is a lower bound, as for the NGL swaps. Whether "KI ... COMB" combines ICE and CME is not stated in the file.
- Naphtha is a monthly average-price swap, F1 is the month being priced and expires on the last business day of that month; the engine rolls on the 5th trading day of that month, out of the month being priced, like every other product. Its expiry dates are derived (scripts/new_products.py), not Bloomberg's.
- UK Gas: the volume unit is lots of 1,000 therms a day (ICE minimum 5 lots); 30,417 therms per lot assumes an average month. The calendar is derived from the ICE rule and matches the Bloomberg generic roll on every contract. Held-contract x (9.0) is 29% of strip x (31.4): the contract we hold trades 9,179 lots a day against 31,979 for the 12-month strip.

- ICE half of NGL is not included. Bogorad's Figure 10 implies ICE roughly doubles NGL volume in 2025; even doubled, Propane would be about half of Lead. Per-product ICE volume to be added when available.
- CME Non-TET Propane (about 1,400 lots a day in late October 2026) is not in our data; it would add roughly 20% to Propane.
- Ethane volume may be understated (see data check above).
- Isobutane prints on only 13% of days (Bogorad excludes it); kept in this analysis by decision.
- EUA and TTF strips capture 85% and 81% of their all-tenor volume; the rest sits in far tenors.
- The Gold chain (even months) and the Silver, Platinum and Palladium chains are inferred from curve-shift tests, not documented by Bloomberg.
- One year only, as requested; no annual or dynamic filter.

Reproduce: `python scripts/liquidity_cal2025.py` from the repo root (about 3 minutes) writes `Analysis/Liquidity_Cal2025_results.csv`.
