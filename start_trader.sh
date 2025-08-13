#!/bin/bash
# Start the paper trading scheduler in the background
echo "Starting Paper Trading System..."
python3 trading_scheduler.py &
echo "Paper trading system started in background"
echo "Check trading.log for activity logs"