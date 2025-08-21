#!/usr/bin/env python3
"""
Scheduler Status - Check the status of the trading scheduler
"""

import os
import subprocess
import json
from datetime import datetime
import pytz
from paper_trader import trader

def check_scheduler_status():
    """Check if scheduler is running"""
    try:
        result = subprocess.run(['pgrep', '-f', 'trading_scheduler.py'], 
                               capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            return True, pids
        return False, []
    except:
        return False, []

def main():
    print("=" * 60)
    print("TRADING SCHEDULER STATUS")
    print("=" * 60)
    print()
    
    # Check scheduler process
    is_running, pids = check_scheduler_status()
    if is_running:
        print(f"✅ Scheduler Status: RUNNING (PID: {', '.join(pids)})")
    else:
        print("❌ Scheduler Status: NOT RUNNING")
        print("   Run './start_trading_system.sh' to start")
    print()
    
    # Check current time
    est_tz = pytz.timezone('US/Eastern')
    now = datetime.now(est_tz)
    print(f"📅 Current Time: {now.strftime('%A, %B %d, %Y at %I:%M %p EST')}")
    
    # Market status
    weekday = now.weekday() < 5
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    is_market_hours = market_open <= now <= market_close and weekday
    
    if is_market_hours:
        print("🟢 Market Status: OPEN")
    elif weekday:
        if now < market_open:
            print("🟡 Market Status: PRE-MARKET")
        else:
            print("🔴 Market Status: AFTER-HOURS")
    else:
        print("🔴 Market Status: CLOSED (Weekend)")
    print()
    
    # Portfolio status
    try:
        portfolio = trader.get_portfolio_summary()
        print("💰 Portfolio Summary:")
        print(f"   Total Value: ${portfolio['total_value']:.2f}")
        print(f"   Cash Balance: ${portfolio['cash_balance']:.2f}")
        print(f"   Active Positions: {len(portfolio['positions'])}")
        print(f"   Total P&L: ${portfolio['total_pnl']:.2f}")
        
        if portfolio['positions']:
            print()
            print("📊 Active Positions:")
            for pos in portfolio['positions']:
                print(f"   • {pos['symbol']}: {pos['quantity']:.2f} shares @ ${pos['current_price']:.2f}")
                print(f"     P&L: ${pos['pnl']:+.2f} ({pos['pnl_pct']:+.2f}%)")
    except Exception as e:
        print(f"⚠️ Unable to get portfolio status: {e}")
    
    print()
    print("📅 Next Scheduled Events:")
    
    # Calculate next events based on current time
    if weekday and now.hour < 10:
        print("   • 10:05 AM EST - Market data update")
        print("   • 10:15 AM EST - Morning trades execution")
        print("   • 3:34 PM EST - End of day closure")
    elif weekday and now.hour < 15:
        print("   • 3:34 PM EST - End of day closure")
    elif weekday and now.hour >= 15:
        print("   • Tomorrow 10:05 AM EST - Market data update")
        print("   • Tomorrow 10:15 AM EST - Morning trades")
    else:
        print("   • Monday 10:05 AM EST - Market data update")
        print("   • Monday 10:15 AM EST - Morning trades")
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    main()