#!/usr/bin/env python3
"""
Background Trading Monitor
Runs the paper trading monitoring system in the background.
This should be started separately from the web application.
"""

import sys
import os
import time
import threading
import signal
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from paper_trader import trader
import schedule
import logging
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TradingMonitor:
    def __init__(self):
        self.running = True
        self.est_tz = pytz.timezone('US/Eastern')
    
    def stop(self):
        self.running = False
        logger.info("Trading monitor stopped")
    
    def is_market_open(self):
        """Check if market is currently open (9:30 AM - 4:00 PM EST, Mon-Fri)"""
        now = datetime.now(self.est_tz)
        
        # Check if it's a weekday
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Market hours: 9:30 AM - 4:00 PM EST
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= now <= market_close
    
    def continuous_monitor(self):
        """Continuously monitor positions during market hours"""
        logger.info("Starting continuous trading monitor...")
        
        while self.running:
            try:
                current_time = datetime.now(self.est_tz)
                
                if self.is_market_open():
                    logger.info(f"Market is OPEN - Running 2-minute monitoring cycle at {current_time.strftime('%I:%M %p EST')}")
                    
                    # Run monitoring cycle (will check positions and update portfolio timestamp)
                    trader.monitoring_cycle()
                    
                    # Sleep for exactly 2 minutes during market hours
                    sleep_time = 120  # 2 minutes
                    next_check = (current_time + timedelta(minutes=2)).strftime('%I:%M %p EST')
                    logger.info(f"Market monitoring: Next position check scheduled for {next_check}")
                else:
                    logger.info(f"Market is CLOSED - No monitoring needed. Current time: {current_time.strftime('%I:%M %p EST')}")
                    # Sleep for 30 minutes when market is closed
                    sleep_time = 1800  # 30 minutes during non-market hours
                
                # Sleep in smaller chunks to allow for graceful shutdown
                for _ in range(sleep_time // 10):
                    if not self.running:
                        break
                    time.sleep(10)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def schedule_daily_trades(self):
        """Schedule daily morning trades and data updates"""
        # Schedule data updates at 10:05 AM EST (converted to UTC)
        schedule.every().monday.at("15:05").do(self.update_market_data)  # 10:05 AM EST = 15:05 UTC (EST+5)
        schedule.every().tuesday.at("15:05").do(self.update_market_data)
        schedule.every().wednesday.at("15:05").do(self.update_market_data)
        schedule.every().thursday.at("15:05").do(self.update_market_data)
        schedule.every().friday.at("15:05").do(self.update_market_data)
        
        # Schedule morning trades at 10:15 AM EST (after data updates)
        schedule.every().monday.at("15:15").do(trader.morning_trade_execution)  # 10:15 AM EST = 15:15 UTC (EST+5)
        schedule.every().tuesday.at("15:15").do(trader.morning_trade_execution)
        schedule.every().wednesday.at("15:15").do(trader.morning_trade_execution)
        schedule.every().thursday.at("15:15").do(trader.morning_trade_execution)
        schedule.every().friday.at("15:15").do(trader.morning_trade_execution)
        
        # Schedule end-of-day close at 3:34 PM EST
        schedule.every().monday.at("20:34").do(trader.end_of_day_close)  # 3:34 PM EST = 20:34 UTC
        schedule.every().tuesday.at("20:34").do(trader.end_of_day_close)
        schedule.every().wednesday.at("20:34").do(trader.end_of_day_close)
        schedule.every().thursday.at("20:34").do(trader.end_of_day_close)
        schedule.every().friday.at("20:34").do(trader.end_of_day_close)
        
        logger.info("Daily trading schedule configured")
        logger.info("Data updates: 10:05 AM EST (Monday-Friday)")
        logger.info("Morning trades: 10:15 AM EST (Monday-Friday)")
        logger.info("End-of-day close: 3:34 PM EST (Monday-Friday)")
    
    def update_market_data(self):
        """Update market data at 10:05 AM EST"""
        try:
            current_time = datetime.now(self.est_tz)
            logger.info(f"Starting scheduled market data update at {current_time.strftime('%I:%M %p EST')}")
            
            # Import and call the data update function
            from scheduler import save_market_data
            save_market_data()
            
            logger.info("Market data update completed successfully")
        except Exception as e:
            logger.error(f"Error updating market data: {e}")
    
    def run_scheduler(self):
        """Run scheduled tasks (morning trades and EOD close)"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute for scheduled tasks
            except KeyboardInterrupt:
                logger.info("Scheduler interrupted")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(60)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down...")
    monitor.stop()

if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    monitor = TradingMonitor()
    
    print("=" * 60)
    print("PAPER TRADING MONITOR STARTING")
    print("=" * 60)
    print("Trading Strategy:")
    print("• Daily data update: 10:05 AM EST (Monday-Friday)")
    print("• Daily entry: 10:15 AM EST (top 2 momentum stocks)")
    print("• 2-minute monitoring during market hours (9:30 AM - 4:00 PM EST)")
    print("• Exit conditions: +3% profit, -0.8% stop loss, or 3:34 PM EST")
    print("• Initial investment: $10,000")
    print("• Position size: 10% per trade")
    print("=" * 60)
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        # Schedule daily trades
        monitor.schedule_daily_trades()
        
        # Start scheduler in a separate thread
        scheduler_thread = threading.Thread(target=monitor.run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Start continuous monitoring (main thread)
        monitor.continuous_monitor()
        
    except KeyboardInterrupt:
        logger.info("Trading monitor stopped by user")
    except Exception as e:
        logger.error(f"Trading monitor error: {e}")
    finally:
        monitor.stop()
        print("\nTrading monitor stopped.")