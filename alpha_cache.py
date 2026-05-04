"""
Alpha cache backed by Postgres with a local-JSON write-through fallback.

Originally this module wrote one JSON file per dataset under the repo
root.  That works fine in a single-process dev container but breaks on
Autoscale deployments, where multiple web instances each get their own
filesystem and a Scheduled Deployment writer can never reach them.

To keep the public surface stable for every alpha module, ``save_json``
and ``load_json`` retain their (path, data) signatures but transparently
upsert/lookup a row in the ``alpha_cache`` table when ``DATABASE_URL``
is configured.  The on-disk JSON file is still written so single-host
dev workflows and offline inspection keep working — but on production
the database is the source of truth.

Concurrency:
* Writers are serialised by the existing ``refresh_lock``.
* Reads are lock-free; the DB upsert is atomic and the local JSON
  write goes through a temp file + ``os.replace`` for atomicity.
* ``stamp_alpha_refresh`` uses a separate ``_meta_lock`` to serialise
  the small read-modify-write of the meta blob.
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
# Protects the small read-modify-write of the meta file/row.
_meta_lock = threading.Lock()

EST = pytz.timezone("US/Eastern")

# ------------------------------------------------------------------
# Cache file paths (also used as DB primary keys via ``_db_key``)
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


# ------------------------------------------------------------------
# DB-backed store (Postgres via SQLAlchemy)
# ------------------------------------------------------------------
def _db_key(path: str) -> str:
    """Use the bare filename as the DB primary key (stable across
    callers, doesn't change if cwd shifts)."""
    return os.path.basename(path)


def _db_available() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


def _db_save(path: str, sanitized: Any) -> bool:
    """Upsert one row in ``alpha_cache``.  Returns True on success."""
    if not _db_available():
        return False
    try:
        # Imported lazily so this module stays importable when models /
        # SQLAlchemy aren't available (e.g. minimal scripts).
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from models import AlphaCache, get_session

        session = get_session()
        try:
            payload = json.dumps(sanitized, default=str, allow_nan=False)
            stmt = pg_insert(AlphaCache.__table__).values(
                key=_db_key(path),
                value=payload,
                updated_at=datetime.utcnow(),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[AlphaCache.key],
                set_={"value": stmt.excluded.value,
                      "updated_at": stmt.excluded.updated_at},
            )
            session.execute(stmt)
            session.commit()
            return True
        finally:
            session.close()
    except Exception as e:
        logger.warning(f"DB cache write for {path} failed: {e}")
        return False


def _db_load(path: str) -> Any | None:
    """Read one row from ``alpha_cache``.  Returns parsed JSON or None."""
    if not _db_available():
        return None
    try:
        from models import AlphaCache, get_session

        session = get_session()
        try:
            row = session.query(AlphaCache).filter(
                AlphaCache.key == _db_key(path)
            ).one_or_none()
            if not row:
                return None
            return json.loads(row.value)
        finally:
            session.close()
    except Exception as e:
        logger.warning(f"DB cache read for {path} failed: {e}")
        return None


def save_json(path: str, data: Any) -> None:
    """Atomically persist a JSON-serialisable object.

    Writes to both the local disk (temp-file + ``os.replace``) and the
    ``alpha_cache`` DB table when ``DATABASE_URL`` is set.  Either path
    failing is logged but does not raise — the goal is that the next
    successful refresh corrects any stale state.
    """
    sanitized = _sanitize_for_json(data)

    # Local disk write (atomic).
    tmp_path = f"{path}.tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(sanitized, f, default=str, allow_nan=False)
        os.replace(tmp_path, path)
    except Exception as e:
        logger.error(f"Failed to write local cache {path}: {e}")
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass

    # DB upsert (best-effort).
    _db_save(path, sanitized)


def load_json(path: str, default: Any) -> Any:
    """Read a cached payload, preferring the freshest source.

    Resolution order:
    1. DB row, if present and ``DATABASE_URL`` is reachable.
    2. Local JSON file on disk.
    3. ``default``.

    The DB takes precedence so a Scheduled Deployment writer's update
    is immediately visible to every Autoscale web instance, even if
    those instances still hold a stale local file from build time.
    """
    db_value = _db_load(path)
    if db_value is not None:
        return db_value
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read local cache {path}: {e}")
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


def seed_db_from_local_files() -> dict[str, bool]:
    """One-shot bootstrap: copy each local cache JSON into the DB.

    Useful right after switching to the DB-backed cache so the first
    page load on production doesn't see empty data while waiting for
    the Scheduled Deployment to fire.  Safe to run repeatedly.
    """
    results: dict[str, bool] = {}
    for path in (
        CACHE_FUNDAMENTALS, CACHE_VALUE, CACHE_RS, CACHE_SETUPS,
        CACHE_REGIME, CACHE_CATALYSTS, CACHE_EDGE, CACHE_BACKTEST,
        CACHE_RVOL, CACHE_ALPHA_META,
    ):
        if not os.path.exists(path):
            results[path] = False
            continue
        try:
            with open(path, "r") as f:
                data = json.load(f)
            results[path] = _db_save(path, _sanitize_for_json(data))
        except Exception as e:
            logger.warning(f"Seed of {path} failed: {e}")
            results[path] = False
    return results
