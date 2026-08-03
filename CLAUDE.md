# Agent notes for this repo

Read `README.md`'s "Status" section first for current locked parameters (Value contract, Carry tenors per asset class) — it's kept up to date as of the date shown there.

## The one trap most likely to cause confusion

**A product appearing in `research/configs/{energy,ngl}.py`'s `PRODUCTS` list does NOT mean it appears in that asset class's live dashboard or Portfolio tab.** As of 2026-08-03:

- `configs/energy.py`'s `PRODUCTS` has 7 products (including Singapore Gasoil, Fuel Oil) — but `energy_dashboard/app.py` and `webapp/`'s Energy page only show/compute 5 (Singapore Gasoil and Fuel Oil excluded).
- `configs/ngl.py`'s `PRODUCTS` has 6 products (including Ethylene, Propylene) — but `ngl_dashboard/app.py` and `webapp/`'s NGL page only show/compute 4 (Ethylene and Propylene excluded).

This is intentional and applies identically on both `main` (Streamlit) and `feature/react-dashboard` (React/FastAPI). It is a dashboard/UI-layer filter only:
- Streamlit: `dashboard_portfolio_tab.py`'s `excluded_products` param, set per-dashboard in `energy_dashboard/app.py` (`ENERGY_PORTFOLIO_EXCLUDED`) / `ngl_dashboard/app.py` (`NGL_PORTFOLIO_EXCLUDED`).
- React backend: `webapp/backend/services/portfolio.py`'s `EXCLUDED_PRODUCTS` dict; `webapp/backend/config_registry.py`'s products dicts (standalone tabs); `webapp/frontend/src/App.tsx` (its own separate hardcoded product lists — a real, easy-to-miss third place this has to be kept in sync, since the frontend doesn't fetch its product list from the backend).

If you're asked to add a product, remove one, or change a product list, check all of: the relevant `configs/*.py` (engine — usually should stay untouched for this kind of change), the Streamlit dashboard's `PRODUCT_ORDER`/`*_EXCLUDED` constant, and (if touching the webapp) `config_registry.py` + `services/portfolio.py`'s `EXCLUDED_PRODUCTS` + `App.tsx`'s hardcoded arrays. Missing any one of these leaves the two live apps (or the two views within one app) inconsistent with each other.

**No cross-asset-class ("Diversified Risk Premia") portfolio exists yet** — combining all 4 asset classes into one book is discussion-only (see `project_cross_asset_portfolio_construction` in project memory, not in this repo). Whoever builds it must reuse the exclusion lists above, not read `configs/*.py`'s raw `PRODUCTS`, or Singapore Gasoil/Fuel Oil/Ethylene/Propylene will silently reappear.

## Branches

- `main` — Streamlit dashboards (Streamlit Cloud deploys from here).
- `feature/react-dashboard` — React/FastAPI rebuild (`webapp/`), unmerged. Render (backend) auto-deploys from this branch on push. **Vercel (frontend) does NOT auto-deploy from git** — it's not Git-connected; changes need a manual `vercel --prod` from `webapp/frontend`.
- Shared engine files (`common_engine.py`, `common_shared.py`, `dashboard_portfolio_tab.py`, `research/engine.py`, `research/risk_parity.py`, `research/configs/*.py`) are used unchanged by both branches — the React backend imports them directly. Any fix to these files needs to land on whichever branch is missing it, or the two live apps will silently diverge. Check `git branch --show-current` before editing them.

## Regenerating reported numbers

`python research/run_regime_table.py <metals|energy|precious|ngl>` is the canonical full-sample + regime-conditional table builder — use this (or `--window-grid` for the JS-ready format `Analysis/Research_Dashboard_F3.html` consumes), not ad hoc scripts, when you need reportable numbers. Changing a `configs/*.py` parameter (Value contract, Carry tenor pairs, etc.) changes every downstream number that touches that strategy, including every portfolio combine method — regenerate rather than hand-patch when parameters change.
