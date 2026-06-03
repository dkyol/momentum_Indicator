#!/usr/bin/env python3
"""Check CoreWeave MRVL indicator match"""

import pandas as pd
from price_data import fetch_daily_history
from volume_indicators import compute_obv, compute_ad_line, compute_mfi, compute_adx
from setups import _rsi

print('Fetching CoreWeave (CRWV) 6-month daily data...')
try:
    history = fetch_daily_history(['CRWV'], period='6mo')
    df = history.get('CRWV')

    if df is None or len(df) < 50:
        print(f'ERROR: Insufficient data for CRWV ({len(df) if df is not None else 0} bars)')
    else:
        closes = df['Close']
        volumes = df['Volume']
        highs = df['High']
        lows = df['Low']

        # Compute all 5 MRVL indicators
        rsi = _rsi(closes, 14)
        obv = compute_obv(closes, volumes)
        ad_line = compute_ad_line(highs, lows, closes, volumes)
        mfi = compute_mfi(highs, lows, closes, volumes, 14)
        adx, plus_di, minus_di = compute_adx(highs, lows, closes, 14)

        # Get current values
        close_now = closes.iloc[-1]
        rsi_now = rsi.iloc[-1]
        obv_now = obv.iloc[-1]
        obv_20d_high = obv.iloc[-20:].max()
        mfi_now = mfi.iloc[-1]
        adx_now = adx.iloc[-1]
        ad_line_now = ad_line.iloc[-1]
        ad_line_20d_high = ad_line.iloc[-20:].max()

        # Trends
        obv_slope_5d = obv.iloc[-5:].diff().mean()
        ad_line_slope_5d = ad_line.iloc[-5:].diff().mean()
        adx_trend = adx.iloc[-1] - adx.iloc[-10:-1].mean()

        print('\n===== CRWV CURRENT INDICATOR STATUS =====')
        print(f'Price: ${close_now:.2f}')
        print(f'RSI(14): {rsi_now:.1f}')
        print(f'\n[OBV] On-Balance Volume')
        print(f'  Current: {obv_now:,.0f}')
        print(f'  20-day high: {obv_20d_high:,.0f}')
        obv_at_high = "YES (accumulation signal)" if obv_now >= obv_20d_high * 0.98 else "NO (below recent highs)"
        print(f'  At new 20-day high? {obv_at_high}')
        print(f'  5-day trend: {obv_slope_5d:+,.0f}')

        print(f'\n[MFI] Money Flow Index (0-100)')
        print(f'  Current: {mfi_now:.1f}')
        mfi_status = "EXHAUSTION (overbought)" if mfi_now > 72 else "ACCUMULATION (institutional)" if 55 <= mfi_now <= 72 else "WEAK (selling pressure)"
        print(f'  Status: {mfi_status}')

        print(f'\n[ADX] Average Directional Index (trend strength)')
        print(f'  Current: {adx_now:.1f}')
        adx_dir = "RISING" if adx_trend > 0 else "FALLING"
        adx_strength = "Very Strong (>40)" if adx_now > 40 else "Moderate (25-40)" if adx_now >= 25 else "Weak (<25)"
        print(f'  Direction: {adx_dir}')
        print(f'  Strength: {adx_strength}')

        print(f'\n[A/D Line] Accumulation/Distribution')
        print(f'  Current: {ad_line_now:,.0f}')
        print(f'  20-day high: {ad_line_20d_high:,.0f}')
        ad_at_high = "YES (accumulation)" if ad_line_now >= ad_line_20d_high * 0.98 else "NO (below recent)"
        print(f'  At new 20-day high? {ad_at_high}')

        print(f'\n===== MRVL-LIKE PATTERN MATCH SCORE =====')
        score = 0
        signals_fired = []

        # Score each indicator
        if obv_now >= obv_20d_high * 0.98:
            score += 1.0
            signals_fired.append("✓ OBV at new highs (strong)")
        elif obv_slope_5d > 0:
            score += 0.5
            signals_fired.append("◐ OBV trending up (developing)")
        else:
            signals_fired.append("✗ OBV declining (distribution)")

        if 55 <= mfi_now <= 72:
            score += 1.0
            signals_fired.append("✓ MFI in accumulation 55-72 (strong)")
        elif 45 <= mfi_now < 55:
            score += 0.5
            signals_fired.append("◐ MFI developing 45-55")
        elif mfi_now > 72:
            signals_fired.append("✗ MFI exhaustion >72 (risk)")
        else:
            signals_fired.append("✗ MFI weak <45")

        if adx_now > 28 and adx_trend > 0:
            score += 1.0
            signals_fired.append("✓ ADX rising and >28 (strong trend)")
        elif adx_trend > 0:
            score += 0.5
            signals_fired.append("◐ ADX rising (developing trend)")
        else:
            signals_fired.append("✗ ADX falling (weakening trend)")

        if ad_line_now >= ad_line_20d_high * 0.98:
            score += 1.0
            signals_fired.append("✓ A/D at new highs (strong)")
        elif ad_line_slope_5d > 0:
            score += 0.5
            signals_fired.append("◐ A/D trending up (developing)")
        else:
            signals_fired.append("✗ A/D declining (distribution)")

        print('\nSignals:')
        for sig in signals_fired:
            print(f'  {sig}')

        print(f'\n>>> TOTAL MRVL-LIKE SCORE: {score:.1f}/4.0')

        if score >= 3.5:
            rec = "🔴 BREAKOUT BUY — All signals converging like MRVL"
            score_label = "4.5-5.0"
        elif score >= 2.5:
            rec = "🟡 ACCUMULATING — Spring loading detected"
            score_label = "2.5-3.4"
        elif score >= 1.5:
            rec = "🔵 EARLY SIGNALS — Watch carefully"
            score_label = "1.5-2.4"
        else:
            rec = "⚪ WATCH ONLY / DISTRIBUTION — No clear setup"
            score_label = "<1.5"

        print(f'    Tier: {score_label}')
        print(f'    Recommendation: {rec}')
        print(f'\n>>> VERDICT: {rec}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
