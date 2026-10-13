# Imputed tenors (Heating Oil F13, Isobutane F14)

`imputed_tenors_ho_isobutane.csv` holds the 33 prices that are missing in the source files inside the 2012 sample, for the two tenors that a Carry long pair depends on. Observed prices are never changed, and the source files in `data/Prices_0924` are untouched. Nothing in the research pipeline reads this file yet: the stored sleeve returns and the dashboards still treat these days as missing. Under the sign-vote rule that meant flat Carry and Carry-Momentum positions; since 2026-10-13 (summed z-scores) a missing value keeps the last signal, so the effect figures below were measured under the sign-vote rule and have not been re-run.

Rule (same-grade fill, missing cells only)

| Product | Missing cells | Fill | Spread used |
|---|---|---|---|
| Heating Oil F13 | 19 trading days, 2012-04-02 to 2012-04-27 | F13 = F12 + s | s = -2.805 cents/gal, the mean of F13 - F12 over March 2012 (22 days) |
| Isobutane F14 | 14 trading days, 2013-03-01 to 2013-03-20 | F14 = F13 + s | s = 0.000 $/gal, the mean of F14 - F13 over February 2013 (F14 equals F13 on all 19 days) |

Why no grade premium for Heating Oil. In April 2012 F13 is the May 2013 contract, the first month with the ULSD grade (CME notice of April 2012; EIA, Today in Energy 11211). Its premium over the old-grade April 2013 contract is only visible after the gap (6.7 cents against the neighbouring spreads on 30 April 2012, about 3.8 to 4.6 cents through 2012, 7.6 cents in February 2013), so using it would be look-ahead. The fill therefore treats the contract as the same grade as F12 and probably understates the true premium. Why not the F10/F12 extrapolation for Isobutane: on days when F14 is observed it misses by 3.2% of price against 1.4% for copying F13, and F13 is available on every gap day.

Columns: date, product, leg_1_tenor, leg_1_price, leg_2_tenor, leg_2_price_imputed, carry_spread_value (leg 1 minus imputed leg 2, in the product's unit: cents/gal for Heating Oil, $/gal for Isobutane), adjustment_applied (the spread s), flag_imputed (always True).

Effect measured on the stored 2012 sleeves (fill versus gap left flat): Heating Oil Carry IR 0.737 to 0.739, Isobutane Carry IR 0.654 to 0.663; Energy and NGL Carry sleeve IRs move by 0.003 or less.

Rebuild: `python Analysis/_v4_build/build_imputed_tenors.py`. The full tenor-by-tenor missing-price check (87 columns, all 23 products) is in `Analysis/_v4_build/tenor_missing_check_all.csv`.
