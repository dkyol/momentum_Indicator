#!/usr/bin/env python3
"""
Simple Scheduler Keeper - Ensures trading scheduler stays running
"""

import subprocess
import time
import logging
from datetime import datetime
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler_keeper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def is_market_hours():
    """Check if it's market hours"""
    est_tz = pytz.timezone('US/Eastern')
    now = datetime.now(est_tz)
    
    # Check weekday
    if now.weekday() >= 5:
        return False
    
    # Check time (9:30 AM - 4:00 PM EST)
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= now <= market_close

def is_scheduler_running():
    """Check if scheduler is running"""
    try:
        result = subprocess.run(['pgrep', '-f', 'trading_scheduler.py'], 
                               capture_output=True, text=True)
        return bool(result.stdout.strip())
    except:
        return False

def start_scheduler():
    """Start the scheduler"""
    try:
        logger.info("Starting trading scheduler...")
        subprocess.run(['python3', 'trading_scheduler.py', '&'], shell=True)
        time.sleep(3)
        if is_scheduler_running():
            logger.info("Scheduler started successfully")
            return True
        else:
            logger.error("Scheduler failed to start")
            return False
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        return False

def main():
    logger.info("Scheduler Keeper started")
    
    while True:
        try:
            market_open = is_market_hours()
            scheduler_running = is_scheduler_running()
            
            if market_open and not scheduler_running:
                logger.warning("Market open but scheduler not running - starting...")
                start_scheduler()
            elif scheduler_running:
                logger.info("Scheduler running normally")
            
            # Check every 60 seconds
            time.sleep(60)
            
        except KeyboardInterrupt:
            logger.info("Scheduler Keeper stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in keeper loop: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()