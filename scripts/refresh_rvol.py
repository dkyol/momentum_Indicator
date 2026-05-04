"""Scheduled Deployment entry point: refresh intraday RVOL.

Run every 15 minutes Mon-Fri during US market hours via a Replit
Scheduled Deployment.  ``save_rvol_snapshot`` self-guards against
off-hours invocations so it's safe to schedule generously.

Recommended cron:  ``*/15 13-21 * * 1-5``  (UTC; covers 09:00-16:45 EST
year-round including DST overlap).
"""
from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("refresh_rvol")


def main() -> int:
    try:
        from models import create_tables
        create_tables()  # idempotent — ensures alpha_cache table exists
        from rvol import save_rvol_snapshot
        result = save_rvol_snapshot()
        log.info("RVOL refresh wrote %d tickers", len(result))
        return 0
    except Exception as e:
        log.exception("RVOL refresh failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
