#!/usr/bin/env python3
"""Broad cross-industry scan for MRVL-like accumulation patterns"""

from watchlist_scanner import scan_watchlist
from watchlist_stocks import get_watchlist, get_sectors

print('Running BROAD CROSS-INDUSTRY scan for MRVL accumulation patterns...\n')
result = scan_watchlist()

stocks = result.get('stocks', [])
watchlist = get_watchlist()
watchlist_map = {item['symbol']: item for item in watchlist}

print(f'Scanned {len(stocks)} stocks\n')

# Group by MRVL convergence score
breakout = [s for s in stocks if s['score'] >= 4.5]
conviction = [s for s in stocks if 3.5 <= s['score'] < 4.5]
accumulating = [s for s in stocks if 2.5 <= s['score'] < 3.5]
early = [s for s in stocks if 1.5 <= s['score'] < 2.5]
watch = [s for s in stocks if s['score'] < 1.5]

print('='*120)
print('BREAKOUT BUY (Score 4.5-5.0) | All MRVL signals converged')
print('='*120)
if breakout:
    for s in sorted(breakout, key=lambda x: x['score'], reverse=True):
        sector = watchlist_map.get(s['symbol'], {}).get('sector', 'Unknown')
        print(f"  {s['symbol']:8s} | Score {s['score']:.1f} | {s['name']:30s} | Sector: {sector}")
else:
    print('  None detected')

print('\n' + '='*120)
print('HIGH CONVICTION (Score 3.5-4.4) | Very close to breakout')
print('='*120)
if conviction:
    for s in sorted(conviction, key=lambda x: x['score'], reverse=True):
        sector = watchlist_map.get(s['symbol'], {}).get('sector', 'Unknown')
        print(f"  {s['symbol']:8s} | Score {s['score']:.1f} | {s['name']:30s} | Sector: {sector}")
else:
    print('  None detected')

print('\n' + '='*120)
print('ACCUMULATING (Score 2.5-3.4) | Spring loading, ready to build')
print('='*120)
if accumulating:
    for s in sorted(accumulating, key=lambda x: x['score'], reverse=True):
        sector = watchlist_map.get(s['symbol'], {}).get('sector', 'Unknown')
        signals = s.get('signals', {})
        sig_count = sum(1 for v in signals.values() if v)
        print(f"  {s['symbol']:8s} | Score {s['score']:.1f} | {s['name']:30s} | {sig_count}/5 signals | RSI {s['rsi']:.0f}")
else:
    print('  None detected')

print('\n' + '='*120)
print('EARLY SIGNALS (Score 1.5-2.4) | Watch carefully')
print('='*120)
if early:
    for s in sorted(early, key=lambda x: x['score'], reverse=True)[:15]:
        sector = watchlist_map.get(s['symbol'], {}).get('sector', 'Unknown')
        print(f"  {s['symbol']:8s} | Score {s['score']:.1f} | {s['name']:30s} | Sector: {sector}")
else:
    print('  None detected')

print('\n' + '='*120)
print('SUMMARY BY SECTOR')
print('='*120)
sectors_found = {}
for s in breakout + conviction + accumulating + early:
    sector = watchlist_map.get(s['symbol'], {}).get('sector', 'Unknown')
    score_tier = 'Breakout' if s['score'] >= 4.5 else 'Conviction' if s['score'] >= 3.5 else 'Accumulating' if s['score'] >= 2.5 else 'Early'
    if sector not in sectors_found:
        sectors_found[sector] = {'Breakout': 0, 'Conviction': 0, 'Accumulating': 0, 'Early': 0}
    sectors_found[sector][score_tier] += 1

for sector in sorted(sectors_found.keys()):
    counts = sectors_found[sector]
    total = sum(counts.values())
    print(f"  {sector:20s} | Breakout: {counts['Breakout']} | Conviction: {counts['Conviction']} | Accumulating: {counts['Accumulating']} | Early: {counts['Early']} | Total: {total}")

print('\n' + '='*120)
print('KEY FINDINGS')
print('='*120)
print(f'  Total actionable stocks (3.5+): {len(breakout) + len(conviction)}')
print(f'  Total accumulating stocks (2.5-3.4): {len(accumulating)}')
print(f'  Total early signal stocks (1.5-2.4): {len(early)}')
print(f'  Total watchable (all scores >0): {len(stocks)}')

# Check for space stocks
space_stocks = [s for s in stocks if watchlist_map.get(s['symbol'], {}).get('sector') == 'Space']
print(f'\n  Space sector stocks scanned: {len(space_stocks)}')
if space_stocks:
    for s in sorted(space_stocks, key=lambda x: x['score'], reverse=True):
        print(f"    {s['symbol']} ({s['name']}): Score {s['score']:.1f}")

print('\n  LUNR, RKLB, SPIR status:')
for sym in ['LUNR', 'RKLB', 'SPIR']:
    found = [s for s in stocks if s['symbol'] == sym]
    if found:
        s = found[0]
        print(f"    {s['symbol']:6s} | Score {s['score']:.1f} | {s['name']}")
    else:
        print(f"    {sym} | No data available")
