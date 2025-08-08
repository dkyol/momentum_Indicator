#!/usr/bin/env python3
"""
Background scheduler runner for market data updates.
This runs the scheduler in a separate process to update data daily at 5 PM EST.
"""

import schedule
import time
import logging
import pytz
from datetime import datetime
from scheduler import save_market_data, is_data_fresh

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    Main scheduler loop that runs market data updates daily at 5 PM EST.
    """
    logger.info("Starting market data scheduler...")
    
    # Set timezone to EST for scheduling
    est = pytz.timezone('US/Eastern')
    
    # Schedule daily update at 5 PM EST
    schedule.every().day.at("17:00").do(save_market_data)
    
    # Run initial update if no fresh data exists
    if not is_data_fresh():
        logger.info("No fresh data found, running initial update...")
        save_market_data()
    else:
        logger.info("Fresh data already exists, using cached data")
    
    logger.info("Scheduler configured. Market data will update daily at 5:00 PM EST")
    logger.info("Current time: {}".format(datetime.now(est).strftime("%Y-%m-%d %H:%M:%S %Z")))
    
    # Keep the scheduler running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")
            time.sleep(60)  # Continue running even if there's an error

if __name__ == "__main__":
    main()