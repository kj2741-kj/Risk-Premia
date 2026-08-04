"""
research/benchmarks.py
========================
Traditional-asset benchmark series for comparing this project's commodity
risk premia strategies against Equity, Fixed Income, a broad Commodity
Index, and Gold as a distinct safe-haven -- the standard "are we actually
adding value beyond simple beta, and do we diversify a traditional
portfolio" questions for any systematic commodity strategy.

Data source: yfinance (free, no credentials, daily ETF-based proxies).
Cached to a local CSV after first download so repeated dashboard runs
don't re-hit the network every time -- refresh manually via
refresh_benchmark_cache() if newer prices are wanted.

Tickers (user's decision, 2026-08-04):
  SPY  - S&P 500 (Equity)
  AGG  - US Aggregate Bond (Fixed Income)
  DBC  - Invesco DB Commodity Index Tracking Fund (broad Commodity Index,
         diversified across energy/metals/agriculture -- deliberately NOT
         this project's own commodity book, so it tests whether the
         active Momentum/Carry/Value signals add value beyond simple
         passive commodity beta)
  GLD  - Gold (distinct traditional safe-haven; partially overlaps with
         this project's own Precious Metals book, which already holds
         Gold as a commodity -- this comparison is really "does our
         systematic, multi-strategy approach beat just holding physical
         Gold passively")

Plus a constructed "60/40 Portfolio" (60% SPY + 40% AGG, daily-rebalanced)
-- the classic traditional balanced-portfolio benchmark commodity risk
premia strategies are pitched as diversifying.

Next step (not yet built): SG Trend Index (SocGen CTA/trend-following
industry benchmark) -- not on yfinance, needs a different source (likely
scraping SocGen's own published index page); flagged for a follow-up.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import yfinance as yf

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_CACHE_FILE = os.path.join(_THIS_DIR, "_benchmark_prices_cache.csv")

TICKERS = {
    "Equity (S&P 500)": "SPY",
    "Fixed Income (US Agg Bond)": "AGG",
    "Commodity Index (DBC)": "DBC",
    "Gold (Safe Haven)": "GLD",
}

START_DATE = "2005-01-01"  # well before REPORT_START (2011), for warm-up headroom


def refresh_benchmark_cache() -> pd.DataFrame:
    """Downloads fresh daily close prices for every ticker in TICKERS via
    yfinance and overwrites the local cache file. Call this manually when
    newer data is wanted -- not run automatically on every load, so a
    Streamlit session never has a live network dependency in the middle of
    rendering."""
    frames = {}
    for ticker in TICKERS.values():
        df = yf.download(ticker, start=START_DATE, progress=False, auto_adjust=True)
        frames[ticker] = df["Close"].squeeze()
    prices = pd.DataFrame(frames)
    prices.to_csv(_CACHE_FILE)
    return prices


def load_benchmark_prices() -> pd.DataFrame:
    """Loads cached daily close prices (columns = raw tickers), pulling
    fresh from yfinance once if no cache file exists yet."""
    if not os.path.exists(_CACHE_FILE):
        return refresh_benchmark_cache()
    return pd.read_csv(_CACHE_FILE, index_col=0, parse_dates=True)


def load_benchmark_returns() -> dict[str, pd.Series]:
    """Daily LOG returns for each individual ticker (keyed by display
    label, matching TICKERS), plus a constructed "60/40 Portfolio" series.

    The 60/40 blend uses SIMPLE (not log) returns for the weighted
    combination -- a daily-rebalanced 60/40 portfolio's dollar P&L is
    genuinely a linear blend of each leg's simple return (0.6*r_equity +
    0.4*r_bond), not a log-additive quantity. The blended simple return is
    then converted to a log return via log(1+r) so the result stays
    directly comparable (via the same cumsum/exp conventions used
    everywhere else in this project) to every other series here."""
    prices = load_benchmark_prices()
    log_returns = {}
    for label, ticker in TICKERS.items():
        log_returns[label] = np.log(prices[ticker]).diff().dropna()

    simple_spy = prices[TICKERS["Equity (S&P 500)"]].pct_change()
    simple_agg = prices[TICKERS["Fixed Income (US Agg Bond)"]].pct_change()
    blended_simple = (0.6 * simple_spy + 0.4 * simple_agg).dropna()
    log_returns["60/40 Portfolio"] = np.log(1 + blended_simple)

    return log_returns
