#!/usr/bin/env python3
"""
Simple Trading Scheduler Daemon
A lightweight daemon that ensures trading schedules execute properly.
"""

import os
import time
import schedule
import logging
from datetime import datetime
import pytz
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - SCHEDULER - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler_daemon.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TradingDaemon:
    def __init__(self):
        self.running = True
        self.est_tz = pytz.timezone('US/Eastern')
        
    def update_market_data(self):
        """Update market data at 10:05 AM EST"""
        try:
            from scheduler import save_market_data
            current_time = datetime.now(self.est_tz)
            logger.info(f"Executing scheduled market data update at {current_time.strftime('%I:%M %p EST')}")
            save_market_data()
            logger.info("Market data update completed successfully")
        except Exception as e:
            logger.error(f"Error updating market data: {e}")
    
    def execute_morning_trades(self):
        """Execute morning trades at 10:15 AM EST"""
        try:
            from paper_trader import trader
            current_time = datetime.now(self.est_tz)
            logger.info(f"Executing scheduled morning trades at {current_time.strftime('%I:%M %p EST')}")
            trader.morning_trade_execution()
            logger.info("Morning trades completed successfully")
        except Exception as e:
            logger.error(f"Error executing morning trades: {e}")
    
    def execute_eod_close(self):
        """Execute end-of-day close at 3:34 PM EST"""
        try:
            from paper_trader import trader
            current_time = datetime.now(self.est_tz)
            logger.info(f"Executing scheduled end-of-day close at {current_time.strftime('%I:%M %p EST')}")
            trader.end_of_day_close()
            logger.info("End-of-day closure completed successfully")
        except Exception as e:
            logger.error(f"Error executing end-of-day close: {e}")
    
    def schedule_tasks(self):
        """Schedule all trading tasks"""
        # Convert EST times to UTC for scheduling (EST is UTC-5, but using local time)
        # Schedule data updates at 10:05 AM EST
        schedule.every().monday.at("10:05").do(self.update_market_data)
        schedule.every().tuesday.at("10:05").do(self.update_market_data)
        schedule.every().wednesday.at("10:05").do(self.update_market_data)
        schedule.every().thursday.at("10:05").do(self.update_market_data)
        schedule.every().friday.at("10:05").do(self.update_market_data)
        
        # Schedule morning trades at 10:15 AM EST
        schedule.every().monday.at("10:15").do(self.execute_morning_trades)
        schedule.every().tuesday.at("10:15").do(self.execute_morning_trades)
        schedule.every().wednesday.at("10:15").do(self.execute_morning_trades)
        schedule.every().thursday.at("10:15").do(self.execute_morning_trades)
        schedule.every().friday.at("10:15").do(self.execute_morning_trades)
        
        # Schedule end-of-day close at 3:34 PM EST
        schedule.every().monday.at("15:34").do(self.execute_eod_close)
        schedule.every().tuesday.at("15:34").do(self.execute_eod_close)
        schedule.every().wednesday.at("15:34").do(self.execute_eod_close)
        schedule.every().thursday.at("15:34").do(self.execute_eod_close)
        schedule.every().friday.at("15:34").do(self.execute_eod_close)
        
        logger.info("Trading schedule configured:")
        logger.info("• 10:05 AM EST - Market data updates (Mon-Fri)")
        logger.info("• 10:15 AM EST - Morning trades (Mon-Fri)")
        logger.info("• 3:34 PM EST - End-of-day close (Mon-Fri)")
    
    def run(self):
        """Main daemon loop"""
        logger.info("Trading scheduler daemon starting...")
        self.schedule_tasks()
        
        while self.running:
            try:
                schedule.run_pending()
                
                # Log status every hour
                now = datetime.now(self.est_tz)
                if now.minute == 0:  # Top of each hour
                    logger.info(f"Scheduler running - Current time: {now.strftime('%I:%M %p EST')}")
                    if now.weekday() < 5:  # Weekdays only
                        next_jobs = schedule.jobs
                        if next_jobs:
                            logger.info(f"Next scheduled job in: {schedule.idle_seconds():.0f} seconds")
                
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)
    
    def stop(self):
        """Stop the daemon"""
        logger.info("Trading scheduler daemon stopping...")
        self.running = False

# Global daemon instance for signal handling
daemon = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    if daemon:
        daemon.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    daemon = TradingDaemon()
    
    print("=" * 60)
    print("TRADING SCHEDULER DAEMON STARTING")
    print("=" * 60)
    print("Scheduled Tasks:")
    print("• 10:05 AM EST - Market data updates (Monday-Friday)")
    print("• 10:15 AM EST - Execute momentum trades (Monday-Friday)")
    print("• 3:34 PM EST - End-of-day closure (Monday-Friday)")
    print("=" * 60)
    print("The daemon will run continuously and log to: scheduler_daemon.log")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        daemon.run()
    except Exception as e:
        logger.error(f"Daemon error: {e}")
    finally:
        if daemon:
            daemon.stop()
        print("Trading scheduler daemon stopped.")