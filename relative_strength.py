"""
Relative-Strength engine.

For every ticker in the universe we compute return percentiles over
1-month, 3-month, 6-month, and 12-month horizons, ranked against:

    * the broad market (SPY)
    * the stock's own GICS sector ETF

We then synthesise a single 1-99 RS rating in the IBD style: a weighted
blend of the four horizons (12m carries the most weight), percentile-
ranked across the entire universe.

Outputs:
    * Per-ticker rows: returns, vs-market percentiles, vs-sector
      percentiles, and the composite RS rating.
    * Per-sector "rotation" rows: average 1m / 3m return for each
      sector ETF, used by the Sector Rotation view.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable

import numpy as np
import pandas as pd

from alpha_cache import CACHE_RS, EST, load_json, save_json, stamp_alpha_refresh
from price_data import fetch_daily_history
from universe import (
    MARKET_BENCHMARK,
    SECTOR_ETFS,
    get_sector_etf,
    get_sector_map,
    get_universe,
)

logger = logging.getLogger(__name__)


# Trading-day approximations for each horizon.
HORIZONS = {
    "ret_1m": 21,
    "ret_3m": 63,
    "ret_6m": 126,
    "ret_12m": 252,
}

# Weights used to collapse horizon returns into the single RS rating.
# 12-month carries the most weight, mirroring IBD's RS construction.
HORIZON_WEIGHTS = {
    "ret_1m": 0.20,
    "ret_3m": 0.20,
    "ret_6m": 0.20,
    "ret_12m": 0.40,
}


def _periodic_return(closes: pd.Series, n: int) -> float | None:
    if closes is None or len(closes) <= n:
        return None
    try:
        last = float(closes.iloc[-1])
        prev = float(closes.iloc[-n - 1])
        if prev <= 0:
            return None
        return (last / prev - 1.0) * 100.0
    except Exception:
        return None


def _percentile(value: float | None, distribution: Iterable[float]) -> float | None:
    """Percentile of ``value`` within ``distribution`` (0-100)."""
    if value is None:
        return None
    arr = np.array([v for v in distribution if v is not None], dtype=float)
    if arr.size == 0:
        return None
    return float((arr <= value).mean() * 100.0)


def compute_relative_strength() -> dict:
    """Compute RS rows + sector rotation summary."""
    universe = get_universe()
    sector_map = get_sector_map()
    sector_etfs = list(SECTOR_ETFS.values())

    all_tickers = list(dict.fromkeys(universe + [MARKET_BENCHMARK] + sector_etfs))
    bars = fetch_daily_history(all_tickers, period="2y")

    # 1) Compute per-ticker horizon returns.
    rows: list[dict] = []
    for ticker in universe:
        df = bars.get(ticker)
        if df is None or "Close" not in df:
            rows.append({"Symbol": ticker, "Sector": sector_map.get(ticker)})
            continue
        closes = df["Close"].dropna()
        row = {
            "Symbol": ticker,
            "Sector": sector_map.get(ticker),
        }
        for label, n in HORIZONS.items():
            row[label] = _periodic_return(closes, n)
        rows.append(row)

    # 2) Benchmark returns – used to express RS as "stock minus benchmark".
    def _bench_returns(symbol: str) -> dict[str, float | None]:
        df = bars.get(symbol)
        if df is None or "Close" not in df:
            return {label: None for label in HORIZONS}
        closes = df["Close"].dropna()
        return {label: _periodic_return(closes, n) for label, n in HORIZONS.items()}

    market_rets = _bench_returns(MARKET_BENCHMARK)
    sector_rets = {sector: _bench_returns(etf) for sector, etf in SECTOR_ETFS.items()}

    # 3) Universe distributions for percentile ranks.
    universe_dists = {label: [r.get(label) for r in rows] for label in HORIZONS}

    # Pre-compute distributions of vs-market and vs-sector excess returns
    # across the universe so we can convert each stock's excess return
    # into a percentile rank rather than just a raw spread.
    excess_market_dists: dict[str, list[float]] = {label: [] for label in HORIZONS}
    excess_sector_dists: dict[str, dict[str, list[float]]] = {
        label: {sector: [] for sector in SECTOR_ETFS} for label in HORIZONS
    }

    for row in rows:
        sec_rets = sector_rets.get(row.get("Sector") or "", {})
        for label in HORIZONS:
            v = row.get(label)
            m = market_rets.get(label)
            s = sec_rets.get(label)
            if v is not None and m is not None:
                excess_market_dists[label].append(v - m)
            sector = row.get("Sector")
            if v is not None and s is not None and sector in excess_sector_dists[label]:
                excess_sector_dists[label][sector].append(v - s)

    for row in rows:
        sec_rets = sector_rets.get(row.get("Sector") or "", {})
        sector = row.get("Sector")

        for label in HORIZONS:
            v = row.get(label)
            m = market_rets.get(label)
            s = sec_rets.get(label)

            # Excess returns – kept for transparency.
            ex_mkt = (v - m) if (v is not None and m is not None) else None
            ex_sec = (v - s) if (v is not None and s is not None) else None
            row[f"{label}_vs_market"] = round(ex_mkt, 2) if ex_mkt is not None else None
            row[f"{label}_vs_sector"] = round(ex_sec, 2) if ex_sec is not None else None

            # Percentile rank of the excess return within the universe –
            # this is the headline IBD-style "vs SPY" / "vs sector" rank.
            row[f"{label}_pct_vs_market"] = (
                round(p, 1)
                if (p := _percentile(ex_mkt, excess_market_dists[label])) is not None
                else None
            )
            sector_dist = excess_sector_dists[label].get(sector or "", [])
            row[f"{label}_pct_vs_sector"] = (
                round(p, 1)
                if (p := _percentile(ex_sec, sector_dist)) is not None
                else None
            )

            # Universe percentile rank of the raw return – preserved for
            # backwards compatibility / RS rating blend.
            row[f"{label}_pct"] = (
                round(p, 1)
                if (p := _percentile(v, universe_dists[label])) is not None
                else None
            )

        # Round raw returns for display.
        for label in HORIZONS:
            v = row.get(label)
            row[label] = round(v, 2) if v is not None else None

    # 4) Composite RS rating: weighted blend of horizon percentiles, then
    #    percentile-ranked across the universe and scaled 1-99.
    weighted = []
    for row in rows:
        comps = []
        wsum = 0.0
        for label, w in HORIZON_WEIGHTS.items():
            p = row.get(f"{label}_pct")
            if p is not None:
                comps.append(p * w)
                wsum += w
        if comps and wsum > 0:
            row["_blend"] = sum(comps) / wsum
        else:
            row["_blend"] = None
        weighted.append(row.get("_blend"))

    blend_dist = [v for v in weighted if v is not None]
    for row in rows:
        b = row.pop("_blend", None)
        if b is None or not blend_dist:
            row["RS_Rating"] = None
        else:
            pct = (np.array(blend_dist) <= b).mean()
            row["RS_Rating"] = max(1, min(99, int(round(pct * 99))))

    rows.sort(key=lambda r: (r.get("RS_Rating") or -1), reverse=True)

    # 5) Sector rotation: 1m / 3m sector-ETF returns sorted by 3m.
    rotation: list[dict] = []
    for sector, etf in SECTOR_ETFS.items():
        rets = sector_rets.get(sector, {})
        rotation.append(
            {
                "Sector": sector,
                "ETF": etf,
                "Ret_1m": round(rets["ret_1m"], 2) if rets.get("ret_1m") is not None else None,
                "Ret_3m": round(rets["ret_3m"], 2) if rets.get("ret_3m") is not None else None,
                "Ret_6m": round(rets["ret_6m"], 2) if rets.get("ret_6m") is not None else None,
                "Ret_12m": round(rets["ret_12m"], 2) if rets.get("ret_12m") is not None else None,
            }
        )
    rotation.sort(key=lambda r: (r.get("Ret_3m") or -999), reverse=True)

    return {
        "rows": rows,
        "rotation": rotation,
        "market_returns": {k: round(v, 2) if v is not None else None for k, v in market_rets.items()},
    }


def save_relative_strength() -> dict:
    result = compute_relative_strength()
    payload = {
        "as_of": datetime.now(EST).isoformat(),
        **result,
    }
    save_json(CACHE_RS, payload)
    stamp_alpha_refresh("relative_strength")
    logger.info(f"Cached relative strength for {len(result.get('rows', []))} tickers")
    return result


def get_cached_relative_strength() -> dict:
    payload = load_json(CACHE_RS, {})
    if not isinstance(payload, dict):
        return {"rows": [], "rotation": [], "market_returns": {}}
    payload.setdefault("rows", [])
    payload.setdefault("rotation", [])
    payload.setdefault("market_returns", {})
    return payload


def get_rs_rating_map() -> dict[str, int]:
    """Convenience: {ticker: RS_Rating} for stitching into other tables."""
    rs = get_cached_relative_strength()
    return {r["Symbol"]: r.get("RS_Rating") for r in rs.get("rows", []) if r.get("Symbol")}
