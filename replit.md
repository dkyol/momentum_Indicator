# Overview

Stock Market Analytics is a Flask-based web application that provides comprehensive real-time analysis of 14 specific stocks through synchronized data tables. The application displays high-volume stock rankings, advanced momentum analysis with technical indicators, and Simple Moving Averages comparisons. Built as an educational and analytical tool, it offers users a professional dashboard view of market data with automated daily updates and secure password protection.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Technology Stack**: Pure HTML, CSS, and vanilla JavaScript with Bootstrap for responsive UI
- **Theme**: Dark theme implementation using Bootstrap's dark mode
- **User Interface**: Clean dashboard-style single-page application focused on data visualization
- **High Volume Stocks Table**: Live data table displaying 14 selected stocks ranked by daily volume with price and return metrics
- **Momentum Analysis Table**: Technical indicators display with color-coded values and probability index progress bars
- **Simple Moving Averages Table**: SMA 50/200 analysis with percentage comparisons and bullish/bearish indicators
- **Security**: Password-protected access with session-based authentication using secure environment variable (SITE_PASSWORD)
- **Styling Approach**: Clean, professional styling focused on data readability and visual hierarchy

## Backend Architecture  
- **Framework**: Flask web framework with Python
- **Architecture Pattern**: Simple MVC pattern with separated concerns
- **Route Structure**: Simple routing with main dashboard view and authentication endpoints
- **Error Handling**: Comprehensive validation for ticker symbols and graceful error responses
- **Logging**: Built-in logging configuration for debugging and monitoring

## Core Analytics Logic
- **Volume Analysis**: Real-time ranking of 14 stocks by daily trading volume with performance metrics
- **Momentum Analysis**: Advanced technical indicators (RSI, Stochastic, MACD, CCI, Williams %R, ROC) with probability index calculation
- **SMA Analysis**: Simple Moving Averages (50-day and 200-day) with trend comparisons and bullish/bearish indicators

## Data Processing
- **Real-time Data**: Live stock data fetching with 1-day, 1-week, and 1-month return calculations
- **High Volume Data**: Cached data system with 14 selected stocks by volume including 1-day, 1-week, and 1-month returns
- **SMA Analysis**: Simple Moving Averages (50-day and 200-day) with percentage comparison calculations for trend analysis
- **Scheduled Updates**: Daily market data refresh at 5:00 PM EST when markets are closed using automated scheduler
- **Cache Management**: JSON-based caching system with freshness validation and automatic fallback to live data
- **Technical Analysis**: Comprehensive technical indicator calculations with color-coded visual representations
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
- **yfinance**: Yahoo Finance API wrapper for stock data retrieval
- **schedule**: Task scheduling library for automated daily data updates at 5 PM EST
- **pytz**: Timezone handling for EST scheduling and timestamp management
- **datetime**: Built-in library for time-based data processing and date calculations

## Development Environment
- **Replit Platform**: Hosting and development environment with automatic dependency management
- **Static Asset Serving**: Flask's built-in static file serving for CSS and JavaScript assets