#!/usr/bin/env python3

from stock_predictor import predict_direction, get_historical_data, get_recent_news, analyze_news_sentiment
import traceback

try:
    print('Testing fixed news function with NVDA...')
    
    # Test news fetch and AI sentiment
    print('\nTesting news and AI sentiment analysis...')
    news = get_recent_news('NVDA')
    print(f'Found {len(news)} news articles')
    if news:
        print('Sample headlines:')
        for i, headline in enumerate(news[:3]):
            print(f'  {i+1}. {headline}')
        
        sentiment_result = analyze_news_sentiment(news)
        print('Grok AI sentiment analysis:')
        print(f'  Score: {sentiment_result["score"]}')
        print(f'  Article count: {sentiment_result["article_count"]}')
        print(f'  Summary: {sentiment_result["summary"]}')
    else:
        sentiment_result = analyze_news_sentiment([])
        print('No news found, testing empty case:')
        print(f'  Score: {sentiment_result["score"]}')
        print(f'  Article count: {sentiment_result["article_count"]}')
        print(f'  Summary: {sentiment_result["summary"]}')
    
    print('\nTesting full prediction...')
    result = predict_direction('NVDA')
    if isinstance(result, dict):
        print('NVDA prediction result:')
        print(f'  Prediction: {result["prediction"]}')
        print(f'  Total score: {result["total_score"]}')
        print(f'  Pattern score: {result["pattern_score"]}')
        print(f'  Sentiment: {result["sentiment_result"]}')

    else:
        print('NVDA prediction result:', result)
    
except Exception as e:
    print('Error:', str(e))
    traceback.print_exc()