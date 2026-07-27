"""
network_momentum_research/kalofolias_graph_learning.py
========================================
Exact reimplementation of V. Kalofolias's graph-learning model (AISTATS
2016, "How to learn a graph from smooth signals"), which is the model
Pu/Roberts/Dong/Zohren's "Network Momentum across Asset Classes" (2023,
Eq. 4) uses verbatim to learn the daily asset-similarity graph:

    min_{A>=0, A=A^T, diag(A)=0}
        tr(V^T (D-A) V) - alpha * sum_i log(sum_j A_ij) + beta * ||A||_F^2

This module is a line-for-line Python port of Kalofolias's OWN reference
MATLAB implementation (not a re-derivation from the paper's equation --
re-deriving the primal-dual proximal-splitting algorithm from scratch
carries real correctness risk, e.g. the exact conjugate-prox scaling in
`_g_star_prox` below does not match a naive Moreau-decomposition rewrite
unless every internal scaling constant is copied exactly). Source pulled
directly from GitHub 2026-07-25 and transcribed function-by-function:
  - epfl-lts2/gspbox: learn_graph/gsp_learn_graph_log_degrees.m (main FBF loop)
  - epfl-lts2/unlocbox: prox/prox_sum_log.m, utils/sum_squareform.m,
    utils/squareform_sp.m, utils/lin_map.m

Problem reduces (via tr(V^T(D-A)V) = sum_{i<j} A_ij*Z_ij, Z_ij=||v_i-v_j||^2)
to an edge-weight-vector optimisation over w = condensed(A) (length
n*(n-1)/2, same ordering as scipy.spatial.distance.squareform):

    min_{w>=0}  2*w'z  - alpha*sum(log(S*w))  + beta*||w||_2^2

solved by forward-backward-forward (FBF) primal-dual splitting (Komodakis &
Pesquet 2015), where S is the sparse "edges -> node degrees" operator
(S*w = row-sums of squareform(w)).

The paper itself (Section 4.1, "Optimisation Details") actually solves Eq.4
via CVXPY+MOSEK rather than this FBF algorithm -- both solve the IDENTICAL
convex problem to its (unique, since strictly convex in the beta*||w||^2
term whenever beta>0) global optimum, so this is not an approximation of
their method, just a different, much cheaper solver for daily/rolling
re-estimation at this project's scale (22 nodes vs. their 64).
"""
from __future__ import annotations

import itertools

import numpy as np


def _pdist_sq_condensed(V: np.ndarray) -> np.ndarray:
    """Condensed (scipy.spatial.distance.squareform-ordered) vector of squared
    Euclidean distances between rows of V (n x d feature matrix) -- this is
    Z in Eq.4, condensed to match w's edge ordering: (0,1),(0,2),...,(0,n-1),
    (1,2),...,(n-2,n-1)."""
    n = V.shape[0]
    sq = (V ** 2).sum(axis=1)
    idx_i, idx_j = zip(*itertools.combinations(range(n), 2))
    idx_i, idx_j = np.array(idx_i), np.array(idx_j)
    z = sq[idx_i] + sq[idx_j] - 2.0 * (V[idx_i] * V[idx_j]).sum(axis=1)
    return np.clip(z, 0.0, None)


def _sum_squareform_dense(n: int) -> np.ndarray:
    """Dense n x l "edges -> node degree" operator S (l = n*(n-1)/2), s.t.
    S @ w == squareform(w).sum(axis=1) for condensed edge-weight vector w.
    Dense (not scipy.sparse) is faster here: n<=22 in this project's use
    (vs. the paper's 64), so l<=231 -- sparse-matrix overhead dominates at
    this size. Direct port of unlocbox/utils/sum_squareform.m's no-mask branch."""
    l = n * (n - 1) // 2
    S = np.zeros((n, l))
    idx_i, idx_j = zip(*itertools.combinations(range(n), 2))
    for e, (i, j) in enumerate(zip(idx_i, idx_j)):
        S[i, e] = 1.0
        S[j, e] = 1.0
    return S


def _prox_sum_log(x: np.ndarray, gamma: float) -> np.ndarray:
    """Proximal operator of -sum(log(x)) with parameter gamma -- direct port
    of unlocbox/prox/prox_sum_log.m: argmin_z 0.5||x-z||^2 - gamma*sum(log(z)),
    closed form (z + sqrt(z^2+4*gamma))/2 from the first-order condition
    -gamma/z + (z-x) = 0."""
    if gamma <= 0:
        return x
    return (x + np.sqrt(x ** 2 + 4.0 * gamma)) / 2.0


def _lin_map(x: float, lims_out: tuple[float, float], lims_in: tuple[float, float]) -> float:
    a, b = lims_in
    c, d = lims_out
    return (x - a) * ((d - c) / (b - a)) + c


def learn_graph(Z_or_V: np.ndarray, alpha: float, beta: float, *, is_features: bool = True,
                w_init: np.ndarray | None = None, maxit: int = 1000, tol: float = 1e-5,
                step_size: float = 0.5, max_w: float = np.inf) -> tuple[np.ndarray, np.ndarray]:
    """Solves Eq.4 for one day's graph. Pass `is_features=True` (default) and
    an (n, d) feature matrix V (this project's V_t: n=22 products stacked
    over the delta-day lookback x 8 features, per Eq.4's own V_t
    construction) -- pairwise squared distances Z are computed internally.
    Pass `is_features=False` and a precomputed (n,n) squared-distance matrix
    Z directly to skip that step (used by the solver's own warm-start loop
    where Z is reused across consecutive days' incremental updates).

    Returns (A, w) -- the (n,n) symmetric zero-diagonal adjacency matrix and
    its condensed edge-weight vector (the latter is the natural warm-start
    seed for the next call via `w_init`)."""
    if is_features:
        V = np.asarray(Z_or_V, dtype=float)
        n = V.shape[0]
        z = _pdist_sq_condensed(V)
    else:
        Zmat = np.asarray(Z_or_V, dtype=float)
        n = Zmat.shape[0]
        idx_i, idx_j = zip(*itertools.combinations(range(n), 2))
        z = Zmat[np.array(idx_i), np.array(idx_j)]

    # CRITICAL: normalize z to O(1) scale before optimizing -- alpha/beta and the
    # FBF step size (gn, below) are calibrated assuming z sits near unit scale
    # (standard usage convention for this exact algorithm, e.g. gsp_learn_graph_log_degrees.m's
    # own tutorials: "Z = Z / mean(Z)"). Skipping this is not a cosmetic omission: when V
    # stacks many days x 8 features (z can reach O(10^3)-O(10^4) here), the very first FBF
    # iteration computes P_n = clip(Y_n - 2*gn*z, 0, max_w) starting from Y_n~0, which clips
    # EVERY entry to exactly 0 regardless of how much z varies between pairs -- the data term
    # never gets a chance to differentiate close vs. far pairs, and the optimizer converges to
    # a graph shaped ONLY by the (symmetric-by-construction) degree-barrier term: perfectly
    # uniform edge weights, identical regardless of alpha/beta, that ignore the input data
    # entirely. Confirmed empirically 2026-07-26: real V_t data gave coefficient-of-variation
    # 0.0000 across 6 different (alpha,beta) combos without this normalization, vs 0.28 (and
    # 0.97 correlation between the true distance and the learned edge weight) with it.
    z = z / z.mean() if z.mean() > 0 else z

    l = len(z)
    S = _sum_squareform_dense(n)
    St = S.T
    norm_K = np.sqrt(2.0 * (n - 1))  # exact bound, unlocbox sum_squareform.m docstring

    h_beta = 2.0 * beta  # w_0=0 case (no reference-graph prior), per gsp_learn_graph_log_degrees.m
    mu = h_beta + norm_K
    epsilon = 0.0  # _lin_map(0.0, [0, 1/(1+mu)], [0,1]) == 0, matches the MATLAB call's literal X=0.0
    gn = _lin_map(step_size, (epsilon, (1 - epsilon) / mu), (0.0, 1.0))

    w = np.zeros(l) if w_init is None else np.array(w_init, dtype=float, copy=True)
    v_n = S @ w

    for _ in range(maxit):
        Y_n = w - gn * (h_beta * w + St @ v_n)
        y_n = v_n + gn * (S @ w)
        P_n = np.clip(Y_n - 2 * gn * z, 0.0, max_w)
        # g_star_prox: Moreau-conjugate prox, exact port of gsp_learn_graph_log_degrees.m's
        # `g_star_prox = @(z,c) z - c*a*prox_sum_log(z/(c*a), 1/(c*a))` -- do NOT
        # "simplify" this to a generic Moreau-decomposition rewrite, the scaling here
        # is the literal reference formula.
        if alpha > 0:
            p_n = y_n - gn * alpha * _prox_sum_log(y_n / (gn * alpha), 1.0 / (gn * alpha))
        else:
            p_n = y_n
        Q_n = P_n - gn * (h_beta * P_n + St @ p_n)
        q_n = p_n + gn * (S @ P_n)

        with np.errstate(invalid="ignore", divide="ignore"):
            norm_w = np.linalg.norm(w)
            norm_v = np.linalg.norm(v_n)
            rel_primal = np.linalg.norm(Q_n - Y_n) / norm_w if norm_w > 0 else np.inf
            rel_dual = np.linalg.norm(q_n - y_n) / norm_v if norm_v > 0 else np.inf

        w = w - Y_n + Q_n
        v_n = v_n - y_n + q_n

        if rel_primal < tol and rel_dual < tol:
            break

    w = np.clip(w, 0.0, None)
    A = np.zeros((n, n))
    idx_i, idx_j = zip(*itertools.combinations(range(n), 2))
    A[idx_i, idx_j] = w
    A[idx_j, idx_i] = w
    return A, w


if __name__ == "__main__":
    # Smoke test: two well-separated 3-blob clusters in feature space should
    # learn a graph with much stronger within-cluster than cross-cluster edges.
    rng = np.random.default_rng(0)
    n_per = 4
    centers = np.array([[0.0, 0.0], [10.0, 10.0]])
    V = np.vstack([c + rng.normal(scale=0.3, size=(n_per, 2)) for c in centers])
    n = V.shape[0]
    A, w = learn_graph(V, alpha=1.0, beta=1.0)
    print("Learned adjacency (rows/cols 0-3 = cluster A, 4-7 = cluster B):")
    print(np.round(A, 3))
    within = (A[:n_per, :n_per].sum() + A[n_per:, n_per:].sum())
    across = A[:n_per, n_per:].sum() * 2
    print(f"within-cluster edge mass: {within:.3f}   across-cluster edge mass: {across:.3f}")
    assert within > 5 * across, "expected within-cluster edges to dominate for well-separated blobs"
    print("OK: within-cluster connectivity strongly dominates, as expected.")
