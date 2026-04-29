"""
Simple JSON-on-disk cache shared by every alpha module.

We follow the existing convention (cached_high_volume_stocks.json,
cached_momentum_data.json, ...) and keep one file per dataset so
the dashboard can render whatever subset is available even if a
later refresh step fails.

All writes go through a temp-file + atomic ``os.replace`` rename so
readers (Flask request handlers) never see partially-written JSON
even if a refresh thread is interrupted.  Cross-thread coordination
between the bootstrap thread, the manual /refresh_alpha endpoint,
and the nightly scheduler is provided by the module-level
``refresh_lock`` — wrap the orchestrator in ``with refresh_lock:``
to serialise full refreshes.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from typing import Any

import pytz

logger = logging.getLogger(__name__)

# Serialises full alpha refreshes across the bootstrap thread,
# the /refresh_alpha endpoint, and the nightly scheduler.
refresh_lock = threading.Lock()
# Protects the small read-modify-write of the meta file.
_meta_lock = threading.Lock()

EST = pytz.timezone("US/Eastern")

# ------------------------------------------------------------------
# Cache file paths
# ------------------------------------------------------------------
CACHE_FUNDAMENTALS = "cached_fundamentals.json"
CACHE_VALUE = "cached_value_screen.json"
CACHE_RS = "cached_relative_strength.json"
CACHE_SETUPS = "cached_setups.json"
CACHE_REGIME = "cached_market_regime.json"
CACHE_CATALYSTS = "cached_catalysts.json"
CACHE_EDGE = "cached_edge_score.json"
CACHE_BACKTEST = "cached_backtest.json"
CACHE_ALPHA_META = "cached_alpha_meta.json"  # last-update info


def save_json(path: str, data: Any) -> None:
    """Atomically write any JSON-serialisable object to disk.

    Writes to ``path + ".tmp"`` then ``os.replace``s it onto the final
    path so concurrent readers always see a complete file.
    """
    tmp_path = f"{path}.tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(data, f, default=str)
        os.replace(tmp_path, path)
    except Exception as e:
        logger.error(f"Failed to write cache {path}: {e}")
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass


def load_json(path: str, default: Any) -> Any:
    """Read a cached JSON file, returning ``default`` if missing or invalid."""
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read cache {path}: {e}")
    return default


def stamp_alpha_refresh(section: str) -> None:
    """Record the current EST timestamp for a named alpha section."""
    with _meta_lock:
        meta = load_json(CACHE_ALPHA_META, {})
        meta[section] = datetime.now(EST).isoformat()
        save_json(CACHE_ALPHA_META, meta)


def get_alpha_meta() -> dict:
    """Return the dict of {section: last_refreshed_iso} timestamps."""
    return load_json(CACHE_ALPHA_META, {})
