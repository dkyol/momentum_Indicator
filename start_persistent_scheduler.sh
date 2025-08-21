#!/bin/bash

# Persistent Scheduler Startup Script
# This script ensures the trading scheduler runs reliably throughout trading hours

echo "=========================================="
echo "STARTING PERSISTENT TRADING SCHEDULER"
echo "=========================================="
echo ""

# Function to cleanup processes
cleanup() {
    echo "Cleaning up processes..."
    pkill -f "scheduler_watchdog.py" 2>/dev/null
    pkill -f "trading_scheduler.py" 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Kill any existing processes
echo "Stopping existing processes..."
pkill -f "scheduler_watchdog.py" 2>/dev/null
pkill -f "trading_scheduler.py" 2>/dev/null
sleep 3

# Start the watchdog process
echo "Starting Scheduler Watchdog..."
python3 scheduler_watchdog.py &
WATCHDOG_PID=$!

echo "Watchdog started with PID: $WATCHDOG_PID"
echo ""
echo "SYSTEM STATUS:"
echo "• Watchdog monitors scheduler every 30 seconds during market hours"
echo "• Automatically restarts scheduler if it crashes"
echo "• Logs all activity to scheduler_watchdog.log"
echo ""
echo "Press Ctrl+C to stop the system"
echo ""

# Monitor the watchdog itself
while true; do
    # Check if watchdog is still running
    if ! kill -0 $WATCHDOG_PID 2>/dev/null; then
        echo "WARNING: Watchdog stopped! Restarting..."
        python3 scheduler_watchdog.py &
        WATCHDOG_PID=$!
        echo "Watchdog restarted with PID: $WATCHDOG_PID"
    fi
    
    # Display status every 5 minutes
    echo "$(date): System running normally - Watchdog PID: $WATCHDOG_PID"
    
    # Sleep for 5 minutes
    sleep 300
done