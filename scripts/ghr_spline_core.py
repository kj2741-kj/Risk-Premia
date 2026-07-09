"""
ghr_spline_core.py
====================
Shared engine behind the GHR (Gorton, Hayashi & Rouwenhorst 2013) cubic-spline
basis-on-normalized-inventory regression (paper Section 4.1, footnote 15).
Commodity-specific scripts (ghr_copper_inventory_spline.py,
ghr_wti_inventory_spline.py, ...) only need to supply:
  - a daily basis Series (Date-indexed, annualized % p.a.)
  - a daily inventory Series (Date-indexed, physical units)
and call `run_spline_analysis(...)` here.

Normalized inventory (paper Section 3.2):
    x_t = I_t / I*_t,  I*_t = trailing 52-week average of I_{t-1..t-52}
  Frequency is WEEKLY throughout (not monthly as in the original paper) so
  the same pipeline works for both LME copper (daily source, resampled) and
  EIA WTI crude stocks (natively weekly).

Regression (J=1 knot at x=1):
    basis = sum(month dummies) + b1*x + b2*x^2 + b3*x^3
            + b4*(x-1)^3 * 1{x>1} + error
  Fit by OLS; Newey-West HAC standard errors (bandwidth = 52 weeks, i.e. the
  paper's 12-month bandwidth rescaled to weekly data).
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go

TRAILING_WEEKS = 52          # I* = trailing 52-week average (paper: 12 months)
NW_BANDWIDTH = 52            # Newey-West lag window (paper: 12-month bandwidth)
MONTH_COLS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Shared axis ranges so plots across commodities are visually comparable on
# the same scale (see ghr_copper_inventory_spline.py / ghr_wti_inventory_
# spline.py docstrings). Chosen to cover copper's full observed range --
# copper is the widest of the two so far -- and clip out the handful of
# crisis-era basis blowouts (2008-09 GFC storage crunch, 2020-04 COVID
# negative-WTI event) that would otherwise stretch the y-axis and squash
# everything else. Those points remain in the regression/CSV; only the
# plotted VIEW is clipped. Pass x_range=None / y_range=None to autorange.
DEFAULT_X_RANGE = (0.3, 2.7)
DEFAULT_Y_RANGE = (-30.0, 30.0)


# ─────────────────────────────────────────────────────────────────────────────
# Contract day-count helper (shared by any F1/F2-style basis loader)
# ─────────────────────────────────────────────────────────────────────────────

def load_ltd_calendar(calendar_xlsx: str, calendar_sheet: str) -> np.ndarray:
    """Sorted array of datetime64 last-tradeable-dates for a futures contract chain."""
    cal = pd.read_excel(calendar_xlsx, sheet_name=calendar_sheet)
    ltd = pd.to_datetime(cal["LAST_TRADEABLE_DT"]).dropna().sort_values()
    return ltd.values.astype("datetime64[ns]")


def compute_days_to_maturity(dates: pd.DatetimeIndex, ltd_array: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    D1 = days from t to the nearest LTD >= t (F1 contract's last trading day).
    D2 = days from t to the next LTD after that (F2 contract's last trading day).
    """
    dates64 = dates.values.astype("datetime64[ns]")
    idx = np.searchsorted(ltd_array, dates64, side="left")
    idx1 = np.clip(idx, 0, len(ltd_array) - 1)
    idx2 = np.clip(idx + 1, 0, len(ltd_array) - 1)
    d1 = (ltd_array[idx1] - dates64).astype("timedelta64[D]").astype(float)
    d2 = (ltd_array[idx2] - dates64).astype("timedelta64[D]").astype(float)
    return d1, d2


def f1f2_basis_from_curve(f1: pd.Series, f2: pd.Series, calendar_xlsx: str, calendar_sheet: str) -> pd.Series:
    """Eq. 15 of the paper: (F1/F2 - 1) * 365/(D2-D1), annualized %, using actual
    contract day-counts from the expiry calendar."""
    df = pd.concat([f1.rename("F1_raw"), f2.rename("F2_raw")], axis=1).dropna()
    ltd_array = load_ltd_calendar(calendar_xlsx, calendar_sheet)
    d1, d2 = compute_days_to_maturity(df.index, ltd_array)
    return (df["F1_raw"] / df["F2_raw"] - 1.0) * 365.0 / (d2 - d1) * 100.0


# ─────────────────────────────────────────────────────────────────────────────
# Weekly resampling + normalized inventory
# ─────────────────────────────────────────────────────────────────────────────

def to_weekly_last(s: pd.Series) -> pd.Series:
    return s.resample("W-FRI").last().dropna()


def normalized_inventory(weekly_stock: pd.Series, trailing_weeks: int = TRAILING_WEEKS) -> pd.DataFrame:
    i_star = weekly_stock.rolling(trailing_weeks, min_periods=trailing_weeks).mean().shift(1)
    x = weekly_stock / i_star
    return pd.DataFrame({"stock": weekly_stock, "I_star": i_star, "x": x})


# ─────────────────────────────────────────────────────────────────────────────
# Design matrix + OLS + Newey-West HAC
# ─────────────────────────────────────────────────────────────────────────────

def build_design_matrix(dates: pd.DatetimeIndex, x: np.ndarray) -> pd.DataFrame:
    """
    h(x) = b1*u + b2*u^2 + b3*u^3 + b4*u^3*1{u>0}, u = x - 1.

    Centering the cubic terms at the knot (u = x-1, so u=0 at x=1) is
    mathematically equivalent to the paper's b1*x + b2*x^2 + b3*x^3 basis --
    {1, x, x^2, x^3} and {1, (x-1), (x-1)^2, (x-1)^3} span the same space --
    but is numerically far better conditioned. Commodities whose normalized
    inventory barely moves around 1 (e.g. WTI, std ~0.06) make x, x^2, x^3
    nearly collinear with the constant already supplied by the 12 monthly
    dummies; centering removes that near-singularity (confirmed: condition
    number of Z'Z for WTI drops from ~4.6e9 uncentered to a well-behaved
    range centered).
    """
    z = pd.DataFrame(0.0, index=dates, columns=MONTH_COLS)
    for i, m in enumerate(dates.month):
        z.iloc[i, m - 1] = 1.0
    u = x - 1.0
    z["u"] = u
    z["u2"] = u ** 2
    z["u3"] = u ** 3
    z["knot"] = np.where(u > 0.0, u ** 3, 0.0)
    return z


def ols_fit(y: np.ndarray, Z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    beta, *_ = np.linalg.lstsq(Z, y, rcond=None)
    resid = y - Z @ beta
    return beta, resid


def newey_west_cov(Z: np.ndarray, resid: np.ndarray, maxlags: int) -> np.ndarray:
    """
    Avar(beta_hat)/n, Newey-West HAC, following Appendix D.1/D.2 of the paper
    collapsed to a single equation (M=1): g_t = Z_t * resid_t.
    """
    n = Z.shape[0]
    g = Z * resid[:, None]
    S = (g.T @ g) / n
    for j in range(1, maxlags + 1):
        w = 1.0 - j / (maxlags + 1)
        gamma = (g[j:].T @ g[:-j]) / n
        S += w * (gamma + gamma.T)
    ZtZ_inv = np.linalg.inv((Z.T @ Z) / n)
    avar = ZtZ_inv @ S @ ZtZ_inv
    return avar / n


def spline_gradient(x0: float, n_cols: int, knot_idx: int) -> np.ndarray:
    """d h(x)/dx at x0, as a gradient over the full column vector (dummies -> 0).
    h is parameterized in u = x-1 (see build_design_matrix); du/dx = 1 so the
    chain rule just means evaluating the same derivative formulas at u0."""
    u0 = x0 - 1.0
    g = np.zeros(n_cols)
    g[knot_idx - 3] = 1.0                          # d/du of u
    g[knot_idx - 2] = 2.0 * u0                      # d/du of u^2
    g[knot_idx - 1] = 3.0 * u0 ** 2                 # d/du of u^3
    if u0 > 0.0:
        g[knot_idx] = 3.0 * u0 ** 2                  # d/du of u^3 * 1{u>0}
    return g


# ─────────────────────────────────────────────────────────────────────────────
# End-to-end analysis, period-configurable
# ─────────────────────────────────────────────────────────────────────────────

def run_spline_analysis(
    daily_basis: pd.Series,
    daily_stock: pd.Series,
    commodity_label: str,
    basis_source: str,
    start: str | None = None,
    end: str | None = None,
    trailing_weeks: int = TRAILING_WEEKS,
    nw_bandwidth: int = NW_BANDWIDTH,
    output_dir: str | None = None,
    save_outputs: bool = True,
    x_range: tuple[float, float] | None = DEFAULT_X_RANGE,
    y_range: tuple[float, float] | None = DEFAULT_Y_RANGE,
) -> dict:
    """
    Fit the cubic-spline basis-on-normalized-inventory regression over an
    arbitrary sample window, given already-loaded daily basis/inventory series
    for any single commodity.

    Parameters
    ----------
    daily_basis    : Date-indexed Series, annualized basis in % p.a.
    daily_stock    : Date-indexed Series, physical inventory level.
    commodity_label: e.g. "Copper", "WTI Crude" -- used in titles/prints only.
    basis_source   : label for the basis definition used (e.g. "f1f2",
                     "cash3m") -- used in file names/titles only.
    start, end     : "YYYY-MM-DD" bounds on the REGRESSION sample (inclusive).
                     None means "use whatever is available" on that side.
                     I* (trailing average) is computed on the FULL stock
                     history first, so narrowing the window does not truncate
                     the lookback used at its first date.
    trailing_weeks : weeks in the I* trailing average (default 52).
    nw_bandwidth   : Newey-West HAC lag window in weeks (default 52).
    output_dir     : where to write CSV/HTML outputs (required if save_outputs).
    save_outputs   : if False, skip writing files (just return results).
    x_range, y_range : fixed axis ranges applied to the plot so different
                     commodities are shown on the same scale and can be
                     compared directly (default: DEFAULT_X_RANGE/_Y_RANGE,
                     sized to copper's full range). Pass None for either to
                     autorange instead (regression/CSV are unaffected either
                     way -- this only clips what's drawn on the chart).

    Returns
    -------
    dict with keys: merged (DataFrame), beta, avar, r2, slopes (dict),
    fig (plotly Figure), csv_path, html_path (paths are None if not saved),
    period_start, period_end, basis_source, commodity_label.
    """
    weekly_basis = to_weekly_last(daily_basis)
    weekly_stock = to_weekly_last(daily_stock)
    inv_weekly = normalized_inventory(weekly_stock, trailing_weeks)

    merged = pd.concat([weekly_basis.rename("basis"), inv_weekly], axis=1).dropna()
    if start is not None:
        merged = merged.loc[merged.index >= pd.Timestamp(start)]
    if end is not None:
        merged = merged.loc[merged.index <= pd.Timestamp(end)]
    if merged.empty:
        raise ValueError(f"No overlapping data in the requested window [{start}, {end}]")

    period_start, period_end = merged.index.min(), merged.index.max()
    print(f"Weekly sample: {period_start.date()} to {period_end.date()} "
          f"({len(merged)} obs)")

    Z_df = build_design_matrix(merged.index, merged["x"].values)
    y = merged["basis"].values
    Z = Z_df.values
    n_cols = Z.shape[1]
    knot_idx = n_cols - 1  # last column = knot term; x,x2,x3 are knot_idx-3..knot_idx-1

    beta, resid = ols_fit(y, Z)
    fitted = Z @ beta
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot

    avar = newey_west_cov(Z, resid, nw_bandwidth)

    def slope_at(x0: float) -> tuple[float, float]:
        g = spline_gradient(x0, n_cols, knot_idx)
        val = float(g @ beta)
        var = float(g @ avar @ g)
        t = val / np.sqrt(var) if var > 0 else np.nan
        return val, t

    slope_1, t_1 = slope_at(1.0)
    slope_075, t_075 = slope_at(0.75)
    diff = slope_075 - slope_1
    g1, g075 = spline_gradient(1.0, n_cols, knot_idx), spline_gradient(0.75, n_cols, knot_idx)
    diff_var = float((g075 - g1) @ avar @ (g075 - g1))
    t_diff = diff / np.sqrt(diff_var) if diff_var > 0 else np.nan

    print(f"\nCubic-spline basis-on-normalized-inventory regression "
          f"({commodity_label}, weekly, basis_source={basis_source!r})")
    print("Basis = monthly dummies + b1*x + b2*x^2 + b3*x^3 + b4*(x-1)^3*1{x>1} + e")
    print(f"{'':>14}{'Slope at 1':>14}{'t':>8}{'Slope at .75':>16}{'t':>8}{'Diff':>10}{'t':>8}{'R2':>8}")
    print(f"{commodity_label:>14}{slope_1:>14.4f}{t_1:>8.2f}{slope_075:>16.4f}{t_075:>8.2f}"
          f"{diff:>10.4f}{t_diff:>8.2f}{r2:>8.3f}")

    # ── Assemble output dataset ─────────────────────────────────────────────
    out = merged.copy()
    out["fitted"] = fitted
    out["month_effect"] = (Z_df[MONTH_COLS].values * beta[:12]).sum(axis=1)
    out["basis_ex_seasonal"] = out["basis"] - out["month_effect"]
    out["fitted_ex_seasonal"] = out["fitted"] - out["month_effect"]

    # ── Figure 6 style scatter + fitted curve ───────────────────────────────
    grid_x = np.linspace(max(out["x"].min(), 0.01), out["x"].max(), 200)
    grid_Z = build_design_matrix(pd.DatetimeIndex([out.index[-1]] * len(grid_x)), grid_x).values
    # month-dummy contribution isn't meaningful on the grid; only take the
    # spline part (x, x2, x3, knot) since we plot the seasonally-adjusted basis.
    grid_curve = grid_Z[:, -4:] @ beta[-4:]

    slug = commodity_label.lower().replace(" ", "_")
    period_tag = f"{basis_source}_{period_start.date()}_{period_end.date()}"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=out["x"], y=out["basis_ex_seasonal"], mode="markers", name="Actual (net of seasonal)",
        marker=dict(size=5, color="#4C78A8", opacity=0.6),
    ))
    fig.add_trace(go.Scatter(
        x=grid_x, y=grid_curve, mode="lines", name="Fitted cubic spline",
        line=dict(color="#E45756", width=3),
    ))
    fig.add_vline(x=1.0, line_dash="dot", line_color="gray", annotation_text="I/I*=1")

    title = (f"{commodity_label} ({basis_source}): Basis vs Normalized Inventory "
              f"({period_start.date()} to {period_end.date()}, net of seasonal effects)")
    n_clipped = 0
    if x_range is not None:
        n_clipped += int(((out["x"] < x_range[0]) | (out["x"] > x_range[1])).sum())
    if y_range is not None:
        n_clipped += int(((out["basis_ex_seasonal"] < y_range[0]) |
                           (out["basis_ex_seasonal"] > y_range[1])).sum())
    if n_clipped > 0:
        title += f"<br><sup>{n_clipped} obs outside the plotted axis range (still in the regression/CSV)</sup>"

    fig.update_layout(
        title=title,
        xaxis_title="Normalized inventory (I/I*)",
        yaxis_title="Basis, % p.a. (net of seasonal effects)",
        template="plotly_white",
        width=900, height=600,
    )
    if x_range is not None:
        fig.update_xaxes(range=list(x_range))
    if y_range is not None:
        fig.update_yaxes(range=list(y_range))
    if n_clipped > 0:
        print(f"Note: {n_clipped} observation(s) fall outside the plotted axis range "
              f"x={x_range}, y={y_range} (still used in the regression and saved CSV).")

    slopes = {
        "slope_at_1": slope_1, "t_at_1": t_1,
        "slope_at_0.75": slope_075, "t_at_0.75": t_075,
        "diff": diff, "t_diff": t_diff,
    }

    csv_path = html_path = None
    if save_outputs:
        if output_dir is None:
            raise ValueError("output_dir is required when save_outputs=True")
        os.makedirs(output_dir, exist_ok=True)
        csv_path = os.path.join(output_dir, f"{slug}_basis_inventory_weekly_{period_tag}.csv")
        html_path = os.path.join(output_dir, f"{slug}_basis_vs_inventory_{period_tag}.html")
        out.to_csv(csv_path)
        fig.write_html(html_path)
        print(f"\nSaved merged weekly series -> {csv_path}")
        print(f"Saved plot -> {html_path}")

    return {
        "merged": out, "beta": beta, "avar": avar, "r2": r2, "slopes": slopes,
        "fig": fig, "csv_path": csv_path, "html_path": html_path,
        "period_start": period_start, "period_end": period_end,
        "basis_source": basis_source, "commodity_label": commodity_label,
    }
