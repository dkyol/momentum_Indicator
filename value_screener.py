"""
Sector-relative value & quality screener.

Combines five valuation ratios into a single percentile-based "cheapness"
score per sector, gated by a quality filter.  The output is the table
that backs the /value page and feeds the composite Edge Score.

Cheapness score (0-100, higher = cheaper than peers in same sector):
  * P/E (trailing)           – lower is better
  * P/B                      – lower is better
  * P/S                      – lower is better
  * EV/EBITDA                – lower is better
  * FCF yield                – higher is better (so we percentile-rank ascending and invert)

Quality gate (a stock is flagged ``passes_quality`` only if all are true):
  * Free cash flow > 0
  * Debt/Equity < 200 (yfinance reports this as a percentage)
  * Revenue growth >= 0  *or* missing (don't punish for unreported)

Stocks failing the quality gate still appear in the screen but their
``Quality_OK`` flag is False so the dashboard can grey them out and the
Edge Score skips them.
"""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from alpha_cache import CACHE_VALUE, EST, load_json, save_json, stamp_alpha_refresh
from fundamentals import get_cached_fundamentals

logger = logging.getLogger(__name__)


# (column in fundamentals row, lower-is-cheaper?) for the value composite.
_VALUE_METRICS = (
    ("trailingPE", True),
    ("priceToBook", True),
    ("priceToSalesTrailing12Months", True),
    ("enterpriseToEbitda", True),
    ("FCF_Yield", False),  # higher yield = cheaper
)


def _passes_quality(row: dict) -> bool:
    fcf = row.get("freeCashflow")
    de = row.get("debtToEquity")
    rev_growth = row.get("revenueGrowth")
    if fcf is not None and fcf <= 0:
        return False
    if de is not None and de > 200:
        return False
    if rev_growth is not None and rev_growth < 0:
        return False
    return True


def compute_value_screen() -> list[dict]:
    """Compute the sector-relative value composite.

    Returns a list of dicts, one per ticker, sorted by composite score
    descending (cheapest first).  Stocks lacking fundamentals data are
    included but with ``Value_Score = None`` so the UI can flag them.
    """
    rows = get_cached_fundamentals()
    if not rows:
        return []

    df = pd.DataFrame(rows)
    if df.empty:
        return []

    # Per-metric per-sector percentile rank.
    metric_ranks: dict[str, pd.Series] = {}
    for col, lower_is_cheaper in _VALUE_METRICS:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        # For lower-is-better metrics we use ascending=True so that the
        # cheapest gets the lowest pct rank, then invert (1 - rank) so
        # cheapest -> 1.0.  For higher-is-better (FCF yield) we do the
        # opposite.
        ranked = series.groupby(df["Sector"]).rank(pct=True)
        if lower_is_cheaper:
            ranked = 1 - ranked
        metric_ranks[col] = ranked

    if not metric_ranks:
        return []

    rank_df = pd.DataFrame(metric_ranks)
    # Composite = average of available metric ranks (skipna so we don't
    # punish a stock whose P/E is undefined because earnings are negative).
    composite = rank_df.mean(axis=1, skipna=True) * 100
    df["Value_Score"] = composite.round(1)

    df["Quality_OK"] = df.apply(lambda r: _passes_quality(r.to_dict()), axis=1)

    # Sort by score descending, NaN composites at the bottom.
    df = df.sort_values("Value_Score", ascending=False, na_position="last")

    out_cols = [
        "Symbol",
        "Sector",
        "trailingPE",
        "priceToBook",
        "priceToSalesTrailing12Months",
        "enterpriseToEbitda",
        "FCF_Yield",
        "debtToEquity",
        "revenueGrowth",
        "earningsGrowth",
        "marketCap",
        "Value_Score",
        "Quality_OK",
    ]
    out_cols = [c for c in out_cols if c in df.columns]

    out = df[out_cols].copy()
    # Replace NaN with None for JSON serialisation.
    out = out.where(pd.notna(out), None)

    return out.to_dict("records")


def save_value_screen() -> list[dict]:
    rows = compute_value_screen()
    payload = {
        "as_of": datetime.now(EST).isoformat(),
        "rows": rows,
    }
    save_json(CACHE_VALUE, payload)
    stamp_alpha_refresh("value")
    logger.info(f"Cached value screen for {len(rows)} tickers")
    return rows


def get_cached_value_screen() -> list[dict]:
    payload = load_json(CACHE_VALUE, {})
    if isinstance(payload, dict):
        return payload.get("rows", [])
    return []
