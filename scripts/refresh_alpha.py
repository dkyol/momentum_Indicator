"""Scheduled Deployment entry point: full alpha pipeline refresh.

Refreshes fundamentals, value screen, relative strength, setups,
market regime, catalysts, and the composite edge score.  Skips the
slow backtest by default; pass ``--with-backtest`` to include it
(use that for a once-a-night schedule, not the daily one).

Recommended crons:
* Daily post-open refresh:    ``5 14 * * 1-5``  UTC (10:05 EST)
* Nightly with backtest:      ``30 3 * * 2-7``  UTC (22:30 EST prior day)
"""
from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("refresh_alpha")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-backtest", action="store_true",
                        help="Include the slow backtest step")
    args = parser.parse_args()

    try:
        from models import create_tables
        create_tables()
        from alpha_engine import refresh_alpha_data
        result = refresh_alpha_data(include_backtest=args.with_backtest)
        log.info("Alpha refresh complete (with_backtest=%s): %s",
                 args.with_backtest, result)
        return 0
    except Exception as e:
        log.exception("Alpha refresh failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
