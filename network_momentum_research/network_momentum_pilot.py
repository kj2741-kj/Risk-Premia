"""
network_momentum_research/network_momentum_pilot.py
=====================================
Step 2 of the Network Momentum pilot (see network_momentum_features.py's
docstring and project memory for the full design/handoff): pairwise
cross-product lead-lag scan across all 22 products in the FULL
Metals+Precious+Energy+NGL universe, testing whether one product's own
lagged momentum-feature composite predicts a DIFFERENT product's next-day
return -- the commodity-only analogue of Pu/Roberts/Dong/Zohren's "network
momentum" claim (their own result is specifically that CROSS-asset-class
edges carry predictive signal beyond each asset's own individual momentum).

Design choices (all ex-ante, see project memory for the full history):
  - Composite signal per product per day = row-mean of the 8 winsorised
    paper features (network_momentum_features.py) -- one interpretable
    scalar per product/day rather than 8 separate regressions per pair
    (22*21*8 = 3696 tests would dilute the FDR family and lose the
    "one slope, one sign, one R^2" interpretability the decision rule
    below needs).
  - Predictor: composite feature, F1_raw-based (raw contract price, same
    convention as this project's own Momentum sleeve). Lagged 1 day
    (no same-bar look-ahead) before predicting the target's return.
  - Target: the target product's OWN log-return methodology series
    (log_price.diff(), F1_continuous_ratio-based) -- the same
    cross-product-combinable return convention used everywhere else in
    this pipeline (project_risk_premia_research_framework memory #16),
    NOT a raw-F1 pct_change.
  - Regression: simple OLS (scipy.stats.linregress) per directed pair,
    ordinary (non-HAC) standard errors -- same "keep it simple, let FDR +
    regime-persistence be the safety net" convention as statarb.py's
    single-sample t-test. Feature autocorrelation likely makes these
    p-values optimistic; that is exactly why the decision rule (memory)
    requires effect size + cross-regime consistency on top of FDR, not
    FDR alone.
  - Reporting window: floored at REPORT_START (2011-01-01, regimes.py),
    matching every other test in this pipeline -- NGL pairs naturally
    truncate further to NGL's own ~2009-08 start via the per-pair inner
    join, no separate carve-out needed.

Decision rule (confirmed with user, 2026-07-25): FDR (q=0.10) is a
robustness CHECK, not the sole gate -- also weigh effect size (R^2/slope,
not just significance), sign/significance consistency across the 4 locked
regimes, and whether a surviving pair is economically explainable. Outcome:
survivors that duplicate the 8 existing StatArb pairs = reassuring sanity
check, not new info, don't build the graph model. Genuinely NEW surviving
pairs = trigger to consider the real Kalofolias graph-learning
implementation. Nothing survives = null result, park Network Momentum,
consistent with this project's existing Metals/Precious StatArb findings.
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats as sstats

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
# Moved to its own network_momentum_research/ folder 2026-07-27 (separate git branch) -- still depends on
# the SHARED research/ infra (configs/*.py, regimes.py, stats.py, statarb.py), which was deliberately left
# in place since those are used by the wider Risk Premia project's other strategies too.
_RESEARCH_DIR = os.path.join(_THIS_DIR, "..", "research")
_CONFIGS_DIR = os.path.join(_RESEARCH_DIR, "configs")
for _p in (_CONFIGS_DIR, _RESEARCH_DIR, _THIS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import energy as energy_cfg  # noqa: E402
import metals as metals_cfg  # noqa: E402
import ngl as ngl_cfg  # noqa: E402
import precious as precious_cfg  # noqa: E402
from network_momentum_features import compute_paper_momentum_features  # noqa: E402
from regimes import REGIMES, REPORT_START  # noqa: E402
from stats import bh_fdr  # noqa: E402
from statarb import SPREAD_LEGS  # noqa: E402

CFG = {"metals": metals_cfg, "precious": precious_cfg, "energy": energy_cfg, "ngl": ngl_cfg}

# (asset_class, product) for all 22 products across the 4 sub-classes.
UNIVERSE: list[tuple[str, str]] = [
    (asset, product) for asset, cfg in CFG.items() for product in cfg.PRODUCTS
]
CLASS_OF: dict[str, str] = {product: asset for asset, product in UNIVERSE}

# Undirected {product_a, product_b} pairs already covered by the existing
# StatArb sleeve (research/statarb.py) -- used to flag "known pair,
# reassuring sanity check" vs "new pair, worth a closer look" below.
KNOWN_STATARB_PRODUCT_PAIRS = {
    frozenset({leg[0][1], leg[1][1]}) for leg in SPREAD_LEGS.values()
}

MIN_OBS = 252  # ~1yr of daily overlap required before a pair is even tested


def _load_product_series(asset: str, product: str) -> tuple[pd.Series, pd.Series]:
    """Returns (composite_feature, log_return) for one product, own FULL
    history (feature warm-up needs it) -- NOT pre-sliced to REPORT_START."""
    cfg = CFG[asset]
    df = cfg.load_f1_series_logret(product)
    features = compute_paper_momentum_features(df["F1_raw"])
    composite = features.mean(axis=1).rename("feature")
    log_ret = df["log_price"].diff().rename("ret")
    return composite, log_ret


def build_series_by_product() -> dict[str, tuple[pd.Series, pd.Series]]:
    print(f"Loading {len(UNIVERSE)} products across {len(CFG)} asset classes...")
    out = {}
    for asset, product in UNIVERSE:
        out[product] = _load_product_series(asset, product)
        print(f"  {asset:<10}{product}")
    return out


def _regress(x: pd.Series, y: pd.Series, start: str, end: str | None = None) -> dict:
    sub = pd.concat([x, y], axis=1, join="inner")
    if start:
        sub = sub.loc[start:]
    if end:
        sub = sub.loc[:end]
    sub = sub.dropna()
    if len(sub) < MIN_OBS or sub["feature"].std() == 0 or sub["ret"].std() == 0:
        return dict(n=len(sub), slope=np.nan, r2=np.nan, p=np.nan)
    slope, intercept, r, p, se = sstats.linregress(sub["feature"], sub["ret"])
    return dict(n=len(sub), slope=float(slope), r2=float(r ** 2), p=float(p))


def pairwise_scan(series_by_product: dict[str, tuple[pd.Series, pd.Series]],
                   start: str = REPORT_START) -> pd.DataFrame:
    """Directed pair (A's lagged feature -> B's next return) OLS scan, one
    row per ordered pair among all 22 products (22*21 = 462 directed pairs)."""
    rows = []
    products = list(series_by_product)
    for a, b in itertools.permutations(products, 2):
        feat_a, _ = series_by_product[a]
        _, ret_b = series_by_product[b]
        x = feat_a.shift(1)  # lag-1: A's feature as of t-1 predicts B's return at t
        res = _regress(x, ret_b, start)
        if np.isnan(res["p"]):
            continue
        rows.append(dict(
            pair=f"{a}->{b}", a=a, b=b,
            cross_class=CLASS_OF[a] != CLASS_OF[b],
            known_statarb_pair=frozenset({a, b}) in KNOWN_STATARB_PRODUCT_PAIRS,
            **res,
        ))
    return pd.DataFrame(rows).sort_values("p").reset_index(drop=True)


def regime_persistence(series_by_product: dict[str, tuple[pd.Series, pd.Series]],
                        a: str, b: str) -> dict[str, dict]:
    """Re-runs the same lag-1 regression within each of the 4 locked regime
    windows (regimes.py) for one directed pair -- the "consistency across
    sub-periods, not a one-period fluke" leg of the decision rule."""
    feat_a, _ = series_by_product[a]
    _, ret_b = series_by_product[b]
    x = feat_a.shift(1)
    out = {}
    for name, start, end in REGIMES:
        out[name] = _regress(x, ret_b, start, end)
    return out


def _fmt_p(p: float) -> str:
    return "n/a" if np.isnan(p) else f"{p:.4f}"


if __name__ == "__main__":
    series_by_product = build_series_by_product()

    print(f"\nRunning pairwise scan (REPORT_START={REPORT_START}, MIN_OBS={MIN_OBS})...")
    scan = pairwise_scan(series_by_product)
    print(f"Directed pairs tested: {len(scan)}")

    pvals = dict(zip(scan["pair"], scan["p"]))
    survivors = bh_fdr(pvals, q=0.10)
    print(f"\n=== FDR (Benjamini-Hochberg, q=0.10) across {len(pvals)} directed pairs ===")
    print(f"Survivors: {len(survivors)}")

    surv_df = scan[scan["pair"].isin(survivors)].sort_values("p")
    if surv_df.empty:
        print("No pairs survive FDR -- consistent null result, same pattern as Metals/Precious "
              "Momentum-Carry-Value and (separately) their StatArb screens. Recommend parking "
              "Network Momentum for this commodity-only universe, per the decision rule in this "
              "module's docstring.")
    else:
        n_cross = int(surv_df["cross_class"].sum())
        n_known = int(surv_df["known_statarb_pair"].sum())
        print(f"Cross-sub-class survivors: {n_cross} / {len(surv_df)}  "
              f"(paper's own claim is specifically about cross-class edges)")
        print(f"Survivors overlapping an existing StatArb leg: {n_known} / {len(surv_df)}")
        print(f"\n{'Pair':<28}{'n':>6}{'slope':>10}{'R2':>8}{'p':>10}  cross  known_pair")
        for _, r in surv_df.iterrows():
            print(f"{r['pair']:<28}{r['n']:>6}{r['slope']:>10.4f}{r['r2']:>8.4f}{r['p']:>10.5f}  "
                  f"{'Y' if r['cross_class'] else 'N':^5}  {'Y' if r['known_statarb_pair'] else 'N':^9}")

        print("\n=== Regime persistence for FDR survivors (4 locked regimes, regimes.py) ===")
        for _, r in surv_df.iterrows():
            a, b = r["a"], r["b"]
            regimes = regime_persistence(series_by_product, a, b)
            full_sign = np.sign(r["slope"])
            consistent = sum(
                1 for res in regimes.values()
                if not np.isnan(res["slope"]) and np.sign(res["slope"]) == full_sign and res["p"] < 0.10
            )
            print(f"\n{r['pair']}  (full-sample slope={r['slope']:.4f}, p={_fmt_p(r['p'])}, "
                  f"same-sign+p<0.10 in {consistent}/{len(regimes)} regimes)")
            for name, res in regimes.items():
                print(f"    {name:<28}n={res['n']:>5}  slope={res['slope']:>9.4f}  p={_fmt_p(res['p'])}")

        print("\n=== Verdict ===")
        genuinely_new = surv_df[~surv_df["known_statarb_pair"]]
        if genuinely_new.empty:
            print("Every FDR survivor duplicates an existing StatArb leg -- reassuring sanity "
                  "check, not new information. Does not justify the full graph-learning build.")
        else:
            print(f"{len(genuinely_new)} FDR-surviving pair(s) are NOT already covered by the "
                  "existing 8 StatArb legs -- inspect the regime-persistence table above before "
                  "treating any of these as a real finding (per this module's decision rule: "
                  "effect size + cross-regime consistency + economic explainability, not FDR alone).")
