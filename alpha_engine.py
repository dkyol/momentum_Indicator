"""
Top-level orchestrator for the alpha pipeline.

Refresh order matters because some steps consume the output of earlier
steps:

    1. fundamentals          – needed by value, catalysts, edge
    2. value screen          – consumes fundamentals
    3. relative strength     – independent (price-only)
    4. setups                – independent (price-only)
    5. market regime         – independent (price-only)
    6. catalysts             – consumes fundamentals
    7. edge score            – consumes value + RS + setups + catalysts
    8. backtest              – heavy, run last & only on demand by default
"""

from __future__ import annotations

import logging

from alpha_cache import refresh_lock
from backtester import save_backtest
from catalysts import save_catalysts
from edge_score import save_edge_scores
from fundamentals import save_fundamentals
from market_regime import save_market_regime
from relative_strength import save_relative_strength
from setups import save_setups
from value_screener import save_value_screen

logger = logging.getLogger(__name__)


def refresh_alpha_data(include_backtest: bool = False) -> dict:
    """Run the full alpha pipeline and return a summary dict.

    ``include_backtest`` defaults to False because the backtester
    re-downloads 3 years of bars for the entire universe and is the
    slowest step; we only run it when explicitly requested (nightly job
    or manual button click).

    A module-level lock (``alpha_cache.refresh_lock``) ensures that the
    bootstrap thread, the /refresh_alpha endpoint, and the nightly
    scheduler can never run simultaneously and produce mixed-generation
    cache files.  Concurrent callers that find the lock held return a
    summary indicating the refresh was skipped.
    """
    if not refresh_lock.acquire(blocking=False):
        logger.info("[alpha] refresh skipped - another refresh is already in progress")
        return {"skipped": "another refresh in progress"}

    try:
        summary: dict[str, str] = {}
        steps = [
            ("fundamentals", save_fundamentals),
            ("value", save_value_screen),
            ("relative_strength", save_relative_strength),
            ("setups", save_setups),
            ("regime", save_market_regime),
            ("catalysts", save_catalysts),
            ("edge", save_edge_scores),
        ]
        if include_backtest:
            steps.append(("backtest", save_backtest))

        for name, fn in steps:
            try:
                logger.info(f"[alpha] running {name}")
                fn()
                summary[name] = "ok"
            except Exception as e:
                logger.error(f"[alpha] {name} failed: {e}")
                summary[name] = f"error: {e}"

        return summary
    finally:
        refresh_lock.release()
