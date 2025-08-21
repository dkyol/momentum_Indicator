#!/bin/bash

# Start Trading System
# This script starts the trading scheduler and monitors its health

echo "========================================"
echo "STARTING AUTOMATED TRADING SYSTEM"
echo "========================================"
echo ""

# Function to check if process is running
check_process() {
    pgrep -f "$1" > /dev/null
    return $?
}

# Kill any existing scheduler processes
echo "Cleaning up existing processes..."
pkill -f "trading_scheduler.py" 2>/dev/null
pkill -f "robust_scheduler.py" 2>/dev/null
sleep 2

# Start the trading scheduler
echo "Starting Trading Scheduler..."
python3 trading_scheduler.py &
SCHEDULER_PID=$!

echo "Trading Scheduler started with PID: $SCHEDULER_PID"
echo ""

# Monitor the scheduler
echo "Monitoring system health..."
echo "Press Ctrl+C to stop"
echo ""

while true; do
    # Check if scheduler is still running
    if ! kill -0 $SCHEDULER_PID 2>/dev/null; then
        echo "WARNING: Trading Scheduler stopped unexpectedly!"
        echo "Restarting..."
        python3 trading_scheduler.py &
        SCHEDULER_PID=$!
        echo "Trading Scheduler restarted with PID: $SCHEDULER_PID"
    fi
    
    # Sleep for 30 seconds before next check
    sleep 30
done