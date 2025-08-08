#!/usr/bin/env python3

from stock_predictor import predict_direction, get_historical_data
import traceback

try:
    print('Testing TSLA prediction...')
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