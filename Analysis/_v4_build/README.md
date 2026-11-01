# v4 build scripts (Risk Premia Analysis v4_2012.docx)

Untracked working folder. Not part of the repository's pipeline. Everything is relocatable (paths are relative to this folder).

## What it needs
- `../../outputs/final_dashboard_2012/products_2012_nets.pkl` (five sleeves per product). Produced by Dimil's pipeline from the repo root:
  `python scripts/final_dashboard/compute_products.py` then `python scripts/final_dashboard/run_2012_variant.py`.
  The second script rewrites the tracked `Analysis/Final_Research_Dashboard_2012.html`; restore it afterwards with `git checkout -- Analysis/Final_Research_Dashboard_2012.html` if you did not mean to change it.
- `dimil_D.json`: the dataset embedded in Dimil's committed 2012 dashboard (cross-check only).
- `dfii10.csv` (FRED 10-year real yield, downloaded 2026-10-12) and `etf_prices_1012.csv` (SPY, AGG, DBC, GLD, Yahoo Finance via yfinance, 2026-10-12).
- Python with pandas, numpy, matplotlib, python-docx, PyMuPDF (optional).

## Files
- `rp.py`, `facts.py`, `facts2.py`, `facts3.py`: full-precision recomputation of every figure (class sleeves, portfolios, correlations, pairs, Skewness legs, tenor tables, real yields, ETF correlations). Every number in the text comes from here.
- `text_front.py`, `text_metals.py`, `text_energy.py`, `text_precious.py`, `text_ngl.py`, `text_agri.py`, `text_corr.py`, `text_appendix.py`: one module per section. Claims such as "positive in every period" are asserted in code (`chk`), so a wrong claim stops the build.
- `make_charts.py`: the 33 figures into `v4img/`.
- `doc_lib.py`, `build_v4.py`: assemble the Word file (uses v3's styles). `build_v4.py` refuses to overwrite an existing file; change `OUT` for a new version.
- `verify_independent.py`: recomputes the dashboard tables from the per-product returns and compares with `dimil_D.json` (3,504 numbers at the time of writing).
- `mk_intro_v4.py`: builds the Introduction redraft from the previous Introduction file.

## Run order
1. Pipeline (above), then `python make_charts.py`.
2. `python verify_independent.py` (should report zero mismatches).
3. Edit `OUT` in `build_v4.py`, then `python build_v4.py`.

## Known conventions
- Numbers are formatted from full precision (Dimil's dataset is rounded to 3 decimals, which can flip a second-decimal digit).
- External facts in the text are hard-coded and listed with sources in the document's Verification Log appendix.
