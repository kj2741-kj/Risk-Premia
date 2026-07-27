# Network Momentum Research

Standalone replication and extension of Pu/Roberts/Dong/Zohren, "Network Momentum across Asset Classes" (2023), on a 22-product commodity-only universe (Metals, Precious Metals, Energy, NGL — Bloomberg data). Kept on its own branch (`network-momentum-research`, forked from `main`) and its own top-level folder, separate from the main Risk Premia project's other strategies, since this is being developed as an independent, potentially publishable piece of research rather than another dashboard sleeve.

## Files
- `network_momentum_paper_replication.py` — main walk-forward driver (grid search, daily graph re-estimation, transaction costs, all 3 walk-forward variants x 2 execution-delay settings)
- `kalofolias_graph_learning.py` — the graph-learning solver (FBF primal-dual splitting, ported from Kalofolias's own reference MATLAB code)
- `network_momentum_features.py` — the paper's 8 momentum features (Section 2.2)
- `network_momentum_pilot.py` — earlier, concluded pairwise pilot study (superseded by the full replication; kept for its own historical reasoning)
- `docs/Network momentum.pdf` — the reference paper
- `outputs/` — checkpoints, cached graph computations, result CSVs, run logs (gitignored, not tracked)

## Shared dependencies (deliberately NOT duplicated here)
This project still depends on the wider Risk Premia repo's shared infrastructure, imported via `sys.path` insertion at the top of each script:
- `../research/configs/{metals,precious,energy,ngl}.py` — per-asset-class data loading (also used by the Momentum/Carry/Value/StatArb sleeves)
- `../research/ratio_continuous.py` — roll-adjusted (multiplicative/ratio) continuous futures price construction

These stay in `research/` rather than being copied here, since other parts of the wider project depend on them too — duplicating them would create two sources of truth for the same roll-adjustment logic.

## Running
```
cd network_momentum_research
python network_momentum_paper_replication.py --block N          # run one block of the default (expanding, shift0) variant
WALKFORWARD_VARIANT=rolling SHIFT_N=1 python network_momentum_paper_replication.py --block N
python network_momentum_paper_replication.py                     # consolidate all blocks of a variant/shift from existing checkpoints (no recompute)
```
`WALKFORWARD_VARIANT` ∈ {expanding, rolling, annual}, `SHIFT_N` ∈ {0, 1}.

See `../.claude` memory (`project_network_momentum_replication`) for the full methodology writeup, bug-fix history, results tables, and current to-do list.
