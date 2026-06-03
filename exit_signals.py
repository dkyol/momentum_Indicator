"""
Exit Signal Engine

Classifies each stock by its exit condition: HOLD, TAKE_PROFIT, OVERBOUGHT, STOP_THREATENED, TREND_BROKEN.

Priority order (first match wins):
1. TREND_BROKEN      – SMA50 crossed below SMA200 (death cross)
2. STOP_THREATENED   – price within 2% above stop level
3. OVERBOUGHT        – RSI > 70 or price > 52w high
4. TAKE_PROFIT       – RSI > 65 or price within 3% of target
5. HOLD              – none of the above

Runs nightly alongside the alpha refresh. Caches results to cached_exit_signals.json.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from alpha_cache import CACHE_EXIT_SIGNALS, load_json, save_json
from setups import get_cached_setups
from swing_picks import build_picks

logger = logging.getLogger(__name__)


def _classify_exit(
    close: float,
    rsi: float | None,
    stop_price: float | None,
    target_price: float | None,
    high_52w: float | None,
    sma_50: float | None,
    sma_200: float | None,
) -> tuple[str, str]:
    """
    Classify exit condition by priority. Returns (signal_code, reason_text).

    Priority order:
    1. TREND_BROKEN      – SMA50 < SMA200
    2. STOP_THREATENED   – price within 2% above stop_price
    3. OVERBOUGHT        – RSI > 70 or price > 52w high
    4. TAKE_PROFIT       – RSI > 65 or price within 3% of target
    5. HOLD              – no signal
    """
    # 1. TREND_BROKEN
    if (
        sma_50 is not None
        and sma_200 is not None
        and sma_50 < sma_200
    ):
        return ("TREND_BROKEN", "Death cross: 50d crossed below 200d SMA")

    # 2. STOP_THREATENED
    if stop_price is not None and close is not None and close > 0:
        dist_above_stop = (close - stop_price) / close
        if dist_above_stop <= 0.02:  # within 2% above stop
            return ("STOP_THREATENED", f"Price within 2% of stop ${stop_price:.2f} — protect capital")

    # 3. OVERBOUGHT
    if rsi is not None and rsi > 70:
        return ("OVERBOUGHT", f"RSI {rsi:.0f} — overbought")
    if high_52w is not None and close is not None and close > high_52w:
        return ("OVERBOUGHT", "Trading above 52w high")

    # 4. TAKE_PROFIT
    if rsi is not None and rsi > 65:
        return ("TAKE_PROFIT", f"RSI {rsi:.0f} approaching overbought — consider trim")
    if target_price is not None and close is not None and close > 0:
        dist_to_target = (target_price - close) / close
        if dist_to_target <= 0.03:  # within 3% of target
            return ("TAKE_PROFIT", f"Within 3% of target ${target_price:.2f}")

    # 5. HOLD
    return ("HOLD", "No exit signal — hold")


def compute_exit_signals(picks: list[dict] | None = None) -> dict[str, dict[str, Any]]:
    """
    Compute exit signals for all tickers in the setups cache.

    Returns dict: {symbol: exit_row, ...} where exit_row contains:
        exit_signal: str          # "HOLD" | "TAKE_PROFIT" | "OVERBOUGHT" | "STOP_THREATENED" | "TREND_BROKEN"
        exit_reason: str          # human-readable text
        distance_to_target_pct: float | None
        distance_to_stop_pct: float | None
        rsi: float | None
        close: float | None
    """
    # If picks not provided, compute them permissively (all setups)
    if picks is None:
        picks = build_picks(min_edge=0, min_rs=0)

    # Map picks by symbol for quick lookup of stop/target levels
    pick_map = {p.get("Symbol"): p for p in picks if p.get("Symbol")}

    # Map setups by symbol for price data
    setups = get_cached_setups() or []
    setup_map = {s.get("Symbol"): s for s in setups if s.get("Symbol")}

    signals: dict[str, dict[str, Any]] = {}

    for sym, setup_row in setup_map.items():
        close = setup_row.get("Close")
        rsi = setup_row.get("RSI_14")
        sma_50 = setup_row.get("SMA_50")
        sma_200 = setup_row.get("SMA_200")
        high_52w = setup_row.get("High_52w")

        # Look up stop/target from the pick if it exists
        pick_row = pick_map.get(sym, {})
        stop_price = pick_row.get("Stop_Level")
        target_price = pick_row.get("Target_Price")

        # Classify
        signal_code, reason_text = _classify_exit(
            close=close,
            rsi=rsi,
            stop_price=stop_price,
            target_price=target_price,
            high_52w=high_52w,
            sma_50=sma_50,
            sma_200=sma_200,
        )

        # Compute distances
        distance_to_target_pct = None
        if target_price is not None and close is not None and close > 0:
            distance_to_target_pct = round((target_price - close) / close * 100, 1)

        distance_to_stop_pct = None
        if stop_price is not None and close is not None and close > 0:
            distance_to_stop_pct = round((close - stop_price) / close * 100, 1)

        signals[sym] = {
            "exit_signal": signal_code,
            "exit_reason": reason_text,
            "distance_to_target_pct": distance_to_target_pct,
            "distance_to_stop_pct": distance_to_stop_pct,
            "rsi": round(float(rsi), 1) if rsi else None,
            "close": round(float(close), 2) if close else None,
        }

    return signals


def save_exit_signals() -> dict[str, Any]:
    """
    Compute exit signals and cache to CACHE_EXIT_SIGNALS.
    Returns the full cache payload.
    """
    try:
        signals = compute_exit_signals()
        payload = {
            "as_of": datetime.now(timezone.utc).isoformat(),
            "signals": signals,
        }
        save_json(CACHE_EXIT_SIGNALS, payload)
        logger.info(f"Exit signals cached: {len(signals)} tickers")
        return payload
    except Exception as e:
        logger.error(f"Failed to save exit signals: {e}")
        return {"as_of": None, "signals": {}}


def get_cached_exit_signals() -> dict[str, Any]:
    """
    Load cached exit signals from CACHE_EXIT_SIGNALS.
    Returns dict with "as_of" and "signals" keys.
    """
    try:
        payload = load_json(CACHE_EXIT_SIGNALS, default={"as_of": None, "signals": {}})
        return payload
    except Exception as e:
        logger.warning(f"Failed to load exit signals: {e}")
        return {"as_of": None, "signals": {}}
