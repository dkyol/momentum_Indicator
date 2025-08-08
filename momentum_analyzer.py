import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import logging

def calculate_momentum_indicators(ticker):
    """
    Fetches hourly historical stock data from Yahoo Finance for the last two weeks 
    and calculates leading momentum indicators.
    
    Parameters:
    - ticker (str): Stock ticker symbol (e.g., 'AAPL').
    
    Returns:
    - pd.DataFrame: DataFrame with original data and added columns for RSI, Stochastic (%K and %D), 
      MACD (line, signal, histogram), CCI, Williams %R, and ROC.
    """
    try:
        # Calculate start date: two weeks ago
        start_date = datetime.now() - timedelta(days=14)
        
        # Download hourly historical data
        data = yf.download(ticker, start=start_date, interval='1h', auto_adjust=True, prepost=False)
        
        if data is None or data.empty:
            raise ValueError(f"No data found for ticker '{ticker}' in the last two weeks.")
        
        # Ensure we have proper column names
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns.values]
        
        # Calculate RSI (14-period)
        delta = data['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))
        
        # Calculate Stochastic Oscillator (14-period %K, 3-period %D)
        high_14 = data['High'].rolling(14).max()
        low_14 = data['Low'].rolling(14).min()
        data['Stoch_K'] = 100 * (data['Close'] - low_14) / (high_14 - low_14)
        data['Stoch_D'] = data['Stoch_K'].rolling(3).mean()
        
        # Calculate MACD (12-26-9)
        ema_12 = data['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = data['Close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = ema_12 - ema_26
        data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
        data['MACD_Hist'] = data['MACD'] - data['MACD_Signal']
        
        # Calculate CCI (20-period)
        tp = (data['High'] + data['Low'] + data['Close']) / 3
        sma_tp = tp.rolling(20).mean()
        mean_dev = tp.rolling(20).apply(lambda x: np.mean(np.abs(x - x.mean())) if len(x) > 0 else 0)
        # Avoid division by zero
        data['CCI'] = (tp - sma_tp) / (0.015 * mean_dev.replace(0, np.nan))
        
        # Calculate Williams %R (14-period)
        data['Williams_R'] = -100 * (high_14 - data['Close']) / (high_14 - low_14)
        
        # Calculate ROC (12-period)
        data['ROC'] = (data['Close'] / data['Close'].shift(12) - 1) * 100
        
        return data
    except Exception as e:
        logging.error(f"Error calculating momentum indicators for {ticker}: {e}")
        return pd.DataFrame()

def calculate_probability_index(data):
    """
    Takes the DataFrame from calculate_momentum_indicators and adds a 'Probability_Index' column.
    The index indicates the probability of a stock price increase (higher value) or decrease (lower value)
    for the next period, scaled from 1 (likely decrease) to 100 (likely increase). It uses a composite
    reversal-based score from the momentum indicators, where oversold conditions suggest higher probability of increase.
    
    Parameters:
    - data (pd.DataFrame): The DataFrame with momentum indicators.
    
    Returns:
    - pd.DataFrame: The input DataFrame with an added 'Probability_Index' column.
    """
    try:
        df = data.copy()
        
        # Compute standard deviations for scaling unbounded indicators
        std_macd_hist = df['MACD_Hist'].std() or 0.01  # Avoid division by zero
        std_cci = df['CCI'].std() or 1.0
        std_roc = df['ROC'].std() or 0.1
        
        # List to hold the index values
        indices = []
        
        for _, row in df.iterrows():
            score_list = []
            
            # RSI: inverted (low RSI = high score)
            try:
                if pd.notna(row['RSI']) and not np.isnan(row['RSI']):
                    score_list.append(100 - row['RSI'])
            except (TypeError, ValueError):
                pass
            
            # Stochastic D: inverted
            try:
                if pd.notna(row['Stoch_D']) and not np.isnan(row['Stoch_D']):
                    score_list.append(100 - row['Stoch_D'])
            except (TypeError, ValueError):
                pass
            
            # Williams %R: negative of value (low Williams = high score)
            try:
                if pd.notna(row['Williams_R']) and not np.isnan(row['Williams_R']):
                    score_list.append(-row['Williams_R'])
            except (TypeError, ValueError):
                pass
            
            # CCI: inverted using tanh for compression
            try:
                if pd.notna(row['CCI']) and not np.isnan(row['CCI']):
                    cci_score = 50 - 50 * np.tanh(row['CCI'] / std_cci)
                    score_list.append(cci_score)
            except (TypeError, ValueError):
                pass
            
            # MACD Histogram: inverted
            try:
                if pd.notna(row['MACD_Hist']) and not np.isnan(row['MACD_Hist']):
                    macd_score = 50 - 50 * np.tanh(row['MACD_Hist'] / std_macd_hist)
                    score_list.append(macd_score)
            except (TypeError, ValueError):
                pass
            
            # ROC: inverted
            try:
                if pd.notna(row['ROC']) and not np.isnan(row['ROC']):
                    roc_score = 50 - 50 * np.tanh(row['ROC'] / std_roc)
                    score_list.append(roc_score)
            except (TypeError, ValueError):
                pass
            
            # Compute average score (0-100)
            if score_list:
                avg_score = np.mean(score_list)
            else:
                avg_score = 50
            
            # Scale to 1-100
            index_value = 1 + 99 * (avg_score / 100)
            
            indices.append(index_value)
        
        df['Probability_Index'] = indices
        return df
    except Exception as e:
        logging.error(f"Error calculating probability index: {e}")
        return data

def get_momentum_summary(tickers):
    """
    Get momentum analysis summary for multiple tickers.
    
    Parameters:
    - tickers (list): List of stock ticker symbols
    
    Returns:
    - list: List of dictionaries with momentum analysis for each ticker
    """
    momentum_data = []
    
    for ticker in tickers[:5]:  # Limit to 5 stocks to avoid timeout
        try:
            # Get momentum indicators
            data = calculate_momentum_indicators(ticker)
            if not data.empty:
                # Calculate probability index
                data_with_prob = calculate_probability_index(data)
                
                # Get latest values
                latest = data_with_prob.iloc[-1]
                
                def safe_round(value, decimals):
                    try:
                        if pd.notna(value) and not np.isnan(value):
                            return round(float(value), decimals)
                        return 'N/A'
                    except (TypeError, ValueError):
                        return 'N/A'
                
                momentum_data.append({
                    'Symbol': ticker,
                    'RSI': safe_round(latest['RSI'], 2),
                    'Stoch_D': safe_round(latest['Stoch_D'], 2),
                    'MACD': safe_round(latest['MACD'], 4),
                    'CCI': safe_round(latest['CCI'], 2),
                    'Williams_R': safe_round(latest['Williams_R'], 2),
                    'ROC': safe_round(latest['ROC'], 2),
                    'Probability_Index': safe_round(latest['Probability_Index'], 1)
                })
            else:
                momentum_data.append({
                    'Symbol': ticker,
                    'RSI': 'N/A',
                    'Stoch_D': 'N/A', 
                    'MACD': 'N/A',
                    'CCI': 'N/A',
                    'Williams_R': 'N/A',
                    'ROC': 'N/A',
                    'Probability_Index': 'N/A'
                })
        except Exception as e:
            logging.error(f"Error processing momentum for {ticker}: {e}")
            momentum_data.append({
                'Symbol': ticker,
                'RSI': 'Error',
                'Stoch_D': 'Error', 
                'MACD': 'Error',
                'CCI': 'Error',
                'Williams_R': 'Error',
                'ROC': 'Error',
                'Probability_Index': 'Error'
            })
    
    # Sort by Probability_Index in descending order (highest first)
    momentum_data.sort(key=lambda x: x['Probability_Index'] if isinstance(x['Probability_Index'], (int, float)) else 0, reverse=True)
    
    return momentum_data