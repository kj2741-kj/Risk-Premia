"""
network_momentum_research/graph_topology_analysis.py
=======================================================
Paper's Section 5.1: characterize the LEARNED GRAPH itself (not backtest
performance) -- edge sparsity, weighted node degree, weighted clustering
coefficient, community structure (Louvain modularity), day-to-day edge
stability (Jaccard index on a thresholded "backbone" graph), and a 2D
embedding comparing the graph's structure in a calm period vs a volatile
one. Lowest priority in this project's Section 5 to-do list (most effort,
least incremental insight, since the specific issue this kind of analysis
would have caught -- the data-blind uniform graph, Bug 1 -- was already
found and fixed via a narrower debugging check earlier in the project) --
scoped down accordingly: two ~2yr illustrative windows, not the full
multi-year backtest history.

Calm/volatile periods reuse this project's own LOCKED macro regimes
(research/regimes.py) rather than inventing new date ranges:
  - Calm: R2_Recovery_Stabilization, restricted to this project's own data
    start (2017-10-09) -> 2019-12-31.
  - Volatile: R3_COVID_Shock, 2020-01-01 -> 2021-12-31 (entirely within the
    backtest range).

Fixed hyperparameters alpha=1, beta=10 (expanding Block 0's own
already-validated selection, whose training window covers both periods)
used throughout -- this is a graph-STRUCTURE characterization, not a
performance backtest, so a single fixed, already-validated (alpha,beta)
pair is appropriate (the paper's own Section 5.1 does the same: characterize
the graph the model actually uses, not re-optimize per sub-analysis).

Full 5-window ensemble (Eq.4-6, DAILY re-estimation, matching every other
"final" computation in this project) -- NOT the single-delta variant from
lookback_sensitivity.py. Kept separate from the main module for the same
reason as every other analysis script here.
"""
from __future__ import annotations

import os

os.environ.setdefault("WALKFORWARD_VARIANT", "expanding")
os.environ.setdefault("SHIFT_N", "0")

import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import pyplot as plt  # noqa: E402

from network_momentum_paper_replication import (  # noqa: E402
    CFG, PRODUCTS, _THIS_DIR, load_panel, rolling_ensemble_graph,
)

ALPHA_FIXED, BETA_FIXED = 1, 10  # expanding Block 0's own selection
CLASS_OF = {p: a for a, cfg in CFG.items() for p in cfg.PRODUCTS}
CLASS_COLOR = {"metals": "#d62728", "precious": "#9467bd", "energy": "#2ca02c", "ngl": "#1f77b4"}

PERIODS = {
    "calm_R2": ("2017-10-09", "2019-12-31"),
    "volatile_R3_COVID": ("2020-01-01", "2021-12-31"),
}

TOP_K_FRAC = 0.20  # "backbone" graph for Jaccard stability -- top 20% of edges by weight
_OUT_DIR = os.path.join(_THIS_DIR, "outputs", "network_momentum_graph_topology_v1")


def _idx(dates: pd.DatetimeIndex, start: str, end: str) -> tuple[int, int]:
    start_idx = int(dates.searchsorted(pd.Timestamp(start)))
    end_idx = int(dates.searchsorted(pd.Timestamp(end), side="right")) - 1
    return start_idx, end_idx


def compute_daily_graphs(U: np.ndarray, start_idx: int, end_idx: int, log=print, label="") -> np.ndarray:
    """Full 5-window-ensemble A_norm for every day in [start_idx,end_idx],
    daily re-estimation -- returns (n_days, N, N)."""
    n_days = end_idx - start_idx + 1
    out = np.empty((n_days, U.shape[1], U.shape[1]))
    warm = None
    for t_idx in range(start_idx, end_idx + 1):
        A_norm, warm = rolling_ensemble_graph(U, t_idx, ALPHA_FIXED, BETA_FIXED, warm)
        out[t_idx - start_idx] = A_norm
        done = t_idx - start_idx + 1
        if done % 100 == 0 or done == n_days:
            log(f"    {label} {done}/{n_days} days")
    return out


def _backbone_edge_set(A: np.ndarray, top_k_frac: float) -> set[tuple[int, int]]:
    n = A.shape[0]
    iu = np.triu_indices(n, 1)
    weights = A[iu]
    k = max(1, int(round(top_k_frac * len(weights))))
    top_idx = np.argsort(weights)[-k:]
    return {(iu[0][i], iu[1][i]) for i in top_idx}


def jaccard_stability(graphs: np.ndarray, top_k_frac: float = TOP_K_FRAC) -> np.ndarray:
    """Day-to-day Jaccard similarity of the top-k-frac backbone edge set."""
    n_days = graphs.shape[0]
    jacc = np.empty(n_days - 1)
    prev_set = _backbone_edge_set(graphs[0], top_k_frac)
    for t in range(1, n_days):
        cur_set = _backbone_edge_set(graphs[t], top_k_frac)
        union = prev_set | cur_set
        jacc[t - 1] = len(prev_set & cur_set) / len(union) if union else np.nan
        prev_set = cur_set
    return jacc


def edge_sparsity(A: np.ndarray, rel_threshold: float = 0.01) -> float:
    n = A.shape[0]
    iu = np.triu_indices(n, 1)
    w = A[iu]
    thresh = rel_threshold * w.max() if w.max() > 0 else 0
    return float((w < thresh).mean())


def weighted_clustering(A: np.ndarray) -> float:
    G = nx.from_numpy_array(A)
    vals = nx.clustering(G, weight="weight")
    return float(np.mean(list(vals.values())))


def period_summary(graphs: np.ndarray, log=print, label="") -> dict:
    n_days = graphs.shape[0]
    sparsity = np.array([edge_sparsity(graphs[t]) for t in range(n_days)])
    degree = np.array([graphs[t].sum(axis=1).mean() for t in range(n_days)])
    clustering = np.array([weighted_clustering(graphs[t]) for t in range(n_days)])
    jacc = jaccard_stability(graphs)

    A_avg = graphs.mean(axis=0)
    G_avg = nx.from_numpy_array(A_avg)
    communities = nx.community.louvain_communities(G_avg, weight="weight", seed=0)
    modularity = nx.community.modularity(G_avg, communities, weight="weight")
    node_to_comm = {}
    for ci, comm in enumerate(communities):
        for node in comm:
            node_to_comm[node] = ci
    n = A_avg.shape[0]
    iu = np.triu_indices(n, 1)
    within = sum(A_avg[i, j] for i, j in zip(*iu) if node_to_comm[i] == node_to_comm[j])
    total = A_avg[iu].sum()
    community_ratio = float(within / total) if total > 0 else np.nan

    log(f"  {label}: n_days={n_days}  sparsity={sparsity.mean():.3f}  degree={degree.mean():.3f}  "
        f"clustering={clustering.mean():.3f}  jaccard={np.nanmean(jacc):.3f}  "
        f"n_communities={len(communities)}  modularity={modularity:.3f}  community_ratio={community_ratio:.3f}")

    return dict(
        sparsity_mean=float(sparsity.mean()), degree_mean=float(degree.mean()),
        clustering_mean=float(clustering.mean()), jaccard_mean=float(np.nanmean(jacc)),
        jaccard_std=float(np.nanstd(jacc)), n_communities=len(communities), modularity=float(modularity),
        community_ratio=community_ratio, A_avg=A_avg, communities=communities,
    )


def plot_embedding(A_avg: np.ndarray, products: list[str], title: str, out_path: str) -> None:
    G = nx.from_numpy_array(A_avg)
    pos = nx.spring_layout(G, weight="weight", seed=0, k=1.2)
    fig, ax = plt.subplots(figsize=(7, 7))
    colors = [CLASS_COLOR[CLASS_OF[p]] for p in products]
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.15, width=[A_avg[u, v] * 8 for u, v in G.edges()])
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=colors, node_size=350)
    nx.draw_networkx_labels(G, pos, {i: p for i, p in enumerate(products)}, ax=ax, font_size=8)
    ax.set_title(title)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


def build_html_report(summaries: dict, img_paths: dict, out_path: str) -> None:
    import base64
    parts = ['<html><head><meta charset="utf-8"><title>Network Momentum -- Graph Topology Analysis</title>',
             '<style>body{font-family:sans-serif;margin:24px}table{border-collapse:collapse}',
             'th,td{border:1px solid #ccc;padding:6px 10px;font-size:13px}th{background:#f0f0f0}',
             'img{max-width:45%;margin:8px}</style></head><body>']
    parts.append('<h1>Graph Topology Analysis: Calm vs Volatile Period</h1>')
    parts.append(f'<p>Fixed hyperparameters alpha={ALPHA_FIXED} beta={BETA_FIXED} (expanding Block 0\'s own '
                 f'selection). Calm = R2_Recovery_Stabilization ({PERIODS["calm_R2"][0]} to '
                 f'{PERIODS["calm_R2"][1]}). Volatile = R3_COVID_Shock ({PERIODS["volatile_R3_COVID"][0]} to '
                 f'{PERIODS["volatile_R3_COVID"][1]}).</p>')

    parts.append('<h2>Summary metrics</h2><table><tr><th>Metric</th>')
    for label in summaries:
        parts.append(f'<th>{label}</th>')
    parts.append('</tr>')
    metric_keys = ["sparsity_mean", "degree_mean", "clustering_mean", "jaccard_mean", "jaccard_std",
                   "n_communities", "modularity", "community_ratio"]
    for key in metric_keys:
        parts.append(f'<tr><td>{key}</td>' + "".join(f'<td>{summaries[l][key]:.4f}</td>' for l in summaries) + '</tr>')
    parts.append('</table>')

    parts.append('<h2>Graph layout (period-averaged, node size fixed, edge width = weight, '
                 'color = sub-asset-class: red=metals, purple=precious, green=energy, blue=ngl)</h2>')
    for label, path in img_paths.items():
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        parts.append(f'<div style="display:inline-block"><h3>{label}</h3><img src="data:image/png;base64,{b64}"></div>')

    parts.append('</body></html>')
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


if __name__ == "__main__":
    os.makedirs(_OUT_DIR, exist_ok=True)
    print("Loading panel...")
    panel = load_panel()
    dates = panel["dates"]
    U = panel["U"]

    summaries = {}
    img_paths = {}
    for label, (start, end) in PERIODS.items():
        print(f"\n########## {label} ({start} -> {end}) ##########")
        ckpt_path = os.path.join(_OUT_DIR, f"{label}_graphs.npy")
        if os.path.exists(ckpt_path):
            graphs = np.load(ckpt_path)
            print(f"  loaded {graphs.shape[0]} daily graphs from checkpoint")
        else:
            start_idx, end_idx = _idx(dates, start, end)
            graphs = compute_daily_graphs(U, start_idx, end_idx, label=label)
            np.save(ckpt_path, graphs)
            print(f"  saved {graphs.shape[0]} daily graphs to {ckpt_path}")

        summary = period_summary(graphs, label=label)
        summaries[label] = summary

        img_path = os.path.join(_OUT_DIR, f"{label}_layout.png")
        plot_embedding(summary["A_avg"], PRODUCTS, f"{label} (period-averaged graph)", img_path)
        img_paths[label] = img_path

    html_path = os.path.join(_THIS_DIR, "outputs", "graph_topology_report.html")
    build_html_report(summaries, img_paths, html_path)
    print(f"\nSaved: {html_path}")

    summary_df = pd.DataFrame({l: {k: v for k, v in s.items() if k not in ("A_avg", "communities")}
                               for l, s in summaries.items()}).T
    summary_df.to_csv(os.path.join(_THIS_DIR, "outputs", "graph_topology_summary.csv"))
    print(f"Saved: {os.path.join(_THIS_DIR, 'outputs', 'graph_topology_summary.csv')}")
