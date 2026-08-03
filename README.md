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

## Status (as of 2026-08-03)

**IMPORTANT for anyone (human or AI agent) reading this repo: the engine's `configs/*.py` PRODUCTS lists and what the LIVE DASHBOARDS actually show/compute are deliberately different as of 2026-08-03.** See "Dashboard-only product exclusions" below before assuming a product that appears in a config file is also in the dashboard/Portfolio tab, or vice versa.

All 4 asset classes have a locked ex-ante strategy set and a full-sample + regime-conditional result. Value's anchor contract is **F3** everywhere (changed from F8 2026-08-03, applied uniformly):

- **Metals** (Copper/Aluminium/Lead/Zinc): Momentum, Carry V1+V2 (F1-F3 and F1-F13), Carry-Momentum (V3), Value (F3). Unchanged since 2026-07-24. FDR (q=0.10) on the 49-cell grid: **0 survivors**.
- **Precious Metals** (Gold/Silver/Copper-COMEX/Platinum/Palladium): Carry tenor is **F1-F3** (changed 2026-08-03 from F1-F2 — user's explicit decision, overriding a real-volume liquidity finding that Platinum/Palladium F3 liquidity is weak, 87.0%/68.5% days traded; see `configs/precious.py`'s docstring for the full caveat).
- **Energy** (engine PRODUCTS: WTI/Brent/RBOB/HeatingOil/NatGas/SingaporeGasoil/FuelOil — **dashboard shows only the first 5**, see below): Carry F1-F3 + **F1-F13** (changed 2026-08-03 from F1-F12, to match Metals). Fuel Oil has no F13 column at all and is still in this file's PRODUCTS list, so its Carry(F1-F13)/CarryMom(F1-F13) leg is silently flat/zero in `run_regime_table.py`'s reports (no crash, just a disclosed dilution) — irrelevant to the dashboard since Fuel Oil isn't shown there. WTI's 2020-04-20 negative print patched (single-cell impute).
- **NGL** (engine PRODUCTS: Ethane/Propane/Butane/Isobutane/Ethylene/Propylene — **dashboard shows only the first 4**, see below): Carry is now **two tiers** as of 2026-08-03 — F2-F4 (short, new) and F2-F14 (changed from Bogorad's original F4-F15, for a 12- rather than 11-month span). Neither pair has been re-verified for liquidity/seasonality since; see `configs/ngl.py`'s docstring for the specific caveat (F2 reintroduces near-tenor heating-season seasonality that F4 was originally chosen to avoid).
- **StatArb** (Energy/NGL only — Metals/Precious tested and genuinely null): 8 cross-commodity spreads, none of which reference Singapore Gasoil, Fuel Oil, Ethylene, or Propylene. FDR (q=0.10) on 64 valid cells: **2 survivors** — EW StatArb(8) full-sample (p=0.00052, the standout) and one isolated regime cell. **This is the first FDR-robust result in the project.** Not yet rerun since the 2026-08-03 tenor changes above (StatArb's own tenors are unaffected, but hasn't been re-verified).

### Dashboard-only product exclusions (2026-08-03) — read this before touching products lists

- **Energy dashboard** (`energy_dashboard/app.py`, all tabs including Portfolio) excludes **Singapore Gasoil and Fuel Oil**. `webapp/` (the React/FastAPI rebuild) excludes them too, via `config_registry.py`'s products dict and `services/portfolio.py`'s `EXCLUDED_PRODUCTS["energy"]`.
- **NGL dashboard** (`ngl_dashboard/app.py`, all tabs including Portfolio) excludes **Ethylene and Propylene**. `webapp/` excludes them too, the same way (`EXCLUDED_PRODUCTS["ngl"]`).
- In BOTH cases, `configs/energy.py`'s and `configs/ngl.py`'s own `PRODUCTS` lists are **untouched** — still 7 and 6 respectively. This is a dashboard/UI-layer filter only (an `excluded_products` param threaded through `dashboard_portfolio_tab.py`, and the webapp's `EXCLUDED_PRODUCTS` dict), not an engine change. `run_regime_table.py` and any other script that imports `configs/{energy,ngl}.py` directly still sees and computes on the full product list.
- **Why this matters if you're extending this codebase**: there is currently no cross-asset-class ("Diversified Risk Premia") portfolio built yet — combining all 4 asset classes' EW Portfolios into one book is still discussion-only. When that gets built, it MUST reuse these same per-asset-class exclusion lists (not read `configs/*.py`'s raw `PRODUCTS`), or these 4 products will silently reappear in the cross-asset book.

Consolidated view: `Analysis/Research_Dashboard_F3.html` (supersedes the older `Research_Dashboard.html`, which is stale/pre-F3 and kept only for historical comparison).

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
