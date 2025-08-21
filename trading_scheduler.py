#!/usr/bin/env python3
"""
Trading Scheduler - Reliable automated trading system
Handles daily trades at 10:15 AM EST and manages positions throughout the day
"""

import schedule
import time
import threading
import logging
from datetime import datetime, timedelta
import pytz
import os
import signal
import sys
from paper_trader import PaperTrader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingScheduler:
    def __init__(self):
        self.trader = PaperTrader()
        self.est_tz = pytz.timezone('US/Eastern')
        self.running = True
        self.monitoring_thread = None
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logger.info("Trading Scheduler initialized")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        sys.exit(0)
    
    def is_market_day(self):
        """Check if today is a trading day (Monday-Friday)"""
        now = datetime.now(self.est_tz)
        # Monday = 0, Friday = 4
        return now.weekday() < 5
    
    def is_market_hours(self):
        """Check if market is open (9:30 AM - 4:00 PM EST)"""
        now = datetime.now(self.est_tz)
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_open <= now <= market_close and self.is_market_day()
    
    def update_market_data(self):
        """Update cached market data at 10:05 AM EST"""
        try:
            if not self.is_market_day():
                logger.info("Not a trading day, skipping market data update")
                return
            
            logger.info("Starting market data update at 10:05 AM EST")
            
            # Import and run the data update function
            from app import save_market_data
            save_market_data()
            
            logger.info("Market data update completed successfully")
            
        except Exception as e:
            logger.error(f"Error updating market data: {e}")
    
    def execute_morning_trades(self):
        """Execute morning trades at 10:15 AM EST"""
        try:
            if not self.is_market_day():
                logger.info("Not a trading day, skipping morning trades")
                return
            
            logger.info("=" * 60)
            logger.info("EXECUTING MORNING TRADES AT 10:15 AM EST")
            logger.info("=" * 60)
            
            # Execute the morning trades
            self.trader.execute_morning_trades()
            
            # Start monitoring thread if not already running
            if self.monitoring_thread is None or not self.monitoring_thread.is_alive():
                self.start_monitoring()
            
            logger.info("Morning trades executed successfully")
            
        except Exception as e:
            logger.error(f"Error executing morning trades: {e}")
    
    def close_all_positions(self):
        """Close all positions at 3:34 PM EST"""
        try:
            if not self.is_market_day():
                logger.info("Not a trading day, skipping EOD closure")
                return
            
            logger.info("=" * 60)
            logger.info("CLOSING ALL POSITIONS AT 3:34 PM EST")
            logger.info("=" * 60)
            
            self.trader.close_all_positions()
            
            logger.info("All positions closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
    
    def monitoring_loop(self):
        """Continuous monitoring loop that runs during market hours"""
        logger.info("Starting position monitoring thread")
        
        while self.running and self.is_market_hours():
            try:
                # Run monitoring cycle every 2 minutes
                self.trader.monitoring_cycle()
                
                # Wait 2 minutes before next check
                for _ in range(120):  # 120 seconds = 2 minutes
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
        
        logger.info("Monitoring loop ended")
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        if self.is_market_hours():
            self.monitoring_thread = threading.Thread(target=self.monitoring_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            logger.info("Monitoring thread started")
    
    def schedule_tasks(self):
        """Schedule all daily tasks"""
        # Clear any existing schedules
        schedule.clear()
        
        # Schedule market data update at 10:05 AM EST
        schedule.every().day.at("10:05").do(self.update_market_data)
        
        # Schedule morning trades at 10:15 AM EST
        schedule.every().day.at("10:15").do(self.execute_morning_trades)
        
        # Schedule EOD closure at 3:34 PM EST
        schedule.every().day.at("15:34").do(self.close_all_positions)
        
        logger.info("Scheduled tasks:")
        logger.info("  - Market data update: 10:05 AM EST")
        logger.info("  - Morning trades: 10:15 AM EST")
        logger.info("  - EOD closure: 3:34 PM EST")
    
    def run(self):
        """Main scheduler loop"""
        logger.info("=" * 60)
        logger.info("TRADING SCHEDULER STARTED")
        logger.info("=" * 60)
        
        # Schedule all tasks
        self.schedule_tasks()
        
        # Log next scheduled runs
        now = datetime.now(self.est_tz)
        logger.info(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"Market day: {self.is_market_day()}")
        logger.info(f"Market hours: {self.is_market_hours()}")
        
        # Start monitoring if market is open
        if self.is_market_hours():
            self.start_monitoring()
        
        # Main scheduler loop
        while self.running:
            try:
                # Run pending scheduled tasks
                schedule.run_pending()
                
                # Sleep for 1 second
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(5)  # Wait 5 seconds before continuing
        
        logger.info("Trading Scheduler stopped")

def main():
    """Main entry point"""
    scheduler = TradingScheduler()
    
    try:
        scheduler.run()
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()