"""
Centralised batched price-data fetcher.

Every alpha module needs daily OHLCV bars for the universe + benchmarks.
``yf.download`` supports batching and is dramatically faster (and friendlier
to Yahoo's rate limits) than calling ``yf.Ticker(t).history(...)`` per ticker.

We expose:

* ``fetch_daily_history(tickers, period="2y")`` – returns a dict
  ``{ticker: pd.DataFrame}`` of single-name OHLCV frames so callers
  can iterate without worrying about MultiIndex columns.

The data is fetched live each time it is called; calling code is
responsible for caching the *derived* result (RS percentiles, setup
flags, etc.) to disk.  We intentionally do **not** cache the raw
price frames themselves – they are large and the analyses are cheap
once we have them in memory.
"""

from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_daily_history(
    tickers: Iterable[str],
    period: str = "2y",
) -> dict[str, pd.DataFrame]:
    """Batch-download daily OHLCV history for the given tickers.

    Returns a dict ``{ticker: DataFrame}`` keyed by the original ticker
    string.  Tickers with no data are omitted from the result.
    """
    tickers_list = list(dict.fromkeys(tickers))  # de-dupe, preserve order
    if not tickers_list:
        return {}

    try:
        raw = yf.download(
            tickers=" ".join(tickers_list),
            period=period,
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as e:
        logger.error(f"Bulk price download failed: {e}")
        return {}

    out: dict[str, pd.DataFrame] = {}

    if raw is None or raw.empty:
        return out

    if isinstance(raw.columns, pd.MultiIndex):
        for t in tickers_list:
            try:
                if t in raw.columns.get_level_values(0):
                    df = raw[t].dropna(how="all")
                    if not df.empty:
                        out[t] = df
            except Exception as e:
                logger.warning(f"Could not extract bars for {t}: {e}")
    else:
        # Single-ticker case: yfinance returns a flat DataFrame.
        df = raw.dropna(how="all")
        if not df.empty and tickers_list:
            out[tickers_list[0]] = df

    return out
