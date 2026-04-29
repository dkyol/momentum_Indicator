"""
Signal backtester & performance report.

Replays each individual signal across the universe over the last 3 years
on daily bars and reports:

    * trades       – number of (signal-day, exit-day) pairs evaluated
    * hit_rate     – % of trades that finished positive
    * avg_return   – mean per-trade return (%)
    * median_return
    * max_return
    * min_return
    * holding_days – fixed holding period used (10)

We use a simple, deterministic backtest:
    - On day T, if the signal is true on the close, "buy" at the next
      day's open (T+1).
    - Hold for HOLDING_DAYS bars.
    - Exit at that day's close.
    - Record return.

This is deliberately simple – it isolates the *signal*'s edge rather
than testing a full strategy with stops & sizing.  The user can then
tune which signals deserve weight in the Edge Score.
"""

from __future__ import annotations

import logging
from datetime import datetime
from statistics import mean, median

import numpy as np
import pandas as pd

from alpha_cache import CACHE_BACKTEST, EST, load_json, save_json, stamp_alpha_refresh
from price_data import fetch_daily_history
from universe import get_universe

logger = logging.getLogger(__name__)


HOLDING_DAYS = 10  # business days held per simulated trade
LOOKBACK_PERIOD = "3y"


def _rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _signal_series(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Compute a boolean Series for each named signal across the full bar history.

    The definitions here MUST match ``setups.py`` so that the backtest
    measures the edge of the same patterns the dashboard surfaces.
    """
    closes = df["Close"].dropna()
    volumes = df["Volume"].reindex(closes.index).fillna(0) if "Volume" in df else pd.Series(0, index=closes.index)

    sma_50 = closes.rolling(50).mean()
    sma_200 = closes.rolling(200).mean()
    rsi = _rsi(closes, 14)
    high_52w = closes.rolling(252, min_periods=200).max()
    avg_vol_20 = volumes.rolling(20).mean()

    trend_pullback = (
        (closes > sma_200)
        & (rsi < 40)
        & ((closes - sma_50).abs() / sma_50 < 0.05)
    ).fillna(False)

    high_52w_breakout = (
        (closes >= high_52w * 0.98) & high_52w.notna()
    ).fillna(False)

    volume_thrust = (
        (volumes > 2 * avg_vol_20)
        & (closes > closes.shift(1))
        & (avg_vol_20 > 0)
    ).fillna(False)

    # Setups.py treats "golden cross" as cross within the last 5 days.
    # We mirror that by flagging True if the cross happened in the prior
    # 5-bar window so a single setup matches one (not five) backtest trades.
    sma_diff = sma_50 - sma_200
    cross_now = ((sma_diff.shift(1) <= 0) & (sma_diff > 0)).fillna(False)
    golden_cross = cross_now.rolling(5, min_periods=1).max().astype(bool)

    # Bullish RSI divergence: lower-low in close vs higher-low in RSI over
    # the trailing 20 bars.  Vectorised version of setups.py's check.
    close_first_low = closes.rolling(20).apply(
        lambda x: x[:10].min() if len(x) >= 20 else float("nan"), raw=True
    )
    close_second_low = closes.rolling(20).apply(
        lambda x: x[10:].min() if len(x) >= 20 else float("nan"), raw=True
    )
    rsi_first_low = rsi.rolling(20).apply(
        lambda x: x[:10].min() if len(x) >= 20 else float("nan"), raw=True
    )
    rsi_second_low = rsi.rolling(20).apply(
        lambda x: x[10:].min() if len(x) >= 20 else float("nan"), raw=True
    )
    bullish_rsi_divergence = (
        (close_second_low < close_first_low) & (rsi_second_low > rsi_first_low)
    ).fillna(False)

    return {
        "trend_pullback": trend_pullback,
        "high_52w_breakout": high_52w_breakout,
        "volume_thrust": volume_thrust,
        "golden_cross": golden_cross,
        "bullish_rsi_divergence": bullish_rsi_divergence,
    }


def _backtest_one_signal(
    bars: dict[str, pd.DataFrame], signal_name: str
) -> dict:
    returns: list[float] = []

    for ticker, df in bars.items():
        if df is None or "Close" not in df or len(df) < 260:
            continue
        try:
            sig = _signal_series(df).get(signal_name)
            if sig is None:
                continue
        except Exception:
            continue

        closes = df["Close"]
        opens = df["Open"] if "Open" in df else closes
        idx = closes.index

        # For every signal day, buy at next-day open and exit HOLDING_DAYS later.
        trigger_positions = np.where(sig.values)[0]
        for pos in trigger_positions:
            entry_pos = pos + 1
            exit_pos = pos + 1 + HOLDING_DAYS
            if exit_pos >= len(idx):
                continue
            try:
                entry = float(opens.iloc[entry_pos])
                exitp = float(closes.iloc[exit_pos])
                if entry <= 0:
                    continue
                returns.append((exitp / entry - 1.0) * 100.0)
            except Exception:
                continue

    if not returns:
        return {
            "signal": signal_name,
            "trades": 0,
            "hit_rate": None,
            "avg_return": None,
            "median_return": None,
            "max_return": None,
            "min_return": None,
        }

    return {
        "signal": signal_name,
        "trades": len(returns),
        "hit_rate": round(sum(1 for r in returns if r > 0) / len(returns) * 100.0, 1),
        "avg_return": round(mean(returns), 2),
        "median_return": round(median(returns), 2),
        "max_return": round(max(returns), 2),
        "min_return": round(min(returns), 2),
    }


def run_backtest() -> dict:
    universe = get_universe()
    logger.info(f"Backtester downloading {LOOKBACK_PERIOD} of bars for {len(universe)} tickers")
    bars = fetch_daily_history(universe, period=LOOKBACK_PERIOD)
    if not bars:
        return {"results": [], "holding_days": HOLDING_DAYS}

    signals = [
        "trend_pullback",
        "high_52w_breakout",
        "volume_thrust",
        "golden_cross",
        "bullish_rsi_divergence",
    ]
    results = [_backtest_one_signal(bars, name) for name in signals]
    return {
        "results": results,
        "holding_days": HOLDING_DAYS,
        "lookback": LOOKBACK_PERIOD,
        "universe_size": len(universe),
    }


def save_backtest() -> dict:
    result = run_backtest()
    payload = {"as_of": datetime.now(EST).isoformat(), **result}
    save_json(CACHE_BACKTEST, payload)
    stamp_alpha_refresh("backtest")
    logger.info(f"Cached backtest results for {len(result.get('results', []))} signals")
    return result


def get_cached_backtest() -> dict:
    payload = load_json(CACHE_BACKTEST, {})
    if not isinstance(payload, dict):
        return {"results": [], "holding_days": HOLDING_DAYS}
    payload.setdefault("results", [])
    payload.setdefault("holding_days", HOLDING_DAYS)
    return payload
