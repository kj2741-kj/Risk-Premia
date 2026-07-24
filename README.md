# Risk Premia — Multi-Asset Momentum/Carry/Value Research

## What's here

Two layers:

1. **Dashboards** (`metals_dashboard/`, `precious_metals_dashboard/`, `energy_dashboard/`, `ngl_dashboard/`, `hub/`) — the original live Streamlit apps (Momentum/Carry/Value/Comparison tabs per asset class), built on `common_engine.py` / `common_shared.py` / `common_curve_loader.py`. Stable, not part of active research right now.
2. **`research/`** — a separate, batch-mode research pipeline for the exploratory question *"where does a classical risk premium (momentum/carry/value) genuinely persist across this multi-asset universe, and does it survive multiple-testing correction and out-of-sample validation?"*. Deliberately decoupled from the dashboards (no Streamlit dependency, zero risk to the live apps).

## `research/` layout

| File | Purpose |
|---|---|
| `engine.py` | Signal/PnL/Sharpe functions. Both dollar-PnL (legacy, reference only) and **log-return** (the methodology used for all cross-asset results) variants. Composite Momentum (3-way MA average) and Carry (V1+V2 average) functions. |
| `ratio_continuous.py` | Multiplicative (ratio) continuous-F1 builder — required for log returns since the dashboards' additive `F1_continuous` goes negative on several products. |
| `regimes.py` | Locked 7-regime scheme (2006–present, cross-asset macro-dated) + slicing helpers. |
| `stats.py` | FDR (Benjamini-Hochberg), cointegration screens, regime-persistence screens. |
| `statarb.py` | StatArb sleeve (8 spreads, Energy/NGL only — tested and excluded for Metals/Precious, see below). Per-leg log-return PnL convention. |
| `configs/{metals,precious,energy,ngl}.py` | Per-asset-class ex-ante-locked parameters (product list, data paths, Carry tenor pairs, StatArb enabled/disabled). Adding a new asset class = new config file only, no engine changes. |
| `run_regime_table.py` | Canonical full-sample + regime-conditional IR table builder — run this, not ad hoc scripts, for reportable numbers. |
| `generate_tradebooks_logret.py` | Formula-driven Excel tradebooks (one workbook per strategy, one sheet per product) for auditing the engine. Asset class selected via `TRADEBOOK_ASSET_CLASS` env var. Outputs are gitignored (large, regeneratable) — see below. |

## Status (as of 2026-07-24)

All 4 asset classes have a locked ex-ante strategy set and a full-sample + regime-conditional result:

- **Metals** (Copper/Aluminium/Lead/Zinc): Momentum, Carry V1+V2 (F1-F3 and F1-F13), Carry-Momentum (V3), Value. FDR (q=0.10) on the 49-cell grid: **0 survivors**.
- **Precious Metals** (Gold/Silver/Copper-COMEX/Platinum/Palladium): same strategy set, Carry tenor corrected to **F1-F2 only** (real-volume liquidity check killed F1-F13 for all 5 products).
- **Energy** (WTI/Brent/RBOB/HeatingOil/NatGas/SingaporeGasoil/FuelOil): Carry F1-F3 + F1-F12. WTI's 2020-04-20 negative print patched (single-cell impute).
- **NGL** (Ethane/Propane/Butane/Isobutane/Ethylene/Propylene): Carry F4-F15 (Bogorad convention).
- **StatArb** (Energy/NGL only — Metals/Precious tested and genuinely null): 8 cross-commodity spreads. FDR (q=0.10) on 64 valid cells: **2 survivors** — EW StatArb(8) full-sample (p=0.00052, the standout) and one isolated regime cell. **This is the first FDR-robust result in the project.**

Consolidated view: `Analysis/Research_Dashboard.html`.

## In progress / pick up here

Excel tradebook generation (the audit step) is unfinished for the newer asset classes:

- **Energy**: 4/6 workbooks done in `tradebooks_logret_energy/` (Momentum, Carry F1-F3, Carry F1-F12, CarryMom F1-F3). **Missing: CarryMom F1-F12 and Value.** Background run was killed mid-way (environment issue, not a code bug) — rerun just those two (`build_carrymom_workbook("F1","F12")`, `build_value_workbook()`), no need to redo the 4 already saved.
- **NGL**: not started. Run `TRADEBOOK_ASSET_CLASS=ngl python generate_tradebooks_logret.py`. Note: NGL's front-month convention differs from the others (see `configs/ngl.py` docstring) and hasn't been specifically re-tested against `_rebuild_ratio_series` yet.
- Once both finish, spot-check a couple of formulas with the `formulas` Python library against the Python engine on a slice, same as was done for Metals, before treating them as verified.

Not started at all: correlation/least-correlated-combination test across the 4 asset classes' strategy return series, and Stage 2 (roll-mechanics-aware portfolio construction / cross-asset DRP).

## Data & methodology notes

- All research-pipeline results use **log returns**, not dollar PnL — necessary for the results to combine cleanly across asset classes with very different price levels (see `engine.py`'s `log_return_*` functions vs the legacy dollar-PnL ones).
- Parameters are locked **ex ante** (convention / economic reasoning / liquidity data), never by scanning for the best in-sample Sharpe — see each `configs/*.py` for the specific justification per asset class.
- `tradebooks_logret/`, `tradebooks_logret_energy/`, `tradebooks_logret_ngl/` (once built) are **gitignored** — large (multi-MB per workbook), fully regeneratable from `generate_tradebooks_logret.py`. Same convention as the existing `tradebooks/` folder.
- `scratch/` is gitignored — throwaway/debug scripts and images, not part of the pipeline.
