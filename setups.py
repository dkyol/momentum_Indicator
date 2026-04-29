"""
Bullish technical setup detector.

Scans daily bars for every ticker in the universe and flags concrete,
named patterns that historically precede above-average returns.  The
output is the table that backs the /setups page and feeds the composite
Edge Score.

Detected setups (each is a separate boolean flag on the row):

* ``trend_pullback``      – Above 200d SMA, RSI(14) < 40, within 5% of 50d SMA
* ``high_52w_breakout``   – Close within 2% of, or above, the 52-week high
* ``volume_thrust``       – Today's volume > 2x 20-day avg AND close up
* ``golden_cross``        – 50d SMA crossed above 200d SMA in the last 5 days
* ``bullish_rsi_divergence`` – Price made a lower low in the last 20 days
                              while RSI made a higher low
"""

from __future__ import annotations

import logging
from datetime import datetime

import numpy as np
import pandas as pd

from alpha_cache import CACHE_SETUPS, EST, load_json, save_json, stamp_alpha_refresh
from price_data import fetch_daily_history
from universe import get_sector_map, get_universe

logger = logging.getLogger(__name__)


def _rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _evaluate(df: pd.DataFrame) -> dict | None:
    """Evaluate the setups for one stock.  Returns None if data is too short."""
    if df is None or len(df) < 220 or "Close" not in df:
        return None

    closes = df["Close"].dropna()
    volumes = df["Volume"].dropna() if "Volume" in df else pd.Series(dtype=float)

    if len(closes) < 220:
        return None

    sma_50 = closes.rolling(50).mean()
    sma_200 = closes.rolling(200).mean()
    rsi = _rsi(closes, 14)
    high_52w = closes.rolling(252, min_periods=200).max()

    last = closes.iloc[-1]
    last_50 = sma_50.iloc[-1]
    last_200 = sma_200.iloc[-1]
    last_rsi = rsi.iloc[-1]
    last_52w = high_52w.iloc[-1]

    # --- trend pullback ---
    trend_pullback = (
        not pd.isna(last_50)
        and not pd.isna(last_200)
        and not pd.isna(last_rsi)
        and last > last_200
        and last_rsi < 40
        and abs(last - last_50) / last_50 < 0.05
    )

    # --- 52-week high breakout ---
    high_52w_breakout = (
        not pd.isna(last_52w) and last >= last_52w * 0.98
    )

    # --- volume thrust ---
    volume_thrust = False
    if len(volumes) >= 21:
        avg_vol_20 = float(volumes.tail(20).mean())
        last_vol = float(volumes.iloc[-1])
        prev_close = float(closes.iloc[-2])
        volume_thrust = (
            avg_vol_20 > 0
            and last_vol > 2 * avg_vol_20
            and last > prev_close
        )

    # --- golden cross in the last 5 days ---
    golden_cross = False
    if len(sma_50) >= 6 and len(sma_200) >= 6:
        diff = sma_50.tail(6) - sma_200.tail(6)
        signs = np.sign(diff.dropna())
        if len(signs) >= 2 and signs.iloc[0] <= 0 and signs.iloc[-1] > 0:
            golden_cross = True

    # --- bullish RSI divergence (last 20 sessions) ---
    bullish_rsi_divergence = False
    if len(closes) >= 20 and len(rsi.dropna()) >= 20:
        recent_close = closes.tail(20)
        recent_rsi = rsi.tail(20)
        # Find the index of the lowest close in first half vs second half.
        first_half_low_close = recent_close.iloc[:10].min()
        second_half_low_close = recent_close.iloc[10:].min()
        first_half_low_rsi = recent_rsi.iloc[:10].min()
        second_half_low_rsi = recent_rsi.iloc[10:].min()
        if (
            second_half_low_close < first_half_low_close
            and second_half_low_rsi > first_half_low_rsi
        ):
            bullish_rsi_divergence = True

    flags = {
        "trend_pullback": bool(trend_pullback),
        "high_52w_breakout": bool(high_52w_breakout),
        "volume_thrust": bool(volume_thrust),
        "golden_cross": bool(golden_cross),
        "bullish_rsi_divergence": bool(bullish_rsi_divergence),
    }
    triggered = [name for name, v in flags.items() if v]

    return {
        "Close": round(float(last), 2),
        "SMA_50": round(float(last_50), 2) if not pd.isna(last_50) else None,
        "SMA_200": round(float(last_200), 2) if not pd.isna(last_200) else None,
        "RSI_14": round(float(last_rsi), 1) if not pd.isna(last_rsi) else None,
        "High_52w": round(float(last_52w), 2) if not pd.isna(last_52w) else None,
        "Pct_From_52w_High": (
            round((float(last) / float(last_52w) - 1.0) * 100.0, 2)
            if not pd.isna(last_52w) and last_52w > 0
            else None
        ),
        **flags,
        "Setup_Count": len(triggered),
        "Setups": triggered,
    }


def compute_setups() -> list[dict]:
    universe = get_universe()
    sector_map = get_sector_map()
    bars = fetch_daily_history(universe, period="2y")

    out: list[dict] = []
    for ticker in universe:
        df = bars.get(ticker)
        evaluation = _evaluate(df)
        if evaluation is None:
            continue
        evaluation["Symbol"] = ticker
        evaluation["Sector"] = sector_map.get(ticker)
        out.append(evaluation)

    out.sort(key=lambda r: r.get("Setup_Count", 0), reverse=True)
    return out


def save_setups() -> list[dict]:
    rows = compute_setups()
    payload = {"as_of": datetime.now(EST).isoformat(), "rows": rows}
    save_json(CACHE_SETUPS, payload)
    stamp_alpha_refresh("setups")
    logger.info(f"Cached setups for {len(rows)} tickers")
    return rows


def get_cached_setups() -> list[dict]:
    payload = load_json(CACHE_SETUPS, {})
    if isinstance(payload, dict):
        return payload.get("rows", [])
    return []


def get_setup_map() -> dict[str, dict]:
    """{ticker: setup_row} for joining into the Edge Score."""
    return {r["Symbol"]: r for r in get_cached_setups() if r.get("Symbol")}
