"""Scheduled Deployment entry point: end-of-day equity snapshot.

Captures one row in ``equity_snapshots`` per trading day so the
portfolio dashboard's equity curve and drawdown KPI stay accurate
even when the web tier is Autoscale (no persistent scheduler).

Recommended cron:  ``10 21 * * 1-5``  UTC  (16:10 EST / 17:10 EDT;
always after the 16:00 ET close).
"""
from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("equity_snapshot")


def main() -> int:
    try:
        from models import create_tables
        create_tables()
        from portfolio_stats import take_equity_snapshot
        try:
            from paper_trader import trader
            price_fn = trader.get_current_price if trader else None
        except Exception as e:
            log.warning("paper_trader unavailable, using yfinance fallback: %s", e)
            price_fn = None
        snap = take_equity_snapshot(get_current_price=price_fn)
        log.info("Equity snapshot: %s", snap)
        return 0
    except Exception as e:
        log.exception("Equity snapshot failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
