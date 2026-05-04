"""
Cumulative / Time-adjusted Relative Volume (RVOL) snapshot.

For every ticker in the universe we compute:

    rvol = today's cumulative volume so far
           / average cumulative volume up to the same time-of-day
             across the previous N trading days

This is the "right" intraday RVOL.  The naive form
``today_full_vol / avg_daily_vol`` is misleading early in the session
because volume is back-loaded around the open and close.  The
time-adjusted version answers the only question that matters
mid-session: "is this stock trading more than usual *for this point
in the day*?"

The snapshot is refreshed every 15 minutes during US market hours
(see ``scheduler.py``) and cached on disk so the /setups page can
join it onto the existing daily-bar setup rows without re-fetching.
"""

from __future__ import annotations

import logging
from datetime import datetime, time as dtime

import pandas as pd
import yfinance as yf

from alpha_cache import (
    CACHE_RVOL,
    EST,
    load_json,
    save_json,
    stamp_alpha_refresh,
)
from universe import get_universe

logger = logging.getLogger(__name__)

# Trailing trading days used to build the time-of-day baseline.
BASELINE_DAYS = 20
# yfinance permits 15-minute intraday bars going back ~60 days, which
# easily covers BASELINE_DAYS + today even after holidays.
INTRADAY_INTERVAL = "15m"
INTRADAY_PERIOD = "60d"
# Regular US equity session.
MARKET_OPEN = dtime(9, 30)
MARKET_CLOSE = dtime(16, 0)
SESSION_MINUTES = 6.5 * 60  # 390


def is_market_hours(now_est: datetime | None = None) -> bool:
    """True on Mon-Fri between 09:30 and 16:00 US/Eastern."""
    now_est = now_est or datetime.now(EST)
    if now_est.weekday() >= 5:
        return False
    t = now_est.time()
    return MARKET_OPEN <= t <= MARKET_CLOSE


def _per_ticker_rvol(df: pd.DataFrame, today: pd.Timestamp) -> dict | None:
    """Compute time-adjusted RVOL for one ticker's 15m bar frame."""
    if df is None or df.empty or "Volume" not in df or "Close" not in df:
        return None

    df = df.dropna(subset=["Volume", "Close"]).copy()
    if df.empty:
        return None

    # Normalise the index to tz-aware US/Eastern so .time() comparisons
    # are session-relative and not UTC-shifted.
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(EST)
    else:
        df.index = df.index.tz_convert(EST)

    # Restrict to regular-hours bars only — pre/post bars distort the
    # time-of-day baseline.
    times = df.index.time
    in_session = pd.Series(
        [(MARKET_OPEN <= t < MARKET_CLOSE) for t in times], index=df.index
    )
    df = df[in_session.values]
    if df.empty:
        return None

    session_dates = pd.Series([d.date() for d in df.index], index=df.index)
    bar_times = pd.Series([d.time() for d in df.index], index=df.index)

    today_mask = session_dates.values == today.date()
    today_df = df[today_mask]
    if today_df.empty:
        return None

    cur_time = bar_times[today_mask].max()
    cur_price = float(today_df["Close"].iloc[-1])
    today_cum = float(today_df["Volume"].sum())

    # Baseline: for each prior day take volume of bars whose time-of-day
    # is <= the latest bar we have today, then average across the last
    # ``BASELINE_DAYS`` such days.
    prior_mask = (~today_mask) & (bar_times.values <= cur_time)
    prior_df = df[prior_mask]
    if prior_df.empty:
        return None

    prior_dates = session_dates[prior_mask]
    cum_by_day = prior_df["Volume"].groupby(prior_dates.values).sum()
    cum_by_day = cum_by_day.tail(BASELINE_DAYS)
    if len(cum_by_day) < 5:
        return None
    avg_cum = float(cum_by_day.mean())
    if avg_cum <= 0:
        return None

    rvol = today_cum / avg_cum

    minutes_elapsed = (
        datetime.combine(datetime.today(), cur_time)
        - datetime.combine(datetime.today(), MARKET_OPEN)
    ).total_seconds() / 60.0
    pct_session = max(0.0, min(1.0, minutes_elapsed / SESSION_MINUTES))

    return {
        "rvol": round(rvol, 2),
        "cum_volume": int(today_cum),
        "avg_cum_volume": int(avg_cum),
        "dollar_volume": int(today_cum * cur_price),
        "pct_of_session": round(pct_session, 3),
        "as_of_bar": cur_time.strftime("%H:%M"),
        "current_price": round(cur_price, 2),
    }


def compute_rvol_snapshot() -> dict[str, dict]:
    """Fetch 15m bars for the whole universe and compute RVOL per ticker."""
    universe = get_universe()
    if not universe:
        return {}

    now_est = datetime.now(EST)
    today = pd.Timestamp(now_est.date())

    try:
        raw = yf.download(
            tickers=" ".join(universe),
            period=INTRADAY_PERIOD,
            interval=INTRADAY_INTERVAL,
            group_by="ticker",
            auto_adjust=False,
            prepost=False,
            progress=False,
            threads=True,
        )
    except Exception as e:
        logger.error(f"Bulk RVOL download failed: {e}")
        return {}

    if raw is None or raw.empty:
        return {}

    out: dict[str, dict] = {}
    if isinstance(raw.columns, pd.MultiIndex):
        top_level = set(raw.columns.get_level_values(0))
        for t in universe:
            if t not in top_level:
                continue
            try:
                sub = raw[t].dropna(how="all")
                res = _per_ticker_rvol(sub, today)
                if res is not None:
                    out[t] = res
            except Exception as e:
                logger.warning(f"RVOL eval failed for {t}: {e}")
    else:
        # Single-ticker fall-through.
        try:
            res = _per_ticker_rvol(raw, today)
            if res is not None:
                out[universe[0]] = res
        except Exception as e:
            logger.warning(f"RVOL eval failed for {universe[0]}: {e}")

    return out


def save_rvol_snapshot(force: bool = False) -> dict[str, dict]:
    """Refresh and persist the RVOL snapshot.

    Skips during off-hours unless ``force=True`` so the 15-minute
    scheduler tick is cheap on weekends and overnight.
    """
    now_est = datetime.now(EST)
    if not force and not is_market_hours(now_est):
        logger.debug("RVOL: outside market hours, skipping refresh")
        return get_cached_rvol()

    snap = compute_rvol_snapshot()

    # If the snapshot is empty (transient yfinance failure, exchange
    # holiday that slipped past the weekday/time guard, or simply no
    # intraday bars yet) and we already have a prior good cache, keep
    # the prior cache rather than overwriting the page with blanks.
    if not snap:
        prior = get_cached_rvol()
        if prior:
            logger.warning(
                "RVOL refresh produced 0 tickers; keeping previous cache "
                "(%d tickers) untouched.", len(prior),
            )
            stamp_alpha_refresh(
                "rvol",
                extra={"rvol_count": len(prior), "rvol_last_status": "empty_skipped"},
            )
            return prior

    payload = {
        "as_of": now_est.isoformat(),
        "rows": snap,
    }
    save_json(CACHE_RVOL, payload)
    stamp_alpha_refresh(
        "rvol",
        extra={"rvol_count": len(snap), "rvol_last_status": "ok" if snap else "empty"},
    )
    logger.info(f"RVOL refresh: {len(snap)} tickers as of {now_est.isoformat()}")
    return snap


def get_cached_rvol() -> dict[str, dict]:
    """Return ``{symbol: rvol_row}`` from the cached snapshot."""
    payload = load_json(CACHE_RVOL, {})
    if isinstance(payload, dict):
        rows = payload.get("rows", {})
        if isinstance(rows, dict):
            return rows
    return {}


def get_cached_rvol_meta() -> dict:
    """Return ``{as_of: iso}`` (or empty) for the cached snapshot."""
    payload = load_json(CACHE_RVOL, {})
    if isinstance(payload, dict):
        return {"as_of": payload.get("as_of")}
    return {}
