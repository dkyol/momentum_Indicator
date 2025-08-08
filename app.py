import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from stock_predictor import predict_direction, get_historical_data, analyze_patterns, get_recent_news, analyze_news_sentiment, get_high_volume_data

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Password for the site
SITE_PASSWORD = "Eb10f600!"

def login_required(f):
    """Decorator to require login for protected routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for password protection"""
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        if password == SITE_PASSWORD:
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            flash('Incorrect password. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Main page with stock prediction interface"""
    try:
        # Get high volume stocks data
        high_volume_df = get_high_volume_data()
        from datetime import timezone, timedelta
        est = timezone(timedelta(hours=-5))  # EST timezone
        current_time = datetime.now(est).strftime("%B %d, %Y at %I:%M %p EST")
        
        # Convert DataFrame to list of dictionaries for template
        high_volume_stocks = []
        if not high_volume_df.empty:
            high_volume_stocks = high_volume_df.to_dict('records')
        
        return render_template('index.html', 
                             high_volume_stocks=high_volume_stocks,
                             query_time=current_time)
    except Exception as e:
        app.logger.error(f"Error loading high volume data: {str(e)}")
        # Still render page even if data fails to load
        return render_template('index.html', 
                             high_volume_stocks=[],
                             query_time="Data unavailable")

@app.route('/predict', methods=['POST'])
@login_required
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
            result = predict_direction(ticker)
            
            # Handle error case
            if isinstance(result, str) and result.startswith("Error:"):
                raise ValueError(result.replace("Error: ", ""))
            
            # Extract data from prediction result
            prediction = result['prediction']
            sentiment_result = result['sentiment_result']
            
            # Determine confidence based on total score
            total_score = result['total_score']
            if total_score > 4:
                confidence = "High"
            elif total_score > 2 or total_score < -2:
                confidence = "Medium"
            else:
                confidence = "Low"
            
            return jsonify({
                'ticker': ticker,
                'prediction': prediction,
                'confidence': confidence,
                'current_price': round(result['current_price'], 2),
                'last_return': round(result['last_return'], 2),
                'pattern_score': result['pattern_score'],
                'sentiment_score': sentiment_result['score'],
                'total_score': total_score,
                'news_count': sentiment_result['article_count'],
                'sentiment_summary': sentiment_result['summary'],
                'analysis_summary': {
                    'pattern_analysis': f"Pattern score: {result['pattern_score']} (based on historical trends and momentum)",
                    'sentiment_analysis': f"AI sentiment: {sentiment_result['score']} from {sentiment_result['article_count']} articles - {sentiment_result['summary']}",
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
