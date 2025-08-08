# Overview

Stock Direction Predictor is a Flask-based web application that analyzes stock market data to predict the next-day direction (up or down) of a given stock. The application combines multiple analytical approaches including historical price pattern analysis, news sentiment analysis, and basic valuation metrics to generate predictions. Built as an educational tool, it provides users with a simple interface to input stock ticker symbols and receive probabilistic direction forecasts with detailed scoring breakdowns.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Technology Stack**: Pure HTML, CSS, and vanilla JavaScript with Bootstrap for responsive UI
- **Theme**: Dark theme implementation using Bootstrap's dark mode
- **User Interface**: Single-page application with real-time form validation and loading states
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
- **Sentiment Analysis**: Keyword-based news sentiment scoring using predefined positive/negative word lists
- **Valuation Metrics**: Basic financial health assessment using stock fundamentals

## Data Processing
- **Historical Data**: 30-day rolling window analysis of stock price movements and daily returns
- **Real-time Integration**: Live data fetching for current market information
- **Score Aggregation**: Weighted scoring system that combines all analytical components into a single prediction

## Session Management
- **Security**: Session secret key configuration with environment variable support
- **Development Mode**: Default development key with production environment override capability

# External Dependencies

## Financial Data APIs
- **Yahoo Finance API**: Primary data source via `yfinance` library for historical stock prices, returns calculation, and basic company metrics

## Frontend Libraries  
- **Bootstrap**: UI framework served via CDN for responsive design and dark theme support
- **Font Awesome**: Icon library for enhanced visual interface elements

## Python Libraries
- **Flask**: Core web framework for application structure and routing
- **pandas**: Data manipulation and analysis for stock price calculations
- **yfinance**: Yahoo Finance API wrapper for stock data retrieval
- **datetime**: Built-in library for time-based data processing and date calculations

## Development Environment
- **Replit Platform**: Hosting and development environment with automatic dependency management
- **Static Asset Serving**: Flask's built-in static file serving for CSS and JavaScript assets