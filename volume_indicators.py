"""
Volume Indicators — The 5 MRVL Signals

Computes OBV, A/D line, MFI, ADX (+ MACD) from daily OHLCV bars.
Used by watchlist_scanner.py to score stocks for MRVL-like breakout setups.

All functions operate on pandas Series — no global state, no I/O.
"""

import numpy as np
import pandas as pd


def compute_obv(closes: pd.Series, volumes: pd.Series) -> pd.Series:
    """
    On-Balance Volume: cumulative sum of volume on up/down days.

    OBV > OBV.rolling(20).mean() = accumulation signal
    OBV making new 20-day highs = institutional buying
    """
    if len(closes) == 0 or len(volumes) == 0:
        return pd.Series(dtype=float)

    obv = pd.Series(0.0, index=closes.index)
    obv.iloc[0] = volumes.iloc[0] if closes.iloc[0] > 0 else 0

    for i in range(1, len(closes)):
        if pd.isna(closes.iloc[i]) or pd.isna(volumes.iloc[i]) or pd.isna(closes.iloc[i - 1]):
            obv.iloc[i] = obv.iloc[i - 1]
        elif closes.iloc[i] > closes.iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] + volumes.iloc[i]
        elif closes.iloc[i] < closes.iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] - volumes.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i - 1]

    return obv


def compute_ad_line(highs: pd.Series, lows: pd.Series, closes: pd.Series, volumes: pd.Series) -> pd.Series:
    """
    Accumulation/Distribution Line: volume-weighted price position.

    CLV = ((Close - Low) - (High - Close)) / (High - Low)
    A/D += CLV * Volume

    A/D making new 20-day highs = institutional accumulation
    """
    if len(closes) == 0 or len(volumes) == 0:
        return pd.Series(dtype=float)

    # Close Location Value
    clv = pd.Series(0.0, index=closes.index)
    for i in range(len(closes)):
        if pd.isna(highs.iloc[i]) or pd.isna(lows.iloc[i]) or pd.isna(closes.iloc[i]):
            clv.iloc[i] = 0.0
        else:
            high_low = highs.iloc[i] - lows.iloc[i]
            if high_low == 0:
                clv.iloc[i] = 0.0
            else:
                clv.iloc[i] = ((closes.iloc[i] - lows.iloc[i]) - (highs.iloc[i] - closes.iloc[i])) / high_low

    # A/D line
    ad_line = (clv * volumes).fillna(0).cumsum()
    return ad_line


def compute_mfi(
    highs: pd.Series, lows: pd.Series, closes: pd.Series, volumes: pd.Series, period: int = 14
) -> pd.Series:
    """
    Money Flow Index: oscillator combining price and volume (0-100).

    Typical Price = (H + L + C) / 3
    Raw Money Flow = TP * Volume
    MFI = 100 - 100 / (1 + Positive MF / Negative MF)

    MFI 55-72 sustained 5+ days = professional institutional buying without exhaustion
    """
    if len(closes) == 0:
        return pd.Series(dtype=float)

    # Typical Price
    tp = (highs + lows + closes) / 3.0
    raw_mf = tp * volumes

    # Positive / Negative MF
    positive_mf = pd.Series(0.0, index=closes.index)
    negative_mf = pd.Series(0.0, index=closes.index)

    for i in range(1, len(tp)):
        if pd.isna(tp.iloc[i]) or pd.isna(tp.iloc[i - 1]):
            continue
        if tp.iloc[i] > tp.iloc[i - 1]:
            positive_mf.iloc[i] = raw_mf.iloc[i]
        elif tp.iloc[i] < tp.iloc[i - 1]:
            negative_mf.iloc[i] = raw_mf.iloc[i]

    # Rolling sums
    pos_mf_roll = positive_mf.rolling(period).sum()
    neg_mf_roll = negative_mf.rolling(period).sum()

    # MFI calculation
    mfi = 100 - (100 / (1 + (pos_mf_roll / neg_mf_roll.replace(0, np.nan))))
    mfi = mfi.fillna(50.0)  # Default to 50 if undefined

    return mfi


def compute_adx(highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Average Directional Index (ADX) + Directional Indicators (+DI, -DI).

    Measures trend strength (0-100). Rising ADX + >28 = strong trend.

    Returns (adx, plus_di, minus_di)
    """
    if len(closes) < period + 1:
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    # True Range
    tr = pd.Series(0.0, index=closes.index)
    for i in range(len(closes)):
        if i == 0:
            tr.iloc[i] = highs.iloc[i] - lows.iloc[i]
        else:
            h_l = highs.iloc[i] - lows.iloc[i]
            h_c = abs(highs.iloc[i] - closes.iloc[i - 1])
            l_c = abs(lows.iloc[i] - closes.iloc[i - 1])
            tr.iloc[i] = max(h_l, h_c, l_c)

    # Directional Movements
    plus_dm = pd.Series(0.0, index=closes.index)
    minus_dm = pd.Series(0.0, index=closes.index)

    for i in range(1, len(closes)):
        up = highs.iloc[i] - highs.iloc[i - 1]
        down = lows.iloc[i - 1] - lows.iloc[i]

        if up > down and up > 0:
            plus_dm.iloc[i] = up
        if down > up and down > 0:
            minus_dm.iloc[i] = down

    # Wilder's smoothed moving average (use EMA-style for stability)
    atr = tr.rolling(period).mean()
    plus_dm_smooth = plus_dm.rolling(period).mean()
    minus_dm_smooth = minus_dm.rolling(period).mean()

    # Directional Indicators
    plus_di = 100 * (plus_dm_smooth / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm_smooth / atr.replace(0, np.nan))
    plus_di = plus_di.fillna(0)
    minus_di = minus_di.fillna(0)

    # ADX (smoothed DI difference)
    di_diff = abs(plus_di - minus_di)
    di_sum = plus_di + minus_di
    di_ratio = di_diff / di_sum.replace(0, np.nan)
    adx = (di_ratio.rolling(period).mean() * 100).fillna(0)

    return adx, plus_di, minus_di


def compute_macd(
    closes: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD (Moving Average Convergence Divergence).

    Returns (macd_line, signal_line, histogram)

    MACD crossing above signal = bullish confirmation
    """
    if len(closes) < slow:
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram
