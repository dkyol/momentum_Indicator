# Overview

Stock Direction Predictor is a Flask-based web application that analyzes stock market data to predict the next-day direction (up or down) of a given stock. The application combines multiple analytical approaches including historical price pattern analysis, news sentiment analysis, and basic valuation metrics to generate predictions. Built as an educational tool, it provides users with a simple interface to input stock ticker symbols and receive probabilistic direction forecasts with detailed scoring breakdowns.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Technology Stack**: Pure HTML, CSS, and vanilla JavaScript with Bootstrap for responsive UI
- **Theme**: Dark theme implementation using Bootstrap's dark mode
- **User Interface**: Single-page application with real-time form validation and loading states
- **High Volume Stocks Table**: Live data table displaying top 10 stocks ranked by daily volume with price and return metrics
- **Momentum Analysis Table**: Technical indicators display with color-coded values and probability index progress bars
- **Security**: Password-protected access with session-based authentication (password: Eb10f600!)
- **Styling Approach**: Custom CSS variables for prediction states (up/down/uncertain) with color-coded results

## Backend Architecture  
- **Framework**: Flask web framework with Python
- **Architecture Pattern**: Simple MVC pattern with separated concerns
- **Route Structure**: RESTful API endpoint (`/predict`) for stock analysis with JSON responses
- **Error Handling**: Comprehensive validation for ticker symbols and graceful error responses
- **Logging**: Built-in logging configuration for debugging and monitoring

## Core Prediction Logic
- **Multi-factor Analysis**: Combines three scoring components weighted differently (pattern analysis x2, sentiment, valuation)
- **Pattern Recognition**: Analyzes historical price data for trends, momentum streaks, and dip rebounds
- **AI-Powered Sentiment Analysis**: Uses Grok AI model for advanced news sentiment analysis with keyword-based fallback
- **Momentum Analysis**: Advanced technical indicators (RSI, Stochastic, MACD, CCI, Williams %R, ROC) with probability index calculation

## Data Processing
- **Historical Data**: 30-day rolling window analysis of stock price movements and daily returns
- **High Volume Data**: Cached data system with top 10 stocks by volume including 1-day, 1-week, and 1-month returns
- **Scheduled Updates**: Daily market data refresh at 5:00 PM EST when markets are closed using automated scheduler
- **Cache Management**: JSON-based caching system with freshness validation and automatic fallback to live data
- **Score Aggregation**: Weighted scoring system that combines all analytical components into a single prediction
- **Timezone Display**: EST timezone formatting for data query timestamps

## Session Management
- **Security**: Session secret key configuration with environment variable support
- **Development Mode**: Default development key with production environment override capability

# External Dependencies

## AI Services
- **X.AI Grok API**: Advanced AI model for news sentiment analysis with OpenAI-compatible interface

## Financial Data APIs
- **Yahoo Finance API**: Primary data source via `yfinance` library for historical stock prices, returns calculation, and basic company metrics

## Frontend Libraries  
- **Bootstrap**: UI framework served via CDN for responsive design and dark theme support
- **Font Awesome**: Icon library for enhanced visual interface elements

## Python Libraries
- **Flask**: Core web framework for application structure and routing
- **OpenAI**: Client library for X.AI Grok API integration with secure environment variable configuration
- **pandas**: Data manipulation and analysis for stock price calculations
- **yfinance**: Yahoo Finance API wrapper for stock data retrieval
- **schedule**: Task scheduling library for automated daily data updates at 5 PM EST
- **pytz**: Timezone handling for EST scheduling and timestamp management
- **datetime**: Built-in library for time-based data processing and date calculations

## Development Environment
- **Replit Platform**: Hosting and development environment with automatic dependency management
- **Static Asset Serving**: Flask's built-in static file serving for CSS and JavaScript assets