"""One-shot: copy local cached_*.json files into the alpha_cache table.

Run this once after deploying the DB-backed cache layer (and any time
you want to push freshly-recomputed local caches up to the production
DB without waiting for the next Scheduled Deployment tick).
"""
from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import sys


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("seed_alpha_cache_db")
    try:
        from models import create_tables
        create_tables()
        from alpha_cache import seed_db_from_local_files
        results = seed_db_from_local_files()
        ok = sum(1 for v in results.values() if v)
        log.info("Seeded %d/%d cache files: %s", ok, len(results), results)
        return 0 if ok else 1
    except Exception as e:
        log.exception("Seed failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
