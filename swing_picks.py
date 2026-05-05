"""
Synthesizes alpha caches into actionable long swing-trade rows.

Reads from:
  - edge_score cache  (ranking, quality, RS, setups, catalysts)
  - setups cache      (price levels: SMA_50, SMA_200, High_52w, RSI_14)
  - backtester cache  (per-signal hit_rate, avg_return)
  - rvol cache        (intraday relative volume)

No network calls, no DB writes — pure cache reads.
"""

from __future__ import annotations

import logging
from typing import Any

from backtester import get_cached_backtest
from edge_score import get_cached_edge_scores
from rvol import get_cached_rvol
from setups import get_cached_setups

logger = logging.getLogger(__name__)

# Highest-conviction setup wins as the "primary" for entry/stop/target derivation
_SETUP_PRIORITY = [
    "trend_pullback",
    "high_52w_breakout",
    "golden_cross",
    "volume_thrust",
    "bullish_rsi_divergence",
]

_ENTRY_TEXT: dict[str, str] = {
    "trend_pullback":         "Buy on close above 50-day SMA",
    "high_52w_breakout":      "Buy on break above 52-week high ({high_52w:.2f})",
    "golden_cross":           "Buy on close above 50-day SMA",
    "volume_thrust":          "Buy on today's close (volume surge confirmed)",
    "bullish_rsi_divergence": "Buy on close above recent swing high",
}


def _stop(setup: str, close: float, sma_200: float | None, high_52w: float | None) -> float:
    """Return a technical stop price for the given setup."""
    if setup in ("trend_pullback", "golden_cross"):
        base = sma_200 if (sma_200 and sma_200 > 0) else close
        return round(base * 0.99, 2)          # 1% below SMA200
    if setup == "high_52w_breakout":
        base = high_52w if (high_52w and high_52w > 0) else close
        return round(base * 0.95, 2)          # 5% below the breakout pivot
    # volume_thrust / bullish_rsi_divergence
    return round(close * 0.97, 2)             # 3% below close


def build_picks(min_edge: int = 60, min_rs: int = 60) -> list[dict[str, Any]]:
    """Return ranked list of actionable long swing-trade candidates.

    Args:
        min_edge: Minimum composite Edge Score (0-100).
        min_rs:   Minimum RS Rating (1-99).

    Returns:
        List of dicts sorted quality-first then edge descending.
    """
    edge_payload = get_cached_edge_scores()
    all_edge_rows = edge_payload.get("rows", [])

    # Setup lookup for price levels not stored in the edge cache
    setup_map = {r.get("Symbol"): r for r in (get_cached_setups() or [])}

    # Backtest lookup by signal name
    bt_map: dict[str, dict] = {}
    for result in (get_cached_backtest().get("results") or []):
        sig = result.get("signal", "")
        if sig:
            bt_map[sig] = result

    rvol_map = get_cached_rvol() or {}

    picks: list[dict[str, Any]] = []

    for edge_row in all_edge_rows:
        edge = edge_row.get("Edge_Score") or 0
        rs = edge_row.get("RS_Rating")
        setups_list: list[str] = edge_row.get("Setups") or []

        if edge < min_edge:
            continue
        if not setups_list:
            continue
        if rs is not None and rs < min_rs:
            continue

        sym = edge_row.get("Symbol")
        sd = setup_map.get(sym, {})

        close = edge_row.get("Close") or sd.get("Close")
        sma_50 = sd.get("SMA_50")
        sma_200 = sd.get("SMA_200")
        high_52w = sd.get("High_52w")

        # Pick the primary setup by priority
        primary = next(
            (s for s in _SETUP_PRIORITY if s in setups_list),
            setups_list[0],
        )

        # Entry text (fill in price placeholder if available)
        entry_tmpl = _ENTRY_TEXT.get(primary, "Buy on close")
        try:
            entry_text = entry_tmpl.format(high_52w=high_52w or 0)
        except (KeyError, TypeError):
            entry_text = entry_tmpl

        # Stop / target
        stop_price = target_price = stop_pct = target_pct = rr = None
        if close and close > 0:
            stop_price = _stop(primary, close, sma_200, high_52w)
            stop_pct = round((close - stop_price) / close * 100, 1)

            bt = bt_map.get(primary)
            avg_ret = bt.get("avg_return") if bt else None

            if avg_ret and avg_ret > 0:
                # Use the historical average, capped at 3× stop distance
                target_pct = round(min(float(avg_ret), stop_pct * 3.0), 1)
            else:
                target_pct = round(stop_pct * 2.0, 1)   # default 2:1 R:R

            target_price = round(close * (1 + target_pct / 100), 2)
            rr = round(target_pct / stop_pct, 1) if stop_pct else None

        bt_stats = bt_map.get(primary)

        # Catalyst label
        parts: list[str] = []
        if edge_row.get("Earnings_Soon") and edge_row.get("Days_To_Earnings") is not None:
            parts.append(f"Earn {edge_row['Days_To_Earnings']}d")
        if edge_row.get("Insider_Buying"):
            parts.append("Insider")
        if edge_row.get("High_Short_Interest"):
            parts.append("Short squeeze")

        rv = rvol_map.get(sym)

        picks.append({
            "Symbol":        sym,
            "Sector":        edge_row.get("Sector") or "—",
            "Edge_Score":    edge,
            "RS_Rating":     rs,
            "Setups":        setups_list,
            "Primary_Setup": primary,
            "Entry_Trigger": entry_text,
            "Close":         round(float(close), 2) if close else None,
            "SMA_50":        round(float(sma_50), 2) if sma_50 else None,
            "SMA_200":       round(float(sma_200), 2) if sma_200 else None,
            "Stop_Level":    stop_price,
            "Stop_Pct":      stop_pct,
            "Target_Price":  target_price,
            "Target_Pct":    target_pct,
            "RR_Ratio":      rr,
            "Hit_Rate":      bt_stats.get("hit_rate") if bt_stats else None,
            "Avg_Return":    bt_stats.get("avg_return") if bt_stats else None,
            "Hold_Days":     bt_stats.get("holding_days", 10) if bt_stats else 10,
            "Catalyst_Flag": " · ".join(parts),
            "Quality_OK":    edge_row.get("Quality_OK", False),
            "RVOL":          round(float(rv["rvol"]), 1) if rv and rv.get("rvol") else None,
        })

    picks.sort(key=lambda r: (0 if r["Quality_OK"] else 1, -(r["Edge_Score"] or 0)))
    return picks
