#!/usr/bin/env python3
"""
System Verification Script
Verifies all components of the trading system are working correctly
"""

import sys
import os
import logging
from datetime import datetime
import pytz

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_imports():
    """Verify all required modules can be imported"""
    print("Checking imports...")
    try:
        import yfinance
        print("✅ yfinance")
    except ImportError as e:
        print(f"❌ yfinance: {e}")
        return False
    
    try:
        import pandas
        print("✅ pandas")
    except ImportError as e:
        print(f"❌ pandas: {e}")
        return False
    
    try:
        import schedule
        print("✅ schedule")
    except ImportError as e:
        print(f"❌ schedule: {e}")
        return False
    
    try:
        from paper_trader import PaperTrader
        print("✅ paper_trader")
    except ImportError as e:
        print(f"❌ paper_trader: {e}")
        return False
    
    try:
        from trading_scheduler import TradingScheduler
        print("✅ trading_scheduler")
    except ImportError as e:
        print(f"❌ trading_scheduler: {e}")
        return False
    
    return True

def verify_database():
    """Verify database connection and tables"""
    print("\nChecking database...")
    try:
        from models import get_session, Portfolio, Position, Trade
        session = get_session()
        
        # Check portfolio
        portfolio = session.query(Portfolio).first()
        if portfolio:
            print(f"✅ Portfolio exists: ${portfolio.total_value:.2f}")
        else:
            print("⚠️ No portfolio found (will be created on first run)")
        
        # Check positions
        position_count = session.query(Position).count()
        print(f"✅ Positions table: {position_count} records")
        
        # Check trades
        trade_count = session.query(Trade).count()
        print(f"✅ Trades table: {trade_count} records")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def verify_scheduler():
    """Verify scheduler configuration"""
    print("\nChecking scheduler configuration...")
    try:
        from trading_scheduler import TradingScheduler
        scheduler = TradingScheduler()
        
        est_tz = pytz.timezone('US/Eastern')
        now = datetime.now(est_tz)
        
        print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Market day: {scheduler.is_market_day()}")
        print(f"Market hours: {scheduler.is_market_hours()}")
        
        print("\nScheduled tasks:")
        print("• 10:05 AM EST - Update market data")
        print("• 10:15 AM EST - Execute morning trades")
        print("• 3:34 PM EST - Close all positions")
        print("• During market - Monitor every 2 minutes")
        
        return True
        
    except Exception as e:
        print(f"❌ Scheduler error: {e}")
        return False

def verify_trading_logic():
    """Verify trading logic and methods"""
    print("\nChecking trading logic...")
    try:
        from paper_trader import PaperTrader
        trader = PaperTrader()
        
        # Check methods exist
        methods = [
            'execute_morning_trades',
            'close_all_positions',
            'monitoring_cycle',
            'get_current_price',
            'check_exit_conditions'
        ]
        
        for method in methods:
            if hasattr(trader, method):
                print(f"✅ Method: {method}")
            else:
                print(f"❌ Missing method: {method}")
                return False
        
        # Check configuration
        print(f"\nTrading configuration:")
        print(f"• Position size: {trader.trade_percentage * 100}% per trade")
        print(f"• Profit target: {trader.profit_target * 100}%")
        print(f"• Stop loss: {trader.stop_loss * 100}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Trading logic error: {e}")
        return False

def main():
    """Main verification process"""
    print("=" * 60)
    print("TRADING SYSTEM VERIFICATION")
    print("=" * 60)
    
    all_good = True
    
    # Run all verifications
    if not verify_imports():
        all_good = False
    
    if not verify_database():
        all_good = False
    
    if not verify_scheduler():
        all_good = False
    
    if not verify_trading_logic():
        all_good = False
    
    # Final status
    print("\n" + "=" * 60)
    if all_good:
        print("✅ SYSTEM VERIFICATION PASSED")
        print("\nThe trading system is configured correctly and ready to run.")
        print("\nTo start the scheduler, run:")
        print("  ./start_trading_system.sh")
        print("\nOr manually:")
        print("  python3 trading_scheduler.py")
    else:
        print("❌ SYSTEM VERIFICATION FAILED")
        print("\nPlease fix the errors above before running the trading system.")
        sys.exit(1)
    
    print("=" * 60)

if __name__ == "__main__":
    main()