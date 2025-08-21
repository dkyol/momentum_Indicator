#!/usr/bin/env python3
"""
Scheduler Watchdog - Ensures the trading scheduler stays running during market hours
"""

import time
import subprocess
import logging
import os
import signal
from datetime import datetime
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler_watchdog.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SchedulerWatchdog:
    def __init__(self):
        self.est_tz = pytz.timezone('US/Eastern')
        self.scheduler_process = None
        self.running = True
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logger.info("Scheduler Watchdog initialized")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        if self.scheduler_process:
            self.scheduler_process.terminate()
    
    def is_market_hours(self):
        """Check if it's during market hours (9:30 AM - 4:00 PM EST, Mon-Fri)"""
        now = datetime.now(self.est_tz)
        
        # Check if it's a weekday
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check if it's during market hours
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= now <= market_close
    
    def is_scheduler_running(self):
        """Check if the trading scheduler is running"""
        try:
            result = subprocess.run(['pgrep', '-f', 'trading_scheduler.py'], 
                                   capture_output=True, text=True)
            return bool(result.stdout.strip())
        except Exception as e:
            logger.error(f"Error checking scheduler status: {e}")
            return False
    
    def start_scheduler(self):
        """Start the trading scheduler"""
        try:
            logger.info("Starting trading scheduler...")
            
            # Kill any existing scheduler processes first
            subprocess.run(['pkill', '-f', 'trading_scheduler.py'], 
                          capture_output=True)
            time.sleep(2)
            
            # Start new scheduler process
            self.scheduler_process = subprocess.Popen(
                ['python3', 'trading_scheduler.py'],
                stdout=open('trading_scheduler.log', 'a'),
                stderr=subprocess.STDOUT
            )
            
            # Wait a moment and check if it started successfully
            time.sleep(3)
            if self.is_scheduler_running():
                logger.info(f"Trading scheduler started successfully (PID: {self.scheduler_process.pid})")
                return True
            else:
                logger.error("Trading scheduler failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            return False
    
    def monitor_scheduler(self):
        """Main monitoring loop"""
        logger.info("Starting scheduler monitoring...")
        
        while self.running:
            try:
                now = datetime.now(self.est_tz)
                is_market_time = self.is_market_hours()
                scheduler_running = self.is_scheduler_running()
                
                if is_market_time:
                    if not scheduler_running:
                        logger.warning("Scheduler not running during market hours - restarting...")
                        if self.start_scheduler():
                            logger.info("Scheduler successfully restarted")
                        else:
                            logger.error("Failed to restart scheduler")
                    else:
                        logger.debug(f"Scheduler running normally at {now.strftime('%I:%M %p EST')}")
                else:
                    if scheduler_running:
                        logger.info("Market closed - scheduler will continue running for next day preparation")
                    else:
                        logger.info("Market closed - scheduler not running (normal)")
                
                # Check every 30 seconds during market hours, every 5 minutes otherwise
                sleep_time = 30 if is_market_time else 300
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
        
        logger.info("Scheduler monitoring stopped")
    
    def run(self):
        """Main entry point"""
        logger.info("=" * 60)
        logger.info("SCHEDULER WATCHDOG STARTED")
        logger.info("=" * 60)
        
        # Start scheduler if we're in market hours
        if self.is_market_hours():
            if not self.is_scheduler_running():
                self.start_scheduler()
        
        # Start monitoring
        try:
            self.monitor_scheduler()
        except KeyboardInterrupt:
            logger.info("Watchdog interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error in watchdog: {e}")

def main():
    watchdog = SchedulerWatchdog()
    watchdog.run()

if __name__ == "__main__":
    main()