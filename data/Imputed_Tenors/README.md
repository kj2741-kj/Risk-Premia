# Imputed tenors (Heating Oil F13, Isobutane F14)

`imputed_tenors_ho_isobutane.csv` holds the 33 prices that are missing in the source files inside the 2012 sample, for the two tenors that a Carry long pair depends on. Observed prices are never changed, and the source files in `data/Prices_0924` are untouched. Since 2026-10-13 (agreed with Dimil) the fills are applied everywhere: `research/imputed_tenors.py` is called at the single place each consumer reads the curves, `load_curve` in `research/configs/energy.py` and `ngl.py` (research pipeline, Final dashboards, rankings, Skewness page, portfolio tab, hub) and `common_curve_loader.load_curve_simple` (the standalone Streamlit dashboards). Only cells that are missing in the source file are filled, so if the provider file is ever repaired the real prices win. Under the summed Carry rule measured before the switch-over: product Carry IRs move by at most 0.004, Isobutane Carry-Momentum 0.543 to 0.521, and the Energy and NGL Carry and Carry-Momentum sleeve IRs by 0.007 or less.

Rule (same-grade fill, missing cells only)

| Product | Missing cells | Fill | Spread used |
|---|---|---|---|
| Heating Oil F13 | 19 trading days, 2012-04-02 to 2012-04-27 | F13 = F12 + s | s = -2.805 cents/gal, the mean of F13 - F12 over March 2012 (22 days) |
| Isobutane F14 | 14 trading days, 2013-03-01 to 2013-03-20 | F14 = F13 + s | s = 0.000 $/gal, the mean of F14 - F13 over February 2013 (F14 equals F13 on all 19 days) |

Why no grade premium for Heating Oil. In April 2012 F13 is the May 2013 contract, the first month with the ULSD grade (CME notice of April 2012; EIA, Today in Energy 11211). Its premium over the old-grade April 2013 contract is only visible after the gap (6.7 cents against the neighbouring spreads on 30 April 2012, about 3.8 to 4.6 cents through 2012, 7.6 cents in February 2013), so using it would be look-ahead. The fill therefore treats the contract as the same grade as F12 and probably understates the true premium. Why not the F10/F12 extrapolation for Isobutane: on days when F14 is observed it misses by 3.2% of price against 1.4% for copying F13, and F13 is available on every gap day.

Columns: date, product, leg_1_tenor, leg_1_price, leg_2_tenor, leg_2_price_imputed, carry_spread_value (leg 1 minus imputed leg 2, in the product's unit: cents/gal for Heating Oil, $/gal for Isobutane), adjustment_applied (the spread s), flag_imputed (always True).

Rebuild: `python Analysis/_v4_build/build_imputed_tenors.py`. The full tenor-by-tenor missing-price check (87 columns, all 23 products) is in `Analysis/_v4_build/tenor_missing_check_all.csv`.
