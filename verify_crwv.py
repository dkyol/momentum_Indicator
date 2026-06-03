from watchlist_stocks import get_watchlist

watchlist = get_watchlist()
print(f'Total stocks: {len(watchlist)}\n')
print('Tier 1 stocks (sorted by score):')
tier1 = [s for s in watchlist if s['tier'] == 1]
for s in sorted(tier1, key=lambda x: x['score'], reverse=True):
    print(f"  {s['symbol']:5s} | Score {s['score']:2d} | {s['name']}")

print('\nCoreWeave details:')
crwv = [s for s in watchlist if s['symbol'] == 'CRWV'][0]
print(f"  Symbol: {crwv['symbol']}")
print(f"  Name: {crwv['name']}")
print(f"  Score: {crwv['score']}/100")
print(f"  Tier: {crwv['tier']}")
print(f"  Narrative: {crwv['narrative']}")
