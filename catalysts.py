"""
Catalyst layer: upcoming earnings, recent insider transactions,
and short-interest snapshots for every ticker in the universe.

Surfaced as a column on the Opportunities table and as a standalone
/catalysts page so the user can filter for "anything with insider
buying" or "earnings in the next 7 days".

yfinance exposes:
    * Ticker.calendar              – next earnings date
    * Ticker.insider_transactions  – recent Form 4 filings
    * Ticker.info[shortPercentOfFloat] – short interest snapshot

Each lookup is wrapped in a try/except so a single Yahoo hiccup never
breaks the whole refresh.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pandas as pd
import pytz
import yfinance as yf

from alpha_cache import CACHE_CATALYSTS, EST, load_json, save_json, stamp_alpha_refresh
from fundamentals import get_cached_fundamentals
from universe import get_universe

logger = logging.getLogger(__name__)


def _next_earnings_date(ticker: yf.Ticker) -> str | None:
    """Best-effort extraction of the next earnings date as ISO yyyy-mm-dd."""
    try:
        cal = ticker.calendar
        if cal is None:
            return None
        # Newer yfinance returns a dict; older returns a DataFrame.
        if isinstance(cal, dict):
            d = cal.get("Earnings Date")
            if isinstance(d, list) and d:
                d = d[0]
            if d is not None:
                return pd.Timestamp(d).strftime("%Y-%m-%d")
        elif isinstance(cal, pd.DataFrame) and "Earnings Date" in cal.index:
            v = cal.loc["Earnings Date"]
            if hasattr(v, "iloc"):
                v = v.iloc[0]
            return pd.Timestamp(v).strftime("%Y-%m-%d")
    except Exception:
        return None
    return None


def _insider_summary(ticker: yf.Ticker) -> dict:
    """Net insider activity in the last 90 days (count + net dollar value)."""
    try:
        df = ticker.insider_transactions
        if df is None or len(df) == 0:
            return {"insider_buys_90d": 0, "insider_sells_90d": 0, "insider_net_value_90d": 0.0}
        df = df.copy()
        if "Start Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Start Date"], errors="coerce")
        elif "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        else:
            return {"insider_buys_90d": 0, "insider_sells_90d": 0, "insider_net_value_90d": 0.0}

        # Normalize timezone safely: yfinance can return either tz-aware
        # or tz-naive datetimes depending on cache state, so we strip
        # the timezone only if one is present.  The cutoff is computed
        # tz-naive on both sides to avoid mixed-tz comparison errors.
        cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=90)
        if df["Date"].dt.tz is not None:
            df["Date"] = df["Date"].dt.tz_convert("UTC").dt.tz_localize(None)
        df = df[df["Date"].notna() & (df["Date"] >= cutoff)]

        buys = sells = 0
        net_value = 0.0
        if "Transaction" in df.columns:
            buys = int(
                df["Transaction"]
                .astype(str)
                .str.contains("Purchase|Buy", case=False, regex=True, na=False)
                .sum()
            )
            sells = int(
                df["Transaction"]
                .astype(str)
                .str.contains("Sale|Sell", case=False, regex=True, na=False)
                .sum()
            )
        if "Value" in df.columns:
            vals = pd.to_numeric(df["Value"], errors="coerce").fillna(0.0)
            if "Transaction" in df.columns:
                signed = vals.where(
                    df["Transaction"]
                    .astype(str)
                    .str.contains("Purchase|Buy", case=False, regex=True, na=False),
                    -vals,
                )
                net_value = float(signed.sum())
            else:
                net_value = float(vals.sum())

        return {
            "insider_buys_90d": buys,
            "insider_sells_90d": sells,
            "insider_net_value_90d": round(net_value, 0),
        }
    except Exception:
        return {"insider_buys_90d": 0, "insider_sells_90d": 0, "insider_net_value_90d": 0.0}


def compute_catalysts() -> list[dict]:
    fundamentals_by_symbol = {r["Symbol"]: r for r in get_cached_fundamentals()}
    today = datetime.now(EST).date()

    rows: list[dict] = []
    for symbol in get_universe():
        try:
            t = yf.Ticker(symbol)
        except Exception:
            t = None

        next_earn = _next_earnings_date(t) if t is not None else None
        days_to_earn = None
        if next_earn:
            try:
                days_to_earn = (datetime.strptime(next_earn, "%Y-%m-%d").date() - today).days
            except Exception:
                days_to_earn = None

        insider = _insider_summary(t) if t is not None else {
            "insider_buys_90d": 0,
            "insider_sells_90d": 0,
            "insider_net_value_90d": 0.0,
        }

        f = fundamentals_by_symbol.get(symbol, {})
        short_pct = f.get("shortPercentOfFloat")
        if short_pct is not None:
            short_pct = round(float(short_pct) * 100, 2)

        rows.append(
            {
                "Symbol": symbol,
                "next_earnings_date": next_earn,
                "days_to_earnings": days_to_earn,
                "earnings_within_14d": (days_to_earn is not None and 0 <= days_to_earn <= 14),
                "short_pct_float": short_pct,
                "high_short_interest": (short_pct is not None and short_pct >= 15),
                **insider,
                "insider_buying_30d_plus": insider["insider_net_value_90d"] > 0
                and insider["insider_buys_90d"] > insider["insider_sells_90d"],
            }
        )
    return rows


def save_catalysts() -> list[dict]:
    """Refresh catalysts and persist to cache.

    yfinance's ``Ticker.calendar`` and ``Ticker.insider_transactions``
    endpoints route through Yahoo's anonymous quoteSummary API, which
    aggressively rate-limits at our universe size (~280 tickers × 2
    endpoints).  When the run is rate-limited every row comes back with
    no earnings date and no insider activity.  In that case we keep the
    previous cache rather than overwriting good data with zeros, and
    stamp a health metric into ``cached_alpha_meta`` so the degraded
    state is visible.
    """
    rows = compute_catalysts()
    with_earnings = sum(1 for r in rows if r.get("next_earnings_date"))
    with_insider = sum(
        1
        for r in rows
        if (r.get("insider_buys_90d", 0) or r.get("insider_sells_90d", 0))
    )
    n = max(1, len(rows))
    health = {
        "catalysts_total": len(rows),
        "catalysts_with_earnings": with_earnings,
        "catalysts_with_insider": with_insider,
        "catalysts_earnings_pct": round(100 * with_earnings / n, 1),
        "catalysts_insider_pct": round(100 * with_insider / n, 1),
    }

    if with_earnings == 0 and with_insider == 0:
        prior = load_json(CACHE_CATALYSTS, {})
        prior_rows = prior.get("rows", []) if isinstance(prior, dict) else []
        prior_with_data = sum(
            1
            for r in prior_rows
            if r.get("next_earnings_date")
            or r.get("insider_buys_90d")
            or r.get("insider_sells_90d")
        )
        if prior_with_data > 0:
            logger.warning(
                "Catalyst refresh appears rate-limited (0 earnings / 0 insider "
                "records across %d tickers); keeping previous cache with %d "
                "populated rows.",
                len(rows),
                prior_with_data,
            )
            stamp_alpha_refresh("catalysts", extra={**health, "catalysts_status": "rate_limited_kept_prior"})
            return prior_rows
        logger.warning(
            "Catalyst refresh returned no earnings or insider data for %d "
            "tickers (likely Yahoo rate limit); short interest still populated "
            "from cached fundamentals.",
            len(rows),
        )
        health["catalysts_status"] = "rate_limited_no_prior"
    else:
        health["catalysts_status"] = "ok"

    payload = {"as_of": datetime.now(EST).isoformat(), "rows": rows}
    save_json(CACHE_CATALYSTS, payload)
    stamp_alpha_refresh("catalysts", extra=health)
    logger.info(
        "Cached catalysts for %d tickers (earnings: %d, insider: %d)",
        len(rows),
        with_earnings,
        with_insider,
    )
    return rows


def get_cached_catalysts() -> list[dict]:
    payload = load_json(CACHE_CATALYSTS, {})
    if isinstance(payload, dict):
        return payload.get("rows", [])
    return []


def get_catalyst_map() -> dict[str, dict]:
    return {r["Symbol"]: r for r in get_cached_catalysts() if r.get("Symbol")}
