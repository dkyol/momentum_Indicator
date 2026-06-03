"""
Weekly Watchlist Scanner — MRVL-Like Breakout Signal Detection

Scans all 23 AI infrastructure watchlist stocks weekly, computes the 5 MRVL
indicators (RVOL, OBV, MFI, ADX, A/D line), scores each stock 0-5 based on
signal convergence, and returns recommendations.

Scoring (0-5 total):
  4.5-5.0 = BREAKOUT BUY (all signals aligned, act now)
  3.5-4.4 = HIGH CONVICTION (very close to breakout)
  2.5-3.4 = ACCUMULATING (spring loading detected)
  1.5-2.4 = EARLY SIGNALS (watch carefully)
  < 1.5 = WATCH ONLY (no clear setup yet)

Runs weekly (Sunday 23:00 UTC / 7 PM ET).
"""

import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from alpha_cache import CACHE_WATCHLIST_SCAN, load_json, save_json, stamp_alpha_refresh
from price_data import fetch_daily_history
from rvol import compute_rvol_snapshot
from setups import _rsi
from volume_indicators import compute_ad_line, compute_adx, compute_mfi, compute_obv
from watchlist_stocks import get_watchlist, get_watchlist_symbols

logger = logging.getLogger(__name__)


def _score_signals(stock_data: dict) -> tuple[float, dict]:
    """
    Score MRVL-like signal convergence (0-5 scale).

    Returns (score, signal_details_dict)
    """
    score = 0.0
    signals = {
        "rvol": False,
        "obv": False,
        "mfi": False,
        "adx": False,
        "ad_line": False,
    }

    # Extract computed values
    rvol_value = stock_data.get("rvol_value", 1.0)
    obv_series = stock_data.get("obv_series")
    mfi_series = stock_data.get("mfi_series")
    adx_series = stock_data.get("adx_series")
    ad_line_series = stock_data.get("ad_line_series")
    closes = stock_data.get("closes")

    # --- RVOL Signal (1 pt max) ---
    # Strong: >1.8x on last 3 up days
    # Developing: >1.4x on most up days
    if rvol_value is not None and not pd.isna(rvol_value):
        if rvol_value > 1.8:
            score += 1.0
            signals["rvol"] = "strong"
        elif rvol_value > 1.4:
            score += 0.5
            signals["rvol"] = "developing"

    # --- OBV Signal (1 pt max) ---
    # Strong: OBV making new 20-day highs
    # Developing: OBV positive slope (5-day)
    if obv_series is not None and len(obv_series) > 20:
        obv_last = obv_series.iloc[-1]
        obv_20d_high = obv_series.iloc[-20:].max()
        obv_slope_5d = obv_series.iloc[-5:].diff().mean()

        if obv_last >= obv_20d_high * 0.98:  # Within 2% of 20d high
            score += 1.0
            signals["obv"] = "strong"
        elif obv_slope_5d > 0:
            score += 0.5
            signals["obv"] = "developing"

    # --- MFI Signal (1 pt max) ---
    # Strong: 55-72 range sustained 5+ days
    # Developing: 45-55 range
    if mfi_series is not None and len(mfi_series) > 5:
        mfi_last_5 = mfi_series.iloc[-5:].mean()

        if 55 <= mfi_last_5 <= 72:
            score += 1.0
            signals["mfi"] = "strong"
        elif 45 <= mfi_last_5 <= 55:
            score += 0.5
            signals["mfi"] = "developing"

    # --- ADX Signal (1 pt max) ---
    # Strong: Rising ADX and >28
    # Developing: Rising from any base
    if adx_series is not None and len(adx_series) > 10:
        adx_last = adx_series.iloc[-1]
        adx_prev = adx_series.iloc[-10:-1].mean()
        adx_rising = adx_last > adx_prev

        if adx_rising and adx_last > 28:
            score += 1.0
            signals["adx"] = "strong"
        elif adx_rising:
            score += 0.5
            signals["adx"] = "developing"

    # --- A/D Line Signal (1 pt max) ---
    # Strong: A/D making new 20-day highs
    # Developing: A/D positive slope (5-day)
    if ad_line_series is not None and len(ad_line_series) > 20:
        ad_last = ad_line_series.iloc[-1]
        ad_20d_high = ad_line_series.iloc[-20:].max()
        ad_slope_5d = ad_line_series.iloc[-5:].diff().mean()

        if ad_last >= ad_20d_high * 0.98:  # Within 2% of 20d high
            score += 1.0
            signals["ad_line"] = "strong"
        elif ad_slope_5d > 0:
            score += 0.5
            signals["ad_line"] = "developing"

    return score, signals


def _get_recommendation(score: float) -> str:
    """Convert 0-5 signal score to recommendation tier."""
    if score >= 4.5:
        return "BREAKOUT BUY"
    elif score >= 3.5:
        return "HIGH CONVICTION"
    elif score >= 2.5:
        return "ACCUMULATING"
    elif score >= 1.5:
        return "EARLY SIGNALS"
    else:
        return "WATCH ONLY"


def scan_watchlist() -> dict:
    """
    Fetch 6-month daily OHLCV for all watchlist stocks, compute all 5 indicators,
    score each stock, return sorted list.

    Returns: {as_of, stocks: [{symbol, name, tier, mrvl_score, close, rsi,
              score (0-5), recommendation, signals: {rvol, obv, mfi, adx, ad_line}, ...}]}
    """
    logger.info("Starting weekly watchlist scan...")

    watchlist = get_watchlist()
    symbols = get_watchlist_symbols()

    # Fetch 6-month daily history
    try:
        price_history = fetch_daily_history(symbols, period="6mo")
        logger.info(f"Fetched daily data for {len(price_history)} symbols")
    except Exception as e:
        logger.error(f"Failed to fetch price history: {e}")
        return {
            "as_of": datetime.now(timezone.utc).isoformat(),
            "stocks": [],
            "error": str(e),
        }

    # Get intraday RVOL snapshot (from current daily data)
    try:
        rvol_snapshot = compute_rvol_snapshot()
    except Exception as e:
        logger.warning(f"Failed to get RVOL snapshot: {e}")
        rvol_snapshot = {}

    # Scan each stock
    results = []
    watchlist_map = {item["symbol"]: item for item in watchlist}

    for symbol in symbols:
        if symbol not in price_history:
            logger.warning(f"No price data for {symbol}")
            continue

        df = price_history[symbol]
        if df is None or len(df) < 50:
            logger.warning(f"{symbol}: insufficient data ({len(df) if df is not None else 0} bars)")
            continue

        try:
            # Extract OHLCV
            opens = df["Open"]
            highs = df["High"]
            lows = df["Low"]
            closes = df["Close"]
            volumes = df["Volume"]

            # Compute indicators
            rsi_series = _rsi(closes, 14)
            obv_series = compute_obv(closes, volumes)
            ad_line_series = compute_ad_line(highs, lows, closes, volumes)
            mfi_series = compute_mfi(highs, lows, closes, volumes, period=14)
            adx_series, plus_di, minus_di = compute_adx(highs, lows, closes, period=14)

            # Get current values
            close_price = closes.iloc[-1]
            rsi_value = rsi_series.iloc[-1] if len(rsi_series) > 0 else np.nan
            rvol_value = rvol_snapshot.get(symbol, {}).get("rvol_ratio", np.nan)
            adx_value = adx_series.iloc[-1] if len(adx_series) > 0 else np.nan
            mfi_value = mfi_series.iloc[-1] if len(mfi_series) > 0 else np.nan
            obv_value = obv_series.iloc[-1] if len(obv_series) > 0 else np.nan
            ad_line_value = ad_line_series.iloc[-1] if len(ad_line_series) > 0 else np.nan

            # Score signals
            stock_data = {
                "rvol_value": rvol_value,
                "obv_series": obv_series,
                "mfi_series": mfi_series,
                "adx_series": adx_series,
                "ad_line_series": ad_line_series,
                "closes": closes,
            }
            signal_score, signals = _score_signals(stock_data)

            # Build result row
            watchlist_item = watchlist_map.get(symbol, {})
            result_row = {
                "symbol": symbol,
                "name": watchlist_item.get("name", symbol),
                "tier": watchlist_item.get("tier", 4),
                "mrvl_score": watchlist_item.get("score", 0),
                "narrative": watchlist_item.get("narrative", ""),
                "close": float(close_price) if not pd.isna(close_price) else None,
                "rsi": float(rsi_value) if not pd.isna(rsi_value) else None,
                "adx": float(adx_value) if not pd.isna(adx_value) else None,
                "mfi": float(mfi_value) if not pd.isna(mfi_value) else None,
                "obv": float(obv_value) if not pd.isna(obv_value) else None,
                "ad_line": float(ad_line_value) if not pd.isna(ad_line_value) else None,
                "rvol": float(rvol_value) if not pd.isna(rvol_value) else None,
                "score": float(signal_score),
                "recommendation": _get_recommendation(signal_score),
                "signals": signals,
            }
            results.append(result_row)

        except Exception as e:
            logger.error(f"{symbol}: error computing indicators: {e}")
            import traceback

            traceback.print_exc()
            continue

    # Sort by signal score descending, then by MRVL watchlist score
    results.sort(key=lambda x: (x["score"], x["mrvl_score"]), reverse=True)

    output = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "stocks": results,
    }

    logger.info(f"Watchlist scan complete: {len(results)} stocks scored")
    return output


def save_watchlist_scan() -> dict:
    """Run scan and write to cache."""
    result = scan_watchlist()
    try:
        save_json(CACHE_WATCHLIST_SCAN, result)
        stamp_alpha_refresh("watchlist_scan", {"stocks_scanned": len(result.get("stocks", []))})
        logger.info(f"Watchlist scan saved to {CACHE_WATCHLIST_SCAN}")
    except Exception as e:
        logger.error(f"Failed to save watchlist scan: {e}")
    return result


def get_cached_watchlist_scan() -> dict:
    """Load from cache, return empty dict if not available."""
    return load_json(
        CACHE_WATCHLIST_SCAN,
        {"as_of": None, "stocks": []},
    )
