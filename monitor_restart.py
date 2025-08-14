#!/usr/bin/env python3
"""
Reliable Paper Trading Monitor
Creates a robust monitoring system that automatically restarts if it crashes
"""

import os
import sys
import time
import subprocess
import logging
from datetime import datetime, timedelta
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitor_restart.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class RobustMonitor:
    def __init__(self):
        self.process = None
        self.est_tz = pytz.timezone('US/Eastern')
        
    def is_market_open(self):
        """Check if market is currently open"""
        now = datetime.now(self.est_tz)
        
        # Check if it's a weekday
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Market hours: 9:30 AM - 4:00 PM EST
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= now <= market_close
        
    def start_monitor(self):
        """Start the monitoring process"""
        try:
            self.process = subprocess.Popen(
                [sys.executable, 'run_scheduler.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )
            logger.info(f"Started monitoring process with PID: {self.process.pid}")
            return True
        except Exception as e:
            logger.error(f"Failed to start monitoring process: {e}")
            return False
    
    def is_monitor_alive(self):
        """Check if the monitoring process is still running"""
        if self.process is None:
            return False
        return self.process.poll() is None
    
    def manual_update(self):
        """Manually trigger a portfolio update"""
        try:
            from paper_trader import trader
            trader.monitoring_cycle()
            logger.info("Manual portfolio update completed")
        except Exception as e:
            logger.error(f"Manual update failed: {e}")
    
    def run_forever(self):
        """Keep the monitor running with automatic restarts"""
        logger.info("Starting robust paper trading monitor...")
        
        while True:
            try:
                current_time = datetime.now(self.est_tz)
                
                if self.is_market_open():
                    # During market hours, ensure monitor is running
                    if not self.is_monitor_alive():
                        logger.warning("Monitor process not running during market hours - restarting...")
                        self.start_monitor()
                        time.sleep(5)  # Give it time to start
                        
                        # If it still failed, do manual update
                        if not self.is_monitor_alive():
                            logger.warning("Process restart failed - doing manual update")
                            self.manual_update()
                    else:
                        logger.info(f"Monitor running normally at {current_time.strftime('%I:%M %p EST')}")
                    
                    # Check every 5 minutes during market hours
                    sleep_time = 300
                else:
                    logger.info(f"Market closed at {current_time.strftime('%I:%M %p EST')} - monitor can be idle")
                    # Check every 30 minutes when market is closed
                    sleep_time = 1800
                
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                logger.info("Shutting down robust monitor...")
                if self.process:
                    self.process.terminate()
                break
            except Exception as e:
                logger.error(f"Error in robust monitor: {e}")
                time.sleep(60)

if __name__ == "__main__":
    monitor = RobustMonitor()
    
    # Do an immediate manual update first
    print("Performing immediate portfolio update...")
    monitor.manual_update()
    
    print("Starting robust monitoring system...")
    print("This will automatically restart the scheduler if it crashes")
    print("Press Ctrl+C to stop")
    
    monitor.run_forever()