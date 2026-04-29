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

        cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=90)
        df = df[df["Date"].dt.tz_localize(None) >= cutoff]

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
    rows = compute_catalysts()
    payload = {"as_of": datetime.now(EST).isoformat(), "rows": rows}
    save_json(CACHE_CATALYSTS, payload)
    stamp_alpha_refresh("catalysts")
    logger.info(f"Cached catalysts for {len(rows)} tickers")
    return rows


def get_cached_catalysts() -> list[dict]:
    payload = load_json(CACHE_CATALYSTS, {})
    if isinstance(payload, dict):
        return payload.get("rows", [])
    return []


def get_catalyst_map() -> dict[str, dict]:
    return {r["Symbol"]: r for r in get_cached_catalysts() if r.get("Symbol")}
