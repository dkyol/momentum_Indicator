# Market Data Scheduler

This system automatically updates market data once daily at 5:00 PM EST when markets are closed.

## How It Works

### Automatic Caching System
- Market data (high volume stocks and momentum analysis) is fetched and cached in JSON files
- Data is automatically refreshed daily at 5 PM EST
- Web application uses cached data for fast loading times
- Falls back to live data fetching if cache is stale

### Cache Files
- `cached_high_volume_stocks.json` - Top 10 stocks by daily volume
- `cached_momentum_data.json` - Technical indicators for top 5 stocks
- `last_data_update.json` - Update timestamp and metadata

### Scheduling Components

#### 1. scheduler.py
Core scheduling functions:
- `save_market_data()` - Fetches and caches market data
- `is_data_fresh()` - Checks if cached data is current
- `get_cached_*()` - Retrieves cached data

#### 2. run_scheduler.py
Background scheduler process:
- Runs continuous loop checking for scheduled updates
- Configured to run daily at 5 PM EST
- Includes error handling and logging

#### 3. daily_update.sh
Manual update script:
```bash
./daily_update.sh
```

### Manual Operations

To manually update data:
```bash
python3 scheduler.py
```

To run background scheduler:
```bash
python3 run_scheduler.py
```

### Integration with Flask App

The main application automatically:
1. Initializes cache on startup if stale
2. Uses cached data for web requests
3. Shows cache status in UI ("Last updated: ..." or "fresh data")

### Benefits

1. **Performance**: Fast page loads using cached data
2. **Reliability**: Reduces API calls and potential rate limiting
3. **Efficiency**: Updates once daily when markets are closed
4. **Fallback**: Automatically fetches fresh data if cache fails

### EST Scheduling

The system is configured to update at 5 PM EST specifically because:
- US stock markets close at 4 PM EST
- Allows 1 hour buffer for end-of-day data processing
- Ensures fresh data is available for next day's analysis