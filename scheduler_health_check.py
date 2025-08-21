#!/usr/bin/env python3
"""
Scheduler Health Check - Comprehensive status monitoring
"""

import subprocess
import os
from datetime import datetime
import pytz

def check_process_running(process_name):
    """Check if a process is running"""
    try:
        result = subprocess.run(['pgrep', '-f', process_name], 
                               capture_output=True, text=True)
        pids = result.stdout.strip().split('\n') if result.stdout.strip() else []
        return len(pids) > 0, pids
    except:
        return False, []

def get_log_tail(log_file, lines=5):
    """Get last few lines of a log file"""
    try:
        with open(log_file, 'r') as f:
            return f.readlines()[-lines:]
    except:
        return ["Log file not found"]

def main():
    print("=" * 70)
    print("TRADING SCHEDULER HEALTH CHECK")
    print("=" * 70)
    print()
    
    # Check current time and market status
    est_tz = pytz.timezone('US/Eastern')
    now = datetime.now(est_tz)
    is_weekday = now.weekday() < 5
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    is_market_hours = market_open <= now <= market_close and is_weekday
    
    print(f"📅 Current Time: {now.strftime('%A, %B %d, %Y at %I:%M %p EST')}")
    
    if is_market_hours:
        print("🟢 Market Status: OPEN")
    elif is_weekday:
        if now < market_open:
            print("🟡 Market Status: PRE-MARKET")
        else:
            print("🔴 Market Status: AFTER-HOURS")
    else:
        print("🔴 Market Status: CLOSED (Weekend)")
    
    print()
    
    # Check processes
    watchdog_running, watchdog_pids = check_process_running('scheduler_watchdog.py')
    scheduler_running, scheduler_pids = check_process_running('trading_scheduler.py')
    
    print("🔧 PROCESS STATUS:")
    if watchdog_running:
        print(f"✅ Scheduler Watchdog: RUNNING (PID: {', '.join(watchdog_pids)})")
    else:
        print("❌ Scheduler Watchdog: NOT RUNNING")
    
    if scheduler_running:
        print(f"✅ Trading Scheduler: RUNNING (PID: {', '.join(scheduler_pids)})")
    else:
        print("❌ Trading Scheduler: NOT RUNNING")
    
    print()
    
    # Check log files
    print("📋 RECENT LOG ACTIVITY:")
    
    if os.path.exists('scheduler_watchdog.log'):
        print("Watchdog Log (last 3 lines):")
        for line in get_log_tail('scheduler_watchdog.log', 3):
            print(f"  {line.strip()}")
    else:
        print("  No watchdog log file found")
    
    print()
    
    if os.path.exists('trading_scheduler.log'):
        print("Scheduler Log (last 3 lines):")
        for line in get_log_tail('trading_scheduler.log', 3):
            print(f"  {line.strip()}")
    else:
        print("  No scheduler log file found")
    
    print()
    
    # Recommendations
    print("🔧 RECOMMENDATIONS:")
    
    if is_market_hours:
        if not watchdog_running and not scheduler_running:
            print("⚠️  START SYSTEM: Run './start_persistent_scheduler.sh'")
        elif not watchdog_running and scheduler_running:
            print("⚠️  START WATCHDOG: Run 'python3 scheduler_watchdog.py &'")
        elif not scheduler_running and watchdog_running:
            print("ℹ️  Watchdog will restart scheduler automatically")
        else:
            print("✅ System running optimally")
    else:
        if not watchdog_running and not scheduler_running:
            print("ℹ️  Market closed - start system before 9:30 AM EST tomorrow")
        else:
            print("ℹ️  System running - ready for next trading session")
    
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()