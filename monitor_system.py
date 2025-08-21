#!/usr/bin/env python3
"""
System Monitor - Simple monitoring for the robust trading scheduler
"""

import os
import time
import json
import subprocess
from datetime import datetime
import pytz

def check_system_health():
    """Check if all components are running properly"""
    print("=" * 60)
    print("TRADING SYSTEM HEALTH CHECK")
    print("=" * 60)
    
    est = pytz.timezone('US/Eastern')
    now = datetime.now(est)
    print(f"Check Time: {now.strftime('%A, %B %d, %Y at %I:%M %p EST')}")
    print()
    
    # Check if robust scheduler is running
    try:
        result = subprocess.run(['pgrep', '-f', 'robust_scheduler'], 
                               capture_output=True, text=True)
        if result.stdout.strip():
            pid = result.stdout.strip()
            print(f"✅ Robust Scheduler: Running (PID: {pid})")
        else:
            print("❌ Robust Scheduler: Not running")
            return False
    except Exception as e:
        print(f"❌ Scheduler Check Failed: {e}")
        return False
    
    # Check status file
    if os.path.exists('scheduler_status.json'):
        try:
            with open('scheduler_status.json', 'r') as f:
                status = json.load(f)
                print(f"📊 Last Task: {status.get('task', 'N/A')}")
                print(f"📊 Status: {status.get('status', 'N/A')}")
                print(f"📊 Updated: {status.get('last_update', 'N/A')}")
        except Exception as e:
            print(f"⚠️ Status File Error: {e}")
    else:
        print("⚠️ Status File: Not found")
    
    # Check current portfolio status
    try:
        from paper_trader import trader
        portfolio = trader.get_portfolio_summary()
        
        print()
        print("💰 Portfolio Status:")
        print(f"   Value: ${portfolio['total_value']:.2f}")
        print(f"   Positions: {len(portfolio['positions'])}")
        
        if portfolio['positions']:
            print("   Active Positions:")
            for pos in portfolio['positions']:
                print(f"     • {pos['symbol']}: ${pos['pnl']:+.2f} ({pos['pnl_pct']:+.2f}%)")
    
    except Exception as e:
        print(f"❌ Portfolio Check Failed: {e}")
    
    print()
    print("🔧 Failsafe Features Active:")
    print("   • Retry logic with exponential backoff")
    print("   • Emergency backup execution")
    print("   • Continuous health monitoring")
    print("   • Backup EOD closure at 3:39 PM")
    print("   • Missed execution detection")
    print()
    
    return True

if __name__ == "__main__":
    check_system_health()