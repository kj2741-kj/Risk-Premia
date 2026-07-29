"""
network_momentum_research/diversification_analysis.py
========================================================
Answers a question the Sharpe-only tables in this project never directly
addressed: HOW does combining all 22 products actually help, beyond a
better Sharpe number? Two angles:

1. Risk-side comparison (vol, max drawdown, Sortino, Calmar) for the full-22
   portfolio vs each of the 4 sub-class-only portfolios (reuses existing
   checkpoints -- no new compute, table1_metrics was already tracking these,
   just never displayed beyond Sharpe).
2. The MECHANISM: pairwise correlation structure of the 22 products' daily
   returns (full period, backtest period, and each walk-forward block's own
   fit/validate/test sub-periods), split into within-sub-class vs
   cross-sub-class average correlation -- and a textbook diversification-
   ratio check (portfolio vol / individual vol ~= sqrt(1/N + (N-1)/N*avg_corr),
   valid here because every individual asset is already vol-targeted to the
   SAME sigma_tgt before combining, Eq.9) comparing the THEORETICAL
   prediction from the correlation matrix against the REALIZED long-only
   vol from the actual backtest -- a sanity check that the diversification
   story is quantitatively consistent, not just qualitatively plausible.

Kept separate from the main pipeline (same reasoning as every other
analysis script in this folder): pure reporting on already-computed
checkpoints + the raw return panel, cannot affect any validated backtest.
"""
from __future__ import annotations

import os

os.environ.setdefault("WALKFORWARD_VARIANT", "expanding")
os.environ.setdefault("SHIFT_N", "0")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from network_momentum_paper_replication import (  # noqa: E402
    BLOCK_SCHEMES, CFG, PRODUCTS, SIGMA_TGT, _THIS_DIR, load_panel, table1_metrics,
)

EXPANDING_BLOCKS = BLOCK_SCHEMES["expanding"]
CLASS_OF = {p: a for a, cfg in CFG.items() for p in cfg.PRODUCTS}
_FULL_CKPT_DIR = os.path.join(_THIS_DIR, "outputs", "network_momentum_checkpoints_v3_expanding_shift0")
_SUBCLASS_DIR = os.path.join(_THIS_DIR, "outputs", "network_momentum_subclass_ablation_v1")


def _idx(dates: pd.DatetimeIndex, start: str, end: str) -> tuple[int, int]:
    start_idx = int(dates.searchsorted(pd.Timestamp(start)))
    end_idx = int(dates.searchsorted(pd.Timestamp(end), side="right")) - 1
    return start_idx, end_idx


# ═══════════════════════════════════════════════════════════════
# 1. Risk-side comparison (vol / mdd / sortino / calmar), reusing existing checkpoints
# ═══════════════════════════════════════════════════════════════

def load_universe_returns(universe: str) -> dict[str, pd.Series]:
    ckpt_dir = _FULL_CKPT_DIR if universe == "full-22" else os.path.join(_SUBCLASS_DIR, universe)
    blocks = [pd.read_pickle(os.path.join(ckpt_dir, f"block_{i}.pkl")) for i in range(3)]
    return {name: pd.concat([b[name] for b in blocks]).sort_index()
            for name in ("gmom", "linreg", "macd", "longonly")}


def build_risk_table() -> pd.DataFrame:
    rows = []
    for universe in ("full-22", "metals", "precious", "energy", "ngl"):
        returns = load_universe_returns(universe)
        for strat, series in returns.items():
            m = table1_metrics(series)
            rows.append(dict(universe=universe, strategy=strat, **m))
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════
# 2. Correlation structure
# ═══════════════════════════════════════════════════════════════

def corr_matrix(daily_ret: pd.DataFrame, start, end) -> pd.DataFrame:
    return daily_ret.loc[start:end].corr()


def avg_corr_breakdown(corr_df: pd.DataFrame) -> dict:
    n = len(corr_df)
    vals = corr_df.to_numpy()
    iu = np.triu_indices(n, 1)
    within, cross = [], []
    products = list(corr_df.index)
    for a, b in zip(*iu):
        c = vals[a, b]
        if CLASS_OF[products[a]] == CLASS_OF[products[b]]:
            within.append(c)
        else:
            cross.append(c)
    return dict(avg_all=float(vals[iu].mean()), avg_within_class=float(np.mean(within)) if within else np.nan,
                avg_cross_class=float(np.mean(cross)) if cross else np.nan, n_pairs=len(iu[0]))


def within_class_avg_corr(corr_df: pd.DataFrame, subclass: str) -> float:
    members = [p for p in corr_df.index if CLASS_OF[p] == subclass]
    sub = corr_df.loc[members, members]
    n = len(members)
    iu = np.triu_indices(n, 1)
    return float(sub.to_numpy()[iu].mean())


def theoretical_vol(n: int, avg_corr: float, sigma_tgt: float = SIGMA_TGT) -> float:
    """Portfolio vol / individual (already vol-targeted) asset vol ~=
    sqrt(1/N + (N-1)/N * avg_corr), for an equal-weighted combination of N
    assets each with variance sigma_tgt^2 and average pairwise correlation
    avg_corr -- exactly the setup Eq.9's vol-targeted-then-averaged
    portfolio construction produces (ignoring signal/timing effects, i.e.
    treating each asset's contribution as if fully invested, x=1)."""
    return sigma_tgt * np.sqrt(max(1.0 / n + (n - 1) / n * avg_corr, 0.0))


def build_period_list(dates: pd.DatetimeIndex) -> list[tuple[str, pd.Timestamp, pd.Timestamp]]:
    periods = [
        ("full_common_panel", dates[0], dates[-1]),
        ("full_backtest_2017-10-09_to_end", pd.Timestamp("2017-10-09"), dates[-1]),
    ]
    for i, (tr_start, tr_end, te_start, te_end) in enumerate(EXPANDING_BLOCKS):
        train_start_idx, train_end_idx = _idx(dates, tr_start, tr_end)
        n_train = train_end_idx - train_start_idx + 1
        n_val = max(round(0.10 * n_train), 60)
        val_start_idx = train_end_idx - n_val + 1
        fit_end_idx = val_start_idx - 1
        test_start_idx, test_end_idx = _idx(dates, te_start, te_end)
        periods.append((f"block{i}_fit", dates[train_start_idx], dates[fit_end_idx]))
        periods.append((f"block{i}_validate", dates[val_start_idx], dates[train_end_idx]))
        periods.append((f"block{i}_test", dates[test_start_idx], dates[test_end_idx]))
    return periods


def build_correlation_report(daily_ret: pd.DataFrame, dates: pd.DatetimeIndex) -> tuple[pd.DataFrame, dict]:
    periods = build_period_list(dates)
    rows = []
    matrices = {}
    for label, start, end in periods:
        cdf = corr_matrix(daily_ret, start, end)
        matrices[label] = cdf
        bd = avg_corr_breakdown(cdf)
        row = dict(period=label, start=str(start.date()), end=str(end.date()), n_days=int((daily_ret.loc[start:end]).shape[0]),
                   **bd)
        for sc in CFG:
            row[f"avg_within_{sc}"] = within_class_avg_corr(cdf, sc)
        rows.append(row)
    return pd.DataFrame(rows), matrices


# ═══════════════════════════════════════════════════════════════
# HTML report (plain local file, no CDN deps -- inline CSS-colored table cells)
# ═══════════════════════════════════════════════════════════════

def _corr_color(v: float) -> str:
    # blue for negative, white for 0, red for positive -- clamp [-1,1]
    v = max(-1.0, min(1.0, v))
    if v >= 0:
        r, g, b = 255, int(255 * (1 - v)), int(255 * (1 - v))
    else:
        r, g, b = int(255 * (1 + v)), int(255 * (1 + v)), 255
    return f"rgb({r},{g},{b})"


def _render_heatmap(corr_df: pd.DataFrame, title: str) -> str:
    products = list(corr_df.index)
    html = [f'<h3>{title}</h3>', '<div style="overflow-x:auto"><table style="border-collapse:collapse;font-size:10px">']
    html.append('<tr><td></td>' + "".join(f'<td style="padding:2px 4px;font-weight:600;writing-mode:vertical-lr">{p}</td>' for p in products) + '</tr>')
    for p in products:
        cells = []
        for q in products:
            v = corr_df.loc[p, q]
            cells.append(f'<td style="background:{_corr_color(v)};padding:2px 4px;text-align:center" title="{p}-{q}: {v:.2f}">{v:.2f}</td>')
        html.append(f'<tr><td style="font-weight:600;padding:2px 6px">{p}</td>{"".join(cells)}</tr>')
    html.append('</table></div>')
    return "\n".join(html)


def build_html_report(risk_df: pd.DataFrame, corr_summary: pd.DataFrame, matrices: dict, out_path: str) -> None:
    parts = ['<html><head><meta charset="utf-8"><title>Network Momentum -- Diversification Analysis</title>',
             '<style>body{font-family:sans-serif;margin:24px}table{border-collapse:collapse}',
             'th,td{border:1px solid #ccc;padding:4px 8px;font-size:13px}th{background:#f0f0f0}</style></head><body>']
    parts.append('<h1>Diversification Analysis: Full-22 vs Sub-Class Portfolios</h1>')

    parts.append('<h2>1. Risk metrics (long-only, isolates pure diversification effect)</h2>')
    parts.append('<p><b>Period: aggregated OOS TEST windows only, all 3 expanding blocks concatenated '
                 '(2021-01-04 to 2026-06-30, ~5.5yr).</b> Not the full 2012-2026 panel, and not the '
                 'fit/validate portions (no return series exists for those -- they only fit the regression '
                 '/ select hyperparameters, never traded).</p>')
    lo = risk_df[risk_df["strategy"] == "longonly"][["universe", "ret", "vol", "sharpe", "mdd", "sortino", "calmar"]]
    parts.append(lo.to_html(index=False, float_format=lambda x: f"{x:.3f}"))

    parts.append('<h2>2. Risk metrics, all 4 strategies, all universes</h2>')
    parts.append(risk_df.to_html(index=False, float_format=lambda x: f"{x:.3f}"))

    parts.append('<h2>3. Correlation summary by period</h2>')
    parts.append(corr_summary.to_html(index=False, float_format=lambda x: f"{x:.3f}"))

    parts.append('<h2>4. Correlation heatmaps (all periods: full panel, full backtest, '
                 'and every block\'s fit/validate/test)</h2>')
    for label, cdf in matrices.items():
        parts.append(_render_heatmap(cdf, label))

    parts.append('</body></html>')
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


if __name__ == "__main__":
    print("Loading panel...")
    panel = load_panel()
    dates = panel["dates"]
    daily_ret = panel["daily_ret"]

    print("Building risk table (vol/mdd/sortino/calmar) from existing checkpoints...")
    risk_df = build_risk_table()
    print(risk_df[risk_df["strategy"] == "longonly"][["universe", "ret", "vol", "sharpe", "mdd", "sortino", "calmar"]]
          .to_string(index=False))

    print("\nBuilding correlation report (full period, backtest period, per-block fit/validate/test)...")
    corr_summary, matrices = build_correlation_report(daily_ret, dates)
    print(corr_summary[["period", "start", "end", "n_days", "avg_all", "avg_within_class", "avg_cross_class"]]
          .to_string(index=False))

    print("\nTheoretical vs realized long-only vol check:")
    full_backtest_corr = corr_summary[corr_summary["period"] == "full_backtest_2017-10-09_to_end"].iloc[0]
    theo_full = theoretical_vol(22, full_backtest_corr["avg_all"])
    realized_full = risk_df[(risk_df["universe"] == "full-22") & (risk_df["strategy"] == "longonly")]["vol"].iloc[0]
    print(f"  full-22: theoretical={theo_full:.3f}  realized={realized_full:.3f}")
    for sc, n in [("metals", 4), ("precious", 5), ("energy", 7), ("ngl", 6)]:
        theo = theoretical_vol(n, full_backtest_corr[f"avg_within_{sc}"])
        realized = risk_df[(risk_df["universe"] == sc) & (risk_df["strategy"] == "longonly")]["vol"].iloc[0]
        print(f"  {sc}: theoretical={theo:.3f}  realized={realized:.3f}")

    out_dir = os.path.join(_THIS_DIR, "outputs")
    risk_df.to_csv(os.path.join(out_dir, "diversification_risk_table.csv"), index=False)
    corr_summary.to_csv(os.path.join(out_dir, "diversification_correlation_summary.csv"), index=False)
    matrix_dir = os.path.join(out_dir, "diversification_correlation_matrices")
    os.makedirs(matrix_dir, exist_ok=True)
    for label, cdf in matrices.items():
        cdf.to_csv(os.path.join(matrix_dir, f"{label}.csv"))
    html_path = os.path.join(out_dir, "diversification_report.html")
    build_html_report(risk_df, corr_summary, matrices, html_path)
    print(f"\nSaved: {html_path}")
    print(f"Saved: {os.path.join(out_dir, 'diversification_risk_table.csv')}")
    print(f"Saved: {os.path.join(out_dir, 'diversification_correlation_summary.csv')}")
    print(f"Saved {len(matrices)} individual correlation matrix CSVs to: {matrix_dir}")
