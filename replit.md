# Overview

Stock Market Analytics is a Flask-based web application that provides comprehensive real-time analysis of 14 specific stocks through synchronized data tables and automated paper trading. The application displays high-volume stock rankings, advanced momentum analysis with technical indicators, Simple Moving Averages comparisons, and a live paper trading portfolio that automatically trades the top momentum stocks. Built as an educational and analytical tool, it offers users a professional dashboard view of market data with automated daily updates, secure password protection, and simulated trading performance tracking.

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