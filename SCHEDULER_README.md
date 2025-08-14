# Paper Trading Monitor

This system provides automated paper trading capabilities with real-time monitoring.

## Starting the Trading System

### Option 1: Quick Start (Background Monitor)
```bash
python3 run_scheduler.py
```
This starts the full trading monitor that:
- Updates portfolio timestamps every 15 minutes during market hours (9:30 AM - 4:00 PM EST)  
- Executes trades at 9:35 AM EST daily
- Closes positions at 3:34 PM EST or when profit/loss targets are hit
- Logs all activities to `trading_monitor.log`

### Option 2: Simple Trading Script
```bash
./start_trader.sh
```
Runs the basic trading scheduler in the background.

## Trading Strategy

- **Initial Investment**: $10,000
- **Entry Time**: 9:35 AM EST daily (Monday-Friday)
- **Stock Selection**: Top 2 stocks by momentum probability index
- **Position Size**: 10% of portfolio value per trade
- **Monitoring**: Every 15 minutes during market hours
- **Exit Conditions**:
  - +3% profit target
  - -0.8% stop loss  
  - 3:34 PM EST end-of-day close

## Portfolio Timestamp

The portfolio "Last updated" timestamp shows in 12-hour EST format and updates every 15 minutes during market hours when the system checks positions for buy/sell decisions.

## Files Generated

- `trading_monitor.log` - Detailed trading activity log
- `trading.log` - Basic trading activities (from start_trader.sh)

## Stopping the System

Press `Ctrl+C` to stop the trading monitor gracefully.