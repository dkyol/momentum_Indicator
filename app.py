import os
import logging
from flask import Flask, render_template, request, jsonify
from stock_predictor import predict_direction, get_historical_data, analyze_patterns, get_recent_news, analyze_news_sentiment, get_valuation_metrics

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

@app.route('/')
def index():
    """Main page with stock prediction interface"""
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict_stock():
    """API endpoint to predict stock direction"""
    try:
        # Get ticker from form data
        ticker = request.form.get('ticker', '').strip().upper()
        
        if not ticker:
            return jsonify({
                'error': 'Please enter a valid stock ticker symbol'
            }), 400
        
        # Validate ticker format (basic check)
        if not ticker.isalpha() or len(ticker) > 5:
            return jsonify({
                'error': 'Invalid ticker format. Please use standard stock symbols (e.g., NVDA, AAPL)'
            }), 400
        
        # Get detailed prediction analysis
        try:
            # Get historical data and patterns
            returns_df = get_historical_data(ticker)
            pattern_score = analyze_patterns(returns_df)
            
            # Get news and sentiment
            news_titles = get_recent_news(ticker)
            sentiment_score = analyze_news_sentiment(news_titles)
            
            # Get valuation score
            valuation_score = get_valuation_metrics(ticker)
            
            # Total score calculation
            total_score = (pattern_score * 2) + sentiment_score + valuation_score
            
            # Prediction logic
            if total_score > 2:
                prediction = "Up"
                confidence = "High" if total_score > 4 else "Medium"
            elif total_score < -2:
                prediction = "Down"
                confidence = "High" if total_score < -4 else "Medium"
            else:
                prediction = "Uncertain"
                confidence = "Low"
            
            # Get current price for display
            current_price = returns_df['Adj Close'].iloc[-1]
            last_return = returns_df['Return'].iloc[-1]
            
            return jsonify({
                'ticker': ticker,
                'prediction': prediction,
                'confidence': confidence,
                'current_price': round(current_price, 2),
                'last_return': round(last_return, 2),
                'pattern_score': pattern_score,
                'sentiment_score': sentiment_score,
                'valuation_score': valuation_score,
                'total_score': total_score,
                'news_count': len(news_titles),
                'analysis_summary': {
                    'pattern_analysis': f"Pattern score: {pattern_score} (based on historical trends and momentum)",
                    'sentiment_analysis': f"News sentiment: {sentiment_score} (from {len(news_titles)} recent articles)",
                    'valuation_analysis': f"Valuation score: {valuation_score} (based on forward P/E ratio)"
                }
            })
            
        except ValueError as ve:
            app.logger.error(f"ValueError for ticker {ticker}: {str(ve)}")
            return jsonify({
                'error': f'Unable to find data for ticker "{ticker}". Please check if it\'s a valid stock symbol.'
            }), 404
            
        except Exception as e:
            app.logger.error(f"Unexpected error for ticker {ticker}: {str(e)}")
            return jsonify({
                'error': 'Unable to analyze stock data. Please try again later.'
            }), 500
            
    except Exception as e:
        app.logger.error(f"Request processing error: {str(e)}")
        return jsonify({
            'error': 'An error occurred while processing your request.'
        }), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('index.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
