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
grok_client = OpenAI(base_url="https://api.x.ai/v1",
                     api_key=os.environ.get("XAI_API_KEY"))


def get_high_volume_data():
    """
    Get top 10 stocks by daily volume with prior day, week, and month returns.
    Returns a DataFrame with stock symbols, volume, and return percentages.
    """
    try:
        # Popular high-volume tickers to analyze
        high_volume_tickers = [
            'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMD', 'BBAI',
            'SPY', 'PLTR', 'HOOD', 'MU', 'FBTC', 'SMCI', 'SNAP', 'GLD'
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

        # Sort by volume and get top 10
        df = df.sort_values('Volume', ascending=False).head(10)

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
    rebounds = returns_df['Return'].shift(
        -1)[dips] > 0  # Next day up after dip
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
        titles = []
        for item in news[:10]:
            # Handle the nested structure from yfinance API
            if 'content' in item and 'title' in item['content']:
                title = item['content']['title']
                if title:
                    titles.append(title)
            else:
                # Fallback to direct title access if structure is different
                title = item.get('title') or item.get('Title') or item.get(
                    'headline', '')
                if title:
                    titles.append(title)
        return titles
    except Exception as e:
        # If news fetch fails, return empty list to continue with other analysis
        print(f"News fetch error: {e}")
        return []


def analyze_news_sentiment(news_titles):
    """
    AI-powered sentiment analysis using Grok model.
    Returns a dictionary with sentiment score and analysis summary.
    """
    if not news_titles:
        return {
            'score': 0,
            'article_count': 0,
            'summary': 'No recent news articles found for analysis.'
        }

    try:
        # Prepare news headlines for analysis
        news_text = "\n".join([f"- {title}" for title in news_titles[:10]])

        # Call Grok AI for detailed sentiment analysis
        response = grok_client.chat.completions.create(
            model="grok-2-1212",
            messages=[{
                "role":
                "system",
                "content":
                "You are a financial sentiment analysis expert. Analyze the sentiment of stock-related news headlines and provide: 1) A numerical score from -5 to +5 (negative=bearish, positive=bullish), 2) A brief summary sentence explaining the overall sentiment. Format your response as: 'Score: [number]\\nSummary: [one sentence explanation]'"
            }, {
                "role":
                "user",
                "content":
                f"Analyze the sentiment of these {len(news_titles)} stock news headlines:\n\n{news_text}"
            }],
            temperature=0,
            max_tokens=150)

        # Parse response for score and summary
        response_text = response.choices[0].message.content.strip()
        lines = response_text.split('\n')

        # Extract score
        score = 0
        summary = "Unable to parse AI response"

        for line in lines:
            if line.startswith('Score:'):
                score_text = line.replace('Score:', '').strip()
                import re
                numbers = re.findall(r'-?\d+(?:\.\d+)?', score_text)
                if numbers:
                    score = float(numbers[0])
                    score = max(-5, min(5, score))  # Clamp to range
            elif line.startswith('Summary:'):
                summary = line.replace('Summary:', '').strip()

        return {
            'score': int(score),
            'article_count': len(news_titles),
            'summary': summary
        }

    except Exception as e:
        # Fallback to simple keyword-based analysis if AI call fails
        print(f"AI sentiment analysis failed, using fallback: {e}")
        fallback_score = fallback_sentiment_analysis(news_titles)
        return {
            'score':
            fallback_score,
            'article_count':
            len(news_titles),
            'summary':
            f'Used fallback analysis on {len(news_titles)} articles due to AI service unavailability.'
        }


def fallback_sentiment_analysis(news_titles):
    """
    Fallback keyword-based sentiment analysis.
    """
    POSITIVE_KEYWORDS = [
        'beat', 'surpass', 'growth', 'upward', 'positive', 'strong', 'rally',
        'buy', 'upgrade', 'exemption', 'resumption'
    ]
    NEGATIVE_KEYWORDS = [
        'miss', 'decline', 'downward', 'negative', 'weak', 'dip', 'sell',
        'downgrade', 'tariff', 'sanction', 'restriction'
    ]

    sentiment_score = 0
    for title in news_titles:
        title_lower = title.lower()
        pos_count = sum(1 for word in POSITIVE_KEYWORDS
                        if re.search(r'\b' + word + r'\b', title_lower))
        neg_count = sum(1 for word in NEGATIVE_KEYWORDS
                        if re.search(r'\b' + word + r'\b', title_lower))
        sentiment_score += pos_count - neg_count

    return sentiment_score


def predict_direction(ticker):
    """
    Combine all analyses to predict if stock will go up or down next day.
    Returns a dictionary with detailed analysis results.
    """
    try:
        # Get historical data and patterns
        returns_df = get_historical_data(ticker)
        pattern_score = analyze_patterns(returns_df)

        # Get news and sentiment
        news_titles = get_recent_news(ticker)
        sentiment_result = analyze_news_sentiment(news_titles)
        sentiment_score = sentiment_result['score'] if isinstance(
            sentiment_result, dict) else sentiment_result

        # Total score: weighted sum (patterns most important, then sentiment)
        total_score = (pattern_score * 2) + sentiment_score

        # Prediction logic
        if total_score > 2:
            prediction = "Up"
        elif total_score < -2:
            prediction = "Down"
        else:
            prediction = "Uncertain"

        return {
            'prediction': prediction,
            'pattern_score': pattern_score,
            'sentiment_result': sentiment_result,
            'total_score': total_score,
            'current_price': returns_df['Adj Close'].iloc[-1],
            'last_return': returns_df['Return'].iloc[-1]
        }

    except Exception as e:
        return f"Error: {str(e)}"


# Example usage
if __name__ == "__main__":
    ticker = input("Enter stock ticker (e.g., NVDA): ").upper()
    prediction = predict_direction(ticker)
    print(f"Predicted direction for {ticker} next trading day: {prediction}")
