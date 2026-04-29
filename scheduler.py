#!/usr/bin/env python3
"""
Market Data Scheduler
Fetches high volume stocks and momentum analysis data once daily at 10:05 AM EST.
"""

import schedule
import time
import json
import logging
import os
from datetime import datetime
import pytz
from stock_analytics import get_high_volume_data
from momentum_analyzer import get_momentum_summary
from sma_analyzer import get_sma_summary
from alpha_engine import refresh_alpha_data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Data file paths
HIGH_VOLUME_DATA_FILE = 'cached_high_volume_stocks.json'
MOMENTUM_DATA_FILE = 'cached_momentum_data.json'
SMA_DATA_FILE = 'cached_sma_data.json'
LAST_UPDATE_FILE = 'last_data_update.json'

def save_market_data():
    """
    Fetch and save high volume stocks and momentum analysis data.
    """
    try:
        logger.info("Starting synchronized daily market data update...")
        
        # Get current EST time
        est = pytz.timezone('US/Eastern')
        update_time = datetime.now(est)
        
        # Fetch high volume stocks data
        logger.info("Fetching high volume stocks data...")
        high_volume_df = get_high_volume_data()
        high_volume_stocks = []
        if not high_volume_df.empty:
            high_volume_stocks = high_volume_df.to_dict('records')
        
        # Get momentum analysis for all high volume stocks
        momentum_data = []
        sma_data = []
        if high_volume_stocks:
            all_symbols = [stock['Symbol'] for stock in high_volume_stocks]
            logger.info(f"Fetching momentum analysis for: {all_symbols}")
            momentum_data = get_momentum_summary(all_symbols)
            
            logger.info(f"Fetching SMA analysis for: {all_symbols}")
            sma_data = get_sma_summary(all_symbols)
        
        # Save data to files
        with open(HIGH_VOLUME_DATA_FILE, 'w') as f:
            json.dump(high_volume_stocks, f, default=str)
        
        with open(MOMENTUM_DATA_FILE, 'w') as f:
            json.dump(momentum_data, f, default=str)
        
        with open(SMA_DATA_FILE, 'w') as f:
            json.dump(sma_data, f, default=str)
        
        # Save last update timestamp
        update_info = {
            'last_update': update_time.isoformat(),
            'stocks_count': len(high_volume_stocks),
            'momentum_count': len(momentum_data),
            'sma_count': len(sma_data)
        }
        with open(LAST_UPDATE_FILE, 'w') as f:
            json.dump(update_info, f)
        
        logger.info(f"Market data updated successfully at {update_time}")
        logger.info(f"High volume stocks: {len(high_volume_stocks)}")
        logger.info(f"Momentum analysis: {len(momentum_data)}")
        logger.info(f"SMA analysis: {len(sma_data)}")
        
    except Exception as e:
        logger.error(f"Error updating market data: {e}")

def load_cached_data(file_path, default_value):
    """
    Load cached data from file, return default if file doesn't exist or is invalid.
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"Cached data file not found: {file_path}")
            return default_value
    except Exception as e:
        logger.error(f"Error loading cached data from {file_path}: {e}")
        return default_value

def get_cached_high_volume_stocks():
    """
    Get cached high volume stocks data.
    """
    return load_cached_data(HIGH_VOLUME_DATA_FILE, [])

def get_cached_momentum_data():
    """
    Get cached momentum analysis data.
    """
    return load_cached_data(MOMENTUM_DATA_FILE, [])

def get_cached_sma_data():
    """
    Get cached SMA analysis data.
    """
    return load_cached_data(SMA_DATA_FILE, [])

def get_last_update_info():
    """
    Get information about the last data update.
    """
    return load_cached_data(LAST_UPDATE_FILE, {})

def is_data_fresh():
    """
    Check if cached data is from today (after 10:05 AM EST).
    """
    try:
        update_info = get_last_update_info()
        if not update_info.get('last_update'):
            return False
        
        est = pytz.timezone('US/Eastern')
        last_update = datetime.fromisoformat(update_info['last_update'])
        today_1005am = datetime.now(est).replace(hour=10, minute=5, second=0, microsecond=0)
        
        # Data is fresh if it was updated today after 10:05 AM EST
        return last_update >= today_1005am and last_update.date() == today_1005am.date()
    except Exception as e:
        logger.error(f"Error checking data freshness: {e}")
        return False

def refresh_alpha_with_backtest():
    """Wrapper used by the nightly schedule – includes the slow backtest step."""
    try:
        refresh_alpha_data(include_backtest=True)
    except Exception as e:
        logger.error(f"Nightly alpha refresh failed: {e}")


def run_scheduler():
    """
    Run the scheduler to update market data daily at 10:05 AM EST.
    """
    logger.info("Starting market data scheduler...")
    
    # Schedule daily update at 10:05 AM EST (15:05 UTC during EST)
    schedule.every().monday.at("15:05").do(save_market_data)
    schedule.every().tuesday.at("15:05").do(save_market_data)
    schedule.every().wednesday.at("15:05").do(save_market_data)
    schedule.every().thursday.at("15:05").do(save_market_data)
    schedule.every().friday.at("15:05").do(save_market_data)

    # Schedule nightly alpha-engine refresh at 10:30 PM EST (after market
    # close, after fundamentals settle).  Includes the slow backtest step.
    schedule.every().monday.at("03:30").do(refresh_alpha_with_backtest)
    schedule.every().tuesday.at("03:30").do(refresh_alpha_with_backtest)
    schedule.every().wednesday.at("03:30").do(refresh_alpha_with_backtest)
    schedule.every().thursday.at("03:30").do(refresh_alpha_with_backtest)
    schedule.every().friday.at("03:30").do(refresh_alpha_with_backtest)
    schedule.every().saturday.at("03:30").do(refresh_alpha_with_backtest)
    
    # Run initial update if no fresh data exists
    if not is_data_fresh():
        logger.info("No fresh data found, running initial update...")
        save_market_data()
    
    logger.info("Scheduler configured. Market data will update daily at 10:05 AM EST (Monday-Friday)")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    # For manual testing
    save_market_data()