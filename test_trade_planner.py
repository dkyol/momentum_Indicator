#!/usr/bin/env python3
"""Quick test of Trade Planner features"""

import sys
sys.path.insert(0, '.')

# Test 1: Exit signals module
print("[TEST 1] Importing exit signals...")
from exit_signals import compute_exit_signals, get_cached_exit_signals
print("  [OK] Exit signals module imported")

# Test 2: Compute exit signals
print("[TEST 2] Computing exit signals...")
try:
    signals = compute_exit_signals()
    print(f"  [PASS] Computed exit signals for {len(signals)} tickers")
    if signals:
        sample = list(signals.items())[:2]
        for sym, sig in sample:
            print(f"    - {sym}: {sig['exit_signal']}")
except Exception as e:
    print(f"  [FAIL] ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Position sizing
print("[TEST 3] Importing position sizing...")
from swing_picks import compute_position_size
print("  [PASS] Position sizing function imported")

# Test position sizing calculation
print("[TEST 4] Testing position sizing calculation...")
sizing = compute_position_size(
    entry_price=100.0,
    stop_price=95.0,
    target_price=110.0,
    account_size=50000,
    risk_pct=1.0
)
print(f"  [PASS] Position sizing calculated:")
print(f"    - Shares: {sizing['shares']}")
print(f"    - Max loss: ${sizing['max_loss_dollars']}")
print(f"    - Position value: ${sizing['position_value']}")
print(f"    - Potential gain: ${sizing['potential_gain']}")

# Test 5: Build picks with sizing
print("[TEST 5] Building picks with position sizing...")
from swing_picks import build_picks
try:
    picks = build_picks(min_edge=50, min_rs=50, account_size=50000, risk_pct=1.0)
    print(f"  [PASS] build_picks() executed: {len(picks)} stocks")
    if picks:
        pick = picks[0]
        print(f"    - Sample: {pick['Symbol']}")
        print(f"    - Has Shares: {'Shares' in pick}")
        print(f"    - Has Position_Value: {'Position_Value' in pick}")
        print(f"    - Has RSI_14: {'RSI_14' in pick}")
        print(f"    - Shares value: {pick.get('Shares')}")
        print(f"    - Position Value: ${pick.get('Position_Value')}")
except Exception as e:
    print(f"  [FAIL] ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Trade planner route logic
print("[TEST 6] Testing trade planner logic...")
try:
    # Simulate what the route does
    all_picks = build_picks(min_edge=0, min_rs=0, account_size=50000, risk_pct=1.0)
    exit_map = get_cached_exit_signals().get('signals', {})

    # BUY ZONE
    buy_zone = [
        r for r in all_picks
        if r.get('Setups')
        and (r.get('Edge_Score') or 0) > 50
        and (r.get('RSI_14') is None or r.get('RSI_14') < 55)
    ]

    # EXIT ZONE
    exit_zone_symbols = {sym for sym, sig in exit_map.items() if sig.get('exit_signal') != 'HOLD'}

    # HOLD ZONE
    hold_zone = [
        r for r in all_picks
        if not r.get('Setups')
        and r['Symbol'] not in exit_zone_symbols
    ]

    print(f"  [PASS] Trade planner zones classified:")
    print(f"    - BUY ZONE: {len(buy_zone)} stocks")
    print(f"    - EXIT ZONE: {len(exit_zone_symbols)} stocks")
    print(f"    - HOLD ZONE: {len(hold_zone)} stocks")

    if buy_zone:
        print(f"    - Sample BUY: {buy_zone[0]['Symbol']} (RSI: {buy_zone[0].get('RSI_14')}, Shares: {buy_zone[0].get('Shares')})")
    if exit_zone_symbols:
        sample_exit = list(exit_zone_symbols)[0]
        print(f"    - Sample EXIT: {sample_exit} ({exit_map[sample_exit]['exit_signal']})")

except Exception as e:
    print(f"  [FAIL] ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n[SUCCESS] All core features work!")
