#!/usr/bin/env python3
"""
Persistent Trading Scheduler
Ensures scheduled tasks run reliably in the background.
This script should be run as a separate process and will restart itself if it crashes.
"""

import os
import sys
import time
import signal
import subprocess
import logging
from datetime import datetime
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('persistent_scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class PersistentScheduler:
    def __init__(self):
        self.running = True
        self.scheduler_process = None
        self.est_tz = pytz.timezone('US/Eastern')
    
    def start_scheduler(self):
        """Start the trading scheduler process"""
        try:
            logger.info("Starting trading scheduler process...")
            self.scheduler_process = subprocess.Popen(
                [sys.executable, 'run_scheduler.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"Scheduler started with PID: {self.scheduler_process.pid}")
            return True
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return False
    
    def check_scheduler_health(self):
        """Check if scheduler process is still running"""
        if self.scheduler_process is None:
            return False
        
        poll_result = self.scheduler_process.poll()
        if poll_result is None:
            return True  # Process is still running
        else:
            logger.warning(f"Scheduler process died with exit code: {poll_result}")
            return False
    
    def restart_scheduler(self):
        """Restart the scheduler process"""
        logger.info("Restarting scheduler process...")
        if self.scheduler_process:
            try:
                self.scheduler_process.terminate()
                self.scheduler_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.scheduler_process.kill()
        
        return self.start_scheduler()
    
    def run(self):
        """Main loop to monitor and maintain scheduler"""
        logger.info("Persistent scheduler starting...")
        
        # Start initial scheduler
        if not self.start_scheduler():
            logger.error("Failed to start initial scheduler")
            return
        
        while self.running:
            try:
                # Check scheduler health every 30 seconds
                if not self.check_scheduler_health():
                    logger.warning("Scheduler unhealthy, attempting restart...")
                    if not self.restart_scheduler():
                        logger.error("Failed to restart scheduler, retrying in 60 seconds...")
                        time.sleep(60)
                        continue
                
                # Check system time for important scheduled events
                now = datetime.now(self.est_tz)
                if now.weekday() < 5:  # Monday-Friday only
                    current_time = now.strftime('%H:%M')
                    
                    # Log important upcoming events
                    if current_time == '10:00':
                        logger.info("Data update scheduled in 5 minutes (10:05 AM EST)")
                    elif current_time == '10:10':
                        logger.info("Trade execution scheduled in 5 minutes (10:15 AM EST)")
                    elif current_time == '15:30':
                        logger.info("End-of-day closure scheduled in 4 minutes (3:34 PM EST)")
                
                time.sleep(30)  # Check every 30 seconds
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)
    
    def stop(self):
        """Stop the scheduler and cleanup"""
        logger.info("Stopping persistent scheduler...")
        self.running = False
        
        if self.scheduler_process:
            try:
                self.scheduler_process.terminate()
                self.scheduler_process.wait(timeout=10)
                logger.info("Scheduler process terminated")
            except subprocess.TimeoutExpired:
                logger.warning("Scheduler process didn't terminate, killing...")
                self.scheduler_process.kill()
            except Exception as e:
                logger.error(f"Error stopping scheduler: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    if 'persistent_scheduler' in globals():
        persistent_scheduler.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    persistent_scheduler = PersistentScheduler()
    
    print("=" * 60)
    print("PERSISTENT TRADING SCHEDULER STARTING")
    print("=" * 60)
    print("This process will:")
    print("• Monitor the trading scheduler for crashes")
    print("• Automatically restart failed processes") 
    print("• Ensure scheduled trades execute reliably")
    print("• Log all scheduler activity")
    print("=" * 60)
    print("Schedule:")
    print("• 10:05 AM EST - Market data updates (Mon-Fri)")
    print("• 10:15 AM EST - Execute trades (Mon-Fri)")
    print("• 3:34 PM EST - End-of-day closure (Mon-Fri)")
    print("• 2-minute monitoring during market hours")
    print("=" * 60)
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        persistent_scheduler.run()
    except Exception as e:
        logger.error(f"Persistent scheduler error: {e}")
    finally:
        persistent_scheduler.stop()
        print("\nPersistent scheduler stopped.")