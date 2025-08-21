# stock_analytics.py
# This script provides stock market analysis including volume ranking and data retrieval.
# Dependencies: yfinance (pip install yfinance), pandas (comes with yfinance)
# Note: Stock analysis for educational purposes; not financial advice. Markets are unpredictable.

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


def get_high_volume_data():
    """
    Get stocks by daily volume with prior day, week, and month returns.
    Returns a DataFrame with stock symbols, volume, and return percentages.
    """
    try:
        # Popular high-volume tickers to analyze
        high_volume_tickers = [
            'NVDA', 'AMD', 'TSLA', 'SPY', 'HOOD', 'AMZN', 'GOOGL', 'SMCI',
            'CRDO', 'ASTS', 'IONQ', 'OPFI', 'RBRK', 'COIN', 'EGO'
        ]

        # Get current date and calculate periods
        end_date = datetime.now()
        start_date = end_date - timedelta(
            days=35)  # Extra days for calculation

        volume_data = []

        for ticker in high_volume_tickers:
            try:
                # Get stock data
                stock = yf.Ticker(ticker)
                data = stock.history(period="2mo", interval="1d")

                if len(data) < 30:  # Need enough data
                    continue

                # Get latest volume and price data
                latest_volume = data['Volume'].iloc[-1]
                current_price = data['Close'].iloc[-1]

                # Calculate returns
                day_return = (
                    (data['Close'].iloc[-1] / data['Close'].iloc[-2]) -
                    1) * 100 if len(data) >= 2 else 0
                week_return = (
                    (data['Close'].iloc[-1] / data['Close'].iloc[-6]) -
                    1) * 100 if len(data) >= 6 else 0
                month_return = (
                    (data['Close'].iloc[-1] / data['Close'].iloc[-21]) -
                    1) * 100 if len(data) >= 21 else 0

                volume_data.append({
                    'Symbol': ticker,
                    'Volume': latest_volume,
                    'Current_Price': current_price,
                    'Day_Return': day_return,
                    'Week_Return': week_return,
                    'Month_Return': month_return
                })

            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")
                continue

        # Create DataFrame and sort by volume
        df = pd.DataFrame(volume_data)
        if df.empty:
            return pd.DataFrame()  # Return empty DataFrame if no data

        # Sort by volume and get top 15 (to ensure we get a good selection)
        df = df.sort_values('Volume', ascending=False).head(15)

        # Round numerical values for display
        df['Current_Price'] = df['Current_Price'].round(2)
        df['Day_Return'] = df['Day_Return'].round(2)
        df['Week_Return'] = df['Week_Return'].round(2)
        df['Month_Return'] = df['Month_Return'].round(2)
        df['Volume'] = df['Volume'].astype(int)

        return df

    except Exception as e:
        print(f"Error in get_high_volume_data: {e}")
        return pd.DataFrame()



