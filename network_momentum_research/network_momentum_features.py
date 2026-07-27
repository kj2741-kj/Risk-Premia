"""
network_momentum_research/network_momentum_features.py
========================================
The 8 individual momentum features from Pu/Roberts/Dong/Zohren, "Network
Momentum across Asset Classes" (2023), Section 2.2 -- built as a standalone,
asset-agnostic feature function ahead of the lightweight cross-commodity
lead-lag pilot (does one commodity's lagged momentum predict a DIFFERENT
commodity's next-day return, beyond the 8 hand-picked StatArb pairs already
in this project -- see project memory for the full pilot design). This
module only builds the FEATURES; the pairwise scan + FDR gate is a separate
step, reusing research/stats.py::bh_fdr the same way every other test in
this pipeline does (the paper itself does NOT apply any multiple-testing
correction -- Table 4's asterisks are plain per-coefficient p<0.05 on a
single rolling regression -- so that discipline is this project's own
addition, not something being replicated from the paper).

Input convention: raw F1 price level (not the ratio-continuous series) --
matches this project's existing Momentum sleeve (engine.py's
momentum_composite_position takes f1r directly) and Value sleeve (raw curve
tenor prices), not the back-adjusted continuous series. A moving-average
crossover / EWMA-based trend feature should track a real contract's actual
price, same reasoning as those two sleeves.

Features (paper's own notation, Eq. 1-3 + Appendix A.2):
  1-5. Vol-scaled return over Delta in {1, 21, 63, 126, 252} trading days:
       r[t-Delta:t] / (sigma_t * sqrt(Delta)), sigma_t = EWM std of daily
       simple returns, 60-day span.
  6-8. Normalised MACD y(S,L) for (S,L) in {(8,24), (16,48), (32,96)}:
       MACD(S,L) = EWMA(price, span~S) - EWMA(price, span~L)  [alpha=1/J]
       MACD_norm = MACD / std(price, 63d rolling)
       y = MACD_norm / std(MACD_norm, 252d rolling)
  All 8 features are then winsorised to +-5x their own EWM std around their
  own EWM mean (half-life=252 days), per the paper's own preprocessing step.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

VOL_SCALE_HORIZONS = (1, 21, 63, 126, 252)
VOL_SPAN = 60
MACD_PAIRS = ((8, 24), (16, 48), (32, 96))
WINSOR_HALFLIFE = 252
WINSOR_N_STD = 5.0


def _daily_simple_return(price: pd.Series) -> pd.Series:
    return price.pct_change()


def vol_scaled_return(price: pd.Series, horizon: int, vol_span: int = VOL_SPAN) -> pd.Series:
    """r[t-horizon:t] / (sigma_t * sqrt(horizon)) -- Eq. in Sec 2.2, first bullet."""
    daily_ret = _daily_simple_return(price)
    sigma_t = daily_ret.ewm(span=vol_span, min_periods=vol_span).std()
    horizon_ret = price.pct_change(horizon)
    return horizon_ret / (sigma_t * np.sqrt(horizon))


def macd_feature(price: pd.Series, s: int, l: int) -> pd.Series:
    """Normalised MACD y(S,L), Eq. 1-3: EWMA(price,S)-EWMA(price,L), divided
    by 63d rolling price std, then divided by 252d rolling std of THAT
    normalised series (a double normalisation -- price-vol-adjusted, then
    made roughly stationary)."""
    m_s = price.ewm(alpha=1.0 / s, min_periods=s).mean()
    m_l = price.ewm(alpha=1.0 / l, min_periods=l).mean()
    macd = m_s - m_l
    macd_norm = macd / price.rolling(63, min_periods=63).std()
    y = macd_norm / macd_norm.rolling(252, min_periods=252).std()
    return y


def _winsorize_ewm(feature: pd.Series, halflife: int = WINSOR_HALFLIFE, n_std: float = WINSOR_N_STD) -> pd.Series:
    """Cap/floor at +-n_std * EWM std around the feature's own EWM mean
    (half-life=252 days), per the paper's stated preprocessing step."""
    center = feature.ewm(halflife=halflife, min_periods=halflife).mean()
    spread = feature.ewm(halflife=halflife, min_periods=halflife).std()
    lo, hi = center - n_std * spread, center + n_std * spread
    return feature.clip(lower=lo, upper=hi)


def compute_paper_momentum_features(price: pd.Series) -> pd.DataFrame:
    """Returns an 8-column DataFrame (same index as `price`), one column per
    feature, winsorised. `price` should be the raw F1 series (see module
    docstring for why raw, not ratio-continuous)."""
    price = price.dropna()
    cols = {}
    for h in VOL_SCALE_HORIZONS:
        cols[f"vscaled_ret_{h}d"] = vol_scaled_return(price, h)
    for s, l in MACD_PAIRS:
        cols[f"macd_{s}_{l}"] = macd_feature(price, s, l)
    df = pd.DataFrame(cols)
    for c in df.columns:
        df[c] = _winsorize_ewm(df[c])
    return df
