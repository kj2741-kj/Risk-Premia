# final_dashboard pipeline (2026-10-11)

Scripts that build `Analysis/Final_Research_Dashboard.html`. They use the repo's own settings (data in `data/Prices_0924`, the 5th-trading-day-of-
expiry-month roll, per-product tenor pairs from `research/configs/*.carry_pairs`), so no in-memory overrides are needed. Run from the repo root,
in this order. Intermediate results are written to `outputs/final_dashboard/` (gitignored).

| Step | Script | Writes |
|---|---|---|
| 1 | `compute_products.py` | `products_v2_nets.pkl` (net log returns of the four sleeves for all 23 products, plus single-pair legs for Precious/Agriculture) |
| 2 | `analyze_v2.py` | `final_v2.json` (asset-class tabs, combined books, cross-pairs, correlations, equity curves) |
| 3 | `analyze_twopair.py` | `twopair_v2.json` (single pair vs two pairs, Precious and Agriculture) |
| 4 | `build_final_dashboard_v2.py` | `Analysis/Final_Research_Dashboard.html` |

Checks: `validate_engine.py` rebuilds every product from repo defaults and compares with `products_v2_nets.pkl`; `ngl_label_check.py` and
`make_ngl_corrected.py` document the NGL sheet-label verification and the corrected workbook (needs the FRED propane CSV in %TEMP%, see its docstring).
