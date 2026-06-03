#!/usr/bin/env python3
"""Populate Trade Planner data by running scheduler jobs"""

import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')

print("=" * 70)
print("Running Data Population Jobs")
print("=" * 70)

# 1. Market data
print("\n[1/3] Fetching market data (high volume stocks, momentum, SMA)...")
try:
    from scheduler import save_market_data
    save_market_data()
    print("  [OK] Market data saved")
except Exception as e:
    print(f"  [ERROR] {e}")
    sys.exit(1)

# 2. Alpha refresh (includes setups, edge scores, etc)
print("\n[2/3] Refreshing alpha data (setups, edge scores, RS, fundamentals)...")
print("       This takes ~2-3 minutes...")
try:
    from alpha_engine import refresh_alpha_data
    refresh_alpha_data(include_backtest=True)
    print("  [OK] Alpha data refreshed")
except Exception as e:
    print(f"  [ERROR] {e}")
    sys.exit(1)

# 3. Exit signals
print("\n[3/3] Computing exit signals...")
try:
    from exit_signals import save_exit_signals
    result = save_exit_signals()
    signals = result.get('signals', {})
    print(f"  [OK] Exit signals computed: {len(signals)} tickers")

    # Show sample signals
    sample = list(signals.items())[:3]
    for sym, sig in sample:
        print(f"       - {sym}: {sig['exit_signal']}")
except Exception as e:
    print(f"  [ERROR] {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("SUCCESS: All data populated!")
print("=" * 70)
print("\nNext steps:")
print("  1. Refresh https://momentum-indicator.onrender.com/trade-planner")
print("  2. You should now see:")
print("     - BUY ZONE: stocks with active setups + Edge Score > 50 + RSI < 55")
print("     - EXIT ZONE: stocks with exit signals (SELL/TRAIL/WATCH)")
print("     - HOLD ZONE: everything else being monitored")
print("  3. Change Account Size/Risk % to see position sizing update instantly")
