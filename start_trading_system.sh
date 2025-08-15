#!/bin/bash
"""
Trading System Startup Script
Starts the persistent scheduler that handles all scheduled trading operations.
"""

echo "=============================================="
echo "STARTING AUTOMATED TRADING SYSTEM"
echo "=============================================="
echo "Schedule:"
echo "• 10:05 AM EST - Market data updates"
echo "• 10:15 AM EST - Execute momentum trades" 
echo "• 3:34 PM EST - End-of-day position closure"
echo "• 2-minute monitoring during market hours"
echo "=============================================="

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Start the persistent scheduler
python3 start_trading_scheduler.py &

# Get the PID of the background process
SCHEDULER_PID=$!

echo "Trading scheduler started with PID: $SCHEDULER_PID"
echo "To stop: kill $SCHEDULER_PID"
echo "Log file: persistent_scheduler.log"
echo "=============================================="

# Wait for the process to finish (or Ctrl+C)
wait $SCHEDULER_PID