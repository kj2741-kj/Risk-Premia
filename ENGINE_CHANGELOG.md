# Engine and research change log

Newest entry first. Author of the entries below: Dimil Patel (with Claude Code assisting). Dates are the dates the work was done (for the earlier
analysis steps they come from file timestamps). The 2026-10-11 entry is the engine/config update; the sections after it record the analysis work
that led to it.

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
- **Streamlit apps** (`*_dashboard/app.py`, `dashboard_portfolio_tab.py`, `hub/app.py`) were not edited: they read the new data automatically through the constants in `scripts/rolling_continuous.py`, keep their "Rolling Logic" selector (default "N days before last trading day"), and use one uniform tenor-pair list per asset class, so they show Precious with the short F1-F2 pair only and Agriculture with F1-F2 only (no per-product long pair). Adding the new roll rule as a selector option and per-product pairs to those apps is a separate change.
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
