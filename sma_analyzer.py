"""
Simple Moving Average (SMA) Analysis Module
Calculates 50-day and 200-day SMAs and percentage differences from current price.
"""

import pandas as pd
import yfinance as yf
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_stock_metrics(ticker):
    """
    Fetches historical stock data from Yahoo Finance for the given ticker,
    calculates the 50-day and 200-day simple moving averages, and computes
    the percentage above or below these averages based on the previous day's close price.
    
    Parameters:
    - ticker (str): Stock ticker symbol (e.g., 'AAPL').
    
    Returns:
    - pd.DataFrame: A DataFrame with the ticker, previous close, SMAs, and percentages.
    """
    try:
        # Download historical data for at least 200 trading days (use 2y to be safe)
        data = yf.download(ticker, period='2y', progress=False)
        
        if data is None or data.shape[0] == 0:
            raise ValueError(f"No data found for ticker '{ticker}'.")
        
        # Calculate 50-day and 200-day SMAs
        data['SMA_50'] = data['Close'].rolling(window=50).mean()
        data['SMA_200'] = data['Close'].rolling(window=200).mean()
        
        # Get the latest values using .iloc for proper indexing
        close = data['Close'].iloc[-1].item()  # Use .item() instead of float()
        sma_50_val = data['SMA_50'].iloc[-1]
        sma_200_val = data['SMA_200'].iloc[-1]
        
        sma_50 = sma_50_val.item() if not pd.isna(sma_50_val) else None
        sma_200 = sma_200_val.item() if not pd.isna(sma_200_val) else None
        
        # Calculate percentages (positive if above, negative if below)
        pct_50 = ((close - sma_50) / sma_50 * 100) if sma_50 is not None else None
        pct_200 = ((close - sma_200) / sma_200 * 100) if sma_200 is not None else None
        
        # Create and return DataFrame
        result_df = pd.DataFrame({
            'Ticker': [ticker],
            'Previous_Close': [round(close, 2)],
            'SMA_50': [round(sma_50, 2) if sma_50 is not None else None],
            'SMA_200': [round(sma_200, 2) if sma_200 is not None else None],
            'Pct_Above_Below_50': [round(pct_50, 2) if pct_50 is not None else None],
            'Pct_Above_Below_200': [round(pct_200, 2) if pct_200 is not None else None]
        })
        
        return result_df
        
    except Exception as e:
        logger.error(f"Error fetching SMA data for {ticker}: {e}")
        # Return error DataFrame
        return pd.DataFrame({
            'Ticker': [ticker],
            'Previous_Close': ['Error'],
            'SMA_50': ['Error'],
            'SMA_200': ['Error'],
            'Pct_Above_Below_50': ['Error'],
            'Pct_Above_Below_200': ['Error']
        })

def get_sma_summary(tickers):
    """
    Get SMA analysis summary for multiple tickers.
    
    Parameters:
    - tickers (list): List of stock ticker symbols
    
    Returns:
    - list: List of dictionaries with SMA analysis for each ticker
    """
    sma_data = []
    
    for ticker in tickers:  # Process all provided tickers
        try:
            logger.info(f"Fetching SMA data for {ticker}")
            df = get_stock_metrics(ticker)
            
            if not df.empty:
                row = df.iloc[0]
                sma_data.append({
                    'Symbol': row['Ticker'],
                    'Previous_Close': row['Previous_Close'],
                    'SMA_50': row['SMA_50'],
                    'SMA_200': row['SMA_200'],
                    'Pct_Above_Below_50': row['Pct_Above_Below_50'],
                    'Pct_Above_Below_200': row['Pct_Above_Below_200']
                })
        except Exception as e:
            logger.error(f"Error processing SMA data for {ticker}: {e}")
            sma_data.append({
                'Symbol': ticker,
                'Previous_Close': 'Error',
                'SMA_50': 'Error',
                'SMA_200': 'Error',
                'Pct_Above_Below_50': 'Error',
                'Pct_Above_Below_200': 'Error'
            })
    
    return sma_data