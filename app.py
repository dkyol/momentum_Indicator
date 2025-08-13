import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from stock_analytics import get_high_volume_data
from momentum_analyzer import get_momentum_summary
from scheduler import get_cached_high_volume_stocks, get_cached_momentum_data, get_cached_sma_data, get_last_update_info, is_data_fresh, save_market_data

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Initialize cache on startup if needed
def initialize_cache():
    """Initialize market data cache on startup if not fresh"""
    if not is_data_fresh():
        logging.info("Initializing market data cache on startup...")
        try:
            save_market_data()
        except Exception as e:
            logging.error(f"Failed to initialize cache: {e}")

# Call initialization
initialize_cache()

# Password for the site - use environment variable for security
SITE_PASSWORD = os.environ.get("SITE_PASSWORD", "Eb10f600!")

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
        # Use cached data or fetch fresh data if cache is stale
        from datetime import timezone, timedelta
        est = timezone(timedelta(hours=-5))  # EST timezone
        current_time = datetime.now(est).strftime("%B %d, %Y at %I:%M %p EST")
        
        if is_data_fresh():
            # Use cached data
            high_volume_stocks = get_cached_high_volume_stocks()
            momentum_data = get_cached_momentum_data()
            sma_data = get_cached_sma_data()
            last_update = get_last_update_info()
            if last_update.get('last_update'):
                try:
                    from datetime import datetime as dt
                    import pytz
                    est_tz = pytz.timezone('US/Eastern')
                    update_dt = dt.fromisoformat(last_update['last_update'])
                    current_time = f"Last updated: {update_dt.strftime('%B %d, %Y at %I:%M %p EST')} (cached)"
                except:
                    pass
        else:
            # Fetch fresh data and cache it
            logging.info("Cache is stale, fetching fresh data...")
            save_market_data()
            high_volume_stocks = get_cached_high_volume_stocks()
            momentum_data = get_cached_momentum_data()
            sma_data = get_cached_sma_data()
            current_time = f"{current_time} (fresh data)"
        
        return render_template('index.html', 
                             high_volume_stocks=high_volume_stocks,
                             momentum_data=momentum_data,
                             sma_data=sma_data,
                             query_time=current_time)
    except Exception as e:
        app.logger.error(f"Error loading high volume data: {str(e)}")
        # Still render page even if data fails to load
        return render_template('index.html', 
                             high_volume_stocks=[],
                             momentum_data=[],
                             sma_data=[],
                             query_time="Data unavailable")



@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('index.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
