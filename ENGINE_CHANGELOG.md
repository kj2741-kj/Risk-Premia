# Engine and research change log

Newest entry first. Author of the entries below: Dimil Patel (with Claude Code assisting). Dates are the dates the work was done (for the earlier
analysis steps they come from file timestamps). The 2026-10-11 entry is the engine/config update; the sections after it record the analysis work
that led to it.

---

## 2026-10-13 (later): Heating Oil F13 and Isobutane F14 gaps filled in the data everywhere

- **Decision (user and Dimil, 2026-10-13).** The only two tenor gaps inside the 2012 sample that a Carry long pair depends on are filled with a same-grade rule, missing cells only: Heating Oil F13 on 2012-04-02 to 04-27 (19 days; in April 2012 F13 is the May 2013 contract, the first ULSD-grade month, not yet listed) = F12 - 2.805 cents/gal (March 2012 mean spread), and Isobutane F14 on 2013-03-01 to 03-20 (14 days) = F13 (the provider repeats F13 as F14). No grade premium is added for Heating Oil because it is only visible after the gap (look-ahead). Soybean Oil's one Good Friday day (2012-04-06, F2/F3/F8) and NGL F1 (unused) are not filled.
- **Code.** New `research/imputed_tenors.py` (reads `data/Imputed_Tenors/imputed_tenors_ho_isobutane.csv`, never overwrites a present price). Applied in `research/configs/energy.py` and `ngl.py` `load_curve` and in `common_curve_loader.load_curve_simple`, so the pipeline, the Final dashboards, the rankings and Skewness pages, the portfolio tab, the hub and the five standalone Streamlit dashboards all see the same prices. Tested: exactly 19 + 14 cells change, all were NaN, nothing else.
- **Effect (measured under the summed Carry rule before the switch).** Product Carry IR changes by at most 0.004, Isobutane Carry-Momentum 0.543 to 0.521, Energy and NGL sleeve IRs by 0.007 or less; no conclusion changes. Pages regenerated: see the commit.

## 2026-10-12 (night): Streamlit Cloud kept stale shared modules after a push; apps now refresh them

- **Symptom.** After the Skewness push (80884c8) every Streamlit Cloud app failed: the five dashboards with `ImportError: cannot import name 'render_skewness_tab' from 'common_engine'` and the hub with `AttributeError` on `cae.ALL_ASSET_CLASSES`. A fresh clone of `main` ran all six apps without error on Python 3.13, so the code was fine.
- **Cause.** A running Streamlit Cloud app keeps its Python process across a git pull and reloads only files inside the app's own folder. Shared modules outside it (`common_engine.py`, `common_shared.py`, `dashboard_portfolio_tab.py`, `research/*`, `scripts/*`) stay in memory in their old version while `app.py` is new. Reproduced locally by loading the old `common_engine` / `cross_asset_engine` into `sys.modules` and running the current apps.
- **Fix.** The six `app.py` files (hub and five dashboards) call `_refresh_repo_modules()` right after the `sys.path` setup: when any loaded repo module's file changed since the last run (and on the first run of a process) the repo's modules are dropped from `sys.modules`, so the imports below read the current code. Unchanged files are left alone (no re-import cost). With stale modules loaded, all five dashboards and the hub run without exceptions; a touched file is reloaded and an unchanged one is not.
- **Note.** Because `app.py` is always read fresh, this takes effect on the next redeploy without a manual reboot. If an app still shows the old error, use Manage app > Reboot app once.

---

## 2026-10-12 (evening): Skewness in the five Streamlit dashboards, their Portfolio tabs and the hub Cross-Asset tab

- **One shared signal.** `research/engine.py`: `raw_signal_skewness_from_returns` (minus the rolling skewness of daily log returns over 252 observations, +1 if negative, -1 if positive), `raw_signal_skewness(log_price)` and `ratio_log_returns(f1c, f1r, f2r, phase)`. The dashboards' dollar-PnL `F1_continuous` is additively stitched, so `log(F1_continuous).diff()` divides by the adjusted level and is wrong (and undefined where the level is <= 0). `ratio_log_returns` rebuilds the exact ratio-stitched log return as log(1 + dollar change / price of the contract held at t-1); it reproduces the research series to 1e-15 on all 23 products (signal agreement 100%).
- **Five dashboards** (`metals`, `energy`, `ngl`, `precious_metals`, `agri`): new Skewness tab (`common_engine.render_skewness_tab`, 126/252/504-day windows plus a custom one, Sharpe by window, rolling skewness, equity curve, rolling Sharpe), included in the Comparison tab. `app.py` files only pass `f2r=f1_df["F2_raw"]`.
- **Portfolio tab** (`dashboard_portfolio_tab.py`): Skewness is a fifth family (reference card, Include toggle, window leg). The original "Portfolio (all reference strategies)" row is unchanged (four strategies); a new row "Portfolio (all reference strategies + Skewness)" adds the fifth.
- **Hub Cross-Asset tab** (`research/cross_asset_engine.py`, `hub/app.py`): `per_product_four_row(include_skewness=False)` adds an optional "Skewness" style; `ALL_STYLE_NAMES`; `cross_n_portfolio(styles=...)`; new style-level combine method `inverse_vol` (1/trailing 63-day vol, lagged one day). Hub: Skewness is a fifth option in "Styles" (off by default, so the headline book is still the validated four-style one), "Inverse Vol" in "Combine method", a "Add Skewness as a fifth style" checkbox in the Cross-Asset-Class section, and "Skewness" / "EW PORT + Skewness" correlation rows (not shown by default).
- **Checks.** Defaults unchanged: `cross_commodity_dynamic` (Equal Weight, Risk Parity, Dynamic Risk Parity), `cross_n_portfolio` and `per_product_four_row` are identical to the previous commit with Skewness off. Skewness style, five asset classes, Equal Weight, 2012+: return 2.09, vol 11.78, max drawdown -43.96, IR 0.18, the same as `Skewness_Research.html`; five-style Equal Weight and Inverse Vol books IR 0.77 and 0.80 (his page: 0.77 and 0.80); Metals five-sleeve Equal Weight IR -0.09. Portfolio-tab Skewness sleeve matches `Skewness_Research.html` for all five asset classes. `validate_engine.py`: worst difference 0. All five dashboards and the hub run headless with no exceptions across every product and every new option.
- **Included from earlier uncommitted work in `hub/app.py`:** per-product tenor pairs for Precious Metals and Agriculture in the Cross-Asset tab (`_uses_product_pairs`, matches the Final Research Dashboard).

---

## 2026-10-13: Carry and Carry-Momentum now SUM the tenor pairs before the sign (new default for the Final dashboard pipeline)

**Decision (user, 2026-10-13).** The sign-vote (each pair's sign, averaged, then signed) left the position flat whenever the two pairs disagreed (16% of days in Metals, 23% Energy, 32% NGL, 29% Precious, 33% Agriculture). New default: **Carry V2 = sign of the SUM of the pairs' z-scores; Carry-Momentum = sign of the SUM of the pairs' raw 20-observation slope changes.** If a pair's value is missing on a day the last signal is kept (flat only before the first signal). Flat days from 2012: 0%. Lag applied once to the combined signal. Single-pair legs (the Precious/Agriculture short, long and "previous" comparison rows) are unchanged.

**Code.** New `research/carry_zsum.py` (`carry_z`, `carry_slope_change`, `summed_signal`, plus the sandbox alternatives below). `scripts/final_dashboard/compute_products.py` uses it by default (`CARRY_COMBINE=zsum`; `CARRY_COMBINE=vote` reproduces the old results). `build_final_dashboard_v2.py` page text updated. `run_2012_variant.py` and `rankings_page.py`: the default now uses the main results; the `ZSUM=2..5` environment modes are the sandbox alternatives (outputs in `outputs/final_dashboard_2012_<suffix>/`, pages `*_zsum_std`, `*_zsum_pm`, `*_rawcarry`, `*_zdiff`, plus `*_zsum` = the adopted combination). Pages regenerated: `Final_Research_Dashboard.html`, `Final_Research_Dashboard_2012.html`, `Commodity_Rankings.html`. The previous results are kept locally in `outputs/vote_backup/`.

**Effect (full-sample IR).** 2012-26: All-5 EW/EW with NatGas 0.77 to 0.87, ex-NatGas 0.88 to 0.93; Carry up in every asset class (Energy 0.29 to 0.46, NGL 0.91 to 1.08, Precious -0.24 to -0.08, Metals 0.02 to 0.13, Agriculture -0.05 to 0.01); Carry-Momentum up in Energy (0.60 to 0.78) and NGL (0.66 to 0.72), unchanged in Metals, down in Precious (-0.09 to -0.23) and Agriculture (-0.10 to -0.34). 2011-26 (main page): All-5 EW/EW 0.73 to 0.84. In-sample, not significance-tested.

**Alternatives tested and not adopted** (2012-26 portfolio IR, All-5 EW/EW with NatGas, adopted = 0.87): Carry-Momentum with each pair's change standardised by its trailing 252-observation standard deviation 0.85; per-month price spread (exact months between the two legs from the expiry calendars, `research/contract_months.py`) 0.86, the only version that fixes Agriculture Carry-Momentum (0.02) but lowers Energy and NGL; change of the Carry z-scores 0.77; Carry as the sign of the summed raw slopes with no z-score 0.79 (Agriculture Carry 0.49 but NGL 0.33 and Metals -0.42).

**Also changed the same day (no switch, one rule everywhere):** `scripts/final_dashboard/compute_products.py` (the `CARRY_COMBINE` switch was removed), `research/run_regime_table.py`, `research/cross_asset_engine.py` (`per_product_four_row`, used by the Streamlit hub's Cross-Asset tab) and `dashboard_portfolio_tab.py` all use `research/carry_zsum.py` (`combined_carry_signal`, `combined_carrymom_signal`). Checks: `run_regime_table._position_for` and `per_product_four_row(per_product_pairs=True)` reproduce the dashboard's Carry and Carry-Momentum series for all 23 products with a maximum daily difference of 0; the portfolio tab's reference Combined Carry and Combined CarryMom equal the dashboard's sleeve for Metals, Energy and NGL (to 1e-16). Portfolio tab: the reference Carry is V2 only (V1 no longer in the reference or the default sleeves, still selectable), several V2 legs in a custom sleeve sum their z-scores, several CarryMom legs sum their raw slope changes. In `combined_carry_signal` V1, if requested, is one sign-vote group averaged with the summed-z V2 group. The old sign-vote is available only from Git history. **Per-product long pairs in the portfolio tab (2026-10-13, later):** for Precious Metals and Agriculture the tab's reference Combined Carry and Combined CarryMom now use each product's own pairs (`cfg.carry_pairs(product)`: short F1-F2 plus Gold F7, Silver F6, Platinum F5, Palladium F5, Corn F6, Wheat F6, Soybean F8, Soybean Oil F8, Coffee F6, Sugar F5), so they equal the dashboard's sleeves exactly (max daily difference 0; Precious Carry IR 0.106, Carry-Momentum -0.080; Agriculture -0.005 and -0.394). The 'separate tenor pairs' checkbox is hidden for them (there is no per-product row set to show). Custom sleeves still take whatever legs the user picks. The hub's Cross-Asset tab already used per-product pairs (`hub/app.py::_uses_product_pairs`). **Still not changed:** the apps' own files, `webapp/` (other branch). **Stale until regenerated (all built before the engine-wide change, with the sign-vote):** `Skewness_Research.html`, `VTI_Research.html` (built on the sign-vote Carry), the Copper Carry tradebook (`tradebooks/Metals/Copper_Carry_V2_Tradebook.xlsx`, sign-vote), the Wheat tradebook. Docs updated: `Readme Portfolio construction 10 Oct.md`, `CLAUDE.md`, methodology document Sections 5.3, 5.4 and the decisions table.

---

## 2026-10-12 (later): Skewness added as a fifth sleeve; separate research pages

- **Skewness sleeve** (after Fernandez-Perez, Fuertes and Miffre 2021, Table 1; time-series version): per product, signal = minus the skewness of the continuous series' daily log returns over 252 observations, +1 if negative, -1 if positive, 2-day lag, 5 bps costs. Added in `scripts/final_dashboard/compute_products.py` (`v["Skewness"]`); `analyze_v2.py` (`STYLES`), `analyze_twopair.py` and `build_final_dashboard_v2.py` now treat five sleeves: asset-class EW PORT and Inverse Vol, combined books, By Style, Cross-Pair, correlations and the page text. Existing sleeves unchanged (maximum difference 0). `Final_Research_Dashboard.html` and `Final_Research_Dashboard_2012.html` regenerated (the 2012 page via `run_2012_variant.py`).
- Separate research pages, not part of the dashboards: `Skewness_Research.html` (`skewness_research.py`), `VTI_Research.html` (`vti_research.py`), `OI_Research.html` (`oi_research.py`, not pushed). VTI (inverse-variance style weights, 60 months) and OI (power, exponential, mean-variance, minimum-variance) did not beat Equal Weight or the existing Inverse Vol, so they were not added to the dashboards.
- `paper_check.py`: cross-sectional rebuild of the paper's TS, Momentum and Skewness styles on our five energy products. Term structure and the correlation structure agree with the paper's Tables 3 and 4 (Sharpe 0.67 vs 0.57; correlations Skewness-TS 0.33 (0.28), Skewness-Mom 0.21 (0.13), TS-Mom 0.69 (0.66)); Momentum agrees in the first two sub-periods and not the last (-0.44 vs 0.18); Skewness does not match (Sharpe 0.44 vs -0.02 full sample; the paper finds it insignificant). Universe (5 contracts against about 10), data vendor and sample (ours from 2007) differ.
- Methodology document: Section 5.8 (Skewness), five sleeves throughout.

---

## 2026-10-12 (latest): three regimes in the Final Research Dashboard

- New `scripts/final_dashboard/final_regimes.py`: R1 2011-01-01 to 2016-12-31, R2 2017-01-01 to 2021-12-31, R3 2022-01-01 to the last price date (no overlap). Replaces the four regimes (2011-15, 2016-19, 2020-21, 2022-26) for this dashboard only; `research/regimes.py`, `run_regime_table.py` and the Streamlit apps keep the four-regime scheme.
- `analyze_v2.py` and `analyze_twopair.py` import the windows from `final_regimes.py`; `build_final_dashboard_v2.py` has three regime columns (R1 2011-2016, R2 2017-2021, R3 2022-2026, plus Full and 2026 YTD) and a Regimes note on the Notes tab. Rebuilt `Analysis/Final_Research_Dashboard.html`. Only the horizon columns changed: every Full and 2026 figure, the equity curves and the correlations are identical to the previous build.
- Check: all regime figures (return, volatility, max drawdown, IR) on the six asset-class tabs, the two All 5 books, By Style and Cross-Pair were recomputed with separate code from the saved sleeve series: 2,120 figures, 0 differences. Opened in Chrome: every tab renders, no console errors.

---

## 2026-10-11: source-data fixes (Sugar, Brent) and WTI Momentum input

- `scripts/rolling_continuous.py`: new `DATA_FIXES` / `apply_data_fixes`, applied in `load_metal_prices` and in the Energy and Agriculture `load_curve`. Sugar No.11 F1 on 2025-06-30 (empty in the file) set to 15.48 (Jul-25 settle, supplied by the user); Brent's 2017-01-02 row (exchange holiday, empty curve) removed. Before the fix the Brent continuous series lost the 2016-12-30 to 2017-01-03 move, and Brent (2017-01-04 to 2017-12-20) and Sugar (2025-07-02 to 2026-06-30) Momentum were flat for 250 days because the 250-day average needs a full window.
- `research/configs/energy.py`: `load_f1_series_logret("WTI")` now replaces `F1_raw` on 2020-04-20 (-37.63) with the imputed curve value (16.005), so Momentum uses the same corrected price as Carry and Value. The continuous series is unchanged.
- Rebuilt `Analysis/Final_Research_Dashboard.html`. Only WTI Momentum, Brent (all sleeves) and Sugar (Momentum, Carry, Carry-Momentum) series changed; every other product is identical. Full-sample IR moves: Energy EW PORT 0.490 to 0.487, Agriculture Momentum -0.131 to -0.151, Agriculture EW PORT -0.205 to -0.212.
- `research/engine.py` (same day, second change): (1) `combine_returns("inverse_vol")` now lags the rolling volatility one observation (`.shift(1)`), so day t's weights use returns up to t-1; the docstring already claimed this. Full-sample IR of the Inverse Vol portfolios: Metals 0.118 to 0.111, Energy 0.481 to 0.477, Energy ex-NatGas 0.604 to 0.606, NGL 1.100 to 1.107, Precious -0.230 to -0.214, Agriculture -0.248 to -0.243. `dashboard_portfolio_tab.py` (Streamlit) also calls this function, so its inverse-vol portfolios change the same way. (2) Momentum moving averages (`ma_crossover_position`, `momentum_composite_position`, `raw_signal_momentum`) use `_ma`, which needs at least 90% of the window (`MA_MIN_FRACTION`) instead of a full window; complete windows give identical values. With the Brent and Sugar data fixed, no product series changed (maximum difference 0).
- New "By Style" tab (`analyze_v2.py` -> `res["bystyle"]`, `build_final_dashboard_v2.py`): each sleeve (Momentum, Carry, Carry-Momentum, Value) is equal-weighted across the five asset classes on common dates, then the four style series are combined into one EW PORT and one Inverse Vol portfolio (63-day, lagged), with and without NatGas (selector). Check: its EW PORT equals the "EW sleeves, EW across" row of the All 5 tabs (IR 0.646 with NatGas, 0.701 ex-NatGas). Page JavaScript syntax-checked; the tab was not opened in a browser.
- Rolling-correlation fix (`scripts/final_dashboard/analyze_v2.py`, `build_final_dashboard_v2.py`): the Equal Weight and Inverse Vol rolling series have different lengths (3,886 from 2011-01-04 and 3,604 from 2012-02-24) but shared one date list taken from the Inverse Vol sample, so the Equal Weight chart was mis-dated and cut short. Dates are now stored with each method, with an assertion that dates and values have equal length; the page's sample-size note now lists days per strategy (Inverse Vol rows 3,604, others 3,886) instead of one number. A rolling value was checked against a direct pandas rolling correlation (identical).

---

## 2026-10-11 (later): Streamlit "Nth trading day" roll option now rolls only in each contract's expiry month

**Why.** Each Streamlit app has a "Rolling Logic" selector with a second option, "Nth trading day of the month", implemented in
`scripts/rolling_continuous_5td.py`. It rolled on the Nth trading day of **every calendar month**. For products with a contract expiring every
month (LME metals, energy, NGL) that equals the new research rule, but for Gold, Silver, Platinum, Palladium and the agricultural products
(contracts expire only in some months) it also rolled in months where nothing expires: 186 rolls over 2011 to mid-2026 against 62 to 108 under
the research rule.

**Change.**
- `scripts/rolling_continuous_5td.py`: roll dates now come from `rolling_continuous._compute_roll_dates_expiry_month` (Nth trading day of the
  month in which each contract's last trade date falls). Docstrings and the CLI help updated. `_nth_trading_days` (every month) is kept but unused.
- The five apps (`metals_dashboard`, `energy_dashboard`, `ngl_dashboard`, `precious_metals_dashboard`, `agri_dashboard`): the option label is now
  "Nth trading day of the expiry month". The default was unchanged at first and was changed later the same day (see "Default" below).

**Verified** (16 products: Copper, Zinc, WTI, NatGas, Ethane, Butane, Gold, Silver, Platinum, Palladium, Corn, Wheat, Soybean, Soybean Oil,
Coffee, Sugar):
- Metals and Energy: results identical to before (same rolls, same continuous series, same phases).
- NGL: identical from 2011 (daily differences about 1e-16); one fewer roll in August 2009 (the old version rolled in a first partial month with no
  expiring contract).
- Precious and Agriculture: roll dates now equal the main engine's `roll_rule="expiry_month_nth_td"` exactly, and the continuous series equals
  the main engine's series (maximum difference 0). Roll counts, Gold 261 to 130, Silver 261 to 109, Platinum/Palladium 261 to 87, Corn/Wheat/Coffee
  261 to 109, Soybean 261 to 153, Soybean Oil 261 to 174, Sugar 261 to 88 (full history).

**Roll-day cost fix (same day, separate commit).** The Nth-trading-day option labelled its roll days `Roll_TD<N>`, but the transaction-cost
functions (`common_shared.py` line 321, `research/engine.py` lines 60 and 142, and the Excel tradebook formulas) charge the roll-day cost only for
phases starting with `Roll_LTD`. So under that option the apps charged no roll-day cost for positions held through a roll, whereas the "N days
before" option and the research numbers did (holding a constant long over the full history: Gold 0.11 against 50.01 in price units, Corn 0.05
against 12.37, WTI 0.01 against 4.70, Copper 0.75 against 477.79). `scripts/rolling_continuous_5td.py` now labels roll days `Roll_LTD-<N>`, the same
as `scripts/rolling_continuous.py`; no cost function was edited. After the change the option's phases, continuous series and constant-long cost
equal the main engine's expiry-month rule exactly (Gold, Corn, WTI, Copper). **App results under this option now include the roll-day cost, so
they are slightly lower than before.**

**Default (same day, separate commit).** The five apps now start on "Nth trading day of the expiry month" (`index=1` in each app's "Rolling Logic"
selector, N = 5), so a new session uses the same roll as the research numbers and `Analysis/Final_Research_Dashboard.html`. "N days before last
trading day" is still selectable. The change only affects new sessions (a session that already has a stored selection keeps it). Checked by running
each app up to the point where its tabs begin (sidebar, roll selector, data and continuous-series build) with Streamlit's test runner: no exceptions
or errors, the selector shows the expiry-month option and N = 5, for Metals, Energy, NGL, Precious and Agriculture. A full run of every tab was not
possible headlessly (the tabs compute very large heatmaps), so the tabs themselves were not exercised.

---

## 2026-10-11: engine and configs updated to the Final Research Dashboard setup

**One-line summary.** Every reportable number now uses the 2026-09-24 price files (data through 2026-09-23), rolls on the 5th trading day of each
contract's expiry month, and uses two tenor pairs per product for Precious and Agriculture with the sign-vote Carry blend of the 10 Oct rule. The
Streamlit apps keep their existing roll default.

### What changed, by file

| File | Change |
|---|---|
| `scripts/rolling_continuous.py` | **Data:** `ENERGY_/METALS_/PRECIOUS_FUTURES_FILE` now point to `data/Prices_0924/` (2026-09-24 pull, through 2026-09-23); `NGL_FUTURES_FILE` points to `data/Prices_0924/NGL_Futures_Updated_labels_corrected.xlsx`. Calendars unchanged. **Roll rule:** new opt-in rule `"expiry_month_nth_td"` (roll on the Nth, default 5th, trading day of the month in which the contract's last trade date falls); original rule kept as `"ltd_minus_n"` and still the default of `build_rolling_f1` / `get_metal_rolling_f1` (new `roll_rule` argument). New helpers `_compute_roll_dates_expiry_month`, `_roll_dates_for_rule`, constants `ROLL_RULES`, `DEFAULT_ROLL_RULE`, `ROLL_FALLBACK_COUNT`. Contracts whose last trade date is after the last price date no longer get snapped to the last price date under the new rule (the old rule did, which put a spurious roll in the final week). **Energy config:** `QS` price sheet now `"Low Sulphur Gasoil (ICE Europe)"` (the 24-Sep file renamed it; data identical to the old "Singapore Gasoil (ICE)" sheet). |
| `research/ratio_continuous.py` | `build_rolling_f1_ratio` and `get_metal_rolling_f1_ratio` accept `roll_rule` and pass it through. Default unchanged. |
| `research/configs/{metals,energy,ngl,precious,agri}.py` | Each sets `ROLL_RULE = "expiry_month_nth_td"`, `ROLL_N = 5` and passes them to both roll builders in `load_f1_series` / `load_f1_series_logret`. Each gets `carry_pairs(product)`. **Precious:** `CARRY_TENOR_PAIRS` is now the short pair `[("F1","F2")]` (was F1-F3) and `CARRY_LONG_FAR_BY_PRODUCT = Gold F7, Silver F6, Platinum F5, Palladium F5`. **Agriculture:** `CARRY_TENOR_PAIRS` stays `[("F1","F2")]`; `CARRY_LONG_FAR_BY_PRODUCT = Corn F6, Wheat F6, Soybean F8, Soybean Oil F8, Coffee F6, Sugar F5`. Metals/Energy/NGL `carry_pairs` just returns their existing uniform pairs. `energy.py`: Singapore Gasoil sheet name updated (see above). |
| `research/run_regime_table.py` | **Implements the 10 Oct Carry rule:** Carry and Carry-Momentum are now V2-only (z-score on carry slope; Carry-Momentum on the 20-day slope change), one signal per tenor pair, blended at signal level by sign-vote, lag applied once, using each product's `carry_pairs(product)`. Output rows are now `Momentum, Carry, CarryMom, Value, EW PORT, Inverse Vol` (Inverse Vol = trailing 63-day, daily). Accepts `agri`. `CARRY_VARIANTS = ("V2",)`; set to `("V1","V2")` to reproduce the old composite. |
| `research/cross_asset_engine.py` | `per_product_four_row(..., per_product_pairs=False)`: when True each product uses its own `cfg.carry_pairs(product)`. Default False, so every existing caller (Streamlit hub, cross-asset tabs) behaves as before. |
| `research/generate_tradebooks_logret.py` | `_rebuild_ratio_series` passes the config's roll settings so tradebooks use the same roll rule as `load_f1_series_logret`. |
| `data/Prices_0924/` | Added `Energy_Futures_Updated.xlsx`, `Metals_Futures_Curve_Updated.xlsx`, `Precious_Metals_Futures_Updated.xlsx`, `NGL_Futures_Updated_labels_corrected.xlsx`, `Expiry_Calendars_Updated_2.xlsx` (24-Sep consolidated calendar, provenance only). The raw mislabelled `NGL_Futures_Updated.xlsx` is **not** committed (kept locally). |
| `scripts/final_dashboard/` | New. The pipeline that builds `Analysis/Final_Research_Dashboard.html` plus the validation and NGL label-check scripts (see its README). |
| `Analysis/Final_Research_Dashboard.html` | Rebuilt: all five asset classes through 2026-09-23, new roll rule, two-pair Carry/Carry-Momentum for Precious and Agriculture, Correlations, Cross-Pair, cumulative-return curves. |
| `README.md`, `Readme Portfolio construction 10 Oct.md`, `CLAUDE.md` | Status notes pointing to this log. |

### Decisions behind the change (all by the user, 2026-10-10/11)
- Carry rule: sign-vote across tenor pairs (flat when the pairs disagree); keep two tenors for Precious and Agriculture.
- Precious short pair F1-F2 (gap of 2 to 3 months); long pairs about 12 months out; Platinum/Palladium F5 used as is (it has data from 2010-02).
- Roll on the 5th trading day of the **month of the last trade date** (not the contract's delivery month, and not every calendar month).
- All price data through 2026-09-23.
- Methods in the final dashboard: Equal Weight and Inverse Vol only; Correlations, Cross-Pair and cumulative-return curves kept.

### Data findings recorded here
- **Price files (Prices_0924 vs 06-30):** history identical for Metals, Energy, Platinum, Palladium, Isobutane; Gold and Silver had only their deepest columns revised (Gold F14 to F20, Silver F12 to F16, from mid 2025), which no code reads; Copper LME F1 lost 12 values on 2005 expiry dates (before the analysis window).
- **NGL sheet labels in the 24-Sep file are wrong** (CAP/BAP/DAE/PCW cyclically shifted). Verified: BAP matches EIA Mont Belvieu propane spot (FRED `DPROPANEMBTX`: median ratio 1.003, level correlation 0.995, 5-day change correlation 0.90); CAP is ethane (2012 vs 2011 average -47% against EIA's reported -48%; 24 cents/gal on 2012-12-19 vs a reported 25 cents; 13 cents/gal on 2020-03-16 vs a reported 12.9 cents); DAE is normal butane; IBD isobutane; PCW is ethylene (8.1 cents/lb on 2020-04-03 vs reported record low 8 cents/lb). Correct mapping: Ethane=CAP, Propane=BAP, Butane=DAE, Isobutane=IBD, Ethylene=PCW. `NGL_Futures_Updated_labels_corrected.xlsx` has the same data with corrected names (identical to the July file's sheets on every overlapping date). **The data provider's file should be corrected at source.**
- **Singapore Gasoil label:** the old sheet "Singapore Gasoil (ICE)" (ticker QS) is identical to the new "Low Sulphur Gasoil (ICE Europe)"; the consolidated calendar also calls QS ICE Low Sulphur Gasoil. The product key `SingaporeGasoil` was kept (it is excluded from every dashboard) but the label is probably wrong.
- **Calendars:** the 24-Sep consolidated calendar agrees with `expiry_calendars_20260701.xlsx` on every shared contract (zero last-trade-date differences), so the existing calendars stay.
- **Roll rule effect:** about 14 to 16 trading days before expiry for Energy, NGL, Precious and Sugar; about 6 for Metals; about 5 for Corn, Wheat and Soybeans. One contract, Isobutane IBDX09 (last trade 2009-11-30), gets no roll at all: the Isobutane price series has only one date in November 2009 (2009-11-10, then 2009-12-14), so there is no 5th trading day and no earlier day to roll on. It sits at the very start of the history, before the 2011 reporting window, so no reported number is affected.

### Validation (run 2026-10-11)
1. **Data-file regression:** with the *original* roll rule, the new price files reproduce the old continuous series exactly through 2026-05-29 (Gold, Platinum, WTI, Copper, Corn, Ethane, Propane, Butane): max log difference 0, phases identical.
2. **Repo-defaults rebuild vs the dashboard series:** rebuilding all 23 products x 4 sleeves using only the repo's own settings (no overrides) matches the series behind the dashboard exactly (worst absolute difference 0.0e+00). `cross_asset_engine.per_product_four_row(..., per_product_pairs=True)` for Precious and Agriculture also matches (0.0e+00). (`scripts/final_dashboard/validate_engine.py`)
3. **Original default preserved:** a call without `roll_rule` reproduces the earlier legacy-rule build (daily log-return difference 2e-15).
4. **`python research/run_regime_table.py <asset>`:** Metals and Precious reproduce the dashboard's sleeve, EW PORT and Inverse Vol rows exactly. Agriculture differs by at most 0.005 IR (e.g. Momentum -0.129 vs -0.131, Inverse Vol -0.248 vs -0.243): `run_regime_table.py` averages products after zero-filling days a product does not trade, while the dashboard keeps only common dates. Energy and NGL via `run_regime_table.py` use `cfg.PRODUCTS` (7 and 6 products including the excluded ones), so they differ from the dashboard by design.
5. All changed files compile and the configs import.

### Not changed / known follow-ups
- **Streamlit apps** (`*_dashboard/app.py`, `dashboard_portfolio_tab.py`, `hub/app.py`) were not edited in the entry below (the "Nth trading day" option was changed in the later entry above): they read the new data automatically through the constants in `scripts/rolling_continuous.py`, keep their "Rolling Logic" selector (default "N days before last trading day"), and use one uniform tenor-pair list per asset class, so they show Precious with the short F1-F2 pair only and Agriculture with F1-F2 only (no per-product long pair). Adding the new roll rule as a selector option and per-product pairs to those apps is a separate change.
- `webapp/` and the `feature/react-dashboard` branch were not touched.
- Metals, Energy and NGL roll calendars are not Bloomberg-matched (no monthly single-contract files exist to check them).
- Platinum/Palladium F5 and Gold F7 sit beyond the range the real-volume liquidity study found fully liquid; Agriculture has had no liquidity study.
- The README "Status" text still describes the 3 Aug locked parameters in places; the figures in `Readme Portfolio construction 10 Oct.md` were produced before the roll-rule and data changes.

### How to switch back
- Original roll rule for research numbers: set `ROLL_RULE = "ltd_minus_n"` (and `ROLL_N = 5`) in the config(s).
- Older Carry composite in `run_regime_table.py`: set `CARRY_VARIANTS = ("V1", "V2")`.
- Old data: point the four `*_FUTURES_FILE` constants back to `data/06-30/` (NGL back to `NGL_Futures_Updated.xlsx`).
- Single-pair Precious Carry: set `CARRY_LONG_FAR_BY_PRODUCT = {}` and `CARRY_TENOR_PAIRS = [("F1","F3")]` in `research/configs/precious.py`.

---

## Earlier work in this series (what led to the engine update)

| Date | What was done | Where |
|---|---|---|
| 2026-10-08 | Checked which contract months Bloomberg uses for gold, silver, platinum, palladium and COMEX copper, by exact-price matching the generic F1..Fn series to the single-contract monthly files; found Bloomberg uses Gold Feb/Apr/Jun/Aug/Oct/Dec, Silver and Copper Mar/May/Jul/Sep/Dec, Platinum Jan/Apr/Jul/Oct, Palladium Mar/Jun/Sep/Dec, and rolls the day after the last trade date | `outputs/roll_check/*_pos_by_month.csv` (local) |
| 2026-10-09 | Wrote up the roll-month findings; discussed CFTC (Commitments of Traders) data sources and coverage (no files) | `outputs/roll_check/Bloomberg_Roll_Months_Check.docx` (local) |
| 2026-10-10 | Built the aligned Precious expiry calendar (gold, silver, platinum, palladium filtered to Bloomberg's months) with a contract-by-contract cross-check against the monthly files; compared Gold carry (F1-F2) tradebooks and the full Precious strategy set on the original vs aligned calendar | `data/06-30/expiry_calendars_20260701_aligned.xlsx`; `outputs/calendar_comparison/` (local) |
| 2026-10-10 | Pulled `origin/main` (Agriculture commits, carry-rule README). Switched the engine to the aligned Precious calendar and four Precious products; commit `0b1e8aa` (committed 2026-10-10 23:28, pushed to `origin/main` with the `Dimil123` account) | `scripts/rolling_continuous.py`, `research/configs/precious.py` |
| 2026-10-10 | Agriculture: investigated the Sugar calendar problem, matched Bloomberg's agri series to the monthly files, built the Bloomberg-matched agri calendar (six products incl. Sugar) and compared performance | `data/Prices_0924/Agri_Rolling_Calendar_bloomberg_matched.xlsx`, `Analysis/Agri_Aligned_Calendar_Dashboard.html` |
| 2026-10-10 | First Final Research Dashboard (five asset classes, EW and Inverse Vol, Energy with/without NatGas, combined books) | `Analysis/Final_Research_Dashboard.html` (commit `0b1e8aa`) |
| 2026-10-11 | Sensitivity studies, all in-sample and local: signal inversion (Metals/Precious/Agri), Value lookback 1y/3y/5y, combined-value vs sign-vote Carry and Carry-Momentum, Precious/Agri second tenor pair, Platinum/Palladium F5 gap check (cannot be filled from the monthly files), Wheat Carry and Soybean Momentum tradebook | `outputs/final_dashboard/*.json`, `tradebooks/Agri/` (local) |
| 2026-10-11 | Pulled `origin/main` (Kartavya: V2-only carry default in the hub, Agriculture as fifth asset class) | git |
| 2026-10-11 | Rebuilt the Final Research Dashboard on the 24-Sep price files with the new roll rule and two-pair Precious/Agriculture Carry; added Correlations, Cross-Pair and cumulative-return curves | `Analysis/Final_Research_Dashboard.html` |
| 2026-10-11 | Verified the NGL sheet labels against EIA propane spot and published prices; wrote the corrected NGL workbook | `data/Prices_0924/NGL_Futures_Updated_labels_corrected.xlsx` |
| 2026-10-11 | Engine and configs updated (this entry) | see above |
