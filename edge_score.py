"""
Composite Edge Score & Opportunities ranker.

Combines value, relative strength, technical setups, and catalyst flags
into a single 0-100 Edge Score per ticker.  The Opportunities page
shows the top N candidates ranked by this score with a human-readable
"reason" string explaining why each one is in the list.

Component weights (tunable in one place):

    * Value (sector-relative cheapness percentile)        : 30%
    * Relative Strength (universe percentile)             : 30%
    * Technical setup match (per-setup bonus, capped 100) : 25%
    * Catalysts (earnings soon / insider buying / short)  : 15%

Stocks that fail the value-screen quality gate are not eligible for
the top-of-list ranking even if they score well technically.
"""

from __future__ import annotations

import logging
from datetime import datetime

from alpha_cache import CACHE_EDGE, EST, load_json, save_json, stamp_alpha_refresh
from catalysts import get_catalyst_map
from relative_strength import get_cached_relative_strength
from setups import get_setup_map
from value_screener import get_cached_value_screen

logger = logging.getLogger(__name__)


WEIGHTS = {
    "value": 0.30,
    "rs": 0.30,
    "setup": 0.25,
    "catalyst": 0.15,
}

# Per-setup contribution to the technical score (0-100 cap).
SETUP_POINTS = {
    "trend_pullback": 35,
    "high_52w_breakout": 30,
    "volume_thrust": 20,
    "golden_cross": 25,
    "bullish_rsi_divergence": 20,
}

# Per-catalyst contribution (0-100 cap).
CATALYST_POINTS = {
    "insider_buying_30d_plus": 50,
    "earnings_within_14d": 25,
    "high_short_interest": 25,
}


def _setup_score(setup_row: dict | None) -> tuple[int, list[str]]:
    if not setup_row:
        return 0, []
    pts = 0
    reasons = []
    for name, weight in SETUP_POINTS.items():
        if setup_row.get(name):
            pts += weight
            reasons.append(name)
    return min(pts, 100), reasons


def _catalyst_score(cat_row: dict | None) -> tuple[int, list[str]]:
    if not cat_row:
        return 0, []
    pts = 0
    reasons = []
    for name, weight in CATALYST_POINTS.items():
        if cat_row.get(name):
            pts += weight
            reasons.append(name)
    return min(pts, 100), reasons


_REASON_LABELS = {
    "trend_pullback": "trend pullback",
    "high_52w_breakout": "52w breakout",
    "volume_thrust": "volume thrust",
    "golden_cross": "golden cross",
    "bullish_rsi_divergence": "RSI divergence",
    "insider_buying_30d_plus": "insider buying",
    "earnings_within_14d": "earnings <14d",
    "high_short_interest": "high short interest",
    "value": "cheap vs sector",
    "rs": "strong RS",
}


def compute_edge_scores(top_n: int = 25) -> dict:
    """Compute Edge Scores using fixed weights – no dynamic reweighting.

    Earlier versions normalised by the sum of *available* component
    weights, which silently upweighted setups & catalysts when value
    or RS data was missing.  We now treat missing components as a
    zero contribution so that a stock with no value/RS data simply
    can't reach the same total as one that does, which matches user
    expectations and keeps the published weights honest.
    """
    value_rows = get_cached_value_screen()
    rs_payload = get_cached_relative_strength()
    setup_map = get_setup_map()
    cat_map = get_catalyst_map()

    rs_map = {r["Symbol"]: r for r in rs_payload.get("rows", []) if r.get("Symbol")}
    value_map = {r["Symbol"]: r for r in value_rows if r.get("Symbol")}

    all_symbols = set(value_map) | set(rs_map) | set(setup_map) | set(cat_map)

    rows: list[dict] = []
    for symbol in all_symbols:
        v = value_map.get(symbol, {})
        r = rs_map.get(symbol, {})
        s = setup_map.get(symbol)
        c = cat_map.get(symbol)

        value_pct = v.get("Value_Score")  # 0-100 already
        rs_rating = r.get("RS_Rating")    # 1-99
        setup_pts, setup_reasons = _setup_score(s)
        catalyst_pts, catalyst_reasons = _catalyst_score(c)

        # Fixed-weight composite.  Missing components contribute zero
        # (they don't get reweighted), so the score is comparable
        # across stocks regardless of data completeness.
        edge = (
            (value_pct or 0) * WEIGHTS["value"]
            + (rs_rating or 0) * WEIGHTS["rs"]
            + setup_pts * WEIGHTS["setup"]
            + catalyst_pts * WEIGHTS["catalyst"]
        )

        # Build reason string.
        reasons: list[str] = []
        if value_pct is not None and value_pct >= 70:
            reasons.append(_REASON_LABELS["value"])
        if rs_rating is not None and rs_rating >= 80:
            reasons.append(_REASON_LABELS["rs"])
        for name in setup_reasons:
            reasons.append(_REASON_LABELS.get(name, name))
        for name in catalyst_reasons:
            reasons.append(_REASON_LABELS.get(name, name))

        # Quality gate: a stock with no value-row at all hasn't passed
        # the quality check – default to False rather than True so we
        # don't silently let no-data names rank as "quality ok".
        if "Quality_OK" in v:
            quality_ok = bool(v.get("Quality_OK"))
        else:
            quality_ok = False

        rows.append(
            {
                "Symbol": symbol,
                "Sector": v.get("Sector") or r.get("Sector") or (s or {}).get("Sector"),
                "Edge_Score": round(edge, 1),
                "Value_Score": value_pct,
                "RS_Rating": rs_rating,
                "Setup_Count": (s or {}).get("Setup_Count", 0),
                "Setups": (s or {}).get("Setups", []),
                "Quality_OK": quality_ok,
                "Reason": ", ".join(reasons) if reasons else "no strong signal",
                "Close": (s or {}).get("Close"),
                "Pct_From_52w_High": (s or {}).get("Pct_From_52w_High"),
                "Next_Earnings": (c or {}).get("next_earnings_date"),
                "Days_To_Earnings": (c or {}).get("days_to_earnings"),
                "Earnings_Soon": bool((c or {}).get("earnings_within_14d")),
                "Insider_Buying": bool((c or {}).get("insider_buying_30d_plus")),
                "High_Short_Interest": bool((c or {}).get("high_short_interest")),
            }
        )

    # Sort: quality first, then edge score.
    rows.sort(
        key=lambda r: (
            1 if r.get("Quality_OK") else 0,
            r.get("Edge_Score") or 0,
        ),
        reverse=True,
    )

    return {
        "rows": rows,
        "top": rows[:top_n],
    }


def save_edge_scores() -> dict:
    result = compute_edge_scores()
    payload = {"as_of": datetime.now(EST).isoformat(), **result}
    save_json(CACHE_EDGE, payload)
    stamp_alpha_refresh("edge")
    logger.info(f"Cached edge scores for {len(result.get('rows', []))} tickers")
    return result


def get_cached_edge_scores() -> dict:
    payload = load_json(CACHE_EDGE, {})
    if not isinstance(payload, dict):
        return {"rows": [], "top": []}
    payload.setdefault("rows", [])
    payload.setdefault("top", [])
    return payload
