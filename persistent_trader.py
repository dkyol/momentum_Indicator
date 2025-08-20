#!/usr/bin/env python3
"""
Persistent Trading System
Robust background scheduler that handles all trading operations.
"""

import os
import time
import logging
import signal
import sys
from datetime import datetime, timedelta
import pytz
import schedule

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - TRADER - %(message)s',
    handlers=[
        logging.FileHandler('persistent_trader.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class PersistentTrader:
    def __init__(self):
        self.running = True
        self.est = pytz.timezone('US/Eastern')
        
    def update_market_data(self):
        """Update all market data tables"""
        try:
            logger.info("Starting market data update...")
            from scheduler import save_market_data
            save_market_data()
            logger.info("Market data update completed successfully")
        except Exception as e:
            logger.error(f"Market data update failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def execute_morning_trades(self):
        """Execute morning momentum trades"""
        try:
            logger.info("Starting morning trade execution...")
            from paper_trader import trader
            trader.morning_trade_execution()
            
            # Log portfolio status
            portfolio = trader.get_portfolio_summary()
            logger.info(f"Trades completed - Portfolio: ${portfolio['total_value']:.2f}, Positions: {len(portfolio['positions'])}")
            
        except Exception as e:
            logger.error(f"Morning trade execution failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def execute_eod_close(self):
        """Execute end-of-day position closure"""
        try:
            logger.info("Starting end-of-day closure...")
            from paper_trader import trader
            trader.end_of_day_close()
            
            # Log final portfolio status
            portfolio = trader.get_portfolio_summary()
            logger.info(f"EOD closure completed - Portfolio: ${portfolio['total_value']:.2f}, Positions: {len(portfolio['positions'])}")
            
        except Exception as e:
            logger.error(f"End-of-day closure failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def setup_schedule(self):
        """Setup all scheduled tasks"""
        # Market data updates at 10:05 AM EST (Monday-Friday)
        schedule.every().monday.at("10:05").do(self.update_market_data)
        schedule.every().tuesday.at("10:05").do(self.update_market_data)
        schedule.every().wednesday.at("10:05").do(self.update_market_data)
        schedule.every().thursday.at("10:05").do(self.update_market_data)
        schedule.every().friday.at("10:05").do(self.update_market_data)
        
        # Morning trades at 10:15 AM EST (Monday-Friday)
        schedule.every().monday.at("10:15").do(self.execute_morning_trades)
        schedule.every().tuesday.at("10:15").do(self.execute_morning_trades)
        schedule.every().wednesday.at("10:15").do(self.execute_morning_trades)
        schedule.every().thursday.at("10:15").do(self.execute_morning_trades)
        schedule.every().friday.at("10:15").do(self.execute_morning_trades)
        
        # End-of-day closure at 3:34 PM EST (Monday-Friday)
        schedule.every().monday.at("15:34").do(self.execute_eod_close)
        schedule.every().tuesday.at("15:34").do(self.execute_eod_close)
        schedule.every().wednesday.at("15:34").do(self.execute_eod_close)
        schedule.every().thursday.at("15:34").do(self.execute_eod_close)
        schedule.every().friday.at("15:34").do(self.execute_eod_close)
        
        logger.info("Schedule configured:")
        logger.info("  • 10:05 AM EST - Market data updates (Mon-Fri)")
        logger.info("  • 10:15 AM EST - Morning trades (Mon-Fri)")
        logger.info("  • 3:34 PM EST - End-of-day closure (Mon-Fri)")
    
    def run(self):
        """Main execution loop"""
        now = datetime.now(self.est)
        logger.info("=" * 50)
        logger.info("PERSISTENT TRADING SYSTEM STARTED")
        logger.info("=" * 50)
        logger.info(f"Start time: {now.strftime('%A, %B %d, %Y at %I:%M %p EST')}")
        
        self.setup_schedule()
        
        # Log next scheduled event
        next_run = schedule.next_run()
        if next_run:
            logger.info(f"Next scheduled task: {next_run}")
        
        logger.info("System running continuously...")
        logger.info("=" * 50)
        
        while self.running:
            try:
                schedule.run_pending()
                
                # Log hourly status
                current_time = datetime.now(self.est)
                if current_time.minute == 0:  # Top of each hour
                    logger.info(f"System running - {current_time.strftime('%I:%M %p EST')}")
                    
                    # Show next scheduled task
                    next_run = schedule.next_run()
                    if next_run:
                        time_until = (next_run - datetime.now()).total_seconds()
                        hours = int(time_until // 3600)
                        minutes = int((time_until % 3600) // 60)
                        logger.info(f"Next task in: {hours}h {minutes}m")
                
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait before retrying
    
    def stop(self):
        """Stop the trading system"""
        logger.info("Stopping persistent trading system...")
        self.running = False

# Global instance for signal handling
trader_system = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    if trader_system:
        trader_system.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    trader_system = PersistentTrader()
    trader_system.run()