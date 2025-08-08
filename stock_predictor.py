# stock_direction_predictor.py
# This script assesses if a given stock is likely to go up or down the next trading day based on historical patterns,
# recent news sentiment, and basic valuation metrics. It leverages logic from analyzing NVDA: dip rebounds, momentum streaks,
# news catalysts (e.g., mitigated risks like tariffs), and sentiment.
# Dependencies: yfinance (pip install yfinance), pandas (comes with yfinance)
# Optional for better sentiment: textblob (pip install textblob), but here we use simple keyword-based sentiment for no extra installs.
# Note: Predictions are probabilistic and for educational purposes; not financial advice. Markets are unpredictable.

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import re  # For simple text processing
import os
import json
from openai import OpenAI

# Initialize Grok AI client
grok_client = OpenAI(
    base_url="https://api.x.ai/v1",
    api_key=os.environ.get("XAI_API_KEY")
)

def get_historical_data(ticker, days=30):
    """
    Fetch historical adjusted closing prices and calculate daily returns.
    """
    end = datetime.now()
    start = end - timedelta(days=days + 1)  # Extra day for returns calculation
    data = yf.download(ticker, start=start, end=end, progress=False)
    if data.empty:
        raise ValueError(f"No data found for {ticker}. Check ticker symbol.")
    
    # Handle MultiIndex columns from yfinance
    if isinstance(data.columns, pd.MultiIndex):
        # Flatten MultiIndex columns and get Close price
        data.columns = [col[0] for col in data.columns]
    
    # Use Close price since auto_adjust=True by default now
    close_col = 'Close' if 'Close' in data.columns else 'Adj Close'
    data['Return'] = data[close_col].pct_change() * 100
    data['Adj Close'] = data[close_col]  # Create Adj Close for compatibility
    return data.dropna()  # Drop first row with NaN return

def analyze_patterns(returns_df):
    """
    Detect patterns like momentum streaks and dip rebounds.
    Returns a score: positive for likely up, negative for likely down.
    """
    pattern_score = 0
    
    # 1. Overall uptrend: percentage of up days
    up_days = (returns_df['Return'] > 0).sum()
    total_days = len(returns_df)
    up_percentage = up_days / total_days
    if up_percentage > 0.6:
        pattern_score += 2  # Strong uptrend
    elif up_percentage > 0.5:
        pattern_score += 1  # Mild uptrend
    
    # 2. Dip rebounds: frequency of up after significant down (>1%)
    dips = returns_df['Return'] < -1
    rebounds = returns_df['Return'].shift(-1)[dips] > 0  # Next day up after dip
    rebound_rate = rebounds.sum() / dips.sum() if dips.sum() > 0 else 0
    if rebound_rate > 0.7:
        pattern_score += 2  # Strong rebound pattern
    elif rebound_rate > 0.5:
        pattern_score += 1
    
    # 3. Recent momentum: last 5 days average return
    recent_returns = returns_df['Return'].tail(5)
    avg_recent = recent_returns.mean()
    if avg_recent > 0.5:
        pattern_score += 1
    elif avg_recent < -0.5:
        pattern_score -= 1
    
    # 4. Check if last day was a dip (predict rebound)
    last_return = returns_df['Return'].iloc[-1]
    if last_return < -1:
        pattern_score += 1  # Likely rebound based on historical logic
    
    return pattern_score

def get_recent_news(ticker):
    """
    Fetch recent news headlines using yfinance.
    Returns list of news titles.
    """
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if not news:
            return []
        # Get last 10 news items' titles (or all if fewer)
        # Handle different possible key names for title
        titles = []
        for item in news[:10]:
            title = item.get('title') or item.get('Title') or item.get('headline', '')
            if title:
                titles.append(title)
        return titles
    except Exception as e:
        # If news fetch fails, return empty list to continue with other analysis
        return []

def analyze_news_sentiment(news_titles):
    """
    AI-powered sentiment analysis using Grok model.
    Returns a sentiment score: positive for bullish news, negative for bearish.
    """
    if not news_titles:
        return 0
    
    try:
        # Prepare news headlines for analysis
        news_text = "\n".join([f"- {title}" for title in news_titles[:10]])
        
        # Call Grok AI for sentiment analysis
        response = grok_client.chat.completions.create(
            model="grok-2-1212",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial sentiment analysis expert. Analyze the sentiment of stock-related news headlines and provide a numerical score from -5 to +5, where negative scores indicate bearish sentiment and positive scores indicate bullish sentiment. Respond with only the numerical score, no explanation."
                },
                {
                    "role": "user",
                    "content": f"Analyze the sentiment of these stock news headlines and return a score from -5 to +5:\n\n{news_text}"
                }
            ],
            temperature=0,
            max_tokens=10
        )
        
        # Extract numerical score from response
        score_text = response.choices[0].message.content.strip()
        # Try to extract number from response
        import re
        numbers = re.findall(r'-?\d+(?:\.\d+)?', score_text)
        if numbers:
            sentiment_score = float(numbers[0])
            # Clamp to expected range
            sentiment_score = max(-5, min(5, sentiment_score))
            return int(sentiment_score)
        else:
            return 0
            
    except Exception as e:
        # Fallback to simple keyword-based analysis if AI call fails
        print(f"AI sentiment analysis failed, using fallback: {e}")
        return fallback_sentiment_analysis(news_titles)

def fallback_sentiment_analysis(news_titles):
    """
    Fallback keyword-based sentiment analysis.
    """
    POSITIVE_KEYWORDS = ['beat', 'surpass', 'growth', 'upward', 'positive', 'strong', 'rally', 'buy', 'upgrade', 'exemption', 'resumption']
    NEGATIVE_KEYWORDS = ['miss', 'decline', 'downward', 'negative', 'weak', 'dip', 'sell', 'downgrade', 'tariff', 'sanction', 'restriction']
    
    sentiment_score = 0
    for title in news_titles:
        title_lower = title.lower()
        pos_count = sum(1 for word in POSITIVE_KEYWORDS if re.search(r'\b' + word + r'\b', title_lower))
        neg_count = sum(1 for word in NEGATIVE_KEYWORDS if re.search(r'\b' + word + r'\b', title_lower))
        sentiment_score += pos_count - neg_count
    
    return sentiment_score

def get_valuation_metrics(ticker):
    """
    Fetch basic valuation metrics like forward P/E.
    Returns a score: positive if undervalued relative to simple threshold.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        forward_pe = info.get('forwardPE', None)
        if forward_pe is None or forward_pe <= 0:
            return 0
        # Arbitrary threshold: <20 undervalued, >50 overvalued (adjust based on sector)
        if forward_pe < 20:
            return 1  # Bullish
        elif forward_pe > 50:
            return -1  # Bearish (but growth stocks like NVDA can rally despite high PE)
        return 0
    except Exception as e:
        # If valuation fetch fails, return neutral score
        return 0

def predict_direction(ticker):
    """
    Combine all analyses to predict if stock will go up or down next day.
    """
    try:
        # Get historical data and patterns
        returns_df = get_historical_data(ticker)
        pattern_score = analyze_patterns(returns_df)
        
        # Get news and sentiment
        news_titles = get_recent_news(ticker)
        sentiment_score = analyze_news_sentiment(news_titles)
        
        # Get valuation score
        valuation_score = get_valuation_metrics(ticker)
        
        # Total score: weighted sum (patterns most important, then sentiment, then valuation)
        total_score = (pattern_score * 2) + sentiment_score + valuation_score
        
        # Prediction logic
        if total_score > 2:
            return "Up"
        elif total_score < -2:
            return "Down"
        else:
            return "Uncertain (neutral score)"
    
    except Exception as e:
        return f"Error: {str(e)}"

# Example usage
if __name__ == "__main__":
    ticker = input("Enter stock ticker (e.g., NVDA): ").upper()
    prediction = predict_direction(ticker)
    print(f"Predicted direction for {ticker} next trading day: {prediction}")
