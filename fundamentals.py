"""
Fundamentals snapshot fetcher & cache.

Pulls valuation, profitability, growth and balance-sheet ratios for every
ticker in the universe via ``yfinance.Ticker(t).info`` and writes a single
JSON cache that downstream screeners load in O(1).

This is the one slow step in the alpha pipeline (yfinance has to make a
network round-trip per ticker for ``.info``).  It is run nightly by the
scheduler and on-demand from the dashboard's "Refresh alpha data" button.

Each cached row has a small, stable shape so the value screener and
edge-score modules can rely on it without re-asking yfinance.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import yfinance as yf

from alpha_cache import CACHE_FUNDAMENTALS, EST, load_json, save_json, stamp_alpha_refresh
from universe import get_sector_map, get_universe

logger = logging.getLogger(__name__)


# Fields we attempt to pull from yfinance .info.  We tolerate missing keys
# – every metric is ``None`` if absent so consumers can filter cleanly.
_FIELDS_NUMERIC = (
    "trailingPE",
    "forwardPE",
    "priceToBook",
    "priceToSalesTrailing12Months",
    "enterpriseToEbitda",
    "enterpriseToRevenue",
    "pegRatio",
    "dividendYield",
    "marketCap",
    "freeCashflow",
    "operatingCashflow",
    "totalRevenue",
    "ebitda",
    "returnOnEquity",
    "returnOnAssets",
    "profitMargins",
    "operatingMargins",
    "grossMargins",
    "debtToEquity",
    "currentRatio",
    "quickRatio",
    "earningsGrowth",
    "revenueGrowth",
    "shortPercentOfFloat",
    "shortRatio",
    "fiftyTwoWeekHigh",
    "fiftyTwoWeekLow",
    "beta",
)


def _safe_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        f = float(v)
        if f != f:  # NaN check
            return None
        return f
    except (TypeError, ValueError):
        return None


def _fcf_yield(info: dict) -> float | None:
    """FCF / Market Cap, expressed as a decimal (0.05 = 5%)."""
    fcf = _safe_float(info.get("freeCashflow"))
    mc = _safe_float(info.get("marketCap"))
    if fcf is None or mc is None or mc <= 0:
        return None
    return fcf / mc


def fetch_fundamentals_snapshot() -> list[dict]:
    """Fetch a fundamentals snapshot for every ticker in the universe."""
    sector_map = get_sector_map()
    rows: list[dict] = []

    for ticker in get_universe():
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception as e:
            logger.warning(f"Fundamentals lookup failed for {ticker}: {e}")
            info = {}

        row: dict[str, Any] = {
            "Symbol": ticker,
            "Sector": sector_map.get(ticker) or info.get("sector") or "Unknown",
            "FCF_Yield": _fcf_yield(info),
        }
        for field in _FIELDS_NUMERIC:
            row[field] = _safe_float(info.get(field))
        rows.append(row)

    return rows


def save_fundamentals() -> list[dict]:
    """Refresh and cache the fundamentals snapshot. Returns the new rows."""
    logger.info("Refreshing fundamentals snapshot...")
    rows = fetch_fundamentals_snapshot()
    payload = {
        "as_of": datetime.now(EST).isoformat(),
        "rows": rows,
    }
    save_json(CACHE_FUNDAMENTALS, payload)
    stamp_alpha_refresh("fundamentals")
    logger.info(f"Cached fundamentals for {len(rows)} tickers")
    return rows


def get_cached_fundamentals() -> list[dict]:
    payload = load_json(CACHE_FUNDAMENTALS, {})
    if isinstance(payload, dict):
        return payload.get("rows", [])
    return []


def get_fundamentals_as_of() -> str | None:
    payload = load_json(CACHE_FUNDAMENTALS, {})
    if isinstance(payload, dict):
        return payload.get("as_of")
    return None
