#!/usr/bin/env python3

from stock_predictor import predict_direction, get_historical_data, get_recent_news, analyze_news_sentiment
import traceback

try:
    print('Testing TSLA prediction with Grok AI sentiment analysis...')
    
    # Test news fetch and AI sentiment
    print('\nTesting news and AI sentiment analysis...')
    news = get_recent_news('TSLA')
    print(f'Found {len(news)} news articles')
    if news:
        print('Sample headlines:')
        for i, headline in enumerate(news[:3]):
            print(f'  {i+1}. {headline}')
        
        sentiment = analyze_news_sentiment(news)
        print(f'Grok AI sentiment score: {sentiment}')
    
    print('\nTesting full prediction...')
    result = predict_direction('TSLA')
    print('TSLA prediction result:', result)
    
    print('\nTesting historical data fetch...')
    data = get_historical_data('TSLA')
    print('Data shape:', data.shape)
    print('Columns:', list(data.columns))
    print('Last return: {:.2f}%'.format(data['Return'].iloc[-1]))
    print('Current price: ${:.2f}'.format(data['Adj Close'].iloc[-1]))
    
except Exception as e:
    print('Error:', str(e))
    traceback.print_exc()