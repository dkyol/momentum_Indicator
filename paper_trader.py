import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz
import logging
from models import Trade, Position, Portfolio, TradingLog, get_session, create_tables
from momentum_analyzer import get_momentum_summary
import time
import schedule
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaperTrader:
    def __init__(self):
        self.initial_investment = 10000.0
        self.trade_percentage = 0.4  # 40% per trade
        self.profit_target = 0.03  # 3% profit target
        self.stop_loss = 0.008  # 0.8% stop loss
        self.est_tz = pytz.timezone('US/Eastern')
        
        # Initialize database
        create_tables()
        self.initialize_portfolio()
    
    def initialize_portfolio(self):
        """Initialize portfolio if it doesn't exist"""
        session = get_session()
        try:
            portfolio = session.query(Portfolio).first()
            if not portfolio:
                portfolio = Portfolio(
                    cash_balance=self.initial_investment,
                    total_value=self.initial_investment,
                    last_updated=datetime.utcnow()
                )
                session.add(portfolio)
                session.commit()
                self.log_message("Portfolio initialized with $10,000", "INFO")
        finally:
            session.close()
    
    def log_message(self, message, log_type="INFO"):
        """Log a message to database and console"""
        session = get_session()
        try:
            log_entry = TradingLog(
                timestamp=datetime.utcnow(),
                message=message,
                log_type=log_type
            )
            session.add(log_entry)
            session.commit()
            logger.info(f"[{log_type}] {message}")
        finally:
            session.close()
    
    def get_current_price(self, symbol):
        """Get current stock price"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")
            if not data.empty:
                return float(data['Close'].iloc[-1])
            return None
        except Exception as e:
            self.log_message(f"Error getting price for {symbol}: {e}", "ERROR")
            return None
    
    def get_top_momentum_stocks(self):
        """Get top 2 stocks from momentum analysis by probability index"""
        try:
            # Use the fixed list of 15 stocks for momentum analysis
            tickers = ['NVDA', 'AMD', 'TSLA', 'SPY', 'HOOD', 'GOOGL', 'IONQ', 'ASTS', 'CRDO', 'OPFI', 'EGO', 'LUNR', 'RKLB', 'VRT', 'RDW', 'PL']
            momentum_data = get_momentum_summary(tickers)
            if not momentum_data:
                self.log_message("No momentum data available", "ERROR")
                return []
            
            # Sort by probability index (descending) and get top 2
            sorted_stocks = sorted(momentum_data, key=lambda x: x.get('Probability_Index', 0), reverse=True)
            top_2 = sorted_stocks[:2]
            
            symbols = [stock['Symbol'] for stock in top_2]
            self.log_message(f"Top momentum stocks selected: {symbols} with probability indices: {[s.get('Probability_Index', 0) for s in top_2]}", "INFO")
            return symbols
        except Exception as e:
            self.log_message(f"Error getting momentum stocks: {e}", "ERROR")
            return []
    
    def execute_buy_order(self, symbol, price):
        """Execute a buy order for 40% of portfolio value"""
        session = get_session()
        try:
            portfolio = session.query(Portfolio).first()
            if not portfolio:
                return False
            
            trade_amount = portfolio.total_value * self.trade_percentage
            quantity = trade_amount / price
            
            # Check if we have enough cash
            if trade_amount > portfolio.cash_balance:
                self.log_message(f"Insufficient cash for {symbol} trade", "ERROR")
                return False
            
            # Update cash balance
            portfolio.cash_balance -= trade_amount
            
            # Create or update position
            position = session.query(Position).filter_by(symbol=symbol).first()
            if position:
                # Update existing position
                total_cost = (position.quantity * position.average_cost) + trade_amount
                position.quantity += quantity
                position.average_cost = total_cost / position.quantity
            else:
                # Create new position with entry price tracking
                est_time = datetime.now(self.est_tz).replace(tzinfo=None)
                position = Position(
                    symbol=symbol,
                    quantity=quantity,
                    average_cost=price,
                    entry_price=price,  # Track entry price for PnL calculation
                    entry_time=est_time,
                    is_active=True
                )
                session.add(position)
            
            # Record trade with position tracking
            est_time = datetime.now(self.est_tz).replace(tzinfo=None)
            trade = Trade(
                symbol=symbol,
                trade_type='BUY',
                quantity=quantity,
                price=price,
                timestamp=est_time,
                investment_amount=trade_amount,
                reason='momentum_entry',
                portfolio_value=portfolio.total_value,
                pnl=0.0,  # No PnL on entry
                position_id=position.id if hasattr(position, 'id') else None
            )
            session.add(trade)
            
            session.commit()
            self.log_message(f"BUY: {quantity:.4f} shares of {symbol} @ ${price:.2f} (${trade_amount:.2f})", "TRADE")
            return True
            
        except Exception as e:
            session.rollback()
            self.log_message(f"Error executing buy order for {symbol}: {e}", "ERROR")
            return False
        finally:
            session.close()
    
    def execute_sell_order(self, symbol, price, reason):
        """Execute a sell order for a position"""
        session = get_session()
        try:
            position = session.query(Position).filter_by(symbol=symbol, is_active=True).first()
            if not position:
                return False
            
            portfolio = session.query(Portfolio).first()
            if not portfolio:
                return False
            
            # Calculate sale proceeds
            sale_amount = position.quantity * price
            
            # Update cash balance
            portfolio.cash_balance += sale_amount
            
            # Calculate P&L
            cost_basis = position.quantity * position.average_cost
            pnl = sale_amount - cost_basis
            
            # Update position with exit information
            est_time = datetime.now(self.est_tz).replace(tzinfo=None)
            position.exit_price = price
            position.exit_time = est_time
            position.realized_pnl = pnl
            position.is_active = False
            
            # Record trade with comprehensive tracking
            trade = Trade(
                symbol=symbol,
                trade_type='SELL',
                quantity=position.quantity,
                price=price,
                timestamp=est_time,
                investment_amount=sale_amount,
                reason=reason,
                portfolio_value=portfolio.total_value + pnl,
                pnl=pnl,
                position_id=position.id
            )
            session.add(trade)
            
            # Update portfolio P&L
            portfolio.daily_pnl += pnl
            portfolio.total_pnl += pnl
            
            session.commit()
            # Log comprehensive exit information
            entry_price = position.entry_price if hasattr(position, 'entry_price') else position.average_cost
            pnl_pct = (pnl / cost_basis) * 100 if cost_basis > 0 else 0
            self.log_message(f"SELL: {position.quantity:.4f} shares of {symbol} @ ${price:.2f} | Entry: ${entry_price:.2f} | Exit: ${price:.2f} | P&L: ${pnl:.2f} ({pnl_pct:+.2f}%) | Reason: {reason}", "TRADE")
            return True
            
        except Exception as e:
            session.rollback()
            self.log_message(f"Error executing sell order for {symbol}: {e}", "ERROR")
            return False
        finally:
            session.close()
    
    def check_exit_conditions(self):
        """Check if any positions should be closed"""
        session = get_session()
        try:
            active_positions = session.query(Position).filter_by(is_active=True).all()
            
            for position in active_positions:
                current_price = self.get_current_price(position.symbol)
                if current_price is None:
                    continue
                
                # Calculate return percentage
                return_pct = (current_price - position.average_cost) / position.average_cost
                
                # Check profit target (3%)
                if return_pct >= self.profit_target:
                    self.execute_sell_order(position.symbol, current_price, "profit_target")
                
                # Check stop loss (0.8%)
                elif return_pct <= -self.stop_loss:
                    self.execute_sell_order(position.symbol, current_price, "stop_loss")
        
        finally:
            session.close()
    
    def execute_morning_trades(self):
        """Execute morning trades at 10:15 AM EST"""
        return self.morning_trade_execution()
    
    def close_all_positions(self):
        """Close all positions (wrapper for end_of_day_close)"""
        return self.end_of_day_close()
    
    def end_of_day_close(self):
        """Close all positions at end of trading day"""
        session = get_session()
        try:
            active_positions = session.query(Position).filter_by(is_active=True).all()
            
            for position in active_positions:
                current_price = self.get_current_price(position.symbol)
                if current_price is not None:
                    self.execute_sell_order(position.symbol, current_price, "eod_close")
        finally:
            session.close()
    
    def update_portfolio_value(self):
        """Update total portfolio value including positions"""
        session = get_session()
        try:
            portfolio = session.query(Portfolio).first()
            if not portfolio:
                return
            
            total_position_value = 0
            active_positions = session.query(Position).filter_by(is_active=True).all()
            
            for position in active_positions:
                current_price = self.get_current_price(position.symbol)
                if current_price is not None:
                    total_position_value += position.quantity * current_price
            
            portfolio.total_value = portfolio.cash_balance + total_position_value
            # Update with EST timezone
            est_tz = pytz.timezone('US/Eastern')
            portfolio.last_updated = datetime.now(est_tz).replace(tzinfo=None)  # Store as naive datetime
            session.commit()
            
            self.log_message(f"Portfolio updated: Total Value ${portfolio.total_value:.2f}, Positions: {len(active_positions)}", "INFO")
            
        finally:
            session.close()
    
    def is_valid_trading_time(self):
        """Check if current time is valid for trading (10:15 AM EST on weekdays)"""
        now = datetime.now(self.est_tz)
        
        # Check if it's a weekday (Monday=0, Friday=4)
        if now.weekday() > 4:  # Saturday=5, Sunday=6
            return False, "Trading only occurs Monday-Friday"
        
        # Check if it's during market hours (9:30 AM - 4:00 PM EST)
        current_time = now.time()
        market_open = datetime.strptime("09:30", "%H:%M").time()
        market_close = datetime.strptime("16:00", "%H:%M").time()
        
        if not (market_open <= current_time <= market_close):
            return False, "Trading only occurs during market hours (9:30 AM - 4:00 PM EST)"
        
        # For scheduled trades, must be exactly 10:15 AM
        scheduled_time = datetime.strptime("10:15", "%H:%M").time()
        current_hour_minute = datetime.strptime(f"{current_time.hour:02d}:{current_time.minute:02d}", "%H:%M").time()
        
        if current_hour_minute != scheduled_time:
            return False, f"Scheduled trades only execute at 10:15 AM EST, current time is {now.strftime('%I:%M %p EST')}"
        
        return True, "Valid trading time"

    def morning_trade_execution(self, force_execute=False):
        """Execute morning trades at 10:15 AM EST with time validation"""
        try:
            # Validate trading time unless forced (for testing/recovery)
            if not force_execute:
                is_valid, reason = self.is_valid_trading_time()
                if not is_valid:
                    self.log_message(f"Trade execution blocked: {reason}", "WARNING")
                    return False

            # Stand down on risk-off days (per market regime panel).
            # Fail-CLOSED: if the regime cache is unreadable for any
            # reason we refuse to open new positions rather than
            # default to "risk-on".  A stale or missing regime read
            # is treated the same as risk-off: the safer side for a
            # capital-allocation decision.
            try:
                from market_regime import get_cached_market_regime, is_risk_on
                regime = get_cached_market_regime().get("regime")
                if not is_risk_on():
                    self.log_message(
                        f"Trade execution skipped: market regime is {regime}",
                        "WARNING",
                    )
                    return False
            except Exception as e:
                self.log_message(
                    f"Trade execution skipped: regime check unavailable "
                    f"(failing closed for safety): {e}",
                    "WARNING",
                )
                return False

            self.log_message("Starting morning trade execution", "INFO")
            
            # Get top 2 momentum stocks
            top_stocks = self.get_top_momentum_stocks()
            
            for symbol in top_stocks:
                current_price = self.get_current_price(symbol)
                if current_price is not None:
                    self.execute_buy_order(symbol, current_price)
                    time.sleep(1)  # Small delay between trades
            
            self.update_portfolio_value()
            
        except Exception as e:
            self.log_message(f"Error in morning trade execution: {e}", "ERROR")
    
    def monitoring_cycle(self):
        """Monitor positions every 2 minutes during trading hours"""
        try:
            # Only monitor during market hours
            if not self.is_trading_hours():
                return
                
            est_time = datetime.now(self.est_tz)
            self.log_message(f"Starting 2-minute monitoring cycle at {est_time.strftime('%I:%M %p EST')}", "INFO")
            
            self.check_exit_conditions()
            self.update_portfolio_value()
            
            self.log_message(f"Completed 2-minute monitoring cycle at {est_time.strftime('%I:%M %p EST')}", "INFO")
        except Exception as e:
            self.log_message(f"Error in monitoring cycle: {e}", "ERROR")
    
    def is_trading_hours(self):
        """Check if current time is during trading hours (9:30 AM - 4:00 PM EST)"""
        now = datetime.now(self.est_tz)
        trading_start = now.replace(hour=9, minute=30, second=0, microsecond=0)
        trading_end = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        # Only trade on weekdays
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        is_open = trading_start <= now <= trading_end
        return is_open
    
    def get_portfolio_summary(self):
        """Get current portfolio summary"""
        session = get_session()
        try:
            portfolio = session.query(Portfolio).first()
            if not portfolio:
                return None
            
            active_positions = session.query(Position).filter_by(is_active=True).all()
            
            positions_data = []
            total_position_value = 0
            
            for position in active_positions:
                current_price = self.get_current_price(position.symbol)
                if current_price is not None:
                    position_value = position.quantity * current_price
                    total_position_value += position_value
                    pnl = position_value - (position.quantity * position.average_cost)
                    pnl_pct = pnl / (position.quantity * position.average_cost) * 100
                    
                    positions_data.append({
                        'symbol': position.symbol,
                        'quantity': position.quantity,
                        'avg_cost': position.average_cost,
                        'current_price': current_price,
                        'position_value': position_value,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct
                    })
            
            total_value = portfolio.cash_balance + total_position_value
            total_return = ((total_value - self.initial_investment) / self.initial_investment) * 100
            
            # Get recent trades for journal display (last 10 trades)
            recent_trades = session.query(Trade).order_by(Trade.timestamp.desc()).limit(10).all()
            trades_data = []
            for trade in recent_trades:
                # Get entry price from position if available
                entry_price = None
                if trade.position_id:
                    position = session.query(Position).filter_by(id=trade.position_id).first()
                    if position and hasattr(position, 'entry_price'):
                        entry_price = position.entry_price
                
                trades_data.append({
                    'timestamp': trade.timestamp,
                    'symbol': trade.symbol,
                    'trade_type': trade.trade_type,
                    'quantity': trade.quantity,
                    'price': trade.price,
                    'entry_price': entry_price,
                    'pnl': trade.pnl if hasattr(trade, 'pnl') else 0.0,
                    'reason': trade.reason
                })

            return {
                'cash_balance': portfolio.cash_balance,
                'position_value': total_position_value,
                'total_value': total_value,
                'total_pnl': total_value - self.initial_investment,
                'total_return_pct': total_return,
                'positions': positions_data,
                'last_updated': portfolio.last_updated,
                'recent_trades': trades_data
            }
            
        finally:
            session.close()

# Global trader instance
trader = PaperTrader()

def start_trading_scheduler():
    """Start the trading scheduler in a separate thread"""
    
    # Schedule morning trades at 9:35 AM EST
    schedule.every().monday.at("14:35").do(trader.morning_trade_execution)  # 9:35 AM EST = 14:35 UTC
    schedule.every().tuesday.at("14:35").do(trader.morning_trade_execution)
    schedule.every().wednesday.at("14:35").do(trader.morning_trade_execution)
    schedule.every().thursday.at("14:35").do(trader.morning_trade_execution)
    schedule.every().friday.at("14:35").do(trader.morning_trade_execution)
    
    # Schedule end-of-day close at 3:34 PM EST
    schedule.every().monday.at("20:34").do(trader.end_of_day_close)  # 3:34 PM EST = 20:34 UTC
    schedule.every().tuesday.at("20:34").do(trader.end_of_day_close)
    schedule.every().wednesday.at("20:34").do(trader.end_of_day_close)
    schedule.every().thursday.at("20:34").do(trader.end_of_day_close)
    schedule.every().friday.at("20:34").do(trader.end_of_day_close)
    
    # Monitor every 15 minutes during trading hours
    def continuous_monitoring():
        while True:
            if trader.is_trading_hours():
                trader.monitoring_cycle()
                time.sleep(900)  # 15 minutes
            else:
                # Check every 30 minutes during non-trading hours
                time.sleep(1800)
    
    # Start monitoring in a separate thread
    monitor_thread = threading.Thread(target=continuous_monitoring, daemon=True)
    monitor_thread.start()
    
    # Run scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    start_trading_scheduler()