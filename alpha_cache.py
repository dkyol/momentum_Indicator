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
CACHE_RVOL = "cached_rvol.json"  # intraday time-adjusted relative volume
CACHE_ALPHA_META = "cached_alpha_meta.json"  # last-update info


def _sanitize_for_json(obj: Any) -> Any:
    """Recursively replace pandas/numpy NaN with None so cached JSON is
    free of ``NaN`` literals.

    ``pd.DataFrame.where(pd.notna, None)`` is unreliable on float-dtype
    columns – pandas casts ``None`` back to ``NaN`` to preserve the
    column dtype.  Converting through ``json.dump`` then yields the
    non-standard ``NaN`` literal (which our own consumers tolerate, but
    which sorts inconsistently and renders as the string "NaN" in
    Jinja).  We do the scrub here so every alpha cache benefits without
    touching individual modules.
    """
    import math
    if obj is None:
        return None
    if isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(v) for v in obj]
    return obj


def save_json(path: str, data: Any) -> None:
    """Atomically write any JSON-serialisable object to disk.

    Writes to ``path + ".tmp"`` then ``os.replace``s it onto the final
    path so concurrent readers always see a complete file.  NaN/Inf
    floats are scrubbed to ``None`` first so caches contain only valid
    JSON and downstream sorting / templating stays well-behaved.
    """
    tmp_path = f"{path}.tmp"
    try:
        sanitized = _sanitize_for_json(data)
        with open(tmp_path, "w") as f:
            json.dump(sanitized, f, default=str, allow_nan=False)
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


def stamp_alpha_refresh(section: str, extra: dict | None = None) -> None:
    """Record the current EST timestamp for a named alpha section.

    Optional ``extra`` dict is merged into the meta payload so callers
    can record per-section health metrics (counts, populated %, status
    flags) alongside the timestamp.  Keys overwrite any prior value.
    """
    with _meta_lock:
        meta = load_json(CACHE_ALPHA_META, {})
        meta[section] = datetime.now(EST).isoformat()
        if extra:
            meta.update(extra)
        save_json(CACHE_ALPHA_META, meta)


def get_alpha_meta() -> dict:
    """Return the dict of {section: last_refreshed_iso} timestamps."""
    return load_json(CACHE_ALPHA_META, {})
