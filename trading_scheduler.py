#!/usr/bin/env python3
"""
Trading Scheduler - Runs the automated paper trading system
This script should be run as a background process to handle trading automation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from paper_trader import start_trading_scheduler
import logging

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('trading.log'),
            logging.StreamHandler()
        ]
    )
    
    print("Starting Paper Trading Scheduler...")
    print("Trading hours: 9:30 AM - 4:00 PM EST (Mon-Fri)")
    print("Entry time: 9:35 AM EST")
    print("Exit conditions: +3% profit, -0.8% stop loss, or 3:34 PM EST")
    print("Press Ctrl+C to stop")
    
    try:
        start_trading_scheduler()
    except KeyboardInterrupt:
        print("\nTrading scheduler stopped.")
    except Exception as e:
        print(f"Error in trading scheduler: {e}")
        logging.error(f"Trading scheduler error: {e}")