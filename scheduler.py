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
from datetime import datetime, time as dtime, timezone
import pytz
from stock_analytics import get_high_volume_data
from momentum_analyzer import get_momentum_summary
from sma_analyzer import get_sma_summary
from alpha_engine import refresh_alpha_data
from portfolio_stats import take_equity_snapshot

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


def daily_equity_snapshot():
    """Capture the end-of-day equity snapshot for the paper-trading book.

    Imports the trader lazily so this scheduler module stays importable
    even before the trader is initialised, and reuses the trader's own
    yfinance-backed price helper to mark open positions to market.
    """
    try:
        from paper_trader import trader as _trader
        price_fn = _trader.get_current_price if _trader else None
    except Exception as e:
        logger.error(f"Could not load paper trader for equity snapshot: {e}")
        price_fn = None
    try:
        take_equity_snapshot(get_current_price=price_fn)
    except Exception as e:
        logger.error(f"Daily equity snapshot failed: {e}")


def run_scheduler():
    """
    Run the scheduler to update market data daily at 10:05 AM EST.
    """
    logger.info("Starting market data scheduler...")
    
    # We want deterministic UTC-anchored slots so jobs fire at the same
    # wall-clock moment regardless of where the container is hosted.
    # The `schedule` library only understands the host process's *local*
    # time, so we convert each desired UTC slot into the equivalent
    # local-clock HH:MM at startup and register that with schedule.at().
    # In US/Eastern this lands at:
    #   * 15:05 UTC  -> 10:05 EST / 11:05 EDT  (post-open daily refresh)
    #   * 03:30 UTC  -> 22:30 EST / 23:30 EDT  (nightly alpha + backtest)
    # Caveat: if the host transitions DST mid-process, the absolute UTC
    # firing moment shifts by 1 hour until next restart.  Most cloud
    # hosts run on UTC where this is a no-op.
    UTC_DAILY_REFRESH_HHMM = (15, 5)
    UTC_NIGHTLY_ALPHA_HHMM = (3, 30)
    # 21:10 UTC -> 16:10 EST / 17:10 EDT, always after the 4 PM US close.
    UTC_EOD_SNAPSHOT_HHMM = (21, 10)

    def _utc_to_local_hhmm(hh: int, mm: int) -> str:
        """Convert a UTC HH:MM slot into the host's local-clock HH:MM
        so that schedule.at(...) fires at the intended UTC moment."""
        today = datetime.now(timezone.utc).date()
        utc_dt = datetime.combine(today, dtime(hour=hh, minute=mm), tzinfo=timezone.utc)
        local_dt = utc_dt.astimezone()  # uses host TZ
        return local_dt.strftime("%H:%M")

    LOCAL_DAILY_REFRESH = _utc_to_local_hhmm(*UTC_DAILY_REFRESH_HHMM)
    LOCAL_NIGHTLY_ALPHA = _utc_to_local_hhmm(*UTC_NIGHTLY_ALPHA_HHMM)
    LOCAL_EOD_SNAPSHOT = _utc_to_local_hhmm(*UTC_EOD_SNAPSHOT_HHMM)

    schedule.every().monday.at(LOCAL_DAILY_REFRESH).do(save_market_data)
    schedule.every().tuesday.at(LOCAL_DAILY_REFRESH).do(save_market_data)
    schedule.every().wednesday.at(LOCAL_DAILY_REFRESH).do(save_market_data)
    schedule.every().thursday.at(LOCAL_DAILY_REFRESH).do(save_market_data)
    schedule.every().friday.at(LOCAL_DAILY_REFRESH).do(save_market_data)

    schedule.every().monday.at(LOCAL_NIGHTLY_ALPHA).do(refresh_alpha_with_backtest)
    schedule.every().tuesday.at(LOCAL_NIGHTLY_ALPHA).do(refresh_alpha_with_backtest)
    schedule.every().wednesday.at(LOCAL_NIGHTLY_ALPHA).do(refresh_alpha_with_backtest)
    schedule.every().thursday.at(LOCAL_NIGHTLY_ALPHA).do(refresh_alpha_with_backtest)
    schedule.every().friday.at(LOCAL_NIGHTLY_ALPHA).do(refresh_alpha_with_backtest)
    schedule.every().saturday.at(LOCAL_NIGHTLY_ALPHA).do(refresh_alpha_with_backtest)

    # End-of-day equity snapshot for the portfolio dashboard (Mon-Fri).
    schedule.every().monday.at(LOCAL_EOD_SNAPSHOT).do(daily_equity_snapshot)
    schedule.every().tuesday.at(LOCAL_EOD_SNAPSHOT).do(daily_equity_snapshot)
    schedule.every().wednesday.at(LOCAL_EOD_SNAPSHOT).do(daily_equity_snapshot)
    schedule.every().thursday.at(LOCAL_EOD_SNAPSHOT).do(daily_equity_snapshot)
    schedule.every().friday.at(LOCAL_EOD_SNAPSHOT).do(daily_equity_snapshot)

    # Run initial update if no fresh data exists
    if not is_data_fresh():
        logger.info("No fresh data found, running initial update...")
        save_market_data()

    logger.info(
        "Scheduler configured.  Daily market refresh at %02d:%02d UTC "
        "(local %s, Mon-Fri); nightly alpha-engine + backtest at "
        "%02d:%02d UTC (local %s, Mon-Sat); EOD equity snapshot at "
        "%02d:%02d UTC (local %s, Mon-Fri).",
        UTC_DAILY_REFRESH_HHMM[0], UTC_DAILY_REFRESH_HHMM[1], LOCAL_DAILY_REFRESH,
        UTC_NIGHTLY_ALPHA_HHMM[0], UTC_NIGHTLY_ALPHA_HHMM[1], LOCAL_NIGHTLY_ALPHA,
        UTC_EOD_SNAPSHOT_HHMM[0], UTC_EOD_SNAPSHOT_HHMM[1], LOCAL_EOD_SNAPSHOT,
    )
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    # For manual testing
    save_market_data()