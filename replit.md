# Overview

Stock Market Analytics is a Flask-based web application that combines a real-time market dashboard, an automated paper-trading book, and a multi-page **Alpha & Opportunity Engine** for finding undervalued stocks and high-probability bullish setups across an ~100-ticker universe. The original 14-stock dashboard (high-volume ranking, momentum, SMAs, paper trading) is preserved on the home page; the alpha pages add value screening, relative strength, technical setups, sector rotation, market regime, catalysts, a composite Edge Score, and a signal backtester. Built as an educational and analytical tool, it offers users a professional dashboard view of market data with automated daily updates, secure password protection, and simulated trading performance tracking.

## Alpha Engine (April 2026)

A second analytics layer focused on idea discovery rather than monitoring:

* **Universe** (`universe.py`) – ~280 liquid US large-caps at S&P 500 scale, tagged with GICS sectors and mapped to Sector SPDR ETFs.  The list is configurable: drop a `universe.json` file at the project root (`[{"symbol": "AAPL", "sector": "Information Technology"}, ...]`) and it overrides the bundled defaults at startup.
* **Fundamentals snapshot** (`fundamentals.py`) – nightly yfinance `.info` pull, cached as `cached_fundamentals.json`.
* **Value & quality screen** (`value_screener.py`) – sector-relative cheapness percentile (P/E, P/B, P/S, EV/EBITDA, FCF yield) gated by a quality filter (positive FCF, D/E < 200, non-shrinking revenue).
* **Relative strength** (`relative_strength.py`) – 1m/3m/6m/12m raw returns and excess returns vs SPY & vs sector ETFs, plus **percentile-rank** columns for each (universe rank for vs-SPY, within-sector rank for vs-sector), IBD-style 1-99 RS Rating, and a sector-rotation table.
* **Technical setups** (`setups.py`) – trend pullback, 52-week breakout, volume thrust, golden cross, bullish RSI divergence.
* **Market regime** (`market_regime.py`) – SPY-vs-200d / VIX / breadth → risk_on / neutral / risk_off classifier; the paper trader skips new entries when risk_off.
* **Catalysts** (`catalysts.py`) – upcoming earnings, 90-day insider transactions, short-interest snapshot.
* **Composite Edge Score** (`edge_score.py`) – weighted blend (Value 30%, RS 30%, Setups 25%, Catalysts 15%) with reason strings; quality-failing stocks demoted.
* **Signal backtester** (`backtester.py`) – 3-year holding-period replay (10 trading-day hold) of **eight** signals: the 5 setups, a price-based value_only proxy (>30% below 52w high while above 200dma), an rs_only proxy (top-quintile 12m return cross-sectionally), and a full edge_score_proxy (value AND rs AND any setup).  Reports trades, hit rate, mean / median / best / worst return, and **max drawdown** (additive cumulative-PnL drawdown in percentage points).
* **Orchestrator** (`alpha_engine.py`) – `refresh_alpha_data(include_backtest=False)`; bootstrapped in a background thread on first app start, refreshed nightly via `scheduler.py`, and triggerable from the navbar "Refresh alpha" button.
* **Routes**: `/opportunities`, `/value`, `/setups`, `/sectors`, `/catalysts`, `/backtest` (all wrapped by `templates/_layout.html` with a regime banner).
* **Cache files**: `cached_fundamentals.json`, `cached_value_screen.json`, `cached_relative_strength.json`, `cached_setups.json`, `cached_market_regime.json`, `cached_catalysts.json`, `cached_edge_score.json`, `cached_backtest.json`, `cached_alpha_meta.json` (last-refreshed timestamps), plus `cached_rvol.json` (intraday time-adjusted Relative Volume, refreshed every 15 minutes during US market hours).
* **Cache backing store**: every `cached_*.json` file is mirrored to a Postgres `alpha_cache` table by `alpha_cache.save_json` / `load_json`. The DB row takes precedence on read, so a Scheduled Deployment writer's update is immediately visible to every Autoscale web instance even though they don't share a filesystem.

## Production scheduling (Autoscale + Scheduled Deployments)

The Autoscale web tier (`gunicorn main:app`) does **not** run the in-process scheduler. Instead, three Replit Scheduled Deployments call entry-point scripts under `scripts/`:

| Script | Purpose | Recommended cron (UTC) |
|---|---|---|
| `python scripts/refresh_rvol.py`     | Intraday time-adjusted RVOL snapshot | `*/15 13-21 * * 1-5` |
| `python scripts/refresh_alpha.py`    | Daily fundamentals/value/RS/setups/regime/catalysts/edge refresh | `5 14 * * 1-5` |
| `python scripts/refresh_alpha.py --with-backtest` | Nightly full pipeline incl. backtest | `30 3 * * 2-7` |
| `python scripts/equity_snapshot.py`  | EOD equity snapshot for the portfolio dashboard | `10 21 * * 1-5` |

`scripts/seed_alpha_cache_db.py` is a one-shot helper that copies the local `cached_*.json` files into the DB — useful right after deploying the DB-backed cache layer or after a manual local refresh.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Technology Stack**: Pure HTML, CSS, and vanilla JavaScript with Bootstrap for responsive UI
- **Theme**: Dark theme implementation using Bootstrap's dark mode
- **User Interface**: Clean dashboard-style single-page application focused on data visualization
- **High Volume Stocks Table**: Live data table displaying 15 selected stocks ranked by daily volume with price and return metrics
- **Momentum Analysis Table**: Technical indicators display with color-coded values and probability index progress bars
- **Simple Moving Averages Table**: SMA 50/200 analysis with percentage comparisons and bullish/bearish indicators
- **Paper Trading Portfolio**: Automated trading simulation with $10,000 initial investment tracking real-time performance
- **Security**: Password-protected access with session-based authentication using secure environment variable (SITE_PASSWORD)
- **Styling Approach**: Clean, professional styling focused on data readability and visual hierarchy

## Backend Architecture  
- **Framework**: Flask web framework with Python
- **Architecture Pattern**: Simple MVC pattern with separated concerns
- **Route Structure**: Simple routing with main dashboard view and authentication endpoints
- **Error Handling**: Comprehensive validation for ticker symbols and graceful error responses
- **Logging**: Built-in logging configuration for debugging and monitoring

## Trading Scheduler System (August 2025 - Complete Refactor)
- **Core Scheduler**: Clean, efficient trading_scheduler.py with reliable execution
- **Daily Schedule**: 10:05 AM data update, 10:15 AM trades, 3:34 PM closure
- **Position Monitoring**: 2-minute checks during market hours for profit/loss targets
- **Exit Conditions**: +3% profit target, -0.8% stop loss, 3:34 PM EOD closure
- **Auto-Restart**: Bash script monitors and restarts scheduler if it crashes
- **System Verification**: Tools to verify all components before trading
- **Status Monitoring**: Real-time status checking and portfolio overview

## Core Analytics Logic
- **Volume Analysis**: Real-time ranking of 14 stocks by daily trading volume with performance metrics
- **Momentum Analysis**: Advanced technical indicators (RSI, Stochastic, MACD, CCI, Williams %R, ROC) with probability index calculation
- **SMA Analysis**: Simple Moving Averages (50-day and 200-day) with trend comparisons and bullish/bearish indicators
- **Automated Paper Trading**: Algorithm that trades top 2 momentum stocks daily at 9:35 AM EST with systematic exit rules

## Data Processing
- **Real-time Data**: Live stock data fetching with 1-day, 1-week, and 1-month return calculations
- **High Volume Data**: Cached data system with 14 selected stocks by volume including 1-day, 1-week, and 1-month returns
- **SMA Analysis**: Simple Moving Averages (50-day and 200-day) with percentage comparison calculations for trend analysis
- **Scheduled Updates**: Daily market data refresh at 10:05 AM EST (Monday-Friday) during market hours using automated scheduler
- **Cache Management**: JSON-based caching system with freshness validation and automatic fallback to live data
- **Technical Analysis**: Comprehensive technical indicator calculations with color-coded visual representations
- **Paper Trading Execution**: Automated daily stock purchases of top 2 momentum stocks (40% allocation each) at 10:15 AM EST
- **Real-time Monitoring**: 2-minute price checks during trading hours with automatic exit conditions
- **Risk Management**: Systematic exits at +3% profit target, -0.8% stop loss, or 3:34 PM EST end-of-day close
- **Portfolio Tracking**: Real-time portfolio value updates with position-level P&L calculations and trade history
- **Database Storage**: PostgreSQL backend storing all trades, positions, and portfolio performance metrics
- **Timezone Display**: EST timezone formatting for data query timestamps

## Session Management
- **Security**: Session secret key configuration with environment variable support
- **Authentication**: Site password stored securely in SITE_PASSWORD environment variable
- **Development Mode**: Default development key with production environment override capability

# External Dependencies

## Core Dependencies

## Financial Data APIs
- **Yahoo Finance API**: Primary data source via `yfinance` library for historical stock prices, returns calculation, and basic company metrics

## Frontend Libraries  
- **Bootstrap**: UI framework served via CDN for responsive design and dark theme support
- **Font Awesome**: Icon library for enhanced visual interface elements

## Python Libraries
- **Flask**: Core web framework for application structure and routing
- **NumPy**: Numerical computing for technical indicator calculations
- **pandas**: Data manipulation and analysis for stock price calculations
- **yfinance**: Yahoo Finance API wrapper for stock data retrieval and real-time price monitoring
- **schedule**: Task scheduling library for automated daily data updates at 5 PM EST and trading execution
- **pytz**: Timezone handling for EST scheduling and timestamp management
- **datetime**: Built-in library for time-based data processing and date calculations
- **SQLAlchemy**: ORM for database management and trade/portfolio data persistence
- **psycopg2-binary**: PostgreSQL adapter for database connectivity

## Development Environment
- **Replit Platform**: Hosting and development environment with automatic dependency management
- **Static Asset Serving**: Flask's built-in static file serving for CSS and JavaScript assets