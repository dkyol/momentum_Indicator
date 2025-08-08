#!/bin/bash
# Daily Market Data Update Script
# This script should be run daily at 5 PM EST to update market data

echo "Starting daily market data update at $(date)"
cd /home/runner/workspace
python3 scheduler.py
echo "Market data update completed at $(date)"