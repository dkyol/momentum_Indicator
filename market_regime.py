"""
Market regime / breadth panel.

Gives the dashboard a single risk-on / neutral / risk-off classifier
based on three classical macro signals:

  1. SPY vs its 200-day SMA (trend)
  2. VIX level (fear)
  3. Breadth: % of universe stocks above their 50-day SMA

The classifier is intentionally simple so it's easy to override:

  * risk-on  : SPY >= SMA200, VIX < 20, breadth >= 55%
  * risk-off : SPY <  SMA200 OR VIX > 28 OR breadth <  35%
  * neutral  : everything else

The paper trader checks ``is_risk_on()`` before entering new positions.
"""

from __future__ import annotations

import logging
from datetime import datetime

import numpy as np
import pandas as pd

from alpha_cache import CACHE_REGIME, EST, load_json, save_json, stamp_alpha_refresh
from price_data import fetch_daily_history
from universe import MARKET_BENCHMARK, VIX_SYMBOL, get_universe

logger = logging.getLogger(__name__)


def _classify(spy_above_200: bool, vix: float | None, breadth: float | None) -> str:
    risk_on = spy_above_200 and (vix is not None and vix < 20) and (breadth is not None and breadth >= 55)
    risk_off = (
        not spy_above_200
        or (vix is not None and vix > 28)
        or (breadth is not None and breadth < 35)
    )
    if risk_on:
        return "risk_on"
    if risk_off:
        return "risk_off"
    return "neutral"


def compute_market_regime() -> dict:
    universe = get_universe()
    tickers = list(dict.fromkeys([MARKET_BENCHMARK, VIX_SYMBOL] + universe))
    bars = fetch_daily_history(tickers, period="2y")

    # SPY vs 200d SMA
    spy = bars.get(MARKET_BENCHMARK)
    spy_close = spy_sma200 = spy_sma50 = None
    spy_above_200 = False
    spy_pct_vs_200 = None
    if spy is not None and "Close" in spy:
        closes = spy["Close"].dropna()
        if len(closes) >= 200:
            spy_close = float(closes.iloc[-1])
            spy_sma200 = float(closes.tail(200).mean())
            spy_sma50 = float(closes.tail(50).mean())
            spy_above_200 = spy_close >= spy_sma200
            if spy_sma200 > 0:
                spy_pct_vs_200 = (spy_close / spy_sma200 - 1.0) * 100.0

    # VIX
    vix_value = None
    vix_df = bars.get(VIX_SYMBOL)
    if vix_df is not None and "Close" in vix_df:
        vix_close = vix_df["Close"].dropna()
        if not vix_close.empty:
            vix_value = float(vix_close.iloc[-1])

    # Breadth: % of universe stocks above 50d SMA
    above_50 = total = 0
    for t in universe:
        df = bars.get(t)
        if df is None or "Close" not in df:
            continue
        closes = df["Close"].dropna()
        if len(closes) < 50:
            continue
        sma50 = float(closes.tail(50).mean())
        if sma50 <= 0:
            continue
        total += 1
        if float(closes.iloc[-1]) >= sma50:
            above_50 += 1
    breadth = (above_50 / total * 100.0) if total > 0 else None

    regime = _classify(spy_above_200, vix_value, breadth)

    return {
        "regime": regime,
        "spy_close": round(spy_close, 2) if spy_close is not None else None,
        "spy_sma_50": round(spy_sma50, 2) if spy_sma50 is not None else None,
        "spy_sma_200": round(spy_sma200, 2) if spy_sma200 is not None else None,
        "spy_pct_vs_200": round(spy_pct_vs_200, 2) if spy_pct_vs_200 is not None else None,
        "spy_above_200": bool(spy_above_200),
        "vix": round(vix_value, 2) if vix_value is not None else None,
        "breadth_pct": round(breadth, 1) if breadth is not None else None,
        "breadth_above": above_50,
        "breadth_total": total,
    }


def save_market_regime() -> dict:
    result = compute_market_regime()
    payload = {"as_of": datetime.now(EST).isoformat(), **result}
    save_json(CACHE_REGIME, payload)
    stamp_alpha_refresh("regime")
    logger.info(f"Cached market regime: {result.get('regime')}")
    return result


def get_cached_market_regime() -> dict:
    payload = load_json(CACHE_REGIME, {})
    if not isinstance(payload, dict):
        return {}
    return payload


def is_risk_on() -> bool:
    """Convenience: True if the latest cached regime is risk_on or neutral.

    The paper trader uses this to decide whether to open new positions.
    We allow neutral as well so the trader doesn't sit out indefinitely;
    only risk_off blocks new entries.
    """
    regime = get_cached_market_regime().get("regime")
    return regime != "risk_off"
