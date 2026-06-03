#!/usr/bin/env python3
"""Generate MRVL-matching report across all watchlist stocks"""

from watchlist_scanner import scan_watchlist
from watchlist_stocks import get_watchlist

print('Running watchlist scan against MRVL accumulation patterns...\n')
result = scan_watchlist()

stocks = result.get('stocks', [])
watchlist_map = {item['symbol']: item for item in get_watchlist()}

print(f'Scanned {len(stocks)} stocks\n')

# Group by MRVL convergence score
breakout = [s for s in stocks if s['score'] >= 4.5]
conviction = [s for s in stocks if 3.5 <= s['score'] < 4.5]
accumulating = [s for s in stocks if 2.5 <= s['score'] < 3.5]
early = [s for s in stocks if 1.5 <= s['score'] < 2.5]
watch = [s for s in stocks if s['score'] < 1.5]

print('='*100)
print('BREAKOUT BUY (Score 4.5-5.0) | All MRVL signals converged, ACT NOW')
print('='*100)
if breakout:
    for s in sorted(breakout, key=lambda x: x['score'], reverse=True):
        print(f"  {s['symbol']:6s} | Score {s['score']:.1f}/5.0 | {s['name']}")
else:
    print('  None detected |no stocks at MRVL breakout convergence yet')

print('\n' + '='*100)
print('HIGH CONVICTION (Score 3.5-4.4) |Very close to breakout, prepare positions')
print('='*100)
if conviction:
    for s in sorted(conviction, key=lambda x: x['score'], reverse=True):
        print(f"  {s['symbol']:6s} | Score {s['score']:.1f}/5.0 | {s['name']}")
else:
    print('  None detected')

print('\n' + '='*100)
print('ACCUMULATING (Score 2.5-3.4) |Spring loading detected, ready to build positions')
print('='*100)
if accumulating:
    for s in sorted(accumulating, key=lambda x: x['score'], reverse=True):
        signals = s.get('signals', {})
        # Format signals: show which ones are firing
        sig_summary = []
        for sig_name, sig_status in signals.items():
            if sig_status == 'strong':
                sig_summary.append(f"{sig_name}(S)")
            elif sig_status == 'developing':
                sig_summary.append(f"{sig_name}(D)")
        sig_str = ' '.join(sig_summary) if sig_summary else 'no signals'
        print(f"  {s['symbol']:6s} | Score {s['score']:.1f} | Signals: {sig_str} | RSI {s['rsi']:.0f}")
else:
    print('  None detected')

print('\n' + '='*100)
print('EARLY SIGNALS (Score 1.5-2.4) |Watch carefully, may develop')
print('='*100)
if early:
    for s in sorted(early, key=lambda x: x['score'], reverse=True)[:10]:
        print(f"  {s['symbol']:6s} | Score {s['score']:.1f}/5.0 | {s['name']}")
else:
    print('  None detected')

print('\n' + '='*100)
print('WATCH ONLY (Score <1.5) |No clear setup yet')
print('='*100)
print(f'  {len(watch)} stocks showing no MRVL-like patterns')

print('\n' + '='*100)
print('SUMMARY')
print('='*100)
print(f'  Breakout Buy (4.5+):       {len(breakout):2d} stocks')
print(f'  High Conviction (3.5-4.4): {len(conviction):2d} stocks')
print(f'  Accumulating (2.5-3.4):    {len(accumulating):2d} stocks  -> Ready to build positions')
print(f'  Early Signals (1.5-2.4):   {len(early):2d} stocks')
print(f'  Watch Only (<1.5):         {len(watch):2d} stocks')
print(f'  Total ActionAble:          {len(breakout) + len(conviction) + len(accumulating):2d} stocks')

print('\n' + '='*100)
print('THE 5 MRVL INDICATORS BEING MONITORED')
print('='*100)
print('''
1. RVOL (Relative Volume)
   - Strong: >1.8x on last 3 up days (institutional inflow)
   - Developing: >1.4x on most up days
   - Signal: Volume spike on up days without distribution on down days

2. OBV (On-Balance Volume)
   - Strong: Making new 20-day highs (accumulation continues)
   - Developing: Positive 5-day slope (trend forming)
   - Signal: Professional money actively accumulating despite quiet price

3. MFI (Money Flow Index 0-100)
   - Strong: 55-72 sustained for 5+ days (institutional buying without exhaustion)
   - Developing: 45-55 range (building accumulation)
   - Signal: Money flowing in, but not overbought (safe to keep buying)

4. ADX (Average Directional Index)
   - Strong: Rising AND >28 (strong trend establishing)
   - Developing: Rising from any baseline (trend strengthening)
   - Signal: Professional trend traders entering, not random noise

5. A/D Line (Accumulation/Distribution)
   - Strong: Making new 20-day highs (professionals in control)
   - Developing: Positive 5-day slope (institutional accumulation starting)
   - Signal: Institutional footprint in price action

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MRVL REFERENCE PATTERN (March 5 to June 2, 2026 = 300% move):
  March 5:  All 5 signals fired = Score 5.0 (BREAKOUT BUY) → Price $90 → $268 by June 2
  April-May: Scores 2.5-3.5 (ACCUMULATING) as weak hands sold, professionals accumulated
  June 2:   Score 4.5+ (HIGH CONVICTION) at breakout on catalysts

STRATEGY:
  • Score 4.5+  = BUY NOW (accumulation complete, breakout imminent)
  • Score 3.5-4.4 = BUILD POSITION (getting close)
  • Score 2.5-3.4 = START ACCUMULATING (spring loading phase, best risk/reward)
  • Score 1.5-2.4 = MONITOR (early signals, wait for confirmation)
  • Score <1.5 = WATCH ONLY (no setup yet)
''')
