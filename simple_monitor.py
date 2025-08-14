#!/usr/bin/env python3
"""
Simple 15-minute monitoring loop for paper trading
Runs directly without subprocess complications
"""

import time
import sys
import os
from datetime import datetime, timedelta
import pytz
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('simple_monitor')

def is_market_open():
    """Check if market is currently open"""
    est_tz = pytz.timezone('US/Eastern')
    now = datetime.now(est_tz)
    
    # Check if it's a weekday
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Market hours: 9:30 AM - 4:00 PM EST
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= now <= market_close

def run_monitoring():
    """Run the 15-minute monitoring loop"""
    from paper_trader import trader
    
    logger.info("Starting simple 15-minute monitoring system...")
    
    while True:
        try:
            est_tz = pytz.timezone('US/Eastern')
            current_time = datetime.now(est_tz)
            
            if is_market_open():
                logger.info(f"Market OPEN - Running monitoring at {current_time.strftime('%I:%M %p EST')}")
                
                # Run the monitoring cycle
                trader.monitoring_cycle()
                
                # Sleep for exactly 15 minutes
                logger.info("Monitoring complete - sleeping for 15 minutes")
                time.sleep(900)  # 15 minutes = 900 seconds
                
            else:
                logger.info(f"Market CLOSED at {current_time.strftime('%I:%M %p EST')} - checking again in 30 minutes")
                time.sleep(1800)  # 30 minutes when market is closed
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in monitoring: {e}")
            logger.info("Retrying in 5 minutes...")
            time.sleep(300)  # Wait 5 minutes before retry

if __name__ == "__main__":
    # Do immediate update first
    try:
        from paper_trader import trader
        logger.info("Performing immediate portfolio update...")
        trader.monitoring_cycle()
        logger.info("Immediate update complete")
    except Exception as e:
        logger.error(f"Immediate update failed: {e}")
    
    # Start the monitoring loop
    run_monitoring()